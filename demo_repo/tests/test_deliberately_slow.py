import time


def test_deliberately_slow():
    """Exists only to trigger run_pytest_suite's 120s timeout guard.
    Point run_pytest_suite at this file specifically
    (test_path="demo_repo/tests/test_deliberately_slow.py").
    Do not include this file's directory in a normal test run.
    """
    time.sleep(150)
    assert True
