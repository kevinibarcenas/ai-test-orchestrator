"""Enhanced CLI with user prompt support"""
from orchestrator.models.orchestrator import OrchestratorInput, SectioningStrategy
from orchestrator.core.orchestrator import TestOrchestrator
import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


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
            "❌ Error: At least one input file (--swagger or --pdf) must be provided", style="red")
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

    # Execute orchestration
    result = asyncio.run(_execute_with_progress(orchestrator_input))

    # Display results
    _display_results(result)


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

    if swagger:
        table.add_row("Swagger File", str(swagger))
    if pdf:
        table.add_row("PDF File", str(pdf))
    if user_prompt:
        table.add_row("User Focus", user_prompt)

    table.add_row("Output Directory", str(output))
    table.add_row("Sectioning Strategy", strategy.value)

    console.print(table)
    console.print()


async def _execute_with_progress(orchestrator_input: OrchestratorInput):
    """Execute orchestration with progress display"""
    orchestrator = TestOrchestrator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:

        task = progress.add_task("Initializing orchestration...", total=None)

        try:
            # Update progress for different phases
            progress.update(task, description="📁 Uploading files...")
            await asyncio.sleep(0.1)  # Brief pause to show progress

            progress.update(task, description="🔍 Analyzing content...")
            await asyncio.sleep(0.1)

            progress.update(task, description="🧪 Generating test cases...")

            # Execute orchestration
            result = await orchestrator.execute(orchestrator_input)

            progress.update(task, description="✅ Generation complete!")
            return result

        except Exception as e:
            progress.update(task, description=f"❌ Failed: {str(e)}")
            raise


def _display_results(result):
    """Display orchestration results"""
    if result.success:
        # Success panel
        console.print(Panel(
            result.summary,
            title="✅ Generation Complete",
            border_style="green"
        ))

        # Artifacts table
        if result.artifacts_generated:
            artifacts_table = Table(title="📁 Generated Artifacts")
            artifacts_table.add_column("Artifact", style="cyan")
            artifacts_table.add_column("Type", style="yellow")

            for artifact in result.artifacts_generated:
                artifact_path = Path(artifact)
                artifact_type = artifact_path.suffix.upper().replace('.', '')
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


@app.command()
def sample():
    """📝 Generate sample files for testing"""
    console.print(
        "🔧 This command will generate sample Swagger and test files...")

    # Create sample swagger file
    sample_dir = Path("samples")
    sample_dir.mkdir(exist_ok=True)

    console.print(f"✅ Sample files would be created in: {sample_dir}")
    console.print(
        "💡 Use the main 'generate' command with your actual API files")


@app.command()
def status():
    """📊 Show orchestrator status and configuration"""
    from config.settings import get_settings
    settings = get_settings()

    status_table = Table(title="🔧 Orchestrator Status")
    status_table.add_column("Setting", style="cyan")
    status_table.add_column("Value", style="green")

    status_table.add_row("Default Model", settings.default_model)
    status_table.add_row("Reasoning Model", settings.reasoning_model)
    status_table.add_row("Max Tokens", str(settings.max_tokens))
    status_table.add_row("Output Directory", str(settings.output_directory))
    status_table.add_row("Debug Mode", str(settings.debug_mode))

    console.print(status_table)


if __name__ == "__main__":
    app()
