from __future__ import annotations

import os
from typing import Any, Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMResponseError(RuntimeError):
    pass


class JsonLLM(Protocol):
    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        pass


class StaticJsonLLM:
    def __init__(self, outputs: list[BaseModel | dict[str, Any]]) -> None:
        self._outputs = list(outputs)

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        if not self._outputs:
            raise LLMResponseError("No static LLM output remains")
        raw = self._outputs.pop(0)
        if isinstance(raw, response_model):
            return raw
        return response_model.model_validate(raw)


class OpenAIJsonLLM:
    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        self._client = client or OpenAI()
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-5.5")

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        response = self._client.responses.parse(
            model=self._model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=response_model,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise LLMResponseError(
                f"OpenAI returned no parsed output for {response_model.__name__}"
            )
        if not isinstance(parsed, response_model):
            return response_model.model_validate(parsed)
        return parsed
