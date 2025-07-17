"""Custom logging configuration with Rich formatting"""
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class OrchestratorLogger:
    """Custom logger with Rich formatting and file output"""

    _instances: dict[str, logging.Logger] = {}

    def __init__(
        self,
        name: str = "orchestrator",
        level: str = "INFO",
        log_file: Optional[Path] = None,
        enable_rich: bool = True
    ):
        self.name = name
        self.level = level.upper()
        self.log_file = log_file
        self.enable_rich = enable_rich

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, self.level))

        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Don't propagate to root logger
        self.logger.propagate = False

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup console and file handlers"""

        # Console handler with Rich formatting
        if self.enable_rich:
            console = Console(stderr=True, force_terminal=True)
            console_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=False
            )
            console_handler.setLevel(getattr(logging, self.level))
            self.logger.addHandler(console_handler)
        else:
            # Standard console handler
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(getattr(logging, self.level))
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler if specified
        if self.log_file:
            self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Setup file logging handler"""
        if not self.log_file:
            return

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files

        # File formatter (more detailed than console)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger


def get_logger(name: str = "orchestrator") -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (will be used for log file naming)

    Returns:
        Configured logger instance
    """
    # Return cached logger if it exists
    if name in OrchestratorLogger._instances:
        return OrchestratorLogger._instances[name]

    # Import settings here to avoid circular imports
    try:
        from config.settings import get_settings
        settings = get_settings()

        # Determine log file path
        log_file = None
        if settings.enable_file_logging:
            log_dir = Path("logs")
            log_file = log_dir / f"{name}.log"

        # Create logger
        orchestrator_logger = OrchestratorLogger(
            name=name,
            level=settings.log_level,
            log_file=log_file,
            # Disable rich in debug mode for cleaner output
            enable_rich=not settings.debug_mode
        )

        logger = orchestrator_logger.get_logger()

        # Cache the logger
        OrchestratorLogger._instances[name] = logger

        return logger

    except Exception as e:
        # Fallback to basic logger if settings fail
        fallback_logger = logging.getLogger(name)
        fallback_logger.setLevel(logging.INFO)

        if not fallback_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            fallback_logger.addHandler(handler)

        fallback_logger.warning(
            f"Failed to load settings, using fallback logger: {e}")
        return fallback_logger


def setup_logging(name: str = "orchestrator", force_reload: bool = False) -> logging.Logger:
    """
    Setup logging for the application

    Args:
        name: Logger name
        force_reload: Force reload of logger configuration

    Returns:
        Configured logger
    """
    if force_reload and name in OrchestratorLogger._instances:
        del OrchestratorLogger._instances[name]

    return get_logger(name)
