"""Prompt management utilities"""
from pathlib import Path
from typing import Dict
from orchestrator.utils.logger import get_logger


class PromptManager:
    """Manages loading and caching of agent prompts"""

    def __init__(self):
        self.logger = get_logger("prompt_manager")
        self.prompts_dir = Path(__file__).parent
        self._cache: Dict[str, str] = {}

    def get_prompt(self, prompt_name: str) -> str:
        """
        Get prompt content by name

        Args:
            prompt_name: Name of the prompt file (without .txt extension)

        Returns:
            Prompt content as string
        """
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        prompt_file = self.prompts_dir / f"{prompt_name}.txt"

        if not prompt_file.exists():
            self.logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_name}.txt")

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            self._cache[prompt_name] = content
            self.logger.debug(f"Loaded prompt: {prompt_name}")
            return content

        except Exception as e:
            self.logger.error(f"Failed to load prompt {prompt_name}: {e}")
            raise

    def reload_prompt(self, prompt_name: str) -> str:
        """Reload prompt from disk (useful for development)"""
        if prompt_name in self._cache:
            del self._cache[prompt_name]
        return self.get_prompt(prompt_name)

    def list_available_prompts(self) -> list[str]:
        """List all available prompt files"""
        return [f.stem for f in self.prompts_dir.glob("*.txt")]


# Global prompt manager instance
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """Get global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
