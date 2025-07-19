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
    """Postman collection output - consolidated approach"""
    collection_file: str = Field(
        default="", description="Main consolidated collection file path")
    environment_files: List[str] = Field(
        default_factory=list, description="Environment file paths (typically one)")
    request_count: int = Field(
        default=0, description="Number of requests contributed to collection")
    folder_count: int = Field(
        default=0, description="Number of folders contributed to collection")
    auth_methods: List[str] = Field(
        default_factory=list, description="Authentication methods used")
    environment_count: int = Field(
        default=1, description="Number of environments (typically 1)")

    # Additional Postman-specific metadata
    has_tests: bool = Field(
        default=True, description="Whether collection includes test scripts")
    has_pre_request_scripts: bool = Field(
        default=True, description="Whether collection includes pre-request scripts")
    variables_count: int = Field(
        default=0, description="Number of collection variables")
    documentation_file: str = Field(
        default="", description="Documentation file path")

    # Consolidation-specific fields
    is_consolidated: bool = Field(
        default=True, description="Whether this is part of a consolidated collection")
    section_folder_name: str = Field(
        default="", description="Name of the folder this section contributes")
