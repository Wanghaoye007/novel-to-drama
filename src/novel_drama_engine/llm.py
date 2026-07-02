from __future__ import annotations

import json
import os
from typing import Any, Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from novel_drama_engine.models import LLMUsageMetrics

T = TypeVar("T", bound=BaseModel)


class LLMResponseError(RuntimeError):
    pass


class LLMConfigurationError(LLMResponseError):
    pass


def _load_json_object_from_text(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as original_exc:
        decoder = json.JSONDecoder()
        for start, char in enumerate(content):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(content[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise original_exc
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("Expected a JSON object", content, 0)
    return parsed


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
        api_key = os.environ.get("OPENAI_API_KEY")
        if client is None and not api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not set. Use --mock for a local demo run or set OPENAI_API_KEY.",
            )
        base_url = os.environ.get("OPENAI_BASE_URL")
        provider = os.environ.get("NOVEL_DRAMA_LLM_PROVIDER", "").lower()
        timeout = float(os.environ.get("OPENAI_TIMEOUT", "300"))
        self._use_chat_json = bool(base_url) or provider in {
            "kimi",
            "moonshot",
            "openai_compatible",
        }
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=timeout,
        )
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-5.5")
        self._max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", "65536"))
        self._chat_validation_retries = max(
            0,
            int(os.environ.get("NOVEL_DRAMA_LLM_VALIDATION_RETRIES", "1")),
        )
        self.last_usage: LLMUsageMetrics | None = None

    def _record_usage(self, usage: Any) -> None:
        if usage is None:
            self.last_usage = None
            return
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        self.last_usage = LLMUsageMetrics(
            prompt_tokens=prompt_tokens if prompt_tokens is not None else input_tokens,
            completion_tokens=(
                completion_tokens
                if completion_tokens is not None
                else output_tokens
            ),
            total_tokens=total_tokens,
        )

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        self.last_usage = None
        if self._use_chat_json:
            return self._complete_with_chat_json(
                system=system,
                user=user,
                response_model=response_model,
            )

        try:
            response = self._client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                text_format=response_model,
            )
        except Exception as exc:
            raise LLMResponseError(
                f"OpenAI request failed while generating {response_model.__name__}: {exc}",
            ) from exc
        self._record_usage(getattr(response, "usage", None))
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise LLMResponseError(
                f"OpenAI returned no parsed output for {response_model.__name__}"
            )
        if not isinstance(parsed, response_model):
            return response_model.model_validate(parsed)
        return parsed

    def _complete_with_chat_json(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        schema = response_model.model_json_schema()
        top_level_keys = ", ".join(schema.get("properties", {}).keys())
        format_instruction = (
            f"Generate one JSON object instance for {response_model.__name__}. "
            "Do not output the schema itself. Do not wrap the JSON in markdown. "
            f"The top-level keys must be: {top_level_keys}. "
            "Do not include schema-only keys such as properties, required, $defs, type, or title "
            "unless they are explicitly part of the requested data. "
            "Use this JSON Schema only as a validation reference:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        base_messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": format_instruction},
            {"role": "user", "content": user},
        ]
        messages = list(base_messages)
        attempts = self._chat_validation_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=self._max_tokens,
                )
            except Exception as exc:
                raise LLMResponseError(
                    f"OpenAI-compatible request failed while generating {response_model.__name__}: {exc}",
                ) from exc
            self._record_usage(getattr(response, "usage", None))

            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                raise LLMResponseError(
                    f"OpenAI-compatible response was truncated while generating {response_model.__name__}"
                )
            content = choice.message.content
            if not content:
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        f"OpenAI-compatible provider returned no content for {response_model.__name__}"
                    )
                repair_instruction = (
                    "The previous response had no content. Return the complete "
                    f"JSON object for {response_model.__name__} only, with the same "
                    "top-level keys and no markdown."
                )
                messages = [
                    *base_messages,
                    {"role": "user", "content": repair_instruction},
                ]
                continue
            try:
                parsed = _load_json_object_from_text(content)
            except json.JSONDecodeError as exc:
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        f"OpenAI-compatible provider returned invalid JSON for {response_model.__name__}: {exc}",
                    ) from exc
                repair_instruction = (
                    "The previous response was invalid JSON. Return the complete corrected "
                    f"JSON object for {response_model.__name__} only, with the same "
                    "top-level keys and no markdown.\n"
                    f"JSON parse error:\n{exc}\n"
                    f"Previous response:\n{content}"
                )
                messages = [
                    *base_messages,
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": repair_instruction},
                ]
                continue
            try:
                return response_model.model_validate(parsed)
            except ValidationError as exc:
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        "OpenAI-compatible provider returned JSON that failed "
                        f"schema validation for {response_model.__name__}: {exc}",
                    ) from exc
                repair_instruction = (
                    "The previous JSON failed validation. Return the complete corrected "
                    f"JSON object for {response_model.__name__} only, with the same "
                    "top-level keys and no markdown.\n"
                    f"Validation error:\n{exc}\n"
                    f"Previous JSON:\n{content}"
                )
                messages = [
                    *base_messages,
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": repair_instruction},
                ]
        raise LLMResponseError(
            f"OpenAI-compatible provider failed to generate {response_model.__name__}"
        )
