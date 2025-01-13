"""
Tools for executing commands and code in Kali Linux environment.
"""

import subprocess
import getpass
import re
import json
from typing import Dict, Any, List, Union
from rich.console import Console
from rich.panel import Panel
from langchain_core.tools import tool
import os
import sys
import tempfile
from contextlib import contextmanager

console = Console()

@contextmanager
def temp_python_file(code: str, imports: List[str] = None):
    """Create a temporary Python file with the given code and imports."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_path = f.name
            if imports:
                f.write('\n'.join(imports) + '\n\n')
            f.write(code)
            f.flush()
            yield f.name
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

class CodeExecutionResult:
    """Container for code execution results"""
    def __init__(self, success: bool, output: str, error: str = None, requires_followup: bool = False):
        self.success = success
        self.output = output
        self.error = error
        self.requires_followup = requires_followup
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "requires_followup": self.requires_followup
        }

@tool
def execute_python(code: str, imports: List[str] = None, variables: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute Python code with given imports and variables.
    
    Args:
        code: The Python code to execute
        imports: List of import statements
        variables: Dictionary of variables to inject
    
    Returns:
        Dict containing execution results
    """
    try:
        # Create temporary Python file
        with temp_python_file(code, imports) as temp_file:
            # Prepare environment
            env = os.environ.copy()
            if variables:
                env.update({k: str(v) for k, v in variables.items()})
            
            # Execute the code
            process = subprocess.Popen(
                [sys.executable, temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            result = CodeExecutionResult(
                success=process.returncode == 0,
                output=stdout.strip(),
                error=stderr.strip() if stderr else None,
                requires_followup=bool(stderr and "ImportError" in stderr)
            )
            
            return result.to_dict()
            
    except Exception as e:
        return CodeExecutionResult(
            success=False,
            output="",
            error=str(e)
        ).to_dict()

@tool
def run_script(script_path: str, args: List[str] = None) -> Dict[str, Any]:
    """Execute a script file with optional arguments.
    
    Args:
        script_path: Path to the script file
        args: Optional list of arguments
    
    Returns:
        Dict containing execution results
    """
    try:
        if not os.path.exists(script_path):
            return CodeExecutionResult(
                success=False,
                output="",
                error=f"Script not found: {script_path}"
            ).to_dict()
        
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        result = CodeExecutionResult(
            success=process.returncode == 0,
            output=stdout.strip(),
            error=stderr.strip() if stderr else None,
            requires_followup=bool(stderr and "ImportError" in stderr)
        )
        
        return result.to_dict()
        
    except Exception as e:
        return CodeExecutionResult(
            success=False,
            output="",
            error=str(e)
        ).to_dict()

@tool
def run_command(command: str, previous_outputs: Dict[str, str] = None) -> Dict[str, Any]:
    """Execute a shell command and return its output.
    
    Args:
        command: The shell command to execute
        previous_outputs: Optional dict of outputs from previous steps
    
    Returns:
        Dict containing execution results
    """
    try:
        # Execute command
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        result = CodeExecutionResult(
            success=process.returncode == 0,
            output=stdout.strip(),
            error=stderr.strip() if stderr else None,
            requires_followup=False
        )
        
        return result.to_dict()
        
    except Exception as e:
        return CodeExecutionResult(
            success=False,
            output="",
            error=str(e)
        ).to_dict()

# Export available tools
tools = [
    execute_python,
    run_script,
    run_command
]
