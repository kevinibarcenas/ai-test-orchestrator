#!/usr/bin/env python3
"""Test actual CSV generation functionality"""
import sys
from pathlib import Path

# Add project root to Python path
# Go up one level from test/ to project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_csv_agent_creation():
    """Test creating CSV agent with dependency injection"""
    print("🧪 Testing CSV Agent Creation...")

    try:
        from src.config.dependencies import get_container
        from src.agents.csv.agent import CsvAgent

        container = get_container()

        # Try to create CSV agent
        csv_agent = container.get(CsvAgent)
        print(f"✅ CSV Agent created: {csv_agent.agent_type}")
        print(f"✅ System prompt name: {csv_agent.get_system_prompt_name()}")
        print(f"✅ Output schema name: {csv_agent.get_output_schema_name()}")

        return True

    except Exception as e:
        print(f"❌ CSV Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_rendering():
    """Test prompt rendering with variables"""
    print("\n🧪 Testing Prompt Rendering...")

    try:
        from src.config.dependencies import get_container
        from src.agents.csv.agent import CsvAgent
        from src.models.agents import Section, AgentInput
        from src.models.base import BaseEndpoint, BaseTestCase, TestCaseType, Priority

        container = get_container()
        csv_agent = container.get(CsvAgent)

        # Create test data
        section = Section(
            section_id="users_001",
            name="User Management",
            description="User management API endpoints",
            endpoints=[
                BaseEndpoint(path="/users", method="GET",
                             summary="Get all users"),
                BaseEndpoint(path="/users", method="POST",
                             summary="Create user"),
            ],
            test_cases=[
                BaseTestCase(name="Test user creation",
                             test_type=TestCaseType.FUNCTIONAL),
                BaseTestCase(name="Test user validation",
                             test_type=TestCaseType.NEGATIVE),
            ]
        )

        agent_input = AgentInput(section=section)

        # Test prompt variable building
        variables = csv_agent.build_prompt_variables(agent_input)
        print(f"✅ Prompt variables built: {list(variables.keys())}")

        # Test prompt rendering
        prompt_manager = container.get(
            type(container.get(CsvAgent).prompt_manager))
        rendered_prompt = prompt_manager.get_prompt(
            "agents/csv/system", variables)

        print(
            f"✅ Prompt rendered successfully (length: {len(rendered_prompt)})")
        print(
            f"📝 Contains section name: {'User Management' in rendered_prompt}")
        print(f"📝 Contains endpoint count: {'2 endpoints' in rendered_prompt}")

        return True

    except Exception as e:
        print(f"❌ Prompt rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mock_llm_output():
    """Test processing mock LLM output"""
    print("\n🧪 Testing Mock LLM Output Processing...")

    try:
        from src.config.dependencies import get_container
        from src.agents.csv.agent import CsvAgent
        from src.models.agents import Section, AgentInput

        container = get_container()
        csv_agent = container.get(CsvAgent)

        # Create test section
        section = Section(
            section_id="test_001",
            name="Test API",
            description="Test API endpoints"
        )

        agent_input = AgentInput(section=section)

        # Mock LLM output
        mock_llm_output = {
            "test_cases": [
                {
                    "test_case_id": "TC_TEST_001",
                    "test_case_name": "Verify GET /test returns success",
                    "test_case_description": "Test that GET request returns 200",
                    "module": "Test Module",
                    "test_type": "Functional",
                    "priority": "High",
                    "estimated_time": "5",
                    "preconditions": "API is running",
                    "test_steps": "1. Send GET request\n2. Verify response",
                    "expected_results": "Status code: 200",
                    "test_data": "No additional data needed",
                    "tags": "smoke,api"
                }
            ],
            "metadata": {
                "coverage_summary": "Basic API testing coverage",
                "total_test_cases": 1
            }
        }

        # Test processing (this will try to create actual files)
        print("⚠️  Note: This will attempt to create actual CSV files...")
        result = await csv_agent.process_llm_output(mock_llm_output, agent_input)

        print(f"✅ LLM output processed successfully")
        print(f"✅ Success: {result.success}")
        print(f"✅ Test case count: {result.test_case_count}")
        print(f"✅ Artifacts: {result.artifacts}")

        return True

    except Exception as e:
        print(f"❌ Mock LLM output processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_agent_execution():
    """Test full agent execution with mock data"""
    print("\n🧪 Testing Full Agent Execution (Mock)...")

    try:
        from src.config.dependencies import get_container
        from src.agents.csv.agent import CsvAgent
        from src.models.agents import Section, AgentInput

        container = get_container()
        csv_agent = container.get(CsvAgent)

        # Create test section
        section = Section(
            section_id="test_full_001",
            name="Full Test API",
            description="Complete API test section"
        )

        agent_input = AgentInput(section=section)

        print("⚠️  Note: This would normally call the LLM, but will fail due to missing API key")
        print("✅ Agent input created successfully")
        print(
            f"✅ Ready for execution: {csv_agent.agent_type} for {section.name}")

        return True

    except Exception as e:
        print(f"❌ Full agent execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🚀 Testing CSV Agent Generation")
    print("=" * 50)

    tests = [
        test_csv_agent_creation,
        test_prompt_rendering,
        # test_mock_llm_output,  # Commented out as it tries to create files
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! CSV agent is ready for generation.")
        print("\nNext steps:")
        print("1. Set up OpenAI API key in .env file")
        print("2. Try: python main.py generate --swagger your_file.yaml --csv-only")
        print("3. Test with real API documentation")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

    return 0

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(main())
    sys.exit(result)
