"""base agent with dependency injection"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import time

from src.config.settings import Settings
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
                 validation_service: ValidationService,
                 settings: Settings):
        self.agent_type = agent_type
        self.prompt_manager = prompt_manager
        self.llm_service = llm_service
        self.validation_service = validation_service
        self.settings = settings
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

    def get_model_for_agent(self) -> str:
        """Get the appropriate model for this agent type"""
        # Use the default model (gpt-4o) for all generation agents
        return self.settings.default_model

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

        # For Swagger files: Check if we have content or file ID
        if hasattr(input_data, 'swagger_content') and input_data.swagger_content:
            user_content.append({
                "type": "input_text",
                "text": f"## Swagger/OpenAPI Specification\n\n```yaml\n{input_data.swagger_content}\n```"
            })
        elif input_data.swagger_file_id:
            # Fallback to file ID if content not available (shouldn't happen with new approach)
            user_content.append({
                "type": "input_file",
                "file_id": input_data.swagger_file_id
            })

        # For PDF files: Use file ID (supported by Responses API)
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
        """Execute the agent with input data and proper token tracking"""
        start_time = time.time()
        agent_model = self.get_model_for_agent()

        self.logger.info(
            f"Starting {self.agent_type.value} agent for section: {input_data.section.section_id} "
            f"using model: {agent_model}"
        )

        try:
            # Build messages for LLM
            messages = self.build_context_messages(input_data)

            # Get output schema
            schema = self.validation_service.get_schema(
                self.get_output_schema_name())

            # Make LLM call with structured output using the appropriate model and get token usage
            llm_output, usage_info = await self.llm_service.generate_structured_response(
                messages=messages,
                schema=schema,
                model=agent_model
            )

            # Log token usage with model information
            self.logger.info(
                f"LLM call completed with {agent_model} - "
                f"Input: {usage_info['input_tokens']}, "
                f"Output: {usage_info['output_tokens']}, "
                f"Total: {usage_info['total_tokens']} tokens"
            )

            # Log reasoning tokens if present (for o1 models, though agents shouldn't use them)
            if usage_info.get('reasoning_tokens', 0) > 0:
                self.logger.info(
                    f"Reasoning tokens used: {usage_info['reasoning_tokens']}"
                )

            # Validate output
            validation_errors = self.validation_service.validate(
                llm_output, schema)
            if validation_errors:
                self.logger.warning(
                    f"LLM output validation warnings: {validation_errors}")

            # Process into agent-specific output
            agent_output = await self.process_llm_output(llm_output, input_data)

            # Update metrics with proper token tracking
            processing_time = time.time() - start_time
            agent_output.metrics.processing_time = processing_time
            agent_output.metrics.token_usage.input_tokens = usage_info["input_tokens"]
            agent_output.metrics.token_usage.output_tokens = usage_info["output_tokens"]
            agent_output.metrics.token_usage.total_tokens = usage_info["total_tokens"]

            # Mark completion time
            agent_output.metrics.mark_completed()
            agent_output.success = True

            self.logger.info(
                f"✅ {self.agent_type.value} agent completed in {processing_time:.2f}s "
                f"(Model: {agent_model}, Tokens: {usage_info['total_tokens']})"
            )
            return agent_output

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ {self.agent_type.value} agent failed: {e}")

            # Return error output with basic metrics
            error_output = AgentOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=False,
                errors=[str(e)]
            )
            error_output.metrics.processing_time = processing_time
            error_output.metrics.mark_completed()

            return error_output

    @abstractmethod
    async def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> AgentOutput:
        """Process the LLM output into agent-specific format"""
        pass
