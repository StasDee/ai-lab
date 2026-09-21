# Module 4: Capstone & CV Polish
### Round 1, Week 4

## Why This Module

Modules 1-3 were separate exercises. This is where they become one artifact a hiring manager can actually open, and where "it runs" stops being good enough. The bar here is: you can defend every design decision in it, out loud, under questioning.

---

## 4.1 Assembling the Capstone

The shape doesn't change from Module 2: only where tool execution comes from changes. Instead of a local `DISPATCH` dict, tool calls now go through your Module 3 MCP server:

```python
import asyncio, json
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
server_params = StdioServerParameters(command="python", args=["tools_server.py"])

async def diagnose_failure(user_prompt: str, max_iterations: int = 6):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()

            # Convert MCP tool definitions into the OpenAI tool-calling schema
            tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema,
                },
            } for t in mcp_tools.tools]

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
                    return msg.content

                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments)
                    result = await session.call_tool(call.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": str(result.content),
                    })

    return "Max iterations reached without a final answer."

asyncio.run(diagnose_failure("Diagnose the last failing test run and suggest a fix."))
```

Notice this is the exact same loop from Module 2: reasoning, tool call, execute, feed back, repeat. The only thing that changed is where "execute" points. That's the actual point of MCP: you can swap the tool source without touching the reasoning loop at all.

## 4.2 Elevate It to Senior Work

Four additions separate a demo from something a senior engineer built:

**Observability**: log every tool call and model decision. A flat JSONL trace file is enough at this scale:

```python
import json, time

def log_step(tool_name, args, result):
    with open("agent_trace.jsonl", "a") as f:
        f.write(json.dumps({
            "timestamp": time.time(),
            "tool": tool_name,
            "args": args,
            "result": str(result)[:500],
        }) + "\n")
```

**Sandboxing story**: document how you'd containerize the MCP server (Docker, restricted filesystem/network) even if you don't fully implement it. Interviewers will ask this whether or not you've built it.

**Failure-mode plan**: the honest answer to "what happens when this is wrong" is a human-in-the-loop review gate before any fix gets auto-applied, not full autonomy. Say that plainly; it reads as more senior than pretending otherwise.

**CI tie-in**: see below, this one has a real architectural wrinkle worth understanding.

## 4.3 The CI Problem Worth Knowing About

A purely local model can't be called directly from a standard GitHub-hosted Actions runner: your model lives on your machine, and the runner doesn't have network access to it unless you expose your machine (a tunnel) or self-host the runner on your own hardware.

This isn't a flaw to hide: it's a genuine production trade-off, and naming it well is a stronger interview answer than a CI pipeline that quietly wouldn't actually work end-to-end. Two honest options:

1. **Self-hosted GitHub Actions runner** on your own machine: the CI job runs where your local model already lives
2. **Fallback to a cloud model for the CI step only**: local for day-to-day dev work (privacy, cost), cloud for the automated pipeline where your machine isn't guaranteed to be online

Pick one, document why, and you have a genuinely good "walk me through a trade-off you made" answer.

## 4.4 Writing It Up

- Fill in the `README.md` and `architecture.md` templates from earlier in this project with what you actually built, not placeholders anymore
- Record a 2-3 minute demo clip
- Finalize your CV bullet

---

## Exercise

- [ ] Assemble the full capstone: Module 1 model + Module 2 loop shape + Module 3 MCP server, using the integrated code above
- [ ] Add structured logging for every tool call and model decision
- [ ] Write your sandboxing plan and failure-mode plan into `architecture.md`: a paragraph each is enough, as long as it's specific
- [ ] Decide and document your CI approach given the local-model constraint (self-hosted runner vs. cloud fallback)
- [ ] Fill in `README.md` and `architecture.md` with real content
- [ ] Push to GitHub, record the demo

## Self-Check

- Walk through your agent loop out loud, step by step, without looking at the code: can you do it cleanly?
- What's your honest, specific answer to "what happens when this agent is wrong"?
- Why can't a purely local model be called directly from a standard GitHub-hosted CI runner, and which of the two fixes did you choose, and why?

## External Links

- GitHub Actions self-hosted runners: https://docs.github.com/en/actions/hosting-your-own-runners
- Docker docs (for the sandboxing story): https://docs.docker.com

---

**Round 1 complete.** When you're ready, Round 2 opens with Module 5, Multi-Agent Orchestration.
