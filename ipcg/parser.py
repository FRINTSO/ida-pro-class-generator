from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import NoReturn

from ipcg.tokens import Token, TokenKind

from .exeptions import ParseException
from .statement import Class, ModuleBlock, VTable, VTableEntry


class InheritanceParser:
    def __init__(self, token_stream: Iterator[Token]) -> None:
        self._token_stream: Iterator[Token] = token_stream

        self._current: Token = Token(TokenKind.EOF, "", 0)
        self._previous: Token = Token(TokenKind.EOF, "", 0)

    def _advance(self) -> None:
        self._previous = self._current
        try:
            self._current = next(self._token_stream)
            print(self._current)
        except StopIteration:
            self._current = Token(TokenKind.EOF, "EOF", 0)

    def _consume(self, token_kind: TokenKind, message: str) -> Token | NoReturn:
        if self._current.kind == token_kind:
            self._advance()
            return self._previous
        raise self._error(message)

    def _consume_literal(self, literal: str, message: str) -> None:
        if self._current.literal == literal:
            self._advance()
            return
        raise self._error(message)

    def _check(self, token_kind: TokenKind) -> bool:
        return self._current.kind is token_kind

    def _check_literal(self, literal: str) -> bool:
        return self._current.literal == literal

    def _match(self, token_type: TokenKind) -> bool:
        if not self._check(token_type):
            return False
        self._advance()
        return True

    def _match_literal(self, literal: str) -> bool:
        if not self._check_literal(literal):
            return False
        self._advance()
        return True

    def _error(self, message: str) -> NoReturn:
        print(f"Error: {message} Received: {self._current}.")
        raise ParseException(f"{message} At line {self._current.line}.")

    def _module_declaration(self) -> ModuleBlock[Class]:
        """
        module_declaration : begin_module vtable_list end_module
        """
        module_begin_literal = self._begin_module().literal

        class_statements: list[Class] = []
        while self._check(TokenKind.IDENTIFIER):
            class_statements.append(self._class_statement())
            _ = self._match(
                TokenKind.EMPTY_LINE,
                # "Different type declarations need to be separated by a newline.",
            )
        module_end_literal = self._end_module().literal
        if module_begin_literal != module_end_literal:
            raise ParseException("Module name did not match declared module name.")
        return ModuleBlock(module_begin_literal, class_statements)

    def _begin_module(self) -> Token:
        """
        begin_module : '<' module '>'
        """
        self._consume_literal("<", "Missing '<' before module name.")
        token = self._consume(TokenKind.MODULE, "Invalid module name.")
        self._consume_literal(">", "Missing '>' after module name.")
        return token

    def _end_module(self) -> Token:
        """
        end_module : '<' 'end' module '>'
        """
        self._consume_literal("<", "Missing '<' before 'end'.")
        self._consume_literal("end", "Missing 'end' after '<'.")
        token = self._consume(TokenKind.MODULE, "Invalid module name.")
        self._consume_literal(">", "Missing '>' after module name.")
        return token

    def _class_statement(self) -> Class:
        """
        class_statement : identifier (':' class_inheritance_list)?
        """
        token = self._consume(TokenKind.IDENTIFIER, "Expect identifier.")
        base_classes: list[Class] = []
        if self._match_literal(":"):
            unresolved_base_classes: list[Class] = self._class_inheritance_list()

            current_class: Class | None = None
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
        return Class(token.literal, base_classes, 0, 0)

    def _class_inheritance_list(self) -> list[Class]:
        """
        CLASS_INHERITANCE_LIST : CLASS_INHERITANCE+
        """
        if self._check(TokenKind.HEX):
            bases: list[Class] = []
            while self._check(TokenKind.HEX):
                bases.append(self._class_inheritance())
            bases.sort(key=lambda x: x.offset)
            return bases
        else:
            raise self._error("Expect inheritance following ':'.")

    def _class_inheritance(self) -> Class:
        """
        class_inheritance : hexadecimal identifier
        """
        offset = self._consume(TokenKind.HEX, "Expect hexadecimal offset.")
        class_name = self._consume(TokenKind.IDENTIFIER, "Expect identifier.")
        offset_number = int(offset.literal, 16)
        return Class(class_name.literal, [], offset_number, 0)

    def parse(self) -> list[ModuleBlock[Class]]:
        statements: list[ModuleBlock[Class]] = []
        self._advance()

        while self._current.kind is not TokenKind.EOF:
            statements.append(self._module_declaration())
            _ = self._match(TokenKind.EMPTY_LINE)
        return statements


class VTableParser:
    def __init__(self, token_stream: Iterator[Token]) -> None:
        self._token_stream: Iterator[Token] = token_stream

        self._current: Token = Token.eof()
        self._previous: Token = Token.eof()

    def _advance(self) -> None:
        self._previous = self._current
        try:
            self._current = next(self._token_stream)
        except StopIteration:
            self._current = Token(TokenKind.EOF, "EOF", 0)

    def _consume(self, token_kind: TokenKind, message: str) -> Token:
        if self._current.kind is token_kind:
            self._advance()
            return self._previous
        raise self._error(message)

    def _consume_literal(self, literal: str, message: str) -> None:
        if self._current.literal == literal:
            self._advance()
            return
        raise self._error(message)

    def _check(self, token_kind: TokenKind) -> bool:
        return self._current.kind is token_kind

    def _check_literal(self, literal: str) -> bool:
        return self._current.literal == literal

    def _match(self, token_kind: TokenKind) -> bool:
        if not self._check(token_kind):
            return False
        self._advance()
        return True

    def _match_literal(self, literal: str) -> bool:
        if not self._check_literal(literal):
            return False
        self._advance()
        return True

    def _error(self, message: str) -> NoReturn:
        print(f"Error: {message} Received: {self._current}.", file=sys.stderr)
        raise ParseException(f"{message} At line {self._current.line}.")

    def _module_declaration(self) -> ModuleBlock[VTable]:
        """
        module_declaration : begin_module vtable_list end_module
        """
        module_begin_literal = self._begin_module().literal
        vtable_lists: list[VTable] = []
        while self._check(TokenKind.M_FLAG):
            vtable_lists.append(self._vtable_declaration())
            _ = self._match(
                TokenKind.EMPTY_LINE,
                # "Expect empty line after vtable.",
            )
        module_end_literal = self._end_module().literal
        if module_begin_literal != module_end_literal:
            raise ParseException("Module name did not match declared module name.")
        _ = self._match(TokenKind.EMPTY_LINE)
        return ModuleBlock(module_begin_literal, vtable_lists)

    def _begin_module(self) -> Token:
        """
        begin_module : '<' module '>'
        """
        self._consume_literal("<", "Missing '<' before module name.")
        token = self._consume(TokenKind.MODULE, "Invalid module name.")
        self._consume_literal(">", "Missing '>' after module name.")
        return token

    def _end_module(self) -> Token:
        """
        end_module : '<' 'end' module '>'
        """
        self._consume_literal("<", "Missing '<' before 'end'.")
        self._consume_literal("end", "Missing 'end' after '<'.")
        token = self._consume(TokenKind.MODULE, "Invalid module name.")
        self._consume_literal(">", "Missing '>' after module name.")
        return token

    def _vtable_declaration(self) -> VTable:
        """
        vtable_declaration : m_flag v_flag a_flag address relative_address (owner_identifier '->') const vtable_identifier
                             'Virtual Functions' '(' number ')' ':' vtable_entry_list
        """
        m_flag = self._consume(TokenKind.M_FLAG, "Expect m flag.").literal
        v_flag = self._consume(TokenKind.V_FLAG, "Expect v flag.").literal
        a_flag = self._consume(TokenKind.A_FLAG, "Expect a flag.").literal
        address = self._consume(
            TokenKind.HEX, "Expect address as a hex number."
        ).literal
        relative_address = self._consume(
            TokenKind.HEX, "Expect relative address as a hex number."
        ).literal
        owner = ""

        if not self._check_literal("const"):
            owner = self._consume(TokenKind.IDENTIFIER, "Expect identifier.").literal
            self._consume_literal("->", "Expect '->' following identifier.")
        self._consume_literal("const", "Expect 'const' before identifier.")
        identifier = self._consume(TokenKind.IDENTIFIER, "Expect identifier.").literal

        self._consume_literal("Virtual Functions", "Expect 'Virtual Functions'.")
        self._consume_literal("(", "Expect '('.")
        vtable_count = self._consume(TokenKind.NUMBER, "Expect decimal number.").literal
        self._consume_literal(")", "Expect ')'.")
        self._consume_literal(":", "Expect ':'.")

        address_number = int(address, base=16)
        relative_address_number = int(relative_address, base=16)
        vtable_count_number = int(vtable_count)

        vtable_entry_list = self._vtable_entry_list(vtable_count_number)

        return VTable(
            m_flag != " ",
            v_flag != " ",
            a_flag != " ",
            address_number,
            relative_address_number,
            owner,
            identifier.strip(),
            vtable_count_number,
            vtable_entry_list,
        )

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
        index = self._consume(TokenKind.NUMBER, "Expect entry index.").literal
        address = self._consume(TokenKind.HEX, "Expect address.").literal
        relative_address = self._consume(
            TokenKind.HEX, "Expect relative address."
        ).literal
        function_identifier = self._consume(
            TokenKind.IDENTIFIER, "Expect function identifier."
        ).literal

        index_number = int(index)
        address_number = int(address, base=16)
        relative_address_number = int(relative_address, base=16)

        return VTableEntry(
            index_number, address_number, relative_address_number, function_identifier
        )

    def parse(self) -> list[ModuleBlock[VTable]]:
        statements: list[ModuleBlock[VTable]] = []
        self._advance()

        while self._current.kind is not TokenKind.EOF:
            statements.append(self._module_declaration())
        return statements
