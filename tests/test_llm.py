from pydantic import BaseModel

from novel_drama_engine.llm import LLMResponseError, OpenAIJsonLLM, StaticJsonLLM
from novel_drama_engine.models import SourceAnalysis


class TinyModel(BaseModel):
    value: str


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
                output_parsed = SourceAnalysis(
                    characters=["林晚"],
                    events=["宴会"],
                    conflicts=["羞辱"],
                    visual_moments=["邀请函被撕碎"],
                    low_value_passages=[],
                    candidate_hooks=["滚出去！"],
                )

            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    llm = OpenAIJsonLLM(client=FakeClient(), model="gpt-test")
    result = llm.complete(system="系统", user="用户", response_model=SourceAnalysis)

    assert result.characters == ["林晚"]
    assert captured["model"] == "gpt-test"
    assert captured["text_format"] is SourceAnalysis
