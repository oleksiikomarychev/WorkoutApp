from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool as lc_tool

from ..prompts.tool_agent import build_tools_decision_system_prompt
from .langchain_runtime import get_chat_llm


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class ToolCallResult:
    decision_type: str
    tool_name: str | None
    arguments: dict[str, Any]
    answer: str | None
    tool_result: Any
    raw_decision: dict[str, Any]


def _build_langchain_tools(tools: list[ToolSpec]):
    lc_tools = []

    for spec in tools:

        async def _tool_impl(_spec: ToolSpec = spec, **kwargs: Any) -> Any:
            return await _spec.handler(dict(kwargs))

        wrapped = lc_tool(
            name=spec.name,
            description=f"{spec.description}. Parameters schema: {spec.parameters_schema!r}",
        )(_tool_impl)

        lc_tools.append(wrapped)

    return lc_tools


def _create_agent_executor(tools: list[ToolSpec], temperature: float) -> AgentExecutor:
    lc_tools = _build_langchain_tools(tools)
    llm = get_chat_llm(temperature=temperature)

    tools_descriptions: list[str] = []
    for t in tools:
        tools_descriptions.append(f"- {t.name}: {t.description}. Parameters JSON schema: {t.parameters_schema!r}")
    tools_block = "\n".join(tools_descriptions)
    build_tools_decision_system_prompt(tools_block)

    system_text = (
        "You are a helpful WorkoutApp assistant with access to tools.\n"
        "You may call one or multiple tools in sequence when needed, and you "
        "should provide a clear final answer to the user after using tools.\n"
        "When tools are sufficient, prefer using them instead of guessing. "
        "If tools are not needed, you may answer directly.\n\n"
        "Most user inputs will contain an explicit 'Context: ...' section that "
        "describes the current WorkoutApp screen (for example: 'Screen: active_plan', "
        "'Screen: coach_athlete_plan', 'Screen: plan_details', 'Screen: user_profile', "
        "'Screen: analytics', 'Screen: coach_athletes', etc.) and may include "
        "detailed instructions about WHEN to use each tool. YOU MUST follow those "
        "screen-specific instructions with high priority when deciding which tools "
        "to call and what arguments to pass.\n\n"
        "For example, the context may state that on the active_plan screen you "
        "should use schedule-shift tools for changing workout dates, mass-edit tools "
        "for changing exercises/sets/volume, and analysis tools when the user asks "
        "about plan structure or progress. On the plan_details screen, the word "
        "'macros' in context usually refers to training plan automation rules, not "
        "nutrition macros, and the context will tell you which macros tools to use.\n\n"
        f"Tool descriptions and JSON parameter schemas (for your reference):\n{tools_block}\n\n"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_text),
            ("human", "{input}"),
        ]
    )

    agent = create_tool_calling_agent(llm, lc_tools, prompt)
    return AgentExecutor(agent=agent, tools=lc_tools, max_iterations=5, verbose=False)


async def run_tools_agent(
    *,
    user_prompt: str,
    tools: list[ToolSpec],
    temperature: float = 0.2,
) -> ToolCallResult:
    if not tools:
        raise ValueError("run_tools_agent requires at least one tool")

    executor = _create_agent_executor(tools, temperature=temperature)

    result: dict[str, Any] = await executor.ainvoke({"input": user_prompt})
    output = result.get("output")
    intermediate_steps = result.get("intermediate_steps", [])

    decision_type: str = "answer"
    tool_name: str | None = None
    arguments_value: dict[str, Any] = {}
    tool_result: Any = None

    if intermediate_steps:
        decision_type = "tool_call"

        last_step = intermediate_steps[-1]
        if isinstance(last_step, tuple) and len(last_step) == 2:
            action, observation = last_step  # type: ignore[misc]
            tool_name = getattr(action, "tool", None)
            tool_input = getattr(action, "tool_input", None)
            if isinstance(tool_input, dict):
                arguments_value = tool_input
            elif tool_input is not None:
                arguments_value = {"input": tool_input}
            tool_result = observation

    if decision_type == "answer" and not output:
        decision_type = "error"

    steps_serialized: list[dict[str, Any]] = []
    for step in intermediate_steps:
        if not (isinstance(step, tuple) and len(step) == 2):
            continue
        action, observation = step
        steps_serialized.append(
            {
                "tool": getattr(action, "tool", None),
                "tool_input": getattr(action, "tool_input", None),
                "observation_preview": str(observation)[:500],
            }
        )

    raw_decision: dict[str, Any] = {
        "output": output,
        "steps": steps_serialized,
    }

    answer: str | None
    if isinstance(output, str):
        answer = output
    elif output is None:
        answer = None
    else:
        answer = str(output)

    return ToolCallResult(
        decision_type=decision_type,
        tool_name=tool_name,
        arguments=arguments_value,
        answer=answer,
        tool_result=tool_result,
        raw_decision=raw_decision,
    )


async def decide_tool_call(
    *,
    user_prompt: str,
    tools: list[ToolSpec],
    temperature: float = 0.2,
) -> dict[str, Any]:
    result = await run_tools_agent(user_prompt=user_prompt, tools=tools, temperature=temperature)
    return {
        "type": result.decision_type,
        "tool": result.tool_name,
        "arguments": result.arguments,
        "answer": result.answer,
    }
