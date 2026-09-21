<div class="day-label">Day 6</div>

# Module 2, Day 6: Build the Hand-Rolled Loop

<p class="subtitle">~2-2.5 hrs | Difficulty: Intermediate</p>

<div class="tldr-box">
<p><strong>TL;DR:</strong> Today Day 5's paper trace becomes ~60 lines of real Python: a tool schema, a dispatch table mapping tool names to functions, and a loop that calls the model, executes whatever it asks for, and feeds the result back, capped by a hard iteration limit. This file, almost unmodified, is what your Module 4 capstone imports directly. Getting the shape right today is not throwaway practice.</p>
</div>

<div class="objective-box">
<p><strong>Objective:</strong> By the end of today you have a working <code>run_agent()</code> function against your local Qwen2.5-Coder-7B-Instruct setup, with your own tools wired through a <code>DISPATCH</code> dict, and you can explain why each of its three defensive design choices (iteration cap, error-as-tool-result, allowlisted commands) exists.</p>
</div>

## Theory

### The three lines that are easy to skip and shouldn't be

Everything in today's loop is unsurprising once you've done Day 5's trace by hand, except three specific design choices that don't show up until you actually write the code. Each one exists because of a failure mode that isn't obvious until you've been bitten by it once.

**`max_iterations` is a safety guard, not an optimization.** Nothing about the ReAct loop *logically* has to terminate. If the model keeps deciding a tool call is warranted (because a schema is ambiguous, because a tool result didn't actually answer its question, or just because of an unlucky sampling run) steps 1 through 4 of Day 5's cycle will happen forever. A `for _ in range(max_iterations)` isn't there to make the code faster; it's the only thing standing between "agent" and "process that never returns."

**Errors are fed back as tool results, not raised.** This is counterintuitive if you're used to standard Python error handling, where an exception usually means "stop and tell a human." Here, an exception inside a tool means something different: "the model asked for something that didn't work: tell *the model*, not the terminal." A model that receives `"Error: 'rm -rf /' is not in the allowed command list"` as a tool result can often reason about that and try something else on the next turn. A model whose calling process just crashed can't do anything at all. Swallowing the exception and routing it back through the loop is what makes an agent resilient instead of brittle.

**The allowlist is the entire security model, for now.** `ALLOWED_COMMANDS = {"pytest", "git status", "ls"}` is one line, and at this stage of the course, it's doing all the work of keeping "agent that runs shell commands" from being "arbitrary remote code execution with extra steps." That's not a criticism of today's code: it's an honest flag that this is a placeholder, not a security boundary you'd ship. Module 4's capstone revisits this properly (sandboxing, least-privilege MCP servers); for today, just know precisely how thin this line is.

### Diagram: the loop, wired

<div class="diagram-wrap">

<img src="day6_wiring.png" alt="Hand-rolled loop wiring">

</div>
<p class="diagram-caption">Every box below is a real line of code you're about to write. The two decision diamonds are the only branching in the whole function.</p>

Trace this against Day 5's 5-step cycle: `tools=[...]` + `messages` is step 1. `response.choices[0].message` landing on the "empty tool_calls?" diamond is steps 2 and 5 (the exit check). The parse → dispatch → append path is step 3. The loop-back arrow into `call` is step 4. The only thing this diagram adds that Day 5's didn't is the **second** decision diamond (the `max_iterations` guard) sitting between "append result" and "call the model again."

### Build it

```python
import json
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

# --- Tool definitions: what the model sees ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file at the given relative path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a whitelisted shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "One of: pytest, git status, ls"}
                },
                "required": ["command"],
            },
        },
    },
]

# --- Tool implementations: what actually runs ---
ALLOWED_COMMANDS = {"pytest", "git status", "ls"}

def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()[:4000]  # cap what gets fed back to the model

def run_shell(command: str) -> str:
    if command not in ALLOWED_COMMANDS:
        return f"Error: '{command}' is not in the allowed command list."
    import subprocess
    result = subprocess.run(command.split(), capture_output=True, text=True, timeout=30)
    return result.stdout + result.stderr

DISPATCH = {"read_file": read_file, "run_shell": run_shell}

# --- The loop ---
def run_agent(user_prompt: str, max_iterations: int = 6):
    messages = [{"role": "user", "content": user_prompt}]

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="qwen2.5-coder-7b-instruct",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content  # model is done: no more tools needed

        for call in msg.tool_calls:
            fn_name = call.function.name
            try:
                args = json.loads(call.function.arguments)
                result = DISPATCH[fn_name](**args)
            except Exception as e:
                result = f"Error executing {fn_name}: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return "Max iterations reached without a final answer."
```

Walk through the `try/except` block specifically: it catches **two different failure classes** in one place. `json.loads` can throw if the model's arguments string isn't valid JSON (rare with a Q4_K_M-and-above model, per Module 1's quantization discussion, but not impossible). `DISPATCH[fn_name](**args)` can throw if the model requested a tool name that doesn't exist, or passed arguments that don't match the function's real signature. Both land in the same `except Exception as e`, and both get turned into the same kind of thing: a string that goes back to the model as a tool result. This is deliberate: from the loop's perspective, "malformed JSON" and "wrong argument name" are the same category of problem: *something the model said didn't work, and the model should find out*.

### A subtlety worth naming: what happens on a bad tool name

If the model emits a `tool_calls` entry for a function name that isn't in `DISPATCH` at all (say it hallucinates `"delete_file"`) the exact same `except Exception` catches the resulting `KeyError`. You don't need a separate check for "is this a tool I actually have." The dispatch dict lookup failing *is* the check. This is a small design win worth noticing: because you route every DISPATCH call through one try/except, you get "unknown tool" handling for free, without writing it explicitly.

## Practice

1. Implement the loop above exactly as written, and confirm it runs against LM Studio (`base_url="http://localhost:1234/v1"`) with a trivial prompt like `"List the files in the current directory."`
2. Add one tool of your own: `http_get(url: str)` is a good choice (use `requests.get(url, timeout=10).text[:2000]`), or adapt something closer to your test-automation background. Write its schema with the same care Day 5 asked you to evaluate `run_shell`'s schema for.
3. Deliberately test the "unknown tool" path: temporarily remove `read_file` from `DISPATCH` (but leave it in `tools`) and ask a prompt that would need it. Confirm the loop doesn't crash: it should feed an error back and let the model react.
4. Print `messages` at the end of a multi-tool-call run and read through it top to bottom. This is the artifact Day 5 asked you to predict on paper: compare what actually happened against your hand trace.

## Common Pitfalls

- **Trusting parsed arguments without validating them.** `json.loads` succeeding only means the string was valid JSON: it says nothing about whether `path` is a real file or `command` is safe. Malformed JSON and *wrong-but-valid* JSON are different problems; today's `except` block only catches the first cleanly.
- **Forgetting `messages.append(msg)` before checking `tool_calls`.** The assistant's own message (including its tool-call request) has to be in history before you append the tool results: otherwise the model loses track of what it asked for.
- **Setting `max_iterations` too low while debugging.** If you're deliberately testing failure modes tomorrow, a cap of 2-3 will look like a bug in your loop when it's actually just the guard doing its job. Keep it generous (6+) while developing.
- **Building `run_shell` without the allowlist "for now, I'll add it later."** Add it now. It costs one line and is the only thing between this code and running whatever the model asks.

## Assignment

Produce `src/agent_loop.py`: a working, importable version of the loop above with:
1. Your own `read_file`/`run_shell` (or adapted equivalents) plus one original tool
2. A `DISPATCH` dict wired to all of them
3. `run_agent()` tested end-to-end against LM Studio with at least one prompt that triggers two sequential tool calls (not just one)
4. A short comment block at the top of the file noting your `max_iterations` choice and why

## Why This Matters for Test Automation

This file is not a throwaway exercise: `run_agent()`'s shape is *exactly* what Module 4's capstone assembles into a real diagnostic tool, just with `DISPATCH` eventually replaced by calls routed through an MCP server (Module 3). The defensive choices you're making today (capped iterations, errors-as-context instead of crashes, an explicit allowlist) are the same ones a senior engineer is expected to name unprompted when asked "what happens when your agent's tool call fails in CI at 2am." Having actually built and broken this loop yourself means that answer comes from experience, not a talking point you memorized.

## Self-Check

- Trace, precisely, what happens if the model emits a tool call for a function name that isn't in `DISPATCH`.
- Why does one `try/except` block around `json.loads` **and** `DISPATCH[fn_name](**args)` handle two different failure classes correctly, rather than needing two separate checks?
- If you removed the `max_iterations` cap entirely, what's the worst case? Is it *guaranteed* to happen, or just possible?
- Where exactly does today's code stop being "an agent's tool" and start being "arbitrary code execution," if the allowlist in `run_shell` were removed?

## External Links

- OpenAI function-calling guide (the schema format most local runtimes mimic): https://platform.openai.com/docs/guides/function-calling

---

**Next:** Day 7, deliberately breaking today's loop on purpose, to see each of the four core agent failure modes up close before you meet them unexpectedly.
