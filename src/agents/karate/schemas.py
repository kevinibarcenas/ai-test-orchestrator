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
