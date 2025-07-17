"""Main CLI entry point for the orchestrator"""
from rich.console import Console
import typer
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


app = typer.Typer(name="orchestrator", help="AI Test Orchestrator CLI")
console = Console()


@app.command()
def generate(
    swagger: Path = typer.Option(..., help="Path to swagger/OpenAPI file"),
    pdf: Path = typer.Option(None, help="Path to TDD PDF file"),
    output: Path = typer.Option("outputs", help="Output directory")
):
    """Generate test artifacts from API specifications"""
    console.print(f"🚀 Generating test artifacts from {swagger}")

    console.print("✅ Generation complete!", style="green")


if __name__ == "__main__":
    app()
