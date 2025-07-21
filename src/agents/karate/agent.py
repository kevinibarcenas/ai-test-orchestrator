# src/agents/karate/agent.py
"""Karate Feature Generation Agent"""
from typing import Any, Dict

from src.config.dependencies import inject
from src.config.settings import Settings
from src.agents.base.agent import BaseAgent
from src.agents.karate.processors import KarateProcessor
from src.models.base import AgentType
from src.models.agents import AgentInput
from src.models.outputs import KarateOutput
from src.prompts.manager import PromptManager
from src.services.llm_service import LLMService
from src.services.validation_service import ValidationService


class KarateAgent(BaseAgent):
    """Agent for generating professional Karate feature files"""

    @inject
    def __init__(self,
                 prompt_manager: PromptManager,
                 llm_service: LLMService,
                 validation_service: ValidationService,
                 settings: Settings,
                 karate_processor: KarateProcessor):
        super().__init__(AgentType.KARATE, prompt_manager,
                         llm_service, validation_service, settings)
        self.karate_processor = karate_processor

    def get_system_prompt_name(self) -> str:
        """Get the name of the system prompt template"""
        return "agents/karate/system"

    def get_output_schema_name(self) -> str:
        """Get the name of the output schema"""
        return "karate_feature_schema"

    def build_prompt_variables(self, input_data: AgentInput) -> Dict[str, Any]:
        """Build variables for prompt template rendering"""
        base_variables = super().build_prompt_variables(input_data)

        # Add Karate-specific variables with emphasis on comprehensive scenario generation
        karate_variables = {
            "feature_name": f"{input_data.section.name} API Tests",
            "framework_version": "1.4.x",
            "test_patterns": ["happy_path", "validation", "error_handling", "edge_cases"],
            "karate_features": ["data_driven", "scenario_outline", "background", "conditional_logic"],
            "assertion_types": ["status", "header", "response_time", "schema", "content"],
            "variable_scoping": ["feature", "scenario", "call"],
            "data_file_formats": ["json", "csv", "yaml"],
            "include_documentation": input_data.agent_config.get("generate_karate_docs", True),
            "include_setup_teardown": False,
            "include_examples": True,
            "best_practices": True,
            "comprehensive_scenarios": True,
            "scenario_requirement": f"Generate AT LEAST {len(input_data.section.test_cases)} scenarios - one for each test case plus additional edge cases",
            "endpoint_coverage": f"Ensure all {len(input_data.section.endpoints)} endpoints have comprehensive test coverage"
        }

        return {**base_variables, **karate_variables}

    async def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> KarateOutput:
        """Process LLM output into Karate feature files"""
        try:
            feature_data = llm_output.get("feature_file", {})
            data_files_data = llm_output.get("data_files", [])
            metadata = llm_output.get("metadata", {})

            self.logger.debug(
                f"Feature data keys: {list(feature_data.keys()) if isinstance(feature_data, dict) else 'Not a dict'}")
            self.logger.debug(
                f"Data files count: {len(data_files_data) if isinstance(data_files_data, list) else 'Not a list'}")
            self.logger.debug(
                f"Metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'Not a dict'}")

            # Debug scenarios specifically
            scenarios = feature_data.get("scenarios", [])
            expected_scenarios = len(input_data.section.test_cases)

            self.logger.info(f"LLM generated {len(scenarios)} scenarios")
            self.logger.info(
                f"Expected at least {expected_scenarios} scenarios based on test cases")

            if scenarios:
                # Log first 3 scenario names
                for i, scenario in enumerate(scenarios[:3]):
                    self.logger.debug(
                        f"Scenario {i+1}: {scenario.get('name', 'Unnamed scenario')}")

            # Debug metadata totals
            self.logger.info(
                f"Metadata claims {metadata.get('total_scenarios', 0)} total scenarios")

            # Extract documentation generation flag from agent config
            generate_docs = input_data.agent_config.get(
                "generate_karate_docs", True)
            self.logger.info(
                f"Documentation generation: {'enabled' if generate_docs else 'disabled'}")

            # Extract output directory from agent config
            output_directory = input_data.agent_config.get("output_directory")

            # Generate feature file using processor with conditional documentation and proper output directory
            generated_files = await self.karate_processor.generate_feature_files(
                feature_data=feature_data,
                data_files_data=data_files_data,
                section_id=input_data.section.section_id,
                metadata=metadata,
                generate_docs=generate_docs,
                output_directory=output_directory
            )

            # Validate the generated feature file
            feature_file = generated_files.get("feature")
            is_valid = False
            if feature_file:
                is_valid = await self.karate_processor.validate_feature_file(feature_file)

            # Prepare documentation file path if generated
            documentation_file = ""
            if generate_docs and "documentation" in generated_files:
                documentation_file = str(generated_files["documentation"])

            return KarateOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=True,
                # Convert Path to string
                artifacts=[str(path) for path in generated_files.values()],
                feature_files=[str(generated_files.get("feature", ""))],
                data_files=[str(path) for path in generated_files.values() if str(
                    path).endswith(('.json', '.csv', '.yaml'))],
                scenario_count=metadata.get("total_scenarios", len(scenarios)),
                background_steps=metadata.get("background_steps", []),
                variables_used=metadata.get("variables_used", []),
                data_driven_scenarios=metadata.get("data_driven_count", 0),
                documentation_file=documentation_file,
                metadata={
                    "feature_title": feature_data.get("feature_title", ""),
                    "validation_passed": is_valid,
                    "section_name": input_data.section.name,
                    "endpoints_processed": len(input_data.section.endpoints),
                    "test_coverage": metadata.get("test_coverage", {}),
                    "karate_version": "1.4.x",
                    "execution_requirements": metadata.get("execution_requirements", {}),
                    "framework_features_used": metadata.get("framework_features_used", []),
                    "documentation_generated": generate_docs,
                    "documentation_path": documentation_file if generate_docs else None,
                    "output_directory": str(output_directory) if output_directory else None,
                    "scenarios_expected": expected_scenarios,
                    "scenarios_generated": len(scenarios),
                    "scenario_coverage_ratio": len(scenarios) / max(expected_scenarios, 1),
                    "model_used": self.get_model_for_agent()
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to process Karate output: {e}")
            return KarateOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=False,
                errors=[f"Karate feature generation failed: {str(e)}"]
            )
