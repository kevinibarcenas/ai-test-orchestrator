"""Mock agent implementation for agents not yet implemented"""
import asyncio
from typing import Any, Dict

from src.models.base import AgentType
from src.models.agents import AgentInput, AgentOutput
from src.models.outputs import KarateOutput, PostmanOutput
from src.utils.logger import get_logger


class MockAgent:
    """Mock agent implementation for testing and development"""

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.logger = get_logger(f"mock_agent_{agent_type.value}")

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """Mock execution that simulates agent work"""

        self.logger.info(
            f"🔨 Mock {self.agent_type.value} agent executing for section: {input_data.section.section_id}")

        # Simulate some processing time
        await asyncio.sleep(0.5)

        # Create appropriate mock output based on agent type
        if self.agent_type == AgentType.KARATE:
            return self._create_mock_karate_output(input_data)
        elif self.agent_type == AgentType.POSTMAN:
            return self._create_mock_postman_output(input_data)
        else:
            return self._create_generic_mock_output(input_data)

    def _create_mock_karate_output(self, input_data: AgentInput) -> KarateOutput:
        """Create mock Karate output"""
        return KarateOutput(
            agent_type=self.agent_type,
            section_id=input_data.section.section_id,
            success=True,
            artifacts=[f"mock_karate_{input_data.section.section_id}.feature"],
            feature_files=[
                f"mock_karate_{input_data.section.section_id}.feature"],
            data_files=[f"mock_data_{input_data.section.section_id}.json"],
            scenario_count=len(input_data.section.test_cases),
            warnings=["This is a mock Karate agent - no actual files generated"],
            metadata={
                "mock": True,
                "endpoints_processed": len(input_data.section.endpoints),
                "test_cases_converted": len(input_data.section.test_cases)
            }
        )

    def _create_mock_postman_output(self, input_data: AgentInput) -> PostmanOutput:
        """Create mock Postman output"""
        return PostmanOutput(
            agent_type=self.agent_type,
            section_id=input_data.section.section_id,
            success=True,
            artifacts=[
                f"mock_postman_{input_data.section.section_id}.json",
                f"mock_environment_{input_data.section.section_id}.json"
            ],
            collection_file=f"mock_postman_{input_data.section.section_id}.json",
            environment_file=f"mock_environment_{input_data.section.section_id}.json",
            request_count=len(input_data.section.endpoints),
            warnings=["This is a mock Postman agent - no actual files generated"],
            metadata={
                "mock": True,
                "endpoints_processed": len(input_data.section.endpoints),
                "collection_name": f"Mock API Tests - {input_data.section.name}"
            }
        )

    def _create_generic_mock_output(self, input_data: AgentInput) -> AgentOutput:
        """Create generic mock output"""
        return AgentOutput(
            agent_type=self.agent_type,
            section_id=input_data.section.section_id,
            success=True,
            artifacts=[
                f"mock_{self.agent_type.value}_{input_data.section.section_id}.txt"],
            warnings=[
                f"This is a mock {self.agent_type.value} agent - no actual files generated"],
            metadata={
                "mock": True,
                "endpoints_processed": len(input_data.section.endpoints),
                "test_cases_processed": len(input_data.section.test_cases)
            }
        )
