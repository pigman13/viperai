from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import Annotated, TypedDict, Literal
from src.config import get_model_settings, OLLAMA_CONFIG
from src.prompts import SCRIPT_MAKER_PROMPT, EXECUTOR_PROMPT
from src.tools import tools
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import json
from IPython.display import Image, display
import tempfile
import os
import time

console = Console()
base_url = OLLAMA_CONFIG["base_url"]

class State(TypedDict):
    """State container for managing message history and execution state"""
    messages: Annotated[list[BaseMessage], add_messages]
    scripts: str | None
    executing: bool
    tool_results: list | None  # Store tool execution results

class ChatAgent:
    def __init__(self):
        model_settings = get_model_settings()
        self.llm = ChatOllama(
            model=model_settings["model"],
            temperature=0.2,
            base_url=base_url
        )
        self.graph = self._create_execution_graph()
        self.tool_history = []
        
    def _create_execution_graph(self) -> StateGraph:
        graph = StateGraph(State)
        llm_with_tools = self.llm.bind_tools(tools)
        
        # Script Maker Node - Creates implementation scripts
        def script_maker(state: State):
            if state.get("scripts") is None:
                try:
                    messages = [
                        SystemMessage(content=SCRIPT_MAKER_PROMPT),
                        *state["messages"]
                    ]
                    response = llm_with_tools.invoke(messages)
                    try:
                        scripts = json.loads(response.content)
                        if not isinstance(scripts, dict) or "scripts" not in scripts:
                            raise ValueError("Invalid scripts structure")
                    except:
                        # Create simple script structure
                        scripts = {
                            "scripts": [{
                                "step": 1,
                                "implementation": {
                                    "type": "bash",
                                    "code": response.content,
                                    "tool": "run_command",
                                    "parameters": []
                                }
                            }]
                        }
                    return {
                        "messages": [response],
                        "scripts": json.dumps(scripts, indent=2),
                        "executing": False,
                        "tool_results": []
                    }
                except Exception as e:
                    console.print(f"[red]Script generation error: {str(e)}[/red]")
                    return {
                        "messages": [AIMessage(content=f"Script generation error: {str(e)}")],
                        "scripts": json.dumps({"scripts": []}),
                        "executing": False,
                        "tool_results": []
                    }
            return state
        
        # Executor Node - Executes scripts
        def executor(state: State):
            if not state.get("executing", False):
                try:
                    scripts = json.loads(state["scripts"])
                    messages = [
                        SystemMessage(content=EXECUTOR_PROMPT),
                        HumanMessage(content=f"Implementation Scripts: {json.dumps(scripts, indent=2)}")
                    ]
                    response = llm_with_tools.invoke(messages)
                    return {
                        "messages": [response],
                        "executing": True,
                        "tool_results": state.get("tool_results", [])
                    }
                except Exception as e:
                    console.print(f"[red]Execution error: {str(e)}[/red]")
                    return {
                        "messages": [AIMessage(content=f"Execution error: {str(e)}")],
                        "executing": True,
                        "tool_results": state.get("tool_results", [])
                    }
            return {
                "messages": [llm_with_tools.invoke(state["messages"])],
                "tool_results": state.get("tool_results", [])
            }
        
        # Tool execution node - Enhanced with result tracking
        class EnhancedToolNode(ToolNode):
            def __call__(self, inputs: dict):
                outputs = super().__call__(inputs)
                tool_results = inputs.get("tool_results", [])
                
                for message in outputs.get("messages", []):
                    if isinstance(message, ToolMessage):
                        try:
                            result = json.loads(message.content)
                            tool_results.append({
                                "tool": message.name,
                                "result": result,
                                "timestamp": time.time()
                            })
                        except:
                            tool_results.append({
                                "tool": message.name,
                                "result": message.content,
                                "timestamp": time.time()
                            })
                
                outputs["tool_results"] = tool_results
                return outputs
        
        # Add nodes
        graph.add_node("script_maker", script_maker)
        graph.add_node("executor", executor)
        graph.add_node("tools", EnhancedToolNode(tools=tools))
        
        # Enhanced routing logic
        def route_next(state: State) -> Literal["executor", "tools", "__end__"]:
            if not state.get("executing"):
                return "executor"
            if state.get("tool_results") and len(state["tool_results"]) > 0:
                last_result = state["tool_results"][-1]
                if isinstance(last_result.get("result"), dict) and last_result["result"].get("requires_followup"):
                    return "executor"
            return tools_condition(state)
        
        # Add edges with enhanced routing
        graph.add_conditional_edges(
            "script_maker",
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
                "__end__": END
            }
        )
        
        graph.add_edge("tools", "executor")
        graph.add_edge(START, "script_maker")
        
        return graph.compile()
    
    def execute(self, user_input: str) -> str:
        try:
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "scripts": None,
                "executing": False,
                "tool_results": []
            }
            
            result = ""
            for event in self.graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    message = event["messages"][-1]
                    
                    if "scripts" in event and event["scripts"]:
                        console.print("\n[bold blue]Script Generation Phase:[/bold blue]")
                        console.print(event["scripts"])
                        
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
