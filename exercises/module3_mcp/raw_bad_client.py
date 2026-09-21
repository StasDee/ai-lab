"""
To run:
    uv run exercises\\module3_mcp\\raw_bad_client.py
"""


import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).with_name("raw_bad_server.py"))],
)


async def call_tools():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("tools:", [t.name for t in (await session.list_tools()).tools])
            print("call:", (await session.call_tool("echo", {})).content)


asyncio.run(call_tools())