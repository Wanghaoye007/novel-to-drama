import time

from pydantic import BaseModel, Field

from novel_drama_engine.llm import (
    LLMConfigurationError,
    LLMProviderLimitError,
    LLMResponseError,
    OpenAIJsonLLM,
    StaticJsonLLM,
)
from novel_drama_engine.models import SourceAnalysis


class TinyModel(BaseModel):
    value: str


class TinyListModel(BaseModel):
    items: list[str] = Field(min_length=2)


class TinyBibleModel(BaseModel):
    facts: list[str]
    forbidden_changes: list[str]


def test_static_llm_returns_validated_model_from_dict():
    llm = StaticJsonLLM([{"value": "ok"}])

    result = llm.complete(system="system", user="user", response_model=TinyModel)

    assert result.value == "ok"


def test_static_llm_raises_when_queue_is_empty():
    llm = StaticJsonLLM([])

    try:
        llm.complete(system="system", user="user", response_model=TinyModel)
    except LLMResponseError as exc:
        assert "No static LLM output remains" in str(exc)
    else:
        raise AssertionError("expected LLMResponseError")


def test_openai_adapter_uses_responses_parse(monkeypatch):
    captured = {}

    class FakeResponses:
        def parse(self, **kwargs):
            captured.update(kwargs)

            class FakeResponse:
                class FakeUsage:
                    input_tokens = 12
                    output_tokens = 8
                    total_tokens = 20

                output_parsed = SourceAnalysis(
                    characters=["林晚"],
                    events=["宴会"],
                    conflicts=["羞辱"],
                    visual_moments=["邀请函被撕碎"],
                    low_value_passages=[],
                    candidate_hooks=["滚出去！"],
                )
                usage = FakeUsage()

            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    llm = OpenAIJsonLLM(client=FakeClient(), model="gpt-test")
    result = llm.complete(system="系统", user="用户", response_model=SourceAnalysis)

    assert result.characters == ["林晚"]
    assert captured["model"] == "gpt-test"
    assert captured["text_format"] is SourceAnalysis
    assert llm.last_usage is not None
    assert llm.last_usage.prompt_tokens == 12
    assert llm.last_usage.completion_tokens == 8
    assert llm.last_usage.total_tokens == 20


def test_openai_adapter_uses_chat_json_for_compatible_base_url(monkeypatch):
    captured = {}

    class FakeMessage:
        content = '{"value":"ok"}'

    class FakeChoice:
        finish_reason = "stop"
        message = FakeMessage()

    class FakeChatCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)

            class FakeResponse:
                class FakeUsage:
                    prompt_tokens = 5
                    completion_tokens = 7
                    total_tokens = 12

                choices = [FakeChoice()]
                usage = FakeUsage()

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.moonshot.ai/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="kimi-test")
    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert captured["model"] == "kimi-test"
    assert captured["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in captured["messages"][1]["content"]
    assert llm.last_usage is not None
    assert llm.last_usage.prompt_tokens == 5
    assert llm.last_usage.completion_tokens == 7
    assert llm.last_usage.total_tokens == 12


def test_openai_adapter_extracts_chat_json_with_trailing_text(monkeypatch):
    captured = {}

    class FakeMessage:
        content = '{"value":"ok"}\n\n已按要求输出。'

    class FakeChoice:
        finish_reason = "stop"
        message = FakeMessage()

    class FakeChatCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)

            class FakeResponse:
                choices = [FakeChoice()]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert captured["response_format"] == {"type": "json_object"}


def test_openai_adapter_extracts_chat_json_from_markdown_fence(monkeypatch):
    class FakeMessage:
        content = '```json\n{"value":"ok"}\n```'

    class FakeChoice:
        finish_reason = "stop"
        message = FakeMessage()

    class FakeChatCompletions:
        def create(self, **kwargs):
            class FakeResponse:
                choices = [FakeChoice()]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"


def test_openai_adapter_repairs_missing_comma_between_json_members(monkeypatch):
    calls = []

    class FakeMessage:
        content = """
{
  "facts": [
    "解约协议已提前放在办公桌上。"
  ]
  "forbidden_changes": [
    "严禁把解约改成临时赌气。"
  ]
}
"""

    class FakeChoice:
        finish_reason = "stop"
        message = FakeMessage()

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)

            class FakeResponse:
                choices = [FakeChoice()]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyBibleModel)

    assert result.facts == ["解约协议已提前放在办公桌上。"]
    assert result.forbidden_changes == ["严禁把解约改成临时赌气。"]
    assert len(calls) == 1


def test_openai_adapter_repairs_malformed_chat_json(monkeypatch):
    calls = []
    contents = [
        '{"value":"broken"',
        '{"value":"ok"}',
    ]

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        finish_reason = "stop"

        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            content = contents[len(calls) - 1]

            class FakeResponse:
                choices = [FakeChoice(content)]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert len(calls) == 2
    repair_prompt = calls[1]["messages"][-1]["content"]
    assert "invalid JSON" in repair_prompt
    assert '{"value":"broken"' in repair_prompt


def test_openai_adapter_repairs_deterministic_mismatched_json_closer_locally(monkeypatch):
    calls = []

    class FakeMessage:
        content = '{"value":"ok"]'

    class FakeChoice:
        finish_reason = "stop"
        message = FakeMessage()

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)

            class FakeResponse:
                choices = [FakeChoice()]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert len(calls) == 1
    assert llm.last_raw_response is not None
    assert llm.last_raw_response["attempts"][0]["local_json_repairs"] == [
        "mismatched_closer"
    ]


def test_openai_adapter_retries_empty_chat_content(monkeypatch):
    calls = []
    contents = ["", '{"value":"ok"}']

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        finish_reason = "stop"

        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            content = contents[len(calls) - 1]

            class FakeResponse:
                choices = [FakeChoice(content)]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert len(calls) == 2
    assert "no content" in calls[1]["messages"][-1]["content"]


def test_openai_adapter_retries_truncated_chat_json(monkeypatch):
    calls = []
    responses = [
        ("length", '{"value":"unfinished"' + " " * 5000),
        ("stop", '{"value":"ok"}'),
    ]

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, finish_reason, content):
            self.finish_reason = finish_reason
            self.message = FakeMessage(content)

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            finish_reason, content = responses[len(calls) - 1]

            class FakeResponse:
                choices = [FakeChoice(finish_reason, content)]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("NOVEL_DRAMA_LLM_VALIDATION_RETRIES", "1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="bytedance-seed/seed-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert len(calls) == 2
    repair_prompt = calls[1]["messages"][-1]["content"]
    assert "truncated" in repair_prompt.lower()
    assert "repeated whitespace" in repair_prompt.lower()
    assert len(repair_prompt) < 5000


def test_openai_adapter_retries_transient_request_timeout(monkeypatch):
    calls = []

    class FakeMessage:
        content = '{"value":"ok"}'

    class FakeChoice:
        finish_reason = "stop"
        message = FakeMessage()

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise TimeoutError("Request timed out.")

            class FakeResponse:
                choices = [FakeChoice()]
                usage = None

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("NOVEL_DRAMA_LLM_VALIDATION_RETRIES", "1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="bytedance-seed/seed-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyModel)

    assert result.value == "ok"
    assert len(calls) == 2
    attempts = (llm.last_raw_response or {}).get("attempts") or []
    assert attempts[0]["request_error"] == "Request timed out."


def test_openai_adapter_repairs_chat_json_validation_errors(monkeypatch):
    calls = []
    contents = [
        '{"items":["one"]}',
        '{"items":["one","two"]}',
    ]

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        finish_reason = "stop"

        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            content = contents[len(calls) - 1]

            class FakeResponse:
                class FakeUsage:
                    prompt_tokens = 5
                    completion_tokens = 7
                    total_tokens = 12

                choices = [FakeChoice(content)]
                usage = FakeUsage()

            return FakeResponse()

    class FakeChat:
        completions = FakeChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.moonshot.ai/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="kimi-test")

    result = llm.complete(system="系统", user="用户", response_model=TinyListModel)

    assert result.items == ["one", "two"]
    assert len(calls) == 2
    repair_prompt = calls[1]["messages"][-1]["content"]
    assert "failed validation" in repair_prompt
    assert "List should have at least 2 items" in repair_prompt
    assert '{"items":["one"]}' in repair_prompt


def test_openai_adapter_requires_api_key_without_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        OpenAIJsonLLM()
    except LLMConfigurationError as exc:
        assert "OPENAI_API_KEY is not set" in str(exc)
    else:
        raise AssertionError("expected LLMConfigurationError")


def test_openai_adapter_wraps_request_errors():
    class FailingResponses:
        def parse(self, **kwargs):
            raise RuntimeError("network down")

    class FakeClient:
        responses = FailingResponses()

    llm = OpenAIJsonLLM(client=FakeClient(), model="gpt-test")

    try:
        llm.complete(system="系统", user="用户", response_model=SourceAnalysis)
    except LLMResponseError as exc:
        assert "OpenAI request failed while generating SourceAnalysis" in str(exc)
        assert "network down" in str(exc)
    else:
        raise AssertionError("expected LLMResponseError")


def test_openai_adapter_classifies_provider_quota_errors(monkeypatch):
    class FailingChatCompletions:
        def create(self, **kwargs):
            raise RuntimeError("Error code: 403 - Key limit exceeded (daily limit)")

    class FakeChat:
        completions = FailingChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    try:
        llm.complete(system="系统", user="用户", response_model=TinyModel)
    except LLMProviderLimitError as exc:
        assert "LLM_PROVIDER_LIMIT" in str(exc)
        assert "Key limit exceeded" in str(exc)
    else:
        raise AssertionError("expected LLMProviderLimitError")


def test_openai_adapter_enforces_hard_chat_timeout(monkeypatch):
    class SlowChatCompletions:
        def create(self, **kwargs):
            time.sleep(2)
            raise AssertionError("request should have timed out before returning")

    class FakeChat:
        completions = SlowChatCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS", "0.2")
    llm = OpenAIJsonLLM(client=FakeClient(), model="google/gemini-test")

    try:
        llm.complete(system="系统", user="用户", response_model=TinyModel)
    except LLMResponseError as exc:
        assert "LLM call timed out after 0.2s" in str(exc)
    else:
        raise AssertionError("expected LLMResponseError")
