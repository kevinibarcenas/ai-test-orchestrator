"""Orchestrator-specific models"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import ProcessingStatus
from .outputs import CsvOutput, KarateOutput, PostmanOutput


class InputFileType(str, Enum):
    """Supported input file types"""
    SWAGGER = "swagger"
    OPENAPI = "openapi"
    PDF = "pdf"


class SectioningStrategy(str, Enum):
    """Strategies for sectioning API specifications"""
    BY_TAG = "by_tag"
    BY_PATH = "by_path"
    BY_METHOD = "by_method"
    BY_COMPLEXITY = "by_complexity"
    MANUAL = "manual"
    AUTO = "auto"


class OrchestratorInput(BaseModel):
    """Input configuration for orchestrator"""
    # File inputs
    swagger_file: Optional[Path] = Field(
        None, description="Swagger/OpenAPI file path")
    pdf_file: Optional[Path] = Field(
        None, description="PDF documentation file path")

    # User guidance
    user_prompt: Optional[str] = Field(
        None, description="User instructions and focus areas")

    # Processing options
    sectioning_strategy: SectioningStrategy = Field(
        SectioningStrategy.AUTO,
        description="Strategy for sectioning the API"
    )

    # Output configuration
    output_directory: Path = Field(
        Path("outputs"), description="Output directory")

    # Agent enablement
    generate_csv: bool = Field(True, description="Generate CSV test cases")
    generate_karate: bool = Field(True, description="Generate Karate tests")
    generate_postman: bool = Field(
        True, description="Generate Postman collection")

    # Processing options
    parallel_processing: bool = Field(
        True, description="Process agents in parallel")
    max_tokens_per_section: int = Field(
        8000, description="Maximum tokens per section")

    @model_validator(mode='after')
    def validate_inputs(self):
        """Validate that at least one input file is provided"""
        if not self.swagger_file and not self.pdf_file:
            raise ValueError(
                "At least one input file (swagger_file or pdf_file) must be provided")
        return self

    @field_validator('output_directory')
    def create_output_directory(cls, v):
        """Ensure output directory exists"""
        v.mkdir(parents=True, exist_ok=True)
        return v


class SectionAnalysis(BaseModel):
    """Analysis of how content should be sectioned"""
    strategy_used: SectioningStrategy = Field(
        ..., description="Strategy that was used")
    total_sections: int = Field(..., description="Number of sections created")
    estimated_total_tokens: int = Field(...,
                                        description="Estimated total tokens needed")
    sections_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Summary of each section"
    )
    analysis_reasoning: str = Field(
        "", description="Reasoning behind the sectioning strategy")


class OrchestratorResult(BaseModel):
    """Complete result from orchestrator execution"""
    # Execution metadata
    execution_id: str = Field(..., description="Unique execution identifier")
    success: bool = Field(..., description="Overall execution success")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Execution timestamp")

    # Input information
    input_files: List[str] = Field(...,
                                   description="Input file paths processed")
    user_prompt: Optional[str] = Field(
        None, description="User instructions provided")

    # Processing results
    sectioning_analysis: SectionAnalysis = Field(
        ..., description="Sectioning analysis results")
    sections_processed: int = Field(...,
                                    description="Number of sections successfully processed")

    # Agent outputs
    csv_outputs: List[CsvOutput] = Field(
        default_factory=list, description="CSV agent results")
    karate_outputs: List[KarateOutput] = Field(
        default_factory=list, description="Karate agent results")
    postman_outputs: List[PostmanOutput] = Field(
        default_factory=list, description="Postman agent results")

    # Performance metrics
    total_processing_time: float = Field(...,
                                         description="Total processing time in seconds")
    total_token_usage: Dict[str, int] = Field(
        default_factory=dict, description="Total token usage")

    # Status and errors
    status: ProcessingStatus = Field(
        default=ProcessingStatus.COMPLETED, description="Final status")
    errors: List[str] = Field(default_factory=list,
                              description="Error messages")
    warnings: List[str] = Field(
        default_factory=list, description="Warning messages")

    # Summary
    summary: str = Field(..., description="Human-readable execution summary")

    # Computed properties
    @property
    def test_cases_generated(self) -> int:
        """Total test cases generated across all outputs"""
        return sum(output.test_case_count for output in self.csv_outputs)

    @property
    def artifacts_generated(self) -> List[str]:
        """All artifacts generated by agents"""
        artifacts = []
        for outputs in [self.csv_outputs, self.karate_outputs, self.postman_outputs]:
            for output in outputs:
                artifacts.extend(output.artifacts)
        return artifacts

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred during processing"""
        if self.errors:
            return True

        for outputs in [self.csv_outputs, self.karate_outputs, self.postman_outputs]:
            for output in outputs:
                if output.errors:
                    return True
        return False
