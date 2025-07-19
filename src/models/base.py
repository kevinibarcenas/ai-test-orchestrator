"""Base model definitions and common schemas"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents available in the system"""
    CSV = "csv"
    KARATE = "karate"
    POSTMAN = "postman"


class TestCaseType(str, Enum):
    """Types of test cases"""
    FUNCTIONAL = "functional"
    INTEGRATION = "integration"
    NEGATIVE = "negative"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BOUNDARY = "boundary"


class Priority(str, Enum):
    """Test case priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProcessingStatus(str, Enum):
    """Processing status indicators"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseSection(BaseModel):
    """Base section model"""
    section_id: str = Field(..., description="Unique section identifier")
    name: str = Field(..., description="Section name")
    description: str = Field(..., description="Section description")

    class Config:
        use_enum_values = True


class BaseEndpoint(BaseModel):
    """Base endpoint model"""
    path: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    summary: Optional[str] = Field(None, description="Endpoint summary")
    tags: List[str] = Field(default_factory=list, description="Endpoint tags")

    class Config:
        use_enum_values = True


class BaseTestCase(BaseModel):
    """Base test case model"""
    name: str = Field(..., description="Test case name")
    test_type: TestCaseType = Field(..., description="Type of test case")
    priority: Priority = Field(
        default=Priority.MEDIUM, description="Test case priority")
    description: Optional[str] = Field(
        None, description="Test case description")

    class Config:
        use_enum_values = True


class TokenUsage(BaseModel):
    """Token usage information"""
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    total_tokens: int = Field(default=0, description="Total tokens used")


class ExecutionMetrics(BaseModel):
    """Execution performance metrics"""
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = Field(None)
    processing_time: float = Field(
        default=0.0, description="Processing time in seconds")
    token_usage: TokenUsage = Field(default_factory=TokenUsage)

    def mark_completed(self) -> None:
        """Mark execution as completed and calculate processing time"""
        self.end_time = datetime.now()
        self.processing_time = (
            self.end_time - self.start_time).total_seconds()
