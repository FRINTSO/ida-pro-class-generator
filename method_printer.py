import sys
from typing import Optional

from class_resolver import ClassResolver
from lexer import Lexer
from module_linker import link_modules
from parser import InheritanceParser, VTableParser
from statement import Statement, Class, LinkedModuleBlock, VTable, VTableEntry


class Printer(Statement.Visitor):
    def __init__(self, module: Optional[str] = None, identifier: Optional[str] = None):
        self.module = module
        self.identifier = identifier
        self.functions: dict[str, list[VTableEntry]] = {}

    def print(self, statements: list[LinkedModuleBlock]) -> None:
        for statement in statements:
            if self.module:
                if statement.module != self.module: continue
            self.execute(statement)

        for fn_name, entry_list in self.functions.items():
            func_def: Optional[VTableEntry] = None
            try:
                func_def = [entry for entry in entry_list if entry.function.implementer == entry.function.definer][0]
                print(f"{fn_name} -> 0x{func_def.relative_address:X}:")
            except IndexError:
                print(f"{fn_name} has no default implementation", file=sys.stderr)
                print(f"{fn_name}:")
                continue

            for entry in entry_list:
                if func_def and entry == func_def: break
                print(f"\t{entry.function.implementer.identifier}\t0x{entry.relative_address:X}")
            print()

    def execute(self, statement: Statement) -> None:
        statement.accept(self)

    def execute_block(self, statements: list[Class]):
        for statement in statements:
            self.execute(statement)

    def visit_linked_module_block(self, statement: LinkedModuleBlock) -> None:
        self.execute_block(statement.classes)

    def visit_class(self, cls: Class) -> None:
        if cls.vtable:
            self.visit_vtable(cls.vtable)

    def visit_vtable(self, vtable: VTable) -> None:
        for entry in vtable.vtable_entry_list:
            self.visit_vtable_entry(entry)

    def visit_vtable_entry(self, entry: VTableEntry) -> None:
        if self.identifier:
            if entry.function.definer.identifier != self.identifier: return

        if entry.function.identifier not in self.functions:
            self.functions[entry.function.identifier] = [entry]
        elif not self._entry_in_list(self.functions[entry.function.identifier], entry):  # contemplating this, whether to skip, or show all classes implementing  it
            self.functions[entry.function.identifier].append(entry)

    @staticmethod
    def _entry_in_list(entries: list[VTableEntry], entry: VTableEntry) -> bool:
        for _entry in entries:
            if entry.address == _entry.address:
                print(f"{entry}\t\t\t{_entry}", file=sys.stderr)
                return True
        return False


def main():
    with open(r"C:\Users\willi\Desktop\Class_Dumper\hitman3\inheritance.txt", "r") as read: inheritance_text = read.read()
    with open(r"C:\Users\willi\Desktop\Class_Dumper\hitman3\vtable.txt", "r") as read: vtable_text = read.read()

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

    printer = Printer(module="hitman3.exe")
    printer.print(linked_modules)


if __name__ == '__main__':
    main()
