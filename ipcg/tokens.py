from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto


class TokenKind(IntEnum):
    EOF = auto()
    IDENTIFIER = auto()
    MODULE = auto()
    HEX = auto()
    NUMBER = auto()
    COLON = auto()
    DOUBLECOLON = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_ANGLE = auto()
    RIGHT_ANGLE = auto()
    ARROW = auto()
    EMPTY_LINE = auto()
    KEYWORD = auto()
    M_FLAG = auto()
    V_FLAG = auto()
    A_FLAG = auto()
    DOT = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    literal: str
    line: int

    @classmethod
    def eof(cls) -> Token:
        return Token(kind=TokenKind.EOF, literal="EOF", line=0)
