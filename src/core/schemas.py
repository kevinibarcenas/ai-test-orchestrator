"""Core schemas for orchestrator operations"""

# Section Analysis Schema - used by SectionAnalyzer
SECTION_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "strategy_used": {
            "type": "string",
            "enum": ["by_tag", "by_path", "by_method", "by_complexity", "manual", "auto"],
            "description": "The sectioning strategy that was applied"
        },
        "total_sections": {
            "type": "integer",
            "minimum": 1,
            "description": "Total number of sections created"
        },
        "estimated_total_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Estimated total tokens needed for all sections"
        },
        "analysis_reasoning": {
            "type": "string",
            "description": "Explanation of why this sectioning strategy was chosen"
        },
        "sections_summary": {
            "type": "array",
            "description": "Summary of each section created",
            "items": {
                "type": "object",
                "properties": {
                    "section_id": {
                        "type": "string",
                        "description": "Unique identifier for the section"
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable section name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what this section covers"
                    },
                    "endpoints": {
                        "type": "array",
                        "description": "API endpoints in this section",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "method": {"type": "string"},
                                "summary": {"type": "string"},
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["path", "method"],
                            "additionalProperties": False
                        }
                    },
                    "test_cases": {
                        "type": "array",
                        "description": "Recommended test cases for this section",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "test_type": {
                                    "type": "string",
                                    "enum": ["functional", "integration", "negative", "security", "performance", "boundary"]
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"]
                                },
                                "description": {"type": "string"}
                            },
                            "required": ["name", "test_type"],
                            "additionalProperties": False
                        }
                    },
                    "estimated_tokens": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Estimated tokens needed to process this section"
                    },
                    "complexity_score": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Complexity score from 1-10 for this section"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Processing priority for this section"
                    }
                },
                "required": ["section_id", "name", "description", "endpoints", "test_cases", "estimated_tokens"],
                "additionalProperties": False
            }
        }
    },
    "required": ["strategy_used", "total_sections", "estimated_total_tokens", "analysis_reasoning", "sections_summary"],
    "additionalProperties": False
}
