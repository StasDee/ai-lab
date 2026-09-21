import os
import json
from pathlib import Path
import re
from typing import List

from openai import OpenAI

os.chdir(Path(__file__).resolve().parent)

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

models = client.models.list()

print("Models available in LM Studio:")
for model in models.data:
    print(model.id)

# Tool definitions: what the model sees
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

            }

        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a whitelisted shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "One of: pytest, git status, dir"}
                },
                "required": ["command"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_list_of_python_or_text_files",
            "description": "Get list of python files names from string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "string": {"type": "string", "description": "Sting containing python file names in it."}
                },
                "required": ["string"],
            }
        }
    },
]

# Tool implementation: what actually runs
ALLOWED_COMMANDS = {"pytest", "git status", "dir", "get_list_of_python_or_text_files"}


def read_file(path: str) -> str:
    print(f"---Reading file {path}")
    with open(path, "r") as f:
        return f.read()[:4000]


def get_list_of_python_or_text_files(string: str) -> List[str]:
    print("---Getting list of files")
    return re.findall(r"\s+(?!_)(\w+\.(?:py|txt))", string)


def run_shell(command: str) -> str:
    print(f"---Running shell command: {command}")
    if command not in ALLOWED_COMMANDS:
        return f"Error: {command} is not in the allowed command list."

    import subprocess
    result = subprocess.run(
        ["cmd", "/c", command],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout + result.stderr


DISPATCH = {"read_file": read_file, "run_shell": run_shell,
            "get_list_of_python_or_text_files": get_list_of_python_or_text_files}


# The loop
def run_agent(user_prompt: str, max_iterations: int = 0):
    messages = [{"role": "user", "content": user_prompt}]

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="google/gemma-4-e4b",
            messages=messages,
            tools=tools,
            temperature=1.2,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        for call in msg.tool_calls:
            fn_name = call.function.name
            print(f"\n...Function name: {fn_name}")
            try:
                args = json.loads(call.function.arguments)
                print(f"...Arguments: {args}")
                result = DISPATCH[fn_name](**args)
                print(f"...Tool call result: {result}")
            except Exception as e:
                result = f"Error executing: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return "max iterations reached without a final answer."


if __name__ == "__main__":
    prompt = "Use the run_shell tool to execute the command dir."
    prompt = "List the files in the current directory."
    prompt = "List the files in the current directory, don't modify results, return them as is."
    prompt = "List the files in the current directory, then return list of python file of resulted string, don't change tools results by yourself."
    prompt = "Read a text in the current directory named agent_loop.txt, return it as a result, change nothing, if you are unable to find the text, then return list of files in the current directory."
    prompt = "Calculate numbers 2 and 10 using calculation_tool, change nothing by yourself."
    res = run_agent(prompt, 10)
    print(f"\nAgent call result: {res}")
