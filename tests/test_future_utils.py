from tests.check import check_result


def test_01():
    source = """
def foo(s):
    if isinstance(s, unicode):
        return s.encode("utf-8")
"""
    expected = """
from future.utils import text_type


def foo(s):
    if isinstance(s, text_type):
        return s.encode("utf-8")
"""
    check_result(source, expected)


def test_02():
    source = """
def foo(s):
    if isinstance(s, unicode):
        return map(lambda c:c.encode("utf-8"), s)
"""
    expected = """
from builtins import map
from future.utils import text_type


def foo(s):
    if isinstance(s, text_type):
        return list(map(lambda c:c.encode("utf-8"), s))
"""
    check_result(source, expected)


def test_03():
    source = """
def foo(d):
    for k, v in d.iterkeys():
        print("{}={}".format(k, v))
"""
    expected = """
from future.utils import iterkeys


def foo(d):
    for k, v in iterkeys(d):
        print("{}={}".format(k, v))
"""
    check_result(source, expected)


def test_04():
    source = """
def foo(d):
    for k in d.iterkeys():
        print("{}".format(k))
    for k, v in d.iteritems():
        print("{}={}".format(k, v))
    for v in d.itervalues():
        print("={}".format(v))
"""
    expected = """
from future.utils import iteritems, iterkeys, itervalues


def foo(d):
    for k in iterkeys(d):
        print("{}".format(k))
    for k, v in iteritems(d):
        print("{}={}".format(k, v))
    for v in itervalues(d):
        print("={}".format(v))
"""
    check_result(source, expected)
