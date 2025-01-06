"""
Configuration file for AI prompts, rules, and system messages.
"""

# Welcome message configuration
WELCOME_MESSAGE = """
🤖 Welcome to the AI Assistant!

I can:
- Execute advanced penetration testing
- Run Windows security commands
- Perform network analysis
- Execute security scripts

Available Categories:
- Network Analysis (nmap, wireshark, netsh)
- System Tools (systeminfo, tasklist, wmic)
- Security Testing (various Windows tools)
- PowerShell Security (security cmdlets)

Type 'exit' or 'quit' to end our conversation.
"""

# System message for the AI
SYSTEM_MESSAGE = """You are an Advanced Penetration Testing Assistant running on a Windows system with comprehensive cybersecurity capabilities. You have elevated privileges to perform security testing and vulnerability assessment.

ENVIRONMENT:
- Operating System: Windows
- Shell: PowerShell/Command Prompt
- Privilege Level: Elevated/Administrator
- Current Limitations: Windows-specific tools and commands

CAPABILITIES:

1. Windows Network Analysis:
   - Windows port scanning (nmap for Windows)
   - Network packet capture (Wireshark/tcpdump)
   - Windows network configuration (netsh, ipconfig)
   - Windows service discovery (netstat, tasklist)

2. Windows Wireless Testing:
   - Wireless interface management (netsh wlan)
   - Network adapter configuration
   - WiFi network enumeration
   - Connection monitoring

3. Windows Web Testing:
   - Local web server testing
   - Web request analysis (curl, wget for Windows)
   - Proxy configuration
   - SSL/TLS testing

4. Windows System Tools:
   - System enumeration (systeminfo)
   - Service management (sc, net)
   - User context analysis (whoami)
   - Process management (tasklist, taskkill)
   - Remote connections (ssh, netcat for Windows)

5. Windows Security Testing:
   - Local password testing
   - Windows authentication analysis
   - Service vulnerability scanning
   - Registry analysis
   - Event log analysis

6. PowerShell Security Scripts:
   - Network scanning automation
   - Security auditing
   - System enumeration
   - Vulnerability assessment

AVAILABLE TOOLS:
1. Windows Network Tools:
   {', '.join(['ipconfig', 'netstat', 'nmap', 'wireshark', 'netsh'])}

2. Windows System Tools:
   {', '.join(['systeminfo', 'tasklist', 'sc', 'reg', 'wmic'])}

3. PowerShell Security:
   {', '.join(['Get-Process', 'Get-Service', 'Test-NetConnection', 'Get-NetTCPConnection'])}

4. Windows Security:
   {', '.join(['net user', 'net localgroup', 'net share', 'net session'])}

5. Additional Tools:
   {', '.join(['curl', 'wget', 'ssh', 'nc'])}

COMMAND SYNTAX:
- Use Windows command prompt syntax
- Use PowerShell cmdlets when appropriate
- Prefix privileged commands with appropriate elevation
- Use proper path formatting (backslashes)

RESPONSE FORMAT:
1. Analyze the target and Windows environment
2. Select appropriate Windows tools
3. Execute commands with proper Windows syntax
4. Monitor and capture results
5. Provide detailed output analysis

You are running with elevated privileges on Windows. Use Windows-specific commands and syntax. Remember that some Linux tools may not be available or may require Windows alternatives."""

# Tool categories and descriptions
TOOL_CATEGORIES = {
    "Network": {
        "description": "Windows network analysis tools",
        "tools": ['ipconfig', 'netstat', 'nmap', 'wireshark', 'netsh']
    },
    "System": {
        "description": "Windows system enumeration tools",
        "tools": ['systeminfo', 'tasklist', 'sc', 'reg', 'wmic']
    },
    "PowerShell": {
        "description": "PowerShell security cmdlets",
        "tools": ['Get-Process', 'Get-Service', 'Test-NetConnection', 'Get-NetTCPConnection']
    },
    "Security": {
        "description": "Windows security tools",
        "tools": ['net user', 'net localgroup', 'net share', 'net session']
    },
    "Additional": {
        "description": "Additional security tools",
        "tools": ['curl', 'wget', 'ssh', 'nc']
    }
}

# Command execution rules
EXECUTION_RULES = {
    "elevation_required": [
        "reg",
        "sc",
        "netsh",
        "net user",
        "net localgroup"
    ],
    "safe_mode_required": [
        "reg",
        "wmic"
    ],
    "network_required": [
        "nmap",
        "wireshark",
        "curl",
        "wget"
    ]
}

# Error messages
ERROR_MESSAGES = {
    "elevation_error": "This command requires administrator privileges.",
    "safe_mode_error": "This command should be run in Safe Mode.",
    "network_error": "This command requires network connectivity.",
    "syntax_error": "Invalid command syntax. Please check the command format.",
    "tool_not_found": "The specified tool is not available on this system."
}

# Protected operations
PROTECTED_OPERATIONS = {
    "file_deletion": {
        "commands": ["del", "rm", "remove", "rmdir", "rd", "erase"],
        "powershell_commands": ["Remove-Item", "Remove-Directory", "Clear-Content"],
        "patterns": [r"-rf", r"/s", r"/q", r"format"]
    }
}

# Privilege Management
PRIVILEGE_CONFIG = {
    "access_granted": False,  # Default state
    "unlimited_access": False,  # For unlimited privileges
    "protected_ops": PROTECTED_OPERATIONS,  # Operations that remain restricted
    "session_token": None,  # For tracking elevated sessions
    "privilege_timeout": None  # No timeout for unlimited access
}

# Access control messages
ACCESS_MESSAGES = {
    "grant_success": "[bold green]Unlimited access granted. File deletion remains restricted for safety.[/bold green]",
    "grant_failed": "[bold red]Access denied. System error.[/bold red]",
    "already_granted": "[yellow]You already have unlimited access.[/yellow]",
    "protected_operation": "[bold red]This operation is restricted to protect system files.[/bold red]",
    "access_required": "[yellow]This operation requires elevated privileges. Use 'grant access' to authenticate.[/yellow]"
}

def is_protected_operation(command: str) -> bool:
    """
    Check if the command is a protected operation
    Args:
        command: Command to check
    Returns:
        Boolean indicating if operation is protected
    """
    command_lower = command.lower()
    protected = PROTECTED_OPERATIONS["file_deletion"]
    
    # Check for protected commands
    if any(cmd in command_lower for cmd in protected["commands"]):
        return True
        
    # Check for PowerShell commands
    if any(cmd.lower() in command_lower for cmd in protected["powershell_commands"]):
        return True
        
    # Check for dangerous patterns
    if any(pattern in command_lower for pattern in protected["patterns"]):
        return True
        
    return False

def grant_access(password: str = None) -> bool:
    """
    Grant unlimited access except for file deletion
    Args:
        password: Optional password (not used in unlimited mode)
    Returns:
        Boolean indicating if access was granted
    """
    global PRIVILEGE_CONFIG
    
    # If already granted
    if PRIVILEGE_CONFIG["access_granted"] and PRIVILEGE_CONFIG["unlimited_access"]:
        return True
        
    # Grant unlimited access
    PRIVILEGE_CONFIG["access_granted"] = True
    PRIVILEGE_CONFIG["unlimited_access"] = True
    PRIVILEGE_CONFIG["session_token"] = "UNLIMITED_SESSION"
    PRIVILEGE_CONFIG["privilege_timeout"] = None  # No timeout
    return True

def check_privileges(command: str = None) -> bool:
    """
    Check if operation is allowed
    Args:
        command: Optional command to check against protected operations
    Returns:
        Boolean indicating if operation is allowed
    """
    if not PRIVILEGE_CONFIG["access_granted"]:
        return False
        
    if command and is_protected_operation(command):
        return False
        
    return True

def revoke_access() -> None:
    """Revoke all access"""
    global PRIVILEGE_CONFIG
    PRIVILEGE_CONFIG["access_granted"] = False
    PRIVILEGE_CONFIG["unlimited_access"] = False
    PRIVILEGE_CONFIG["session_token"] = None

def get_tool_description(tool_name: str) -> str:
    """Get the description of a specific tool"""
    for category in TOOL_CATEGORIES.values():
        if tool_name in category["tools"]:
            return category["description"]
    return "Tool description not found."

def check_command_requirements(command: str) -> list:
    """Check requirements for a command"""
    requirements = []
    for rule, commands in EXECUTION_RULES.items():
        if any(cmd in command for cmd in commands):
            requirements.append(rule)
    return requirements 