from typing import List, Dict, TextIO, Tuple

from os import listdir
import re


class VTable:
    def __init__(self, rva_func_addresses: list[int]):
        self.functions = rva_func_addresses


class TypeInfo:
    def __init__(self, vtable: VTable):
        self.vfptr: VTable = vtable
        self.m_data: List[int] = ...
        self.m_name: List[str] = ...


class PMD:
    def __init__(self, offset: int):
        self.mdisp: int = offset
        self.pdisp: int = 0
        self.vdisp: int = 0

    def __str__(self):
        return f"<{self.mdisp}, {self.pdisp}, {self.vdisp}>"


class RTTIBaseClassDescriptor:
    def __init__(self, type_descriptor: str, contained_bases: int, where: PMD):
        self.type_descriptor: str = type_descriptor
        self.contained_bases: int = contained_bases
        self.where: PMD = where
        self.attributes: int = 0

    def __str__(self):
        return f"RTTIBaseClassDescriptor <{self.type_descriptor}, {self.contained_bases}, {self.where}, {self.attributes}>"

    __repr__ = __str__


class RTTIClassHierarchyDescriptor:
    def __init__(self, attributes: int, base_classes: list):
        self.attributes: int = attributes
        self.base_classes: List[RTTIBaseClassDescriptor] = base_classes

    def __str__(self):
        return f"RTTIClassHierarchyDescriptor <{self.attributes}, {len(self.base_classes)}, {self.base_classes}>"

    __repr__ = __str__


class RTTICompleteObjectLocator:
    def __init__(self, offset: int, type_descriptor: str, base_types: List[str]):
        self.offset: int = offset  # vtable offset in the complete class
        self.type_descriptor: str = type_descriptor
        self.class_descriptor: RTTIClassHierarchyDescriptor = ...
        self.size: int = ...
        self.representation: List[str] = base_types

    def __str__(self):
        return f"RTTICompleteObjectLocator <{self.offset}, {self.type_descriptor}, {self.class_descriptor}>"

    __repr__ = __str__


NULL_OBJECT = object()


class TypeHierarchy:
    def __init__(self, folder_path: str):
        self.modules: Dict[str, List[RTTICompleteObjectLocator]] = {}
        self._types: Dict[str, Dict[str, RTTICompleteObjectLocator]] = {}
        self._scan_symbols(folder_path)

    @staticmethod
    def _contains_rtti_files(folder_path: str) -> bool:
        file_paths: List[str] = listdir(folder_path)

        contains_inheritance_file: bool = False
        contains_vtable_file: bool = False

        file_path: str
        for file_path in file_paths:
            if file_path.endswith("inheritance.txt"):
                contains_inheritance_file = True
            elif file_path.endswith("vtable.txt"):
                contains_vtable_file = True

        return contains_inheritance_file and contains_vtable_file

    @staticmethod
    def _consume(stream: TextIO, expected: str) -> bool:
        actual: str = stream.readline(len(expected))
        return TypeHierarchy._match(actual, expected)

    @staticmethod
    def _match(actual: str, expected: str) -> bool:
        return actual == expected

    @staticmethod
    def _seek_module_begin(stream: TextIO) -> str:
        line: str = stream.readline()
        while line:
            if line[0] == '<':
                line = line.rstrip("\n")
                if line[-1] != ">": raise Exception("Angle bracket was not closed.")
                tokens: List[str] = line.split()

                if len(tokens) == 1:
                    return line[1:-1]
                elif len(tokens) == 3 and tokens[1] == "end":
                    raise Exception("Module end declaration was encountered but not expected.")
                else:
                    raise Exception("Incorrect module declaration.")

            line = stream.readline()

        return ""

    @staticmethod
    def _read_modules(stream: TextIO) -> Dict[str, str]:
        modules: Dict[str, str] = {}
        current_module = TypeHierarchy._seek_module_begin(stream)
        while current_module:
            module_types: str = ""
            line: str = stream.readline()
            while line and line[0] != "<":
                module_types += line
                line = stream.readline()
            else:
                if not TypeHierarchy._match(line, f"< end {current_module}>\n"): raise Exception(
                    "Expected module end declaration.")
                modules[current_module] = module_types

            current_module = TypeHierarchy._seek_module_begin(stream)

        return modules

    @staticmethod
    def _clean_identifier(identifier: str) -> str:
        type_name_match = re.match(r"(?:[^:\s]|::)+", identifier)
        # if type_name_match.group().find(" ") != -1: return ""
        type_name = type_name_match.group()
        type_name = type_name.replace(" ", "_")
        type_name = type_name.replace(",", "_")
        type_name = type_name.replace("::", "__")
        type_name = type_name.replace(">", "_")
        type_name = type_name.replace("<", "_")
        type_name = type_name.replace("`", "_")
        type_name = type_name.replace("'", "_")
        return type_name

    def create_type(self, module_type: str) -> RTTICompleteObjectLocator | None:
        base_type = module_type.split("\n")
        identifier: str = self._clean_identifier(base_type[0])
        if not identifier: return None
        return RTTICompleteObjectLocator(0, identifier, base_type[1:])

    @staticmethod
    def _resolve_base_classes(module_types: Dict[str, RTTICompleteObjectLocator]):
        for object_locator in module_types.values():
            base_classes: List[RTTIBaseClassDescriptor] = [
                RTTIBaseClassDescriptor(object_locator.type_descriptor, len(object_locator.representation), PMD(0))]

            for index, name_base in enumerate(object_locator.representation):
                offset, name = re.split(r"\t+", name_base)
                if not offset: continue
                name = TypeHierarchy._clean_identifier(name)
                offset = int(offset, 16)
                where = PMD(offset)
                bases: int = 0
                try:
                    bases = len(module_types[name].representation)
                except KeyError as e:
                    pass
                base_classes.append(RTTIBaseClassDescriptor(name, bases, where))

            class_description = RTTIClassHierarchyDescriptor(0, base_classes)
            object_locator.class_descriptor = class_description

    def _scan_symbols(self, folder_path: str):
        if not self._contains_rtti_files(folder_path): raise Exception("Folder did not contain inheritance.txt or vtable.txt.")

        modules: Dict[str, str] = {}

        with open(fr"{folder_path}\inheritance.txt", "r") as read_inheritance:
            modules = TypeHierarchy._read_modules(read_inheritance)

        for module, module_type_declarations in modules.items():
            self._types[module] = {}
            module_types: Dict[str, RTTICompleteObjectLocator] = self._types[module]

            lines: List[str] = module_type_declarations.split("\n\n")
            for line in lines:
                if line:
                    object_locator: RTTICompleteObjectLocator = self.create_type(line)
                    if object_locator:
                        module_types[object_locator.type_descriptor] = object_locator

            self._resolve_base_classes(module_types)

    def get_symbol(self, module: str, type_name: str):
        return self._types[module][type_name]


def main():
    # types = TypeHierarchy(r"C:\Users\william.malmgrenhan\Desktop\Class_Dumper\hitman3")
    types = TypeHierarchy(r"hierarchies")

    print(types.get_symbol("hitman3.exe", "Base"))


if __name__ == '__main__':
    main()
