import os.path
from configparser import ConfigParser
import sys

from class_resolver import ClassResolver
from lexer import Lexer
from module_linker import link_modules
from module_printer import Printer
from parser import InheritanceParser, VTableParser


def create_config_parser() -> ConfigParser:
    config = ConfigParser()

    if not os.path.exists('config.cfg'):
        with open('config.cfg', 'w') as configfile:
            current_path = os.path.abspath('')
            configfile.write(f'[Paths]\n'
                             f'class_dumper_dir={current_path}')
    config.read('config.cfg')
    return config


def save_config(config: ConfigParser) -> None:
    with open('config.cfg', 'w') as configfile:
        config.write(configfile)


def get_config_path(config: ConfigParser) -> str:
    try:
        return config['Paths']['class_dumper_dir']
    except KeyError:
        return "No path to class_dumper has been set."


def set_config_path(config: ConfigParser, path: str) -> None:
    config['Paths']['class_dumper_dir'] = path


def check_file_presence(inheritance, vtable) -> None:
    should_raise = False
    exception = ""
    if not os.path.isfile(inheritance):
        should_raise = True
        exception += "inheritance.txt"
    if not os.path.isfile(vtable):
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
        directory = config['Paths']['class_dumper_dir']
    except KeyError:
        raise KeyError("Config file did not contain a path. Delete the config file and rerun the program.")

    game_dir = os.path.join(directory, identifier)
    if not os.path.isdir(game_dir): raise Exception("Game folder did not exist.")
    inheritance = os.path.join(game_dir, "inheritance.txt")
    vtable = os.path.join(game_dir, "vtable.txt")

    check_file_presence(inheritance, vtable)

    with open(inheritance, 'r') as read_inheritance: inheritance_text = read_inheritance.read()
    with open(vtable, 'r') as read_vtable: vtable_text = read_vtable.read()

    return inheritance_text, vtable_text


def scan_game_classes(config: ConfigParser, game: str, module: str = "", identifier: str = "") -> None:
    inheritance_text, vtable_text = load_game_class_files(config, game)
    lexer = Lexer()
    inheritance_tokens = lexer.tokenize(inheritance_text)
    vtable_tokens = lexer.tokenize(vtable_text)

    inheritance_parser = InheritanceParser(inheritance_tokens)
    vtable_parser = VTableParser(vtable_tokens)

    class_modules = inheritance_parser.parse()
    vtable_modules = vtable_parser.parse()

    linked_modules = link_modules(class_modules, vtable_modules)

    resolver = ClassResolver()
    resolver.resolve(linked_modules)

    printer = Printer(module, identifier) if identifier else Printer()
    printer.print(linked_modules)


def list_games(config: ConfigParser):
    class_dumper_dir = get_config_path(config)
    for game_dir in next(os.walk(class_dumper_dir, ))[1]:
        print(game_dir)


def main(*args):
    """
    Usage:
      py main.py <command> [options]

    Commands:
      get-path
      set-path [path]
      scan-game [game-name]
      scan-class [game-name] [class-name]
      list-games

    General Options:
      -h, --help
    """
    config = create_config_parser()

    match args:
        case ['get-path']:
            print(get_config_path(config))
        case ['set-path', _]:
            set_config_path(config, args[1])
            save_config(config)
        case ['scan-game', _]:
            scan_game_classes(config, game=args[1])
        case ['scan-module', _, _]:
            scan_game_classes(config, game=args[1], module=args[2])
        case ['scan-class', _, _]:
            scan_game_classes(config, game=args[1], identifier=args[2])
        case ['list-games']:
            list_games(config)
        case ['-h'] | ['--help'] | []:
            print(main.__doc__.replace('    ', ''), end="")
        case _:
            print("Unrecognized command")


if __name__ == '__main__':
    main(*sys.argv[1:])
    # main("scan-game", "Fallout4")
