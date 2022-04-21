import re

from module_linker import link_modules
from class_resolver import ClassResolver
from statement import Statement, Class, LinkedModuleBlock
from lexer import Lexer
from parser import InheritanceParser, VTableParser


class Printer(Statement.Visitor):
    def __init__(self, target=None):
        self._established_classes: set[str] = set()
        self.target = target

    def print(self, statements: list[LinkedModuleBlock]) -> None:
        for statement in statements:
            self.execute(statement)

    def execute(self, statement: Statement) -> None:
        statement.accept(self)

    def execute_block(self, statements: list[Class]):
        for statement in statements:
            if self.target:
                if statement.identifier != self.target: continue
            self.execute(statement)

    def visit_linked_module_block(self, statement: LinkedModuleBlock) -> None:
        self.execute_block(statement.classes)

    def visit_class(self, cls: Class) -> None:
        if cls.identifier in self._established_classes: return

        for base in cls.bases:
            self.visit_class(base)

        print(self._format_class(cls))
        self._established_classes.add(cls.identifier)

    @staticmethod
    def _fix_identifier(identifier: str) -> str:
        identifier = re.sub(r"(class|union|struct|enum) ", "", identifier)
        identifier = re.sub(r"`anonymous namespace'", "_", identifier)
        identifier = re.sub(r"<|> ?", "__", identifier)
        return re.sub(r"[^A-Za-z0-9_:]+", "_", identifier)

    @staticmethod
    def _format_class(cls: Class) -> str:
        formatted = f"// Is determined size: {cls.is_determined_size()}\n"
        formatted += f"class {Printer._fix_identifier(cls.identifier)}"

        for index, base in enumerate(cls.bases):
            if index == 0:
                formatted += f" : {Printer._fix_identifier(base.identifier)}"
            else:
                formatted += f", {Printer._fix_identifier(base.identifier)}"
        formatted += " {\n"
        # formatted += "public:\n"
        if cls.vtable:
            for virtual_method in cls.vtable.vtable_entry_list:
                virtual_function = virtual_method.function

                if virtual_function.implementer and (virtual_function.implementer.identifier == cls.identifier or virtual_function.definer.identifier == cls.identifier):
                    formatted += f"\tvirtual void {Printer._fix_identifier(virtual_method.function.identifier)}(){{}}\n"

        if cls.get_size() == 0:
            padded_offset = f"{cls.offset:X}".zfill(4)
            formatted += f"char pad_{padded_offset};\n"

        if cls.is_determined_size() and (size := cls.get_size()) > 8:
            # highest base with a determined size
            selected_base: Class = cls
            while len(selected_base.bases) > 0:
                selected_base = selected_base.bases[-1]
                if selected_base.is_determined_size():
                    break

            if selected_base != cls:
                size -= selected_base.offset + selected_base.get_size()
                padded_offset = f"{cls.get_size() - size:X}".zfill(4)
            else:
                if cls.vtable:
                    size -= 8
                padded_offset = f"{cls.offset:X}".zfill(4)

            for offset in range(0, size, 8):
                formatted += f"\t__int64 field_{f'{int(padded_offset, base=16)+offset:X}'.zfill(4)};\n"
            # formatted += f"\tchar pad_{padded_offset}[{hex(size)}];\n"

        formatted += "};\n"

        return formatted


def main():
    # lexer = InheritanceLexer(r"inheritance.txt")
    with open(r"hierarchies\fallout4\inheritance.txt", "r") as read: inheritance_text = read.read()
    with open(r"hierarchies\fallout4\vtable.txt", "r") as read: vtable_text = read.read()

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

    printer = Printer()
    printer.print(linked_modules)


if __name__ == '__main__':
    main()
