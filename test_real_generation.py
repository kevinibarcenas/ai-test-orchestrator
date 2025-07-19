#!/usr/bin/env python3
"""Test real end-to-end generation with OpenAI API - CSV + Postman Agents"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_full_orchestrator():
    """Test orchestrator with both CSV and Postman agents using OpenAI API"""
    print("🚀 Full Orchestrator Test - CSV + Postman Generation")
    print("=" * 70)

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
            print("Please create test/swagger_files/ directory with your YAML files")
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

        # Create orchestrator input with both CSV and Postman enabled
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            user_prompt="Generate comprehensive test cases and API collections with good coverage of CRUD operations, authentication, error handling scenarios, and professional Postman collections for enterprise usage",
            output_directory=Path("outputs/real_test"),
            sectioning_strategy=SectioningStrategy.AUTO,
            generate_csv=True,        # ✅ CSV agent (QMetry test cases)
            generate_postman=True,    # ✅ Postman agent (API collections)
            generate_karate=False,    # ❌ Disable Karate for now
            parallel_processing=False,  # Sequential for easier debugging
            max_tokens_per_section=20000  # Increased for Postman collections
        )

        print("✅ Orchestrator input configured:")
        print(f"   📁 Swagger file: {orchestrator_input.swagger_file}")
        print(f"   📝 User prompt: {orchestrator_input.user_prompt[:100]}...")
        print(f"   📂 Output directory: {orchestrator_input.output_directory}")
        print(f"   🎯 Strategy: {orchestrator_input.sectioning_strategy}")
        print(f"   📊 CSV generation: {orchestrator_input.generate_csv}")
        print(
            f"   📮 Postman generation: {orchestrator_input.generate_postman}")
        print(f"   🥋 Karate generation: {orchestrator_input.generate_karate}")
        print(
            f"   ⚡ Max tokens/section: {orchestrator_input.max_tokens_per_section}")
        print(
            f"   🔄 Parallel processing: {orchestrator_input.parallel_processing}")

        # Execute orchestration
        print(f"\n🚀 Starting orchestration...")
        print("This will:")
        print("1. 📄 Read Swagger file as text (no upload needed)")
        print("2. 🔍 Analyze content and create sections using LLM")
        print("3. 📊 Generate CSV test cases for QMetry import")
        print("4. 📮 Generate Postman collection with environments")
        print("5. 📋 Compile and validate results")
        print()

        # Start the orchestration
        result = await orchestrator.execute(orchestrator_input)

        # Display results
        print(f"\n📊 ORCHESTRATION RESULTS")
        print("=" * 50)
        print(f"✅ Success: {result.success}")
        print(f"⏱️  Processing time: {result.total_processing_time:.2f}s")
        print(f"📄 Sections processed: {result.sections_processed}")
        print(f"🧪 Test cases generated: {result.test_cases_generated}")

        # Display CSV results
        if result.csv_outputs:
            print(f"\n📊 CSV Generation Results:")
            for i, csv_output in enumerate(result.csv_outputs, 1):
                print(
                    f"   Section {i}: {csv_output.test_case_count} test cases")
                if csv_output.csv_file:
                    csv_path = Path(csv_output.csv_file)
                    if csv_path.exists():
                        size = csv_path.stat().st_size
                        print(f"   📁 File: {csv_path.name} ({size:,} bytes)")

        # Display Postman results
        if result.postman_outputs:
            print(f"\n📮 Postman Generation Results:")
            for i, postman_output in enumerate(result.postman_outputs, 1):
                print(
                    f"   Section {i}: {postman_output.request_count} requests")
                if postman_output.collection_file:
                    collection_path = Path(postman_output.collection_file)
                    if collection_path.exists():
                        size = collection_path.stat().st_size
                        print(
                            f"   📁 Collection: {collection_path.name} ({size:,} bytes)")

                if postman_output.environment_files:
                    print(
                        f"   🌍 Environments: {len(postman_output.environment_files)} files")
                    for env_file in postman_output.environment_files:
                        env_path = Path(env_file)
                        if env_path.exists():
                            print(f"      - {env_path.name}")

        # Display all generated artifacts
        artifacts = result.artifacts_generated
        if artifacts:
            print(f"\n📁 Generated Artifacts ({len(artifacts)}):")
            for artifact in artifacts:
                artifact_path = Path(artifact)
                if artifact_path.exists():
                    size = artifact_path.stat().st_size
                    print(f"   ✅ {artifact_path.name} ({size:,} bytes)")
                else:
                    print(f"   ❌ {artifact_path.name} (file not found)")

        # Display any errors or warnings
        if result.errors:
            print(f"\n⚠️  Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   • {error}")

        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"   • {warning}")

        # Display sectioning analysis info
        if hasattr(result, 'sectioning_analysis'):
            analysis = result.sectioning_analysis
            print(f"\n🔍 Section Analysis:")
            print(f"   Strategy used: {analysis.strategy_used.value}")
            print(f"   Total sections: {analysis.total_sections}")
            print(f"   Estimated tokens: {analysis.estimated_total_tokens:,}")
            if len(analysis.sections_summary) <= 3:
                for section in analysis.sections_summary:
                    print(
                        f"   📋 {section.get('name', 'Unknown')} - {section.get('estimated_tokens', 0)} tokens")
            else:
                for section in analysis.sections_summary[:3]:
                    print(
                        f"   📋 {section.get('name', 'Unknown')} - {section.get('estimated_tokens', 0)} tokens")
                print(
                    f"     ... and {len(analysis.sections_summary) - 3} more sections")

        return result.success

    except Exception as e:
        print(f"❌ Full orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the full orchestrator test with CSV and Postman agents"""
    print("🧪 AI Test Orchestrator - Multi-Agent Generation Test")
    print("=" * 60)

    success = await test_full_orchestrator()

    if success:
        print("\n🎉 SUCCESS! Multi-agent orchestrator test completed!")
        print("\n✅ Your refactored architecture is working with real OpenAI API!")
        print("\nGenerated Outputs:")
        print("📊 CSV Files: QMetry-compatible test cases for import")
        print("📮 Postman Collections: Enterprise-grade API collections")
        print("🌍 Environment Files: Dev/staging/prod configurations")
        print("📖 Documentation: Usage guides and setup instructions")
        print("\nNext steps:")
        print("1. Check the generated files in outputs/real_test/")
        print("2. Import CSV files into QMetry for test management")
        print("3. Import Postman collection and environment files")
        print("4. Review and customize the generated test scenarios")
        print("5. Implement Karate agent using the same pattern")
    else:
        print("\n❌ Multi-agent orchestrator test failed")
        print("Check the errors above and ensure:")
        print("1. OpenAI API key is valid and has sufficient credits")
        print("2. Swagger file is valid YAML/JSON format")
        print("3. Internet connection is working")
        print("4. All required dependencies are installed")
        print("5. Schema files are properly created")
        return 1

    return 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
