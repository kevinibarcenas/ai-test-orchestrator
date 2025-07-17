"""QMetry CSV agent for generating test case CSV files"""
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from config.schemas import CSV_TEST_CASE_SCHEMA
from orchestrator.agents.base import BaseAgent
from orchestrator.models.schemas import AgentInput, AgentType, CsvOutput


class CsvAgent(BaseAgent):
    """Agent for generating QMetry-compatible CSV test cases"""

    def __init__(self):
        super().__init__(AgentType.CSV)

    def get_system_prompt(self) -> str:
        """Get the system prompt for CSV generation"""
        return """You are an expert test case analyst specializing in creating comprehensive test cases for QMetry import.

Your task is to analyze API specifications and generate detailed test cases in a structured format that will be exported to CSV.

## QMetry CSV Requirements:
- Each test case must have a unique ID
- Test steps should be clear and actionable
- Expected results must be specific and measurable
- Include both positive and negative test scenarios
- Consider edge cases and error conditions
- Add appropriate test data examples

## Test Case Quality Guidelines:
1. **Test Case Names**: Clear, descriptive, following pattern: "Verify [action] [condition] [expected outcome]"
2. **Descriptions**: Concise but complete explanation of what is being tested
3. **Test Steps**: Numbered, actionable steps that a tester can follow
4. **Expected Results**: Specific expected outcomes, including status codes, response structure
5. **Test Data**: Include realistic sample data for requests
6. **Priority**: Assign based on business criticality (High/Medium/Low)
7. **Test Type**: Categorize appropriately (Functional, Integration, Negative, Security, etc.)

## Coverage Requirements:
- Happy path scenarios for all endpoints
- Input validation testing (required fields, data types, formats)
- Authentication and authorization testing
- Error scenarios (4xx, 5xx responses)
- Boundary value testing where applicable

Generate comprehensive test cases that provide 70% test coverage and give testers a solid foundation to build upon."""

    def get_output_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for CSV output"""
        return CSV_TEST_CASE_SCHEMA

    def process_llm_output(self, llm_output: Dict[str, Any], input_data: AgentInput) -> CsvOutput:
        """Process LLM output into CSV files"""
        try:
            test_cases = llm_output.get("test_cases", [])
            metadata = llm_output.get("metadata", {})

            # Generate CSV file
            csv_file_path = self._generate_csv_file(
                test_cases,
                input_data.section.section_id,
                metadata.get("csv_headers", self._get_default_headers())
            )

            return CsvOutput(
                agent_type=self.agent_type,
                section_id=input_data.section.section_id,
                success=True,
                artifacts=[str(csv_file_path)],
                csv_file=str(csv_file_path),
                test_case_count=len(test_cases),
                metadata={
                    "headers": metadata.get("csv_headers", self._get_default_headers()),
                    "coverage_summary": metadata.get("coverage_summary", ""),
                    "total_test_cases": metadata.get("total_test_cases", len(test_cases))
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

    def _get_default_headers(self) -> List[str]:
        """Get default CSV headers for QMetry"""
        return [
            "Test Case ID",
            "Test Case Name",
            "Test Case Description",
            "Module",
            "Test Type",
            "Priority",
            "Estimated Time (mins)",
            "Preconditions",
            "Test Steps",
            "Expected Results",
            "Test Data",
            "Tags"
        ]

    def _generate_csv_file(
        self,
        test_cases: List[Dict[str, Any]],
        section_id: str,
        headers: List[str]
    ) -> Path:
        """Generate CSV file from test cases"""

        # Create output directory
        output_dir = Path(self.settings.output_directory) / "csv"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        csv_filename = f"test_cases_{section_id}_{self._get_timestamp()}.csv"
        csv_file_path = output_dir / csv_filename

        self.logger.info(f"Generating CSV file: {csv_filename}")

        try:
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

                # Write headers
                writer.writerow(headers)

                # Write test cases
                for test_case in test_cases:
                    row = self._test_case_to_csv_row(test_case, headers)
                    writer.writerow(row)

            self.logger.info(
                f"✅ CSV file generated: {csv_file_path} ({len(test_cases)} test cases)")
            return csv_file_path

        except Exception as e:
            self.logger.error(f"Failed to write CSV file: {e}")
            raise

    def _test_case_to_csv_row(self, test_case: Dict[str, Any], headers: List[str]) -> List[str]:
        """Convert test case dictionary to CSV row"""
        row = []

        # Map test case fields to CSV columns
        field_mapping = {
            "Test Case ID": test_case.get("test_case_id", ""),
            "Test Case Name": test_case.get("test_case_name", ""),
            "Test Case Description": test_case.get("test_case_description", ""),
            "Module": test_case.get("module", "API Tests"),
            "Test Type": test_case.get("test_type", "Functional"),
            "Priority": test_case.get("priority", "Medium"),
            "Estimated Time (mins)": test_case.get("estimated_time", "15"),
            "Preconditions": test_case.get("preconditions", ""),
            "Test Steps": self._format_test_steps(test_case.get("test_steps", "")),
            "Expected Results": test_case.get("expected_results", ""),
            "Test Data": self._format_test_data(test_case.get("test_data", "")),
            "Tags": test_case.get("tags", "")
        }

        # Build row according to header order
        for header in headers:
            row.append(field_mapping.get(header, ""))

        return row

    def _format_test_steps(self, test_steps: str) -> str:
        """Format test steps for CSV (handle multiline)"""
        if isinstance(test_steps, list):
            # Join list items with numbered steps
            formatted_steps = []
            for i, step in enumerate(test_steps, 1):
                formatted_steps.append(f"{i}. {step}")
            return "\n".join(formatted_steps)

        return str(test_steps).replace('\n', '\n')  # Preserve line breaks

    def _format_test_data(self, test_data: Any) -> str:
        """Format test data for CSV"""
        if isinstance(test_data, dict):
            # Convert dict to readable format
            formatted_data = []
            for key, value in test_data.items():
                formatted_data.append(f"{key}: {value}")
            return "\n".join(formatted_data)
        elif isinstance(test_data, list):
            return "\n".join(str(item) for item in test_data)

        return str(test_data)

    def _get_timestamp(self) -> str:
        """Get timestamp for filename"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def validate_csv_output(self, csv_file_path: Path) -> bool:
        """Validate generated CSV file"""
        try:
            if not csv_file_path.exists():
                self.logger.error(f"CSV file does not exist: {csv_file_path}")
                return False

            # Check file is not empty
            if csv_file_path.stat().st_size == 0:
                self.logger.error("CSV file is empty")
                return False

            # Validate CSV structure
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)

                if not headers:
                    self.logger.error("CSV file has no headers")
                    return False

                # Check required headers are present
                required_headers = [
                    "Test Case ID", "Test Case Name", "Test Steps", "Expected Results"]
                missing_headers = [
                    h for h in required_headers if h not in headers]

                if missing_headers:
                    self.logger.error(
                        f"Missing required headers: {missing_headers}")
                    return False

                # Count rows
                row_count = sum(1 for row in reader)
                if row_count == 0:
                    self.logger.error("CSV file has no test cases")
                    return False

                self.logger.info(
                    f"✅ CSV validation passed: {row_count} test cases")
                return True

        except Exception as e:
            self.logger.error(f"CSV validation failed: {e}")
            return False

    async def generate_sample_csv(self, output_path: Path) -> bool:
        """Generate a sample CSV for testing"""
        try:
            headers = self._get_default_headers()
            sample_test_cases = [
                {
                    "test_case_id": "TC_001",
                    "test_case_name": "Verify GET /users returns user list",
                    "test_case_description": "Verify that GET request to /users endpoint returns a list of users with correct structure",
                    "module": "User Management",
                    "test_type": "Functional",
                    "priority": "High",
                    "estimated_time": "10",
                    "preconditions": "API server is running\nAuthentication token is valid",
                    "test_steps": "1. Send GET request to /users endpoint\n2. Include valid authorization header\n3. Verify response status code\n4. Validate response structure",
                    "expected_results": "Status code: 200\nResponse contains array of user objects\nEach user object has required fields (id, name, email)",
                    "test_data": "Authorization: Bearer <valid_token>",
                    "tags": "smoke,users,positive"
                },
                {
                    "test_case_id": "TC_002",
                    "test_case_name": "Verify POST /users with invalid email returns error",
                    "test_case_description": "Verify that POST request to /users with invalid email format returns appropriate error",
                    "module": "User Management",
                    "test_type": "Negative",
                    "priority": "Medium",
                    "estimated_time": "5",
                    "preconditions": "API server is running",
                    "test_steps": "1. Send POST request to /users\n2. Include request body with invalid email\n3. Verify error response",
                    "expected_results": "Status code: 400\nError message indicates invalid email format",
                    "test_data": "{\n  \"name\": \"Test User\",\n  \"email\": \"invalid-email\"\n}",
                    "tags": "validation,users,negative"
                }
            ]

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                writer.writerow(headers)

                for test_case in sample_test_cases:
                    row = self._test_case_to_csv_row(test_case, headers)
                    writer.writerow(row)

            self.logger.info(f"✅ Sample CSV generated: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate sample CSV: {e}")
            return False
