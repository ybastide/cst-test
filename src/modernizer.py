import re
from pathlib import Path
from typing import Dict, Optional, Set, Union, Tuple, List

from libcst import (
    Arg,
    BaseExpression,
    BaseStatement,
    CSTNode,
    Call,
    ImportAlias,
    ImportStar,
    Module,
    Name,
    RemovalSentinel,
    SimpleStatementLine,
    ensure_type,
    matchers as m,
    parse_module,
    parse_statement,
    Attribute,
    Comment,
    Param,
    TrailingWhitespace,
    Assign,
    FunctionDef,
    EmptyLine,
)
from libcst.metadata import PositionProvider


class Modernizer(m.MatcherDecoratableTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)
    # FIXME use a stack of e.g. SimpleStatementLine then proper visit_Import/ImportFrom to store the ssl node

    def __init__(
        self, path: Path, verbose: bool = False, ignored: Optional[List[str]] = None
    ):
        super().__init__()
        self.path = path
        self.verbose = verbose
        self.ignored = set(ignored or [])
        self.errors = False
        self.stack: List[Tuple[str, ...]] = []
        self.annotations: Dict[
            Tuple[str, ...], Comment  # key: tuple of canonical variable name
        ] = {}
        self.python_future_updated_node: Optional[SimpleStatementLine] = None
        self.python_future_imports: Dict[str, str] = {}
        self.python_future_new_imports: Set[str] = set()
        self.builtins_imports: Dict[str, str] = {}
        self.builtins_new_imports: Set[str] = set()
        self.builtins_updated_node: Optional[SimpleStatementLine] = None
        self.future_utils_imports: Dict[str, str] = {}
        self.future_utils_new_imports: Set[str] = set()
        self.future_utils_updated_node: Optional[SimpleStatementLine] = None
        # self.last_import_node: Optional[CSTNode] = None
        self.last_import_node_stmt: Optional[CSTNode] = None

    # @m.call_if_inside(m.ImportFrom(module=m.Name("__future__")))
    # @m.visit(m.ImportAlias() | m.ImportStar())
    # def import_python_future_check(self, node: Union[ImportAlias, ImportStar]) -> None:
    #     self.add_import(self.python_future_imports, node)

    # @m.leave(m.ImportFrom(module=m.Name("__future__")))
    # def import_python_future_modify(
    #     self, original_node: ImportFrom, updated_node: ImportFrom
    # ) -> Union[BaseSmallStatement, RemovalSentinel]:
    #     return updated_node

    @m.call_if_inside(m.ImportFrom(module=m.Name("builtins")))
    @m.visit(m.ImportAlias() | m.ImportStar())
    def import_builtins_check(self, node: Union[ImportAlias, ImportStar]) -> None:
        self.add_import(self.builtins_imports, node)

    # @m.leave(m.ImportFrom(module=m.Name("builtins")))
    # def builtins_modify(
    #     self, original_node: ImportFrom, updated_node: ImportFrom
    # ) -> Union[BaseSmallStatement, RemovalSentinel]:
    #     return updated_node

    @m.call_if_inside(
        m.ImportFrom(module=m.Attribute(value=m.Name("future"), attr=m.Name("utils")))
    )
    @m.visit(m.ImportAlias() | m.ImportStar())
    def import_future_utils_check(self, node: Union[ImportAlias, ImportStar]) -> None:
        self.add_import(self.future_utils_imports, node)

    # @m.leave(
    #     m.ImportFrom(module=m.Attribute(value=m.Name("future"), attr=m.Name("utils")))
    # )
    # def future_utils_modify(
    #     self, original_node: ImportFrom, updated_node: ImportFrom
    # ) -> Union[BaseSmallStatement, RemovalSentinel]:
    #     return updated_node

    @staticmethod
    def add_import(
        imports: Dict[str, str], node: Union[ImportAlias, ImportStar]
    ) -> None:
        if isinstance(node, ImportAlias):
            imports[node.name.value] = (
                node.asname.name.value if node.asname else node.name.value
            )
        else:
            imports["*"] = "*"

    # @m.call_if_not_inside(m.BaseCompoundStatement())
    # def visit_Import(self, node: Import) -> Optional[bool]:
    #     self.last_import_node = node
    #     return None

    # @m.call_if_not_inside(m.BaseCompoundStatement())
    # def visit_ImportFrom(self, node: ImportFrom) -> Optional[bool]:
    #     self.last_import_node = node
    #     return None

    @m.call_if_not_inside(m.BaseCompoundStatement())
    def visit_SimpleStatementLine(self, node: SimpleStatementLine) -> Optional[bool]:
        for n in node.body:
            if m.matches(n, m.Import() | m.ImportFrom()):
                self.last_import_node_stmt = node
        return None

    # @m.visit(
    #     m.AllOf(
    #         m.SimpleStatementLine(),
    #         m.MatchIfTrue(
    #             lambda node: any(m.matches(c, m.Assign()) for c in node.children)
    #         ),
    #         m.MatchIfTrue(
    #             lambda node: "# type:" in node.trailing_whitespace.comment.value
    #         ),
    #     )
    # )
    # def visit_assign(self, node: SimpleStatementSuite) -> None:
    #     return None

    def visit_Param(self, node: Param) -> Optional[bool]:
        class Visitor(m.MatcherDecoratableVisitor):
            def __init__(self):
                super().__init__()
                self.ptype: Optional[str] = None

            def visit_TrailingWhitespace_comment(
                self, node: "TrailingWhitespace"
            ) -> None:
                if node.comment and "type:" in node.comment.value:
                    mo = re.match(r"#\s*type:\s*(\S*)", node.comment.value)
                    self.ptype = mo.group(1) if mo else None
                return None

        v = Visitor()
        node.visit(v)
        if self.verbose:
            pos = self.get_metadata(PositionProvider, node).start
            print(
                f"{self.path}:{pos.line}:{pos.column}: parameter {node.name.value}: {v.ptype or 'unknown type'}"
            )
        return None

    @m.visit(m.SimpleStatementLine())
    def visit_simple_stmt(self, node: SimpleStatementLine) -> None:
        assign = None
        for c in node.children:
            if m.matches(c, m.Assign()):
                assign = ensure_type(c, Assign)
        if assign:
            if m.MatchIfTrue(
                lambda n: n.trailing_whitespace.comment
                and "type:" in n.trailing_whitespace.comment.value
            ):

                class TypingVisitor(m.MatcherDecoratableVisitor):
                    def __init__(self):
                        super().__init__()
                        self.vtype = None

                    def visit_TrailingWhitespace_comment(
                        self, node: "TrailingWhitespace"
                    ) -> None:
                        if node.comment:
                            mo = re.match(r"#\s*type:\s*(\S*)", node.comment.value)
                            if mo:
                                vtype = mo.group(1)
                        return None

                tv = TypingVisitor()
                node.visit(tv)
                vtype = tv.vtype
            else:
                vtype = None

            class NameVisitor(m.MatcherDecoratableVisitor):
                def __init__(self):
                    super().__init__()
                    self.names: List[str] = []

                def visit_Name(self, node: Name) -> Optional[bool]:
                    self.names.append(node.value)
                    return None

            if self.verbose:
                pos = self.get_metadata(PositionProvider, node).start
                for target in assign.targets:
                    v = NameVisitor()
                    target.visit(v)
                    for name in v.names:
                        print(
                            f"{self.path}:{pos.line}:{pos.column}: variable {name}: {vtype or 'unknown type'}"
                        )

    def visit_FunctionDef_body(self, node: FunctionDef) -> None:
        class Visitor(m.MatcherDecoratableVisitor):
            def __init__(self):
                super().__init__()

            def visit_EmptyLine_comment(self, node: "EmptyLine") -> None:
                # FIXME too many matches on test_param_02
                if not node.comment:
                    return
                # TODO: use comment.value
                return None

        v = Visitor()
        node.visit(v)
        return None

    @m.call_if_not_inside(m.BaseCompoundStatement())
    def leave_SimpleStatementLine(
        self, original_node: SimpleStatementLine, updated_node: SimpleStatementLine
    ) -> Union[BaseStatement, RemovalSentinel]:
        for n in updated_node.body:
            if m.matches(n, m.ImportFrom(module=m.Name("__future__"))):
                self.python_future_updated_node = updated_node
            elif m.matches(n, m.ImportFrom(module=m.Name("builtins"))):
                self.builtins_updated_node = updated_node
            elif m.matches(
                n,
                m.ImportFrom(
                    module=m.Attribute(value=m.Name("future"), attr=m.Name("utils"))
                ),
            ):
                self.future_utils_updated_node = updated_node
        return updated_node

    map_matcher = m.Call(
        func=m.Name("filter") | m.Name("map") | m.Name("zip") | m.Name("range")
    )

    @m.visit(map_matcher)
    def visit_map(self, node: Call) -> None:
        func_name = ensure_type(node.func, Name).value
        if func_name not in self.builtins_imports:
            self.builtins_new_imports.add(func_name)

    @m.call_if_not_inside(
        m.Call(func=m.Name("list") | m.Attribute(attr=m.Name("join"))) | m.CompFor()
    )
    @m.leave(map_matcher)
    def fix_map(self, original_node: Call, updated_node: Call) -> BaseExpression:
        # TODO test with CompFor etc.
        # TODO improve join test
        func_name = ensure_type(updated_node.func, Name).value
        if func_name not in self.builtins_imports:
            updated_node = Call(func=Name("list"), args=[Arg(updated_node)])
        return updated_node

    @m.visit(m.Call(func=m.Name("xrange")))
    def visit_xrange(self, node: Call) -> None:
        func_name = "range"
        if func_name not in self.builtins_imports:
            self.builtins_new_imports.add(func_name)

    @m.leave(m.Call(func=m.Name("xrange")))
    def fix_xrange(self, original_node: Call, updated_node: Call) -> BaseExpression:
        return updated_node.with_changes(func=Name("range"))

    iter_matcher = m.Call(
        func=m.Attribute(
            attr=m.Name("iterkeys") | m.Name("itervalues") | m.Name("iteritems")
        )
    )

    @m.visit(iter_matcher)
    def visit_iter(self, node: Call) -> None:
        func_name = ensure_type(node.func, Attribute).attr.value
        if func_name not in self.future_utils_imports:
            self.future_utils_new_imports.add(func_name)

    @m.leave(iter_matcher)
    def fix_iter(self, original_node: Call, updated_node: Call) -> BaseExpression:
        attribute = ensure_type(updated_node.func, Attribute)
        func_name = attribute.attr
        dict_name = attribute.value
        return updated_node.with_changes(func=func_name, args=[Arg(dict_name)])

    not_iter_matcher = m.Call(
        func=m.Attribute(attr=m.Name("keys") | m.Name("values") | m.Name("items"))
    )

    @m.call_if_not_inside(
        m.Call(func=m.Name("list") | m.Attribute(attr=m.Name("join"))) | m.CompFor()
    )
    @m.leave(not_iter_matcher)
    def fix_not_iter(self, original_node: Call, updated_node: Call) -> BaseExpression:
        updated_node = Call(func=Name("list"), args=[Arg(updated_node)])
        return updated_node

    @m.call_if_not_inside(m.Import() | m.ImportFrom())
    @m.leave(m.Name(value="unicode"))
    def fix_unicode(self, original_node: Name, updated_node: Name) -> BaseExpression:
        value = "text_type"
        if value not in self.future_utils_imports:
            self.future_utils_new_imports.add(value)
        return updated_node.with_changes(value=value)

    def leave_Module(self, original_node: Module, updated_node: Module) -> Module:
        updated_node = self.update_imports(
            original_node,
            updated_node,
            "builtins",
            self.builtins_updated_node,
            self.builtins_imports,
            self.builtins_new_imports,
            True,
        )
        updated_node = self.update_imports(
            original_node,
            updated_node,
            "future.utils",
            self.future_utils_updated_node,
            self.future_utils_imports,
            self.future_utils_new_imports,
            False,
        )
        return updated_node

    def update_imports(
        self,
        original_module: Module,
        updated_module: Module,
        import_name: str,
        updated_import_node: SimpleStatementLine,
        current_imports: Dict[str, str],
        new_imports: Set[str],
        noqa: bool,
    ) -> Module:
        if not new_imports:
            return updated_module
        noqa_comment = "  # noqa" if noqa else ""
        if not updated_import_node:
            i = -1
            blank_lines = "\n\n"
            if self.last_import_node_stmt:
                blank_lines = ""
                for i, (original, updated) in enumerate(
                    zip(original_module.body, updated_module.body)
                ):
                    if original is self.last_import_node_stmt:
                        break
            stmt = parse_module(
                f"from {import_name} import {', '.join(sorted(new_imports))}{noqa_comment}\n{blank_lines}",
                config=updated_module.config_for_parsing,
            )
            body = list(updated_module.body)
            self.last_import_node_stmt = stmt
            return updated_module.with_changes(
                body=body[: i + 1] + stmt.children + body[i + 1 :]
            )
        else:
            if "*" not in current_imports:
                current_imports_set = {
                    f"{k}" if k == v else f"{k} as {v}"
                    for k, v in current_imports.items()
                }
                stmt = parse_statement(
                    f"from {import_name} import {', '.join(sorted(new_imports | current_imports_set))}{noqa_comment}"
                )
                return updated_module.deep_replace(updated_import_node, stmt)
                # for i, (original, updated) in enumerate(
                #     zip(original_module.body, updated_module.body)
                # ):
                #     if original is original_import_node:
                #         body = list(updated_module.body)
                #         return updated_module.with_changes(
                #             body=body[:i] + [stmt] + body[i + 1 :]
                #         )
        return updated_module
