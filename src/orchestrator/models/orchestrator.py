"""Orchestrator-specific models and schemas"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class InputFileType(str, Enum):
    """Supported input file types"""
    SWAGGER = "swagger"
    OPENAPI = "openapi"
    PDF = "pdf"


class SectioningStrategy(str, Enum):
    """Strategies for sectioning API specifications"""
    BY_TAG = "by_tag"              # Group by OpenAPI tags
    # Group by path patterns (/users/*, /orders/*)
    BY_PATH = "by_path"
    BY_METHOD = "by_method"        # Group by HTTP methods
    BY_COMPLEXITY = "by_complexity"  # Group by endpoint complexity
    MANUAL = "manual"              # User-specified sections
    AUTO = "auto"                  # Let AI decide the best strategy


class OrchestratorInput(BaseModel):
    """Input for the orchestrator"""
    # File inputs (at least one required)
    swagger_file: Optional[Path] = Field(
        None, description="Swagger/OpenAPI file path")
    pdf_file: Optional[Path] = Field(
        None, description="PDF documentation file path")

    # User guidance
    user_prompt: Optional[str] = Field(
        None,
        description="User instructions (e.g., 'focus on users section', 'test payment workflows')"
    )

    # Processing options
    sectioning_strategy: SectioningStrategy = Field(
        SectioningStrategy.AUTO,
        description="How to section the API for processing"
    )

    # Output configuration
    output_directory: Path = Field(
        Path("outputs"),
        description="Output directory for generated artifacts"
    )

    # Agent selection
    generate_karate: bool = Field(True, description="Generate Karate features")
    generate_postman: bool = Field(
        True, description="Generate Postman collection")
    generate_csv: bool = Field(True, description="Generate QMetry CSV")

    # Processing options
    max_tokens_per_section: int = Field(
        8000,
        description="Maximum tokens per section to control costs"
    )
    parallel_processing: bool = Field(
        True,
        description="Process agents in parallel for each section"
    )

    @field_validator('swagger_file', 'pdf_file')
    def validate_file_exists(cls, v):
        if v is not None and not v.exists():
            raise ValueError(f"File does not exist: {v}")
        return v

    @field_validator('user_prompt')
    def validate_user_prompt(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v

    @model_validator
    def validate_at_least_one_file(cls, values):
        swagger_file = values.get('swagger_file')
        pdf_file = values.get('pdf_file')

        if not swagger_file and not pdf_file:
            raise ValueError(
                "At least one input file (swagger_file or pdf_file) must be provided")

        return values


class SectionAnalysis(BaseModel):
    """Analysis of how to section the input"""
    strategy_used: SectioningStrategy = Field(
        ..., description="Strategy that was used")
    total_sections: int = Field(..., description="Number of sections created")
    estimated_total_tokens: int = Field(...,
                                        description="Estimated total token usage")
    sections_summary: List[str] = Field(...,
                                        description="Summary of each section")
    user_focus_applied: bool = Field(
        False, description="Whether user prompt influenced sectioning")


class OrchestratorProgress(BaseModel):
    """Progress tracking for orchestrator execution"""
    execution_id: str = Field(..., description="Unique execution ID")
    current_phase: str = Field(..., description="Current execution phase")
    sections_total: int = Field(..., description="Total sections to process")
    sections_completed: int = Field(0, description="Sections completed")
    agents_total: int = Field(..., description="Total agent executions needed")
    agents_completed: int = Field(0, description="Agent executions completed")
    start_time: datetime = Field(default_factory=datetime.now)
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time")

    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage"""
        if self.agents_total == 0:
            return 0.0
        return (self.agents_completed / self.agents_total) * 100


class OrchestratorResult(BaseModel):
    """Complete result from orchestrator execution"""
    execution_id: str = Field(..., description="Unique execution ID")
    success: bool = Field(..., description="Overall execution success")

    # Input summary
    input_files: List[str] = Field(..., description="Input files processed")
    user_prompt: Optional[str] = Field(None, description="User prompt used")

    # Processing summary
    sectioning_analysis: SectionAnalysis = Field(
        ..., description="How content was sectioned")
    sections_processed: int = Field(...,
                                    description="Number of sections successfully processed")

    # Agent results
    karate_results: List[Any] = Field(
        default_factory=list, description="Karate agent outputs")
    postman_results: List[Any] = Field(
        default_factory=list, description="Postman agent outputs")
    csv_results: List[Any] = Field(
        default_factory=list, description="CSV agent outputs")

    # Execution metrics
    total_processing_time: float = Field(...,
                                         description="Total processing time in seconds")
    total_token_usage: Dict[str, int] = Field(
        default_factory=dict, description="Total token usage")

    # Output summary
    artifacts_generated: List[str] = Field(...,
                                           description="Paths to generated artifacts")

    # Quality metrics
    test_cases_generated: int = Field(
        0, description="Total test cases generated")
    endpoints_covered: int = Field(
        0, description="Number of endpoints with test coverage")
    coverage_percentage: float = Field(
        0.0, description="Estimated coverage percentage")

    # Errors and warnings
    errors: List[str] = Field(default_factory=list,
                              description="Execution errors")
    warnings: List[str] = Field(
        default_factory=list, description="Execution warnings")

    # Execution summary
    summary: str = Field(..., description="Human-readable execution summary")
