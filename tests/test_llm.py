from pydantic import BaseModel, Field

from novel_drama_engine.llm import (
    LLMConfigurationError,
    LLMResponseError,
    OpenAIJsonLLM,
    StaticJsonLLM,
)
from novel_drama_engine.models import SourceAnalysis


class TinyModel(BaseModel):
    value: str


class TinyListModel(BaseModel):
    items: list[str] = Field(min_length=2)


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
