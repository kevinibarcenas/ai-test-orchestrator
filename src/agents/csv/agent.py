"""CSV agent using dependency injection and external prompts"""
from typing import Any, Dict

from src.config.dependencies import inject
from src.agents.base.agent import BaseAgent
from src.agents.csv.processors import CSVProcessor
from src.models.base import AgentType
from src.models.agents import AgentInput
from src.models.outputs import CsvOutput
from src.prompts.manager import PromptManager
from src.services.llm_service import LLMService
from src.services.validation_service import ValidationService


class CsvAgent(BaseAgent):
    """Agent for generating QMetry-compatible CSV test cases"""

    @inject
    def __init__(self,
                 prompt_manager: PromptManager,
                 llm_service: LLMService,
                 validation_service: ValidationService,
                 csv_processor: CSVProcessor):
        super().__init__(AgentType.CSV, prompt_manager, llm_service, validation_service)
        self.csv_processor = csv_processor

    def get_system_prompt_name(self) -> str:
        """Get the name of the system prompt template"""
        return "agents/csv/system"

    def get_output_schema_name(self) -> str:
        """Get the name of the output schema"""
        return "csv_test_case_schema"

    def build_prompt_variables(self, input_data: AgentInput) -> Dict[str, Any]:
        """Build variables for prompt template rendering"""
        base_variables = super().build_prompt_variables(input_data)

        # Add CSV-specific variables
        csv_variables = {
            "csv_headers": ", ".join(self.csv_processor.get_default_headers()),
            "qmetry_compatible": True,
            "target_coverage": "70%",
            "test_case_types": ["Functional", "Integration", "Negative", "Security", "Boundary"],
            "priority_levels": ["High", "Medium", "Low"]
        }

        return {**base_variables, **csv_variables}

    async def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> CsvOutput:
        """Process LLM output into CSV files"""
        try:
            test_cases = llm_output.get("test_cases", [])
            metadata = llm_output.get("metadata", {})

            # Generate CSV file using processor
            csv_file_path = await self.csv_processor.generate_csv_file(
                test_cases=test_cases,
                section_id=input_data.section.section_id,
                headers=metadata.get(
                    "csv_headers", self.csv_processor.get_default_headers())
            )

            # Validate the generated CSV
            is_valid = await self.csv_processor.validate_csv_output(csv_file_path)
            if not is_valid:
                self.logger.warning("Generated CSV file failed validation")

            return CsvOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=True,
                artifacts=[str(csv_file_path)],
                csv_file=str(csv_file_path),
                test_case_count=len(test_cases),
                headers=metadata.get(
                    "csv_headers", self.csv_processor.get_default_headers()),
                coverage_summary=metadata.get("coverage_summary", ""),
                metadata={
                    "total_test_cases": len(test_cases),
                    "test_distribution": metadata.get("test_distribution", {}),
                    "validation_passed": is_valid,
                    "section_name": input_data.section.name,
                    "endpoints_processed": len(input_data.section.endpoints)
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to process CSV output: {e}")
            return CsvOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=False,
                errors=[f"CSV processing failed: {str(e)}"]
            )
