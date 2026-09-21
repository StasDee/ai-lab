"""Tests for the MCP tools themselves.

These call the tool functions directly rather than over MCP. The protocol
round trip is Day 13's concern; what matters here is that each tool behaves
correctly on its own, including on the failure paths, which is exactly the
part that's easy to get wrong and never notice.
"""

from ai_lab.mcp_server import tools_server


def test_demo_repo_defaults_exist():
    """The tools' defaults must point at files that are actually there."""
    assert tools_server.DEFAULT_TEST_PATH.is_dir()
    assert tools_server.DEFAULT_LOG_PATH.is_file()


def test_get_last_failure_log_reads_the_log():
    result = tools_server.get_last_failure_log()
    assert "FAILURES" in result


def test_get_last_failure_log_handles_missing_file():
    """A missing log is an expected case, not a crash."""
    result = tools_server.get_last_failure_log("does/not/exist.log")
    assert result == "No failure log found at that path."


def test_get_last_failure_log_caps_output():
    """Tool results re-enter the model's context, so they stay bounded."""
    assert len(tools_server.get_last_failure_log()) <= 6000
