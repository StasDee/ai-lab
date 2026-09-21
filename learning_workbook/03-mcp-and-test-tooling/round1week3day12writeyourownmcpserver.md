<div class="day-kicker">Day 12</div>

<h1 class="doc-title">Module 3, Day 12: Write Your Own MCP Server</h1>

<div class="subtitle">~1.5-2 hrs | Difficulty: Intermediate</div>

<div class="tldr-box">

**TL;DR:** Yesterday you connected to someone else's server. Today you become the "someone else": you write `test_tools_server.py`, a real MCP server exposing `run_pytest_suite` and `get_last_failure_log`, using the official Python SDK's `FastMCP` class. The entire server is a Python function with type hints and a docstring, decorated with `@mcp.tool()`: the SDK introspects your function signature to build the JSON Schema Day 10 showed you on the wire, and turns your docstring into the tool description the model actually reads. Same reliability-lever lesson as Module 2's tool descriptions, now with real stakes: this schema is about to be read by LM Studio, and next week, by code you write yourself.

</div>

## Objective

<div class="objective-box">

By the end of today you have a working `test_tools_server.py` that LM Studio can connect to and call successfully, end to end, and you can explain exactly how a bare Python function turns into the `tools/list` JSON Day 10 showed you, with no manual schema-writing anywhere in your code.

</div>

## Theory

### 1. What FastMCP is actually doing for you

The official Python `mcp` SDK ships a high-level class, `FastMCP`, whose entire job is to remove the boilerplate between "a Python function that does something useful" and "a spec-compliant MCP server that exposes it correctly." Without it, you'd be hand-writing JSON-RPC message handlers, manually constructing JSON Schema objects, and wiring up the `initialize` / `tools/list` / `tools/call` lifecycle from Day 10 by hand. `FastMCP` collapses all of that into one decorator:

`mcp = FastMCP("test-automation-tools")` creates your server instance: the string is the server's name, the same `serverInfo.name` field you saw inside the `initialize` response on Day 10. Everything below that is a normal Python function until `@mcp.tool()` touches it.

The SDK's exact API surface can shift between releases: package names, import paths, and even class names have moved before and may move again. If `from mcp.server.fastmcp import FastMCP` doesn't match what you have installed, check `pip show mcp` and the current docs linked at the end of this module before assuming your code is wrong. This is worth internalizing as a general skill, not a one-off caveat: reading an SDK's actual installed version beats trusting a remembered import path, the same instinct Day 2 taught you for model id strings.

### 2. The introspection step: how a function becomes a schema

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-automation-tools")

@mcp.tool()
def run_pytest_suite(test_path: str = "tests/") -> str:
    """Run the pytest suite at the given path and return the raw output.

    Args:
        test_path: Relative path to the test directory or file.
    """
    ...
```

This is the mechanical heart of today's lesson, and it directly explains a piece of "magic" that would otherwise feel like magic. When Python executes `@mcp.tool()` on your function, `FastMCP`:

1. **Reads the function name** (`run_pytest_suite`) and uses it, unmodified, as the tool's `name`, the same string that shows up in a `tools/call` request's `params.name`.
2. **Reads the type hints** on every parameter (`test_path: str = "tests/"`) and translates them into JSON Schema types: `str` becomes `"type": "string"`, the default value becomes the schema's `default`, and a parameter with no default becomes `"required"`.
3. **Reads the docstring** and uses it, in full, as the tool's top-level `description`, including the `Args:` block itself, taken as literal text. It's a natural assumption that this gets split into a separate `description` per parameter; on the SDK version this course targets, it doesn't. Each parameter's own schema entry only gets a `title` derived from its name (`test_path` becomes `"title": "Test Path"`) plus whatever point 2 already covered: no parameter-level `description` field at all. Your `Args:` text still reaches the model, just folded into that one description string rather than attached to the specific parameter it explains.
4. **Assembles all of it** into the exact `inputSchema` shape Day 10's `tools/list` response carried over the wire.

<img class="diagram" src="diagram1.png" alt="From a typed Python function to a wire-level JSON Schema">
<p class="diagram-caption">Diagram: what @mcp.tool() actually does at decoration time</p>

The practical consequence: your docstring is not documentation for humans who read your source code: it's the actual schema content a model uses to decide how to call your tool. This is Module 2.2's tool-description reliability lesson again, but the mechanism is now completely literal rather than a general principle: there's no separate schema file to keep in sync, no chance of the docstring saying one thing and the schema saying another, because the docstring is the source the schema gets generated from. Write it as if it's the only information the model will ever get about this tool, because, functionally, it is.

### 3. The two tools, in full

Here's the complete server you're building today, matching exactly what `03-mcp-and-test-tooling.md` already established for this project:

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

A few implementation details worth understanding rather than just typing out:

- `subprocess.run(..., timeout=120)` caps how long a hung test suite can block your server. Without it, a genuinely stuck test run would hang the tool call forever, the MCP-level equivalent of Module 2's `max_iterations` safety guard, just applied to a subprocess instead of a reasoning loop.
- `capture_output=True, text=True` collects both stdout and stderr as strings rather than letting them print to your terminal: the tool's return value needs to be text that flows back into the model's context, not console output nobody's reading.
- Returning `result.stdout + result.stderr` unconditionally, even on failure, is deliberate: a failing test run's output is exactly the diagnostic signal your Module 4 capstone needs. Don't raise an exception here just because pytest exited non-zero: a failing test suite is the expected, useful case, not an error state for your server.
- `f.read()[:6000]` caps how much log content re-enters the model's context in one tool result, the same "don't blow the context budget on one tool call" instinct Module 2's `read_file` used with its `[:4000]` slice.
- `except FileNotFoundError` returns a plain, readable message instead of letting an unhandled exception crash the tool call. A model that receives "No failure log found at that path" as a tool result can reason about it and try something else; a model that receives a stack trace or a dead connection cannot.
- `mcp.run(transport="stdio")` is the one line that decides which transport from Day 10/11's discussion this server actually uses: swapping this to `transport="streamable-http"` later (Round 2 territory) is a real, one-line-visible example of the transport being decoupled from everything above it.

### 4. What happens if a tool raises an exception anyway

You didn't wrap every possible failure in a `try/except` above, deliberately. FastMCP catches unhandled exceptions raised inside a tool function and converts them into an MCP-level tool execution error automatically, the `isError: true` shape Day 10 showed you. That's a safety net, not a design plan: relying on it for expected failure modes (a missing file, a timeout) produces a worse tool result than handling them yourself, because your own message can be specific and actionable ("No failure log found at that path") where the SDK's generic conversion is not. Handle what you can anticipate; let the safety net catch what you can't.

### 5. Registering and testing your server

Add your server to `mcp.json` alongside Playwright MCP from Day 11: a host can run more than one server at once, exactly as Day 10's roles diagram showed:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "test-tools": {
      "command": "P:/CodingWorkspace/ai-lab/.venv/Scripts/python.exe",
      "args": ["P:/CodingWorkspace/ai-lab/src/test_tools_server.py"]
    }
  }
}
```

> Windows-specific, and worth getting right before you debug a phantom "missing package" error: a bare `"command": "python"` resolves against whatever `python` means in the environment LM Studio itself was launched from: not necessarily the `.venv` you've been installing `mcp`, `pytest`, and everything else into all week. LM Studio is normally launched from the Start Menu or a desktop shortcut, not from an activated virtual environment shell, so the subprocess it spawns may find a completely different Python installation on your machine's PATH, one that's never heard of the `mcp` package. The failure that produces, `ModuleNotFoundError: No module named 'mcp'` the instant the server tries to start, looks exactly like a broken install even though the install is fine. The fix is to point `"command"` at your virtual environment's Python explicitly, using its full path; and on Windows specifically, that path is `.venv\Scripts\python.exe`, not `.venv\bin\python` the way it would be on macOS or Linux. This one line is worth checking now, not after twenty minutes of debugging a package that was actually installed correctly the whole time.

> There's a second, separate path problem hiding in the same config, easy to hit even after the fix above: LM Studio treats each `mcp.json` server entry as its own "plugin," with its own private sandbox directory: confirmed as `~/.lmstudio/extensions/plugins/mcp/<server-name>/` (on Windows, `C:\Users\<you>\.lmstudio\extensions\plugins\mcp\test-tools\`). A relative path in `"args"`, like a bare `"test_tools_server.py"`, resolves against *that* sandbox directory, not your project folder, so even with `"command"` pointed correctly at your venv's Python, the interpreter still can't find the file, and fails with a plain `[Errno 2] No such file or directory` naming a path you never wrote and don't recognize. The fix is the same instinct as above, applied to `"args"` instead of `"command"`: use the full, absolute path to `test_tools_server.py` in your actual project, exactly as the config above now shows, not just its filename.

Restart LM Studio's MCP connections (or LM Studio itself, if the UI doesn't hot-reload config changes), and confirm `test-tools` shows up as connected. Then, in a chat with tools enabled, ask your model to run your test suite: you should see it call `run_pytest_suite` and report back real output.

### 6. One server, already reusable

<img class="diagram" src="diagram2.png" alt="One test_tools_server.py, called by two different hosts on two different days">
<p class="diagram-caption">Diagram: the exact same server, unmodified, callable from LM Studio today and your own code tomorrow</p>

Notice what you have not done to make this true: you haven't written any LM-Studio-specific code, and you won't write any different code tomorrow when Day 13 connects to this exact same file from a standalone Python script instead. This is Day 10's N×M lesson paying off directly: the server doesn't know or care who's connecting, which is exactly what makes it reusable without modification.

## Practice

Before working through the checks below, set up two things the exercise needs: real fixtures for both tools to run against, and the exact wording to type for each check.

### Setup: fixtures both tools need

Create the following in your project (adjust paths if your layout differs from `P:/CodingWorkspace/ai-lab/`):

**`tests/test_sample.py`**: a small suite with one deliberate failure, so `run_pytest_suite` has real diagnostic output to return instead of "no tests collected":

```python
def test_addition():
    assert 1 + 1 == 2


def test_string_upper():
    assert "hello".upper() == "HELLO"


def test_list_length():
    assert len([1, 2, 3]) == 3


def test_this_one_fails_on_purpose():
    assert 2 + 2 == 5
```

**`tests/test_slow.py`**: kept separate from the main suite, so it only runs when item 5 below points `run_pytest_suite` at it directly:

```python
import time


def test_deliberately_slow():
    """Exists only to trigger run_pytest_suite's 120s timeout guard.

    Point run_pytest_suite at this file specifically
    (test_path="tests/test_slow.py"). Do not include this file's
    directory in a normal test run.
    """
    time.sleep(150)
    assert True
```

**`reports/last_run.log`**: a fake but realistic failure log, so `get_last_failure_log` has something real to return:

```
============================= FAILURES =============================
_____________________ test_this_one_fails_on_purpose _____________________

    def test_this_one_fails_on_purpose():
>       assert 2 + 2 == 5
E       assert (2 + 2) == 5

tests/test_sample.py:13: AssertionError
===================== short test summary info ======================
FAILED tests/test_sample.py::test_this_one_fails_on_purpose - assert (2 + 2) == 5
1 failed, 3 passed in 0.04s
```

Worth being honest with yourself about one thing here: `run_pytest_suite` doesn't write to `reports/last_run.log`. Nothing currently connects the two tools: you're hand-authoring the log so `get_last_failure_log` has something genuine to fetch, not because a suite run produced it. That's enough to test each tool in isolation today; it isn't a working pipeline yet.

1. **Type the server in yourself**, rather than copy-pasting, at least the first time: the goal is fluency with the `@mcp.tool()` pattern, not just a working file.

2. **Confirm the happy path on both tools before testing any failure mode.** With `test-tools` connected in LM Studio, try:
   - *"Run the pytest suite in tests/ and tell me which tests failed and why."* Expect a tool call with `test_path="tests/"`, a tool result containing the real short traceback for `test_this_one_fails_on_purpose`, and a final answer that names that failing test specifically, not a generic "some tests failed."
   - *"What was the last test failure? Check the failure log."* Expect a tool call at the default `log_path`, a result containing your fixture log content, and a summary that actually reflects it, worth checking this isn't just a plausible-sounding guess, since a small quantized model can occasionally ignore a tool result and answer from its own assumptions instead.

3. **Deliberately break your own docstring** and observe the effect: remove the `Args:` block from `run_pytest_suite`, reconnect, and ask: *"Run the pytest suite located at tests/integration/."* Does it correctly pass `test_path="tests/integration/"`, or does it guess wrong or omit the argument? Restore the docstring afterward; this is a live demonstration of Section 2's claim, not just a claim.

4. **Trigger the `FileNotFoundError` path on purpose.** Ask: *"Check the failure log at reports/does_not_exist.log."* Confirm you get your friendly message back, "No failure log found at that path," not a crash or a stack trace in the tool result.

5. **Trigger a slow-running command and confirm the timeout actually fires.** Ask: *"Run the pytest suite in tests/test_slow.py."* After roughly 120 seconds, `subprocess.run`'s `timeout=120` kills the hung process, but since `run_pytest_suite` doesn't catch that timeout (Section 4), what comes back is FastMCP's generic `isError: true` conversion, not a message you wrote yourself. That's the live version of Section 4's point: seeing the guard actually catch something, and seeing exactly how much less useful that result looks next to the `FileNotFoundError` message above, is worth more than trusting either fact in the abstract.

## Common Pitfalls

- **Forgetting the server runs from wherever LM Studio launches it, not your project root.** Relative paths like `"tests/"` or `"reports/last_run.log"` resolve against the subprocess's working directory, which may not be what you expect: verify with an absolute-path test before assuming a relative path is broken.
- **Using a bare `"python"` in `mcp.json` on Windows and assuming it's your `.venv`.** Covered in detail in Section 5's callout: LM Studio's own launch environment decides which `python` that resolves to, and it's frequently not the virtual environment you've been installing packages into all week. Point `"command"` at your venv's full interpreter path explicitly.
- **Using a bare filename in `mcp.json`'s `"args"` and assuming it resolves against your project.** Covered in Section 5's second callout: LM Studio runs each server from its own private plugin sandbox directory, not your project folder, so a relative `"test_tools_server.py"` resolves there instead and fails with a file-not-found error naming a path you never wrote. Use the full absolute path to the file in `"args"` instead.
- **Writing a vague docstring "for later."** There is no "later" here: the docstring is live schema content the moment the file runs. A docstring like `"""Runs tests."""` gives your model almost nothing to decide when to call this tool versus another one.
- **Catching every exception broadly (`except Exception:`) instead of the specific ones you expect.** This silently swallows real bugs in your own tool code, not just the external failures (missing file, timed-out subprocess) you meant to handle gracefully.
- **Returning `None` or a non-string type from a tool function.** The result needs to flow back into the model's context as text; returning `None` (e.g. from a code path that forgets a `return`) produces a confusing, mostly-empty tool result rather than an error you'd notice immediately.
- **Assuming `subprocess.run` inherits your Python environment automatically.** Even once the server itself is running under the right interpreter, `pytest` still needs to be on the PATH that `subprocess` call sees, a separate, narrower version of the same environment-mismatch idea, one layer further in. If `run_pytest_suite` fails, check this before assuming your test suite itself is broken.
- **Not restarting LM Studio's MCP connections after editing `mcp.json` or your server file.** A stale connection to an old version of your server is a common source of "why isn't my fix showing up" confusion: Day 11's pitfall about JSON syntax errors applies here too, since a broken `mcp.json` fails exactly the same way, silently.

## Why This Matters for Test Automation

`test_tools_server.py` is not a throwaway exercise file: it's literally the server your Module 4 `diagnose_failure()` function calls, unmodified, per `04-capstone-and-cv.md`'s architecture. Everything you get right today about timeout handling, error messages, and docstring precision is capstone infrastructure, not practice.

It's also a clean, concrete answer to a question interviewers actually ask: "how would you expose your test infrastructure to an AI tool without hand-rolling a custom integration for every consumer?" You now have a real, working answer: two tools, a handful of lines each, reusable by any MCP-speaking host that connects to the same subprocess command.

## Assignment

Produce `src/test_tools_server.py`, working end-to-end via LM Studio's chat, matching Section 3's implementation (adapt paths to your actual project structure). Confirm and document:

1. A successful `run_pytest_suite` call and its real output, pasted into `docs/setup-notes.md` as a Day 12 addendum.
2. A successful `get_last_failure_log` call, including one attempt against a path that doesn't exist, to prove the `FileNotFoundError` handling works as intended.
3. One or two sentences: what would you write differently in either docstring if you knew, for certain, that only a colleague with zero context would ever read it, not you, and not a model that already has this lesson's context?

## Self-Check

- If you handed this server to a teammate with zero other context, would your tool descriptions alone be enough for them to use it correctly? What's the honest answer, not the hopeful one?
- Walk through, from memory, the four things `@mcp.tool()` reads off your function to build its schema.
- Why does `run_pytest_suite` return `result.stdout + result.stderr` even when pytest fails, instead of raising an exception?
- What's the difference between a failure you handle yourself with `try/except` and one you let FastMCP's automatic exception-to-error conversion catch, and why does that choice matter for how useful the resulting tool result is to the model?
- What single line would you change to move this server from stdio to Streamable HTTP, and what would not need to change?
- On Windows, what decides which Python interpreter actually runs when LM Studio launches your server via `"command": "python"`, and why might that not be your `.venv`?

## External Links

- Python MCP SDK (official): https://github.com/modelcontextprotocol/python-sdk
- FastMCP tools documentation (decorator behavior, schema generation): https://gofastmcp.com/servers/tools
- MCP tools specification (the wire-level shape your schema is generated into): https://modelcontextprotocol.io/specification/latest/server/tools
- Python subprocess documentation (timeouts, capturing output): https://docs.python.org/3/library/subprocess.html

**Next:** Day 13, Call Your Server From Your Own Agent Code. LM Studio's UI has been standing in for your own code for two days now; today you write the client side yourself, in Python, and retire the middleman.
