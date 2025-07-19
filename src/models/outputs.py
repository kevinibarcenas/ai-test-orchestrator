"""Output-specific models for different agent types"""
from typing import List, Optional

from pydantic import Field

from .agents import AgentOutput


class CsvOutput(AgentOutput):
    """CSV/QMetry-specific output"""
    csv_file: Optional[str] = Field(
        None, description="Generated CSV file path")
    test_case_count: int = Field(
        default=0, description="Number of test cases generated")
    headers: List[str] = Field(
        default_factory=list, description="CSV headers used")
    coverage_summary: str = Field(
        default="", description="Test coverage summary")


class KarateOutput(AgentOutput):
    """Karate-specific output"""
    feature_files: List[str] = Field(
        default_factory=list, description="Generated feature files")
    data_files: List[str] = Field(
        default_factory=list, description="Generated data files")
    scenario_count: int = Field(
        default=0, description="Number of scenarios generated")


class PostmanOutput(AgentOutput):
    """Postman-specific output"""
    collection_file: Optional[str] = Field(
        None, description="Generated collection file")
    environment_file: Optional[str] = Field(
        None, description="Generated environment file")
    request_count: int = Field(
        default=0, description="Number of requests in collection")
