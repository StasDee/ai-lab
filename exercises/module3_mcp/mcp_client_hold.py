"""
To run:
    uv run exercises\\module3_mcp\\mcp_client_hold.py
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
    cwd=str(REPO),
)


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_last_failure_log", {"log_path": "reports/last_run.log"}
            )
            print("call ok:", result.content[0].text[:40].replace("\n", " "))
            print("holding the connection open for 90 seconds...", flush=True)
            await asyncio.sleep(90)
            print("disconnecting")


asyncio.run(main())