"""Agent package initialization"""
from .base import BaseAgent
from .csv_agent import CsvAgent


def create_csv_agent() -> CsvAgent:
    """Factory function for CSV agent"""
    return CsvAgent()


__all__ = ["BaseAgent", "CsvAgent", "create_csv_agent"]
