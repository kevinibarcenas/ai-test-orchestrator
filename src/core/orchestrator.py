import asyncio
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List, Optional

from src.config.dependencies import inject
from src.config.settings import Settings
from src.core.file_manager import FileManager
from src.core.section_analyzer import SectionAnalyzer
from src.core.result_compiler import ResultCompiler
from src.core.agent_factory import AgentFactory
from src.models.orchestrator import OrchestratorInput, OrchestratorResult, ProcessingStatus
from src.models.agents import AgentInput, Section
from src.prompts.manager import PromptManager
from src.utils.logger import get_logger


class TestOrchestrator:
    """Simplified main orchestrator with dependency injection"""

    @inject
    def __init__(self,
                 settings: Settings,
                 file_manager: FileManager,
                 prompt_manager: PromptManager,
                 section_analyzer: SectionAnalyzer,
                 result_compiler: ResultCompiler,
                 agent_factory: AgentFactory):
        self.settings = settings
        self.file_manager = file_manager
        self.prompt_manager = prompt_manager
        self.section_analyzer = section_analyzer
        self.result_compiler = result_compiler
        self.agent_factory = agent_factory
        self.logger = get_logger("orchestrator")

    async def execute(self, orchestrator_input: OrchestratorInput) -> OrchestratorResult:
        """Execute the complete test generation workflow"""
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        self.logger.info(f"🚀 Starting orchestration execution: {execution_id}")
        self.logger.info(f"📋 Documentation settings: Master={orchestrator_input.generate_documentation}, "
                         f"CSV={orchestrator_input.generate_csv_docs}, "
                         f"Karate={orchestrator_input.generate_karate_docs}, "
                         f"Postman={orchestrator_input.generate_postman_docs}")

        try:
            # Phase 1: Upload and validate files
            self.logger.info("📁 Phase 1: Uploading input files...")
            file_ids = await self._upload_input_files(orchestrator_input)

            # Phase 2: Analyze and section content
            self.logger.info(
                "🔍 Phase 2: Analyzing content and determining sections...")
            sectioning_analysis = await self.section_analyzer.analyze_and_section(
                orchestrator_input, file_ids
            )

            # Phase 3: Execute agents for each section
            self.logger.info(
                "🤖 Phase 3: Executing agents for test generation...")
            agent_results = await self._execute_agents_for_sections(
                orchestrator_input, sectioning_analysis.sections_summary, file_ids
            )

            # Phase 4: Compile final results
            self.logger.info("📊 Phase 4: Compiling final results...")
            result = await self.result_compiler.compile_result(
                execution_id=execution_id,
                orchestrator_input=orchestrator_input,
                sectioning_analysis=sectioning_analysis,
                agent_results=agent_results,
                start_time=start_time
            )

            self.logger.info(
                f"✅ Orchestration completed: {execution_id} "
                f"({result.total_processing_time:.2f}s, {result.test_cases_generated} test cases)"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Orchestration failed: {execution_id} - {e}")

            return await self.result_compiler.create_error_result(
                execution_id=execution_id,
                orchestrator_input=orchestrator_input,
                error=e,
                processing_time=processing_time
            )

    async def _upload_input_files(self, orchestrator_input: OrchestratorInput) -> Dict[str, Optional[str]]:
        """Upload input files and return file IDs - Only upload PDFs, read YAML as text"""
        file_ids = {"swagger": None, "pdf": None, "swagger_content": None}

        # For Swagger/YAML files: Read content as text instead of uploading
        if orchestrator_input.swagger_file:
            self.logger.info(
                f"Reading Swagger file as text: {orchestrator_input.swagger_file.name}")
            try:
                with open(orchestrator_input.swagger_file, 'r', encoding='utf-8') as f:
                    swagger_content = f.read()
                file_ids["swagger_content"] = swagger_content
                self.logger.info(
                    f"✅ Swagger content read: {len(swagger_content)} characters")
            except Exception as e:
                self.logger.error(f"❌ Failed to read Swagger file: {e}")
                raise

        # For PDF files: Upload them to get file IDs (as they're supported by Responses API)
        if orchestrator_input.pdf_file:
            self.logger.info(
                f"Uploading PDF file: {orchestrator_input.pdf_file.name}")
            pdf_info = await self.file_manager.upload_file(
                orchestrator_input.pdf_file, purpose="user_data"
            )
            file_ids["pdf"] = pdf_info.file_id
            self.logger.info(f"✅ PDF uploaded: {pdf_info.file_id}")

        return file_ids

    def _create_agent_input(self, section_data: Dict, orchestrator_input: OrchestratorInput, file_ids: Dict) -> AgentInput:
        """Create AgentInput with proper configuration including documentation flags"""
        section = self._create_section_from_data(section_data)

        return AgentInput(
            section=section,
            swagger_file_id=file_ids.get("swagger"),
            pdf_file_id=file_ids.get("pdf"),
            swagger_content=file_ids.get("swagger_content"),
            user_prompt=orchestrator_input.user_prompt,
            agent_config={
                # Documentation control flags
                "generate_documentation": orchestrator_input.generate_documentation,
                "generate_csv_docs": orchestrator_input.generate_csv_docs,
                "generate_karate_docs": orchestrator_input.generate_karate_docs,
                "generate_postman_docs": orchestrator_input.generate_postman_docs,

                # Processing configuration
                "max_tokens_per_section": orchestrator_input.max_tokens_per_section,
                "sectioning_strategy": orchestrator_input.sectioning_strategy.value,
                "parallel_processing": orchestrator_input.parallel_processing
            }
        )

    async def _execute_agents_for_sections(
        self,
        orchestrator_input: OrchestratorInput,
        sections: List[Dict],
        file_ids: Dict[str, Optional[str]]
    ) -> Dict[str, List]:
        """Execute enabled agents for all sections with Postman consolidation"""
        results = {"csv": [], "karate": [], "postman": []}

        # Create SHARED Postman agent instance if generating Postman collections
        shared_postman_agent = None
        if orchestrator_input.generate_postman:
            shared_postman_agent = self.agent_factory.create_postman_agent()
            # Reset the processor state for a fresh collection
            shared_postman_agent.postman_processor.reset_state()

        # Create agent inputs for each section with proper configuration
        agent_inputs = []
        for section_data in sections:
            agent_input = self._create_agent_input(
                section_data, orchestrator_input, file_ids)
            agent_inputs.append(agent_input)

        # Execute agents based on configuration
        if orchestrator_input.parallel_processing:
            await self._execute_agents_parallel_with_shared(orchestrator_input, agent_inputs, results, shared_postman_agent)
        else:
            await self._execute_agents_sequential_with_shared(orchestrator_input, agent_inputs, results, shared_postman_agent)

        # POSTMAN FINALIZATION: Generate consolidated collection after all sections are processed
        if orchestrator_input.generate_postman and results["postman"] and shared_postman_agent:
            await self._finalize_postman_collection(orchestrator_input, results, shared_postman_agent)

        return results

    async def _execute_agents_parallel(
        self,
        orchestrator_input: OrchestratorInput,
        agent_inputs: List[AgentInput],
        results: Dict[str, List]
    ) -> None:
        """Execute agents in parallel for better performance"""
        tasks = []

        for agent_input in agent_inputs:
            if orchestrator_input.generate_csv:
                csv_agent = self.agent_factory.create_csv_agent()
                tasks.append(("csv", csv_agent.execute(agent_input)))

            if orchestrator_input.generate_karate:
                karate_agent = self.agent_factory.create_karate_agent()
                tasks.append(("karate", karate_agent.execute(agent_input)))

            if orchestrator_input.generate_postman:
                postman_agent = self.agent_factory.create_postman_agent()
                tasks.append(("postman", postman_agent.execute(agent_input)))

        # Execute in batches to avoid overwhelming the system
        batch_size = self.settings.max_concurrent_agents
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*[task[1] for task in batch], return_exceptions=True)

            # Process results
            for (agent_type, _), result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"{agent_type} agent failed: {result}")
                else:
                    results[agent_type].append(result)
                    self.logger.info(f"✅ {agent_type} agent completed")

    async def _execute_agents_sequential(
        self,
        orchestrator_input: OrchestratorInput,
        agent_inputs: List[AgentInput],
        results: Dict[str, List]
    ) -> None:
        """Execute agents sequentially"""
        for agent_input in agent_inputs:
            section_name = agent_input.section.name

            if orchestrator_input.generate_csv:
                self.logger.info(f"Executing CSV agent for {section_name}...")
                csv_agent = self.agent_factory.create_csv_agent()
                csv_result = await csv_agent.execute(agent_input)
                results["csv"].append(csv_result)

            if orchestrator_input.generate_karate:
                self.logger.info(
                    f"Executing Karate agent for {section_name}...")
                karate_agent = self.agent_factory.create_karate_agent()
                karate_result = await karate_agent.execute(agent_input)
                results["karate"].append(karate_result)

            if orchestrator_input.generate_postman:
                self.logger.info(
                    f"Executing Postman agent for {section_name}...")
                postman_agent = self.agent_factory.create_postman_agent()
                postman_result = await postman_agent.execute(agent_input)
                results["postman"].append(postman_result)

    async def _execute_agents_sequential_with_shared(
        self,
        orchestrator_input: OrchestratorInput,
        agent_inputs: List[AgentInput],
        results: Dict[str, List],
        shared_postman_agent: Any
    ) -> None:
        """Execute agents sequentially using shared Postman agent instance"""
        for agent_input in agent_inputs:
            section_name = agent_input.section.name

            if orchestrator_input.generate_csv:
                self.logger.info(f"Executing CSV agent for {section_name}...")
                csv_agent = self.agent_factory.create_csv_agent()
                csv_result = await csv_agent.execute(agent_input)
                results["csv"].append(csv_result)

            if orchestrator_input.generate_karate:
                self.logger.info(
                    f"Executing Karate agent for {section_name}...")
                karate_agent = self.agent_factory.create_karate_agent()
                karate_result = await karate_agent.execute(agent_input)
                results["karate"].append(karate_result)

            if orchestrator_input.generate_postman and shared_postman_agent:
                self.logger.info(
                    f"Executing Postman agent for {section_name}...")
                # Use the SHARED agent instance to maintain state
                postman_result = await shared_postman_agent.execute(agent_input)
                results["postman"].append(postman_result)

    async def _execute_agents_parallel_with_shared(
        self,
        orchestrator_input: OrchestratorInput,
        agent_inputs: List[AgentInput],
        results: Dict[str, List],
        shared_postman_agent: Any
    ) -> None:
        """Execute agents in parallel - but Postman agent runs sequentially to maintain state"""
        tasks = []

        for agent_input in agent_inputs:
            if orchestrator_input.generate_csv:
                csv_agent = self.agent_factory.create_csv_agent()
                tasks.append(("csv", csv_agent.execute(agent_input)))

            if orchestrator_input.generate_karate:
                karate_agent = self.agent_factory.create_karate_agent()
                tasks.append(("karate", karate_agent.execute(agent_input)))

        # Execute CSV and Karate in parallel
        if tasks:
            batch_size = self.settings.max_concurrent_agents
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                batch_results = await asyncio.gather(*[task[1] for task in batch], return_exceptions=True)

                # Process results
                for (agent_type, _), result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        self.logger.error(
                            f"{agent_type} agent failed: {result}")
                    else:
                        results[agent_type].append(result)
                        self.logger.info(f"✅ {agent_type} agent completed")

        # Execute Postman agent SEQUENTIALLY to maintain collection state
        if orchestrator_input.generate_postman and shared_postman_agent:
            for agent_input in agent_inputs:
                section_name = agent_input.section.name
                self.logger.info(
                    f"Executing Postman agent for {section_name}...")
                postman_result = await shared_postman_agent.execute(agent_input)
                results["postman"].append(postman_result)

    async def _finalize_postman_collection(
        self,
        orchestrator_input: OrchestratorInput,
        results: Dict[str, List],
        shared_postman_agent: Any
    ) -> None:
        """Finalize and export the consolidated Postman collection with conditional documentation"""
        try:
            self.logger.info("📮 Finalizing consolidated Postman collection...")

            # Extract documentation generation flag
            generate_docs = orchestrator_input.generate_postman_docs

            # Use the shared agent's processor
            postman_processor = shared_postman_agent.postman_processor

            # Generate the final consolidated collection with conditional documentation
            timestamp = self._get_timestamp()
            base_name = f"api_collection_{timestamp}"

            generated_files = await postman_processor.finalize_and_export_collection(
                base_name,
                generate_docs=generate_docs
            )

            # Validate the generated collection
            collection_path = generated_files.get("collection")
            is_valid = False
            if collection_path:
                is_valid = await postman_processor.validate_collection(collection_path)

            # Update all Postman outputs with the final file information
            for postman_output in results["postman"]:
                # Update with actual file paths
                artifacts = [str(path) for path in generated_files.values()]
                postman_output.artifacts = artifacts
                postman_output.collection_file = str(
                    generated_files.get("collection", ""))

                # Environment files (just one now)
                env_files = [str(generated_files["environment"])
                             ] if "environment" in generated_files else []
                postman_output.environment_files = env_files

                # Documentation file
                if generate_docs and "documentation" in generated_files:
                    postman_output.documentation_file = str(
                        generated_files["documentation"])
                else:
                    postman_output.documentation_file = ""

                # Update metadata
                postman_output.metadata["validation_passed"] = is_valid
                postman_output.metadata["generated_files"] = list(
                    generated_files.keys())
                postman_output.metadata["finalized"] = True
                postman_output.metadata["documentation_generated"] = generate_docs

            # Update the first output with consolidated metrics
            if results["postman"]:
                first_output = results["postman"][0]
                first_output.request_count = postman_processor._total_requests
                first_output.folder_count = len(postman_processor._all_folders)
                first_output.environment_count = 1  # Single environment now

                first_output.metadata[
                    "collection_summary"] = f"Consolidated collection with {postman_processor._total_requests} requests across {len(postman_processor._all_folders)} functional areas"
                first_output.metadata["folder_structure"] = postman_processor._all_folders

            doc_status = "with documentation" if generate_docs else "without documentation"
            self.logger.info(
                f"✅ Consolidated Postman collection finalized {doc_status}: {len(generated_files)} files generated")

        except Exception as e:
            self.logger.error(f"❌ Postman collection finalization failed: {e}")
            # Mark all Postman outputs as failed
            for postman_output in results["postman"]:
                postman_output.success = False
                postman_output.errors.append(
                    f"Collection finalization failed: {str(e)}")

    def _create_section_from_data(self, section_data: Dict) -> 'Section':
        """Create Section model from dictionary data"""
        from src.models.agents import Section
        from src.models.base import BaseEndpoint, BaseTestCase

        # Convert endpoints
        endpoints = []
        for ep_data in section_data.get("endpoints", []):
            endpoints.append(BaseEndpoint(**ep_data))

        # Convert test cases
        test_cases = []
        for tc_data in section_data.get("test_cases", []):
            test_cases.append(BaseTestCase(**tc_data))

        return Section(
            section_id=section_data["section_id"],
            name=section_data["name"],
            description=section_data["description"],
            endpoints=endpoints,
            test_cases=test_cases,
            estimated_tokens=section_data.get("estimated_tokens", 0)
        )

    def _get_timestamp(self) -> str:
        """Get timestamp for filename"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # Convenience methods for CLI usage
    async def generate_from_swagger(
        self,
        swagger_file: Path,
        user_prompt: Optional[str] = None,
        output_dir: Path = Path("outputs"),
        generate_documentation: bool = True
    ) -> OrchestratorResult:
        """Convenience method for Swagger-only generation with documentation control"""
        from pathlib import Path
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            user_prompt=user_prompt,
            output_directory=output_dir,
            generate_documentation=generate_documentation,
            generate_csv_docs=generate_documentation,
            generate_karate_docs=generate_documentation,
            generate_postman_docs=generate_documentation
        )
        return await self.execute(orchestrator_input)
