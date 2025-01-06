from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from tools import tools
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
import json

# Initialize Rich console
console = Console()

class State(TypedDict):
    """State for managing messages"""
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]

class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
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

def create_chat_graph() -> StateGraph:
    """
    Create the chat workflow graph following LangGraph pattern
    Input: None
    Output: Compiled StateGraph
    """
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
    
    # Add edges
    graph.add_conditional_edges(
        "chatbot",
        should_use_tools,
        {
            "tools": "tools",  # If tools needed, go to tools node
            "__end__": END     # If no tools needed, end
        }
    )
    
    # Add edge from tools back to chatbot and starting edge
    graph.add_edge("tools", "chatbot")
    graph.add_edge(START, "chatbot")
    
    return graph.compile()

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

def main():
    """Main chat loop"""
    try:
        # Initialize chat graph
        graph = create_chat_graph()
        
        # Show welcome message
        display_welcome()
        
        # Initialize message history
        message_history = [
            SystemMessage(content="""You are a friendly and helpful AI assistant that can engage in normal conversation AND use Windows system commands when needed.
            
            For normal conversation:
            - Be friendly and engaging
            - Show personality and empathy
            - Help users with their questions
            - Use markdown formatting when appropriate
            
            For system commands (only when explicitly requested):
            - Use the provided tools only when specifically asked
            - Always think carefully about command safety
            - Format commands properly
            - Explain what each command does before running it
            
            Remember: Only use tools when specifically asked. Otherwise, engage in normal conversation.""")
        ]
        
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
                
                # Initialize state with message history
                initial_state = {
                    "messages": message_history
                }
                
                # Process through graph with status indicator
                with console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
                    for event in graph.stream(initial_state):
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
