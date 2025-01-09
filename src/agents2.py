from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import Annotated, TypedDict, Literal
from src.config import get_model_settings, OLLAMA_CONFIG
from src.prompts import PLANNER_PROMPT, EXECUTOR_PROMPT
from src.tools import tools
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import json
from IPython.display import Image, display
import tempfile
import os

console = Console()
base_url = OLLAMA_CONFIG["base_url"]

class State(TypedDict):
    """State container for managing message history and plan"""
    messages: Annotated[list[BaseMessage], add_messages]
    plan: str | None
    executing: bool

class ChatAgent:
    def __init__(self):
        model_settings = get_model_settings()
        self.llm = ChatOllama(
            model=model_settings["model"],
            temperature=0.2,
            base_url=base_url
        )
        self.graph = self._create_execution_graph()
        
    def _create_execution_graph(self) -> StateGraph:
        graph = StateGraph(State)
        llm_with_tools = self.llm.bind_tools(tools)
        
        # Planner Node
        def planner(state: State):
            if state.get("plan") is None:
                messages = [
                    SystemMessage(content=PLANNER_PROMPT),
                    *state["messages"]
                ]
                response = self.llm.invoke(messages)
                return {
                    "messages": [response],
                    "plan": response.content,
                    "executing": False
                }
            return state
        
        # Executor Node
        def executor(state: State):
            if not state.get("executing", False):
                messages = [
                    SystemMessage(content=EXECUTOR_PROMPT),
                    HumanMessage(content=state["plan"])
                ]
                response = llm_with_tools.invoke(messages)
                return {
                    "messages": [response],
                    "executing": True
                }
            return {
                "messages": [llm_with_tools.invoke(state["messages"])]
            }
        
        # Add nodes
        graph.add_node("planner", planner)
        graph.add_node("executor", executor)
        graph.add_node("tools", ToolNode(tools=tools))
        
        # Routing logic
        def route_next(state: State) -> Literal["executor", "tools", "__end__"]:
            if not state.get("plan"):
                return "executor"
            if not state.get("executing"):
                return "executor"
            return tools_condition(state)
        
        # Add edges
        graph.add_conditional_edges(
            "planner",
            lambda _: "executor",
            {
                "executor": "executor"
            }
        )
        
        graph.add_conditional_edges(
            "executor",
            route_next,
            {
                "executor": "executor",
                "tools": "tools",
                "__end__": "__end__"
            }
        )
        
        graph.add_edge("tools", "executor")
        graph.add_edge(START, "planner")
        
        return graph.compile()
    
    def execute(self, user_input: str) -> str:
        try:
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "plan": None,
                "executing": False
            }
            
            result = ""
            for event in self.graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    message = event["messages"][-1]
                    
                    if "plan" in event and event["plan"] and not event.get("executing", False):
                        console.print("\n[bold blue]Planning Phase:[/bold blue]")
                        console.print(event["plan"])
                        
                    if isinstance(message, ToolMessage):
                        try:
                            tool_output = json.loads(message.content)
                            console.print(f"\n[bold blue]Tool Output ({message.name}):[/bold blue]")
                            console.print(tool_output)
                        except json.JSONDecodeError:
                            console.print(f"\n[bold blue]Tool Output ({message.name}):[/bold blue]")
                            console.print(message.content)
                    else:
                        if event.get("executing", False):
                            console.print("\n[bold blue]Execution Phase:[/bold blue]")
                        result = message.content
                        console.print(message.content)
            
            return result
                            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            console.print(Panel(f"[red]{error_msg}[/red]", 
                              title="[red]Execution Error[/red]", 
                              border_style="red"))
            return error_msg
    
    def visualize_graph(self):
        """Visualize the agent graph structure"""
        try:
            # Create temp file for the image
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                # Generate and save the graph visualization
                graph_image = self.graph.get_graph().draw_mermaid_png()
                tmp.write(graph_image)
                tmp.flush()
                
                # Display using rich
                console.print("\n[bold blue]Agent Graph Structure:[/bold blue]")
                console.print(f"[green]Saved graph visualization to: {tmp.name}[/green]")
                
                return tmp.name
        except Exception as e:
            console.print(f"[red]Failed to visualize graph: {str(e)}[/red]")
            return None
