"""Agent-specific models"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import AgentType, BaseSection, BaseEndpoint, BaseTestCase, ExecutionMetrics


class Section(BaseSection):
    """Extended section with endpoints and test cases"""
    endpoints: List[BaseEndpoint] = Field(
        default_factory=list, description="Section endpoints")
    test_cases: List[BaseTestCase] = Field(
        default_factory=list, description="Section test cases")
    estimated_tokens: int = Field(
        default=0, description="Estimated tokens for processing")


class AgentInput(BaseModel):
    """Input data for agent execution"""
    section: Section = Field(..., description="Section to process")
    swagger_file_id: Optional[str] = Field(None, description="Swagger file ID")
    pdf_file_id: Optional[str] = Field(None, description="PDF file ID")
    user_prompt: Optional[str] = Field(None, description="User instructions")
    agent_config: Dict[str, Any] = Field(
        default_factory=dict, description="Agent-specific configuration")


class AgentOutput(BaseModel):
    """Base output from agent execution"""
    agent_type: AgentType = Field(..., description="Type of agent")
    section_id: str = Field(..., description="Processed section ID")
    success: bool = Field(
        default=False, description="Execution success status")
    artifacts: List[str] = Field(
        default_factory=list, description="Generated artifact paths")
    errors: List[str] = Field(default_factory=list,
                              description="Error messages")
    warnings: List[str] = Field(
        default_factory=list, description="Warning messages")
    metrics: ExecutionMetrics = Field(
        default_factory=ExecutionMetrics, description="Execution metrics")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata")

    # Backward compatibility
    @property
    def processing_time(self) -> float:
        return self.metrics.processing_time

    @processing_time.setter
    def processing_time(self, value: float) -> None:
        self.metrics.processing_time = value

    @property
    def token_usage(self) -> Dict[str, int]:
        return {
            "input_tokens": self.metrics.token_usage.input_tokens,
            "output_tokens": self.metrics.token_usage.output_tokens,
            "total_tokens": self.metrics.token_usage.total_tokens
        }

    @token_usage.setter
    def token_usage(self, value: Dict[str, int]) -> None:
        self.metrics.token_usage.input_tokens = value.get("input_tokens", 0)
        self.metrics.token_usage.output_tokens = value.get("output_tokens", 0)
        self.metrics.token_usage.total_tokens = value.get("total_tokens", 0)
