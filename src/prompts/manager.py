# src/prompts/manager.py
"""Advanced prompt management system with versioning and templating"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import yaml
import json

from src.utils.logger import get_logger


class PromptType(str, Enum):
    """Types of prompts in the system"""
    SYSTEM = "system"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    VALIDATION = "validation"
    SPECIALIZED = "specialized"


@dataclass
class PromptMetadata:
    """Metadata for prompt templates"""
    name: str
    version: str
    prompt_type: PromptType
    description: str
    author: str
    created_at: datetime
    last_modified: datetime
    dependencies: List[str] = None
    variables: List[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.variables is None:
            self.variables = []
        if self.tags is None:
            self.tags = []


class PromptTemplate:
    """A prompt template with variable substitution support"""

    def __init__(self,
                 content: str,
                 metadata: PromptMetadata,
                 parent: Optional['PromptTemplate'] = None):
        self.content = content
        self.metadata = metadata
        self.parent = parent
        self._variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """Extract variable placeholders from prompt content"""
        # Find all {{variable}} patterns
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, self.content)))

    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """Render the prompt with variable substitution"""
        if variables is None:
            variables = {}

        # Start with parent content if available
        content = ""
        if self.parent:
            content = self.parent.render(variables) + "\n\n"

        content += self.content

        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, str(var_value))

        return content.strip()

    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """Validate that all required variables are provided"""
        missing = []
        for var in self._variables:
            if var not in variables:
                missing.append(var)
        return missing


class PromptManager:
    """Advanced prompt management system"""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = Path(prompts_dir)
        self.logger = get_logger("prompt_manager")
        self._templates: Dict[str, PromptTemplate] = {}
        self._metadata_cache: Dict[str, PromptMetadata] = {}

        # Load all prompts on initialization
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load all prompt templates from the directory structure"""
        try:
            # Find all prompt files
            prompt_files = list(self.prompts_dir.rglob("*.txt"))
            metadata_files = list(self.prompts_dir.rglob("*.yaml"))

            # Load metadata first
            for metadata_file in metadata_files:
                self._load_metadata(metadata_file)

            # Load prompt templates
            for prompt_file in prompt_files:
                self._load_prompt_template(prompt_file)

            self.logger.info(f"Loaded {len(self._templates)} prompt templates")

        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}")
            raise

    def _load_metadata(self, metadata_file: Path) -> None:
        """Load prompt metadata from YAML file"""
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            metadata = PromptMetadata(
                name=data['name'],
                version=data['version'],
                prompt_type=PromptType(data['type']),
                description=data['description'],
                author=data['author'],
                created_at=datetime.fromisoformat(data['created_at']),
                last_modified=datetime.fromisoformat(data['last_modified']),
                dependencies=data.get('dependencies', []),
                variables=data.get('variables', []),
                tags=data.get('tags', [])
            )

            self._metadata_cache[metadata.name] = metadata

        except Exception as e:
            self.logger.warning(
                f"Failed to load metadata from {metadata_file}: {e}")

    def _load_prompt_template(self, prompt_file: Path) -> None:
        """Load a prompt template from file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Derive prompt name from file path
            relative_path = prompt_file.relative_to(self.prompts_dir)
            prompt_name = str(relative_path.with_suffix(''))

            # Get metadata or create default
            metadata = self._metadata_cache.get(
                prompt_name,
                self._create_default_metadata(prompt_name, content)
            )

            # Handle inheritance
            parent = None
            if metadata.dependencies:
                # For now, support single inheritance
                parent_name = metadata.dependencies[0]
                parent = self._templates.get(parent_name)

            template = PromptTemplate(content, metadata, parent)
            self._templates[prompt_name] = template

        except Exception as e:
            self.logger.error(
                f"Failed to load prompt template {prompt_file}: {e}")

    def _create_default_metadata(self, name: str, content: str) -> PromptMetadata:
        """Create default metadata for prompt without explicit metadata"""
        return PromptMetadata(
            name=name,
            version="1.0.0",
            prompt_type=PromptType.SYSTEM,
            description=f"Auto-generated metadata for {name}",
            author="system",
            created_at=datetime.now(),
            last_modified=datetime.now(),
            dependencies=[],
            variables=self._extract_variables_from_content(content),
            tags=[]
        )

    def _extract_variables_from_content(self, content: str) -> List[str]:
        """Extract variables from prompt content"""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, content)))

    def get_prompt(self,
                   prompt_name: str,
                   variables: Optional[Dict[str, Any]] = None,
                   version: Optional[str] = None) -> str:
        """Get rendered prompt by name"""
        template = self.get_template(prompt_name, version)
        return template.render(variables or {})

    def get_template(self,
                     prompt_name: str,
                     version: Optional[str] = None) -> PromptTemplate:
        """Get prompt template by name"""
        if version:
            versioned_name = f"{prompt_name}@{version}"
            if versioned_name in self._templates:
                return self._templates[versioned_name]

        if prompt_name not in self._templates:
            raise ValueError(f"Prompt template not found: {prompt_name}")

        return self._templates[prompt_name]

    def create_composite_prompt(self,
                                base_prompts: List[str],
                                variables: Optional[Dict[str, Any]] = None) -> str:
        """Create a composite prompt from multiple base prompts"""
        parts = []
        for prompt_name in base_prompts:
            template = self.get_template(prompt_name)
            rendered = template.render(variables or {})
            parts.append(rendered)

        return "\n\n".join(parts)

    def validate_prompt(self,
                        prompt_name: str,
                        variables: Dict[str, Any]) -> List[str]:
        """Validate prompt variables"""
        template = self.get_template(prompt_name)
        return template.validate_variables(variables)

    def list_prompts(self,
                     prompt_type: Optional[PromptType] = None,
                     tags: Optional[List[str]] = None) -> List[str]:
        """List available prompts with optional filtering"""
        results = []
        for name, template in self._templates.items():
            # Filter by type
            if prompt_type and template.metadata.prompt_type != prompt_type:
                continue

            # Filter by tags
            if tags and not any(tag in template.metadata.tags for tag in tags):
                continue

            results.append(name)

        return sorted(results)

    def list_available_prompts(self) -> List[str]:
        """List all available prompts (alias for backward compatibility)"""
        return self.list_prompts()

    def get_prompt_info(self, prompt_name: str) -> Dict[str, Any]:
        """Get detailed information about a prompt"""
        template = self.get_template(prompt_name)
        return {
            "name": template.metadata.name,
            "version": template.metadata.version,
            "type": template.metadata.prompt_type.value,
            "description": template.metadata.description,
            "author": template.metadata.author,
            "created_at": template.metadata.created_at.isoformat(),
            "last_modified": template.metadata.last_modified.isoformat(),
            "dependencies": template.metadata.dependencies,
            "variables": template._variables,
            "tags": template.metadata.tags,
            "has_parent": template.parent is not None
        }

    def reload_prompts(self) -> None:
        """Reload all prompts from disk"""
        self._templates.clear()
        self._metadata_cache.clear()
        self._load_prompts()
        self.logger.info("Prompts reloaded successfully")


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        from src.config.settings import get_settings
        settings = get_settings()
        prompts_dir = Path(__file__).parent / "templates"
        _prompt_manager = PromptManager(prompts_dir)
    return _prompt_manager


def init_prompt_manager(prompts_dir: Path) -> PromptManager:
    """Initialize prompt manager with custom directory"""
    global _prompt_manager
    _prompt_manager = PromptManager(prompts_dir)
    return _prompt_manager
