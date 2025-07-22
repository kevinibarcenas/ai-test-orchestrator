"""Output validation service"""
import json
import jsonschema
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger


class ValidationService(ABC):
    """Abstract validation service interface"""

    @abstractmethod
    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        """Get schema by name"""
        pass

    @abstractmethod
    def validate(self, data: Any, schema: Dict[str, Any]) -> List[str]:
        """Validate data against schema and return validation errors"""
        pass

    @abstractmethod
    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Register a new schema"""
        pass


class JSONSchemaValidationService(ValidationService):
    """JSON Schema-based validation service"""

    def __init__(self):
        self.logger = get_logger("validation_service")
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._load_default_schemas()

    def _load_default_schemas(self) -> None:
        """Load default schemas from agent modules"""
        try:
            # Import and register CSV schema
            from src.agents.csv.schemas import CSV_TEST_CASE_SCHEMA
            self.register_schema("csv_test_case_schema", CSV_TEST_CASE_SCHEMA)

            # Import and register Postman schema
            from src.agents.postman.schemas import POSTMAN_COLLECTION_SCHEMA
            self.register_schema("postman_collection_schema",
                                 POSTMAN_COLLECTION_SCHEMA)

            # Import and register Karate schema
            from src.agents.karate.schemas import KARATE_FEATURE_SCHEMA
            self.register_schema("karate_feature_schema",
                                 KARATE_FEATURE_SCHEMA)

            # Import and register core orchestrator schemas
            from src.core.schemas import SECTION_ANALYSIS_SCHEMA
            self.register_schema("section_analysis_schema",
                                 SECTION_ANALYSIS_SCHEMA)

        except ImportError as e:
            self.logger.warning(f"Failed to load some schemas: {e}")

    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        """Get schema by name"""
        if schema_name not in self._schemas:
            raise ValueError(f"Schema not found: {schema_name}")
        return self._schemas[schema_name]

    def validate(self, data: Any, schema: Dict[str, Any]) -> List[str]:
        """Validate data against JSON schema"""
        errors = []

        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Validation error: {e.message}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")

        return errors

    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Register a new schema"""
        self._schemas[name] = schema
