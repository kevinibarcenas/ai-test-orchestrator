# src/agents/karate/schemas.py
"""Karate Feature Generation Schemas"""

KARATE_FEATURE_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_file": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Feature file name following convention: section-name.feature"
                },
                "feature_title": {
                    "type": "string",
                    "description": "Clear, descriptive feature title following pattern: [Section Name] API Tests"
                },
                "feature_description": {
                    "type": "string",
                    "description": "Comprehensive description explaining the scope and purpose of this feature"
                },
                "background": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Common setup steps executed before each scenario using Karate DSL syntax"
                },
                "scenarios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Clear scenario name describing the test case"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of what this scenario validates"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Karate tags for scenario categorization (@smoke, @regression, @api, etc.)"
                            },
                            "scenario_type": {
                                "type": "string",
                                "enum": ["scenario", "scenario_outline"],
                                "description": "Type of scenario - use scenario_outline for data-driven tests"
                            },
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Karate DSL steps using Given/When/Then/And syntax with proper formatting"
                            },
                            "examples": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Examples table rows as proper Gherkin format - MUST use | table | format | only - NO placeholder text. Empty array for regular scenarios. For Scenario Outline: ['| param1 | param2 |', '| value1 | value2 |']"
                            }
                        },
                        "required": ["name", "description", "tags", "scenario_type", "steps", "examples"],
                        "additionalProperties": False
                    },
                    "description": "Array of test scenarios covering different aspects of the API"
                }
            },
            "required": ["filename", "feature_title", "feature_description", "background", "scenarios"],
            "additionalProperties": False
        },
        "data_files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Data file name with appropriate extension (.json, .csv, .yaml)"
                    },
                    "file_type": {
                        "type": "string",
                        "enum": ["json", "csv", "yaml"],
                        "description": "File format type"
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Purpose of this data file (test_data, validation_rules, config, etc.)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Actual data content as JSON string for any file type"
                    },
                    "usage_description": {
                        "type": "string",
                        "description": "How this data file is used in the feature scenarios"
                    }
                },
                "required": ["filename", "file_type", "purpose", "content", "usage_description"],
                "additionalProperties": False
            },
            "description": "Supporting data files for data-driven testing"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "feature_summary": {
                    "type": "string",
                    "description": "Executive summary of the feature's testing capabilities and coverage"
                },
                "total_scenarios": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Total number of scenarios in the feature file"
                },
                "data_driven_count": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of scenarios using Scenario Outline for data-driven testing"
                },
                "background_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of background steps for reference"
                },
                "variables_used": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Variables and configuration parameters used in the feature as strings"
                },
                "test_coverage": {
                    "type": "object",
                    "properties": {
                        "endpoints_covered": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Number of API endpoints covered by test scenarios"
                        },
                        "total_endpoints": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Total number of endpoints in the API section"
                        },
                        "coverage_percentage": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Percentage of endpoints covered by tests"
                        },
                        "test_types_summary": {
                            "type": "string",
                            "description": "Summary of test types covered (e.g., 'happy_path, validation, error_handling')"
                        },
                        "http_methods_summary": {
                            "type": "string",
                            "description": "Summary of HTTP methods covered (e.g., 'GET, POST, PUT, DELETE')"
                        }
                    },
                    "required": ["endpoints_covered", "total_endpoints", "coverage_percentage", "test_types_summary", "http_methods_summary"],
                    "additionalProperties": False,
                    "description": "Analysis of test coverage provided by the feature"
                },
                "framework_features_used": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["scenario_outline", "background", "data_tables", "doc_strings", "json_path", "schema_validation", "conditional_logic", "loops", "function_calls", "file_reading", "database_access", "parallel_execution"]
                    },
                    "description": "Karate framework features utilized in this feature file"
                },
                "execution_requirements": {
                    "type": "object",
                    "properties": {
                        "karate_version": {
                            "type": "string",
                            "description": "Minimum Karate framework version required"
                        },
                        "java_version": {
                            "type": "string",
                            "description": "Minimum Java version required"
                        },
                        "dependencies_summary": {
                            "type": "string",
                            "description": "Summary of additional dependencies required"
                        },
                        "configuration_summary": {
                            "type": "string",
                            "description": "Summary of required configuration files"
                        },
                        "environment_summary": {
                            "type": "string",
                            "description": "Summary of required environment variables"
                        }
                    },
                    "required": ["karate_version", "java_version", "dependencies_summary", "configuration_summary", "environment_summary"],
                    "additionalProperties": False,
                    "description": "Technical requirements for executing the feature file"
                },
                "validation_rules": {
                    "type": "object",
                    "properties": {
                        "response_time_fast": {
                            "type": "integer",
                            "description": "Fast operations threshold in ms"
                        },
                        "response_time_standard": {
                            "type": "integer",
                            "description": "Standard operations threshold in ms"
                        },
                        "response_time_complex": {
                            "type": "integer",
                            "description": "Complex operations threshold in ms"
                        },
                        "expected_status_codes": {
                            "type": "string",
                            "description": "Expected status codes as comma-separated string"
                        },
                        "mandatory_headers": {
                            "type": "string",
                            "description": "Mandatory headers as comma-separated string"
                        },
                        "schema_validation_enabled": {
                            "type": "boolean",
                            "description": "Whether schema validation is enabled"
                        }
                    },
                    "required": ["response_time_fast", "response_time_standard", "response_time_complex", "expected_status_codes", "mandatory_headers", "schema_validation_enabled"],
                    "additionalProperties": False,
                    "description": "Validation rules and thresholds used in test assertions"
                },
                "documentation_sections": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Documentation sections to include as simple string list"
                }
            },
            "required": ["feature_summary", "total_scenarios", "data_driven_count", "background_steps", "variables_used", "test_coverage", "framework_features_used", "execution_requirements", "validation_rules", "documentation_sections"],
            "additionalProperties": False
        }
    },
    "required": ["feature_file", "data_files", "metadata"],
    "additionalProperties": False
}
