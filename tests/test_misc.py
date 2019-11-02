from tests.check import check_result


# def test_dict_01():
#     source = """
# def foo(d):
#     return d.keys() + d.values() + d.items()
# """
#     expected = """
# def foo(d):
#     return list(d.keys()) + list(d.values()) + list(d.items())
# """
#     check_result(source, expected)


# def test_dict_02():
#     source = """
# def foo(d):
#     return list(d.keys() + d.values() + d.items())
# """
#     expected = """
# def foo(d):
#     return list(d.keys() + d.values() + d.items())
# """
#     check_result(source, expected)


def test_param_01():
    source = """
def foo(
        i,  # type: int
):
    # type: (...) -> bool
    b, a, d = i > 2  # type: bool
    return b
"""
    expected = source
    check_result(source, expected)


def test_param_02():
    source = """
def foo(i):
    # type: (int) -> bool
    if not i:
        # boo!
        raise ValueError("i is nothing")
    
    return i > 2
"""
    expected = source
    check_result(source, expected)
