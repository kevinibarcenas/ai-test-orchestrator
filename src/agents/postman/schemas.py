# src/agents/postman/schemas.py
"""Postman Collection Generation Schemas"""

POSTMAN_COLLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "collection": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Collection name based on API section"
                },
                "description": {
                    "type": "string",
                    "description": "Comprehensive description of the collection's purpose and capabilities"
                },
                "version": {
                    "type": "string",
                    "description": "API version (e.g., '1.0.0')"
                },
                "variable": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                            "description": {"type": "string"},
                            "type": {"type": "string"}
                        },
                        "required": ["key", "value", "description", "type"],
                        "additionalProperties": False
                    },
                    "description": "Collection-level variables (api_version, timeout, etc.)"
                },
                "auth": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["bearer", "apikey", "basic", "oauth2", "none"],
                            "description": "Primary authentication method"
                        },
                        "bearer": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                    "type": {"type": "string"}
                                },
                                "required": ["key", "value", "type"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["type", "bearer"],
                    "additionalProperties": False,
                    "description": "Collection-level authentication configuration"
                },
                "event": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "listen": {
                                "type": "string",
                                "enum": ["prerequest", "test"],
                                "description": "Event type"
                            },
                            "script": {
                                "type": "object",
                                "properties": {
                                    "exec": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "JavaScript code lines"
                                    },
                                    "type": {"type": "string"}
                                },
                                "required": ["exec", "type"],
                                "additionalProperties": False
                            }
                        },
                        "required": ["listen", "script"],
                        "additionalProperties": False
                    },
                    "description": "Collection-level pre-request and test scripts"
                },
                "item": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Folder or request name"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the folder/request purpose"
                            },
                            "item": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "request": {
                                            "type": "object",
                                            "properties": {
                                                "method": {
                                                    "type": "string",
                                                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                                                },
                                                "header": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "key": {"type": "string"},
                                                            "value": {"type": "string"},
                                                            "description": {"type": "string"},
                                                            "disabled": {"type": "boolean"}
                                                        },
                                                        "required": ["key", "value", "description", "disabled"],
                                                        "additionalProperties": False
                                                    }
                                                },
                                                "url": {
                                                    "type": "object",
                                                    "properties": {
                                                        "raw": {"type": "string"},
                                                        "host": {
                                                            "type": "array",
                                                            "items": {"type": "string"}
                                                        },
                                                        "path": {
                                                            "type": "array",
                                                            "items": {"type": "string"}
                                                        },
                                                        "query": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "key": {"type": "string"},
                                                                    "value": {"type": "string"},
                                                                    "description": {"type": "string"},
                                                                    "disabled": {"type": "boolean"}
                                                                },
                                                                "required": ["key", "value", "description", "disabled"],
                                                                "additionalProperties": False
                                                            }
                                                        },
                                                        "variable": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "key": {"type": "string"},
                                                                    "value": {"type": "string"},
                                                                    "description": {"type": "string"}
                                                                },
                                                                "required": ["key", "value", "description"],
                                                                "additionalProperties": False
                                                            }
                                                        }
                                                    },
                                                    "required": ["raw", "host", "path", "query", "variable"],
                                                    "additionalProperties": False
                                                },
                                                "body": {
                                                    "type": "object",
                                                    "properties": {
                                                        "mode": {
                                                            "type": "string",
                                                            "enum": ["raw", "formdata", "urlencoded", "file", "graphql", "none"]
                                                        },
                                                        "raw": {"type": "string"},
                                                        "options": {
                                                            "type": "object",
                                                            "properties": {
                                                                "raw": {
                                                                    "type": "object",
                                                                    "properties": {
                                                                        "language": {
                                                                            "type": "string",
                                                                            "enum": ["json", "xml", "html", "text", "javascript"]
                                                                        }
                                                                    },
                                                                    "required": ["language"],
                                                                    "additionalProperties": False
                                                                }
                                                            },
                                                            "required": ["raw"],
                                                            "additionalProperties": False
                                                        }
                                                    },
                                                    "required": ["mode", "raw", "options"],
                                                    "additionalProperties": False
                                                },
                                                "description": {"type": "string"}
                                            },
                                            "required": ["method", "header", "url", "body", "description"],
                                            "additionalProperties": False
                                        },
                                        "response": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "status": {"type": "string"},
                                                    "code": {"type": "integer"},
                                                    "header": {
                                                        "type": "array",
                                                        "items": {"type": "string"}
                                                    },
                                                    "body": {"type": "string"}
                                                },
                                                "required": ["name", "status", "code", "header", "body"],
                                                "additionalProperties": False
                                            },
                                            "description": "Sample responses for documentation"
                                        },
                                        "event": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "listen": {
                                                        "type": "string",
                                                        "enum": ["prerequest", "test"]
                                                    },
                                                    "script": {
                                                        "type": "object",
                                                        "properties": {
                                                            "exec": {
                                                                "type": "array",
                                                                "items": {"type": "string"}
                                                            },
                                                            "type": {"type": "string"}
                                                        },
                                                        "required": ["exec", "type"],
                                                        "additionalProperties": False
                                                    }
                                                },
                                                "required": ["listen", "script"],
                                                "additionalProperties": False
                                            },
                                            "description": "Request-level pre-request and test scripts"
                                        }
                                    },
                                    "required": ["name", "description", "request", "response", "event"],
                                    "additionalProperties": False
                                },
                                "description": "Individual requests within this folder"
                            }
                        },
                        "required": ["name", "description", "item"],
                        "additionalProperties": False
                    },
                    "description": "Collection folders and requests"
                }
            },
            "required": ["name", "description", "version", "variable", "auth", "event", "item"],
            "additionalProperties": False
        },
        "environments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Environment name (development, staging, production)"
                    },
                    "values": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "value": {"type": "string"},
                                "description": {"type": "string"},
                                "enabled": {"type": "boolean"}
                            },
                            "required": ["key", "value", "description", "enabled"],
                            "additionalProperties": False
                        },
                        "description": "Environment variable definitions"
                    }
                },
                "required": ["name", "values"],
                "additionalProperties": False
            },
            "description": "Environment configurations for different deployment stages"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "collection_summary": {
                    "type": "string",
                    "description": "Executive summary of the collection's capabilities and coverage"
                },
                "total_requests": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Total number of requests in the collection"
                },
                "folder_structure": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of folder names for organization"
                },
                "auth_methods": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["bearer", "apikey", "basic", "oauth2", "none"]
                    },
                    "description": "Authentication methods used in the collection"
                },
                "environment_variables": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of environment variable names"
                },
                "test_coverage": {
                    "type": "object",
                    "properties": {
                        "endpoints_covered": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Number of endpoints with test requests"
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
                        "test_scenarios": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["happy_path", "validation", "authentication", "authorization", "error_handling", "edge_cases"]
                            },
                            "description": "Types of test scenarios included"
                        }
                    },
                    "required": ["endpoints_covered", "total_endpoints", "coverage_percentage", "test_scenarios"],
                    "additionalProperties": False,
                    "description": "Analysis of test coverage provided by the collection"
                },
                "advanced_features": {
                    "type": "object",
                    "properties": {
                        "has_pre_request_scripts": {"type": "boolean"},
                        "has_test_scripts": {"type": "boolean"},
                        "has_dynamic_variables": {"type": "boolean"},
                        "has_request_chaining": {"type": "boolean"},
                        "has_error_handling": {"type": "boolean"},
                        "newman_compatible": {"type": "boolean"}
                    },
                    "required": ["has_pre_request_scripts", "has_test_scripts", "has_dynamic_variables", "has_request_chaining", "has_error_handling", "newman_compatible"],
                    "additionalProperties": False,
                    "description": "Advanced features implemented in the collection"
                }
            },
            "required": ["collection_summary", "total_requests", "folder_structure", "auth_methods", "environment_variables", "test_coverage", "advanced_features"],
            "additionalProperties": False
        }
    },
    "required": ["collection", "environments", "metadata"],
    "additionalProperties": False
}
