#!/usr/bin/env python3
"""Main entry point for AI Test Orchestrator"""
import sys
from pathlib import Path

# Ensure we can import from src
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    try:
        from src.scripts.cli import app
        app()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(
            f"Make sure you're in the project root directory: {project_root}")
        print("Available directories:")
        for item in project_root.iterdir():
            if item.is_dir():
                print(f"  - {item.name}/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
