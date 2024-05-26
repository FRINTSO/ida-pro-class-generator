from __future__ import annotations

import sys
from typing import NoReturn, TYPE_CHECKING, Optional

from pygments.token import Token, Name, Whitespace, Number

from lexer import Lexer
from statement import ModuleBlock, Class, VTable, VTableEntry
from exeptions import ParseException

if TYPE_CHECKING:
    from pygments.token import _TokenType
    TokenType = tuple[_TokenType, str, int]


class InheritanceParser:
    def __init__(self, token_stream) -> None:
        self._token_stream = token_stream

        self._current: TokenType = (Token, '', 0)
        self._previous: TokenType = (Token, '', 0)

    def _advance(self) -> None:
        self._previous = self._current
        try:
            self._current = next(self._token_stream)
        except StopIteration:
            self._current = (Token.EOF, 'EOF', 0)

    def _consume(self, token_type: _TokenType, message: str) -> TokenType | NoReturn:
        if self._current[0] == token_type:
            self._advance()
            return self._previous
        raise self._error(message)

    def _consume_literal(self, literal: str, message: str) -> None:
        if self._current[1] == literal:
            self._advance()
            return
        raise self._error(message)

    def _check(self, token_type: _TokenType) -> bool:
        return self._current[0] is token_type

    def _check_literal(self, literal: str) -> bool:
        return self._current[1] == literal

    def _match(self, token_type: _TokenType) -> bool:
        if not self._check(token_type): return False
        self._advance()
        return True

    def _match_literal(self, literal: str) -> bool:
        if not self._check_literal(literal): return False
        self._advance()
        return True

    def _error(self, message: str) -> NoReturn:
        print(f"Error: {message} Received: {self._current}.")
        raise ParseException(f"{message} At line {self._current[2]}.")

    def _module_declaration(self) -> ModuleBlock:
        """
        module_declaration : begin_module vtable_list end_module
        """
        _, module_begin_literal, _ = self._begin_module()

        class_statements: list[Class] = []
        while self._check(Name.Identifier):
            class_statements.append(self._class_statement())
            self._consume(Whitespace.EmptyLine, "Different type declarations need to be separated by a newline.")
        _, module_end_literal, _ = self._end_module()
        if module_begin_literal != module_end_literal:
            raise ParseException("Module name did not match declared module name.")
        return ModuleBlock(module_begin_literal, class_statements)

    def _begin_module(self) -> TokenType:
        """
        begin_module : '<' module '>'
        """
        self._consume_literal("<", "Missing '<' before module name.")
        token = self._consume(Name.Module, "Invalid module name.")
        self._consume_literal('>', "Missing '>' after module name.")
        return token

    def _end_module(self) -> TokenType:
        """
        end_module : '<' 'end' module '>'
        """
        self._consume_literal('<', "Missing '<' before 'end'.")
        self._consume_literal('end', "Missing 'end' after '<'.")
        token = self._consume(Name.Module, "Invalid module name.")
        self._consume_literal('>', "Missing '>' after module name.")
        return token

    def _class_statement(self) -> Class:
        """
        class_statement : identifier (':' class_inheritance_list)?
        """
        _, class_name, _ = self._consume(Name.Identifier, "Expect identifier.")
        base_classes: list[Class] = []
        if self._match_literal(':'):
            unresolved_base_classes: list[Class] = self._class_inheritance_list()

            current_class: Optional[Class] = None
            new_offset = -1
            for class_statement in unresolved_base_classes:
                if new_offset != class_statement.offset:
                    new_offset = class_statement.offset
                    current_class = class_statement
                    base_classes.append(current_class)
                elif current_class is not None:
                    current_class.bases.append(class_statement)
                    current_class = class_statement

        # if class has vtable, then class size is at least 8 bytes
        return Class(class_name, base_classes, 0, 0)

    def _class_inheritance_list(self) -> list[Class]:
        """
        CLASS_INHERITANCE_LIST : CLASS_INHERITANCE+
        """
        if self._check(Number.Hex):
            bases: list[Class] = []
            while self._check(Number.Hex):
                bases.append(self._class_inheritance())
            bases.sort(key=lambda x: x.offset)
            return bases
        else:
            raise self._error("Expect inheritance following ':'.")

    def _class_inheritance(self) -> Class:
        """
        class_inheritance : hexadecimal identifier
        """
        _, offset, _ = self._consume(Number.Hex, "Expect hexadecimal offset.")
        _, class_name, _ = self._consume(Name.Identifier, "Expect identifier.")
        offset_number = int(offset, 16)
        return Class(class_name, [], offset_number, 0)

    def parse(self) -> list[ModuleBlock]:
        statements: list[ModuleBlock] = []
        self._advance()

        while self._current[0] is not Token.EOF:
            statements.append(self._module_declaration())
            self._match(Whitespace.EmptyLine)
        return statements


class VTableParser:
    def __init__(self, token_stream):
        self._token_stream = token_stream

        self._current: TokenType = ...
        self._previous: TokenType = ...

    def _advance(self) -> None:
        self._previous = self._current
        try:
            self._current = next(self._token_stream)
        except StopIteration:
            self._current = (Token.EOF, 'EOF', 0)

    def _consume(self, token_type: _TokenType, message: str) -> TokenType:
        if self._current[0] == token_type:
            self._advance()
            return self._previous
        raise self._error(message)

    def _consume_literal(self, literal: str, message: str) -> None:
        if self._current[1] == literal:
            self._advance()
            return
        raise self._error(message)

    def _check(self, token_type: _TokenType) -> bool:
        return self._current[0] is token_type

    def _check_literal(self, literal: str) -> bool:
        return self._current[1] == literal

    def _match(self, token_type: _TokenType) -> bool:
        if not self._check(token_type): return False
        self._advance()
        return True

    def _match_literal(self, literal: str) -> bool:
        if not self._check_literal(literal): return False
        self._advance()
        return True

    def _error(self, message: str) -> NoReturn:
        print(f"Error: {message} Received: {self._current}.", file=sys.stderr)
        raise ParseException(f"{message} At line {self._current[2]}.")

    def _module_declaration(self) -> ModuleBlock:
        """
        module_declaration : begin_module vtable_list end_module
        """
        _, module_begin_literal, _ = self._begin_module()
        vtable_lists: list[VTable] = []
        while self._check(Token.MFlag):
            vtable_lists.append(self._vtable_declaration())
            self._consume(Whitespace.EmptyLine, "Expect empty line after vtable.")
        _, module_end_literal, _ = self._end_module()
        if module_begin_literal != module_end_literal:
            raise ParseException("Module name did not match declared module name.")
        self._match(Whitespace.EmptyLine)
        return ModuleBlock(module_begin_literal, vtable_lists)

    def _begin_module(self) -> TokenType:
        """
        begin_module : '<' module '>'
        """
        self._consume_literal("<", "Missing '<' before module name.")
        token = self._consume(Name.Module, "Invalid module name.")
        self._consume_literal('>', "Missing '>' after module name.")
        return token

    def _end_module(self) -> TokenType:
        """
        end_module : '<' 'end' module '>'
        """
        self._consume_literal('<', "Missing '<' before 'end'.")
        self._consume_literal('end', "Missing 'end' after '<'.")
        token = self._consume(Name.Module, "Invalid module name.")
        self._consume_literal('>', "Missing '>' after module name.")
        return token

    def _vtable_declaration(self) -> VTable:
        """
        vtable_declaration : m_flag v_flag a_flag address relative_address (owner_identifier '->') const vtable_identifier
                             'Virtual Functions' '(' number ')' ':' vtable_entry_list
        """
        _, m_flag, _ = self._consume(Token.MFlag, "Expect m flag.")
        _, v_flag, _ = self._consume(Token.VFlag, "Expect v flag.")
        _, a_flag, _ = self._consume(Token.AFlag, "Expect a flag.")
        _, address, _ = self._consume(Number.Hex, "Expect address as a hex number.")
        _, relative_address, _ = self._consume(Number.Hex, "Expect relative address as a hex number.")
        owner = ""

        if not self._check_literal('const'):
            _, owner, _ = self._consume(Name.Identifier, "Expect identifier.")
            self._consume_literal('->', "Expect '->' following identifier.")
        self._consume_literal('const', "Expect 'const' before identifier.")
        _, identifier, _ = self._consume(Name.Identifier, "Expect identifier.")

        self._consume_literal('Virtual Functions', "Expect 'Virtual Functions'.")
        self._consume_literal('(', "Expect '('.")
        _, vtable_count, _ = self._consume(Number, "Expect decimal number.")
        self._consume_literal(')', "Expect ')'.")
        self._consume_literal(':', "Expect ':'.")

        address_number = int(address, base=16)
        relative_address_number = int(relative_address, base=16)
        vtable_count_number = int(vtable_count)

        vtable_entry_list = self._vtable_entry_list(vtable_count_number)

        return VTable(m_flag != " ", v_flag != " ", a_flag != " ", address_number, relative_address_number, owner,
                      identifier.strip(), vtable_count_number, vtable_entry_list)

    def _vtable_entry_list(self, count: int) -> list[VTableEntry]:
        """
        vtable_entry_list : vtable_entry+
        """
        entries: list[VTableEntry] = []
        for _ in range(count):
            entries.append(self._vtable_entry())

        return entries

    def _vtable_entry(self) -> VTableEntry:
        """
        vtable_entry : number address relative_address function_type function_address
        """
        _, index, _ = self._consume(Number, "Expect entry index.")
        _, address, _ = self._consume(Number.Hex, "Expect address.")
        _, relative_address, _ = self._consume(Number.Hex, "Expect relative address.")
        _, function_identifier, _ = self._consume(Name.Identifier, "Expect function identifier.")

        index_number = int(index)
        address_number = int(address, base=16)
        relative_address_number = int(relative_address, base=16)

        return VTableEntry(index_number, address_number, relative_address_number, function_identifier)

    def parse(self) -> list[ModuleBlock]:
        statements: list[ModuleBlock] = []
        self._advance()

        while self._current[0] is not Token.EOF:
            statements.append(self._module_declaration())
        return statements


def main():
    # lexer = InheritanceLexer(r"C:\Users\william.malmgrenhan\Desktop\Class_Dumper\ROTTR\inheritance.txt")
    # lexer = InheritanceLexer(r"inheritance.txt")
    with open(r"C:\Users\willi\Desktop\Class_Dumper\GTA5\vtable.txt", "r") as read: text = read.read()

    lexer = Lexer()
    lexer.tokenize(text)
    tokens = lexer.tokenize(text)
    parser = VTableParser(tokens)
    # parser = InheritanceParser(tokens)
    statements = parser.parse()
    for statement in statements:
        print(statement)


if __name__ == '__main__':
    main()
