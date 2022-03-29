from typing import List

from lexer import InheritanceLexer
from parser import InheritanceParser
from source_iterator import SourceIterator
from statement import ModuleBlock


class ClassConstructor(SourceIterator):
    def __init__(self, modules: List[ModuleBlock]):
        super().__init__(modules)

    def generate(self):
        for module in self._source:
            print(module)


def main():
    lexer = InheritanceLexer("hierarchies/inheritance.txt")
    tokens = lexer.tokenize()
    parser = InheritanceParser(tokens)
    statements = parser.parse()
    class_constructor = ClassConstructor(statements)
    class_constructor.generate()


if __name__ == '__main__':
    main()