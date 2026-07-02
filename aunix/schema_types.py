"""Pydantic types tuned for OpenAI structured-output JSON Schema.

OpenAI requires object schemas to set additionalProperties=false, so free-form
dict fields are represented as JSON strings in the LLM schema and coerced back to
dicts at validation time.
"""
from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import BeforeValidator, WithJsonSchema


def _coerce_json_object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("JSON value must be an object")
        return parsed
    raise TypeError(f"expected dict or JSON string, got {type(value).__name__}")


def _coerce_json_string_map(value: Any) -> dict[str, str]:
    raw = _coerce_json_object(value)
    return {str(key): str(val) for key, val in raw.items()}


JsonObjectField = Annotated[
    dict[str, Any],
    BeforeValidator(_coerce_json_object),
    WithJsonSchema(
        {
            "type": "string",
            "description": (
                'JSON object string, e.g. {"limit": 100} or '
                '{"note": "{{finding.summary}}"}'
            ),
        }
    ),
]

JsonStringMapField = Annotated[
    dict[str, str],
    BeforeValidator(_coerce_json_string_map),
    WithJsonSchema(
        {
            "type": "string",
            "description": (
                'JSON object string mapping row field to response path, '
                'e.g. {"deal_id": "id"}'
            ),
        }
    ),
]
