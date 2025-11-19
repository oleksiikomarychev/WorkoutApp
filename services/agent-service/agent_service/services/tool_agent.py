from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .llm_wrapper import generate_structured_output


@dataclass
class ToolSpec:
    """Specification of a single callable tool for the LLM agent.

    The model sees only name/description/parameters_schema; the handler is
    executed server-side when the model decides to call the tool.
    """

    name: str
    description: str
    parameters_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]


@dataclass
class ToolCallResult:
    """Result of a single decision + optional tool execution."""

    decision_type: str  # "tool_call" or "answer" or "error"
    tool_name: Optional[str]
    arguments: Dict[str, Any]
    answer: Optional[str]
    tool_result: Any
    raw_decision: Dict[str, Any]


async def _decide_tool_call(
    *,
    user_prompt: str,
    tools: List[ToolSpec],
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """Ask the LLM to decide whether to call a tool or answer directly.

    Returns the raw JSON decision dict produced by `generate_structured_output`.
    """

    tools_descriptions: List[str] = []
    for t in tools:
        tools_descriptions.append(
            f"- {t.name}: {t.description}. Parameters JSON schema: {t.parameters_schema!r}"
        )
    tools_block = "\n".join(tools_descriptions)

    system_prompt = (
        "You are an AI assistant with access to tools.\n\n"
        "You MUST respond strictly as JSON matching the given schema.\n\n"
        "Available tools (each with a JSON parameters schema describing its input):\n"
        f"{tools_block}\n\n"
        "If you decide to call a tool, respond as:\n"
        "{\n"
        "  \"type\": \"tool_call\",\n"
        "  \"tool\": \"<tool_name>\",\n"
        "  \"arguments\": { ... }\n"
        "}\n\n"
        "If you decide to answer directly, respond as:\n"
        "{\n"
        "  \"type\": \"answer\",\n"
        "  \"answer\": \"<final natural language answer>\"\n"
        "}\n"
    )

    full_prompt = f"{system_prompt}\n\nUser request:\n{user_prompt}"

    schema: Dict[str, Any] = {
        "type": "object",
        "required": ["type"],
        "properties": {
            "type": {
                "type": "string",
                "enum": ["tool_call", "answer"],
            },
            "tool": {
                "type": "string",
                "enum": [t.name for t in tools],
            },
            "arguments": {
                "type": "object",
                "additionalProperties": True,
            },
            "answer": {
                "type": "string",
            },
        },
    }

    decision = await generate_structured_output(
        prompt=full_prompt,
        response_schema=schema,
        temperature=temperature,
        max_output_tokens=2048,
    )

    if not isinstance(decision, Dict):
        raise ValueError("LLM decision is not a JSON object")

    return decision


async def decide_tool_call(
    *,
    user_prompt: str,
    tools: List[ToolSpec],
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """Public helper that delegates to the internal decision routine.

    This is useful for HTTP endpoints that want to inspect the LLM's choice
    and then execute tools with additional server-side constraints.
    """

    return await _decide_tool_call(
        user_prompt=user_prompt,
        tools=tools,
        temperature=temperature,
    )


async def run_tools_agent(
    *,
    user_prompt: str,
    tools: List[ToolSpec],
    temperature: float = 0.2,
) -> ToolCallResult:
    """High-level entry point: decide & optionally execute a tool.

    - Asks the LLM whether to call one of the provided tools or answer directly.
    - If it chooses a tool and the tool exists, executes its handler with the
      provided arguments.
    - Returns a ToolCallResult that callers can serialize or post-process.
    """

    if not tools:
        raise ValueError("run_tools_agent requires at least one tool")

    decision = await _decide_tool_call(
        user_prompt=user_prompt,
        tools=tools,
        temperature=temperature,
    )

    raw_type = str(decision.get("type") or "").lower()
    tool_name_value = decision.get("tool")
    arguments_value = decision.get("arguments")
    answer_value = decision.get("answer")

    if not isinstance(arguments_value, dict):
        arguments_value = {}

    tool_name: Optional[str]
    if isinstance(tool_name_value, str) and tool_name_value:
        tool_name = tool_name_value
    else:
        tool_name = None

    answer: Optional[str]
    if isinstance(answer_value, str) and answer_value:
        answer = answer_value
    else:
        answer = None

    decision_type = raw_type if raw_type in {"tool_call", "answer"} else "error"

    # Default: no tool execution
    tool_result: Any = None

    if decision_type == "tool_call" and tool_name is not None:
        by_name = {t.name: t for t in tools}
        spec = by_name.get(tool_name)
        if spec is None:
            decision_type = "error"
        else:
            tool_result = await spec.handler(arguments_value)

    return ToolCallResult(
        decision_type=decision_type,
        tool_name=tool_name,
        arguments=arguments_value,
        answer=answer,
        tool_result=tool_result,
        raw_decision=decision,
    )
