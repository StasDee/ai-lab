import re
from typing import List

from smolagents import  tool
from smolagents import OpenAIServerModel
from smolagents import ToolCallingAgent

ALLOWED_COMMANDS = {"pytest", "git status", "dir", "get_list_of_python_or_text_files"}


@tool
def read_file(path: str) -> str:
    """Read the contents of a text file at the given relative path.

    Args:
        path: Relative path to the file.
    """
    print(f"---Reading file {path}")
    with open(path, "r") as f:
        return f.read()[:4000]


@tool
def get_list_of_python_or_text_files(string: str) -> List[str]:
    """Get list of python files names from string.

    Args:
         string: Sting containing python file names in it.
        """
    print("---Getting list of files")
    return re.findall(r"\s+(?!_)(\w+\.(?:py|txt))", string)


@tool
def run_shell(command: str) -> str:
    """Run a whitelisted shell command and return its output.

    Args:
        command: Whitelisted shell command.
    """
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



model = OpenAIServerModel(
    model_id="google/gemma-4-e4b",
    api_base="http://localhost:1234/v1",
    api_key="not-needed",
    max_tokens=1024,
    temperature=0.0,
)

agent = ToolCallingAgent(
    tools=[
        read_file,
        get_list_of_python_or_text_files,
        run_shell,
    ],
    model=model,
)

prompt = "Calculate the sum of numbers from 1 to 10"
prompt = "Use the run_shell tool to execute the command dir."
prompt = "List the files in the current windows directory."
prompt = "List the files in the current windows directory, don't modify results, return them as is."
prompt = "List the files in the current windows directory, then return list of python files of resulted string as list of values, don't change tools results by yourself."
prompt = "Read a text in the current directory named agent_loop.txt, return it as a result, change nothing, if you are unable to find the text, then return list of files in the current directory."
prompt = "Calculate numbers 2 and 10 using calculation_tool, change nothing by yourself."

result = agent.run(
    prompt,
     s=3,
)

print(result)
