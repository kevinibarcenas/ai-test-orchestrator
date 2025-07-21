#!/usr/bin/env python3
"""Test real end-to-end generation with OpenAI API - Complete Multi-Agent Test"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_complete_orchestrator():
    """Test orchestrator with all agents using OpenAI API - Production Ready"""
    print("🚀 AI Test Orchestrator - Complete Production Test")
    print("=" * 60)

    try:
        # Check for API key
        from src.config.settings import get_settings
        settings = get_settings()

        if not settings.openai_api_key:
            print("❌ OpenAI API key not found!")
            print("Please set OPENAI_API_KEY in your .env file or environment variables")
            return False

        print(f"✅ OpenAI API key configured")
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

        # Use the first Swagger file
        swagger_file = swagger_files[0]
        api_name = swagger_file.stem.replace('_', ' ').title()
        print(f"🎯 Testing with: {api_name} ({swagger_file.name})")

        # Get orchestrator from DI container
        from src.config.dependencies import get_container
        from src.core.orchestrator import TestOrchestrator
        from src.models.orchestrator import OrchestratorInput, SectioningStrategy

        container = get_container()
        orchestrator = container.get(TestOrchestrator)

        # Create orchestrator input with all agents enabled
        orchestrator_input = OrchestratorInput(
            swagger_file=swagger_file,
            user_prompt="Focus on all endpoints with 100 percent coverage, that means all possible values for fields with enumerated or status-like values",
            output_directory=Path("outputs/artifacts"),
            sectioning_strategy=SectioningStrategy.AUTO,
            generate_csv=True,        # ✅ QMetry test cases
            generate_karate=True,     # ✅ BDD feature files
            generate_postman=True,    # ✅ API collections
            parallel_processing=True,  # ✅ Enable parallel execution
            generate_documentation=False,     # 📋 Master documentation flag
        )

        print(f"\n🔧 Configuration:")
        print(f"   📊 CSV Generation: {orchestrator_input.generate_csv}")
        print(f"   🥋 Karate Generation: {orchestrator_input.generate_karate}")
        print(
            f"   📮 Postman Generation: {orchestrator_input.generate_postman}")
        print(
            f"   ⚡ Parallel Processing: {orchestrator_input.parallel_processing}")
        print(f"   🎯 Strategy: {orchestrator_input.sectioning_strategy.value}")

        print(f"\n🚀 Starting complete test generation...")
        print("⏳ Please wait... This may take 1-2 minutes for full processing")

        # Start the orchestration
        result = await orchestrator.execute(orchestrator_input)

        # Calculate token usage and costs (approximate)
        total_tokens = result.total_token_usage.get("total_tokens", 0)
        input_tokens = result.total_token_usage.get("input_tokens", 0)
        output_tokens = result.total_token_usage.get("output_tokens", 0)

        # Display clean results summary
        print(f"\n" + "="*60)
        print(f"📊 ORCHESTRATION RESULTS")
        print(f"="*60)

        if result.success:
            print(f"✅ Status: SUCCESS")
        else:
            print(f"❌ Status: FAILED")

        print(f"⏱️  Processing Time: {result.total_processing_time:.1f}s")
        print(f"📄 API Sections: {result.sections_processed}")
        print(f"🧪 Total Test Cases: {result.test_cases_generated}")

        # Token usage summary
        print(f"\n💰 Token Usage & Cost:")
        print(f"   📥 Input Tokens: {input_tokens:,}")
        print(f"   📤 Output Tokens: {output_tokens:,}")
        print(f"   🔢 Total Tokens: {total_tokens:,}")

        # Agent-specific results
        agent_summary = []

        if result.csv_outputs:
            csv_count = sum(
                output.test_case_count for output in result.csv_outputs)
            csv_files = len(
                [output for output in result.csv_outputs if output.success])
            agent_summary.append(
                f"📊 CSV: {csv_files} files, {csv_count} test cases")

        if result.karate_outputs:
            karate_scenarios = sum(
                output.scenario_count for output in result.karate_outputs)
            karate_files = len(
                [output for output in result.karate_outputs if output.success])
            agent_summary.append(
                f"🥋 Karate: {karate_files} features, {karate_scenarios} scenarios")

        if result.postman_outputs:
            postman_requests = sum(
                output.request_count for output in result.postman_outputs)
            postman_collections = 1 if any(
                output.success for output in result.postman_outputs) else 0
            agent_summary.append(
                f"📮 Postman: {postman_collections} collection, {postman_requests} requests")

        if agent_summary:
            print(f"\n🎯 Generated Artifacts:")
            for summary in agent_summary:
                print(f"   {summary}")

        # Show sample generated files
        artifacts = result.artifacts_generated
        if artifacts:
            print(f"\n📁 Sample Generated Files:")

            # Group by type and show examples
            csv_files = [f for f in artifacts if f.endswith('.csv')]
            feature_files = [f for f in artifacts if f.endswith('.feature')]
            postman_files = [f for f in artifacts if any(
                x in f.lower() for x in ['collection', 'environment'])]

            if csv_files:
                sample_csv = Path(csv_files[0])
                size = sample_csv.stat().st_size if sample_csv.exists() else 0
                print(f"   📊 {sample_csv.name} ({size:,} bytes)")

            if feature_files:
                sample_feature = Path(feature_files[0])
                size = sample_feature.stat().st_size if sample_feature.exists() else 0
                print(f"   🥋 {sample_feature.name} ({size:,} bytes)")

            if postman_files:
                sample_postman = Path(postman_files[0])
                size = sample_postman.stat().st_size if sample_postman.exists() else 0
                print(f"   📮 {sample_postman.name} ({size:,} bytes)")

            if len(artifacts) > 3:
                print(f"   📂 ... and {len(artifacts) - 3} more files")

        # Display output location
        print(f"\n📂 Output Location: {orchestrator_input.output_directory}")

        # Show any critical errors
        if result.errors:
            print(f"\n⚠️  Issues Found ({len(result.errors)}):")
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"   • {error[:100]}{'...' if len(error) > 100 else ''}")
            if len(result.errors) > 3:
                print(f"   • ... and {len(result.errors) - 3} more issues")

        return result.success

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return False


async def main():
    """Run the complete production test"""
    success = await test_complete_orchestrator()

    print(f"\n" + "="*60)
    if success:
        print("🎉 SUCCESS! Production test completed successfully!")
        print("\n📋 Next Steps:")
        print("   1. 📊 Import CSV files into QMetry for test management")
        print("   2. 🥋 Copy Karate features to your test project")
        print("   3. 📮 Import Postman collection for API testing")
        print("   4. 🔧 Configure environments and variables")
        print("   5. 🚀 Execute tests in your CI/CD pipeline")

        print(f"\n✨ All artifacts are production-ready and enterprise-grade!")

    else:
        print("❌ Production test failed!")
        print("\n🔍 Troubleshooting:")
        print("   • Check OpenAI API key and credits")
        print("   • Verify Swagger file is valid YAML/JSON")
        print("   • Ensure stable internet connection")
        print("   • Review error messages above")
        return 1

    return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
