"""Content analysis and sectioning service"""
from typing import Any, Dict, List, Optional

from src.config.dependencies import inject
from src.services.llm_service import LLMService
from src.services.validation_service import ValidationService
from src.prompts.manager import PromptManager
from src.models.orchestrator import OrchestratorInput, SectionAnalysis, SectioningStrategy
from src.utils.logger import get_logger


class SectionAnalyzer:
    """Analyzes content and determines optimal sectioning strategy"""

    @inject
    def __init__(self,
                 llm_service: LLMService,
                 prompt_manager: PromptManager,
                 validation_service: ValidationService):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.validation_service = validation_service
        self.logger = get_logger("section_analyzer")

    async def analyze_and_section(
        self,
        orchestrator_input: OrchestratorInput,
        file_ids: Dict[str, Optional[str]]
    ) -> SectionAnalysis:
        """Analyze input content and determine sectioning strategy"""

        try:
            # Build analysis context variables
            prompt_variables = self._build_prompt_variables(orchestrator_input)

            # Get analysis prompt from template
            analysis_prompt = self.prompt_manager.get_prompt(
                "orchestrator/analysis",
                prompt_variables
            )

            # Prepare messages for LLM
            messages = self._build_analysis_messages(
                orchestrator_input, file_ids, analysis_prompt)

            # Get analysis schema
            schema = self.validation_service.get_schema(
                "section_analysis_schema")

            # Make LLM call for analysis with proper token handling
            llm_output, usage_info = await self.llm_service.generate_structured_response(
                messages=messages,
                schema=schema
            )

            # Log token usage
            self.logger.info(
                f"Section analysis completed - Input: {usage_info['input_tokens']}, "
                f"Output: {usage_info['output_tokens']}, "
                f"Total: {usage_info['total_tokens']} tokens"
            )

            # Validate the output
            validation_errors = self.validation_service.validate(
                llm_output, schema)
            if validation_errors:
                self.logger.warning(
                    f"Analysis output validation warnings: {validation_errors}")

            # Convert to SectionAnalysis model
            section_analysis = self._convert_to_section_analysis(
                llm_output, orchestrator_input)

            self.logger.info(
                f"✅ Analysis completed: {section_analysis.total_sections} sections, "
                f"strategy: {section_analysis.strategy_used.value}"
            )

            return section_analysis

        except Exception as e:
            self.logger.error(f"Section analysis failed: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis(orchestrator_input)

    def _build_prompt_variables(self, orchestrator_input: OrchestratorInput) -> Dict[str, Any]:
        """Build variables for prompt template"""
        return {
            "sectioning_strategy": orchestrator_input.sectioning_strategy.value,
            "user_prompt": orchestrator_input.user_prompt or "No specific focus areas provided",
            "has_swagger": orchestrator_input.swagger_file is not None,
            "has_pdf": orchestrator_input.pdf_file is not None,
            "generate_csv": orchestrator_input.generate_csv,
            "generate_karate": orchestrator_input.generate_karate,
            "generate_postman": orchestrator_input.generate_postman
        }

    def _build_analysis_messages(
        self,
        orchestrator_input: OrchestratorInput,
        file_ids: Dict[str, Optional[str]],
        analysis_prompt: str
    ) -> List[Dict[str, Any]]:
        """Build messages for LLM analysis call"""

        messages = [
            {"role": "system", "content": analysis_prompt}
        ]

        # Build user content with file attachments
        user_content = []

        # For Swagger files: Use text content instead of file ID
        if file_ids.get("swagger_content"):
            user_content.append({
                "type": "input_text",
                "text": f"## Swagger/OpenAPI Specification\n\n```yaml\n{file_ids['swagger_content']}\n```"
            })

        # For PDF files: Use file ID (supported by Responses API)
        if file_ids.get("pdf"):
            user_content.append({
                "type": "input_file",
                "file_id": file_ids["pdf"]
            })

        # Add analysis request
        analysis_request = self._build_analysis_request(orchestrator_input)
        user_content.append({
            "type": "input_text",
            "text": analysis_request
        })

        messages.append({
            "role": "user",
            "content": user_content
        })

        return messages

    def _build_analysis_request(self, orchestrator_input: OrchestratorInput) -> str:
        """Build the analysis request text"""
        request_parts = [
            "## Analysis Request",
            "",
            f"**Sectioning Strategy**: {orchestrator_input.sectioning_strategy.value}",
            "",
        ]

        if orchestrator_input.user_prompt:
            request_parts.extend([
                "**User Instructions:**",
                orchestrator_input.user_prompt,
                ""
            ])

        request_parts.extend([
            "**Required Outputs:**",
            f"- CSV Test Cases: {'✓' if orchestrator_input.generate_csv else '✗'}",
            f"- Karate Features: {'✓' if orchestrator_input.generate_karate else '✗'}",
            f"- Postman Collection: {'✓' if orchestrator_input.generate_postman else '✗'}",
            "",
            "Please analyze the provided documentation and create an optimal sectioning plan."
        ])

        return "\n".join(request_parts)

    def _convert_to_section_analysis(
        self,
        llm_output: Dict[str, Any],
        orchestrator_input: OrchestratorInput
    ) -> SectionAnalysis:
        """Convert LLM output to SectionAnalysis model"""

        return SectionAnalysis(
            strategy_used=SectioningStrategy(
                llm_output.get("strategy_used", "auto")),
            total_sections=llm_output.get("total_sections", 0),
            estimated_total_tokens=llm_output.get("estimated_total_tokens", 0),
            sections_summary=llm_output.get("sections_summary", []),
            analysis_reasoning=llm_output.get("analysis_reasoning", "")
        )

    def _create_fallback_analysis(self, orchestrator_input: OrchestratorInput) -> SectionAnalysis:
        """Create a fallback analysis when LLM analysis fails"""
        self.logger.warning("Creating fallback section analysis")

        # Create a simple single-section fallback
        fallback_section = {
            "section_id": "fallback_001",
            "name": "Complete API",
            "description": "Fallback section containing all endpoints",
            "endpoints": [],
            "test_cases": []
        }

        return SectionAnalysis(
            strategy_used=SectioningStrategy.AUTO,
            total_sections=1,
            sections_summary=[fallback_section],
            analysis_reasoning="Fallback analysis due to processing error"
        )
