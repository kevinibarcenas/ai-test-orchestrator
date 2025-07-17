"""AI Test Orchestrator Package"""
from .utils.logger import get_logger

__version__ = "0.1.0"
__author__ = "Your Name"
__description__ = "AI-powered test automation orchestrator"

# Initialize package logger
logger = get_logger("orchestrator")
logger.info(f"Initializing {__description__} v{__version__}")
