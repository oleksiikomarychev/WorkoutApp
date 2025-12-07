from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..prompts.simple_chat import DEFAULT_SYSTEM_PROMPT
from .langchain_runtime import get_chat_llm


@dataclass
class SimpleChatSession:
    user_id: str | None = None
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    history: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._llm = get_chat_llm(temperature=0.4)

    def to_state(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "system_prompt": self.system_prompt,
            "history": list(self.history),
        }

    @classmethod
    def from_state(
        cls,
        state: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
        system_prompt: str | None = None,
    ) -> SimpleChatSession:
        state = state or {}
        session = cls(
            user_id=user_id or state.get("user_id"),
            system_prompt=system_prompt or state.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
        )
        history = state.get("history")
        if isinstance(history, list):
            session.history = [
                {"role": str(turn.get("role", "")), "content": str(turn.get("content", ""))}
                for turn in history
                if isinstance(turn, dict)
            ]
        return session

    async def respond(self, user_input: str) -> str:
        if not user_input.strip():
            return ""

        self.history.append({"role": "user", "content": user_input})

        messages = [SystemMessage(content=self.system_prompt)]
        for turn in self.history[-30:]:
            role = turn.get("role")
            content = turn.get("content", "")
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        response = await self._llm.ainvoke(messages)
        text = response.content if isinstance(response.content, str) else str(response.content)
        text = text.strip()
        self.history.append({"role": "assistant", "content": text})
        return text


async def simple_chat_generator(
    user_input: str,
    state: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    session = SimpleChatSession.from_state(state, user_id=user_id, system_prompt=system_prompt)
    reply = await session.respond(user_input)
    return {"reply": reply, "state": session.to_state()}
