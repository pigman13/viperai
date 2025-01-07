"""
AI Assistant with Chat and Command Execution Capabilities
Implements a graph-based chat system with tool execution support.
"""

# Standard library imports
import json
from typing import Annotated, List, TypedDict

# Third-party imports
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import (
    HumanMessage, 
    AIMessage, 
    SystemMessage, 
    ToolMessage
)
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# Local imports
from tools import tools

class Agent:
    """
    AI Assistant with chat and command execution capabilities
    Input: None
    Output: Handles chat interactions and command execution
    """
    def __init__(self):
        # Initialize core components
        self.console = Console()
        self.memory = MemorySaver()
        self.graph = self._create_chat_graph()
        self.message_history = self._initialize_message_history()

    def _create_chat_graph(self) -> StateGraph:
        """Creates and configures the chat workflow graph"""
        graph = StateGraph(State)
        llm = ChatOllama(model="mannix/llama3.1-8b-abliterated:tools-q4_0")
        llm_with_tools = llm.bind_tools(tools)
        
        def chatbot(state: State):
            return {"messages": [llm_with_tools.invoke(state["messages"])]}
        
        graph.add_node("chatbot", chatbot)
        graph.add_node("tools", BasicToolNode(tools=tools))
        
        def should_use_tools(state: State) -> str:
            if messages := state.get("messages", []):
                last_message = messages[-1]
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    return "tools"
            return "__end__"
        
        graph.add_conditional_edges(
            "chatbot",
            should_use_tools,
            {
                "tools": "tools",
                "__end__": END
            }
        )
        graph.add_edge("tools", "chatbot")
        graph.add_edge(START, "chatbot")
        
        return graph.compile(checkpointer=self.memory)

    def _initialize_message_history(self):
        """Initialize system message history"""
        return [
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

    def display_welcome(self):
        """Displays welcome message and available commands"""
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
        self.console.print(Panel(welcome_text, 
                           title="[bold blue]Chat Interface[/bold blue]",
                           border_style="blue",
                           padding=(1, 2)))

    def run(self):
        """Main application loop with error handling"""
        try:
            self.display_welcome()
            
            while True:
                try:
                    user_input = Prompt.ask("\n[bold green]You[/bold green]")
                    if user_input.lower() in ["exit", "quit", "bye"]:
                        self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                        break
                    
                    self.message_history.append(HumanMessage(content=user_input))
                    initial_state = {"messages": self.message_history}
                    
                    with self.console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
                        for event in self.graph.stream(initial_state):
                            for value in event.values():
                                if "messages" in value and value["messages"]:
                                    message = value["messages"][-1]
                                    self.message_history.append(message)
                                    self.console.print("\n[bold blue]Assistant[/bold blue]:")
                                    try:
                                        self.console.print(Markdown(message.content))
                                    except:
                                        self.console.print(message.content)
                    
                except Exception as e:
                    self.console.print(f"[red]Error in chat loop: {str(e)}[/red]")
                    
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
        except Exception as e:
            self.console.print(Panel(f"[red]Error: {str(e)}[/red]", 
                              title="[red]Error Occurred[/red]", 
                              border_style="red"))

# Type definitions and base classes
class State(TypedDict):
    """State container for managing message history"""
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]

class BasicToolNode:
    """Node for executing tools requested by the AI"""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        # Validate input
        if not (messages := inputs.get("messages", [])):
            raise ValueError("No message found in input")
            
        # Process tool calls
        outputs = []
        message = messages[-1]
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

if __name__ == "__main__":
    agent = Agent()
    agent.run()
