# Test script: test_di.py
from src.config.dependencies import get_container
from src.config.settings import Settings
from src.prompts.manager import PromptManager

container = get_container()

# Test basic service resolution
settings = container.get(Settings)
print(f"✅ Settings loaded: {settings.default_model}")

prompt_manager = container.get(PromptManager)
print(
    f"✅ Prompt manager loaded: {len(prompt_manager.list_available_prompts())} prompts")
