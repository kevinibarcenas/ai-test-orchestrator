#!/usr/bin/env python3
"""Test real end-to-end generation with OpenAI API"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_full_orchestrator():
    """Test the full orchestrator with real API calls"""
    print("🚀 Testing Full Orchestrator with Real OpenAI API")
    print("=" * 60)

    try:
        # Check for API key
        from src.config.settings import get_settings
        settings = get_settings()

        if not settings.openai_api_key:
            print("❌ OpenAI API key not found!")
            print("Please set OPENAI_API_KEY in your .env file or environment variables")
            return False

        print(
            f"✅ OpenAI API key found (ends with: ...{settings.openai_api_key[-4:]})")
        print(f"✅ Using model: {settings.default_model}")

        # Check for Swagger files
        swagger_dir = Path("test").joinpath("swagger_files")
        if not swagger_dir.exists():
            print(f"❌ Swagger directory not found: {swagger_dir}")
            print("Please create test-swagger/ directory with your YAML files")
            return False

        swagger_files = list(swagger_dir.glob("*.yaml")) + \
            list(swagger_dir.glob("*.yml"))
        if not swagger_files:
            print(f"❌ No YAML files found in {swagger_dir}")
            return False

        print(f"✅ Found {len(swagger_files)} Swagger files:")
        for f in swagger_files:
            print(f"   📄 {f.name}")

        # Use the first Swagger file
        swagger_file = swagger_files[0]
        print(f"\n🎯 Testing with: {swagger_file.name}")

        # Get orchestrator from DI container
        from src.config.dependencies import get_container
        from src.core.orchestrator import TestOrchestrator
        from src.models.orchestrator import OrchestratorInput, SectioningStrategy

        container = get_container()
        orchestrator = container.get(TestOrchestrator)
        print("✅ Orchestrator created via dependency injection")

        # Create orchestrator input
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            user_prompt="Focus on generating comprehensive test cases with good coverage of CRUD operations, authentication, and error handling scenarios",
            output_directory=Path("outputs/real_test"),
            sectioning_strategy=SectioningStrategy.AUTO,
            generate_csv=True,
            generate_karate=False,  # Disable for now since we only have CSV agent
            generate_postman=False,  # Disable for now since we only have CSV agent
            parallel_processing=False,  # Sequential for easier debugging
            max_tokens_per_section=6000
        )

        print("✅ Orchestrator input configured:")
        print(f"   📁 Swagger file: {orchestrator_input.swagger_file}")
        print(f"   📝 User prompt: {orchestrator_input.user_prompt[:100]}...")
        print(f"   📂 Output directory: {orchestrator_input.output_directory}")
        print(f"   🎯 Strategy: {orchestrator_input.sectioning_strategy}")
        print(f"   🔧 CSV generation: {orchestrator_input.generate_csv}")
        print(
            f"   ⚡ Max tokens/section: {orchestrator_input.max_tokens_per_section}")

        # Execute orchestration
        print(f"\n🚀 Starting orchestration...")
        print("This will:")
        print("1. 📤 Upload Swagger file to OpenAI")
        print("2. 🔍 Analyze content and create sections")
        print("3. 🧪 Generate test cases for each section")
        print("4. 📊 Compile results and create CSV files")
        print()

        result = await orchestrator.execute(orchestrator_input)

        # Display results
        print(f"\n📊 ORCHESTRATION RESULTS")
        print("=" * 40)
        print(f"✅ Success: {result.success}")
        print(f"⏱️  Processing time: {result.total_processing_time:.2f}s")
        print(f"📄 Sections processed: {result.sections_processed}")
        print(f"🧪 Test cases generated: {result.test_cases_generated}")

        if result.total_token_usage.get("total_tokens"):
            print(
                f"🪙 Total tokens used: {result.total_token_usage['total_tokens']:,}")
            print(
                f"   📥 Input tokens: {result.total_token_usage.get('input_tokens', 0):,}")
            print(
                f"   📤 Output tokens: {result.total_token_usage.get('output_tokens', 0):,}")

        if result.artifacts_generated:
            print(
                f"\n📁 Generated Artifacts ({len(result.artifacts_generated)}):")
            for artifact in result.artifacts_generated:
                artifact_path = Path(artifact)
                if artifact_path.exists():
                    size = artifact_path.stat().st_size
                    print(f"   ✅ {artifact_path.name} ({size:,} bytes)")
                else:
                    print(f"   ❌ {artifact_path.name} (not found)")

        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   • {error}")

        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"   • {warning}")

        print(f"\n📋 Summary:")
        print(f"   {result.summary}")

        # Show sectioning analysis
        if hasattr(result, 'sectioning_analysis'):
            analysis = result.sectioning_analysis
            print(f"\n🔍 Sectioning Analysis:")
            print(f"   Strategy used: {analysis.strategy_used}")
            print(f"   Total sections: {analysis.total_sections}")
            print(f"   Estimated tokens: {analysis.estimated_total_tokens:,}")
            if analysis.sections_summary:
                print(f"   Section details:")
                # Show first 3
                for i, section in enumerate(analysis.sections_summary[:3], 1):
                    print(
                        f"     {i}. {section.get('name', 'Unknown')} - {section.get('estimated_tokens', 0)} tokens")
                if len(analysis.sections_summary) > 3:
                    print(
                        f"     ... and {len(analysis.sections_summary) - 3} more sections")

        return result.success

    except Exception as e:
        print(f"❌ Full orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the full orchestrator test"""
    print("🧪 AI Test Orchestrator - Real Generation Test")
    print("=" * 50)

    success = await test_full_orchestrator()

    if success:
        print("\n🎉 SUCCESS! Full orchestrator test completed!")
        print("\n✅ Your refactored architecture is working with real OpenAI API!")
        print("\nNext steps:")
        print("1. Check the generated CSV files in outputs/real_test/")
        print("2. Implement Karate and Postman agents using the same pattern")
        print("3. Test with different Swagger files and user prompts")
        print("4. Optimize prompts and sectioning strategies")
    else:
        print("\n❌ Full orchestrator test failed")
        print("Check the errors above and ensure:")
        print("1. OpenAI API key is valid")
        print("2. Swagger file is valid YAML/JSON")
        print("3. Internet connection is working")
        return 1

    return 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
