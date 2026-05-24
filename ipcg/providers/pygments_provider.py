from __future__ import annotations

from typing import TYPE_CHECKING, final

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Keyword, Name, Number, Punctuation, Token, Whitespace

if TYPE_CHECKING:
    from pygments.token import _TokenType

    TokenType = tuple[_TokenType, str, int]

from collections.abc import Iterator

from ..tokens import Token as TokenStruct
from ..tokens import TokenKind

_PYGMENTS_MAP: dict[object, TokenKind] = {
    Name.Identifier: TokenKind.IDENTIFIER,
    Name.Module: TokenKind.MODULE,
    Number.Hex: TokenKind.HEX,
    Number: TokenKind.NUMBER,
    Whitespace.EmptyLine: TokenKind.EMPTY_LINE,
    Token.MFlag: TokenKind.M_FLAG,
    Token.VFlag: TokenKind.V_FLAG,
    Token.AFlag: TokenKind.A_FLAG,
    Keyword: TokenKind.KEYWORD,
}

_LITERAL_MAP: dict[str, TokenKind] = {
    "<": TokenKind.LEFT_ANGLE,
    ">": TokenKind.RIGHT_ANGLE,
    ":": TokenKind.COLON,
    "::": TokenKind.DOUBLECOLON,
    "->": TokenKind.ARROW,
    "(": TokenKind.LEFT_PAREN,
    ")": TokenKind.RIGHT_PAREN,
}


class PygmentsProvider:
    def tokenize(self, text: str) -> Iterator[TokenStruct]:
        lexer = PygmentsLexer()
        for pygments_type, literal, line in lexer.tokenize(text):
            kind = _PYGMENTS_MAP.get(pygments_type)
            if kind is None and pygments_type is Punctuation:
                kind = _LITERAL_MAP.get(literal)
            if kind is None:
                kind = TokenKind.IDENTIFIER  # fallback
            yield TokenStruct(kind, literal, line)


# --- LEXER ---


# https://www.cs.auckland.ac.nz/references/unix/digital/AQTLTBTE/DOCU_006.HTM


@final
class PygmentsLexer(RegexLexer):
    name = "Lexer"

    tokens = {
        "root": [
            (
                r"(<)([\w-]+(?:\.[\w-]+)+)(>)",
                bygroups(Punctuation, Name.Module, Punctuation),
            ),
            (
                r"(<) (end) ([\w-]+(?:\.[\w-]+)+)(>)",
                bygroups(Punctuation, Name.Identifier, Name.Module, Punctuation),
            ),
            (
                r"^([M ])([V ])([A ]) (0x[a-zA-Z0-9]+)\t\+([a-zA-Z0-9]+)\t(.+) (->) (const) (.+)",
                bygroups(
                    Token.MFlag,
                    Token.VFlag,
                    Token.AFlag,
                    Number.Hex,
                    Number.Hex,
                    Name.Identifier,
                    Punctuation,
                    Keyword,
                    Name.Identifier,
                ),
            ),
            (
                r"^([M ])([V ])([A ]) (0x[a-zA-Z0-9]+)\t\+([a-zA-Z0-9]+)\t(const) (.+)",
                bygroups(
                    Token.MFlag,
                    Token.VFlag,
                    Token.AFlag,
                    Number.Hex,
                    Number.Hex,
                    Keyword,
                    Name.Identifier,
                ),
            ),
            (
                r"^\t(Virtual Functions) (\()(\d+)(\))(:)",
                bygroups(Name, Punctuation, Number, Punctuation, Punctuation),
            ),
            (
                r"^\t(\d+)\t(0x[a-zA-Z0-9]+)\t\+([a-zA-Z0-9]+)\t\t(\w+_[a-zA-Z0-9]+)",
                bygroups(Number, Number.Hex, Number.Hex, Name.Identifier),
            ),
            (r"^(.+) \(No Base Classes\)", bygroups(Name.Identifier)),
            (r"^(.+)(:)(\n)", bygroups(Name.Identifier, Punctuation, Whitespace)),
            (r"^(0x[0-9a-fA-F]+)\t+(.+)", bygroups(Number.Hex, Name.Identifier)),
            (r"^\t(.+)", bygroups(Name.NoHexIdentifier)),
            (r"\n{2,}", Whitespace.EmptyLine),
            (r"\s", Whitespace),
        ]
    }

    def tokenize(self, text: str) -> Iterator[TokenType]:
        token_stream: Iterator[_TokenType] = self.get_tokens(text)
        line_nr = 1
        last_offset: str = ""
        literal: str
        for token, literal in token_stream:
            line_nr += literal.count("\n")
            if token is Whitespace:
                continue
            elif token is Number.Hex:
                last_offset = literal
            elif token is Name.NoHexIdentifier:
                yield Number.Hex, last_offset, line_nr
                token = Name.Identifier

            yield token, literal, line_nr
