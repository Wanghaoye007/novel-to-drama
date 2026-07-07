from __future__ import annotations

from contextlib import contextmanager
import json
import os
import re
import signal
import threading
from typing import Any, Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from novel_drama_engine.models import LLMUsageMetrics

T = TypeVar("T", bound=BaseModel)


class LLMResponseError(RuntimeError):
    pass


class LLMConfigurationError(LLMResponseError):
    pass


class LLMProviderLimitError(LLMResponseError):
    pass


class LLMProviderAuthError(LLMResponseError):
    pass


@contextmanager
def _hard_timeout(seconds: float):
    if (
        seconds <= 0
        or threading.current_thread() is not threading.main_thread()
        or not hasattr(signal, "SIGALRM")
    ):
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def raise_timeout(_signum, _frame):
        raise TimeoutError(f"LLM call timed out after {seconds:g}s")

    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


def _provider_error_label(exc: Exception) -> tuple[type[LLMResponseError], str] | None:
    text = str(exc)
    normalized = text.lower()
    if any(
        token in normalized
        for token in [
            "key limit exceeded",
            "daily limit",
            "insufficient_quota",
            "quota",
            "credit balance",
            "billing hard limit",
            "limit exceeded",
        ]
    ):
        return (
            LLMProviderLimitError,
            "LLM_PROVIDER_LIMIT: provider quota or key daily limit exceeded",
        )
    if any(
        token in normalized
        for token in [
            "invalid api key",
            "unauthorized",
            "401",
            "api key is not set",
            "authentication",
        ]
    ):
        return (
            LLMProviderAuthError,
            "LLM_PROVIDER_AUTH: provider API key is missing or invalid",
        )
    if "rate limit" in normalized or "too many requests" in normalized or "429" in normalized:
        return (
            LLMProviderLimitError,
            "LLM_PROVIDER_RATE_LIMIT: provider rate limit exceeded",
        )
    return None


def _wrap_provider_exception(
    *,
    prefix: str,
    response_model: type[BaseModel],
    exc: Exception,
) -> LLMResponseError:
    classified = _provider_error_label(exc)
    if classified is not None:
        error_type, label = classified
        return error_type(f"{prefix} while generating {response_model.__name__}: {label}. {exc}")
    return LLMResponseError(f"{prefix} while generating {response_model.__name__}: {exc}")


def _decode_json_object_from_text(content: str) -> dict[str, Any]:
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


MISSING_MEMBER_COMMA_RE = re.compile(
    r'(?P<value>\]|\}|"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
    r'(?P<space>\s*\n\s*)'
    r'(?P<key>"[^"\n]+":)'
)


def _repair_missing_member_commas(content: str) -> str:
    return MISSING_MEMBER_COMMA_RE.sub(r"\g<value>,\g<space>\g<key>", content)


def _load_json_object_from_text(content: str) -> dict[str, Any]:
    try:
        return _decode_json_object_from_text(content)
    except json.JSONDecodeError as original_exc:
        repaired = _repair_missing_member_commas(content)
        if repaired == content:
            raise original_exc
        try:
            return _decode_json_object_from_text(repaired)
        except json.JSONDecodeError:
            raise original_exc


def _compact_text(value: str, max_chars: int) -> str:
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    head_chars = max_chars // 2
    tail_chars = max_chars - head_chars
    return (
        value[:head_chars]
        + "\n\n...[truncated for JSON repair]...\n\n"
        + value[-tail_chars:]
    )


class JsonLLM(Protocol):
    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        pass


class StaticJsonLLM:
    def __init__(self, outputs: list[BaseModel | dict[str, Any]]) -> None:
        self._outputs = list(outputs)
        self.last_raw_response: dict[str, Any] | None = None

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        if not self._outputs:
            raise LLMResponseError("No static LLM output remains")
        raw = self._outputs.pop(0)
        raw_payload: Any = raw.model_dump(mode="json") if isinstance(raw, BaseModel) else raw
        self.last_raw_response = {
            "provider": "static",
            "response_model": response_model.__name__,
            "content": raw_payload,
        }
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
        self._call_timeout_seconds = float(
            os.environ.get(
                "NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS",
                os.environ.get("OPENAI_TIMEOUT", "300"),
            )
        )
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
            int(os.environ.get("NOVEL_DRAMA_LLM_VALIDATION_RETRIES", "2")),
        )
        self._repair_snippet_chars = max(
            1000,
            int(os.environ.get("NOVEL_DRAMA_LLM_REPAIR_SNIPPET_CHARS", "60000")),
        )
        self.last_usage: LLMUsageMetrics | None = None
        self.last_raw_response: dict[str, Any] | None = None

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
        self.last_raw_response = None
        if self._use_chat_json:
            return self._complete_with_chat_json(
                system=system,
                user=user,
                response_model=response_model,
            )

        try:
            with _hard_timeout(self._call_timeout_seconds):
                response = self._client.responses.parse(
                    model=self._model,
                    input=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    text_format=response_model,
                )
        except Exception as exc:
            raise _wrap_provider_exception(
                prefix="OpenAI request failed",
                response_model=response_model,
                exc=exc,
            ) from exc
        self._record_usage(getattr(response, "usage", None))
        response_payload: Any = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else str(response)
        )
        self.last_raw_response = {
            "provider": "responses",
            "model": self._model,
            "response_model": response_model.__name__,
            "response": response_payload,
        }
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
            "Return raw data JSON only. The response must start with { and end with }. "
            "Do not output the schema itself. Do not wrap the JSON in markdown. "
            "Do not emit multiple JSON objects, explanations, comments, or trailing prose. "
            f"The top-level keys must be: {top_level_keys}. "
            "If the task asks for a wrapper object, do not output a nested item directly. "
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
        raw_attempts: list[dict[str, Any]] = []
        for attempt in range(attempts):
            try:
                with _hard_timeout(self._call_timeout_seconds):
                    response = self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        max_tokens=self._max_tokens,
                    )
            except Exception as exc:
                self.last_raw_response = {
                    "provider": "chat.completions",
                    "model": self._model,
                    "response_model": response_model.__name__,
                    "attempts": raw_attempts,
                    "request_error": str(exc),
                }
                raise _wrap_provider_exception(
                    prefix="OpenAI-compatible request failed",
                    response_model=response_model,
                    exc=exc,
                ) from exc
            self._record_usage(getattr(response, "usage", None))

            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            content = choice.message.content
            raw_attempt: dict[str, Any] = {
                "attempt": attempt + 1,
                "finish_reason": finish_reason,
                "content": content,
            }
            usage = getattr(response, "usage", None)
            if usage is not None:
                raw_attempt["usage"] = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }
            raw_attempts.append(raw_attempt)
            self.last_raw_response = {
                "provider": "chat.completions",
                "model": self._model,
                "response_model": response_model.__name__,
                "attempts": raw_attempts,
            }
            if finish_reason == "length":
                raise LLMResponseError(
                    f"OpenAI-compatible response was truncated while generating {response_model.__name__}"
                )
            if not content:
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        f"OpenAI-compatible provider returned no content for {response_model.__name__}"
                    )
                repair_instruction = (
                    "The previous response had no content."
                )
                messages = self._repair_messages(
                    system=system,
                    user=user,
                    response_model=response_model,
                    schema=schema,
                    top_level_keys=top_level_keys,
                    issue=repair_instruction,
                    previous_response="",
                )
                continue
            try:
                parsed = _load_json_object_from_text(content)
            except json.JSONDecodeError as exc:
                raw_attempt["json_error"] = str(exc)
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        f"OpenAI-compatible provider returned invalid JSON for {response_model.__name__}: {exc}",
                    ) from exc
                messages = self._repair_messages(
                    system=system,
                    user=user,
                    response_model=response_model,
                    schema=schema,
                    top_level_keys=top_level_keys,
                    issue=f"The previous response was invalid JSON.\nJSON parse error:\n{exc}",
                    previous_response=content,
                )
                continue
            try:
                result = response_model.model_validate(parsed)
                raw_attempt["validated"] = True
                self.last_raw_response = {
                    "provider": "chat.completions",
                    "model": self._model,
                    "response_model": response_model.__name__,
                    "attempts": raw_attempts,
                    "validated_json": parsed,
                }
                return result
            except ValidationError as exc:
                raw_attempt["validation_error"] = str(exc)
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        "OpenAI-compatible provider returned JSON that failed "
                        f"schema validation for {response_model.__name__}: {exc}",
                    ) from exc
                messages = self._repair_messages(
                    system=system,
                    user=user,
                    response_model=response_model,
                    schema=schema,
                    top_level_keys=top_level_keys,
                    issue=f"The previous JSON failed validation.\nValidation error:\n{exc}",
                    previous_response=content,
                )
        raise LLMResponseError(
            f"OpenAI-compatible provider failed to generate {response_model.__name__}"
        )

    def _repair_messages(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        schema: dict[str, Any],
        top_level_keys: str,
        issue: str,
        previous_response: str,
    ) -> list[dict[str, str]]:
        original_task = _compact_text(
            f"SYSTEM PROMPT:\n{system}\n\nUSER PROMPT:\n{user}",
            self._repair_snippet_chars,
        )
        previous = _compact_text(previous_response, self._repair_snippet_chars)
        schema_text = json.dumps(schema, ensure_ascii=False)
        return [
            {
                "role": "system",
                "content": (
                    "You are a strict JSON repair worker for an automated production pipeline. "
                    "Return exactly one valid JSON object and nothing else. No markdown. "
                    "No comments. No explanations. Do not output the JSON Schema itself. "
                    "The object must validate against the requested schema. "
                    "If the previous response is the wrong nesting level, rebuild or wrap it "
                    "into the requested top-level object. If required fields are missing, infer "
                    "the smallest faithful value from the original task and previous response."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Requested model: {response_model.__name__}\n"
                    f"Required top-level keys: {top_level_keys}\n\n"
                    f"JSON Schema:\n{schema_text}\n\n"
                    f"Original generation task excerpt:\n{original_task}\n\n"
                    f"Repair issue:\n{issue}\n\n"
                    f"Previous response:\n{previous}\n\n"
                    "Return only the corrected JSON object."
                ),
            },
        ]
