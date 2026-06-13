from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.model_gateway.errors import StructuredOutputError

T = TypeVar("T", bound=BaseModel)


def parse_structured_json(text: str, schema: type[T]) -> T:
    try:
        data = json.loads(text)
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise StructuredOutputError(str(exc)) from exc
