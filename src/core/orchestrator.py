import asyncio
from pathlib import Path
import time
import uuid
from typing import Dict, List, Optional

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
        """Upload input files and return file IDs"""
        file_ids = {"swagger": None, "pdf": None}

        if orchestrator_input.swagger_file:
            self.logger.info(
                f"Uploading Swagger file: {orchestrator_input.swagger_file.name}")
            swagger_info = await self.file_manager.upload_file(
                orchestrator_input.swagger_file, purpose="user_data"
            )
            file_ids["swagger"] = swagger_info.file_id
            self.logger.info(f"✅ Swagger uploaded: {swagger_info.file_id}")

        if orchestrator_input.pdf_file:
            self.logger.info(
                f"Uploading PDF file: {orchestrator_input.pdf_file.name}")
            pdf_info = await self.file_manager.upload_file(
                orchestrator_input.pdf_file, purpose="user_data"
            )
            file_ids["pdf"] = pdf_info.file_id
            self.logger.info(f"✅ PDF uploaded: {pdf_info.file_id}")

        return file_ids

    async def _execute_agents_for_sections(
        self,
        orchestrator_input: OrchestratorInput,
        sections: List[Dict],
        file_ids: Dict[str, Optional[str]]
    ) -> Dict[str, List]:
        """Execute enabled agents for all sections"""
        results = {"csv": [], "karate": [], "postman": []}

        # Create agent inputs for each section
        agent_inputs = []
        for section_data in sections:
            section = self._create_section_from_data(section_data)
            agent_input = AgentInput(
                section=section,
                swagger_file_id=file_ids.get("swagger"),
                pdf_file_id=file_ids.get("pdf"),
                user_prompt=orchestrator_input.user_prompt
            )
            agent_inputs.append(agent_input)

        # Execute agents based on configuration
        if orchestrator_input.parallel_processing:
            await self._execute_agents_parallel(orchestrator_input, agent_inputs, results)
        else:
            await self._execute_agents_sequential(orchestrator_input, agent_inputs, results)

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

    # Convenience methods for CLI usage
    async def generate_from_swagger(
        self,
        swagger_file: Path,
        user_prompt: Optional[str] = None,
        output_dir: Path = Path("outputs")
    ) -> OrchestratorResult:
        """Convenience method for Swagger-only generation"""
        from pathlib import Path
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            user_prompt=user_prompt,
            output_directory=output_dir
        )
        return await self.execute(orchestrator_input)
