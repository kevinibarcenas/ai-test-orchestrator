"""Refactored base agent with dependency injection"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import time

from src.prompts.manager import PromptManager
from src.services.llm_service import LLMService
from src.services.validation_service import ValidationService
from src.models.agents import AgentInput, AgentOutput, AgentType
from src.utils.logger import get_logger


class BaseAgent(ABC):
    """Abstract base class for all agents with dependency injection"""

    def __init__(self,
                 agent_type: AgentType,
                 prompt_manager: PromptManager,
                 llm_service: LLMService,
                 validation_service: ValidationService):
        self.agent_type = agent_type
        self.prompt_manager = prompt_manager
        self.llm_service = llm_service
        self.validation_service = validation_service
        self.logger = get_logger(f"agent_{agent_type.value}")

    @abstractmethod
    def get_system_prompt_name(self) -> str:
        """Get the name of the system prompt template"""
        pass

    @abstractmethod
    def get_output_schema_name(self) -> str:
        """Get the name of the output schema"""
        pass

    @abstractmethod
    def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> AgentOutput:
        """Process the LLM output into agent-specific format"""
        pass

    def build_prompt_variables(self, input_data: AgentInput) -> Dict[str, Any]:
        """Build variables for prompt template rendering"""
        return {
            "section_name": input_data.section.name,
            "section_description": input_data.section.description,
            "endpoint_count": len(input_data.section.endpoints),
            "test_case_count": len(input_data.section.test_cases),
            "agent_type": self.agent_type.value
        }

    def build_context_messages(self, input_data: AgentInput) -> List[Dict[str, Any]]:
        """Build context messages for the LLM call"""
        # Get rendered system prompt
        prompt_variables = self.build_prompt_variables(input_data)
        system_prompt = self.prompt_manager.get_prompt(
            self.get_system_prompt_name(),
            prompt_variables
        )

        messages = [
            {"role": "system", "content": system_prompt}
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
        """Execute the agent with input data"""
        start_time = time.time()
        self.logger.info(
            f"Starting {self.agent_type.value} agent for section: {input_data.section.section_id}")

        try:
            # Build messages for LLM
            messages = self.build_context_messages(input_data)

            # Get output schema
            schema = self.validation_service.get_schema(
                self.get_output_schema_name())

            # Make LLM call with structured output
            llm_output = await self.llm_service.generate_structured_response(
                messages=messages,
                schema=schema
            )

            # Validate output
            validation_errors = self.validation_service.validate(
                llm_output, schema)
            if validation_errors:
                self.logger.warning(
                    f"LLM output validation warnings: {validation_errors}")

            # Process into agent-specific output
            agent_output = self.process_llm_output(llm_output, input_data)

            # Update metadata
            processing_time = time.time() - start_time
            agent_output.processing_time = processing_time
            agent_output.success = True

            self.logger.info(
                f"✅ {self.agent_type.value} agent completed in {processing_time:.2f}s")
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
