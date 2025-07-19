"""Main orchestrator for coordinating test generation workflow"""
import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from config.settings import get_settings
from orchestrator.agents.csv_agent import CsvAgent
from orchestrator.agents.prompts import get_prompt_manager
from orchestrator.core.file_manager import get_file_manager
from orchestrator.models.orchestrator import *
from orchestrator.models.schemas import *
from orchestrator.utils.logger import get_logger


class TestOrchestrator:
    """Main orchestrator for test generation workflow"""

    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("orchestrator")
        self.file_manager = get_file_manager()
        self.prompt_manager = get_prompt_manager()
        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.openai_timeout,
            max_retries=self.settings.openai_max_retries
        )

        # Agent instances (lazy loaded)
        self._csv_agent: Optional[CsvAgent] = None
        self._karate_agent = None  # Will implement later
        self._postman_agent = None  # Will implement later

    @property
    def csv_agent(self) -> CsvAgent:
        """Get CSV agent instance"""
        if self._csv_agent is None:
            self._csv_agent = CsvAgent()
        return self._csv_agent

    async def execute(self, orchestrator_input: OrchestratorInput) -> OrchestratorResult:
        """
        Execute the complete test generation workflow

        Args:
            orchestrator_input: Configuration for the orchestration

        Returns:
            Complete orchestration result
        """
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
            sectioning_analysis = await self._analyze_and_section(
                orchestrator_input, file_ids
            )

            # Phase 3: Generate detailed test sections
            self.logger.info("🧪 Phase 3: Generating detailed test sections...")
            test_sections = await self._generate_test_sections(
                orchestrator_input, file_ids, sectioning_analysis
            )

            # Phase 4: Execute agents for each section
            self.logger.info(
                "🤖 Phase 4: Executing agents for test generation...")
            agent_results = await self._execute_agents_for_sections(
                orchestrator_input, test_sections, file_ids
            )

            # Phase 5: Compile final results
            self.logger.info("📊 Phase 5: Compiling final results...")
            result = await self._compile_final_result(
                execution_id, orchestrator_input, sectioning_analysis,
                agent_results, start_time
            )

            self.logger.info(
                f"✅ Orchestration completed: {execution_id} "
                f"({result.total_processing_time:.2f}s, {result.test_cases_generated} test cases)"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Orchestration failed: {execution_id} - {e}")

            return OrchestratorResult(
                execution_id=execution_id,
                success=False,
                input_files=[str(f) for f in [
                    orchestrator_input.swagger_file, orchestrator_input.pdf_file] if f],
                user_prompt=orchestrator_input.user_prompt,
                sectioning_analysis=SectionAnalysis(
                    strategy_used=orchestrator_input.sectioning_strategy,
                    total_sections=0,
                    estimated_total_tokens=0,
                    sections_summary=[]
                ),
                sections_processed=0,
                total_processing_time=processing_time,
                errors=[str(e)],
                summary=f"Execution failed: {str(e)}"
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

    async def _analyze_and_section(
        self,
        orchestrator_input: OrchestratorInput,
        file_ids: Dict[str, Optional[str]]
    ) -> SectionAnalysis:
        """Analyze input content and determine sectioning strategy"""

        # Build analysis prompt with user context
        analysis_prompt = self._build_analysis_prompt(orchestrator_input)

        # Prepare messages for analysis
        messages = [
            {"role": "system", "content": self.prompt_manager.get_prompt(
                "orchestrator_analysis")},
        ]

        user_content = []

        # Add file inputs
        if file_ids["swagger"]:
            user_content.append({
                "type": "input_file",
                "file_id": file_ids["swagger"]
            })

        if file_ids["pdf"]:
            user_content.append({
                "type": "input_file",
                "file_id": file_ids["pdf"]
            })

        # Add analysis prompt
        user_content.append({
            "type": "input_text",
            "text": analysis_prompt
        })

        messages.append({"role": "user", "content": user_content})

        # Get sectioning analysis from LLM using reasoning model
        self.logger.info("🧠 Analyzing content with reasoning model...")
        response = self.client.responses.create(
            model=self.settings.reasoning_model,  # o3-mini
            reasoning={"effort": "medium"},
            input=messages,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "sectioning_analysis",
                    "schema": self._get_sectioning_schema(),
                    "strict": True
                }
            }
        )

        analysis_data = json.loads(response.output_text)
        self.logger.info(
            f"✅ Content analysis complete: {analysis_data['total_sections']} sections identified")

        # Convert to SectionAnalysis model
        return SectionAnalysis(
            strategy_used=SectioningStrategy(analysis_data["strategy_used"]),
            total_sections=analysis_data["total_sections"],
            estimated_total_tokens=analysis_data["estimated_total_tokens"],
            sections_summary=analysis_data["sections_summary"],
            user_focus_applied=analysis_data.get("user_focus_applied", False)
        )

    def _build_analysis_prompt(self, orchestrator_input: OrchestratorInput) -> str:
        """Build prompt for content analysis"""
        prompt = f"""
# API Documentation Analysis Request

## Objective
Analyze the provided API documentation and determine the optimal sectioning strategy for comprehensive test generation.

## User Requirements
"""

        if orchestrator_input.user_prompt:
            prompt += f"""
**User Focus Instructions:** {orchestrator_input.user_prompt}
**Priority:** High - ensure user requirements are addressed in sectioning strategy
"""
        else:
            prompt += """
**User Focus:** None specified - provide comprehensive coverage of all API functionality
**Priority:** Standard - cover all endpoints with balanced sectioning
"""

        prompt += f"""

## Processing Constraints
- **Maximum tokens per section:** {orchestrator_input.max_tokens_per_section}
- **Preferred sectioning strategy:** {orchestrator_input.sectioning_strategy.value}
- **Target coverage:** 70% of API functionality with practical, maintainable test cases
- **Quality focus:** Executable test cases for QA engineers

## Analysis Requirements

### 1. Content Discovery
- Identify all API endpoints, methods, and parameters
- Analyze endpoint complexity and dependencies
- Review authentication and authorization patterns
- Identify data models and validation rules

### 2. Sectioning Strategy
- Apply the requested strategy: {orchestrator_input.sectioning_strategy.value}
- Consider user focus areas for prioritization
- Balance section sizes to stay within token limits
- Group related functionality logically
- Ensure sections can be processed independently

### 3. Token Estimation
- Estimate tokens needed per section for comprehensive test generation
- Include overhead for:
  - Test case descriptions and steps
  - Request/response examples
  - Validation scenarios
  - Error conditions
  - Test data examples

### 4. Quality Considerations
- Prioritize endpoints based on business criticality
- Consider real-world testing scenarios
- Plan for both positive and negative test cases
- Ensure maintainable test organization

## Output Requirements
Provide a detailed sectioning plan that:
- Maximizes test coverage within constraints
- Addresses user focus areas
- Enables efficient parallel processing
- Produces maintainable test suites
- Stays within token limits per section

Analyze the documentation thoroughly and create an optimal sectioning strategy.
"""
        return prompt

    def _get_sectioning_schema(self) -> Dict[str, Any]:
        """Get JSON schema for sectioning analysis"""
        return {
            "type": "object",
            "properties": {
                "strategy_used": {
                    "type": "string",
                    "enum": ["by_tag", "by_path", "by_method", "by_complexity", "auto"]
                },
                "total_sections": {"type": "integer", "minimum": 1, "maximum": 20},
                "estimated_total_tokens": {"type": "integer", "minimum": 0},
                "sections_summary": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Brief description of each section (max 200 chars each)"
                },
                "user_focus_applied": {"type": "boolean"},
                "sections_detail": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section_id": {"type": "string"},
                            "section_name": {"type": "string"},
                            "description": {"type": "string"},
                            "endpoints": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of endpoints in format 'METHOD /path'"
                            },
                            "estimated_tokens": {"type": "integer", "minimum": 0},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "complexity": {"type": "string", "enum": ["simple", "medium", "complex"]},
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Other sections this depends on"
                            }
                        },
                        "required": ["section_id", "section_name", "description", "endpoints", "estimated_tokens", "priority"],
                        "additionalProperties": False
                    }
                },
                "coverage_analysis": {
                    "type": "object",
                    "properties": {
                        "total_endpoints": {"type": "integer"},
                        "endpoints_per_section": {"type": "array", "items": {"type": "integer"}},
                        "estimated_coverage_percentage": {"type": "number", "minimum": 0, "maximum": 100}
                    },
                    "required": ["total_endpoints", "estimated_coverage_percentage"],
                    "additionalProperties": False
                }
            },
            "required": [
                "strategy_used", "total_sections", "estimated_total_tokens",
                "sections_summary", "sections_detail", "coverage_analysis"
            ],
            "additionalProperties": False
        }

    async def _generate_test_sections(
        self,
        orchestrator_input: OrchestratorInput,
        file_ids: Dict[str, Optional[str]],
        sectioning_analysis: SectionAnalysis
    ) -> List[TestSection]:
        """Generate detailed test sections with actual test cases"""
        test_sections = []

        # Re-analyze with the reasoning model output to get detailed sections
        response = self.client.responses.create(
            model=self.settings.reasoning_model,
            reasoning={"effort": "medium"},
            input=[
                {"role": "system", "content": self.prompt_manager.get_prompt(
                    "orchestrator_analysis")},
                {"role": "user", "content": [
                    *([{"type": "input_file", "file_id": file_ids["swagger"]}]
                      if file_ids["swagger"] else []),
                    *([{"type": "input_file", "file_id": file_ids["pdf"]}]
                      if file_ids["pdf"] else []),
                    {"type": "input_text", "text": self._build_analysis_prompt(
                        orchestrator_input)}
                ]}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "sectioning_analysis",
                    "schema": self._get_sectioning_schema(),
                    "strict": True
                }
            }
        )

        detailed_analysis = json.loads(response.output_text)

        # Generate test sections for each identified section
        for section_detail in detailed_analysis["sections_detail"]:
            self.logger.info(
                f"Generating test cases for section: {section_detail['section_name']}")

            # Generate test cases for this section
            test_cases = await self._generate_test_cases_for_section(
                section_detail, orchestrator_input, file_ids
            )

            # Create TestSection object
            section = TestSection(
                section_id=section_detail["section_id"],
                name=section_detail["section_name"],
                description=section_detail["description"],
                endpoints=self._parse_endpoints(section_detail["endpoints"]),
                test_cases=test_cases,
                estimated_tokens=section_detail["estimated_tokens"]
            )

            test_sections.append(section)
            self.logger.info(
                f"✅ Generated {len(test_cases)} test cases for {section.name}")

        return test_sections

    def _parse_endpoints(self, endpoint_strings: List[str]) -> List[EndpointInfo]:
        """Parse endpoint strings into EndpointInfo objects"""
        endpoints = []

        for endpoint_str in endpoint_strings:
            # Parse "METHOD /path" format
            parts = endpoint_str.strip().split(' ', 1)
            if len(parts) == 2:
                method_str, path = parts
                try:
                    method = HttpMethod(method_str.upper())
                    endpoint = EndpointInfo(
                        path=path,
                        method=method,
                        summary=f"{method_str} {path}",
                        description=f"API endpoint for {path}"
                    )
                    endpoints.append(endpoint)
                except ValueError:
                    self.logger.warning(
                        f"Invalid HTTP method in endpoint: {endpoint_str}")

        return endpoints

    async def _generate_test_cases_for_section(
        self,
        section_detail: Dict[str, Any],
        orchestrator_input: OrchestratorInput,
        file_ids: Dict[str, Optional[str]]
    ) -> List[TestCase]:
        """Generate actual test cases for a specific section"""

        # Build section-specific prompt
        section_prompt = f"""
# Test Case Generation for Section: {section_detail['section_name']}

## Section Details
**Description:** {section_detail['description']}
**Priority:** {section_detail['priority']}
**Complexity:** {section_detail.get('complexity', 'medium')}

## Endpoints to Cover:
{chr(10).join(f"- {endpoint}" for endpoint in section_detail['endpoints'])}

## User Requirements:
"""

        if orchestrator_input.user_prompt:
            section_prompt += f"**User Focus:** {orchestrator_input.user_prompt}\n"
        else:
            section_prompt += "**User Focus:** Comprehensive coverage of all functionality\n"

        section_prompt += f"""

## Test Generation Requirements:
- Generate comprehensive test cases for all endpoints in this section
- Include happy path, validation, error, and edge case scenarios  
- Provide realistic test data examples
- Ensure 70% coverage of endpoint functionality
- Create immediately executable test cases
- Follow standard test case naming conventions

## Token Budget: {section_detail['estimated_tokens']} tokens

Generate detailed test case definitions for this section that can be used by QA engineers for thorough API testing.
"""

        # Generate test cases using default model
        response = self.client.responses.create(
            model=self.settings.default_model,
            input=[
                {"role": "system", "content": self.prompt_manager.get_prompt(
                    "orchestrator_sectioning")},
                {"role": "user", "content": [
                    *([{"type": "input_file", "file_id": file_ids["swagger"]}]
                      if file_ids["swagger"] else []),
                    *([{"type": "input_file", "file_id": file_ids["pdf"]}]
                      if file_ids["pdf"] else []),
                    {"type": "input_text", "text": section_prompt}
                ]}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "test_cases",
                    "schema": self._get_test_cases_schema(),
                    "strict": True
                }
            }
        )

        test_cases_data = json.loads(response.output_text)

        # Convert to TestCase objects
        test_cases = []
        for tc_data in test_cases_data["test_cases"]:
            # Parse endpoint info
            endpoint_parts = tc_data["endpoint"].split(
                ' ', 1) if ' ' in tc_data["endpoint"] else ["GET", tc_data["endpoint"]]
            method = HttpMethod(endpoint_parts[0].upper()) if len(
                endpoint_parts) > 0 else HttpMethod.GET
            path = endpoint_parts[1] if len(
                endpoint_parts) > 1 else tc_data["endpoint"]

            endpoint = EndpointInfo(
                path=path,
                method=method,
                summary=tc_data.get("endpoint_summary",
                                    f"{method.value} {path}")
            )

            test_case = TestCase(
                id=tc_data["id"],
                name=tc_data["name"],
                description=tc_data["description"],
                endpoint=endpoint,
                test_type=TestCaseType(tc_data["test_type"]),
                priority=tc_data.get("priority", "Medium"),
                test_data=tc_data.get("test_data", {}),
                expected_result=tc_data.get("expected_result", {}),
                assertions=tc_data.get("assertions", []),
                preconditions=tc_data.get("preconditions", []),
                postconditions=tc_data.get("postconditions", [])
            )

            test_cases.append(test_case)

        return test_cases

    def _get_test_cases_schema(self) -> Dict[str, Any]:
        """Get JSON schema for test case generation"""
        return {
            "type": "object",
            "properties": {
                "test_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "endpoint": {"type": "string", "description": "Format: 'METHOD /path'"},
                            "endpoint_summary": {"type": "string"},
                            "test_type": {
                                "type": "string",
                                "enum": ["happy_path", "edge_case", "error_case", "security", "performance"]
                            },
                            "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                            "test_data": {"type": "object"},
                            "expected_result": {"type": "object"},
                            "assertions": {"type": "array", "items": {"type": "string"}},
                            "preconditions": {"type": "array", "items": {"type": "string"}},
                            "postconditions": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["id", "name", "description", "endpoint", "test_type"],
                        "additionalProperties": False
                    }
                },
                "section_summary": {"type": "string"},
                "total_test_cases": {"type": "integer"},
                "coverage_notes": {"type": "string"}
            },
            "required": ["test_cases", "section_summary", "total_test_cases"],
            "additionalProperties": False
        }

    async def _execute_agents_for_sections(
        self,
        orchestrator_input: OrchestratorInput,
        test_sections: List[TestSection],
        file_ids: Dict[str, Optional[str]]
    ) -> Dict[str, List[Any]]:
        """Execute selected agents for each test section"""

        results = {
            "csv": [],
            "karate": [],
            "postman": []
        }

        for i, section in enumerate(test_sections, 1):
            self.logger.info(
                f"🤖 Processing section {i}/{len(test_sections)}: {section.name}")

            # Prepare agent input
            agent_input = AgentInput(
                section=section,
                swagger_file_id=file_ids["swagger"],
                pdf_file_id=file_ids["pdf"],
                context={
                    "user_prompt": orchestrator_input.user_prompt,
                    "sectioning_strategy": orchestrator_input.sectioning_strategy.value,
                    "section_number": i,
                    "total_sections": len(test_sections)
                }
            )

            # Execute selected agents
            if orchestrator_input.parallel_processing:
                # Execute agents in parallel
                tasks = []

                if orchestrator_input.generate_csv:
                    tasks.append(("csv", self.csv_agent.execute(agent_input)))

                # Add other agents when implemented
                # if orchestrator_input.generate_karate:
                #     tasks.append(("karate", self.karate_agent.execute(agent_input)))
                # if orchestrator_input.generate_postman:
                #     tasks.append(("postman", self.postman_agent.execute(agent_input)))

                if tasks:
                    # Execute all tasks
                    task_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

                    # Process results
                    for (agent_type, _), result in zip(tasks, task_results):
                        if isinstance(result, Exception):
                            self.logger.error(
                                f"{agent_type} agent failed for section {section.section_id}: {result}")
                        else:
                            results[agent_type].append(result)
                            self.logger.info(
                                f"✅ {agent_type} agent completed for {section.name}")

            else:
                # Execute agents sequentially
                if orchestrator_input.generate_csv:
                    self.logger.info(
                        f"Executing CSV agent for {section.name}...")
                    csv_result = await self.csv_agent.execute(agent_input)
                    results["csv"].append(csv_result)
                    if csv_result.success:
                        self.logger.info(
                            f"✅ CSV generated: {csv_result.test_case_count} test cases")
                    else:
                        self.logger.error(
                            f"❌ CSV generation failed: {csv_result.errors}")

        return results

    async def _compile_final_result(
        self,
        execution_id: str,
        orchestrator_input: OrchestratorInput,
        sectioning_analysis: SectionAnalysis,
        agent_results: Dict[str, List[Any]],
        start_time: float
    ) -> OrchestratorResult:
        """Compile final orchestration result"""
        processing_time = time.time() - start_time

        # Collect artifacts
        artifacts = []
        test_cases_total = 0
        token_usage_total = {"input_tokens": 0,
                             "output_tokens": 0, "total_tokens": 0}

        # Process CSV results
        for csv_result in agent_results["csv"]:
            if csv_result.success:
                artifacts.extend(csv_result.artifacts)
                test_cases_total += csv_result.test_case_count

                for key, value in csv_result.token_usage.items():
                    if key in token_usage_total:
                        token_usage_total[key] += value

        # Determine overall success
        success = len(artifacts) > 0 and test_cases_total > 0

        # Generate summary
        summary = self._generate_execution_summary(
            orchestrator_input, sectioning_analysis, agent_results, success, processing_time
        )

        return OrchestratorResult(
            execution_id=execution_id,
            success=success,
            input_files=[
                str(f) for f in [orchestrator_input.swagger_file, orchestrator_input.pdf_file]
                if f is not None
            ],
            user_prompt=orchestrator_input.user_prompt,
            sectioning_analysis=sectioning_analysis,
            sections_processed=len(agent_results["csv"]),
            csv_results=agent_results["csv"],
            karate_results=agent_results["karate"],
            postman_results=agent_results["postman"],
            total_processing_time=processing_time,
            total_token_usage=token_usage_total,
            artifacts_generated=artifacts,
            test_cases_generated=test_cases_total,
            endpoints_covered=0,  # Would calculate from actual analysis
            coverage_percentage=0.0,  # Would calculate from actual analysis
            summary=summary
        )

    def _generate_execution_summary(
        self,
        orchestrator_input: OrchestratorInput,
        sectioning_analysis: SectionAnalysis,
        agent_results: Dict[str, List[Any]],
        success: bool,
        processing_time: float
    ) -> str:
        """Generate human-readable execution summary"""
        if success:
            csv_count = len([r for r in agent_results["csv"] if r.success])
            total_test_cases = sum(
                r.test_case_count for r in agent_results["csv"] if r.success)

            summary = f"""
✅ Test generation completed successfully!

📊 **Processing Summary:**
- Sections processed: {sectioning_analysis.total_sections}
- Processing time: {processing_time:.2f} seconds
- Strategy used: {sectioning_analysis.strategy_used.value}

🧪 **Test Generation Results:**
- CSV files generated: {csv_count}
- Total test cases: {total_test_cases}

📁 **Input Files:**
"""
            for file_path in orchestrator_input.input_files if hasattr(orchestrator_input, 'input_files') else []:
                summary += f"- {file_path}\n"

            if orchestrator_input.user_prompt:
                summary += f"\n🎯 **User Focus:** {orchestrator_input.user_prompt}"

            return summary.strip()

        else:
            return f"""
❌ Test generation failed after {processing_time:.2f} seconds.

Please check the logs for detailed error information.
"""

    # Convenience methods for CLI usage
    async def generate_from_swagger(
        self,
        swagger_file: Path,
        user_prompt: Optional[str] = None,
        output_dir: Path = Path("outputs")
    ) -> OrchestratorResult:
        """Convenience method for Swagger-only generation"""
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            user_prompt=user_prompt,
            output_directory=output_dir
        )
        return await self.execute(orchestrator_input)

    async def generate_from_pdf(
        self,
        pdf_file: Path,
        user_prompt: Optional[str] = None,
        output_dir: Path = Path("outputs")
    ) -> OrchestratorResult:
        """Convenience method for PDF-only generation"""
        orchestrator_input = OrchestratorInput(
            pdf_file=pdf_file,
            user_prompt=user_prompt,
            output_directory=output_dir
        )
        return await self.execute(orchestrator_input)

    async def generate_from_both(
        self,
        swagger_file: Path,
        pdf_file: Path,
        user_prompt: Optional[str] = None,
        output_dir: Path = Path("outputs")
    ) -> OrchestratorResult:
        """Convenience method for both files"""
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            pdf_file=pdf_file,
            user_prompt=user_prompt,
            output_directory=output_dir
        )
        return await self.execute(orchestrator_input)
