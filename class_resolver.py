import cProfile
from typing import Optional

import module_linker
from lexer import Lexer
from parser import InheritanceParser, VTableParser
from statement import Statement, Class, LinkedModuleBlock, VTable


class ClassResolver(Statement.Visitor):
    def __init__(self) -> None:
        self._current_module: Optional[LinkedModuleBlock] = None
        self._current_module_type_symbols: dict[str, Class] = {}
        self._current_module_vtable_symbols: dict[str, VTable] = {}
        self._current_module_vtable_owned_symbols: dict[tuple[str, str], VTable] = {}

    def resolve(self, linked_modules: list[LinkedModuleBlock]) -> None:
        linked_module: LinkedModuleBlock
        for linked_module in linked_modules:
            self.execute(linked_module)

    def execute(self, statement: Statement) -> None:
        statement.accept(self)

    def visit_linked_module_block(self, linked_module: LinkedModuleBlock) -> None:
        self._current_module = linked_module
        self._current_module_type_symbols = {class_statement.identifier: class_statement for class_statement in
                                             linked_module.classes}

        self._current_module_vtable_symbols = {vtable.identifier[:-34]
                                               if vtable.identifier.endswith("::`anonymous namespace'::`vftable'")
                                               else vtable.identifier[:-11]: vtable
                                               for vtable in linked_module.vtables
                                               if not vtable.owner}

        self._current_module_vtable_owned_symbols = {(vtable.owner,
                                                      vtable.identifier[:-34]
                                                      if vtable.identifier.endswith(
                                                          "::`anonymous namespace'::`vftable'")
                                                      else vtable.identifier[:-11]): vtable
                                                     for vtable in linked_module.vtables
                                                     if vtable.owner}

        cls: Class
        for cls in linked_module.classes:
            self.execute(cls)

    def visit_class(self, cls: Class) -> None:
        bases: list[Class] = []
        for base in cls.bases:
            vtable = self._find_vtable_with_owner(base.identifier, cls.identifier)

            if retrieved_base := self._get_base(bases, base):
                retrieved_base.vtable = vtable
                continue

            if base.identifier in self._current_module_type_symbols:
                new_class: Class = self._current_module_type_symbols[base.identifier].clone()
                new_class.offset = base.offset
                new_class.vtable = vtable
                bases.append(new_class)
                self.visit_class(new_class)
            else:
                # fix base's bases' offset not being zero at the first base
                base.vtable = vtable
                bases.append(base)
                self.visit_class(base)

        if not cls.vtable:
            cls.vtable = self._find_vtable_without_owner(cls.identifier)

        self._adjust_sizeof_bases(bases)

        sizeof_bases: int = self._calculate_sizeof_bases(bases)

        if not sizeof_bases and cls.vtable:
            sizeof_bases = 8

        cls.bases = bases
        cls.set_size(sizeof_bases, False)

        # Update vtable methods
        self._set_vtable_function_names(cls)

    @staticmethod
    def _calculate_sizeof_bases(bases: list[Class]) -> int:
        if len(bases):
            return bases[-1].offset + bases[-1].get_size()
        return 0

    def _set_vtable_function_names(self, cls: Class) -> None:
        if not cls.vtable: return
        if not len(cls.bases):
            for entry in cls.vtable.vtable_entry_list:
                entry.function.identifier = f"{cls.identifier}::Function{entry.index}"
                entry.function.definer = cls
                entry.function.implementer = cls
        else:
            # find first base class with same offset that has a vtable
            valid_base: Class = cls.bases[0]
            # sanity check
            # if valid_base.offset != 0: return
            while not valid_base.vtable:
                if not len(valid_base.bases): return
                valid_base = valid_base.bases[0]

            for entry in valid_base.vtable.vtable_entry_list:
                cls_entry = cls.vtable.vtable_entry_list[entry.index]
                cls_entry.function.definer = entry.function.definer
                cls_entry.function.identifier = entry.function.identifier
                if cls_entry.address == entry.address:
                    cls_entry.function.implementer = entry.function.implementer
                else:
                    cls_entry.function.implementer = cls

            for entry in cls.vtable.vtable_entry_list[valid_base.vtable.vtable_count:]:
                entry.function.identifier = f"{cls.identifier}::Function{entry.index}"
                entry.function.definer = cls
                entry.function.implementer = cls

            for valid_base in cls.bases[1:]:
                if not valid_base.vtable: continue
                if valid_base.identifier not in self._current_module_vtable_symbols: continue
                established_vtable = self._current_module_vtable_symbols[valid_base.identifier]

                for entry in established_vtable.vtable_entry_list:
                    cls_entry = valid_base.vtable.vtable_entry_list[entry.index]
                    if cls_entry.address == entry.address:
                        cls_entry.function.implementer = entry.function.implementer
                    else:
                        cls_entry.function.implementer = cls

    @staticmethod
    def _adjust_sizeof_bases(bases: list[Class]) -> None:
        for index, base in enumerate(bases[1:], start=1):
            bases[index - 1].set_size(base.offset - bases[index - 1].offset, True)

    def _find_vtable_without_owner(self, identifier: str) -> Optional[VTable]:
        if identifier not in self._current_module_vtable_symbols: return None
        return self._current_module_vtable_symbols[identifier]

    def _find_vtable_with_owner(self, identifier: str, owner: str) -> Optional[VTable]:
        if (owner, identifier) not in self._current_module_vtable_owned_symbols: return None
        return self._current_module_vtable_owned_symbols[(owner, identifier)]

    @staticmethod
    def _get_base(classes: list[Class], base: Class) -> Optional[Class]:
        cls: Class
        for cls in classes:
            if cls.identifier == base.identifier:
                return cls
            else:
                retrieved_base: Optional[Class] = ClassResolver._get_base(cls.bases, base)
                if retrieved_base:
                    return retrieved_base
        return None


def main() -> None:
    with open("hierarchies/hitman3/inheritance.txt", "r") as read: inheritance_text = read.read()
    with open("hierarchies/hitman3/vtable.txt", "r") as read: vtable_text = read.read()

    lexer = Lexer()
    inheritance_tokens = lexer.tokenize(inheritance_text)
    vtable_tokens = lexer.tokenize(vtable_text)

    inheritance_parser = InheritanceParser(inheritance_tokens)
    vtable_parser = VTableParser(vtable_tokens)

    class_modules = inheritance_parser.parse()
    vtable_modules = vtable_parser.parse()

    linked_modules = module_linker.link_modules(class_modules, vtable_modules)

    resolver = ClassResolver()
    resolver.resolve(linked_modules)


if __name__ == '__main__':
    main()
