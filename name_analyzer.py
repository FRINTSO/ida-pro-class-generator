import re
from typing import List, NoReturn

from exeptions import NameAnalyzerException
from lex_token import Token, TokType
from lexer import InheritanceLexer
from source_iterator import SourceIterator

type_keywords = {
    "bool": TokType.BOOL,
    "char": TokType.CHAR,
    "short": TokType.SHORT,
    "long": TokType.LONG,
    "int": TokType.INT,
    "double": TokType.DOUBLE,
    "float": TokType.FLOAT,
    "signed": TokType.SIGNED,
    "unsigned": TokType.UNSIGNED,
    "__ptr64": TokType.PTR64,
    "__int64": TokType.INT64,
    "void": TokType.VOID
}


class NameAnalyzer(SourceIterator):
    def __init__(self, tokens: List[Token]):
        super().__init__(tokens)
        self._start = 0
        self._tokens: List[Token] = []
        self._names: List[str] = []
        self._allowed_chars_re = re.compile(r"[^\w_]")
        self._should_fix_names = True

    def analyze_names(self, should_fix_names: bool = True) -> List[Token]:
        self._should_fix_names = should_fix_names
        while not self._is_at_end():
            self._start = self._current
            self._analyze_name()
        return self._tokens

    def _analyze_name(self) -> NoReturn:

        if self._check(TokType.IDENTIFIER) and self._peek_next().token_type == TokType.DOT: self._module()  # module
        elif self._check(TokType.IDENTIFIER) or self._check(TokType.BACKTICK): self._type_name()
        else:
            self._add_token(self._advance())

    def _module(self) -> NoReturn:
        """
        MODULE : IDENTIFIER (DOT IDENTIFIER)+
        """
        module_name = self._consume(TokType.IDENTIFIER, "Expect identifier as the first part of a module name.").literal
        while self._match(TokType.DOT):
            module_name += "." + self._consume(TokType.IDENTIFIER, "Expect identifier after '.'.").literal
        self._add_token(Token(TokType.MODULE, module_name, self._line_nr()))

    def _type_name(self) -> NoReturn:
        """
        type_name : namespace_or_type_name
        """
        type_name = self._namespace_or_type_name()
        self._add_token(Token(TokType.IDENTIFIER, type_name, self._line_nr()))

    def _namespace_or_type_name(self) -> str:
        """
        namespace_or_type_name : special_name type_argument_list?
                               | namespace_or_typename '::' special_name type_argument_list?
        """
        namespace_name = self._special_name()
        if self._check(TokType.LEFT_ANGLE_BRACE):
            namespace_name += self._type_argument_list()
        if self._match(TokType.DOUBLE_COLON):
            namespace_name += f"::{self._namespace_or_type_name()}"

            if self._check(TokType.LEFT_ANGLE_BRACE):
                namespace_name += self._type_argument_list()
        elif self._match(TokType.ASTERISK, TokType.AMPERSAND):
            namespace_name += "*" if self._previous().token_type == TokType.ASTERISK else "&"
            while self._match(TokType.ASTERISK, TokType.AMPERSAND): namespace_name += "*" if self._previous().token_type == TokType.ASTERISK else "&"
            namespace_name += self._namespace_or_type_name()
            # self._consume(TokenType.PTR64, "Expect '__ptr64' following pointer type.")
            if self._check_literal("const"):
                self._advance()
                namespace_name += "const"
        elif self._check(TokType.LEFT_BRACE):
            if self._peek(1).literal == "No" and self._peek(2).literal == "Base" and self._peek(3).literal == "Classes":
                self._advance(4)
                self._consume(TokType.RIGHT_BRACE, "Expect ')'.")
            else:
                namespace_name += self._function_pointer_name()
                namespace_name += self._function_pointer_parameters()
        return namespace_name

    def _function_pointer_name(self) -> str:
        """
        function_pointer_name : calling_convention '*'* namespace_or_type_name?
        """

        self._consume(TokType.LEFT_BRACE, "Expect '('.")
        if not self._match(TokType.CDECL, TokType.FASTCALL, TokType.VECTORCALL):
            raise self._error("Expected calling convention.")
        function_pointer_name = self._previous().literal
        while self._match(TokType.ASTERISK): function_pointer_name += "*"
        if not self._check(TokType.RIGHT_BRACE):
            function_pointer_name += self._namespace_or_type_name()
        self._consume(TokType.RIGHT_BRACE, "Expect ')'.")
        return f"({function_pointer_name})"

    def _function_pointer_parameters(self) -> str:
        self._consume(TokType.LEFT_BRACE, "Expect '('.")
        parameters = ""
        if self._check(TokType.IDENTIFIER) or self._peek().token_type in type_keywords.values():
            parameters += self._type_argument()
            while self._match(TokType.COMMA):
                parameters += f",{self._type_argument()}"
        self._consume(TokType.RIGHT_BRACE, "Expect ')'.")
        return f"({parameters})"

    def _type_argument_list(self) -> str:
        """
        type_argument_list : '<' type_arguments '>'
        """
        self._consume(TokType.LEFT_ANGLE_BRACE, "Expect '<'.")
        type_arguments = self._type_arguments()
        self._consume(TokType.RIGHT_ANGLE_BRACE, f"Expect '>', received {self._source[self._current]}.")
        return f"<{type_arguments}>"

    def _type_arguments(self) -> str:
        """
        type_arguments : type_argument (',' type_argument)*
        """
        type_arguments = self._type_argument()
        while self._match(TokType.COMMA):
            type_arguments += f",{self._type_argument()}"
        return type_arguments

    def _type_argument(self) -> str:
        """
        type_argument : SOMETHING
        """
        if self._check_literals("class", "struct", "enum"): self._advance()

        if self._check(TokType.IDENTIFIER) or self._peek().token_type in type_keywords.values():
            if self._peek_next().token_type in (TokType.CDECL, TokType.FASTCALL, TokType.VECTORCALL, TokType.STDCALL):
                return self._function_pointer_as_parameter()
            return self._namespace_or_type_name()
        elif self._match(TokType.NUMBER):
            return self._previous().literal
        elif self._check(TokType.LEFT_ANGLE_BRACE):
            return self._lambda()
        elif self._check(TokType.BACKTICK):
            return self._namespace_or_type_name()
        raise self._error(f"Unexpected type argument: {self._source[self._current].literal}")

    def _lambda(self) -> str:
        self._consume(TokType.LEFT_ANGLE_BRACE, "Expect '<'.")
        _lambda = self._consume(TokType.IDENTIFIER, "Expect identifier.")
        self._consume(TokType.RIGHT_ANGLE_BRACE, "Expect '>'.")
        return _lambda.literal

    def _function_pointer_as_parameter(self) -> str:
        function_pointer = self._namespace_or_type_name()
        if not self._match(TokType.CDECL, TokType.FASTCALL, TokType.VECTORCALL, TokType.STDCALL):
            raise self._error("Expected calling convention.")
        function_pointer += self._previous().literal
        function_pointer += self._function_pointer_parameters()
        return function_pointer

    def _special_name(self) -> str:
        """
        special_name : identifier
                     | custom_name
        """
        if self._match(TokType.IDENTIFIER):
            return self._previous().literal
        elif self._peek().token_type in type_keywords.values():
            return self._type_keyword()
        else:
            return self._custom_name()

    def _custom_name(self) -> str:
        """
        custom_name : BACKTICK STRING APOSTROPHE
        """
        # replace invalid characters by underscores
        self._consume(TokType.BACKTICK, "Expect backtick.")
        custom_name = self._advance().literal
        while not self._match(TokType.APOSTROPHE):
            custom_name += f"_{self._advance().literal}"
        return custom_name

    def _type_keyword(self) -> str:

        def _match_long():
            if self._match(TokType.INT):
                return "long int"
            elif self._match(TokType.LONG):
                if self._match(TokType.INT):
                    return "long long int"
                return "long long"
            elif self._match(TokType.DOUBLE):
                return "long double"
            return "long"

        def _match_short():
            if self._match(TokType.INT):
                return "short int"
            return "short"

        if self._match(TokType.SHORT):
            return _match_short()
        elif self._match(TokType.LONG):
            return _match_long()
        elif self._match(TokType.SIGNED):
            if self._match(TokType.INT):
                return "signed int"
            elif self._match(TokType.CHAR):
                return "signed char"
            elif self._match(TokType.SHORT):
                return f"signed {_match_short()}"
            elif self._match(TokType.LONG):
                return f"signed {_match_long()}"
            elif self._match(TokType.INT64):
                return "signed __int64"
            elif self._match(TokType.PTR64):
                return "signed __ptr64"
        elif self._match(TokType.UNSIGNED):
            if self._match(TokType.INT):
                return "unsigned int"
            elif self._match(TokType.CHAR):
                return "unsigned char"
            elif self._match(TokType.SHORT):
                return f"unsigned {_match_short()}"
            elif self._match(TokType.LONG):
                return f"unsigned {_match_long()}"
            elif self._match(TokType.INT64):
                return "unsigned __int64"
            elif self._match(TokType.PTR64):
                return "unsigned __ptr64"
        elif self._match(TokType.INT64):
            return "__int64"
        elif self._match(TokType.PTR64):
            return "__ptr64"
        elif self._match(TokType.BOOL, TokType.CHAR, TokType.INT, TokType.FLOAT, TokType.DOUBLE, TokType.VOID):
            return self._previous().token_type.name.lower()
        else:
            raise self._error("Invalid integral type.")

    def _line_nr(self) -> int:
        return self._source[self._start].line_nr

    def _check(self, token_type: TokType) -> bool:
        if self._is_at_end(): return False
        return self._peek().token_type == token_type

    def _consume(self, token_type: TokType, message: str) -> Token:
        if self._check(token_type): return self._advance()
        raise self._error(message)

    def _check_literal(self, literal: str) -> bool:
        if self._is_at_end(): return False
        return self._peek().literal == literal

    def _check_literals(self, *literals: str) -> bool:
        for literal in literals:
            if self._check_literal(literal):
                return True
        return False

    def _consume_literal(self, literal: str, message: str) -> Token:
        if self._check_literal(literal): return self._advance()
        raise self._error(message)

    def _match(self, *types: TokType) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _add_token(self, token: Token) -> NoReturn:
        # clean name
        if self._should_fix_names and token.token_type == TokType.IDENTIFIER:
            token.literal = self._clean_name(token.literal)
        self._tokens.append(token)

    def _clean_name(self, name: str) -> str:
        name = self._allowed_chars_re.sub("_", name)
        return name

    def _error(self, message: str) -> NameAnalyzerException:
        print(f"Error at line {self._peek().line_nr}: {message}, Start: {self._start}, Current: {self._current}")
        return NameAnalyzerException(message)


def main() -> NoReturn:
    lexer = InheritanceLexer(r"vtable.txt")
    tokens = lexer.tokenize()
    name_analyzer = NameAnalyzer(tokens)
    tokens = name_analyzer.analyze_names()
    for token in tokens:
        print(token)


if __name__ == '__main__':
    main()
