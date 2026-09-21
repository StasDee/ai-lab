"""MCP server exposing test-automation tools.

Run it directly (no file path needed once the package is installed):

    uv run python -m ai_lab.mcp_server.tools_server

Any MCP host can launch it the same way: LM Studio via mcp.json, or
ai_lab.agents.diagnostic_agent via stdio_client. The server has no idea
which one is talking to it, which is the whole point.

To run:
    .venv/Scripts/python.exe -m ai_lab.mcp_server.tools_server
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

# Where the project under diagnosis lives.
#
# This cannot be a bare relative path. An MCP host launches this file as a
# subprocess from whatever working directory it likes: LM Studio uses its
# own plugin sandbox folder, not your project root, so "demo_repo/" would
# silently resolve somewhere unexpected at runtime. Anchoring to __file__
# makes the default correct wherever the process is started from, and the
# env var gives CI (or anyone pointing this at a real codebase) a way to
# override it without editing code.
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # .../src/ai_lab
_PROJECT_ROOT = _PACKAGE_ROOT.parent.parent  # .../ai-lab

DEMO_REPO = Path(os.environ.get("AI_LAB_DEMO_REPO", _PROJECT_ROOT / "demo_repo"))
DEFAULT_TEST_PATH = DEMO_REPO / "tests"

print(f'---tests path: {str(DEFAULT_TEST_PATH)}', file=sys.stderr)
DEFAULT_LOG_PATH = DEMO_REPO / "reports" / "last_run.log"

PYTEST_TIMEOUT_SECONDS = 120

mcp = MCPServer("test-automation-tools")


@mcp.tool()
def run_pytest_suite(test_path: str = str(DEFAULT_TEST_PATH)) -> str:
    """Run the pytest suite at the given path and return its combined stdout
    and stderr, including full tracebacks for any failures.

    Use this to execute or re-run tests. Use get_last_failure_log instead if
    you only need to inspect a previous run's log without re-executing anything.

    Args:
        test_path: Path to the test directory or file, absolute or relative to
            the directory this server process was launched from.
            Defaults to "tests/". The run is terminated if it
            exceeds 120 seconds.
    """
    resolved_path = Path(test_path)
    if not resolved_path.is_absolute():
        resolved_path = _PROJECT_ROOT / resolved_path

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(resolved_path), "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=PYTEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return (
            f"Test run at {resolved_path} exceeded the "
            f"{PYTEST_TIMEOUT_SECONDS}s timeout and was terminated after {elapsed:.1f}s."
        )
    elapsed = time.time() - start
    return f"[Completed in {elapsed:.1f}s]\n" + result.stdout + result.stderr


@mcp.tool()
def get_last_failure_log(log_path: str = str(DEFAULT_LOG_PATH)) -> str:
    """Return the contents of the most recent test failure log, without
    re-running any tests.

    Use this to inspect a previous run's output. Use run_pytest_suite instead
    if you need current results. If no file exists at log_path, returns the message
    "No failure log found at that path" instead of raising an error.

    Args:
        log_path: Path to the log file, relative to the directory
            this server process was launched from. Defaults to
            "reports/last_run.log".
    """
    try:
        with open(log_path, "r") as f:
            return f.read()[:6000]
    except FileNotFoundError:
        return "No failure log found at that path."


if __name__ == "__main__":
    mcp.run(transport="stdio")
