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
