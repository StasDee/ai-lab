# Module 2: Python Agents From Scratch
### Round 1, Week 2

## Why This Module

"Agent" gets thrown around as if it's mysterious. It isn't. By the end of this module you'll have built the whole mechanism yourself (no framework hiding the moving parts) which means you can debug it when it breaks and explain it precisely when an interviewer asks "so what does an agent actually do."

---

## 2.1 What an Agent Actually Is

A plain chat completion is one round trip: you send messages, you get text back, done.

An **agent** is a loop:

1. Send the model messages **plus a list of tools it's allowed to use**
2. The model either answers directly, or asks to call a tool
3. Your code executes that tool call in the real world (read a file, run a command, hit an API)
4. The result goes back into the message history as new context
5. Repeat until the model gives a final answer instead of another tool call

This pattern (interleaving reasoning with tool calls) is usually called **ReAct** (Reason + Act). There's no magic step where the model "does" anything outside your code; it only ever produces text. Your loop is what turns that text into action.

## 2.2 What Actually Happens on the Wire

The model never calls a function. It emits structured text (JSON matching a schema you gave it) and your code decides what to do with that JSON. "Tool calling" support in an API or local server just means the model was trained to reliably produce that JSON shape when you hand it a schema, instead of you having to regex it out of free text.

This is why **tool descriptions and schemas are a reliability lever, not documentation**. A vague description ("gets file stuff") gives the model less signal about when and how to call the tool correctly than a precise one ("reads the contents of a text file at the given relative path, returns UTF-8 text"). Sloppy schemas are a common, invisible cause of "the agent isn't working": it's not the model failing, it's the schema underspecifying the tool.

## 2.3 Build the Loop Yourself

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

Notice three things that are easy to miss when a framework does this for you:

- **`max_iterations` is a safety guard, not an optimization.** Without it, a model that keeps calling tools never stops.
- **Errors are fed back as tool results, not raised.** The model can often self-correct ("that command isn't allowed, let me try `ls` instead") if you give it the error as context instead of crashing.
- **The allowlist in `run_shell` is the whole security model right now.** Module 8 replaces this with something real; for now, know that this line is the only thing standing between "agent" and "arbitrary code execution."

## 2.4 Why Hand-Roll First

You'll reach for LangGraph or CrewAI in Round 2, and that's the right call once you have multiple agents that need to coordinate. But building the raw loop first means:

- You can debug a broken agent instead of guessing which framework abstraction is misbehaving
- You can answer "what does your agent actually do" precisely, instead of "the framework handles it"
- You know exactly what a framework is buying you, because you've felt the boilerplate it removes

## 2.5 The Framework Pass

Now rebuild the same capability with [smolagents](https://huggingface.co/docs/smolagents/index), a lightweight agent library from Hugging Face:

```python
from smolagents import ToolCallingAgent, tool
from smolagents import OpenAIServerModel

@tool
def read_file(path: str) -> str:
    """Read the contents of a text file at the given relative path.

    Args:
        path: Relative path to the file.
    """
    with open(path, "r") as f:
        return f.read()[:4000]

model = OpenAIServerModel(
    model_id="qwen2.5-coder-7b-instruct",
    api_base="http://localhost:1234/v1",
    api_key="not-needed",
)

agent = ToolCallingAgent(tools=[read_file], model=model)
result = agent.run("Read config.yaml and summarize what it configures.")
```

Same idea, far less code: the loop, message bookkeeping, and JSON parsing are now handled for you. What's now hidden: the exact retry/error-handling behavior, and how many iterations it'll silently attempt before giving up. Know that trade-off exists even when you don't need to touch it.

## 2.6 How Agent Loops Actually Fail

- **Malformed tool-call JSON**: wrap parsing in try/except, feed the error back as a tool result so the model can retry
- **Hallucinated or wrong arguments**: validate arguments before executing, don't trust them just because they parsed
- **Infinite tool-calling loops**: always cap `max_iterations`; decide up front what "give up gracefully" looks like
- **Ignoring tool results**: if the model keeps asking the same question after you've answered it, that's a signal your tool result format is hard for the model to use, not that the model is "being difficult"

---

## Exercise

- [ ] Build the hand-rolled loop above with your own 2-3 tools (adapt `read_file`/`run_shell`, or add an `http_get`)
- [ ] Rebuild the identical capability using smolagents
- [ ] Write a short comparison note: lines of code, how easy each was to debug, what the framework hid from you

## Self-Check

- What actually happens on the wire when a model "calls a tool"?
- Why is tool description quality itself a reliability lever, not just documentation?
- Name two concrete ways your hand-rolled loop could infinite-loop, and how you guard against each.

## External Links

- ReAct paper (Yao et al., the pattern this whole module is built on): https://arxiv.org/abs/2210.03629
- smolagents docs: https://huggingface.co/docs/smolagents/index
- OpenAI function-calling guide (the schema format most local runtimes mimic): https://platform.openai.com/docs/guides/function-calling

---

**Next:** Module 3, MCP & Real Test Tooling. You've hand-rolled tools; now you plug into the standard that lets any agent use any tool, including the ones the QA industry already ships.
