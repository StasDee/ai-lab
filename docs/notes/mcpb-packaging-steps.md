# Packaging a Python MCP server as a Claude Desktop extension (.mcpb)

Reference for repeating this later. Written after doing it once, live, against
`another_mcp_server.py` (now at `exercises/module3_mcp/another_mcp_server.py`,
not `src/ai_lab/mcp_server/`: adjust the path below to wherever the script
you're packaging actually lives).

Paths in this document are examples from the author's machine; adjust the
drive and folder names.

## 0. Before you start

Don't run any of this from the `ai-lab` project root. `mcpb pack` zips up the
current directory, and packing the whole repo (`.venv`, `.git`, everything)
is not what you want. Build in a small, separate folder instead.

## 1. Install the mcpb CLI (once per machine)

```powershell
npm install -g @anthropic-ai/mcpb
```

This is a Node.js tool, unrelated to the project's own `.venv` or `uv`.
Needs Node/npm on the machine, nothing else.

## 2. Set up a dedicated bundle folder

```powershell
mkdir P:\CodingWorkspace\<bundle-name>
mkdir P:\CodingWorkspace\<bundle-name>\server
copy P:\CodingWorkspace\ai-lab\src\ai_lab\mcp_server\<script>.py P:\CodingWorkspace\<bundle-name>\server\
cd P:\CodingWorkspace\<bundle-name>
```

One script per bundle, copied in, not symlinked or referenced in place.

## 3. Confirm the script actually starts the server

This is the step most likely to get skipped, and the one that caused the
"Server disconnected" error the first time through. A script that only
defines `mcp = MCPServer(...)` plus some `@mcp.tool()` functions and stops
there will import cleanly and exit immediately when launched as a plain
`python script.py` subprocess, nothing runs the stdio loop.

Check the bottom of the file for:

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

If it's missing, add it before packaging. (`mcp dev` / `mcp run` don't need
this, since they call `.run()` for you. A packaged extension launches the
script directly, so it does need it.)

## 4. Run mcpb init

```powershell
mcpb init
```

Answer name, version, description, author as plain text, none of it affects
whether the server runs.

**Check the generated `server.type` before moving on.** It has defaulted to
a Node.js template before even for a folder containing only a `.py` file.
If `type` isn't `"python"`, or `entry_point` doesn't point at the real
script, fix it now rather than after packing.

## 5. Fix manifest.json by hand

Open `manifest.json` and get the `server` block to look like this:

```json
"server": {
  "type": "python",
  "entry_point": "server/<script>.py",
  "mcp_config": {
    "command": "P:\\CodingWorkspace\\ai-lab\\.venv\\Scripts\\python.exe",
    "args": [
      "${__dirname}/server/<script>.py"
    ],
    "env": {}
  }
}
```

Two things worth getting right:

- `command` needs to be the actual venv Python that has `mcp` installed,
  not a bare `"python"`. Same reasoning as every other subprocess launch
  in this project: a bare command name depends on whatever `PATH`
  Claude Desktop's own process happens to have, which isn't guaranteed
  to resolve to the right interpreter.
- Windows paths in JSON need doubled backslashes (`\\`), a single
  backslash is read as an escape sequence and corrupts the path silently.

Leave `${__dirname}` alone, Claude Desktop fills that in at install time to
wherever it actually unpacks the bundle.

## 6. Pack it

Only needed once the tool set actually feels done. Still adding tools?
Skip straight to step 7's unpacked option instead, no need to pack yet.

```powershell
mcpb pack . <bundle-name>.mcpb
```

Expect "Manifest schema validation passes!" and a file listing showing
`manifest.json` plus the one server script, nothing else. Re-running this
after edits just overwrites the output, no extra flag needed.

## 7. Install in Claude Desktop

Two ways in, depending on where the server actually is.

**Still actively adding tools:** skip packing entirely. In Settings >
Extensions > Advanced settings > Extension Developer, click "Install
unpacked extension" and select the bundle *folder* (the one with
`manifest.json` and `server/` in it), not a file. Claude Desktop reads
straight from the folder, so there's no repack step each time the script
changes, just the restart below.

**Tool set is done, want a real `.mcpb` to keep or hand to someone else:**
use the packed file from step 6, Extension Developer > "Install
Extension…", select the `.mcpb`.

**Either way, restart Claude Desktop fully after any change to the
server's tools.** Confirmed as a known, currently open limitation, not
something specific to this setup: there is no way to refresh a server's
tool list without a full app restart, not even starting a new
conversation picks it up.

**Re-installing an already-packed extension after a fix:** remove the
existing one first (Settings > Extensions, find it, remove). Claude
Desktop doesn't reliably notice the underlying file changed on its own.

## 8. Test it

Ask Claude Desktop to use one of the server's actual tools by name, and
check the result is real, computed output, not a generic reply or an
error. If it shows "Server disconnected" instead, Settings > Extensions >
Advanced settings > Extension Developer, or the Developer settings panel
under the Desktop app, shows connection status and logs, check there
before guessing.

## Gotchas hit doing this the first time

- `mcpb pack` run from the wrong directory bundles far more than intended.
- `mcpb init` can generate a Node.js-shaped manifest for a Python script.
- A bare `"python"`/`"node"` command in `mcp_config` depends on luck.
- Missing `mcp.run(transport="stdio")` looks identical to a broken path,
  from Claude Desktop's side both just show "Server disconnected."
- Single backslashes in a Windows path inside JSON break silently.
- Reinstalling requires removing the old extension first.
- No live refresh: a full Claude Desktop restart is required to pick up
  any change to a server's tools, packed or unpacked.

## Sticky notes bundle walkthrough

Worked example specific to `sticky_mcp.py`, first done following
https://www.youtube.com/watch?v=-8k9lGpGQ6g&t=923s. Fills in the concrete
values the general steps above leave as placeholders.

```powershell
npm install -g @anthropic-ai/mcpb
mkdir P:\CodingWorkspace\sticky-mcp-bundle
mkdir P:\CodingWorkspace\sticky-mcp-bundle\server
copy exercises\module3_mcp\sticky_mcp.py P:\CodingWorkspace\sticky-mcp-bundle\server\
cd P:\CodingWorkspace\sticky-mcp-bundle
mcpb init
```

`mcpb init` answers used for this bundle:

- Extension name: (sticky-mcp-bundle) - accept default
- Author name: Stas
- Display name (optional): (sticky-mcp-bundle) - accept default
- Version: (1.0.0) - accept default, or change
- Description: sticky notes MCP server: save quick text notes to a file
- Add a detailed long description? (y/N) - skip
- Author email (optional): - skip
- Author url (optional): skip
- Homepage URL (optional): skip
- Documentation URL (optional): skip
- Support URL (optional): skip
- Icon file path (optional): skip
- Add theme/size-specific icons array? (y/N) - skip
- Add screenshots? (y/N) - skip
- Server type: choose Python
- Entry point: (server/main.py) - server/sticky_mcp.py
- Does your MCP Server provide tools you want to advertise (optional)? (Y/n) - n
- Tool description (optional): Saves a text note to the sticky notes file
- Add another tool? N
- Does your server generate additional tools at runtime? N
- Does your MCP Server provide prompts you want to advertise (optional)? N
- Add compatibility constraints? (y/N) N
- Add user-configurable options? (y/N) N
- Keywords (comma-separated, optional): - skip
- License: (MIT) - skip
- Add repository information? (y/N) - N

In this bundle's `manifest.json`, besides fixing `command` as in step 5
above, set `"env": {}`: a `"PYTHONPATH": "${__dirname}/server/lib"` entry
does not apply here, there is no `server/lib` for this bundle.

The bundle copy writes notes.txt next to itself
(sticky-mcp-bundle\server\notes.txt) unless the manifest server block sets
env STICKY_NOTES_FILE to another path.

Testing this specific bundle in Claude Desktop:

1. Use the `add_note` tool to save a note saying "testing from Claude
   Desktop". Confirm it landed:
   `type P:\CodingWorkspace\sticky-mcp-bundle\server\notes.txt`.
2. After changing the code: copy the updated script over the bundle's copy
   (`copy exercises\module3_mcp\sticky_mcp.py P:\CodingWorkspace\sticky-mcp-bundle\server\ -Force`),
   reinstall as in step 7's "Re-installing" note above, restart Claude
   Desktop fully, then use the `read_notes` tool to show all notes and
   confirm what's actually new.
