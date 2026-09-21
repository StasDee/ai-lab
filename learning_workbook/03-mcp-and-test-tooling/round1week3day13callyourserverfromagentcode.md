---
title: "Day 13"
pagetitle: "Module 3, Day 13: Call Your Server From Your Own Agent Code"
---

# Module 3, Day 13: Call Your Server From Your Own Agent Code

*~1-1.5 hrs | Difficulty: Intermediate*

::: tldr
**TL;DR:** LM Studio has been quietly playing the client role for you since Day 11. Today you write that code yourself: a standalone Python script that launches `test_tools_server.py` as a subprocess, speaks the exact newline-delimited JSON-RPC from Day 10 over its stdin/stdout pipes, and calls both of your tools without LM Studio anywhere in the loop. This is the single piece of code that turns “I used an MCP server through a chat UI” into “I built a system that talks to MCP servers”, and it’s the literal client-side code your Module 4 capstone runs, unmodified.
:::

## Objective

::: objective
By the end of today you have a working `mcp_client_test.py` that connects to your own server, lists its tools, and calls both of them, entirely in code you wrote and control. You can describe, precisely, what happens at the operating-system level between your script and the server subprocess, using the actual wire format (not a hand-wavy “they talk to each other”).
:::

::: note
**Project note (mcp 2.2.0, restructured repo).** This lesson was written against mcp 1.x and the pre-restructure file layout. Wherever it says `test_tools_server.py`, your server is `src/ai_lab/mcp_server/tools_server.py`, launched as a module: `python -m ai_lab.mcp_server.tools_server`. The code in Theory Section 2 and in Practice uses those names. On mcp 2.x, attributes on MCP tool and result objects are snake_case in Python (`input_schema`, `is_error`), while the JSON on the wire stays camelCase. Run scripts with `uv run python <file>` from PowerShell or cmd, never Git Bash (MinTTY breaks asyncio subprocess creation on Windows). If an import or attribute looks unfamiliar, check the v1 to v2 migration guide before assuming a new bug: https://py.sdk.modelcontextprotocol.io/v2/migration/
:::

## Theory

### 1. Why LM Studio’s UI stops being enough

Everything through Day 12 has routed through LM Studio: it launched your server, ran the handshake, listed your tools, and dispatched your tool calls, all behind a chat window you never had to write code for. That’s genuinely useful for testing and exploration, which is exactly why Day 11 and Day 12 used it. But your Module 4 capstone is not a chat window: it’s `capstone_agent.py`, a script that needs to programmatically decide when to call a tool, feed the result back into a reasoning loop, and keep going without a human clicking anything. LM Studio’s UI has no API for “run this exact tool-calling loop unattended”: that capability has to live in code you write, which is precisely what today produces.

### 2. The pieces: `StdioServerParameters`, `stdio_client`, `ClientSession`

The official Python SDK gives you three building blocks that map directly onto the mechanics you’ve already learned:

```python
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

Mapped onto what you already know:

- `StdioServerParameters(command=<venv python>, args=["-m", "ai_lab.mcp_server.tools_server"])` is exactly `mcp.json`’s `"command"` and `"args"` fields from Day 11 and Day 12: the same subprocess launch specification, just now living in your Python code instead of a config file LM Studio reads. Nothing about how the server is started changed; only who’s doing the starting. The one extra field is `cwd`, the server’s working directory, so relative paths like `tests/` resolve against your repo root.
- `stdio_client(server_params)` is what actually spawns that subprocess and opens the stdin/stdout pipes to it. It hands back `(read, write)`, two asyncio stream objects, which are your code’s direct handle onto the exact newline-delimited JSON-RPC pipes Day 10 described in the abstract.
- `ClientSession(read, write)` wraps those raw streams with the actual protocol logic: message framing, matching responses to requests by `id`, and the `initialize` / `tools/list` / `tools/call` methods as ordinary Python calls. This object is the “client” role from Day 10’s table, made concrete: it’s the connector, living inside your script (which is now the host), maintaining one connection to one server.
- `await session.initialize()` performs the exact handshake from Day 10 Section 4: the request/response pair with `protocolVersion` and `capabilities` you saw as raw JSON is happening here, just wrapped in a method call so you never have to construct that JSON by hand.
- `await session.list_tools()` sends the `tools/list` request and gives you back the tool schemas your `@mcp.tool()` decorators generated on Day 12: `tools.tools` is a list of objects with `.name`, `.description`, and `.input_schema` (`.inputSchema` on the 1.x SDK; mcp 2.x uses snake_case attribute names while the JSON on the wire stays camelCase), the same fields Module 4’s `diagnose_failure()` function converts into the OpenAI `tools=[...]` shape.
- `await session.call_tool("run_pytest_suite", {"test_path": "tests/"})` sends the `tools/call` request and returns the result: the same `content` / `isError` shape from Day 10’s JSON examples (`is_error` on the Python object in mcp 2.x), now as a Python object instead of a dict you’d have to parse yourself.

#### 2.1 Running this alongside LM Studio: two subprocesses, not one shared server

It’s natural to assume that if LM Studio is already connected to `test_tools_server.py` via Day 12’s `mcp.json`, and you now also run `mcp_client_test.py`, both are talking to the same running server. They aren’t. Every call to `stdio_client()` (LM Studio’s internal one, and yours) launches its own, independent subprocess. If both happen to be running at once, you have two entirely separate Python processes on your machine, each with its own copy of `test_tools_server.py` loaded into memory, each with its own private stdin/stdout pipes, neither aware the other exists.

This follows directly from Day 10’s 1:1 client-to-server rule, made concrete: a client’s “one server” really means “one subprocess that client personally started,” not a shared, addressable instance other clients can also attach to. There’s no coordination, no shared state, and no locking between the two: if that ever matters (two tool calls racing to write the same file, say), it’s something you’d have to build yourself, not something MCP gives you for free.

If your actual goal is “one running server instance that multiple clients genuinely share,” that requirement is itself the signal you’ve outgrown stdio: it’s exactly the case Day 11’s stdio-vs-HTTP diagram drew a line around. Streamable HTTP’s one-shared-service model exists precisely for this, at the cost of the session handling and network exposure stdio lets you skip entirely.

### 3. Why async/await shows up here at all

If you haven’t written much asyncio code yet, the `async with` / `await` pattern above can look like ceremony for its own sake. It isn’t: it’s a direct consequence of what’s actually happening: your script and the server subprocess are two independent processes communicating over pipes, and writing to or reading from those pipes takes real, unpredictable time (the server has to actually run pytest, actually read a file). `async` / `await` is Python’s mechanism for saying “this specific operation might take a while: don’t block the rest of the program while you wait for it.” The two nested `async with` blocks are async context managers: they guarantee the subprocess gets cleanly started when you enter the block and cleanly terminated when you leave it (or if an exception interrupts you), the same safety guarantee a plain `with open(...) as f:` gives you for files, just extended to cover a whole subprocess and its open pipes instead of one file handle.

### 4. What’s actually happening on the wire, this time for real

Day 10 showed you the JSON-RPC message shapes; Day 13 is where you can point at the actual bytes. When `stdio_client` spawns `test_tools_server.py`, your script becomes the parent process and the server becomes a child process, connected by two pipes the operating system sets up for you:

![Diagram: what stdio_client actually wires together](diagrams/day13-stdio-wiring.png)

The MCP specification is precise about this transport, and it’s worth knowing the exact rule rather than an approximation: messages are **newline-delimited JSON** (one complete JSON-RPC object per line, with no embedded newlines inside a message) written to the child’s stdin by the client and read from the child’s stdout by the client. If you added a `print()` statement inside `test_tools_server.py` for debugging, it would corrupt this stream, because anything the server writes to stdout that isn’t a valid MCP message breaks the framing for everything after it: this is exactly why the spec reserves **stderr**, not stdout, for a server’s own logging. If you ever need to debug your own `test_tools_server.py`, reach for `print(..., file=sys.stderr)`, never a bare `print()`.

::: note
**Version note (mcp 2.x).** The rule above still describes the protocol, but the 2.x SDK adds a guard on the server side: while an `MCPServer` is serving over stdio, its stdout is pointed at stderr and protocol messages travel through a private copy of the original stdout. A stray `print()` in tool code therefore lands on stderr, where `stdio_client` passes it through to your terminal, instead of on the wire. The guard only covers servers built on the SDK’s stdio transport, which is why Practice step 4 has you break the rule twice: once against your real server, and once against a hand-written one that has no guard.
:::

### 5. The role flip, made literal

> Look back at Day 10’s Section 2.1 callout: “By Day 16, your own `capstone_agent.py` has become the host.” Today’s `mcp_client_test.py` is that exact transition happening one day early, in miniature. The moment your own Python script holds a live `ClientSession`, your script is the host, and the connector object inside it is the client: LM Studio is no longer anywhere in the picture. Day 10’s diagram of “one host, two clients, two servers” wasn’t a hypothetical; it’s what your own machine looks like by the end of today, minus LM Studio’s UI layered on top.

## Practice {.pagebreak}

Before working through the checks below: use the same `tests/` and `reports/last_run.log` fixtures you built on Day 12. This exercise reuses them; there’s nothing new to set up.

1. **Write `mcp_client_test.py`** using Section 2’s code as your starting point, pointed at your actual `test_tools_server.py` from Day 12: extended to call both tools, not just one. Section 2’s snippet is deliberately minimal to teach the three building blocks; here’s the complete version to actually build:

    ```python
    import asyncio
    import sys
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    PYTHON = sys.executable
    REPO = Path(__file__).resolve().parents[2]

    server_params = StdioServerParameters(
        command=PYTHON,
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
    ```

2. **Run it and confirm `list_tools()` reports both tools** (`run_pytest_suite` and `get_last_failure_log`) with no LM Studio process running at all. This is your proof that the server never depended on LM Studio specifically. Run `uv run python mcp_client_test.py`. Expect the first two lines close to:

    ```
    Negotiated protocol: 2025-11-25
    Tools available: ['run_pytest_suite', 'get_last_failure_log']
    ```

    The protocol string is whatever your installed SDK negotiates; check it yourself rather than assuming it from this page.

3. **Call both tools from your script and print the results.** Compare the `result.content` shape you see here against the raw JSON `result.content` array from Day 10’s Section 3: same structure, now accessed as Python objects. On the current SDK, expect something close to:

    ```
    run_pytest_suite result:
    [TextContent(type='text', text='.F                                                                       [100%]\n=================================== FAILURES ===================================\n...\n1 failed, 3 passed in 0.03s\n', annotations=None, meta=None)]

    get_last_failure_log result:
    [TextContent(type='text', text='============================= FAILURES =============================\n...\n1 failed, 3 passed in 0.04s', annotations=None, meta=None)]
    ```

    (Field names on `TextContent` can differ slightly between SDK versions: check `pip show mcp` if your output doesn’t match, the same instinct Day 12 taught you for import paths.)

    The last lines of the Step 1 script print the whole result object, and on mcp 2.x it carries more than Day 10’s example. Expect `CallToolResult(meta=None, content=[TextContent(...)], structured_content={'result': '...'}, is_error=False, result_type='complete')`. Three differences from the raw JSON: Python attribute names are snake_case (`result.is_error`; `result.isError` raises `AttributeError`), while the JSON on the wire keeps `isError`; the wire JSON also carries `structuredContent`, which repeats the text because your tools return `str`; and `content` is the field to read.

4. **Deliberately corrupt the pipe, on purpose, to see Section 4’s rule in action.** Add `print("debugging", flush=True)` at the top of `get_last_failure_log`’s body in your server. The `flush=True` matters here: a plain `print()` can sit in Python’s output buffer when stdout is a pipe rather than a terminal, and may never actually reach the stream in a short-lived script, that’s a real, separate thing worth knowing, not just a formality for this exercise.

    Before rerunning, add this line near the top of your client script, temporarily:

    ```python
    import logging
    logging.basicConfig(level=logging.ERROR)
    ```

    Rerun your client and call `get_last_failure_log`. On mcp 2.2.0 this does not corrupt the stream, and that is the result to record: your printed result is correct, there is no `ERROR:` line and no `ValidationError`, and the word `debugging` appears on its own line in your terminal. That is the guard from the Section 4 version note at work: your `print()` went to stderr, not to the wire. (Checked on Linux. The SDK has Windows-specific handle handling for the same mechanism, so your own terminal is the observation to write down.) Then undo the edits: run `git restore src/ai_lab/mcp_server/tools_server.py` and delete the two temporary logging lines.

    To see the rule actually broken, take the SDK’s guard out of the picture. `raw_bad_server.py` is a hand-written server that prints `debugging` to the real stdout during the handshake, and `raw_bad_client.py` connects to it. Create both next to your client script:

    **`raw_bad_server.py`**

    ```python
    import json
    import sys

    # A hand-written server with none of the SDK's stdout protection.
    for line in sys.stdin:
        msg = json.loads(line)
        method, msg_id = msg.get("method"), msg.get("id")
        if method == "initialize":
            print("debugging", flush=True)  # stray text on the real stdout
            result = {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "raw-bad", "version": "0"},
            }
        elif method == "tools/list":
            result = {"tools": [{"name": "echo", "inputSchema": {"type": "object", "properties": {}}}]}
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": "pong"}], "isError": False}
        else:
            continue  # notifications get no reply
        print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
    ```

    **`raw_bad_client.py`**

    ```python
    import asyncio
    import sys
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    PYTHON = sys.executable

    params = StdioServerParameters(
        command=PYTHON,
        args=[str(Path(__file__).with_name("raw_bad_server.py"))],
    )


    async def main():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("tools:", [t.name for t in (await session.list_tools()).tools])
                print("call:", (await session.call_tool("echo", {})).content)


    asyncio.run(main())
    ```

    Run `uv run python raw_bad_client.py`. Expect the script to finish normally and print `tools: ['echo']` and `call: [TextContent(type='text', text='pong', annotations=None, meta=None)]`, while your terminal also shows something like:

    ```
    Failed to parse JSONRPC message from server
    Traceback (most recent call last):
    ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for union[JSONRPCRequest,JSONRPCNotification,JSONRPCResponse,JSONRPCError]
      Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='debugging', input_type=str]
    ```

    Sit with what this actually shows: the corruption is real (the debug text landed on the wire as a bogus protocol message) but it didn’t crash your script, and the tool result you can see still came back fine. That’s arguably worse than a loud crash: a stray `print()` produces a logged parse failure that is easy to skim past among other terminal output. It appears even without the temporary logging lines, because Python prints ERROR-level log records to stderr when logging is unconfigured; `basicConfig` only adds an `ERROR:mcp.client.stdio:` prefix. The error also names a union of the four JSON-RPC message types, where older SDK versions named `JSONRPCMessage`. Exact behavior can vary by SDK version; this is what mcp 2.2.0 did. Remove the `print()` and the temporary logging line once you’ve seen it.

5. **Time the full round trip for a `call_tool()` invocation**, the same instinct Day 4 taught you for model latency. Is most of the time spent in subprocess startup (once, at connection time) or in the tool call itself? Add timing around the same three points, plus a second call in the same session and the shutdown. Save this as `mcp_client_timed.py` next to your client script:

    ```python
    import asyncio
    import sys
    import time
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    PYTHON = sys.executable
    REPO = Path(__file__).resolve().parents[2]

    server_params = StdioServerParameters(
        command=PYTHON,
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

        print(f"Connection + handshake:    {connected - start:.3f}s")
        print(f"Tool call itself:          {called - connected:.3f}s")
        print(f"Second call, same session: {called_again - called:.3f}s")
        print(f"Shutdown:                  {closed - called_again:.3f}s")


    asyncio.run(call_tools_timed())
    ```

    Run `uv run python mcp_client_timed.py` three times. On one ordinary machine, three runs of the first two lines looked like:

    ```
    Connection + handshake: 0.402s
    Tool call itself:       0.278s
    ```

    Your own numbers will differ, but the pattern is the point: connection + handshake is a roughly fixed cost per connection (spawning a Python process and completing the initialize round trip), while the tool call’s cost tracks what the tool actually does. This distinction matters the moment your Module 4 loop starts making several tool calls per diagnostic session: the fixed cost is paid once per session, not once per call.

    The second call shows it directly. On a Linux test machine with mcp 2.2.0, three runs printed a connection + handshake of 0.71 to 0.75s, a first tool call of about 0.32s, a second call in the same session of 0.003s, and a shutdown of about 0.10s. A correct result on your machine has a stable connection cost across the three runs and a second call that is far cheaper than the first.

<div class="pagebreak"></div>

6. **Run your script while LM Studio is also connected to the same `test_tools_server.py` from Day 12.** Confirm both work independently, then count how many `test_tools_server.py` processes are actually running. Your client exits in under a second, so it has to hold its connection open long enough to overlap with LM Studio’s. Create `mcp_client_hold.py` next to your client script:

    ```python
    import asyncio
    import sys
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    PYTHON = sys.executable
    REPO = Path(__file__).resolve().parents[2]

    server_params = StdioServerParameters(
        command=PYTHON,
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
    ```

    Then, in order:

    a. In LM Studio, open the Tools tab (wrench icon) in the right sidebar. It was called the Program tab in older versions and in LM Studio’s docs. Confirm `test-tools` is listed and switched on. If it isn’t listed, open the config with `notepad "$env:USERPROFILE\.lmstudio\mcp.json"` in PowerShell and check that its `"args"` are `["-m", "ai_lab.mcp_server.tools_server"]`. The exact wording of the on/off control needs verification against your installed LM Studio version, so use what the tab shows.

    b. Start a chat with the tools enabled and send the Day 12 prompt: `What was the last test failure? Check the failure log.` The model should call `get_last_failure_log` and answer from your log content. This also makes sure LM Studio has started its own server process.

    c. In a PowerShell window, run `uv run python mcp_client_hold.py`. It prints `call ok: ...`, then `holding the connection open for 90 seconds...`.

    d. Within those 90 seconds, in a second PowerShell window, count the server processes:

        ```bash
        # macOS / Linux
        ps aux | grep tools_server
        ```

        ```powershell
        # Windows PowerShell: shows the full command line and the parent process, not just the process name
        Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
          Where-Object { $_.CommandLine -like '*ai_lab.mcp_server.tools_server*' } |
          Select-Object ProcessId, ParentProcessId, CommandLine
        ```

    e. While the script is still holding, send another prompt in LM Studio. It should still answer, independently of your script.

    f. After `disconnecting` prints, run the same process query again. Only the server LM Studio started should remain.

    Seeing two separate `test_tools_server.py` processes, not one, is Section 2.1’s claim made observable rather than theoretical. Expect two rows with different `ParentProcessId` values: one under LM Studio, one under your hold script. If you see four rows, each server may appear as a launcher plus interpreter pair, since a venv `python.exe` on Windows can start the real interpreter as a child. `ParentProcessId` shows which rows belong together. If LM Studio launches the server with a different command, adjust the `-like` pattern to match its `"args"`.

## Common Pitfalls

- **Forgetting `await`.** Every SDK call in Section 2’s example is a coroutine: `session.initialize()`, `session.list_tools()`, `session.call_tool(...)` all need `await` in front of them. A missing `await` doesn’t always fail loudly; sometimes it just silently returns a coroutine object instead of a result, which is a confusing thing to debug the first time you meet it.
- **Forgetting `asyncio.run(...)` at the top level.** `async def call_tool():` defines a coroutine; it doesn’t run anything by itself. If nothing appears to happen when you run your script, check that you actually invoked it through `asyncio.run()`.
- **Path problems between where you run the script and where the server expects to run.** Without `cwd`, `StdioServerParameters` starts the server in your current working directory when you launch `mcp_client_test.py`, so relative paths like `"tests/"` and `"reports/last_run.log"` resolve against wherever you happened to launch from, which may not be the repo root. Set `cwd` to the repo root, as the Practice code does. This is the same relative-path trap Day 12 flagged for `run_pytest_suite`’s `test_path`, now one layer up the stack.
- **Assuming LM Studio and your script share one running server.** Covered in Section 2.1: they don’t. Each connection gets its own subprocess, its own memory, and (relevant later) its own independent 120-second timeout clock on any in-flight `run_pytest_suite` call. There’s no shared state to coordinate unless you build it yourself.
- **Writing to stdout inside the server for debugging.** Covered in Section 4 above, but worth repeating as a pitfall in its own right because it’s easy to reach for reflexively: any bare `print()` inside an MCP server run over stdio is a live bug waiting to corrupt the message stream, not a harmless debugging aid. (On mcp 2.x an `MCPServer` diverts stray stdout to stderr, see the version note in Section 4, but the habit still matters for any server that isn’t built on the SDK’s stdio transport.)
- **Letting an exception escape the `async with` blocks uncleanly.** The context managers are what guarantee your subprocess actually terminates when your script exits: code that bypasses them (e.g. manually managing the process without `stdio_client`’s context manager) risks leaving orphaned server processes running after your script has already ended.
- **Assuming `list_tools()` needs to be called before every `call_tool()`.** It doesn’t: call it once per session to discover what’s available (exactly how Module 4’s `diagnose_failure()` uses it once, up front, to build the `tools=[...]` schema), then call `call_tool()` as many times as your logic needs within that same session.

## Why This Matters for Test Automation

This is the piece of code that makes your capstone’s central claim true: “any host can call this server, not just LM Studio.” Today you proved it: not by reading that claim, but by writing a second, completely independent host and watching the exact same server respond identically. That’s a concrete, demonstrable answer to an interview question like “how do you know your tool integration isn’t accidentally coupled to one specific client?” You tested it against two.

It’s also the direct, unmodified ancestor of Module 4’s `diagnose_failure()` function: strip away the OpenAI tool-calling conversion and the reasoning loop around it, and what’s left is exactly today’s `stdio_client` / `ClientSession` pattern. Getting comfortable with it now, in isolation, means Module 4 is assembly of pieces you already trust, not new machinery arriving at the same time as everything else.

## Assignment

Produce `src/mcp_client_test.py`:

1. Connects to your own `test_tools_server.py` directly, with no LM Studio involved anywhere in the process.
2. Calls `list_tools()` and prints both tool names, proving discovery works.
3. Calls both `run_pytest_suite` and `get_last_failure_log`, printing real results from each.
4. Include, as a comment or a short paragraph in `docs/setup-notes.md`, what you observed when you deliberately broke stdout in Practice step 4: the actual error or garbled output you saw, not a prediction of what you expected to see.

## Self-Check

- Walk through, in order, exactly what happens on the wire between your script and the server subprocess, from the moment you call `stdio_client(server_params)` to the moment `call_tool()` returns a result.
- Why does a bare `print()` statement inside an MCP server break things, specifically: what rule does it violate, and why does that rule exist?
- What’s the practical difference between `StdioServerParameters` in your Python code and the `"command"` / `"args"` fields in `mcp.json`? Is there a difference in what actually happens, or only in where the configuration lives?
- Why do `session.initialize()`, `list_tools()`, and `call_tool()` all need `await`, and what would you observe if you forgot one?
- If your script crashes partway through a session without hitting the end of the `async with` blocks, what happens to the server subprocess, and why does that matter?
- If LM Studio and your script are both connected to `test_tools_server.py` at the same time, are they talking to one shared server process or two independent ones? What would you actually see if you checked your OS’s process list?

## External Links

- Python MCP SDK (client usage examples): https://github.com/modelcontextprotocol/python-sdk
- MCP stdio transport specification (the exact framing rules referenced in Section 4): https://modelcontextprotocol.io/specification/latest/basic/transports
- Python asyncio documentation (coroutines, `async with`, `asyncio.run`): https://docs.python.org/3/library/asyncio.html
- MCP Python SDK v1 to v2 migration guide (renamed attributes and moved imports): https://py.sdk.modelcontextprotocol.io/v2/migration/

**Next:** Day 14, Schema Design & Module Review. You’ve now used, built, and called an MCP server from every angle Module 3 planned. Today consolidates the schema-design principles from both Module 2 and Module 3 into one set of house rules, and closes out the module with your first real `decisions.md` entry.
