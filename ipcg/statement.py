from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import final, override


class Statement:
    class Visitor:
        def visit_module_block(self, statement: ModuleBlock):
            pass

        def visit_class(self, statement: Class):
            pass

        def visit_vtable(self, statement: VTable):
            pass

        def visit_vtable_entry(self, statement: VTableEntry):
            pass

        def visit_linked_module_block(self, statement: LinkedModuleBlock):
            pass

    def accept(self, visitor: Visitor):
        pass


@final
@dataclass
class ModuleBlock(Statement):
    module: str
    statements: list[Statement]

    @override
    def accept(self, visitor: Statement.Visitor) -> None:
        return visitor.visit_module_block(self)

    @override
    def __str__(self) -> str:
        return f"ModuleBlock({self.module}, {self.statements})"

    __repr__ = __str__


@final
class Class(Statement):
    _class_sizes: dict[str, Size] = {}

    identifier: str
    bases: list[Class]
    offset: int
    _size: Size
    vtable: VTable | None
    is_faulty: bool

    def __init__(
        self,
        identifier: str,
        bases: list[Class],
        offset: int,
        size: int,
        vtable: VTable | None = None,
    ) -> None:
        self.identifier = identifier
        self.bases = bases
        self.offset = offset
        if identifier not in Class._class_sizes:
            Class._class_sizes[identifier] = Size(size)
        self._size = self._class_sizes[identifier]
        self.vtable = vtable
        self.is_faulty = False

    def set_size(self, size: int, is_determined: bool) -> None:
        if self._size.is_determined:
            return
        self._size = Size(size, is_determined)

    def get_size(self) -> int:
        return self._size.size

    def is_determined_size(self) -> bool:
        return self._size.is_determined

    def clone(self) -> Class:
        bases: list[Class] = [base.clone() for base in self.bases]
        new_class = Class(self.identifier, bases, self.offset, self._size.size)
        new_class.vtable = self.vtable
        return new_class

    @override
    def accept(self, visitor: Statement.Visitor) -> None:
        visitor.visit_class(self)

    @override
    def __str__(self) -> str:
        return f"Class({self.identifier}, {self.bases}, {self.offset}, {self._size.size}, {self.vtable})"

    __repr__ = __str__


@final
@dataclass
class Size:
    size: int
    is_determined: bool = False

    @override
    def __str__(self) -> str:
        return hex(self.size)

    __repr__ = __str__


@final
@dataclass
class VTable(Statement):
    m_flag: bool
    v_flag: bool
    a_flag: bool
    address: int
    relative_address: int
    owner: str
    identifier: str
    vtable_count: int
    vtable_entry_list: list[VTableEntry]

    @override
    def accept(self, visitor: Statement.Visitor) -> None:
        visitor.visit_vtable(self)

    @override
    def __str__(self) -> str:
        return f"VTable({self.m_flag}, {self.v_flag}, {self.a_flag}, {hex(self.address)}, {hex(self.relative_address)}, {self.owner}, {self.identifier}, {self.vtable_count}, {self.vtable_entry_list}) "

    __repr__ = __str__


@final
@dataclass
class VTableEntry(Statement):
    index: int
    address: int
    relative_address: int
    function_identifier: InitVar[str]
    function: Function = field(init=False)

    def __post_init__(self, function_identifier: str) -> None:
        self.function = Function(function_identifier, None, None)

    @override
    def accept(self, visitor: Statement.Visitor) -> None:
        visitor.visit_vtable_entry(self)

    @override
    def __str__(self) -> str:
        return f"VTableEntry({self.index}, {hex(self.address)}, {hex(self.relative_address)}, {self.function})"

    __repr__ = __str__


@final
@dataclass
class LinkedModuleBlock(Statement):
    module: str
    classes: list[Class]
    vtables: list[VTable]

    @override
    def accept(self, visitor: Statement.Visitor) -> None:
        visitor.visit_linked_module_block(self)

    @override
    def __str__(self) -> str:
        return f"LinkedModuleBlock({self.module}, {self.classes}, {self.vtables})"

    __repr__ = __str__


@final
@dataclass
class Function:
    identifier: str
    definer: Class | None
    implementer: Class | None

    @override
    def __str__(self) -> str:
        if self.implementer and self.implementer != self.definer:
            return f"{self.implementer.identifier} -> {self.identifier}"
        return self.identifier

    __repr__ = __str__
