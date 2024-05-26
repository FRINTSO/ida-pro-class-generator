import sys
from typing import Optional

import module_linker
from lexer import Lexer
from parser import InheritanceParser, VTableParser
from statement import Statement, Class, LinkedModuleBlock, VTable, VTableEntry


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

        # 34 is length of anon-namespace string
        # 11 is length of vftable string
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
            try:
                self.visit_class(cls)
            except IndexError:
                print(f"{cls.identifier} may be faulty", file=sys.stderr)
                cls.is_faulty = True

    def visit_class(self, cls: Class) -> None:
        bases: list[Class] = []
        for base in cls.bases:
            vtable = self._find_vtable_with_owner(base.identifier, cls.identifier)

            if retrieved_base := self._get_base(bases, base):
                if retrieved_base.vtable and vtable:
                    self._override_vtable_function_names(retrieved_base.vtable, vtable)
                retrieved_base.vtable = vtable
                continue

            if base.identifier in self._current_module_type_symbols:
                new_class: Class = self._current_module_type_symbols[base.identifier].clone()
                new_class.offset = base.offset
                new_class.vtable = vtable
                bases.append(new_class)
                self.visit_class(new_class)
            else:
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

        # self.__print_vftable_function_names(cls)
        # Update vtable methods
        self._set_vtable_function_names(cls)
        # self.__print_vftable_function_names(cls)

    @staticmethod
    def __print_vftable_function_names(cls: Class) -> None:
        if not cls.vtable: return

        print(f"CLASS: {cls.identifier}")
        for entry in cls.vtable.vtable_entry_list:
            print(entry.function)
        print()

    def _override_vtable_function_names(self, old_vtable: VTable, new_vtable: VTable) -> None:
        owner_cls: Optional[Class] = None
        if new_vtable.owner in self._current_module_type_symbols:
            owner_cls = self._current_module_type_symbols[new_vtable.owner]
        for entry in old_vtable.vtable_entry_list:
            try:
                cls_entry = new_vtable.vtable_entry_list[entry.index]
            except IndexError:
                raise IndexError(owner_cls.identifier)
            # cls_entry.function = entry.function  # bug: copies object pointer, instead of copying all fields of object
            # Potential Fix
            cls_entry.function.identifier = entry.function.identifier
            cls_entry.function.definer = entry.function.definer
            cls_entry.function.implementer = entry.function.implementer

            if cls_entry.address != entry.address and owner_cls:
                cls_entry.function.implementer = owner_cls

    @staticmethod
    def _calculate_sizeof_bases(bases: list[Class]) -> int:
        if len(bases):
            return bases[-1].offset + bases[-1].get_size()
        return 0

    def _set_vtable_function_names(self, cls: Class) -> None:  # class should (maybe) not take ownership of nullsub method, since it can be shared
        if not cls.vtable: return
        if not len(cls.bases):  # redoes vtable init, should check for repetition
            for entry in cls.vtable.vtable_entry_list:
                entry.function.identifier = f"{cls.identifier}::Function{entry.index}"
                entry.function.definer = cls
                entry.function.implementer = cls
        else:
            # find first base class with same offset that has a vtable
            valid_base: Class = cls.bases[0]
            while not valid_base.vtable:
                if not len(valid_base.bases):
                    if valid_base.vtable is None:
                        for entry in cls.vtable.vtable_entry_list:
                            entry.function.identifier = f"{cls.identifier}::Function{entry.index}"
                            entry.function.definer = cls
                            entry.function.implementer = cls
                    return
                valid_base = valid_base.bases[0]

            owner_cls = None
            if cls.vtable.owner and cls.vtable.owner in self._current_module_type_symbols:
                owner_cls = self._current_module_type_symbols[cls.vtable.owner]
            elif cls.vtable.owner:
                return

            for entry in valid_base.vtable.vtable_entry_list:
                try:
                    cls_entry = cls.vtable.vtable_entry_list[entry.index]
                except IndexError:
                    raise IndexError(cls.identifier, valid_base.identifier)
                cls_entry.function.definer = entry.function.definer
                cls_entry.function.identifier = entry.function.identifier
                if cls_entry.address == entry.address:
                    cls_entry.function.implementer = entry.function.implementer
                elif owner_cls:
                    cls_entry.function.implementer = owner_cls
                else:
                    cls_entry.function.implementer = cls

            for entry in cls.vtable.vtable_entry_list[valid_base.vtable.vtable_count:]:
                entry.function.identifier = f"{cls.identifier}::Function{entry.index}"
                entry.function.definer = cls
                if owner_cls:
                    entry.function.implementer = owner_cls
                else:
                    entry.function.implementer = cls

            for valid_base in cls.bases[1:]:
                if not valid_base.vtable: continue
                if valid_base.identifier not in self._current_module_vtable_symbols: continue
                established_vtable = self._current_module_vtable_symbols[valid_base.identifier]

                for entry in established_vtable.vtable_entry_list:  # if cls_entry == entry, then continue
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
    with open(r"C:\Users\willi\Desktop\Class_Dumper\hitman3\inheritance.txt", "r") as read: inheritance_text = read.read()
    with open(r"C:\Users\willi\Desktop\Class_Dumper\hitman3\vtable.txt", "r") as read: vtable_text = read.read()

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
