"""
To run:
    uv run exercises\\module3_mcp\\mcp_client_timed.py
"""

import asyncio
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[2]

server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "ai_lab.mcp_server.tools_server"],
    cwd=str(REPO),
)


async def call_tools_timed():
    start = time.perf_counter()
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            connected = time.perf_counter()

            await session.call_tool("run_pytest_suite", {"test_path": "tests/"})
            called = time.perf_counter()

            await session.call_tool(
                "get_last_failure_log", {"log_path": "reports/last_run.log"}
            )
            called_again = time.perf_counter()
    closed = time.perf_counter()
    print(f"Connection + handshake: {connected - start:.3f}s")
    print(f"Tool call itself: {called - connected:.3f}s")
    print(f"Second call, same session: {called_again - called:.3f}s")
    print(f"Shutdown: {closed - called_again:.3f}s")


asyncio.run(call_tools_timed())
