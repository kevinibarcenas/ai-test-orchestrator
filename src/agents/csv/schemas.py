"""CSV agent specific schemas"""

# Main schema for CSV test case generation
CSV_TEST_CASE_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "description": "Array of comprehensive test cases for QMetry import",
            "items": {
                "type": "object",
                "properties": {
                    "test_case_id": {
                        "type": "string",
                        "description": "Unique test case identifier following pattern TC_[SECTION]_[NUMBER]"
                    },
                    "test_case_name": {
                        "type": "string",
                        "description": "Clear, descriptive test case name following pattern: Verify [action] [condition] [expected outcome]"
                    },
                    "test_case_description": {
                        "type": "string",
                        "description": "Detailed description of what is being tested and why"
                    },
                    "module": {
                        "type": "string",
                        "description": "Module or functional area being tested (e.g., User Management, Authentication)"
                    },
                    "test_type": {
                        "type": "string",
                        "enum": ["Functional", "Integration", "Negative", "Security", "Performance", "Boundary"],
                        "description": "Type of test case based on testing approach"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                        "description": "Test case priority based on business criticality"
                    },
                    "estimated_time": {
                        "type": "string",
                        "description": "Estimated execution time in minutes (e.g., '10', '15')"
                    },
                    "preconditions": {
                        "type": "string",
                        "description": "Prerequisites that must be met before test execution"
                    },
                    "test_steps": {
                        "type": "string",
                        "description": "Numbered, actionable test steps that any tester can follow"
                    },
                    "expected_results": {
                        "type": "string",
                        "description": "Specific expected outcomes including status codes, response structure, and validation points"
                    },
                    "test_data": {
                        "type": "string",
                        "description": "Sample test data, request examples, and input variations"
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags for test categorization and filtering"
                    }
                },
                "required": [
                    "test_case_id",
                    "test_case_name",
                    "test_case_description",
                    "module",
                    "test_type",
                    "priority",
                    "test_steps",
                    "expected_results"
                ],
                "additionalProperties": False
            }
        },
        "metadata": {
            "type": "object",
            "properties": {
                "coverage_summary": {
                    "type": "string",
                    "description": "Summary of test coverage provided by these test cases"
                },
                "total_test_cases": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Total number of test cases generated"
                },
                "csv_headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CSV column headers to use for export"
                },
                "test_distribution": {
                    "type": "object",
                    "properties": {
                        "functional": {"type": "integer", "minimum": 0},
                        "integration": {"type": "integer", "minimum": 0},
                        "negative": {"type": "integer", "minimum": 0},
                        "security": {"type": "integer", "minimum": 0},
                        "performance": {"type": "integer", "minimum": 0},
                        "boundary": {"type": "integer", "minimum": 0}
                    },
                    "description": "Distribution of test cases by type"
                },
                "coverage_analysis": {
                    "type": "object",
                    "properties": {
                        "endpoints_covered": {"type": "integer", "minimum": 0},
                        "total_endpoints": {"type": "integer", "minimum": 0},
                        "coverage_percentage": {"type": "number", "minimum": 0, "maximum": 100},
                        "uncovered_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Areas that may need additional test coverage"
                        }
                    },
                    "description": "Analysis of test coverage provided"
                },
                "quality_metrics": {
                    "type": "object",
                    "properties": {
                        "avg_steps_per_test": {"type": "number", "minimum": 1},
                        "detailed_test_data_count": {"type": "integer", "minimum": 0},
                        "validation_points_count": {"type": "integer", "minimum": 0}
                    },
                    "description": "Quality metrics for generated test cases"
                }
            },
            "required": ["coverage_summary", "total_test_cases"],
            "additionalProperties": False
        }
    },
    "required": ["test_cases", "metadata"],
    "additionalProperties": False
}

# Schema for CSV validation
CSV_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid": {
            "type": "boolean",
            "description": "Whether the CSV file passes validation"
        },
        "row_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of data rows in CSV"
        },
        "header_validation": {
            "type": "object",
            "properties": {
                "required_headers_present": {"type": "boolean"},
                "missing_headers": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "extra_headers": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["required_headers_present"],
            "additionalProperties": False
        },
        "content_validation": {
            "type": "object",
            "properties": {
                "empty_required_fields": {"type": "integer", "minimum": 0},
                "malformed_test_steps": {"type": "integer", "minimum": 0},
                "missing_test_data": {"type": "integer", "minimum": 0}
            },
            "additionalProperties": False
        },
        "errors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Validation error messages"
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Validation warning messages"
        }
    },
    "required": ["is_valid", "row_count"],
    "additionalProperties": False
}
