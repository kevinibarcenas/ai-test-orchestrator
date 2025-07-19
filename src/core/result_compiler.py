"""Result compilation and aggregation service"""
import time
from typing import Any, Dict, List

from src.config.dependencies import inject
from src.models.orchestrator import OrchestratorInput, OrchestratorResult, SectionAnalysis, ProcessingStatus
from src.models.outputs import CsvOutput, KarateOutput, PostmanOutput
from src.utils.logger import get_logger


class ResultCompiler:
    """Compiles and aggregates results from agent execution"""

    @inject
    def __init__(self):
        self.logger = get_logger("result_compiler")

    async def compile_result(
        self,
        execution_id: str,
        orchestrator_input: OrchestratorInput,
        sectioning_analysis: SectionAnalysis,
        agent_results: Dict[str, List[Any]],
        start_time: float
    ) -> OrchestratorResult:
        """Compile final orchestration result from all components"""

        processing_time = time.time() - start_time

        try:
            # Extract and validate agent outputs
            csv_outputs = self._extract_csv_outputs(
                agent_results.get("csv", []))
            karate_outputs = self._extract_karate_outputs(
                agent_results.get("karate", []))
            postman_outputs = self._extract_postman_outputs(
                agent_results.get("postman", []))

            # Calculate aggregated metrics
            total_token_usage = self._calculate_total_token_usage(
                csv_outputs, karate_outputs, postman_outputs
            )

            # Collect all errors and warnings
            errors, warnings = self._collect_errors_and_warnings(
                csv_outputs, karate_outputs, postman_outputs
            )

            # Determine overall success status
            success = len(errors) == 0 and any([
                csv_outputs, karate_outputs, postman_outputs
            ])

            status = ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED

            # Generate summary
            summary = self._generate_execution_summary(
                orchestrator_input, sectioning_analysis,
                csv_outputs, karate_outputs, postman_outputs,
                processing_time, success
            )

            # Create result object
            result = OrchestratorResult(
                execution_id=execution_id,
                success=success,
                input_files=self._get_input_file_paths(orchestrator_input),
                user_prompt=orchestrator_input.user_prompt,
                sectioning_analysis=sectioning_analysis,
                sections_processed=len([
                    output for outputs in [csv_outputs, karate_outputs, postman_outputs]
                    for output in outputs if output.success
                ]),
                csv_outputs=csv_outputs,
                karate_outputs=karate_outputs,
                postman_outputs=postman_outputs,
                total_processing_time=processing_time,
                total_token_usage=total_token_usage,
                status=status,
                errors=errors,
                warnings=warnings,
                summary=summary
            )

            self.logger.info(
                f"✅ Result compilation completed for {execution_id}")
            return result

        except Exception as e:
            self.logger.error(f"Result compilation failed: {e}")
            return await self.create_error_result(
                execution_id, orchestrator_input, e, processing_time
            )

    async def create_error_result(
        self,
        execution_id: str,
        orchestrator_input: OrchestratorInput,
        error: Exception,
        processing_time: float
    ) -> OrchestratorResult:
        """Create an error result when orchestration fails"""

        # Create minimal sectioning analysis for error case
        error_analysis = SectionAnalysis(
            strategy_used=orchestrator_input.sectioning_strategy,
            total_sections=0,
            estimated_total_tokens=0,
            sections_summary=[],
            analysis_reasoning=f"Execution failed: {str(error)}"
        )

        return OrchestratorResult(
            execution_id=execution_id,
            success=False,
            input_files=self._get_input_file_paths(orchestrator_input),
            user_prompt=orchestrator_input.user_prompt,
            sectioning_analysis=error_analysis,
            sections_processed=0,
            total_processing_time=processing_time,
            total_token_usage={"input_tokens": 0,
                               "output_tokens": 0, "total_tokens": 0},
            status=ProcessingStatus.FAILED,
            errors=[str(error)],
            warnings=[],
            summary=f"Execution failed: {str(error)}"
        )

    def _extract_csv_outputs(self, csv_results: List[Any]) -> List[CsvOutput]:
        """Extract and validate CSV outputs"""
        csv_outputs = []
        for result in csv_results:
            if isinstance(result, CsvOutput):
                csv_outputs.append(result)
            else:
                # Handle legacy or malformed results
                self.logger.warning(f"Invalid CSV result type: {type(result)}")
        return csv_outputs

    def _extract_karate_outputs(self, karate_results: List[Any]) -> List[KarateOutput]:
        """Extract and validate Karate outputs"""
        karate_outputs = []
        for result in karate_results:
            if isinstance(result, KarateOutput):
                karate_outputs.append(result)
            elif hasattr(result, 'agent_type') and result.agent_type.value == 'karate':
                # Convert AgentOutput to KarateOutput if possible
                try:
                    karate_output = KarateOutput(
                        agent_type=result.agent_type,
                        section_id=result.section_id,
                        success=result.success,
                        artifacts=result.artifacts,
                        errors=result.errors,
                        warnings=result.warnings,
                        metadata=result.metadata,
                        feature_files=[],  # Will be empty for failed cases
                        data_files=[],
                        scenario_count=0
                    )
                    karate_outputs.append(karate_output)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to convert AgentOutput to KarateOutput: {e}")
            else:
                self.logger.warning(
                    f"Invalid Karate result type: {type(result)}")
        return karate_outputs

    def _extract_postman_outputs(self, postman_results: List[Any]) -> List[PostmanOutput]:
        """Extract and validate Postman outputs"""
        postman_outputs = []
        for result in postman_results:
            if isinstance(result, PostmanOutput):
                postman_outputs.append(result)
            else:
                self.logger.warning(
                    f"Invalid Postman result type: {type(result)}")
        return postman_outputs

    def _calculate_total_token_usage(
        self,
        csv_outputs: List[CsvOutput],
        karate_outputs: List[KarateOutput],
        postman_outputs: List[PostmanOutput]
    ) -> Dict[str, int]:
        """Calculate total token usage across all agents"""

        total_input = 0
        total_output = 0

        for outputs in [csv_outputs, karate_outputs, postman_outputs]:
            for output in outputs:
                if hasattr(output, 'metrics') and output.metrics.token_usage:
                    total_input += output.metrics.token_usage.input_tokens
                    total_output += output.metrics.token_usage.output_tokens
                elif hasattr(output, 'token_usage') and output.token_usage:
                    # Backward compatibility
                    total_input += output.token_usage.get("input_tokens", 0)
                    total_output += output.token_usage.get("output_tokens", 0)

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output
        }

    def _collect_errors_and_warnings(
        self,
        csv_outputs: List[CsvOutput],
        karate_outputs: List[KarateOutput],
        postman_outputs: List[PostmanOutput]
    ) -> tuple[List[str], List[str]]:
        """Collect all errors and warnings from agent outputs"""

        all_errors = []
        all_warnings = []

        for outputs in [csv_outputs, karate_outputs, postman_outputs]:
            for output in outputs:
                all_errors.extend(output.errors)
                all_warnings.extend(output.warnings)

        return all_errors, all_warnings

    def _generate_execution_summary(
        self,
        orchestrator_input: OrchestratorInput,
        sectioning_analysis: SectionAnalysis,
        csv_outputs: List[CsvOutput],
        karate_outputs: List[KarateOutput],
        postman_outputs: List[PostmanOutput],
        processing_time: float,
        success: bool
    ) -> str:
        """Generate human-readable execution summary"""

        if not success:
            return "Execution failed - see errors for details"

        summary_parts = [
            f"Successfully processed {sectioning_analysis.total_sections} sections",
            f"using {sectioning_analysis.strategy_used.value} strategy"
        ]

        # Add output statistics
        if csv_outputs:
            total_test_cases = sum(
                output.test_case_count for output in csv_outputs)
            summary_parts.append(
                f"Generated {total_test_cases} CSV test cases")

        if karate_outputs:
            total_scenarios = sum(output.scenario_count for output in karate_outputs if hasattr(
                output, 'scenario_count'))
            if total_scenarios > 0:
                summary_parts.append(
                    f"Generated {total_scenarios} Karate scenarios")

        if postman_outputs:
            total_requests = sum(
                output.request_count for output in postman_outputs)
            if total_requests > 0:
                summary_parts.append(
                    f"Generated {total_requests} Postman requests")

        summary_parts.append(f"Completed in {processing_time:.2f} seconds")

        return ". ".join(summary_parts) + "."

    def _get_input_file_paths(self, orchestrator_input: OrchestratorInput) -> List[str]:
        """Get list of input file paths"""
        file_paths = []

        if orchestrator_input.swagger_file:
            file_paths.append(str(orchestrator_input.swagger_file))

        if orchestrator_input.pdf_file:
            file_paths.append(str(orchestrator_input.pdf_file))

        return file_paths
