"""A deliberately failing test: gives Module 1's benchmark script and the
capstone agent's run_pytest_suite / get_last_failure_log something real to
diagnose. Replace with your own project's tests once the workbook exercises
are done.
"""


def add(a, b):
    return a + b


def test_add_deliberately_wrong():
    # Intentionally wrong expectation so this test fails out of the box.
    assert add(2, 2) == 5


def test_addition():
    assert 1 + 1 == 2


def test_string_upper():
    assert "hello".upper() == "HELLO"


def test_list_length():
    assert len([1, 2, 3]) == 3


def test_this_one_fails_on_purpose():
    assert 2 + 2 == 5
