#!/usr/bin/env python3
"""Quick test using the CLI with real API"""
import subprocess
import sys
from pathlib import Path


def find_swagger_files():
    """Find available Swagger files"""
    swagger_dir = Path("test").joinpath("swagger_files")
    if not swagger_dir.exists():
        print("❌ test-swagger directory not found")
        return []

    files = list(swagger_dir.glob("*.yaml")) + list(swagger_dir.glob("*.yml"))
    return files


def run_cli_test():
    """Run CLI test with the first available Swagger file"""
    print("🚀 Quick CLI Test with Real API")
    print("=" * 40)

    # Find Swagger files
    swagger_files = find_swagger_files()
    if not swagger_files:
        print("❌ No Swagger files found in test-swagger/")
        print("Please add a .yaml or .yml file to test-swagger/ directory")
        return False

    swagger_file = swagger_files[0]
    print(f"✅ Using Swagger file: {swagger_file}")

    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found - make sure OPENAI_API_KEY is set in environment")

    # Build CLI command
    cmd = [
        sys.executable, "main.py", "generate",
        "--swagger", str(swagger_file),
        "--csv-only",
        "--output", "outputs/cli_test",
        "--focus", "Generate comprehensive test cases covering CRUD operations, input validation, and error scenarios"
    ]

    print(f"🔧 Running command:")
    print(f"   {' '.join(cmd)}")
    print()

    try:
        # Run the CLI command
        result = subprocess.run(cmd, capture_output=False, text=True)

        if result.returncode == 0:
            print("\n🎉 CLI test completed successfully!")

            # Check for generated files
            output_dir = Path("outputs/cli_test")
            if output_dir.exists():
                csv_files = list(output_dir.rglob("*.csv"))
                if csv_files:
                    print(f"\n📁 Generated files:")
                    for csv_file in csv_files:
                        size = csv_file.stat().st_size
                        print(f"   ✅ {csv_file.name} ({size:,} bytes)")
                else:
                    print("⚠️  No CSV files found in output directory")

            return True
        else:
            print(f"\n❌ CLI test failed with return code: {result.returncode}")
            return False

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


if __name__ == "__main__":
    success = run_cli_test()
    sys.exit(0 if success else 1)
