#!/usr/bin/env python3
"""Simple test for the refactored setup - run from project root"""
import sys
from pathlib import Path

# Add current directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_basic_imports():
    """Test that we can import the basic components"""
    print("🧪 Testing Basic Imports...")

    try:
        # Test settings
        from src.config.settings import get_settings
        settings = get_settings()
        print(f"✅ Settings: {settings.default_model}")

        # Test logger
        from src.utils.logger import get_logger
        logger = get_logger("test")
        print("✅ Logger loaded")

        # Test models
        from src.models.base import AgentType
        print(f"✅ Models: {list(AgentType)}")

        # Test dependency injection
        from src.config.dependencies import get_container
        container = get_container()
        print("✅ DI Container loaded")

        return True

    except Exception as e:
        print(f"❌ Basic imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_manager():
    """Test prompt manager"""
    print("\n🧪 Testing Prompt Manager...")

    try:
        from src.prompts.manager import get_prompt_manager
        prompt_manager = get_prompt_manager()

        prompts = prompt_manager.list_available_prompts()
        print(f"✅ Found {len(prompts)} prompts")

        if prompts:
            print(f"✅ Available prompts: {prompts}")

        return True

    except Exception as e:
        print(f"❌ Prompt manager failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_agent():
    """Test CSV agent creation"""
    print("\n🧪 Testing CSV Agent...")

    try:
        from src.config.dependencies import get_container

        # Try to get container
        container = get_container()
        print("✅ Container obtained")

        # Try to create CSV agent
        from src.agents.csv.agent import CsvAgent
        csv_agent = container.get(CsvAgent)
        print(f"✅ CSV Agent created: {csv_agent.agent_type}")

        return True

    except Exception as e:
        print(f"❌ CSV agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests"""
    print("🚀 Simple Test Suite")
    print("=" * 30)

    tests = [
        test_basic_imports,
        test_prompt_manager,
        test_csv_agent
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
