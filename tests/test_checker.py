from pathlib import Path

import libcst as cst

from src.checker import Checker


def test_assertEquals_01():
    source = """
class MyTestCase(unittest.TestCase):
    def test_1():
        self.assertEquals(True, False)
"""
    module = cst.parse_module(source)
    wrapper = cst.MetadataWrapper(module)
    checker = Checker(Path("(test)"))
    wrapper.visit(checker)
    assert checker.errors


def test_assertEquals_02():
    source = """
def test_1():
    assertEquals(True, False)
"""
    module = cst.parse_module(source)
    wrapper = cst.MetadataWrapper(module)
    checker = Checker(Path("(test)"))
    wrapper.visit(checker)
    assert not checker.errors
