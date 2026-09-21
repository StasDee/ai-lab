# Module 3: MCP & Real Test Tooling
### Round 1, Week 3

## Why This Module

Module 2's tools lived inside your program only: nobody else could use `run_shell` without copying your code. MCP is the standard that turns a tool into something any compatible agent can use, including tools the QA industry has already built for you, like Playwright MCP.

---

## 3.1 What MCP Actually Solves

Before a shared protocol, every agent framework needed custom integration code for every tool it wanted to use: N agents times M tools means N×M integrations. MCP standardizes the interface: a **server** exposes tools/resources/prompts over a defined protocol, and any **host** that speaks MCP can use any server with zero custom glue code.

Contrast with your Module 2 `DISPATCH` dict: that only existed inside your script. An MCP server exists independently: your agent, Claude Desktop, Cursor, or LM Studio can all use the same one.

## 3.2 The Three Roles

- **Host**: the application the user interacts with (LM Studio, Claude Desktop, your own agent code)
- **Client**: the connector inside the host that talks to one specific server
- **Server**: the program exposing tools/resources/prompts (Playwright MCP, or the one you'll write below)

## 3.3 Transports

- **stdio**: the server runs as a local subprocess. Simple, no network exposure. Default choice for local dev tools.
- **HTTP / streamable-http**: for remote or shared servers, e.g. one running as a persistent service for a whole team.

This module sticks to stdio: right choice for a local, single-user tool.

## 3.4 Using an Existing Server: Playwright MCP

Microsoft's Playwright MCP drives a real browser through the accessibility tree (structured DOM data) rather than screenshots, faster and more deterministic than computer-vision approaches, and it can generate runnable Playwright test code directly from an agent session.

Add it to LM Studio via `mcp.json` (Program tab → Install → Edit mcp.json):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Try one simple action through your local model: "navigate to example.com and tell me the page title."

## 3.5 Writing Your Own MCP Server

Use the official Python `mcp` SDK. This exposes two test-automation tools your capstone will use directly.

> The SDK's exact API surface can shift between releases: if the import paths below don't match what you have installed, check the current docs linked at the end of this module.

```python
from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("test-automation-tools")

@mcp.tool()
def run_pytest_suite(test_path: str = "tests/") -> str:
    """Run the pytest suite at the given path and return the raw output.

    Args:
        test_path: Relative path to the test directory or file.
    """
    result = subprocess.run(
        ["pytest", test_path, "--tb=short", "-q"],
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout + result.stderr

@mcp.tool()
def get_last_failure_log(log_path: str = "reports/last_run.log") -> str:
    """Return the contents of the most recent test failure log.

    Args:
        log_path: Relative path to the log file.
    """
    try:
        with open(log_path, "r") as f:
            return f.read()[:6000]
    except FileNotFoundError:
        return "No failure log found at that path."

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Register it in `mcp.json` pointing at this script, connect it in LM Studio, and confirm your local model can call `run_pytest_suite` end-to-end.

## 3.6 Calling Your MCP Server From Your Own Agent

LM Studio's UI is fine for testing, but your Module 4 capstone needs your *own* agent code calling this server directly, not routed through LM Studio's chat window.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["tools_server.py"],
)

async def call_tool():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            result = await session.call_tool("run_pytest_suite", {"test_path": "tests/"})
            print(result.content)

asyncio.run(call_tool())
```

This is the piece that turns your MCP server from "something LM Studio can use" into "something your own agent loop can call": you'll wire this directly into Module 2's loop shape in the capstone.

## 3.7 Schema Design, Higher Stakes Now

Module 2 already flagged tool descriptions as a reliability lever. With MCP, your schema gets reused across contexts you don't control: a vague `run_pytest_suite` description works fine when you wrote the calling code yourself, and fails silently when a different agent or teammate tries to use your server without your mental model of it. Write descriptions as if a stranger has to use the tool correctly with zero other context.

---

## Exercise

- [ ] Install Playwright MCP, connect it via LM Studio, drive one browser action
- [ ] Write your own MCP server exposing `run_pytest_suite` and `get_last_failure_log`
- [ ] Connect to your own server from Python code directly (not just LM Studio's UI) and call both tools end-to-end

## Self-Check

- What specifically does MCP solve that your Module 2 `DISPATCH` dict didn't?
- Why does stdio make sense here but not for a tool shared across a team?
- If you handed your MCP server to a teammate with zero context, would your tool descriptions be enough for them to use it correctly?

## External Links

- MCP official docs/spec: https://modelcontextprotocol.io
- Python MCP SDK: https://github.com/modelcontextprotocol/python-sdk
- Playwright MCP: https://github.com/microsoft/playwright-mcp
- LM Studio MCP docs: https://lmstudio.ai/docs/app/mcp

---

**Next:** Module 4, Capstone & CV Polish. Everything so far becomes one project.
