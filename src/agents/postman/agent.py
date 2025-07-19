# src/agents/postman/agent.py
"""Postman Collection Generation Agent"""
from typing import Any, Dict

from src.config.dependencies import inject
from src.agents.base.agent import BaseAgent
from src.agents.postman.processors import PostmanProcessor
from src.models.base import AgentType
from src.models.agents import AgentInput
from src.models.outputs import PostmanOutput
from src.prompts.manager import PromptManager
from src.services.llm_service import LLMService
from src.services.validation_service import ValidationService


class PostmanAgent(BaseAgent):
    """Agent for generating professional Postman API collections"""

    @inject
    def __init__(self,
                 prompt_manager: PromptManager,
                 llm_service: LLMService,
                 validation_service: ValidationService,
                 postman_processor: PostmanProcessor):
        super().__init__(AgentType.POSTMAN, prompt_manager, llm_service, validation_service)
        self.postman_processor = postman_processor

    def get_system_prompt_name(self) -> str:
        """Get the name of the system prompt template"""
        return "agents/postman/system"

    def get_output_schema_name(self) -> str:
        """Get the name of the output schema"""
        return "postman_collection_schema"

    def build_prompt_variables(self, input_data: AgentInput) -> Dict[str, Any]:
        """Build variables for prompt template rendering"""
        base_variables = super().build_prompt_variables(input_data)

        # Add Postman-specific variables
        postman_variables = {
            "collection_name": f"{input_data.section.name} API Collection",
            "api_version": "v1",  # Could be extracted from API spec
            "environment_types": ["development", "staging", "production"],
            "auth_methods": ["bearer", "apikey", "basic"],
            "test_types": ["status_validation", "schema_validation", "data_extraction", "error_handling"],
            "advanced_features": True,
            "include_documentation": input_data.agent_config.get("generate_postman_docs", True),
            "include_test_scripts": True,
            "include_pre_request_scripts": True
        }

        return {**base_variables, **postman_variables}

    async def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> PostmanOutput:
        """Process LLM output and add to consolidated collection"""
        try:
            collection_data = llm_output.get("collection", {})
            environments_data = llm_output.get("environments", [])
            metadata = llm_output.get("metadata", {})

            # Add section-specific metadata
            section_metadata = {
                **metadata,
                "section_name": input_data.section.name,
                "section_description": input_data.section.description,
                "endpoints_processed": len(input_data.section.endpoints)
            }

            # Extract documentation generation flag from agent config
            generate_docs = input_data.agent_config.get(
                "generate_postman_docs", True)
            self.logger.info(
                f"Documentation generation: {'enabled' if generate_docs else 'disabled'}")

            # Add this section to the consolidated collection (no files generated yet)
            await self.postman_processor.generate_collection_files(
                collection_data=collection_data,
                environments_data=environments_data,
                section_id=input_data.section.section_id,
                metadata=section_metadata
            )

            # Return output without file paths (files will be generated during finalization)
            return PostmanOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=True,
                artifacts=[],  # Will be populated during finalization
                collection_file="",  # Will be set during finalization
                environment_files=[],  # Will be set during finalization
                request_count=metadata.get("total_requests", 0),
                folder_count=len(metadata.get("folder_structure", [])),
                auth_methods=metadata.get("auth_methods", []),
                environment_count=len(environments_data),
                has_tests=True,
                has_pre_request_scripts=True,
                variables_count=len(collection_data.get("variable", [])),
                documentation_file="",  # Will be set during finalization
                is_consolidated=True,
                section_folder_name=input_data.section.name,
                metadata={
                    "collection_summary": metadata.get("collection_summary", ""),
                    "folder_structure": metadata.get("folder_structure", []),
                    "environment_variables": metadata.get("environment_variables", []),
                    "test_coverage": metadata.get("test_coverage", {}),
                    "section_name": input_data.section.name,
                    "endpoints_processed": len(input_data.section.endpoints),
                    "consolidated": True,  # Flag to indicate this is part of a consolidated collection
                    "documentation_generation": generate_docs
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to process Postman output: {e}")
            return PostmanOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=False,
                errors=[f"Postman collection generation failed: {str(e)}"]
            )
