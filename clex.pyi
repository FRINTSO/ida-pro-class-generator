from typing import Final

TOKEN_EOF: Final[int]
TOKEN_IDENTIFIER: Final[int]
TOKEN_MODULE: Final[int]
TOKEN_COLON: Final[int]
TOKEN_LEFT_ANGLE: Final[int]
TOKEN_RIGHT_ANGLE: Final[int]
TOKEN_HEX: Final[int]
TOKEN_ARROW: Final[int]
TOKEN_EMPTY_LINE: Final[int]
TOKEN_NUMBER: Final[int]
TOKEN_KEYWORD: Final[int]
TOKEN_ERROR: Final[int]
TOKEN_DOUBLECOLON: Final[int]
TOKEN_BACKTICK: Final[int]
TOKEN_APOSTROPHE: Final[int]
TOKEN_DOT: Final[int]
TOKEN_COMMA: Final[int]
TOKEN_AMPERSAND: Final[int]
TOKEN_ASTERISK: Final[int]
TOKEN_HYPHEN: Final[int]
TOKEN_UNDERSCORE: Final[int]

class Token:
    type: int
    literal: str
    line: int
    def __init__(self, type: int, literal: str, line: int) -> None: ...

class Lexer:
    text: str
    start: str
    current: str
    line: int
    def __init__(self, text: str) -> None: ...
    def scan_token(self) -> Token: ...
    def advance(self) -> str: ...
    def peek(self) -> str: ...
    def peek_next(self) -> str: ...
    def match(self, expected: str) -> bool: ...
    def skip_whitespace(self) -> None: ...
    def make_token(self, type: int) -> Token: ...
    def is_at_end(self) -> bool: ...
    @staticmethod
    def isalpha(c: str) -> bool: ...
    @staticmethod
    def isdigit(c: str) -> bool: ...
    @staticmethod
    def isalnum(c: str) -> bool: ...
