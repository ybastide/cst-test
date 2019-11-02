from pathlib import Path

from libcst import Attribute, BinaryOperation, ImportAlias, matchers as m
from libcst.metadata import PositionProvider


class Checker(m.MatcherDecoratableVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.future_division = False
        self.errors = False

    @m.call_if_inside(m.ImportFrom(module=m.Name("__future__")))
    @m.visit(m.ImportAlias(name=m.Name("division")))
    def import_div(self, node: ImportAlias) -> None:
        self.future_division = True

    @m.visit(m.BinaryOperation(operator=m.Divide()))
    def check_div(self, node: BinaryOperation) -> None:
        if not self.future_division:
            pos = self.get_metadata(PositionProvider, node).start
            print(
                f"{self.path}:{pos.line}:{pos.column}: division without `from __future__ import division`"
            )
            self.errors = True

    @m.visit(m.Attribute(attr=m.Name("maxint"), value=m.Name("sys")))
    def check_maxint(self, node: Attribute) -> None:
        pos = self.get_metadata(PositionProvider, node).start
        print(f"{self.path}:{pos.line}:{pos.column}: use of sys.maxint")
        self.errors = True
