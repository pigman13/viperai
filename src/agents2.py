from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import List, Dict, Any, Annotated, TypedDict
from src.config import get_model_settings, OLLAMA_CONFIG
from src.prompts import PLANNER_PROMPT, EXECUTOR_PROMPT, SUMMARY_PROMPT
from src.tools import tools
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import json

console = Console()
base_url = OLLAMA_CONFIG["base_url"]

## initialize langgraph classes
class State(TypedDict):
    """State container for managing message history"""
    # messages: Annotated[List[HumanMessage | AIMessage], add_messages]
    messages: Annotated[List, add_messages]

## initialize tools
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
    
class ChatAgent:
    """Agent responsible for executing plans using tools"""
    
    def __init__(self):
        # Initialize core components
        model_settings = get_model_settings()
        self.llm = ChatOllama(
            model=model_settings["model"],
            temperature=0.2,
            base_url=base_url
        )
        self.graph = self._create_execution_graph()
        
        # Save and display the graph visualization
        graph_image = self.graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
        with open("graph_visualization.png", "wb") as f:
            f.write(graph_image)
        display(Image(graph_image))
        self.message_history = [SystemMessage(content=EXECUTOR_PROMPT)]
        
    def _create_execution_graph(self) -> StateGraph:
        """Creates and configures the execution workflow graph"""
        graph = StateGraph(State)
        llm_with_tools = self.llm.bind_tools(tools)
        
        def executor(state: State):
            messages = state["messages"]
            messages = EXECUTOR_PROMPT + "\n" + messages[-1].content
            print(messages)
            print("using executor")
            return {"messages": [llm_with_tools.invoke(messages)]}
        #EXECUTOR DOES ONLY ONE STEP AND THEN CALLS SUMMARY


        def planner(state: State):
            print("using planner")
            """Planner node that creates execution steps for the executor
            
            Input: State containing message history
            Output: Dict with messages containing step-by-step execution plan"""
            # Get messages from state
            messages = state.get("messages", [])
            if not messages:
                raise ValueError("No messages found in state")
            
            # Get the last user message
            last_message = messages[-1].content
            
            # Create execution plan format
            plan = PLANNER_PROMPT + "\n" + last_message
            # Return formatted plan for executor
            result = self.llm.invoke(plan)
            return {"messages": [result]}

        def summary(state: State):
            print("using summary")
            messages = state.get("messages", [])
            messages.append(HumanMessage(content=SUMMARY_PROMPT))
            result = self.llm.invoke(messages)
            return {"messages": [result]}

        graph.add_node("executor", executor)
        graph.add_node("planner", planner)
        graph.add_node("tools", BasicToolNode(tools=tools))
        graph.add_node("summary", summary)
        
        def should_use_tools(state: State) -> str:
            try:
                if messages := state.get("messages", []):
                    last_message = messages[-1]
                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        return "tools"
                return "summary"
            except:
                return "tools"
        
        def found_error(state: State) -> str:
            try:
                if messages := state.get("messages", []):
                    last_message = messages[-1]
                    if hasattr(last_message, "content") and "error" in last_message.content.lower():
                        return "planner"
                return "summary"
            except:
                return "summary"
            
        # graph.add_conditional_edges(
        #     "executor",
        #     found_error,
        #     {
        #         True: "planner",
        #         False: "__end__"
        #     }
        # )

        # graph.add_conditional_edges(
        #     "planner",
        #     should_use_tools,
        #     {
        #         "tools": "tools",
        #         "__end__": END
        #     }
        # )
        graph.add_conditional_edges(
            "executor",
            should_use_tools,
            {
                "tools": "tools",
                "summary": "summary"
            }
        )
        graph.add_conditional_edges(
            "tools",
            found_error,
            {
                "planner": "planner",
                "summary": "summary"
            }
        )
        # graph.add_edge("tools", "executor")
        graph.add_edge("planner", "executor")
        # graph.add_edge("executor", "planner")
        graph.add_edge(START, "planner")
        graph.add_edge("summary", END)
        
        return graph.compile()
    
    def execute(self, plan: str) -> str:
        """Execute a given plan using available tools"""
        # Reset message history to ensure clean state
        self.message_history = [SystemMessage(content=EXECUTOR_PROMPT)]
        
        execution_prompt = f"""Execute this plan using the appropriate tool:

{plan}

Follow the plan exactly and report results clearly."""
        
        try:
            self.message_history.append(HumanMessage(content=execution_prompt))
            initial_state = {"messages": self.message_history}
            
            result = ""
            for event in self.graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    message = event["messages"][-1]
                    if isinstance(message, ToolMessage):
                        tool_output = json.loads(message.content)
                        console.print(f"[bold blue]Tool Output ({message.name}):[/bold blue]")
                        console.print(tool_output)
                    else:
                        result = message.content
                        console.print("[bold blue]Assistant:[/bold blue]", message.content)
            return result
                            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            console.print(Panel(f"[red]{error_msg}[/red]", 
                              title="[red]Execution Error[/red]", 
                              border_style="red"))
            return error_msg
