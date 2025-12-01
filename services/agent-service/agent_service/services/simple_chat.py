"""Lightweight chat session for plain GPT-style conversations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..prompts.simple_chat import DEFAULT_SYSTEM_PROMPT
from .conversation_graph import _initialize_chat_llm


@dataclass
class SimpleChatSession:
    user_id: Optional[str] = None
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    history: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Create a dedicated LLM instance per session to keep temperature settings isolated.
        self._llm = _initialize_chat_llm(temperature=0.4)

    def to_state(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "system_prompt": self.system_prompt,
            "history": list(self.history),
        }

    @classmethod
    def from_state(
        cls,
        state: Optional[Dict[str, Any]] = None,
        *,
        user_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> "SimpleChatSession":
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
        for turn in self.history[-30:]:  # keep last 30 turns to limit prompt size
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
    state: Optional[Dict[str, Any]] = None,
    *,
    user_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    session = SimpleChatSession.from_state(state, user_id=user_id, system_prompt=system_prompt)
    reply = await session.respond(user_input)
    return {"reply": reply, "state": session.to_state()}
