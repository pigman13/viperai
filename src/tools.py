import subprocess
from typing import Dict, Any, Optional, List
from rich.console import Console
from langchain.tools import Tool
import tempfile
import os
import sys
import re

console = Console()

# List of allowed commands for pentesting
ALLOWED_COMMANDS = {
    # Network Discovery & Analysis
    'ipconfig': 'Display IP configuration',
    'arp': 'Display/modify ARP cache',
    'netstat': 'Network connections and stats',
    'nslookup': 'DNS queries and zone transfers',
    'tracert': 'Trace network route',
    'ping': 'Test network connectivity',
    'nmap': 'Network port scanning',
    'tcpdump': 'Packet capture and analysis',
    
    # Wireless Tools
    'netsh': 'Network shell configuration',
    'iwconfig': 'Wireless interface configuration',
    'airmon-ng': 'Wireless monitor mode',
    'airodump-ng': 'Wireless packet capture',
    'aireplay-ng': 'Wireless packet injection',
    
    # Web Testing
    'sqlmap': 'SQL injection testing',
    'nikto': 'Web server scanning',
    'dirb': 'Web content scanning',
    'wget': 'Web content retrieval',
    'curl': 'Web request testing',
    
    # System & Network
    'systeminfo': 'System information',
    'whoami': 'Current user context',
    'net': 'Network resource management',
    'route': 'Network routing table',
    'ssh': 'Secure shell client',
    'nc': 'Netcat networking utility',
    
    # File Operations
    'dir': 'List directory contents',
    'type': 'Display file contents',
    'cd': 'Change directory',
    'pwd': 'Print working directory',
    
    # Security Tools
    'python': 'Execute security scripts',
    'pip': 'Install security packages',
    'hydra': 'Password attack tool',
    'john': 'Password cracker',
    'hashcat': 'Password recovery',
    
    # Custom Scripts
    'pentest.py': 'Custom pentest automation',
    'scan.py': 'Custom network scanner',
    'exploit.py': 'Custom exploit framework'
}

def run_shell_command(command: str) -> Dict[str, Any]:
    """
    Run pentesting commands with elevated privileges
    Args:
        command: The command to run
    Returns:
        Dictionary with command results and status
    """
    try:
        # Split command into parts
        cmd_parts = command.split()
        base_cmd = cmd_parts[0].lower()
        
        # Run command with appropriate privileges
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            shell=True,
            cwd=os.getcwd()
        )
        
        return {
            "success": True,
            "output": result.stdout if result.stdout else result.stderr,
            "command": command
        }
            
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: Failed to execute {command} - {str(e)}",
            "command": command
        }

def execute_python(code: str) -> Dict[str, Any]:
    """
    Execute Python security scripts
    Args:
        code: Python code to execute
    Returns:
        Dictionary with execution results
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
        
        try:
            # Execute with appropriate privileges
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True
            )
            
            return {
                "success": True,
                "output": result.stdout if result.stdout else result.stderr,
                "code": code
            }
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
            
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: Failed to execute code - {str(e)}",
            "code": code
        }

def install_security_package(package: str) -> Dict[str, Any]:
    """
    Install security packages and tools
    Args:
        package: Package name to install
    Returns:
        Dictionary with installation results
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True
        )
        
        return {
            "success": True,
            "output": result.stdout if result.stdout else result.stderr,
            "package": package
        }
            
    except Exception as e:
        return {
            "success": False,
            "output": f"Error: Failed to install {package} - {str(e)}",
            "package": package
        }

# Create tool instances
tools = [
    Tool(
        name="pentest_command",
        func=run_shell_command,
        description=f"""Run pentesting commands with elevated privileges. Available commands:
        {chr(10).join([f'- {cmd}: {desc}' for cmd, desc in ALLOWED_COMMANDS.items()])}""",
        return_direct=True
    ),
    Tool(
        name="security_script",
        func=execute_python,
        description="Execute Python security scripts with elevated privileges.",
        return_direct=True
    ),
    Tool(
        name="install_security_tool",
        func=install_security_package,
        description="Install security packages and tools with elevated privileges.",
        return_direct=True
    )
]

# Function to get all tools
def get_tools() -> List[Tool]:
    """Get list of pentesting tools"""
    return tools
