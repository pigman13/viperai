import subprocess
from typing import Dict, Any
from rich.console import Console
from langchain_core.tools import tool

console = Console()

@tool
def run_command(command: str) -> str:
    """Execute a command in PowerShell and return its output.
    Args:
        command: The command to execute
    Returns:
        The command output as string
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            shell=True
        )
        return result.stdout if result.stdout else result.stderr
            
    except Exception as e:
        return f"Error: {str(e)}"

# Single tool for binding
tools = [run_command]
