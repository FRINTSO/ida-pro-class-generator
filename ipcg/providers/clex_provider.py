from __future__ import annotations

from collections.abc import Iterator

import clex

from ..tokens import Token, TokenKind

_CLEX_MAP: dict[int, TokenKind] = {
    clex.TOKEN_EOF: TokenKind.EOF,
    clex.TOKEN_IDENTIFIER: TokenKind.IDENTIFIER,
    clex.TOKEN_MODULE: TokenKind.MODULE,
    clex.TOKEN_HEX: TokenKind.HEX,
    clex.TOKEN_NUMBER: TokenKind.NUMBER,
    clex.TOKEN_COLON: TokenKind.COLON,
    clex.TOKEN_DOUBLECOLON: TokenKind.DOUBLECOLON,
    clex.TOKEN_LEFT_ANGLE: TokenKind.LEFT_ANGLE,
    clex.TOKEN_RIGHT_ANGLE: TokenKind.RIGHT_ANGLE,
    clex.TOKEN_ARROW: TokenKind.ARROW,
    clex.TOKEN_EMPTY_LINE: TokenKind.EMPTY_LINE,
    clex.TOKEN_KEYWORD: TokenKind.KEYWORD,
}


class ClexProvider:
    def tokenize(self, text: str) -> Iterator[Token]:
        lexer = clex.Lexer(text)
        while True:
            tok = lexer.scan_token()
            if tok.type == clex.TOKEN_EOF:
                return
            kind = _CLEX_MAP.get(tok.type, TokenKind.IDENTIFIER)
            yield Token(kind, tok.literal, tok.line)
