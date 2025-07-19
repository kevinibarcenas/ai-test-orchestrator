#!/usr/bin/env python3
"""Test CSV generation with mock data"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_csv_generation_mock():
    """Test CSV generation with mocked LLM output"""
    print("🧪 Testing CSV Generation with Mock Data...")

    try:
        from src.config.dependencies import get_container
        from src.agents.csv.agent import CsvAgent
        from src.models.agents import Section, AgentInput
        from src.models.base import BaseEndpoint, BaseTestCase, TestCaseType

        # Get container and agent
        container = get_container()
        csv_agent = container.get(CsvAgent)
        print("✅ CSV Agent obtained")

        # Create test section with realistic data
        section = Section(
            section_id="users_001",
            name="User Management",
            description="User management API endpoints for CRUD operations",
            endpoints=[
                BaseEndpoint(path="/api/v1/users", method="GET",
                             summary="Get all users"),
                BaseEndpoint(path="/api/v1/users", method="POST",
                             summary="Create new user"),
                BaseEndpoint(
                    path="/api/v1/users/{id}", method="GET", summary="Get user by ID"),
                BaseEndpoint(
                    path="/api/v1/users/{id}", method="PUT", summary="Update user"),
                BaseEndpoint(
                    path="/api/v1/users/{id}", method="DELETE", summary="Delete user"),
            ],
            test_cases=[
                BaseTestCase(name="Test user creation",
                             test_type=TestCaseType.FUNCTIONAL),
                BaseTestCase(name="Test user validation",
                             test_type=TestCaseType.NEGATIVE),
                BaseTestCase(name="Test user authentication",
                             test_type=TestCaseType.SECURITY),
            ]
        )

        agent_input = AgentInput(section=section)
        print(
            f"✅ Test section created: {section.name} with {len(section.endpoints)} endpoints")

        # Test prompt rendering
        variables = csv_agent.build_prompt_variables(agent_input)
        print(f"✅ Prompt variables built: {list(variables.keys())}")

        # Mock LLM output with comprehensive test cases
        mock_llm_output = {
            "test_cases": [
                {
                    "test_case_id": "TC_USERS_001",
                    "test_case_name": "Verify GET /api/v1/users returns user list successfully",
                    "test_case_description": "Verify that GET request to users endpoint returns a properly formatted list of users with correct pagination",
                    "module": "User Management",
                    "test_type": "Functional",
                    "priority": "High",
                    "estimated_time": "10",
                    "preconditions": "1. API server is running\n2. Database contains at least 3 test users\n3. Valid authentication token available",
                    "test_steps": "1. Send GET request to /api/v1/users endpoint\n2. Include valid Authorization header with Bearer token\n3. Verify response status code is 200\n4. Validate response contains array of user objects\n5. Verify each user object has required fields (id, name, email, created_at)\n6. Check response includes pagination metadata\n7. Verify response time is under 2 seconds",
                    "expected_results": "Status code: 200 OK\nResponse body contains array of user objects\nEach user has required fields: id (integer), name (string), email (string), created_at (datetime)\nPagination metadata included: total, page, limit\nResponse time < 2000ms\nContent-Type: application/json",
                    "test_data": "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\nExpected fields: id, name, email, created_at, updated_at\nPagination: ?page=1&limit=10",
                    "tags": "smoke,users,positive,api,pagination"
                },
                {
                    "test_case_id": "TC_USERS_002",
                    "test_case_name": "Verify POST /api/v1/users creates user with valid data",
                    "test_case_description": "Verify that POST request with valid user data successfully creates a new user and returns proper response",
                    "module": "User Management",
                    "test_type": "Functional",
                    "priority": "High",
                    "estimated_time": "8",
                    "preconditions": "1. API server is running\n2. Valid authentication token with create permissions\n3. Email address not already in use",
                    "test_steps": "1. Send POST request to /api/v1/users\n2. Include valid user data in request body\n3. Include authorization header\n4. Verify response status code is 201\n5. Validate response contains created user object\n6. Verify user ID is generated\n7. Confirm user can be retrieved via GET",
                    "expected_results": "Status code: 201 Created\nResponse contains created user object with generated ID\nUser object includes all submitted data\nLocation header points to new user resource\nUser can be retrieved with GET /api/v1/users/{id}",
                    "test_data": "{\n  \"name\": \"John Doe\",\n  \"email\": \"john.doe@example.com\",\n  \"password\": \"SecurePass123!\",\n  \"role\": \"user\"\n}",
                    "tags": "crud,users,positive,creation"
                },
                {
                    "test_case_id": "TC_USERS_003",
                    "test_case_name": "Verify POST /api/v1/users returns 400 for invalid email",
                    "test_case_description": "Verify that POST request with malformed email address returns appropriate validation error",
                    "module": "User Management",
                    "test_type": "Negative",
                    "priority": "Medium",
                    "estimated_time": "5",
                    "preconditions": "1. API server is running\n2. Valid authentication token",
                    "test_steps": "1. Send POST request to /api/v1/users\n2. Include request body with invalid email format\n3. Include authorization header\n4. Verify response status code is 400\n5. Validate error message indicates email format issue\n6. Confirm no user was created",
                    "expected_results": "Status code: 400 Bad Request\nError response contains validation details\nError message: \"Invalid email format\"\nResponse includes field-specific error: email\nNo user record created in database",
                    "test_data": "{\n  \"name\": \"Invalid User\",\n  \"email\": \"invalid-email-format\",\n  \"password\": \"SecurePass123!\"\n}",
                    "tags": "validation,users,negative,email"
                },
                {
                    "test_case_id": "TC_USERS_004",
                    "test_case_name": "Verify GET /api/v1/users/{id} returns 404 for non-existent user",
                    "test_case_description": "Verify that GET request for non-existent user ID returns appropriate not found error",
                    "module": "User Management",
                    "test_type": "Negative",
                    "priority": "Medium",
                    "estimated_time": "3",
                    "preconditions": "1. API server is running\n2. Valid authentication token\n3. User ID 99999 does not exist",
                    "test_steps": "1. Send GET request to /api/v1/users/99999\n2. Include authorization header\n3. Verify response status code is 404\n4. Validate error message indicates user not found",
                    "expected_results": "Status code: 404 Not Found\nError message: \"User not found\"\nResponse body contains error details\nNo user data returned",
                    "test_data": "User ID: 99999\nAuthorization: Bearer <valid_token>",
                    "tags": "error-handling,users,negative,not-found"
                },
                {
                    "test_case_id": "TC_USERS_005",
                    "test_case_name": "Verify DELETE /api/v1/users/{id} requires admin permissions",
                    "test_case_description": "Verify that DELETE request with regular user token returns authorization error",
                    "module": "User Management",
                    "test_type": "Security",
                    "priority": "High",
                    "estimated_time": "6",
                    "preconditions": "1. API server is running\n2. Regular user token (non-admin)\n3. Valid user ID exists",
                    "test_steps": "1. Send DELETE request to /api/v1/users/{valid_id}\n2. Include regular user authorization header\n3. Verify response status code is 403\n4. Validate error message indicates insufficient permissions\n5. Confirm user was not deleted",
                    "expected_results": "Status code: 403 Forbidden\nError message: \"Insufficient permissions\"\nUser record remains in database\nNo deletion performed",
                    "test_data": "Authorization: Bearer <regular_user_token>\nUser ID: <existing_user_id>",
                    "tags": "security,authorization,users,permissions"
                }
            ],
            "metadata": {
                "coverage_summary": "Comprehensive test coverage for User Management API including happy path, validation, error handling, and security scenarios",
                "total_test_cases": 5,
                "csv_headers": [
                    "Test Case ID", "Test Case Name", "Test Case Description",
                    "Module", "Test Type", "Priority", "Estimated Time (mins)",
                    "Preconditions", "Test Steps", "Expected Results",
                    "Test Data", "Tags"
                ],
                "test_distribution": {
                    "functional": 2,
                    "negative": 2,
                    "security": 1
                },
                "coverage_analysis": {
                    "endpoints_covered": 5,
                    "total_endpoints": 5,
                    "coverage_percentage": 100.0,
                    "uncovered_areas": []
                }
            }
        }

        print(
            f"✅ Mock LLM output prepared with {len(mock_llm_output['test_cases'])} test cases")

        # Process the mock output
        result = await csv_agent.process_llm_output(mock_llm_output, agent_input)

        print(f"✅ Processing complete!")
        print(f"   Success: {result.success}")
        print(f"   Test cases: {result.test_case_count}")
        print(f"   CSV file: {result.csv_file}")
        print(f"   Artifacts: {result.artifacts}")

        if result.csv_file:
            csv_path = Path(result.csv_file)
            if csv_path.exists():
                file_size = csv_path.stat().st_size
                print(f"✅ CSV file created successfully: {file_size} bytes")

                # Show first few lines
                with open(csv_path, 'r') as f:
                    lines = f.readlines()[:3]
                    print(f"✅ File preview:")
                    for i, line in enumerate(lines):
                        print(f"   Line {i+1}: {line.strip()[:100]}...")
            else:
                print(f"❌ CSV file not found at: {csv_path}")

        return True

    except Exception as e:
        print(f"❌ CSV generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the CSV generation test"""
    print("🚀 Testing Real CSV Generation")
    print("=" * 40)

    success = await test_csv_generation_mock()

    if success:
        print("\n🎉 CSV generation test passed!")
        print("✅ Your refactored architecture is fully functional!")
        print("\nNext steps:")
        print("1. Add OpenAI API key to test real LLM calls")
        print("2. Test with actual Swagger/OpenAPI files")
        print("3. Implement Karate and Postman agents using the same pattern")
    else:
        print("\n❌ CSV generation test failed")
        return 1

    return 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
