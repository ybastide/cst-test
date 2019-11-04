from pathlib import Path
from typing import List, Tuple, Optional

from libcst import (
    Attribute,
    BinaryOperation,
    ClassDef,
    FunctionDef,
    ImportAlias,
    matchers as m,
    Call,
    ensure_type,
    Name,
)
from libcst.metadata import PositionProvider


class Checker(m.MatcherDecoratableVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.future_division = False
        self.errors = False
        self.stack: List[str] = []

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

    def visit_ClassDef(self, node: ClassDef) -> None:
        self.stack.append(node.name.value)

    def leave_ClassDef(self, node: ClassDef) -> None:
        self.stack.pop()

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self.stack.append(node.name.value)

    def leave_FunctionDef(self, node: FunctionDef) -> None:
        self.stack.pop()

    def visit_ClassDef_bases(self, node: "ClassDef") -> None:
        return

    def visit_Call(self, node: Call) -> Optional[bool]:
        if m.matches(node.func, m.Attribute()):  # method call
            name = ensure_type(node.func, Attribute).attr.value
            if name == "assertEquals":
                pos = self.get_metadata(PositionProvider, node).start
                print(f"{self.path}:{pos.line}:{pos.column}: use of assertEquals")
                self.errors = True
        return None
