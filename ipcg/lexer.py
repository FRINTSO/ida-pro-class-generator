from __future__ import annotations
from typing import Iterator, TYPE_CHECKING

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Punctuation, Token, Number, Name, Whitespace, Keyword

if TYPE_CHECKING:
    from pygments.token import _TokenType
    TokenType = tuple[_TokenType, str, int]


# https://www.cs.auckland.ac.nz/references/unix/digital/AQTLTBTE/DOCU_006.HTM


class Lexer(RegexLexer):
    name = "Lexer"

    tokens = {
        'root': [
            (r'(<)([\w-]+(?:\.[\w-]+)+)(>)', bygroups(Punctuation, Name.Module, Punctuation)),
            (r'(<) (end) ([\w-]+(?:\.[\w-]+)+)(>)',
             bygroups(Punctuation, Name.Identifier, Name.Module, Punctuation)),
            (r'^([M ])([V ])([A ]) (0x[a-zA-Z0-9]+)\t\+([a-zA-Z0-9]+)\t(.+) (->) (const) (.+)',
             bygroups(Token.MFlag, Token.VFlag, Token.AFlag, Number.Hex, Number.Hex, Name.Identifier, Punctuation,
                      Keyword, Name.Identifier)),
            (r'^([M ])([V ])([A ]) (0x[a-zA-Z0-9]+)\t\+([a-zA-Z0-9]+)\t(const) (.+)',
             bygroups(Token.MFlag, Token.VFlag, Token.AFlag, Number.Hex, Number.Hex, Keyword, Name.Identifier)),
            (r'^\t(Virtual Functions) (\()(\d+)(\))(:)', bygroups(Name, Punctuation, Number, Punctuation, Punctuation)),
            (r'^\t(\d+)\t(0x[a-zA-Z0-9]+)\t\+([a-zA-Z0-9]+)\t\t(\w+_[a-zA-Z0-9]+)',
             bygroups(Number, Number.Hex, Number.Hex, Name.Identifier)),
            (r"^(.+) \(No Base Classes\)", bygroups(Name.Identifier)),
            (r"^(.+)(:)(\n)", bygroups(Name.Identifier, Punctuation, Whitespace)),
            (r"^(0x[0-9a-fA-F]+)\t+(.+)", bygroups(Number.Hex, Name.Identifier)),
            (r"^\t(.+)", bygroups(Name.NoHexIdentifier)),
            (r'\n{2,}', Whitespace.EmptyLine),
            (r'\s', Whitespace)
        ]
    }

    def tokenize(self, text: str) -> Iterator[TokenType]:
        token_stream: Iterator[_TokenType] = self.get_tokens(text)
        line_nr = 1
        last_offset: str = ""
        literal: str
        for token, literal in token_stream:
            line_nr += literal.count('\n')
            if token is Whitespace:
                continue
            elif token is Number.Hex:
                last_offset = literal
            elif token is Name.NoHexIdentifier:
                yield Number.Hex, last_offset, line_nr
                token = Name.Identifier

            yield token, literal, line_nr


def main():
    with open(r"hierarchies\hitman3\inheritance.txt", "r") as read:
        text = read.read()

    lexer = Lexer()

    tokens = lexer.tokenize(text)
    for token in tokens:
        if token[0] in Name:
            print(token)


if __name__ == '__main__':
    main()
