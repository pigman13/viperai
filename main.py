"""
Main application entry point for the AI Assistant system.
Uses LangGraph for agent coordination and tool execution.
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
import requests
from src.config import get_model_settings, get_api_settings
from src.agents2 import ChatAgent

console = Console()

def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        api_settings = get_api_settings()
        response = requests.get(f"{api_settings['base_url']}/api/version")
        return response.status_code == 200
    except:
        return False

def display_welcome():
    """Display welcome message"""
    welcome_text = """
🤖 Welcome to the LangGraph AI System!

This system uses:
- A Planner Agent to create detailed execution plans
- An Executor Agent to safely run commands
- LangGraph for agent coordination
- Rich tools for Windows system operations

Available Tools:
1. run_shell_command
   - Windows shell commands
   - Safe command execution
   
2. execute_python
   - Python script execution
   - Security-focused operations

Type 'exit' or 'quit' to end conversation.
"""
    console.print(Panel(welcome_text, 
                       title="[bold blue]AI Assistant[/bold blue]",
                       border_style="blue",
                       padding=(1, 2)))

def main():
    """Main application loop with LangGraph integration"""
    try:
        # Show welcome message
        display_welcome()
        
        # Check Ollama connection
        console.print("[yellow]Checking Ollama connection...[/yellow]")
        if not check_ollama_connection():
            console.print(Panel(
                "[red]Error: Cannot connect to Ollama. Please make sure Ollama is running.[/red]\n" +
                "[yellow]1. Open a new terminal\n2. Run 'ollama serve'\n3. Try running this program again[/yellow]",
                title="[red]Connection Error[/red]",
                border_style="red"
            ))
            return
            
        console.print("[green]Connected to Ollama successfully![/green]")
        
        # Initialize agents
        console.print("[yellow]Initializing LangGraph agents...[/yellow]")
        chat_agent = ChatAgent()
        console.print("[green]Agents initialized successfully![/green]")
        
        # After initializing chat_agent
        console.print("[yellow]Generating graph visualization...[/yellow]")
        graph_path = chat_agent.visualize_graph()
        if graph_path:
            console.print("[green]Graph visualization generated successfully![/green]")
        
        # Main chat loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold green]You[/bold green]")
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                
                # # First, get the plan
                # console.print("\n[bold blue]Planning Phase:[/bold blue]")
                # plan = planner.plan(user_input)
                
                # Then execute the plan
                # console.print("\n[bold blue]Execution Phase:[/bold blue]")
                # result = executor.execute(plan)
                console.print("\n[bold blue]Starting Agent:[/bold blue]")
                result = chat_agent.execute(user_input)
                
                if result:
                    console.print("\n[bold blue]Final Result:[/bold blue]")
                    console.print(Markdown(result))
                
            except Exception as e:
                console.print(Panel(f"[red]Error in chat loop: {str(e)}[/red]",
                                  title="[red]Error[/red]",
                                  border_style="red"))
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(Panel(f"[red]Error: {str(e)}[/red]", 
                          title="[red]Error Occurred[/red]", 
                          border_style="red"))

if __name__ == "__main__":
    main()
