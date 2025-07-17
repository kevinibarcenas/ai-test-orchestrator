"""Unit tests for CSV agent"""
import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from orchestrator.agents.csv_agent import CsvAgent
from orchestrator.models.schemas import AgentType, CsvOutput


class TestCsvAgent:
    """Test suite for CSV agent"""

    def test_initialization(self, csv_agent):
        """Test CSV agent initialization"""
        assert csv_agent.agent_type == AgentType.CSV
        assert csv_agent.agent_type.value == "csv"

    def test_system_prompt(self, csv_agent):
        """Test system prompt generation"""
        prompt = csv_agent.get_system_prompt()
        assert "QMetry" in prompt
        assert "test case" in prompt.lower()
        assert "CSV" in prompt

    def test_output_schema(self, csv_agent):
        """Test output schema structure"""
        schema = csv_agent.get_output_schema()
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "test_cases" in schema["properties"]
        assert "metadata" in schema["properties"]

    def test_default_headers(self, csv_agent):
        """Test default CSV headers"""
        headers = csv_agent._get_default_headers()

        expected_headers = [
            "Test Case ID", "Test Case Name", "Test Case Description",
            "Module", "Test Type", "Priority", "Estimated Time (mins)",
            "Preconditions", "Test Steps", "Expected Results", "Test Data", "Tags"
        ]

        assert headers == expected_headers
        assert len(headers) == 12

    def test_format_test_steps_list(self, csv_agent):
        """Test formatting test steps from list"""
        steps = ["Open browser", "Navigate to login", "Enter credentials"]
        formatted = csv_agent._format_test_steps(steps)

        expected = "1. Open browser\n2. Navigate to login\n3. Enter credentials"
        assert formatted == expected

    def test_format_test_steps_string(self, csv_agent):
        """Test formatting test steps from string"""
        steps = "Single step instruction"
        formatted = csv_agent._format_test_steps(steps)
        assert formatted == steps

    def test_format_test_data_dict(self, csv_agent):
        """Test formatting test data from dictionary"""
        test_data = {
            "username": "testuser",
            "password": "testpass",
            "email": "test@example.com"
        }

        formatted = csv_agent._format_test_data(test_data)

        assert "username: testuser" in formatted
        assert "password: testpass" in formatted
        assert "email: test@example.com" in formatted

    def test_format_test_data_list(self, csv_agent):
        """Test formatting test data from list"""
        test_data = ["data1", "data2", "data3"]
        formatted = csv_agent._format_test_data(test_data)

        expected = "data1\ndata2\ndata3"
        assert formatted == expected

    def test_format_test_data_string(self, csv_agent):
        """Test formatting test data from string"""
        test_data = "Simple test data"
        formatted = csv_agent._format_test_data(test_data)
        assert formatted == test_data

    def test_test_case_to_csv_row(self, csv_agent):
        """Test converting test case to CSV row"""
        test_case = {
            "test_case_id": "TC_001",
            "test_case_name": "Test user login",
            "test_case_description": "Verify user can login successfully",
            "module": "Authentication",
            "test_type": "Functional",
            "priority": "High",
            "estimated_time": "5",
            "preconditions": "User account exists",
            "test_steps": ["Open login page", "Enter credentials", "Click login"],
            "expected_results": "User is redirected to dashboard",
            "test_data": {"username": "testuser", "password": "pass123"},
            "tags": "login,authentication"
        }

        headers = csv_agent._get_default_headers()
        row = csv_agent._test_case_to_csv_row(test_case, headers)

        assert len(row) == len(headers)
        assert row[0] == "TC_001"  # Test Case ID
        assert row[1] == "Test user login"  # Test Case Name
        assert row[2] == "Verify user can login successfully"  # Description
        assert row[3] == "Authentication"  # Module
        assert row[4] == "Functional"  # Test Type
        assert row[5] == "High"  # Priority
        assert "1. Open login page" in row[8]  # Test Steps

    def test_timestamp_generation(self, csv_agent):
        """Test timestamp generation for filenames"""
        timestamp = csv_agent._get_timestamp()

        # Should be in format YYYYMMDD_HHMMSS
        assert len(timestamp) == 15
        assert "_" in timestamp
        assert timestamp[:8].isdigit()  # Date part
        assert timestamp[9:].isdigit()  # Time part


class TestCsvGeneration:
    """Test CSV file generation functionality"""

    def test_generate_csv_file(self, csv_agent, tmp_path):
        """Test CSV file generation"""
        test_cases = [
            {
                "test_case_id": "TC_001",
                "test_case_name": "Test case 1",
                "test_case_description": "Description 1",
                "test_steps": "Step 1",
                "expected_results": "Result 1"
            },
            {
                "test_case_id": "TC_002",
                "test_case_name": "Test case 2",
                "test_case_description": "Description 2",
                "test_steps": "Step 2",
                "expected_results": "Result 2"
            }
        ]

        headers = csv_agent._get_default_headers()

        # Mock output directory
        with patch.object(csv_agent.settings, 'output_directory', tmp_path):
            csv_path = csv_agent._generate_csv_file(
                test_cases, "test_section", headers)

        assert csv_path.exists()
        assert csv_path.suffix == ".csv"

        # Verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            csv_headers = next(reader)
            rows = list(reader)

        assert csv_headers == headers
        assert len(rows) == 2
        assert rows[0][0] == "TC_001"
        assert rows[1][0] == "TC_002"

    @pytest.mark.asyncio
    async def test_generate_sample_csv(self, csv_agent, tmp_path):
        """Test sample CSV generation"""
        output_path = tmp_path / "sample.csv"
        success = await csv_agent.generate_sample_csv(output_path)

        assert success
        assert output_path.exists()

        # Verify content
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        assert len(headers) == 12
        assert len(rows) == 2  # Sample has 2 test cases
        assert rows[0][0] == "TC_001"
        assert rows[1][0] == "TC_002"


class TestCsvValidation:
    """Test CSV validation functionality"""

    def test_validate_valid_csv(self, csv_agent, temp_csv_file):
        """Test validation of valid CSV file"""
        result = csv_agent.validate_csv_output(temp_csv_file)
        assert result is True

    def test_validate_missing_file(self, csv_agent, tmp_path):
        """Test validation of missing file"""
        missing_file = tmp_path / "missing.csv"
        result = csv_agent.validate_csv_output(missing_file)
        assert result is False

    def test_validate_empty_csv(self, csv_agent, tmp_path):
        """Test validation of empty CSV file"""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.touch()

        result = csv_agent.validate_csv_output(empty_csv)
        assert result is False

    def test_validate_csv_missing_headers(self, csv_agent, tmp_path):
        """Test validation of CSV with missing required headers"""
        invalid_csv = tmp_path / "invalid.csv"

        with open(invalid_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Only One Header"])  # Missing required headers
            writer.writerow(["Some data"])

        result = csv_agent.validate_csv_output(invalid_csv)
        assert result is False

    def test_validate_csv_no_data_rows(self, csv_agent, tmp_path):
        """Test validation of CSV with headers but no data"""
        no_data_csv = tmp_path / "no_data.csv"

        with open(no_data_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Test Case ID", "Test Case Name",
                            "Test Steps", "Expected Results"])
            # No data rows

        result = csv_agent.validate_csv_output(no_data_csv)
        assert result is False


class TestCsvProcessing:
    """Test LLM output processing"""

    def test_process_llm_output_success(self, csv_agent, sample_agent_input, tmp_path):
        """Test successful processing of LLM output"""
        llm_output = {
            "test_cases": [
                {
                    "test_case_id": "TC_001",
                    "test_case_name": "Test case 1",
                    "test_case_description": "Description 1",
                    "test_steps": "Step 1",
                    "expected_results": "Result 1"
                }
            ],
            "metadata": {
                "total_test_cases": 1,
                "csv_headers": csv_agent._get_default_headers(),
                "coverage_summary": "Basic coverage achieved"
            }
        }

        with patch.object(csv_agent.settings, 'output_directory', tmp_path):
            result = csv_agent.process_llm_output(
                llm_output, sample_agent_input)

        assert isinstance(result, CsvOutput)
        assert result.success is True
        assert result.test_case_count == 1
        assert len(result.artifacts) == 1
        assert result.csv_file is not None
        assert result.metadata["total_test_cases"] == 1

    def test_process_llm_output_failure(self, csv_agent, sample_agent_input):
        """Test processing of invalid LLM output"""
        invalid_output = {
            "invalid_structure": "This will cause an error"
        }

        result = csv_agent.process_llm_output(
            invalid_output, sample_agent_input)

        assert isinstance(result, CsvOutput)
        assert result.success is False
        assert len(result.errors) > 0
        assert result.test_case_count == 0
