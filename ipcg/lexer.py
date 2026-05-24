from collections.abc import Iterator
from typing import Literal, Protocol, assert_never

from .tokens import Token

type LexerBackend = Literal["pygments", "clex"]


class LexerProvider(Protocol):
    def tokenize(self, text: str) -> Iterator[Token]: ...


def get_lexer_provider(backend: LexerBackend = "pygments") -> LexerProvider:
    match backend:
        case "pygments":
            from ipcg.providers.pygments_provider import PygmentsProvider

            return PygmentsProvider()
        case "clex":
            from ipcg.providers.clex_provider import ClexProvider

            return ClexProvider()

    assert_never(backend)
