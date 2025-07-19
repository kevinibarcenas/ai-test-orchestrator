"""Agent factory for creating and managing agent instances"""
from typing import Dict, Type, Optional, Any

from src.config.dependencies import inject, get_container
from src.models.base import AgentType
from src.agents.base.agent import BaseAgent
from src.utils.logger import get_logger


class AgentFactory:
    """Factory for creating agent instances with proper dependency injection"""

    @inject
    def __init__(self):
        self.logger = get_logger("agent_factory")
        self._agent_registry: Dict[AgentType, Type[BaseAgent]] = {}
        self._agent_cache: Dict[AgentType, BaseAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Register default agent implementations"""
        try:
            # Register CSV agent
            from src.agents.csv.agent import CsvAgent
            self.register_agent(AgentType.CSV, CsvAgent)

            # Register other agents as they're implemented
            # from src.agents.karate.agent import KarateAgent
            # self.register_agent(AgentType.KARATE, KarateAgent)

            # from src.agents.postman.agent import PostmanAgent
            # self.register_agent(AgentType.POSTMAN, PostmanAgent)

            self.logger.info(
                f"Registered {len(self._agent_registry)} agent types")

        except ImportError as e:
            self.logger.warning(f"Some agents not available: {e}")

    def register_agent(self, agent_type: AgentType, agent_class: Type[BaseAgent]) -> None:
        """Register an agent implementation"""
        self._agent_registry[agent_type] = agent_class
        self.logger.debug(
            f"Registered agent: {agent_type.value} -> {agent_class.__name__}")

    def create_agent(self, agent_type: AgentType, use_cache: bool = False) -> BaseAgent:
        """Create an agent instance with dependency injection"""

        # Check cache first if requested
        if use_cache and agent_type in self._agent_cache:
            return self._agent_cache[agent_type]

        # Get agent class
        if agent_type not in self._agent_registry:
            raise ValueError(f"Agent type not registered: {agent_type.value}")

        agent_class = self._agent_registry[agent_type]

        try:
            # Create instance using dependency injection container
            container = get_container()
            agent_instance = container.get(agent_class)

            # Cache if requested
            if use_cache:
                self._agent_cache[agent_type] = agent_instance

            self.logger.debug(f"Created agent: {agent_type.value}")
            return agent_instance

        except Exception as e:
            self.logger.error(
                f"Failed to create agent {agent_type.value}: {e}")
            raise

    def create_csv_agent(self, use_cache: bool = False) -> BaseAgent:
        """Create CSV agent instance"""
        return self.create_agent(AgentType.CSV, use_cache)

    def create_karate_agent(self, use_cache: bool = False) -> BaseAgent:
        """Create Karate agent instance"""
        # For now, return a mock agent until Karate agent is implemented
        return self._create_mock_agent(AgentType.KARATE)

    def create_postman_agent(self, use_cache: bool = False) -> BaseAgent:
        """Create Postman agent instance"""
        # For now, return a mock agent until Postman agent is implemented
        return self._create_mock_agent(AgentType.POSTMAN)

    def _create_mock_agent(self, agent_type: AgentType) -> BaseAgent:
        """Create a mock agent for agents not yet implemented"""
        from src.agents.base.mock_agent import MockAgent
        return MockAgent(agent_type)

    def get_available_agents(self) -> list[AgentType]:
        """Get list of available agent types"""
        return list(self._agent_registry.keys())

    def is_agent_available(self, agent_type: AgentType) -> bool:
        """Check if an agent type is available"""
        return agent_type in self._agent_registry

    def clear_cache(self) -> None:
        """Clear agent cache"""
        self._agent_cache.clear()
        self.logger.debug("Agent cache cleared")

    def get_agent_info(self, agent_type: AgentType) -> Dict[str, Any]:
        """Get information about an agent type"""
        if agent_type not in self._agent_registry:
            return {"available": False, "reason": "Not registered"}

        agent_class = self._agent_registry[agent_type]

        return {
            "available": True,
            "agent_type": agent_type.value,
            "class_name": agent_class.__name__,
            "module": agent_class.__module__,
            "cached": agent_type in self._agent_cache
        }
