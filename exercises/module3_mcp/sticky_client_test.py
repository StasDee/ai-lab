"""Client for sticky_mcp.py: add a note, read it back, verify it round-trips.

Run (PowerShell or cmd, not Git Bash):
    uv run python exercises/module3_mcp/sticky_client_test.py

Expected output:
    tools: ['add_note', 'read_notes']
    PASS
Uses a temporary notes file, so the real notes.txt is never touched.
Any failure raises AssertionError with the actual server output.
"""

import asyncio
import sys
import tempfile
import uuid
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("sticky_mcp.py")


async def main(notes_file: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env={"STICKY_NOTES_FILE": str(notes_file)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("tools:", names)
            assert names == ["add_note", "read_notes"], names

            marker = f"note-{uuid.uuid4().hex[:8]}"
            added = await session.call_tool("add_note", {"message": marker})
            assert not added.is_error, added.content

            result = await session.call_tool("read_notes", {})
            text = result.content[0].text
            assert marker in text, text

    print("PASS")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        asyncio.run(main(Path(tmp) / "notes.txt"))
