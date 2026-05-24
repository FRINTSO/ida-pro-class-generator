import argparse
import os.path
import signal
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from ipcg.class_resolver import ClassResolver
from ipcg.lexer import LexerBackend, get_lexer_provider
from ipcg.method_printer import Printer as MethodPrinter
from ipcg.module_linker import link_modules
from ipcg.module_printer import Printer as ModulePrinter
from ipcg.parser import InheritanceParser, VTableParser

_ = signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def create_config_parser() -> ConfigParser:
    config = ConfigParser()

    if not os.path.exists("config.cfg"):
        with open("config.cfg", "w") as configfile:
            current_path = os.path.abspath("")
            _ = configfile.write(f"[Paths]\nclass_dumper_dir={current_path}")
    _ = config.read("config.cfg")
    return config


def save_config(config: ConfigParser) -> None:
    with open("config.cfg", "w") as configfile:
        config.write(configfile)


def get_config_path(config: ConfigParser) -> str:
    try:
        return config["Paths"]["class_dumper_dir"]
    except KeyError:
        return "No path to class_dumper has been set."


def set_config_path(config: ConfigParser, path: str) -> None:
    config["Paths"]["class_dumper_dir"] = path


def check_file_presence(inheritance: Path, vtable: Path) -> None:
    should_raise = False
    exception = ""
    if not inheritance.is_file():
        should_raise = True
        exception += "inheritance.txt"
    if not vtable.is_file():
        should_raise = True
        if len(exception) != 0:
            exception += " and vtable.txt"
        else:
            exception += "vtable.txt"

    if should_raise:
        exception += " does not exist in the specified folder"
        raise FileNotFoundError(exception)


def load_game_class_files(config: ConfigParser, identifier: str) -> tuple[str, str]:
    try:
        directory = Path(config["Paths"]["class_dumper_dir"])
    except KeyError:
        raise KeyError(
            "Config file did not contain a path. Delete the config file and rerun the program."
        )

    game_dir = directory / identifier
    if not game_dir.is_dir():
        raise Exception("Game folder did not exist.")
    inheritance = game_dir / "inheritance.txt"
    vtable = game_dir / "vtable.txt"

    check_file_presence(inheritance, vtable)

    with inheritance.open("r") as f:
        inheritance_text = f.read()
    with vtable.open("r") as f:
        vtable_text = f.read()

    return inheritance_text, vtable_text


def scan_game_classes(
    config: ConfigParser,
    *,
    game: str,
    module: str = "",
    identifier: str = "",
    lexer_backend: LexerBackend,
) -> None:
    inheritance_text, vtable_text = load_game_class_files(config, game)
    lexer = get_lexer_provider(lexer_backend)
    inheritance_tokens = lexer.tokenize(inheritance_text)

    # for nr, token in enumerate(inheritance_tokens):
    #     print(nr, token)
    # raise SystemExit(1)

    vtable_tokens = lexer.tokenize(vtable_text)

    inheritance_parser = InheritanceParser(inheritance_tokens)
    vtable_parser = VTableParser(vtable_tokens)

    class_modules = inheritance_parser.parse()
    vtable_modules = vtable_parser.parse()

    linked_modules = link_modules(class_modules, vtable_modules)

    resolver = ClassResolver()
    resolver.resolve(linked_modules)

    printer = ModulePrinter(module, identifier) if identifier else ModulePrinter()
    printer.print(linked_modules)


def scan_game_methods(
    config: ConfigParser,
    *,
    game: str,
    module: str,
    identifier: str = "",
    lexer_backend: LexerBackend,
) -> None:
    inheritance_text, vtable_text = load_game_class_files(config, game)
    lexer = get_lexer_provider(lexer_backend)
    inheritance_tokens = lexer.tokenize(inheritance_text)
    vtable_tokens = lexer.tokenize(vtable_text)

    inheritance_parser = InheritanceParser(inheritance_tokens)
    vtable_parser = VTableParser(vtable_tokens)

    class_modules = inheritance_parser.parse()
    vtable_modules = vtable_parser.parse()

    linked_modules = link_modules(class_modules, vtable_modules)

    resolver = ClassResolver()
    resolver.resolve(linked_modules)

    printer = MethodPrinter(module, identifier) if identifier else MethodPrinter(module)
    printer.print(linked_modules)


def list_games(config: ConfigParser):
    class_dumper_dir = get_config_path(config)
    for game_dir in next(
        os.walk(
            class_dumper_dir,
        )
    )[1]:
        print(game_dir)


def build_parser() -> argparse.ArgumentParser:
    lexer_parent = argparse.ArgumentParser(add_help=False)
    _ = lexer_parent.add_argument(
        "--lexer",
        choices=("pygments", "clex"),
        default="pygments",
        help="Lexer backend to use (default: pygments)",
    )

    parser = argparse.ArgumentParser(prog="ipcg", description="IDA Pro Class Generator")
    sub = parser.add_subparsers(dest="command", required=True)

    _ = sub.add_parser(
        "get-path",
        parents=[lexer_parent],
        help="Show the current class-dumper directory",
    )

    sp = sub.add_parser(
        "set-path", parents=[lexer_parent], help="Set the class-dumper directory"
    )
    _ = sp.add_argument("path")

    sp = sub.add_parser(
        "scan-game",
        parents=[lexer_parent],
        help="List all modules and classes for a game",
    )
    _ = sp.add_argument("game")

    sp = sub.add_parser(
        "scan-module",
        parents=[lexer_parent],
        help="List classes within a specific module",
    )
    _ = sp.add_argument("game")
    _ = sp.add_argument("module")

    sp = sub.add_parser(
        "scan-class",
        parents=[lexer_parent],
        help="List a specific class across all modules",
    )
    _ = sp.add_argument("game")
    _ = sp.add_argument("class_name", metavar="class")

    sp = sub.add_parser(
        "scan-methods",
        parents=[lexer_parent],
        help="List methods for all classes in a module",
    )
    _ = sp.add_argument("game")
    _ = sp.add_argument("module")

    sp = sub.add_parser(
        "scan-class-methods",
        parents=[lexer_parent],
        help="List methods for a specific class",
    )
    _ = sp.add_argument("game")
    _ = sp.add_argument("module")
    _ = sp.add_argument("class_name", metavar="class")

    _ = sub.add_parser(
        "list-games", parents=[lexer_parent], help="List all available games"
    )

    return parser


@dataclass(frozen=True, slots=True)
class GetPathArgs:
    pass


@dataclass(frozen=True, slots=True)
class SetPathArgs:
    path: str


@dataclass(frozen=True, slots=True)
class ScanGameArgs:
    game: str


@dataclass(frozen=True, slots=True)
class ScanModuleArgs:
    game: str
    module: str


@dataclass(frozen=True, slots=True)
class ScanClassArgs:
    game: str
    class_name: str


@dataclass(frozen=True, slots=True)
class ScanMethodsArgs:
    game: str
    module: str


@dataclass(frozen=True, slots=True)
class ScanClassMethodsArgs:
    game: str
    module: str
    class_name: str


@dataclass(frozen=True, slots=True)
class ListGamesArgs:
    pass


type Args = (
    GetPathArgs
    | SetPathArgs
    | ScanGameArgs
    | ScanModuleArgs
    | ScanClassArgs
    | ScanMethodsArgs
    | ScanClassMethodsArgs
    | ListGamesArgs
)


def parse_args() -> tuple[Args, LexerBackend]:
    parser = build_parser()
    ns = parser.parse_args()
    lexer: LexerBackend = ns.lexer  # pyright: ignore[reportAny]

    match ns.command:  # pyright: ignore[reportAny]
        case "get-path":
            return GetPathArgs(), lexer
        case "set-path":
            return SetPathArgs(ns.path), lexer  # pyright: ignore[reportAny]
        case "scan-game":
            return ScanGameArgs(ns.game), lexer  # pyright: ignore[reportAny]
        case "scan-module":
            return ScanModuleArgs(ns.game, ns.module), lexer  # pyright: ignore[reportAny]
        case "scan-class":
            return ScanClassArgs(ns.game, ns.class_name), lexer  # pyright: ignore[reportAny]
        case "scan-methods":
            return ScanMethodsArgs(ns.game, ns.module), lexer  # pyright: ignore[reportAny]
        case "scan-class-methods":
            return ScanClassMethodsArgs(ns.game, ns.module, ns.class_name), lexer  # pyright: ignore[reportAny]
        case "list-games":
            return ListGamesArgs(), lexer
        case _:  # pyright: ignore[reportAny]
            raise SystemExit(f"Unknown command: {ns.command}")  # pyright: ignore[reportAny]


def main():
    args, lexer_backend = parse_args()
    config = create_config_parser()

    match args:
        case GetPathArgs():
            print(get_config_path(config))
        case SetPathArgs(path):
            set_config_path(config, path)
            save_config(config)
        case ScanGameArgs(game):
            scan_game_classes(config, game=game, lexer_backend=lexer_backend)
        case ScanModuleArgs(game, module):
            scan_game_classes(
                config, game=game, module=module, lexer_backend=lexer_backend
            )
        case ScanClassArgs(game, class_name):
            scan_game_classes(
                config, game=game, identifier=class_name, lexer_backend=lexer_backend
            )
        case ScanMethodsArgs(game, module):
            scan_game_methods(
                config, game=game, module=module, lexer_backend=lexer_backend
            )
        case ScanClassMethodsArgs(game, module, class_name):
            scan_game_methods(
                config,
                game=game,
                module=module,
                identifier=class_name,
                lexer_backend=lexer_backend,
            )
        case ListGamesArgs():
            list_games(config)
