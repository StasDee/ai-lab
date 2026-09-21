"""Round 1 capstone: a single-agent ReAct loop that diagnoses failing tests.

Usage:
    uv run python -m ai_lab.agents.diagnostic_agent

Round 2 adds a multi-agent version alongside this one. Keep this file
working: the comparison between the two is the point, so this is not
something the orchestration work replaces.
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ai_lab.llm.client import DEFAULT_MODEL, client

# Launch the server as a module rather than a file path: no path to break
# when the repo moves or a folder gets renamed.
server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "ai_lab.mcp_server.tools_server"],
)


async def diagnose_failure(user_prompt: str, max_iterations: int = 6) -> str:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()

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
                    model=DEFAULT_MODEL,
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


if __name__ == "__main__":
    print(asyncio.run(
        diagnose_failure("Diagnose the last failing test run and suggest a fix.")
    ))
