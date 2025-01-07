"""
Two-agent system with Planner and Executor agents.
"""
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import List, Dict, Any, Annotated, TypedDict
from src.config import get_model_settings
from src.tools import tools
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import json

# Initialize shared components
console = Console()

# Planner Agent - Brief and tool-focused
PLANNER_PROMPT = """You are a Planning AI that creates direct, actionable plans using available tools.

AVAILABLE TOOLS:
1. run_shell_command
   - Executes Windows shell commands
   - Returns: {"success": bool, "output": str, "command": str}

2. execute_python
   - Runs Python security scripts
   - Returns: {"success": bool, "output": str, "code": str}

When given a task, create a step-by-step plan using these exact tools:

Step 1: [Action Name]
- Tool: [run_shell_command/execute_python]
- Input: exact command or code to run
- Goal: what we expect to get

Step 2: [Next Action]
- Tool: [run_shell_command/execute_python]
- Input: command/code (can use {{output_from_step1}})
- Goal: what we'll do with it

RULES:
- Use ONLY the tools listed above
- NO fake tools or commands
- Commands must work on Windows
- All output goes to console
- Use {{variable}} for dynamic values"""

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

class PlannerAgent:
    """Agent responsible for planning operations"""
    
    def __init__(self):
        model_settings = get_model_settings()
        self.llm = ChatOllama(
            model=model_settings["model"],
            temperature=0.7
        )
        self.message_history = [SystemMessage(content=PLANNER_PROMPT)]
        
    def plan(self, user_input: str) -> str:
        """Create a plan based on user input"""
        # Reset message history to ensure clean state
        self.message_history = [SystemMessage(content=PLANNER_PROMPT)]
        self.message_history.append(HumanMessage(content=user_input))
        
        console.print("[bold blue]🤖 Planning...[/bold blue]")
        response = self.llm.invoke(self.message_history)
        console.print("[bold blue]Plan:[/bold blue]")
        console.print(Markdown(response.content))
        return response.content

class ExecutorAgent:
    """Agent responsible for executing plans using tools"""
    
    def __init__(self):
        # Initialize core components
        model_settings = get_model_settings()
        self.llm = ChatOllama(
            model=model_settings["model"],
            temperature=0.2
        )
        self.graph = self._create_execution_graph()
        
        display(
            Image(
                self.graph.get_graph().draw_mermaid_png(
                    draw_method=MermaidDrawMethod.API,
                )
            )
        )
        self.message_history = [SystemMessage(content=EXECUTOR_PROMPT)]
        
    def _create_execution_graph(self) -> StateGraph:
        """Creates and configures the execution workflow graph"""
        graph = StateGraph(State)
        llm_with_tools = self.llm.bind_tools(tools)
        
        def executor(state: State):
            return {"messages": [llm_with_tools.invoke(state["messages"])]}
        
        graph.add_node("executor", executor)
        graph.add_node("tools", BasicToolNode(tools=tools))
        
        def should_use_tools(state: State) -> str:
            if messages := state.get("messages", []):
                last_message = messages[-1]
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    return "tools"
            return "__end__"
        
        graph.add_conditional_edges(
            "executor",
            should_use_tools,
            {
                "tools": "tools",
                "__end__": END
            }
        )
        graph.add_edge("tools", "executor")
        graph.add_edge(START, "executor")
        
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

def create_agents() -> tuple:
    """Create and return both agents"""
    return PlannerAgent(), ExecutorAgent() 

if __name__ == "__main__":
    planner, executor = create_agents()
    planner.plan("Get the current network interface name")
    executor.execute(planner.plan("Get the current network interface name"))
