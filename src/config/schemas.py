"""JSON schemas for OpenAI structured outputs"""

# Schema for test case generation
TEST_CASE_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "test_type": {
                        "type": "string",
                        "enum": ["happy_path", "edge_case", "error_case", "security", "performance"]
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"]
                    },
                    "endpoint_path": {"type": "string"},
                    "http_method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
                    },
                    "test_data": {"type": "object"},
                    "expected_result": {"type": "object"},
                    "assertions": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "preconditions": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["id", "name", "description", "test_type", "endpoint_path", "http_method"],
                "additionalProperties": False
            }
        },
        "section_summary": {"type": "string"},
        "coverage_analysis": {"type": "string"}
    },
    "required": ["test_cases", "section_summary"],
    "additionalProperties": False
}

# Schema for Karate feature generation
KARATE_FEATURE_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_file": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "feature_title": {"type": "string"},
                "feature_description": {"type": "string"},
                "background": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "scenarios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["name", "steps"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["filename", "feature_title", "scenarios"],
            "additionalProperties": False
        },
        "data_files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "object"}
                },
                "required": ["filename", "content"],
                "additionalProperties": False
            }
        }
    },
    "required": ["feature_file"],
    "additionalProperties": False
}

# Schema for Postman collection generation
POSTMAN_COLLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "collection": {
            "type": "object",
            "properties": {
                "info": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "schema": {"type": "string"}
                    },
                    "required": ["name"],
                    "additionalProperties": False
                },
                "item": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "request": {
                                "type": "object",
                                "properties": {
                                    "method": {"type": "string"},
                                    "header": {"type": "array"},
                                    "url": {"type": "object"},
                                    "body": {"type": "object"}
                                },
                                "required": ["method", "url"],
                                "additionalProperties": False
                            },
                            "event": {"type": "array"}
                        },
                        "required": ["name", "request"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["info", "item"],
            "additionalProperties": False
        },
        "environment": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "values": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                            "enabled": {"type": "boolean"}
                        },
                        "required": ["key", "value"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["name", "values"],
            "additionalProperties": False
        }
    },
    "required": ["collection"],
    "additionalProperties": False
}

# Schema for CSV/QMetry test case generation
CSV_TEST_CASE_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "test_case_id": {"type": "string"},
                    "test_case_name": {"type": "string"},
                    "test_case_description": {"type": "string"},
                    "module": {"type": "string"},
                    "test_type": {"type": "string"},
                    "priority": {"type": "string"},
                    "estimated_time": {"type": "string"},
                    "preconditions": {"type": "string"},
                    "test_steps": {"type": "string"},
                    "expected_results": {"type": "string"},
                    "test_data": {"type": "string"},
                    "tags": {"type": "string"}
                },
                "required": [
                    "test_case_id",
                    "test_case_name",
                    "test_case_description",
                    "test_steps",
                    "expected_results"
                ],
                "additionalProperties": False
            }
        },
        "metadata": {
            "type": "object",
            "properties": {
                "total_test_cases": {"type": "integer"},
                "coverage_summary": {"type": "string"},
                "csv_headers": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["total_test_cases", "csv_headers"],
            "additionalProperties": False
        }
    },
    "required": ["test_cases", "metadata"],
    "additionalProperties": False
}
