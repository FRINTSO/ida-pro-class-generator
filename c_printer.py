import re
from typing import Optional

from module_linker import link_modules
from class_resolver import ClassResolver
from statement import Statement, Class, LinkedModuleBlock
from lexer import Lexer
from parser import InheritanceParser, VTableParser
from module_printer import Printer

class CPrinter(Printer):
    def _format_vftable(self, cls: Class) -> str:
        formatted = f"struct {self._fix_identifier(cls.identifier)}_vftable_{f'{cls.vtable.relative_address:X}'[2:]}\n{{\n"
        for virtual_method in cls.vtable.vtable_entry_list:
            formatted += f"\tvoid* {self._fix_identifier(virtual_method.function.identifier)}_{f'{virtual_method.address:X}'[2:]};\n"
        formatted += "};\n"
        return formatted

    def _format_class(self, cls: Class) -> str:
        if cls.vtable:
            formatted = self._format_vftable(cls)
        else:
            formatted = ""
        formatted += f"// Is determined size: {cls.is_determined_size()}\n"
        formatted += f"// Size: {cls.get_size():X}\n"
        formatted += f"struct {self._fix_identifier(cls.identifier)}\n{{\n"

        if not cls.bases and cls.vtable:
                formatted += f"\t{self._fix_identifier(cls.identifier)}_vftable_{f'{cls.vtable.relative_address:X}'[2:]}* vftptr;\n"
        else:
            for base in cls.bases:
                formatted += f"\t{self._fix_identifier(base.identifier)} {self._fix_identifier(base.identifier)};\n"

        if cls.get_size() == 0 and not cls.bases:
            padded_offset = f"{cls.offset:X}"
            formatted += f"char pad_{padded_offset};\n"

        elif cls.is_determined_size() and (size := cls.get_size()) > 8:
            # highest base with a determined size
            selected_base: Class = cls
            while len(selected_base.bases) > 0:
                selected_base = selected_base.bases[-1]
                if selected_base.is_determined_size():
                    break

            # selected_base: Class = cls.bases[-1] if len(cls.bases) > 0 else cls

            # if not selected_base.is_determined_size() and selected_base.offset == 0:
            #     selected_base = cls

            if selected_base != cls:
                selected_base_size = selected_base.get_size() if selected_base.get_size() != 0 else 8
                size -= selected_base.offset + selected_base_size
                if not selected_base.vtable and selected_base.offset == 0 and cls.vtable:
                    size -= 8
                padded_offset = f"{cls.get_size() - size:X}"
            else:
                if cls.vtable:
                    size -= 8
                padded_offset = f"{cls.offset:X}"

            for offset in range(0, size, 8):
                formatted += f"\t__int64 field_{f'{int(padded_offset, base=16)+offset:X}'};\n"

        formatted += "};\n"
        return formatted


def main():
    # lexer = InheritanceLexer(r"inheritance.txt")
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

    printer = CPrinter(module="hitman3.exe")
    printer.print(linked_modules)


if __name__ == '__main__':
    main()
