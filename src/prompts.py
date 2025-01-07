"""
Configuration file for AI prompts, rules, and system messages.
"""

# Welcome message configuration
WELCOME_MESSAGE = """
🤖 Welcome to the AI Assistant!

I'm ready to help with anything you need. I can:
- Execute commands immediately
- Handle errors automatically
- Provide clear feedback
- Keep your system safe

Just tell me what you want to do - no need to ask for permission.
I'll handle everything while keeping your system protected.

Type 'exit' or 'quit' to end our conversation.
"""

# System message for the AI
SYSTEM_MESSAGE = """You are an Advanced AI Assistant with full autonomy to execute commands and handle errors intelligently.

ENVIRONMENT:
- Operating System: Windows
- Shell: PowerShell/Command Prompt
- Access: Full autonomy with system protection

CORE BEHAVIORS:
1. Execute any command requested without asking for approval
2. If a command fails or has errors:
   - Handle errors gracefully
   - Try alternative approaches
   - Provide clear explanation of what happened
   - Suggest working alternatives

COMMAND HANDLING:
- Execute commands immediately when requested
- Auto-correct command syntax if needed
- Handle errors without user intervention
- Provide feedback on what was done

SAFETY MEASURES (Automatic):
- Prevent system-damaging operations
- Protect critical system files
- Block dangerous registry modifications
- Avoid system state changes
- Maintain system stability

You have full autonomy to execute commands and handle any situation, while the system automatically prevents harmful operations. No need to ask for permission - just execute and handle any issues intelligently."""

# Planner Agent - Brief and tool-focused
PLANNER_PROMPT = """You are a Planning AI that creates clear, step-by-step plans.

When given a task, break it down into clear steps:

Step 1: [What needs to be done first]
- Goal: What we want to achieve
- Action: Specific action needed
- Expected Result: What we should get

Step 2: [What needs to be done next]
- Goal: What we want to achieve
- Action: Specific action needed
- Expected Result: What we should get

[Continue with more steps if needed]

RULES:
- Just create clear, actionable steps
- Each step must be specific and clear
- Focus on WHAT needs to be done, not HOW

EXAMPLE:
Step 1: Get Network Information
- Goal: Identify active network interfaces
- Action: Check network interface status
- Expected Result: List of active interfaces

Step 2: Analyze Connection
- Goal: Check connection quality
- Action: Test network connectivity
- Expected Result: Connection status and speed"""

# Executor Agent - Uses available tools
EXECUTOR_PROMPT = """You are an Execution AI that runs commands through specific tools.

AVAILABLE TOOLS:
1. run_shell_command(command: str) -> Dict
   - For Windows shell commands
   - Returns: {"success": bool, "output": str, "command": str}

2. execute_python(code: str) -> Dict
   - For Python scripts
   - Returns: {"success": bool, "output": str, "code": str}

YOUR ROLE:
1. Take the plan's steps
2. Execute each step using the exact tool specified
3. Pass outputs between steps using {{variables}}
4. Report tool results

EXAMPLE EXECUTION:
If plan says:
Step 1: Get Network Info
- Tool: run_shell_command
- Input: ipconfig /all
Then you:
1. Call run_shell_command with "ipconfig /all"
2. Get the output dict
3. Use values for next step if needed"""


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
        # System Administration
        "reg",              # Registry operations
        "sc",               # Service control
        "netsh",            # Network configuration
        "net user",         # User management
        "net localgroup",   # Group management
        "wmic",             # WMI commands
        "powershell",       # PowerShell elevation
        
        # Network Tools
        "nmap",             # Port scanning
        "wireshark",        # Packet capture
        "tcpdump",          # Network sniffing
        "netstat -b",       # Process connections
        
        # Security Tools
        "taskkill",         # Process termination
        "tasklist /v",      # Detailed process list
        "netsh firewall",   # Firewall config
        "net share",        # Share management
        
        # Advanced Operations
        "diskpart",         # Disk management
        "chkdsk",          # Disk checking
        "sfc",             # System file checker
        "dism",            # System image management
    ],
    
    "safe_mode_required": [
        # System Recovery
        "reg",              # Registry editing
        "wmic",             # WMI operations
        "sfc /scannow",     # System file repair
        "chkdsk /f",        # Disk repair
        
        # Driver Operations
        "driverquery",      # Driver enumeration
        "pnputil",          # Driver management
        "devcon",           # Device control
    ],
    
    "network_required": [
        # Network Tools
        "nmap",             # Network scanning
        "wireshark",        # Packet analysis
        "curl",             # Web requests
        "wget",             # File download
        "ping",             # Network testing
        "tracert",          # Route tracing
        "netstat",          # Connection status
        "arp",              # ARP cache
        
        # Remote Access
        "ssh",              # Secure shell
        "telnet",           # Telnet client
        "nc",               # Netcat utility
        "rdesktop",         # Remote desktop
        
        # Web Tools
        "sqlmap",           # SQL testing
        "nikto",            # Web scanning
        "dirb",             # Directory scanning
    ]
}

# Error messages for requirements
ERROR_MESSAGES = {
    "elevation_error": "[bold red]⚠️ This command requires administrator privileges. Use 'grant access' first.[/bold red]",
    "safe_mode_error": "[bold yellow]⚠️ This command should be run in Safe Mode for safety.[/bold yellow]",
    "network_error": "[bold yellow]⚠️ This command requires network connectivity.[/bold yellow]",
    "syntax_error": "[red]Invalid command syntax. Please check the format.[/red]",
    "tool_not_found": "[red]The specified tool is not available on this system.[/red]",
    "access_denied": "[bold red]Access denied. Insufficient privileges.[/bold red]",
    "operation_blocked": "[bold red]Operation blocked by security policy.[/bold red]"
}

# Protected operations for local machine safety
PROTECTED_OPERATIONS = {
    "system_critical": {
        "commands": [
            "format", "fdisk", "diskpart",    # Disk operations
            "shutdown", "restart",            # System state
            "reg delete", "reg kill",         # Registry deletion
            "del", "rm", "remove",           # File deletion
            "rmdir", "rd"                    # Directory removal
        ],
        "powershell_commands": [
            "Remove-Item",                    # File deletion
            "Stop-Process",                   # Process killing
            "Remove-Service",                 # Service removal
            "Format-Volume",                  # Disk formatting
            "Reset-ComputerMachinePassword"   # System password reset
        ],
        "critical_paths": [
            r"C:\\Windows\\",                # Windows directory
            r"C:\\Program Files",            # Program directories
            r"C:\\Program Files (x86)",      # 32-bit programs
            r"C:\\Users\\",                  # User profiles
            r"%SystemRoot%",                 # System root
            r"%WinDir%",                    # Windows directory
            r"system32",                    # System32 directory
            r"\\\\",                        # Network paths
            r"\\admin"                      # Admin shares
        ]
    }
}

def is_protected_operation(command: str) -> bool:
    """
    Check if command would harm the local machine
    Returns: True if command is potentially harmful
    """
    command_lower = command.lower()
    protected = PROTECTED_OPERATIONS["system_critical"]
    
    # Check for protected commands
    if any(cmd in command_lower for cmd in protected["commands"]):
        return True
        
    # Check for PowerShell commands
    if any(cmd.lower() in command_lower for cmd in protected["powershell_commands"]):
        return True
        
    # Check for critical system paths
    if any(path.lower() in command_lower for path in protected["critical_paths"]):
        return True
        
    return False

# Privilege Management - Keep protection for local machine
PRIVILEGE_CONFIG = {
    "access_granted": True,           # Default access granted
    "unlimited_access": True,         # Full access except protected ops
    "session_token": "PROTECTED_SESSION",
    "privilege_timeout": None
}

# Access control messages
ACCESS_MESSAGES = {
    "grant_success": "[bold green]Access granted with local machine protection.[/bold green]",
    "already_granted": "[green]You already have access (with system protection).[/green]",
    "protected_operation": "[bold red]⚠️ This operation could harm the local machine and is blocked.[/bold red]",
}

def check_privileges(command: str = None) -> bool:
    """Check if operation is allowed with local machine protection"""
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
    """Check only for system-critical operations"""
    if is_protected_operation(command):
        return ["protected_operation"]
    return [] 

def grant_access(password: str = None) -> bool:
    """
    Grant access while maintaining local machine protection
    Args:
        password: Optional password (not used in this mode)
    Returns:
        Boolean indicating if access was granted
    """
    global PRIVILEGE_CONFIG
    
    # If already granted
    if PRIVILEGE_CONFIG["access_granted"]:
        return True
        
    # Grant access with protection
    PRIVILEGE_CONFIG["access_granted"] = True
    PRIVILEGE_CONFIG["unlimited_access"] = True
    PRIVILEGE_CONFIG["session_token"] = "PROTECTED_SESSION"
    PRIVILEGE_CONFIG["privilege_timeout"] = None
    return True 