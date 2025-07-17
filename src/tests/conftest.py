"""Shared pytest fixtures and configuration"""
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

import pytest

from config.settings import Settings
from orchestrator.agents.csv_agent import CsvAgent
from orchestrator.models.schemas import *


@pytest.fixture(scope="session")
def test_settings():
    """Test settings with temporary directories"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        settings = Settings(
            openai_api_key="test_key_123",
            log_level="DEBUG",
            enable_file_logging=False,
            output_directory=temp_path / "outputs",
            registry_file=temp_path / "registry.json",
            debug_mode=True,
            max_file_size_mb=1  # Small for testing
        )

        # Create directories
        settings.output_directory.mkdir(parents=True, exist_ok=True)

        yield settings


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('orchestrator.agents.base.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = json.dumps({
            "test_cases": [
                {
                    "test_case_id": "TC_001",
                    "test_case_name": "Sample test case",
                    "test_case_description": "Sample description",
                    "test_steps": "1. Step one\n2. Step two",
                    "expected_results": "Expected result",
                    "test_type": "Functional",
                    "priority": "Medium"
                }
            ],
            "metadata": {
                "total_test_cases": 1,
                "csv_headers": [
                    "Test Case ID", "Test Case Name", "Test Case Description",
                    "Module", "Test Type", "Priority", "Estimated Time (mins)",
                    "Preconditions", "Test Steps", "Expected Results", "Test Data", "Tags"
                ]
            }
        })
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 200
        mock_response.usage.total_tokens = 300

        mock_client.responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        yield mock_client


@pytest.fixture
def sample_endpoint():
    """Sample API endpoint for testing"""
    return EndpointInfo(
        path="/api/v1/users",
        method=HttpMethod.GET,
        summary="Get users list",
        description="Retrieve a paginated list of users",
        tags=["users"],
        parameters=[
            {"name": "limit", "in": "query", "type": "integer"},
            {"name": "offset", "in": "query", "type": "integer"}
        ],
        responses={
            "200": {
                "description": "Success",
                "schema": {"type": "array", "items": {"$ref": "#/definitions/User"}}
            },
            "400": {"description": "Bad Request"},
            "401": {"description": "Unauthorized"}
        }
    )


@pytest.fixture
def sample_test_case(sample_endpoint):
    """Sample test case for testing"""
    return TestCase(
        id="TC_001",
        name="Verify GET /users returns user list successfully",
        description="Test that GET request to /users endpoint returns a valid list of users",
        endpoint=sample_endpoint,
        test_type=TestCaseType.HAPPY_PATH,
        priority="High",
        test_data={
            "limit": 10,
            "offset": 0,
            "headers": {"Authorization": "Bearer <token>"}
        },
        expected_result={
            "status_code": 200,
            "response_type": "array",
            "min_items": 0
        },
        assertions=[
            "response.status == 200",
            "response.header['content-type'] == 'application/json'",
            "response.jsonPath('$').isArray()"
        ],
        preconditions=[
            "API server is running",
            "Valid authentication token is available"
        ]
    )


@pytest.fixture
def sample_test_section(sample_endpoint, sample_test_case):
    """Sample test section for testing"""
    return TestSection(
        section_id="users_management",
        name="User Management API",
        description="Test cases for user-related API endpoints",
        endpoints=[sample_endpoint],
        test_cases=[sample_test_case],
        estimated_tokens=1500
    )


@pytest.fixture
def sample_agent_input(sample_test_section):
    """Sample agent input for testing"""
    return AgentInput(
        section=sample_test_section,
        swagger_file_id="file_abc123",
        pdf_file_id="file_def456",
        templates={
            "csv_template": "qmetry_standard",
            "include_test_data": True
        },
        context={
            "project_name": "Test API",
            "environment": "staging",
            "base_url": "https://api.test.com"
        }
    )


@pytest.fixture
def csv_agent(test_settings, mock_openai_client):
    """CSV agent instance for testing"""
    with patch('orchestrator.agents.csv_agent.get_settings', return_value=test_settings):
        agent = CsvAgent()
        yield agent


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing"""
    return [
        ["Test Case ID", "Test Case Name", "Test Case Description",
            "Test Steps", "Expected Results"],
        ["TC_001", "Test login", "Test user login functionality",
            "1. Enter credentials\n2. Click login", "User is logged in"],
        ["TC_002", "Test logout", "Test user logout functionality",
            "1. Click logout button", "User is logged out"]
    ]


@pytest.fixture
def temp_csv_file(tmp_path, sample_csv_content):
    """Temporary CSV file for testing"""
    import csv

    csv_file = tmp_path / "test_cases.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in sample_csv_content:
            writer.writerow(row)

    return csv_file


# Sample files fixtures
@pytest.fixture
def sample_swagger_content():
    """Sample OpenAPI/Swagger content"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Sample API for testing"
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get users",
                    "description": "Retrieve list of users",
                    "tags": ["users"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "default": 10}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/User"}
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create user",
                    "description": "Create a new user",
                    "tags": ["users"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CreateUser"}
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "User created"},
                        "400": {"description": "Invalid input"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"}
                    }
                },
                "CreateUser": {
                    "type": "object",
                    "required": ["name", "email"],
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"}
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_swagger_file(tmp_path, sample_swagger_content):
    """Sample swagger YAML file"""
    import yaml

    swagger_file = tmp_path / "api_spec.yaml"
    with open(swagger_file, 'w') as f:
        yaml.dump(sample_swagger_content, f)

    return swagger_file


# Test directory setup
@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests"""
    import logging
    logging.getLogger("orchestrator").setLevel(logging.DEBUG)


# Mock utilities
@pytest.fixture
def mock_file_manager():
    """Mock file manager for testing"""
    with patch('orchestrator.core.file_manager.get_file_manager') as mock_fm:
        mock_manager = Mock()
        mock_manager.upload_file.return_value = Mock(file_id="file_123")
        mock_manager.get_file_info.return_value = None
        mock_fm.return_value = mock_manager
        yield mock_manager
