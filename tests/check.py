import difflib
from pathlib import Path

import libcst as cst

from src.modernizer import Modernizer


def check_result(source, expected):
    module = cst.parse_module(source)
    wrapper = cst.MetadataWrapper(module)
    modernizer = Modernizer(Path("(test)"))
    modified_tree = wrapper.visit(modernizer)
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(True),
            modified_tree.code.splitlines(True),
            fromfile="expected",
            tofile="actual",
        )
    )
    assert modified_tree.code == expected, diff
