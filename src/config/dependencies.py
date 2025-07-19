"""Updated dependency injection container with all refactored services"""
from typing import Any, Callable, Dict, Optional, TypeVar, Type
from abc import ABC, abstractmethod
import inspect
from functools import wraps

T = TypeVar('T')


class ServiceContainer:
    """Dependency injection container for the application"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._transient: Dict[str, Type] = {}

    def register_singleton(self, interface: Type[T], implementation: T) -> None:
        """Register a singleton service instance"""
        key = self._get_service_key(interface)
        self._singletons[key] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory function for creating service instances"""
        key = self._get_service_key(interface)
        self._factories[key] = factory

    def register_transient(self, interface: Type[T], implementation_class: Type[T]) -> None:
        """Register a transient service (new instance each time)"""
        key = self._get_service_key(interface)
        self._transient[key] = implementation_class

    def register_implementation(self, interface: Type[T], implementation_class: Type[T]) -> None:
        """Register an implementation class for an interface"""
        interface_key = self._get_service_key(interface)
        impl_key = self._get_service_key(implementation_class)
        self._transient[interface_key] = implementation_class
        self._transient[impl_key] = implementation_class

    def get(self, interface: Type[T]) -> T:
        """Resolve a service dependency"""
        key = self._get_service_key(interface)

        # Check singletons first
        if key in self._singletons:
            return self._singletons[key]

        # Check factories
        if key in self._factories:
            return self._factories[key]()

        # Check transient services
        if key in self._transient:
            return self._create_instance(self._transient[key])

        # Try to create directly if it's a concrete class
        if inspect.isclass(interface) and not inspect.isabstract(interface):
            return self._create_instance(interface)

        raise ValueError(f"Service not registered: {interface}")

    def _get_service_key(self, interface: Type) -> str:
        """Get unique key for service interface"""
        return f"{interface.__module__}.{interface.__qualname__}"

    def _create_instance(self, implementation_class: Type[T]) -> T:
        """Create instance with dependency injection"""
        # Get constructor signature
        sig = inspect.signature(implementation_class.__init__)
        args = {}

        # Resolve dependencies
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                try:
                    args[param_name] = self.get(param.annotation)
                except ValueError:
                    # If dependency not found, try to use default value
                    if param.default != inspect.Parameter.empty:
                        args[param_name] = param.default
                    else:
                        # Skip optional dependencies
                        continue

        return implementation_class(**args)


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get global service container"""
    global _container
    if _container is None:
        _container = ServiceContainer()
        _setup_services()
    return _container


def inject(func: Callable) -> Callable:
    """Decorator for automatic dependency injection"""
    sig = inspect.signature(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        container = get_container()

        # Resolve dependencies for missing arguments
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = container.get(param.annotation)
                except ValueError:
                    # Dependency not found, continue without injection
                    pass

        return func(*args, **kwargs)

    return wrapper


def _setup_services():
    """Setup all service registrations"""
    container = get_container()

    # Register core configuration
    _register_core_services(container)

    # Register business services
    _register_business_services(container)

    # Register agent services
    _register_agent_services(container)


def _register_core_services(container: ServiceContainer):
    """Register core application services"""
    from src.config.settings import get_settings, Settings
    from src.utils.logger import get_logger

    # Settings (singleton)
    settings = get_settings()
    container.register_singleton(Settings, settings)

    # Logger factory
    container.register_factory(type(get_logger()), lambda: get_logger())


def _register_business_services(container: ServiceContainer):
    """Register business logic services"""

    # LLM Service
    from src.services.llm_service import LLMService, OpenAILLMService
    container.register_implementation(LLMService, OpenAILLMService)

    # Validation Service
    from src.services.validation_service import ValidationService, JSONSchemaValidationService
    container.register_implementation(
        ValidationService, JSONSchemaValidationService)

    # Export Service
    from src.services.export_service import ExportService, FileExportService
    container.register_implementation(ExportService, FileExportService)

    # Prompt Manager (singleton)
    from src.prompts.manager import get_prompt_manager, PromptManager
    prompt_manager = get_prompt_manager()
    container.register_singleton(PromptManager, prompt_manager)

    # Core services
    from src.core.file_manager import FileManager
    from src.core.section_analyzer import SectionAnalyzer
    from src.core.result_compiler import ResultCompiler
    from src.core.agent_factory import AgentFactory
    from src.core.orchestrator import TestOrchestrator

    container.register_transient(FileManager, FileManager)
    container.register_transient(SectionAnalyzer, SectionAnalyzer)
    container.register_transient(ResultCompiler, ResultCompiler)
    container.register_transient(AgentFactory, AgentFactory)
    container.register_transient(TestOrchestrator, TestOrchestrator)


def _register_agent_services(container: ServiceContainer):
    """Register agent-specific services"""

    # CSV Agent and Processor
    from src.agents.csv.agent import CsvAgent
    from src.agents.csv.processors import CSVProcessor

    container.register_transient(CSVProcessor, CSVProcessor)
    container.register_transient(CsvAgent, CsvAgent)

    # Register other agents as they're implemented
    # from src.agents.karate.agent import KarateAgent
    # container.register_transient(KarateAgent, KarateAgent)

    # from src.agents.postman.agent import PostmanAgent
    # container.register_transient(PostmanAgent, PostmanAgent)


def clear_container():
    """Clear the global container (useful for testing)"""
    global _container
    _container = None


def override_service(interface: Type[T], implementation: T):
    """Override a service registration (useful for testing)"""
    container = get_container()
    container.register_singleton(interface, implementation)
