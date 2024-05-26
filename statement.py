from typing import Generic, TypeVar

_T = TypeVar('_T')


class Statement:
    class Visitor:
        def visit_module_block(self, statement): pass
        def visit_class(self, statement): pass
        def visit_vtable(self, statement): pass
        def visit_vtable_entry(self, statement): pass
        def visit_linked_module_block(self, statement): pass

    def accept(self, visitor): pass


class ModuleBlock(Statement, Generic[_T]):
    def __init__(self, module, statements):
        self.module = module
        self.statements = statements

    def accept(self, visitor):
        return visitor.visit_module_block(self)

    def __str__(self):
        return f"ModuleBlock({self.module}, {self.statements})"

    __repr__ = __str__


class Class(Statement):
    _class_sizes = {}

    def __init__(self, identifier, bases, offset, size):
        self.identifier = identifier
        self.bases = bases
        self.offset = offset
        if identifier not in Class._class_sizes:
            Class._class_sizes[identifier] = Size(size)
        self._size = self._class_sizes[identifier]
        self.vtable = None
        self.is_faulty = False

    def set_size(self, size, is_determined):
        if self._size.is_determined: return
        self._size.size = size
        self._size.is_determined = is_determined

    def get_size(self):
        return self._size.size

    def is_determined_size(self) -> bool:
        return self._size.is_determined

    def clone(self):
        bases: list[Class] = [base.clone() for base in self.bases]
        new_class = Class(self.identifier, bases, self.offset, self._size.size)
        new_class.vtable = self.vtable
        return new_class

    def accept(self, visitor):
        return visitor.visit_class(self)

    def __str__(self):
        return f"Class({self.identifier}, {self.bases}, {self.offset}, {self._size.size}, {self.vtable})"

    __repr__ = __str__


class Size:
    def __init__(self, size):
        self.size = size
        self.is_determined = False

    def __str__(self):
        return hex(self.size)

    __repr__ = __str__


class VTable(Statement):
    def __init__(
            self,
            m_flag,
            v_flag,
            a_flag,
            address,
            relative_address,
            owner,
            identifier,
            vtable_count,
            vtable_entry_list):
        self.m_flag = m_flag
        self.v_flag = v_flag
        self.a_flag = a_flag
        self.address = address
        self.relative_address = relative_address
        self.owner = owner
        self.identifier = identifier
        self.vtable_count = vtable_count
        self.vtable_entry_list = vtable_entry_list

    def accept(self, visitor):
        return visitor.visit_vtable(self)

    def __str__(self):
        return f"VTable({self.m_flag}, {self.v_flag}, {self.a_flag}, {hex(self.address)}, {hex(self.relative_address)}, {self.owner}, {self.identifier}, {self.vtable_count}, {self.vtable_entry_list}) "

    __repr__ = __str__


class VTableEntry(Statement):
    def __init__(self, index, address, relative_address, function_identifier):
        self.index = index
        self.address = address
        self.relative_address = relative_address
        self.function = Function(function_identifier, None, None)

    def accept(self, visitor):
        return visitor.visit_vtable_entry(self)

    def __str__(self):
        return f"VTableEntry({self.index}, {hex(self.address)}, {hex(self.relative_address)}, {self.function})"

    __repr__ = __str__


class LinkedModuleBlock(Statement):
    def __init__(self, module, classes, vtables):
        self.module = module
        self.classes = classes
        self.vtables = vtables

    def accept(self, visitor):
        return visitor.visit_linked_module_block(self)

    def __str__(self):
        return f"LinkedModuleBlock({self.module}, {self.classes}, {self.vtables})"

    __repr__ = __str__


class Function:
    def __init__(self, identifier, definer, implementer):
        self.identifier = identifier
        self.definer = definer
        self.implementer = implementer

    def __str__(self):
        if self.implementer and self.implementer != self.definer:
            return f"{self.implementer.identifier} -> {self.identifier}"
        return self.identifier

    __repr__ = __str__
