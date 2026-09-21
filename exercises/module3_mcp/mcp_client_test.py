"""Diagnostic: call run_pytest_suite over the real stdio MCP transport,
bypassing LM Studio entirely, to see whether the hang is in the server
or specific to LM Studio's own client.

To run:
    .venv\\Scripts\\python.exe exercises\\module3_mcp\\mcp_client_test.py
    uv run exercises\\module3_mcp\\mcp_client_test.py
"""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[2]

server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "ai_lab.mcp_server.tools_server"],
    cwd=str(REPO),  # relative paths like "tests/" now resolve against the repo root
)


async def call_tools():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("Negotiated protocol:", init.protocol_version)

            tools = await session.list_tools()
            print("Tools available:", [t.name for t in tools.tools])

            suite_result = await session.call_tool("run_pytest_suite", {"test_path": "tests/"})
            print("\nrun_pytest_suite result:")
            print(suite_result.content)

            log_result = await session.call_tool(
                "get_last_failure_log", {"log_path": "reports/last_run.log"}
            )
            print("\nget_last_failure_log result:")
            print(log_result.content)

            print("\nFull CallToolResult (step 3):")
            print(repr(log_result))
            print("is_error:", log_result.is_error)


asyncio.run(call_tools())
