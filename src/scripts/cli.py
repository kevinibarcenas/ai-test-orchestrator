"""Refactored CLI with dependency injection"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config.dependencies import get_container
    from src.core.orchestrator import TestOrchestrator
    from src.models.orchestrator import OrchestratorInput, OrchestratorResult, SectioningStrategy
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Make sure you're running from the project root directory")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print(f"Project root: {project_root}")
    sys.exit(1)


app = typer.Typer(name="orchestrator", help="🚀 AI Test Orchestrator CLI")
console = Console()


@app.command()
def generate(
    swagger: Optional[Path] = typer.Option(
        None, "--swagger", "-s", help="Path to Swagger/OpenAPI file"),
    pdf: Optional[Path] = typer.Option(
        None, "--pdf", "-p", help="Path to PDF documentation file"),
    user_prompt: Optional[str] = typer.Option(
        None, "--focus", "-f", help="User instructions (e.g., 'focus on users section')"),
    output: Path = typer.Option(
        "outputs", "--output", "-o", help="Output directory"),
    strategy: SectioningStrategy = typer.Option(
        SectioningStrategy.AUTO, "--strategy", help="Sectioning strategy"),
    csv_only: bool = typer.Option(
        False, "--csv-only", help="Generate only CSV files"),
    parallel: bool = typer.Option(
        True, "--parallel/--sequential", help="Process agents in parallel"),
):
    """🧪 Generate test artifacts from API specifications"""

    # Validate inputs
    if not swagger and not pdf:
        console.print(
            "❌ Error: At least one input file (--swagger or --pdf) must be provided",
            style="red"
        )
        raise typer.Exit(1)

    # Display input summary
    _display_input_summary(swagger, pdf, user_prompt, output, strategy)

    # Create orchestrator input
    orchestrator_input = OrchestratorInput(
        swagger_file=swagger,
        pdf_file=pdf,
        user_prompt=user_prompt,
        output_directory=output,
        sectioning_strategy=strategy,
        generate_karate=not csv_only,
        generate_postman=not csv_only,
        generate_csv=True,
        parallel_processing=parallel
    )

    # Execute orchestration with dependency injection
    result = asyncio.run(_execute_with_progress(orchestrator_input))

    # Display results
    _display_results(result)


@app.command()
def status():
    """📊 Show orchestrator status and configuration"""
    try:
        container = get_container()
        from src.config.settings import Settings
        settings = container.get(Settings)

        status_table = Table(title="🔧 Orchestrator Status")
        status_table.add_column("Setting", style="cyan")
        status_table.add_column("Value", style="green")

        status_table.add_row("Default Model", settings.default_model)
        status_table.add_row("Reasoning Model", settings.reasoning_model)
        status_table.add_row("Output Directory",
                             str(settings.output_directory))
        status_table.add_row("Debug Mode", str(settings.debug_mode))

        console.print(status_table)

    except Exception as e:
        console.print(f"❌ Failed to get status: {e}", style="red")


@app.command()
def prompts():
    """📝 List available prompt templates"""
    try:
        container = get_container()
        from src.prompts.manager import PromptManager
        prompt_manager = container.get(PromptManager)

        available_prompts = prompt_manager.list_available_prompts()

        prompts_table = Table(title="📝 Available Prompt Templates")
        prompts_table.add_column("Prompt Name", style="cyan")
        prompts_table.add_column("Type", style="green")
        prompts_table.add_column("Variables", style="yellow")

        for prompt_name in available_prompts:
            try:
                info = prompt_manager.get_prompt_info(prompt_name)
                variables = ", ".join(info.get("variables", []))
                prompts_table.add_row(
                    prompt_name,
                    info.get("type", "unknown"),
                    variables or "None"
                )
            except Exception:
                prompts_table.add_row(prompt_name, "error", "unknown")

        console.print(prompts_table)

    except Exception as e:
        console.print(f"❌ Failed to list prompts: {e}", style="red")


async def _execute_with_progress(orchestrator_input: OrchestratorInput) -> OrchestratorResult:
    """Execute orchestration with progress display"""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        task = progress.add_task("🚀 Initializing orchestrator...", total=None)

        try:
            # Get orchestrator from dependency injection container
            container = get_container()
            orchestrator = container.get(TestOrchestrator)

            progress.update(task, description="📁 Processing input files...")
            result = await orchestrator.execute(orchestrator_input)

            progress.update(
                task, description="✅ Orchestration completed!", total=1, completed=1)
            return result

        except Exception as e:
            progress.update(task, description=f"❌ Orchestration failed: {e}")
            raise


def _display_input_summary(
    swagger: Optional[Path],
    pdf: Optional[Path],
    user_prompt: Optional[str],
    output: Path,
    strategy: SectioningStrategy
):
    """Display input summary"""
    table = Table(title="🚀 Orchestration Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    input_files = []
    if swagger:
        input_files.append(f"Swagger: {swagger.name}")
    if pdf:
        input_files.append(f"PDF: {pdf.name}")

    table.add_row("Input Files", " | ".join(input_files))
    table.add_row("Output Directory", str(output))
    table.add_row("Sectioning Strategy", strategy.value)

    if user_prompt:
        table.add_row("User Instructions", user_prompt)

    console.print(table)


def _display_results(result: OrchestratorResult):
    """Display orchestration results"""

    if result.success:
        # Success panel
        success_text = f"Execution ID: {result.execution_id}\n"
        success_text += f"Processing Time: {result.total_processing_time:.2f}s\n\n"
        success_text += result.summary

        console.print(Panel(
            success_text,
            title="✅ Generation Successful",
            border_style="green"
        ))

        # Artifacts table
        if result.artifacts_generated:
            artifacts_table = Table(title="📁 Generated Artifacts")
            artifacts_table.add_column("File", style="cyan")
            artifacts_table.add_column("Type", style="green")

            for artifact_path_str in result.artifacts_generated:
                artifact_path = Path(artifact_path_str)
                artifact_type = "CSV" if artifact_path.suffix == ".csv" else "Other"
                artifacts_table.add_row(artifact_path.name, artifact_type)

            console.print(artifacts_table)

        # Performance metrics
        metrics_table = Table(title="📊 Performance Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")

        metrics_table.add_row(
            "Processing Time", f"{result.total_processing_time:.2f}s")
        metrics_table.add_row("Test Cases Generated",
                              str(result.test_cases_generated))
        metrics_table.add_row("Sections Processed",
                              str(result.sections_processed))

        if result.total_token_usage.get("total_tokens"):
            metrics_table.add_row("Total Tokens", str(
                result.total_token_usage["total_tokens"]))

        console.print(metrics_table)

    else:
        # Error panel
        error_text = f"Execution ID: {result.execution_id}\n"
        error_text += f"Processing Time: {result.total_processing_time:.2f}s\n\n"

        if result.errors:
            error_text += "Errors:\n"
            for error in result.errors:
                error_text += f"• {error}\n"

        console.print(Panel(
            error_text,
            title="❌ Generation Failed",
            border_style="red"
        ))


if __name__ == "__main__":
    app()
