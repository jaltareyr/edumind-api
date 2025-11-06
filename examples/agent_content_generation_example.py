"""
Example usage of the OpenAI Agents integration for educational content generation.

This example shows how to programmatically use the agent endpoint to generate
educational content from your LightRAG knowledge graph.
"""

import asyncio
import os
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Configuration
API_BASE_URL = os.getenv("LIGHTRAG_API_URL", "http://localhost:8020")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def check_agent_status():
    """Check if the agent system is ready."""
    console.print("\n[bold cyan]Checking agent system status...[/bold cyan]")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/agent/status")
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            
            if status == "operational":
                console.print("[bold green]✓ Agent system is operational[/bold green]")
                return True
            else:
                console.print(f"[bold yellow]⚠ Agent status: {status}[/bold yellow]")
                console.print(f"  {data.get('message')}")
                return False
        else:
            console.print(f"[bold red]✗ Status check failed: {response.status_code}[/bold red]")
            return False


async def generate_study_guide():
    """Generate a study guide for software design principles."""
    
    console.print("\n[bold cyan]Generating Study Guide...[/bold cyan]")
    
    # Define the request
    request_data = {
        "requirements": """
        I want a comprehensive study guide on software design principles 
        for computer science students preparing for their final exams. 
        
        Please cover:
        - SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)
        - DRY (Don't Repeat Yourself)
        - KISS (Keep It Simple, Stupid)
        - YAGNI (You Aren't Gonna Need It)
        - Separation of Concerns
        - Design Patterns (if available in knowledge graph)
        
        Include examples and citations so students can refer back to original sources.
        Generate both PDF and PowerPoint formats.
        """,
        "include_pdf": True,
        "include_ppt": True,
        "output_dir": "./output/study_guides"
    }
    
    console.print("\n[bold]Request:[/bold]")
    console.print(f"  Requirements: {request_data['requirements'][:100]}...")
    console.print(f"  Output formats: PDF={request_data['include_pdf']}, PPT={request_data['include_ppt']}")
    console.print(f"  Output directory: {request_data['output_dir']}")
    
    # Make the request with a progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Agents are analyzing requirements and generating content...", 
            total=None
        )
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agent/generate",
                json=request_data
            )
        
        progress.update(task, completed=True)
    
    # Process response
    if response.status_code == 200:
        data = response.json()
        status = data.get("status")
        
        console.print(f"\n[bold]Response Status:[/bold] {status}")
        console.print(f"[bold]Message:[/bold] {data.get('message')}")
        
        if data.get("generated_files"):
            console.print("\n[bold green]Generated Files:[/bold green]")
            for file_path in data["generated_files"]:
                path = Path(file_path)
                if path.exists():
                    size = path.stat().st_size / 1024  # KB
                    console.print(f"  ✓ {file_path} ({size:.1f} KB)")
                else:
                    console.print(f"  ✗ {file_path} (not found)")
        
        if data.get("topics_covered"):
            console.print("\n[bold]Topics Covered:[/bold]")
            for topic in data["topics_covered"]:
                console.print(f"  • {topic}")
        
        if data.get("error"):
            console.print(f"\n[bold red]Error:[/bold red] {data['error']}")
        
        return status == "success"
    else:
        console.print(f"\n[bold red]Request failed: {response.status_code}[/bold red]")
        console.print(response.text)
        return False


async def generate_presentation():
    """Generate a presentation on microservices architecture."""
    
    console.print("\n[bold cyan]Generating Microservices Presentation...[/bold cyan]")
    
    request_data = {
        "requirements": """
        Create a professional PowerPoint presentation on microservices architecture
        for a technical team. Cover:
        - Introduction to microservices
        - Key architectural patterns (API Gateway, Service Discovery, Circuit Breaker)
        - Benefits and challenges
        - Best practices
        
        Include citations from the knowledge graph where available.
        This is for a professional audience, so use technical language.
        """,
        "include_pdf": False,
        "include_ppt": True,
        "output_dir": "./output/presentations"
    }
    
    console.print(f"\n[bold]Generating PPT only[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Creating presentation...", total=None)
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agent/generate",
                json=request_data
            )
        
        progress.update(task, completed=True)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("generated_files"):
            console.print("\n[bold green]Presentation created:[/bold green]")
            for file_path in data["generated_files"]:
                console.print(f"  ✓ {file_path}")
        
        return data.get("status") == "success"
    else:
        console.print(f"\n[bold red]Failed: {response.status_code}[/bold red]")
        return False


async def main():
    """Main execution function."""
    
    console.print("[bold]OpenAI Agents Integration - Example Usage[/bold]")
    console.print("=" * 60)
    
    # Check prerequisites
    if not OPENAI_API_KEY:
        console.print("\n[bold red]ERROR: OPENAI_API_KEY environment variable not set[/bold red]")
        console.print("Set it with: export OPENAI_API_KEY='your-key'")
        return
    
    console.print(f"\n[bold]Configuration:[/bold]")
    console.print(f"  API URL: {API_BASE_URL}")
    console.print(f"  OpenAI Key: {'*' * 20}{OPENAI_API_KEY[-4:]}")
    
    # Check agent status
    if not await check_agent_status():
        console.print("\n[bold red]Agent system not ready. Aborting.[/bold red]")
        return
    
    # Example 1: Study guide
    console.print("\n" + "=" * 60)
    console.print("[bold]Example 1: Generate Study Guide[/bold]")
    console.print("=" * 60)
    
    success = await generate_study_guide()
    
    if success:
        console.print("\n[bold green]✓ Study guide generated successfully![/bold green]")
    
    # Example 2: Presentation
    console.print("\n" + "=" * 60)
    console.print("[bold]Example 2: Generate Presentation[/bold]")
    console.print("=" * 60)
    
    success = await generate_presentation()
    
    if success:
        console.print("\n[bold green]✓ Presentation generated successfully![/bold green]")
    
    console.print("\n" + "=" * 60)
    console.print("[bold green]Examples completed![/bold green]")
    console.print("=" * 60)


if __name__ == "__main__":
    # Install required packages if not available
    try:
        import httpx
        import rich
    except ImportError:
        console.print("[yellow]Installing required packages...[/yellow]")
        import subprocess
        subprocess.run(["pip", "install", "httpx", "rich"])
        console.print("[green]Packages installed. Please run the script again.[/green]")
        exit(0)
    
    asyncio.run(main())
