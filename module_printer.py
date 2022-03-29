from module_linker import link_modules
from class_resolver import ClassResolver
from statement import Statement, Class, LinkedModuleBlock
from lexer import Lexer
from parser import InheritanceParser, VTableParser


class Printer(Statement.Visitor):
    def print(self, statements: list[LinkedModuleBlock]) -> None:
        for statement in statements:
            self.execute(statement)

    def execute(self, statement: Statement) -> None:
        statement.accept(self)

    def execute_block(self, statements: list[Class]):
        for statement in statements:
            self.execute(statement)

    def visit_linked_module_block(self, statement: LinkedModuleBlock) -> None:
        self.execute_block(statement.classes)

    def visit_class(self, statement: Class) -> None:
        if statement.identifier != "ZHitman5": return

        print(f"class {statement.identifier}", end="")

        base: Class
        for index, base in enumerate(statement.bases):
            if index == 0: print(f" : {base.identifier}", end="")
            else: print(f", {base.identifier}", end="")
        print(" {")
        if statement.vtable:
            for virtual_method in statement.vtable.vtable_entry_list:
                print(f"\t{virtual_method.function}")
        print("}")


def main():
    # lexer = InheritanceLexer(r"inheritance.txt")
    with open("hierarchies/hitman3/inheritance.txt", "r") as read: inheritance_text = read.read()
    with open("hierarchies/hitman3/vtable.txt", "r") as read: vtable_text = read.read()

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
