"""Sticky notes MCP server: save quick text notes to a file.

Run (PowerShell or cmd, not Git Bash):
    uv run python exercises/module3_mcp/sticky_mcp.py

Notes are stored in notes.txt next to this script, or in the file named by
the STICKY_NOTES_FILE environment variable.
Claude Desktop packaging steps: docs/notes/mcpb-packaging-steps.md
"""

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("AI Sticky Notes")

NOTES_FILE = Path(
    os.environ.get("STICKY_NOTES_FILE", Path(__file__).resolve().parent / "notes.txt")
)


def _read_notes() -> list[str]:
    """Return all non-empty notes, one per line. A missing file means no notes."""
    if not NOTES_FILE.exists():
        return []
    text = NOTES_FILE.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


@mcp.tool()
def add_note(message: str) -> str:
    """Append a note to the sticky notes file.

    Args:
        message: Text of the note. Line breaks are replaced with spaces so
            each note stays on one line.

    Returns:
        "Note saved" on success, or an error message if the note is empty.
    """
    message = " ".join(message.splitlines()).strip()
    if not message:
        return "Error: note is empty, nothing saved."
    with NOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(message + "\n")
    return "Note saved"


@mcp.tool()
def read_notes() -> str:
    """Return all saved notes, one per line, or "No notes yet." if there are none."""
    return "\n".join(_read_notes()) or "No notes yet."


@mcp.resource("notes://latest")
def get_latest_note() -> str:
    """Return the most recently added note, or "No notes yet." if there are none."""
    notes = _read_notes()
    return notes[-1] if notes else "No notes yet."


@mcp.prompt()
def note_summary_prompt() -> str:
    """Build a prompt that asks the model to summarize all current notes."""
    notes = _read_notes()
    if not notes:
        return "There are no notes yet."
    return "Summarize the current notes:\n" + "\n".join(notes)


if __name__ == "__main__":
    mcp.run(transport="stdio")
