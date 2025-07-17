"""Base agent class for all specialized agents"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from openai import OpenAI
from pydantic import BaseModel

from config.settings import get_settings
from orchestrator.models.schemas import AgentInput, AgentOutput, AgentType
from orchestrator.utils.logger import get_logger


class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.settings = get_settings()
        self.logger = get_logger(f"agent_{agent_type.value}")
        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.openai_timeout,
            max_retries=self.settings.openai_max_retries
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass

    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for structured output"""
        pass

    @abstractmethod
    def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> AgentOutput:
        """Process the LLM output into agent-specific format"""
        pass

    def build_context_messages(self, input_data: AgentInput) -> list:
        """Build context messages for the LLM call"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]

        # Add file inputs if available
        user_content = []

        if input_data.swagger_file_id:
            user_content.append({
                "type": "input_file",
                "file_id": input_data.swagger_file_id
            })

        if input_data.pdf_file_id:
            user_content.append({
                "type": "input_file",
                "file_id": input_data.pdf_file_id
            })

        # Add section context
        section_context = self._build_section_context(input_data.section)
        user_content.append({
            "type": "input_text",
            "text": section_context
        })

        messages.append({
            "role": "user",
            "content": user_content
        })

        return messages

    def _build_section_context(self, section) -> str:
        """Build context text for the section"""
        context = f"""
## Section: {section.name}

**Description:** {section.description}

**Endpoints to Process:**
"""
        for endpoint in section.endpoints:
            context += f"\n- {endpoint.method} {endpoint.path}"
            if endpoint.summary:
                context += f": {endpoint.summary}"

        context += f"\n\n**Test Cases to Generate:**"
        for test_case in section.test_cases:
            context += f"\n- {test_case.name} ({test_case.test_type})"

        return context

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute the agent with input data

        Args:
            input_data: Agent input containing section and file references

        Returns:
            Agent output with generated artifacts
        """
        start_time = time.time()
        self.logger.info(
            f"Starting {self.agent_type.value} agent for section: {input_data.section.section_id}")

        try:
            # Build messages for LLM
            messages = self.build_context_messages(input_data)

            # Make LLM call with structured output
            response = self.client.responses.create(
                model=self.settings.default_model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": f"{self.agent_type.value}_output",
                        "schema": self.get_output_schema(),
                        "strict": True
                    }
                }
            )

            # Parse LLM output
            import json
            llm_output = json.loads(response.output_text)

            # Process into agent-specific output
            agent_output = self.process_llm_output(llm_output, input_data)

            # Update metadata
            processing_time = time.time() - start_time
            agent_output.processing_time = processing_time
            agent_output.success = True

            # Add token usage if available
            if hasattr(response, 'usage'):
                agent_output.token_usage = {
                    "input_tokens": getattr(response.usage, 'input_tokens', 0),
                    "output_tokens": getattr(response.usage, 'output_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0)
                }

            self.logger.info(
                f"✅ {self.agent_type.value} agent completed in {processing_time:.2f}s "
                f"(tokens: {agent_output.token_usage.get('total_tokens', 0)})"
            )

            return agent_output

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ {self.agent_type.value} agent failed: {e}")

            # Return error output
            return AgentOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=False,
                processing_time=processing_time,
                errors=[str(e)]
            )

    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate LLM output against expected schema"""
        try:
            # Basic validation - can be extended with jsonschema
            required_keys = []
            schema = self.get_output_schema()

            if "required" in schema:
                required_keys = schema["required"]

            for key in required_keys:
                if key not in output:
                    self.logger.warning(
                        f"Missing required key in output: {key}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent"""
        return {
            "type": self.agent_type.value,
            "model": self.settings.default_model,
            "max_tokens": self.settings.max_tokens,
            "timeout": self.settings.agent_timeout
        }
