"""Pydantic models for agent inputs and outputs"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from models.agents import Section


class AgentType(str, Enum):
    """Available agent types"""
    KARATE = "karate"
    POSTMAN = "postman"
    CSV = "csv"
    DOCUMENTATION = "documentation"


class TestCaseType(str, Enum):
    """Test case types"""
    HAPPY_PATH = "happy_path"
    EDGE_CASE = "edge_case"
    ERROR_CASE = "error_case"
    SECURITY = "security"
    PERFORMANCE = "performance"


class HttpMethod(str, Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class EndpointInfo(BaseModel):
    """Information about an API endpoint"""
    path: str = Field(..., description="Endpoint path")
    method: HttpMethod = Field(..., description="HTTP method")
    summary: Optional[str] = Field(None, description="Endpoint summary")
    description: Optional[str] = Field(
        None, description="Detailed description")
    tags: List[str] = Field(default_factory=list, description="Endpoint tags")
    parameters: List[Dict[str, Any]] = Field(
        default_factory=list, description="Parameters")
    request_body: Optional[Dict[str, Any]] = Field(
        None, description="Request body schema")
    responses: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Response schemas")
    security: List[Dict[str, Any]] = Field(
        default_factory=list, description="Security requirements")


class TestCase(BaseModel):
    """Individual test case definition"""
    id: str = Field(..., description="Unique test case ID")
    name: str = Field(..., description="Test case name")
    description: str = Field(..., description="Test case description")
    endpoint: EndpointInfo = Field(..., description="Target endpoint")
    test_type: TestCaseType = Field(..., description="Type of test case")
    priority: str = Field(default="Medium", description="Test priority")
    test_data: Dict[str, Any] = Field(
        default_factory=dict, description="Test input data")
    expected_result: Dict[str, Any] = Field(
        default_factory=dict, description="Expected results")
    assertions: List[str] = Field(
        default_factory=list, description="Test assertions")
    preconditions: List[str] = Field(
        default_factory=list, description="Prerequisites")
    postconditions: List[str] = Field(
        default_factory=list, description="Cleanup steps")


class TestSection(BaseModel):
    """A section of related test cases"""
    section_id: str = Field(..., description="Section identifier")
    name: str = Field(..., description="Section name")
    description: str = Field(..., description="Section description")
    endpoints: List[EndpointInfo] = Field(...,
                                          description="Endpoints in this section")
    test_cases: List[TestCase] = Field(..., description="Generated test cases")
    estimated_tokens: int = Field(
        default=0, description="Estimated token usage")


class AgentInput(BaseModel):
    """Input data for agents"""
    section: Section = Field(..., description="Section to process")
    user_prompt: Optional[str] = Field(
        None, description="User instructions and focus areas")
    # File references
    swagger_file_id: Optional[str] = Field(
        None, description="OpenAI file ID for swagger")
    pdf_file_id: Optional[str] = Field(
        None, description="OpenAI file ID for PDF")
    # Text content (for YAML files that don't need upload)
    swagger_content: Optional[str] = Field(
        None, description="Raw Swagger/YAML content as text")
    templates: Dict[str, Any] = Field(
        default_factory=dict, description="Template configurations")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context")


class AgentOutput(BaseModel):
    """Base output from agents"""
    agent_type: AgentType = Field(...,
                                  description="Type of agent that generated this")
    section_id: str = Field(..., description="Section ID processed")
    success: bool = Field(..., description="Whether processing succeeded")
    artifacts: List[str] = Field(
        default_factory=list, description="Generated artifact file paths")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Processing metadata")
    errors: List[str] = Field(default_factory=list,
                              description="Any errors encountered")
    warnings: List[str] = Field(
        default_factory=list, description="Any warnings")
    processing_time: float = Field(
        default=0.0, description="Processing time in seconds")
    token_usage: Dict[str, int] = Field(
        default_factory=dict, description="Token usage stats")


class KarateOutput(AgentOutput):
    """Karate-specific output"""
    feature_files: List[str] = Field(
        default_factory=list, description="Generated .feature files")
    test_count: int = Field(
        default=0, description="Number of test scenarios generated")


class PostmanOutput(AgentOutput):
    """Postman-specific output"""
    collection_file: Optional[str] = Field(
        None, description="Generated collection file")
    environment_file: Optional[str] = Field(
        None, description="Generated environment file")
    request_count: int = Field(
        default=0, description="Number of requests in collection")


class CsvOutput(AgentOutput):
    """CSV/QMetry-specific output"""
    csv_file: Optional[str] = Field(None, description="Generated CSV file")
    test_case_count: int = Field(
        default=0, description="Number of test cases in CSV")


class AgentExecutionResult(BaseModel):
    """Complete execution result from orchestrator"""
    execution_id: str = Field(..., description="Unique execution ID")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Execution timestamp")
    input_files: List[str] = Field(..., description="Input file paths")
    sections_processed: int = Field(...,
                                    description="Number of sections processed")
    karate_output: Optional[KarateOutput] = Field(
        None, description="Karate agent results")
    postman_output: Optional[PostmanOutput] = Field(
        None, description="Postman agent results")
    csv_output: Optional[CsvOutput] = Field(
        None, description="CSV agent results")
    total_processing_time: float = Field(
        default=0.0, description="Total processing time")
    total_token_usage: Dict[str, int] = Field(
        default_factory=dict, description="Total token usage")
    success: bool = Field(..., description="Overall success status")
    summary: str = Field(..., description="Execution summary")
