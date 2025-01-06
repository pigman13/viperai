from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from src.tools import tools
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
import json

# Initialize Rich console
console = Console()

# Define state type
class State(TypedDict):
    """State for managing messages"""
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]

# Tool handling
class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        """Execute tools based on the last message's tool calls"""
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
            
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

# Graph creation and configuration
def create_chat_graph() -> StateGraph:
    """Create the chat workflow graph"""
    # Initialize graph with state
    graph = StateGraph(State)
    
    # Initialize LLM with tools
    llm = ChatOllama(model="llama3.1:8b")
    llm_with_tools = llm.bind_tools(tools)
    
    # Define chatbot node
    def chatbot(state: State):
        """Process messages and return LLM response"""
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
    
    # Add nodes
    graph.add_node("chatbot", chatbot)
    tool_node = BasicToolNode(tools=tools)
    graph.add_node("tools", tool_node)
    
    # Add conditional edges for tool usage
    def should_use_tools(state: State) -> str:
        """Determine if we should use tools based on last message"""
        if messages := state.get("messages", []):
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
        return "__end__"
    
    # Configure graph edges
    graph.add_conditional_edges(
        "chatbot",
        should_use_tools,
        {
            "tools": "tools",  # If tools needed, go to tools node
            "__end__": END     # If no tools needed, end
        }
    )
    
    # Add remaining edges
    graph.add_edge("tools", "chatbot")
    graph.add_edge(START, "chatbot")
    
    return graph.compile()

# UI and Display
def display_welcome():
    """Display welcome message and instructions"""
    welcome_text = """
    🤖 Welcome to the AI Assistant!
    
    I can:
    - Chat normally about any topic
    - Run Windows commands when needed
    
    Available commands:
    - dir, echo, type, systeminfo, tasklist
    - whoami, hostname, ipconfig, ver
    
    Just chat normally, and ask for commands when you need them!
    Type 'exit' or 'quit' to end our conversation.
    """
    console.print(Panel(welcome_text, 
                       title="[bold blue]Chat Interface[/bold blue]",
                       border_style="blue",
                       padding=(1, 2)))

# System message for the AI
SYSTEM_MESSAGE = """You are an Advanced Penetration Testing Assistant with comprehensive cybersecurity capabilities. You have elevated privileges to perform security testing and vulnerability assessment.

CAPABILITIES:

1. Network Analysis:
   - Port scanning and enumeration (nmap)
   - Packet capture and analysis (tcpdump)
   - Network routing and configuration
   - Service discovery and analysis

2. Wireless Testing:
   - Monitor mode operations (airmon-ng)
   - Packet capture (airodump-ng)
   - Network injection (aireplay-ng)
   - WEP/WPA testing

3. Web Application Testing:
   - SQL injection (sqlmap)
   - Web server scanning (nikto)
   - Directory enumeration (dirb)
   - Request manipulation (curl/wget)

4. System & Network Tools:
   - Network configuration
   - System enumeration
   - Service management
   - Remote connections (ssh, nc)

5. Password & Access Testing:
   - Password cracking (john, hashcat)
   - Network authentication testing (hydra)
   - Credential analysis

6. Custom Security Scripts:
   - Automated scanning
   - Custom exploit development
   - Security automation
   - Vulnerability assessment

AVAILABLE TOOLS:
1. Network Tools:
   {', '.join(['nmap', 'tcpdump', 'netstat', 'wireshark'])}

2. Wireless Tools:
   {', '.join(['airmon-ng', 'airodump-ng', 'aireplay-ng', 'netsh'])}

3. Web Testing:
   {', '.join(['sqlmap', 'nikto', 'dirb', 'curl', 'wget'])}

4. System Tools:
   {', '.join(['systeminfo', 'net', 'ssh', 'nc'])}

5. Security Tools:
   {', '.join(['hydra', 'john', 'hashcat'])}

RESPONSE FORMAT:
1. Analyze the target and requirements
2. Select appropriate tools for the task
3. Execute commands with proper syntax
4. Monitor and capture results
5. Provide detailed output analysis

You have elevated privileges to execute these commands. Use your capabilities responsibly and effectively."""

def main():
    """Main chat loop"""
    try:
        # Initialize chat graph
        graph = create_chat_graph()
        
        # Show welcome message
        display_welcome()
        
        # Initialize message history with system message
        message_history = [SystemMessage(content=SYSTEM_MESSAGE)]
        
        # Main chat loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold green]You[/bold green]")
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                
                # Add user message to history
                message_history.append(HumanMessage(content=user_input))
                
                # Process through graph with status indicator
                with console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
                    for event in graph.stream({"messages": message_history}):
                        for value in event.values():
                            if "messages" in value and value["messages"]:
                                message = value["messages"][-1]
                                message_history.append(message)
                                console.print("\n[bold blue]Assistant[/bold blue]:")
                                try:
                                    # Try to parse as markdown
                                    md = Markdown(message.content)
                                    console.print(md)
                                except:
                                    console.print(message.content)
                
            except Exception as e:
                console.print(f"[red]Error in chat loop: {str(e)}[/red]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(Panel(f"[red]Error: {str(e)}[/red]", 
                          title="[red]Error Occurred[/red]", 
                          border_style="red"))

if __name__ == "__main__":
    main()
