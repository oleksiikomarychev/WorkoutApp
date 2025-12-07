from dataclasses import dataclass
from enum import Enum


class MessageCommandKind(str, Enum):
    MASS_EDIT_ACTIVE = "mass_edit_active"
    MASS_EDIT_FLEX = "mass_edit_flex"
    FSM_ACTIVATE = "fsm_activate"
    PLAIN = "plain"


@dataclass
class MessageCommand:
    kind: MessageCommandKind
    content: str
    rest: str = ""


class MessageCommandParser:
    def parse(self, content: str) -> MessageCommand:
        stripped = content.strip()

        if stripped.startswith("/mass-edit"):
            rest = stripped[len("/mass-edit") :].strip()
            return MessageCommand(
                kind=MessageCommandKind.MASS_EDIT_ACTIVE,
                content=content,
                rest=rest,
            )

        if stripped.startswith("/mass_edit"):
            rest = stripped[len("/mass_edit") :].strip()
            return MessageCommand(
                kind=MessageCommandKind.MASS_EDIT_FLEX,
                content=content,
                rest=rest,
            )

        if stripped == "@fsm_plan_generator":
            return MessageCommand(
                kind=MessageCommandKind.FSM_ACTIVATE,
                content=content,
                rest="",
            )

        return MessageCommand(
            kind=MessageCommandKind.PLAIN,
            content=content,
            rest=stripped,
        )
