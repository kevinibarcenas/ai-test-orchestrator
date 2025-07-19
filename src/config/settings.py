"""Application settings and configuration management"""
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # OpenAI Configuration
    openai_api_key: str = Field("", description="OpenAI API key")
    openai_max_retries: int = Field(3, description="Maximum API retries")
    openai_timeout: int = Field(60, description="API timeout in seconds")
    openai_base_url: Optional[str] = Field(
        None, description="Custom OpenAI base URL")

    # Model Configuration
    default_model: str = Field("gpt-4o", description="Default GPT model")
    reasoning_model: str = Field(
        "o3-mini", description="Reasoning model for complex tasks")
    max_tokens: int = Field(4000, description="Maximum tokens per request")

    # Logging Configuration
    log_level: str = Field("INFO", description="Logging level")
    enable_file_logging: bool = Field(True, description="Enable file logging")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

    # File Management
    max_file_size_mb: int = Field(32, description="Maximum file size in MB")
    upload_timeout: int = Field(
        300, description="File upload timeout in seconds")
    supported_file_types: list[str] = Field(
        default=[".yaml", ".yml", ".json", ".pdf"],
        description="Supported file types"
    )

    # Agent Configuration
    max_concurrent_agents: int = Field(
        3, description="Maximum concurrent agents")
    agent_timeout: int = Field(
        120, description="Agent execution timeout in seconds")

    # Output Configuration
    output_directory: Path = Field(
        Path("outputs"), description="Base output directory"
    )
    backup_outputs: bool = Field(True, description="Backup existing outputs")

    # Registry Configuration
    registry_file: Path = Field(
        Path("registry.json"), description="Test registry file path"
    )
    enable_change_detection: bool = Field(
        True, description="Enable change detection for incremental updates"
    )

    # Development Configuration
    debug_mode: bool = Field(False, description="Enable debug mode")
    enable_dry_run: bool = Field(False, description="Enable dry run mode")

    @field_validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("output_directory", "registry_file")
    def create_directories(cls, v):
        if isinstance(v, Path):
            v.parent.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("max_file_size_mb")
    def validate_file_size(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("max_file_size_mb must be between 1 and 100")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)"""
    global _settings
    _settings = Settings()
    return _settings
