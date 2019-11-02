import os
import sys

from tests.check import check_result

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


def test_map_01():
    source = """
def foo():
    results = [1, 2, 3]
    return map(lambda i: i * 2, results)
"""
    expected = """
from builtins import map


def foo():
    results = [1, 2, 3]
    return list(map(lambda i: i * 2, results))
"""
    check_result(source, expected)


def test_map_02():
    source = """
def foo():
    results = [1, 2, 3]
    return map(lambda i: i * 2, results)  # comment
"""
    expected = """
from builtins import map


def foo():
    results = [1, 2, 3]
    return list(map(lambda i: i * 2, results))  # comment
"""
    check_result(source, expected)


def test_map_03():
    source = """
from builtins import map


def foo():
    results = [1, 2, 3]
    return map(lambda i: i * 2, results)
"""
    expected = """
from builtins import map


def foo():
    results = [1, 2, 3]
    return map(lambda i: i * 2, results)
"""
    check_result(source, expected)


def test_map_04():
    source = """
import os
import re


def foo():
    results = [1, 2, 3]
    return map(lambda i: i * 2, results)
"""
    expected = """
import os
import re
from builtins import map


def foo():
    results = [1, 2, 3]
    return list(map(lambda i: i * 2, results))
"""
    check_result(source, expected)


def test_map_05():
    source = """
from builtins import str as unicode


def foo():
    results = [1, 2, 3]
    return map(lambda i: i * 2, results)
"""
    expected = """
from builtins import map, str as unicode


def foo():
    results = [1, 2, 3]
    return list(map(lambda i: i * 2, results))
"""
    check_result(source, expected)


def test_map_06():
    source = """
print(foo.map())
"""
    expected = """
print(foo.map())
"""
    check_result(source, expected)


def test_range_01():
    source = """
print(range(5))
"""
    expected = """
from builtins import range


print(list(range(5)))
"""
    check_result(source, expected)


def test_xrange_01():
    source = """
print(list(xrange(5)))
for i in xrange(4):
    print(i)
"""
    expected = """
from builtins import range


print(list(range(5)))
for i in range(4):
    print(i)
"""
    check_result(source, expected)
