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
from src.prompts import SYSTEM_MESSAGE, WELCOME_MESSAGE, TOOL_CATEGORIES, check_command_requirements, grant_access, check_privileges, ACCESS_MESSAGES, PRIVILEGE_CONFIG, is_protected_operation
import time
import requests

# Initialize Rich console
console = Console()

# Ollama configuration
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "timeout": 60,  # Increased timeout
    "retry_attempts": 3,
    "retry_delay": 2
}

def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{OLLAMA_CONFIG['base_url']}/api/version")
        return response.status_code == 200
    except:
        return False

def initialize_llm():
    """Initialize LLM with retry logic"""
    attempts = 0
    while attempts < OLLAMA_CONFIG["retry_attempts"]:
        try:
            if not check_ollama_connection():
                console.print("[yellow]Waiting for Ollama to be available...[/yellow]")
                time.sleep(OLLAMA_CONFIG["retry_delay"])
                attempts += 1
                continue
                
            return ChatOllama(
                model="llama3.1:8b",
                base_url=OLLAMA_CONFIG["base_url"],
                timeout=OLLAMA_CONFIG["timeout"]
            )
        except Exception as e:
            console.print(f"[yellow]Attempt {attempts + 1} failed: {str(e)}[/yellow]")
            attempts += 1
            time.sleep(OLLAMA_CONFIG["retry_delay"])
            
    raise ConnectionError("Failed to connect to Ollama after multiple attempts")

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
    try:
        llm = initialize_llm()
        llm_with_tools = llm.bind_tools(tools)
    except Exception as e:
        console.print(Panel(f"[red]Failed to initialize Ollama: {str(e)}[/red]", 
                          title="[red]Connection Error[/red]",
                          border_style="red"))
        raise e
    
    # Define chatbot node
    def chatbot(state: State):
        """Process messages and return LLM response"""
        try:
            return {"messages": [llm_with_tools.invoke(state["messages"])]}
        except Exception as e:
            console.print(f"[red]Error in chat processing: {str(e)}[/red]")
            return {"messages": [AIMessage(content="I encountered an error processing your request. Please try again.")]}
    
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
    console.print(Panel(WELCOME_MESSAGE, 
                       title="[bold blue]Penetration Testing Assistant[/bold blue]",
                       border_style="blue",
                       padding=(1, 2)))

def handle_command(user_input: str) -> bool:
    """
    Handle special commands
    Returns: Boolean indicating if command was handled
    """
    if user_input.lower() == "grant access":
        if check_privileges():
            console.print(ACCESS_MESSAGES["already_granted"])
        else:
            if grant_access():
                console.print(ACCESS_MESSAGES["grant_success"])
            else:
                console.print(ACCESS_MESSAGES["grant_failed"])
        return True
    return False

def main():
    """Main chat loop"""
    try:
        # Show welcome message
        display_welcome()
        
        # Check Ollama connection first
        console.print("[yellow]Checking Ollama connection...[/yellow]")
        if not check_ollama_connection():
            console.print(Panel(
                "[red]Error: Cannot connect to Ollama. Please make sure Ollama is running on port 11434.[/red]\n" +
                "[yellow]1. Open a new terminal\n2. Run 'ollama serve'\n3. Try running this program again[/yellow]",
                title="[red]Connection Error[/red]",
                border_style="red"
            ))
            return
            
        console.print("[green]Connected to Ollama successfully![/green]")
        
        # Initialize chat graph
        graph = create_chat_graph()
        
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
                
                # Handle special commands
                if handle_command(user_input):
                    continue
                
                # Check if operation is protected
                if is_protected_operation(user_input):
                    console.print(ACCESS_MESSAGES["protected_operation"])
                    continue
                
                # Check command requirements if it's a command
                if any(tool in user_input.lower() for category in TOOL_CATEGORIES.values() for tool in category["tools"]):
                    requirements = check_command_requirements(user_input.lower())
                    if requirements:
                        console.print("[yellow]Command requirements:[/yellow]")
                        for req in requirements:
                            if req == "elevation_required" and not check_privileges(user_input):
                                console.print(ACCESS_MESSAGES["access_required"])
                                continue
                            console.print(f"- {req}")
                
                # Add user message to history
                message_history.append(HumanMessage(content=user_input))
                
                # Process through graph with status indicator
                with console.status("[bold yellow]Analyzing and executing...[/bold yellow]", spinner="dots"):
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
