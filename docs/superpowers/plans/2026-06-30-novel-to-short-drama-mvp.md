# Novel To Short Drama MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI prototype that turns one round of Chinese novel text plus optional prior context into 1-3 short-drama episode scripts, quality results, and next-round context.

**Architecture:** Use a small package with Pydantic schemas as the contract between all six rounds. The CLI calls a pipeline service that invokes an LLM adapter for each structured round, saves every artifact as JSON, renders user-facing scripts, and retries once when quality says the script needs rewriting. Tests use a deterministic fake LLM so core behavior is verified without network calls.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer CLI, OpenAI Python SDK Responses API structured parsing, pytest.

---

## Source Design

Primary spec: `docs/superpowers/specs/2026-06-30-novel-to-short-drama-mvp-design.md`

Relevant OpenAI API doc: `https://developers.openai.com/api/docs/guides/structured-outputs`

## Scope

Ship only the internal CLI MVP:

- Input: source novel text file and optional `next_round_context` JSON file.
- Internal rounds: source parser, episode context resolver, internal bible builder, script generator, continuity/boom check, state writeback.
- Output: `RoundResult` JSON, rendered scripts, and `next_round_context.json`.
- Storage: local project directory with JSON artifacts.
- Tests: unit tests for schemas, storage, LLM adapter, pipeline retry behavior, renderer, CLI, and five fixture smoke cases.

Do not build web UI, accounts, payments, localization, video generation, cover generation, or a full 50-episode planner in this plan.

## File Structure

- Create: `pyproject.toml` — package metadata, dependencies, test config, CLI entry point.
- Create: `src/novel_drama_engine/__init__.py` — package version.
- Create: `src/novel_drama_engine/models.py` — all Pydantic contracts used between rounds.
- Create: `src/novel_drama_engine/llm.py` — LLM protocol, fake LLM, OpenAI structured-output adapter.
- Create: `src/novel_drama_engine/prompts.py` — prompt builders for each round.
- Create: `src/novel_drama_engine/storage.py` — local JSON artifact persistence.
- Create: `src/novel_drama_engine/rounds.py` — six round classes.
- Create: `src/novel_drama_engine/pipeline.py` — orchestration, failure handling, retry behavior.
- Create: `src/novel_drama_engine/renderer.py` — user-facing script rendering.
- Create: `src/novel_drama_engine/cli.py` — Typer command.
- Create: `tests/conftest.py` — reusable fake outputs and fixture helpers.
- Create: `tests/test_models.py` — schema tests.
- Create: `tests/test_storage.py` — artifact persistence tests.
- Create: `tests/test_llm.py` — fake and OpenAI adapter contract tests.
- Create: `tests/test_pipeline.py` — end-to-end pipeline tests with fake LLM.
- Create: `tests/test_renderer.py` — script rendering tests.
- Create: `tests/test_cli.py` — CLI tests.
- Create: `tests/test_acceptance_fixtures.py` — five genre smoke cases.
- Create: `examples/haomen_source.txt` — sample input.
- Create: `README.md` — local usage instructions.

## Pipeline Diagram

```text
source text + optional previous context
  |
  v
SourceParser -> SourceAnalysis
  |
  v
EpisodeContextResolver -> EpisodeContext
  |
  v
InternalBibleBuilder -> StoryBible
  |
  v
ScriptBatchGenerator -> ScriptBatch
  |
  v
ContinuityBoomChecker -> QualityReport
  |                         |
  | needs_rewrite           | usable/context_conflict
  v                         v
ScriptBatchGenerator ----> StateWriter -> NextRoundContext
  |
  v
RoundResult + rendered scripts + persisted artifacts
```

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/novel_drama_engine/__init__.py`
- Create: `README.md`
- Test: no test file in this task

- [ ] **Step 1: Create package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "novel-drama-engine"
version = "0.1.0"
description = "Round-based Chinese novel to short-drama script MVP engine"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "openai>=2.0,<3.0",
  "pydantic>=2.7,<3.0",
  "typer>=0.12,<1.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9.0",
  "pytest-cov>=5.0,<6.0"
]

[project.scripts]
novel-drama = "novel_drama_engine.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

- [ ] **Step 2: Create package init**

Create `src/novel_drama_engine/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create README**

Create `README.md`:

````markdown
# Novel Drama Engine

Round-based MVP for turning Chinese novel text into short-drama scripts.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run

```bash
export OPENAI_API_KEY="your-key"
novel-drama run --input examples/haomen_source.txt --project-dir .drama_project
```

The command writes JSON artifacts and rendered scripts under `.drama_project/`.
````

- [ ] **Step 4: Install dependencies**

Run:

```bash
python -m pip install -e ".[dev]"
```

Expected: installation succeeds and `novel-drama --help` becomes available after the CLI exists in Task 7.

- [ ] **Step 5: Commit scaffold**

Run:

```bash
git add pyproject.toml README.md src/novel_drama_engine/__init__.py
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "chore: scaffold python package"
```

Expected: commit succeeds.

### Task 2: Domain Models

**Files:**
- Create: `src/novel_drama_engine/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write schema tests**

Create `tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    RoundResult,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
    StoryStage,
    NextRoundContext,
)


def test_story_stage_rejects_unknown_value():
    with pytest.raises(ValidationError):
        EpisodeContext(
            target_episode_range="EP01-EP03",
            story_stage="slow_setup",
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.8,
        )


def test_round_result_serializes_nested_models():
    script = EpisodeScript(
        episode=1,
        title="宴会羞辱",
        hook_3s="把她拖出去！",
        main_emotion="羞辱",
        watch_reason="观众想看女主如何反击。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(kind="action", text="△林晚站在宴会厅中央，邀请函被撕成两半。"),
                    SceneLine(kind="dialogue", speaker="林雪", emotion="温柔带刺", text="姐姐，你是不是走错地方了？"),
                ],
            )
        ],
        cliffhanger="管家推门而入：大小姐，我们终于找到您了。",
        state_update={"new_fact": "管家认出林晚"},
    )
    result = RoundResult(
        project_id="demo",
        round_number=1,
        source_analysis=SourceAnalysis(
            characters=["林晚", "林雪"],
            events=["生日宴羞辱"],
            conflicts=["真假千金身份冲突"],
            visual_moments=["邀请函被撕碎"],
            low_value_passages=[],
            candidate_hooks=["把她拖出去！"],
        ),
        episode_context=EpisodeContext(
            target_episode_range="EP01-EP01",
            story_stage=StoryStage.OPENING_PRESSURE,
            source_to_episode_mapping=["生日宴羞辱 -> EP01"],
            must_carry_context=[],
            forbidden_reveals=["林晚是真千金"],
            adaptation_actions=["压缩铺垫，直接从宴会冲突开场"],
            confidence=0.95,
        ),
        story_bible=StoryBible(
            genre="真假千金",
            mainline="林晚被假千金夺走身份后逐步反击。",
            characters=["林晚", "林雪"],
            relationships=["林雪冒充林家千金"],
            speech_styles={"林晚": "克制短句，反击锋利"},
            immutable_facts=["林晚是真千金"],
            forbidden_changes=["不得新增亲哥哥"],
        ),
        script_batch=ScriptBatch(episodes=[script]),
        quality_report=QualityReport(
            status=QualityStatus.USABLE,
            scores=QualityScores(hook=8, conflict=9, cliffhanger=8, continuity=10, video_feasibility=8),
            blocking_issues=[],
            rewrite_instruction="",
        ),
        next_round_context=NextRoundContext(
            summary="EP01 结束于管家认出林晚。",
            current_episode=1,
            open_hooks=["管家为何叫她大小姐"],
            forbidden_reveals=["林晚是真千金"],
            character_knowledge={"林雪": ["林晚身份有问题"]},
            relationship_changes=["林晚与林雪公开对立"],
            prop_states=[],
            foreshadowing_ledger=["管家的称呼将在 EP03 推进"],
        ),
    )

    data = result.model_dump()
    assert data["episode_context"]["story_stage"] == "opening_pressure"
    assert data["script_batch"]["episodes"][0]["hook_3s"] == "把她拖出去！"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'novel_drama_engine.models'`.

- [ ] **Step 3: Implement schemas**

Create `src/novel_drama_engine/models.py`:

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class StoryStage(StrEnum):
    OPENING_PRESSURE = "opening_pressure"
    IDENTITY_HOOK = "identity_hook"
    FIRST_COUNTERATTACK = "first_counterattack"
    MISUNDERSTANDING_ESCALATION = "misunderstanding_escalation"
    MIDPOINT_REVERSAL = "midpoint_reversal"
    TRUTH_NEAR_REVEAL = "truth_near_reveal"
    PUBLIC_REVEAL = "public_reveal"
    FINAL_RECKONING = "final_reckoning"


class QualityStatus(StrEnum):
    USABLE = "usable"
    NEEDS_REWRITE = "needs_rewrite"
    CONTEXT_CONFLICT = "context_conflict"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class SourceAnalysis(BaseModel):
    characters: list[str]
    events: list[str]
    conflicts: list[str]
    visual_moments: list[str]
    low_value_passages: list[str]
    candidate_hooks: list[str]


class EpisodeContext(BaseModel):
    target_episode_range: str
    story_stage: StoryStage
    source_to_episode_mapping: list[str]
    must_carry_context: list[str]
    forbidden_reveals: list[str]
    adaptation_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class StoryBible(BaseModel):
    genre: str
    mainline: str
    characters: list[str]
    relationships: list[str]
    speech_styles: dict[str, str]
    immutable_facts: list[str]
    forbidden_changes: list[str]


class SceneLine(BaseModel):
    kind: Literal["action", "dialogue", "os", "vo", "transition"]
    text: str
    speaker: str | None = None
    emotion: str | None = None


class Scene(BaseModel):
    heading: str
    characters: list[str]
    lines: list[SceneLine]


class EpisodeScript(BaseModel):
    episode: int = Field(ge=1)
    title: str
    hook_3s: str
    main_emotion: str
    watch_reason: str
    scenes: list[Scene]
    cliffhanger: str
    state_update: dict[str, Any]


class ScriptBatch(BaseModel):
    episodes: list[EpisodeScript] = Field(min_length=1, max_length=3)


class QualityScores(BaseModel):
    hook: int = Field(ge=0, le=10)
    conflict: int = Field(ge=0, le=10)
    cliffhanger: int = Field(ge=0, le=10)
    continuity: int = Field(ge=0, le=10)
    video_feasibility: int = Field(ge=0, le=10)


class QualityReport(BaseModel):
    status: QualityStatus
    scores: QualityScores
    blocking_issues: list[str]
    rewrite_instruction: str


class NextRoundContext(BaseModel):
    summary: str
    current_episode: int = Field(ge=0)
    open_hooks: list[str]
    forbidden_reveals: list[str]
    character_knowledge: dict[str, list[str]]
    relationship_changes: list[str]
    prop_states: list[str]
    foreshadowing_ledger: list[str]


class RoundResult(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    source_analysis: SourceAnalysis
    episode_context: EpisodeContext
    story_bible: StoryBible
    script_batch: ScriptBatch
    quality_report: QualityReport
    next_round_context: NextRoundContext
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
pytest tests/test_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit schemas**

Run:

```bash
git add src/novel_drama_engine/models.py tests/test_models.py
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "feat: add structured domain models"
```

Expected: commit succeeds.

### Task 3: JSON Artifact Storage

**Files:**
- Create: `src/novel_drama_engine/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write storage tests**

Create `tests/test_storage.py`:

```python
from novel_drama_engine.models import SourceAnalysis
from novel_drama_engine.storage import ProjectStore


def test_store_writes_round_artifact(tmp_path):
    store = ProjectStore(tmp_path)
    analysis = SourceAnalysis(
        characters=["林晚"],
        events=["宴会被羞辱"],
        conflicts=["身份冲突"],
        visual_moments=["邀请函被撕碎"],
        low_value_passages=[],
        candidate_hooks=["把她拖出去！"],
    )

    path = store.write_round_artifact(1, "source_analysis", analysis)

    assert path == tmp_path / "round_001" / "source_analysis.json"
    assert '"林晚"' in path.read_text(encoding="utf-8")


def test_store_reads_context_json(tmp_path):
    context_path = tmp_path / "context.json"
    context_path.write_text(
        '{"summary":"EP01结束","current_episode":1,"open_hooks":[],"forbidden_reveals":[],"character_knowledge":{},"relationship_changes":[],"prop_states":[],"foreshadowing_ledger":[]}',
        encoding="utf-8",
    )

    context = ProjectStore(tmp_path).read_next_round_context(context_path)

    assert context.summary == "EP01结束"
    assert context.current_episode == 1
```

- [ ] **Step 2: Run storage tests to verify they fail**

Run:

```bash
pytest tests/test_storage.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'novel_drama_engine.storage'`.

- [ ] **Step 3: Implement storage**

Create `src/novel_drama_engine/storage.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from novel_drama_engine.models import NextRoundContext, RoundResult


class ProjectStore:
    def __init__(self, project_dir: Path | str) -> None:
        self.project_dir = Path(project_dir)

    def round_dir(self, round_number: int) -> Path:
        path = self.project_dir / f"round_{round_number:03d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_round_artifact(self, round_number: int, name: str, model: BaseModel) -> Path:
        path = self.round_dir(round_number) / f"{name}.json"
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        return path

    def write_text_artifact(self, round_number: int, name: str, text: str) -> Path:
        path = self.round_dir(round_number) / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_round_result(self, result: RoundResult) -> Path:
        return self.write_round_artifact(result.round_number, "round_result", result)

    def write_next_round_context(self, result: RoundResult) -> Path:
        path = self.round_dir(result.round_number) / "next_round_context.json"
        path.write_text(result.next_round_context.model_dump_json(indent=2), encoding="utf-8")
        return path

    def read_next_round_context(self, path: Path | str) -> NextRoundContext:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return NextRoundContext.model_validate(raw)
```

- [ ] **Step 4: Run storage tests**

Run:

```bash
pytest tests/test_storage.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit storage**

Run:

```bash
git add src/novel_drama_engine/storage.py tests/test_storage.py
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "feat: persist round artifacts"
```

Expected: commit succeeds.

### Task 4: LLM Adapter

**Files:**
- Create: `src/novel_drama_engine/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write LLM adapter tests**

Create `tests/test_llm.py`:

```python
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
```

- [ ] **Step 2: Run LLM tests to verify they fail**

Run:

```bash
pytest tests/test_llm.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'novel_drama_engine.llm'`.

- [ ] **Step 3: Implement LLM adapter**

Create `src/novel_drama_engine/llm.py`:

```python
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
            raise LLMResponseError(f"OpenAI returned no parsed output for {response_model.__name__}")
        if not isinstance(parsed, response_model):
            return response_model.model_validate(parsed)
        return parsed
```

- [ ] **Step 4: Run LLM tests**

Run:

```bash
pytest tests/test_llm.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit LLM adapter**

Run:

```bash
git add src/novel_drama_engine/llm.py tests/test_llm.py
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "feat: add structured llm adapter"
```

Expected: commit succeeds.

### Task 5: Round Prompt Builders and Round Services

**Files:**
- Create: `src/novel_drama_engine/prompts.py`
- Create: `src/novel_drama_engine/rounds.py`
- Create: `tests/conftest.py`
- Create: `tests/test_pipeline.py` initial tests

- [ ] **Step 1: Add reusable fake outputs**

Create `tests/conftest.py`:

```python
import pytest

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
    StoryStage,
)


@pytest.fixture
def happy_round_outputs():
    return [
        SourceAnalysis(
            characters=["林晚", "林雪", "顾承"],
            events=["林晚在生日宴被赶走"],
            conflicts=["真假千金身份冲突", "男主误判女主"],
            visual_moments=["邀请函被撕碎", "林晚站在宴会中央"],
            low_value_passages=["宴会前长篇心理描写"],
            candidate_hooks=["把她拖出去！"],
        ),
        EpisodeContext(
            target_episode_range="EP01-EP01",
            story_stage=StoryStage.OPENING_PRESSURE,
            source_to_episode_mapping=["生日宴羞辱 -> EP01"],
            must_carry_context=[],
            forbidden_reveals=["林晚是真千金"],
            adaptation_actions=["压缩铺垫，直接从宴会冲突开场"],
            confidence=0.93,
        ),
        StoryBible(
            genre="真假千金",
            mainline="林晚被假千金夺走身份后，在公开羞辱中逐步反击。",
            characters=["林晚", "林雪", "顾承"],
            relationships=["林雪冒充千金", "顾承暂时误会林晚"],
            speech_styles={"林晚": "克制短句，反击锋利", "林雪": "表面温柔，每句带刺"},
            immutable_facts=["林晚是真千金"],
            forbidden_changes=["不得新增亲哥哥", "不得提前公开亲子鉴定"],
        ),
        ScriptBatch(
            episodes=[
                EpisodeScript(
                    episode=1,
                    title="被赶出生日宴",
                    hook_3s="把她拖出去！",
                    main_emotion="羞辱",
                    watch_reason="观众想看林晚如何从公开羞辱里反击。",
                    scenes=[
                        Scene(
                            heading="1-1 夜-内-林家宴会厅",
                            characters=["林晚", "林雪", "顾承"],
                            lines=[
                                SceneLine(kind="action", text="△林晚站在宴会厅中央，手里的邀请函被顾承撕成两半。"),
                                SceneLine(kind="dialogue", speaker="顾承", emotion="冷", text="滚出去。"),
                                SceneLine(kind="dialogue", speaker="林雪", emotion="温柔", text="姐姐，别让大家难堪。"),
                            ],
                        )
                    ],
                    cliffhanger="门口老管家一震：大小姐？",
                    state_update={"open_hook": "管家认出林晚"},
                )
            ]
        ),
        QualityReport(
            status=QualityStatus.USABLE,
            scores=QualityScores(hook=9, conflict=9, cliffhanger=8, continuity=10, video_feasibility=8),
            blocking_issues=[],
            rewrite_instruction="",
        ),
        NextRoundContext(
            summary="EP01 结束于管家认出林晚。",
            current_episode=1,
            open_hooks=["管家为什么叫林晚大小姐"],
            forbidden_reveals=["林晚是真千金"],
            character_knowledge={"林雪": ["林晚身份有问题"], "顾承": ["林晚被赶出宴会"]},
            relationship_changes=["林晚与顾承冲突升级"],
            prop_states=["邀请函被撕碎"],
            foreshadowing_ledger=["管家称呼将在后续推进身份线"],
        ),
    ]
```

- [ ] **Step 2: Write round service test**

Create `tests/test_pipeline.py` with the first round-service test:

```python
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.rounds import (
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
    ContinuityBoomChecker,
)


def test_round_services_consume_llm_outputs_in_order(happy_round_outputs):
    llm = StaticJsonLLM(happy_round_outputs)
    source = SourceParser(llm).run("林晚被赶出生日宴。")
    context = EpisodeContextResolver(llm).run("林晚被赶出生日宴。", None, source)
    bible = InternalBibleBuilder(llm).run("林晚被赶出生日宴。", source, context)
    scripts = ScriptBatchGenerator(llm).run("林晚被赶出生日宴。", source, context, bible, None, "")
    quality = ContinuityBoomChecker(llm).run(source, context, bible, scripts, None)
    next_context = StateWriter(llm).run(source, context, bible, scripts, quality, None)

    assert source.candidate_hooks == ["把她拖出去！"]
    assert context.target_episode_range == "EP01-EP01"
    assert scripts.episodes[0].hook_3s == "把她拖出去！"
    assert quality.status == "usable"
    assert next_context.current_episode == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
pytest tests/test_pipeline.py::test_round_services_consume_llm_outputs_in_order -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'novel_drama_engine.rounds'`.

- [ ] **Step 4: Implement prompt builders**

Create `src/novel_drama_engine/prompts.py`:

```python
from __future__ import annotations

from pydantic import BaseModel


def dump_model(name: str, model: BaseModel | None) -> str:
    if model is None:
        return f"{name}: null"
    return f"{name}: {model.model_dump_json(indent=2)}"


SOURCE_PARSER_SYSTEM = "你是短剧小说解析器。只提取短剧生产资产，不写剧情总结。"
EPISODE_CONTEXT_SYSTEM = "你是短剧集数和上下文解析器。判断原文应映射到哪几集，并给出承接约束。"
BIBLE_SYSTEM = "你是短剧 Story Bible 构建器。自动锁定主线、人物、关系和禁止改动项。"
SCRIPT_SYSTEM = "你是爆款竖屏短剧编剧。输出可拍摄、强冲突、短台词、每集留钩的剧本。"
QUALITY_SYSTEM = "你是短剧质检器。检查 Hook、冲突、信息差、连续性、可拍性。"
STATE_SYSTEM = "你是短剧状态回写器。把本轮事实、关系、伏笔、道具和下一轮钩子写回状态。"


def source_parser_user(source_text: str) -> str:
    return f"小说原文：\n{source_text}\n\n提取人物、事件、冲突、可视频化场面、低价值段落和候选 Hook。"


def episode_context_user(source_text: str, previous_context: BaseModel | None, source_analysis: BaseModel) -> str:
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            dump_model("previous_context", previous_context),
            dump_model("source_analysis", source_analysis),
            "判断 target_episode_range、story_stage、must_carry_context、forbidden_reveals、adaptation_actions，并给 confidence。",
        ]
    )


def bible_user(source_text: str, source_analysis: BaseModel, episode_context: BaseModel) -> str:
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            "生成内部 Story Bible。不要要求用户确认。",
        ]
    )


def script_user(source_text: str, source_analysis: BaseModel, episode_context: BaseModel, story_bible: BaseModel, previous_context: BaseModel | None, rewrite_instruction: str) -> str:
    return "\n\n".join(
        [
            f"小说原文：\n{source_text}",
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("previous_context", previous_context),
            f"rewrite_instruction: {rewrite_instruction}",
            "每集输出 3 秒 Hook、主情绪、watch_reason、场景、cliffhanger、state_update。OS 后必须跟动作或明确决定。",
        ]
    )


def quality_user(source_analysis: BaseModel, episode_context: BaseModel, story_bible: BaseModel, script_batch: BaseModel, previous_context: BaseModel | None) -> str:
    return "\n\n".join(
        [
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("script_batch", script_batch),
            dump_model("previous_context", previous_context),
            "检查是否可用。若必须重写，status=needs_rewrite 并给 rewrite_instruction。",
        ]
    )


def state_user(source_analysis: BaseModel, episode_context: BaseModel, story_bible: BaseModel, script_batch: BaseModel, quality_report: BaseModel, previous_context: BaseModel | None) -> str:
    return "\n\n".join(
        [
            dump_model("source_analysis", source_analysis),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("script_batch", script_batch),
            dump_model("quality_report", quality_report),
            dump_model("previous_context", previous_context),
            "生成 next_round_context，保留 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger。",
        ]
    )
```

- [ ] **Step 5: Implement round services**

Create `src/novel_drama_engine/rounds.py`:

```python
from __future__ import annotations

from novel_drama_engine import prompts
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeContext,
    NextRoundContext,
    QualityReport,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
)


class SourceParser:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(self, source_text: str) -> SourceAnalysis:
        return self.llm.complete(
            system=prompts.SOURCE_PARSER_SYSTEM,
            user=prompts.source_parser_user(source_text),
            response_model=SourceAnalysis,
        )


class EpisodeContextResolver:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(self, source_text: str, previous_context: NextRoundContext | None, source_analysis: SourceAnalysis) -> EpisodeContext:
        return self.llm.complete(
            system=prompts.EPISODE_CONTEXT_SYSTEM,
            user=prompts.episode_context_user(source_text, previous_context, source_analysis),
            response_model=EpisodeContext,
        )


class InternalBibleBuilder:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(self, source_text: str, source_analysis: SourceAnalysis, episode_context: EpisodeContext) -> StoryBible:
        return self.llm.complete(
            system=prompts.BIBLE_SYSTEM,
            user=prompts.bible_user(source_text, source_analysis, episode_context),
            response_model=StoryBible,
        )


class ScriptBatchGenerator:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
    ) -> ScriptBatch:
        return self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.script_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                rewrite_instruction,
            ),
            response_model=ScriptBatch,
        )


class ContinuityBoomChecker:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        script_batch: ScriptBatch,
        previous_context: NextRoundContext | None,
    ) -> QualityReport:
        return self.llm.complete(
            system=prompts.QUALITY_SYSTEM,
            user=prompts.quality_user(source_analysis, episode_context, story_bible, script_batch, previous_context),
            response_model=QualityReport,
        )


class StateWriter:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        script_batch: ScriptBatch,
        quality_report: QualityReport,
        previous_context: NextRoundContext | None,
    ) -> NextRoundContext:
        return self.llm.complete(
            system=prompts.STATE_SYSTEM,
            user=prompts.state_user(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                quality_report,
                previous_context,
            ),
            response_model=NextRoundContext,
        )
```

- [ ] **Step 6: Run round service test**

Run:

```bash
pytest tests/test_pipeline.py::test_round_services_consume_llm_outputs_in_order -q
```

Expected: PASS.

- [ ] **Step 7: Commit round services**

Run:

```bash
git add src/novel_drama_engine/prompts.py src/novel_drama_engine/rounds.py tests/conftest.py tests/test_pipeline.py
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "feat: add round services"
```

Expected: commit succeeds.

### Task 6: Pipeline Orchestration and Retry

**Files:**
- Create: `src/novel_drama_engine/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add pipeline tests**

Append to `tests/test_pipeline.py`:

```python
import pytest

from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import QualityReport, QualityScores, QualityStatus
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.storage import ProjectStore


def test_pipeline_rejects_empty_source(tmp_path):
    pipeline = RoundPipeline(llm=StaticJsonLLM([]), store=ProjectStore(tmp_path))

    with pytest.raises(EmptySourceError):
        pipeline.run(project_id="demo", round_number=1, source_text="   ")


def test_pipeline_persists_artifacts(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.script_batch.episodes[0].title == "被赶出生日宴"
    assert (tmp_path / "round_001" / "source_analysis.json").exists()
    assert (tmp_path / "round_001" / "round_result.json").exists()
    assert (tmp_path / "round_001" / "next_round_context.json").exists()


def test_pipeline_rewrites_once_when_quality_requires_it(tmp_path, happy_round_outputs):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    failed_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(hook=4, conflict=6, cliffhanger=5, continuity=9, video_feasibility=8),
        blocking_issues=["前3秒 Hook 不够强"],
        rewrite_instruction="把开头改成当众驱逐。",
    )
    rewritten_script = first_script.model_copy(deep=True)
    rewritten_script.episodes[0].hook_3s = "把她拖出去！她不是林家的女儿！"
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(hook=9, conflict=9, cliffhanger=8, continuity=10, video_feasibility=8),
        blocking_issues=[],
        rewrite_instruction="",
    )
    outputs = outputs[:4] + [failed_quality, rewritten_script, final_quality, outputs[5]]
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.script_batch.episodes[0].hook_3s == "把她拖出去！她不是林家的女儿！"
    assert result.quality_report.status == QualityStatus.USABLE
```

- [ ] **Step 2: Run pipeline tests to verify they fail**

Run:

```bash
pytest tests/test_pipeline.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'novel_drama_engine.pipeline'`.

- [ ] **Step 3: Implement pipeline**

Create `src/novel_drama_engine/pipeline.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import NextRoundContext, QualityStatus, RoundResult
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
)
from novel_drama_engine.storage import ProjectStore


class EmptySourceError(ValueError):
    pass


@dataclass
class RoundPipeline:
    llm: JsonLLM
    store: ProjectStore

    def run(
        self,
        *,
        project_id: str,
        round_number: int,
        source_text: str,
        previous_context: NextRoundContext | None = None,
    ) -> RoundResult:
        if not source_text.strip():
            raise EmptySourceError("source_text is empty")

        source_analysis = SourceParser(self.llm).run(source_text)
        self.store.write_round_artifact(round_number, "source_analysis", source_analysis)

        episode_context = EpisodeContextResolver(self.llm).run(source_text, previous_context, source_analysis)
        self.store.write_round_artifact(round_number, "episode_context", episode_context)

        story_bible = InternalBibleBuilder(self.llm).run(source_text, source_analysis, episode_context)
        self.store.write_round_artifact(round_number, "story_bible", story_bible)

        script_generator = ScriptBatchGenerator(self.llm)
        script_batch = script_generator.run(source_text, source_analysis, episode_context, story_bible, previous_context, "")
        self.store.write_round_artifact(round_number, "script_batch", script_batch)

        checker = ContinuityBoomChecker(self.llm)
        quality_report = checker.run(source_analysis, episode_context, story_bible, script_batch, previous_context)

        if quality_report.status == QualityStatus.NEEDS_REWRITE:
            self.store.write_round_artifact(round_number, "quality_report_before_rewrite", quality_report)
            script_batch = script_generator.run(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                quality_report.rewrite_instruction,
            )
            self.store.write_round_artifact(round_number, "script_batch_rewrite", script_batch)
            quality_report = checker.run(source_analysis, episode_context, story_bible, script_batch, previous_context)
            if quality_report.status == QualityStatus.NEEDS_REWRITE:
                quality_report = quality_report.model_copy(update={"status": QualityStatus.NEEDS_HUMAN_REVIEW})

        self.store.write_round_artifact(round_number, "quality_report", quality_report)

        next_round_context = StateWriter(self.llm).run(
            source_analysis,
            episode_context,
            story_bible,
            script_batch,
            quality_report,
            previous_context,
        )

        result = RoundResult(
            project_id=project_id,
            round_number=round_number,
            source_analysis=source_analysis,
            episode_context=episode_context,
            story_bible=story_bible,
            script_batch=script_batch,
            quality_report=quality_report,
            next_round_context=next_round_context,
        )
        self.store.write_round_result(result)
        self.store.write_next_round_context(result)
        return result
```

- [ ] **Step 4: Run pipeline tests**

Run:

```bash
pytest tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit pipeline**

Run:

```bash
git add src/novel_drama_engine/pipeline.py tests/test_pipeline.py
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "feat: orchestrate generation pipeline"
```

Expected: commit succeeds.

### Task 7: Renderer and CLI

**Files:**
- Create: `src/novel_drama_engine/renderer.py`
- Create: `src/novel_drama_engine/cli.py`
- Create: `tests/test_renderer.py`
- Create: `tests/test_cli.py`
- Create: `examples/haomen_source.txt`

- [ ] **Step 1: Write renderer tests**

Create `tests/test_renderer.py`:

```python
from novel_drama_engine.renderer import render_episode, render_round_summary


def test_render_episode_outputs_short_drama_format(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    text = render_episode(script_batch.episodes[0])

    assert "第1集 被赶出生日宴" in text
    assert "1-1 夜-内-林家宴会厅" in text
    assert "人物：林晚、林雪、顾承" in text
    assert "顾承（冷）：滚出去。" in text


def test_render_round_summary_includes_quality_status(happy_round_outputs):
    quality = happy_round_outputs[4]
    script_batch = happy_round_outputs[3]

    text = render_round_summary(script_batch, quality)

    assert "质量结论：usable" in text
    assert "Hook: 9" in text
```

- [ ] **Step 2: Write CLI test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.llm import StaticJsonLLM


def test_cli_run_writes_outputs(tmp_path, happy_round_outputs, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")
    project_dir = tmp_path / "project"

    monkeypatch.setattr(cli, "build_llm", lambda: StaticJsonLLM(happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        ["run", "--input", str(source), "--project-dir", str(project_dir), "--project-id", "demo"],
    )

    assert result.exit_code == 0
    assert "EP01-EP01" in result.stdout
    assert "第1集 被赶出生日宴" in result.stdout
    assert (project_dir / "round_001" / "rendered_scripts.md").exists()
```

- [ ] **Step 3: Run renderer and CLI tests to verify they fail**

Run:

```bash
pytest tests/test_renderer.py tests/test_cli.py -q
```

Expected: FAIL with missing `renderer` and `cli` modules.

- [ ] **Step 4: Implement renderer**

Create `src/novel_drama_engine/renderer.py`:

```python
from __future__ import annotations

from novel_drama_engine.models import EpisodeScript, QualityReport, SceneLine, ScriptBatch


def render_line(line: SceneLine) -> str:
    if line.kind == "action":
        return line.text
    if line.kind == "dialogue":
        emotion = f"（{line.emotion}）" if line.emotion else ""
        speaker = line.speaker or "角色"
        return f"{speaker}{emotion}：{line.text}"
    if line.kind == "os":
        speaker = line.speaker or "角色"
        return f"{speaker}OS：{line.text}"
    if line.kind == "vo":
        speaker = line.speaker or "画外"
        return f"{speaker}VO：{line.text}"
    return line.text


def render_episode(script: EpisodeScript) -> str:
    parts = [f"第{script.episode}集 {script.title}", "", f"3秒 Hook：{script.hook_3s}", f"主情绪：{script.main_emotion}", f"消费理由：{script.watch_reason}", ""]
    for scene in script.scenes:
        parts.append(scene.heading)
        parts.append(f"人物：{'、'.join(scene.characters)}")
        parts.append("")
        parts.extend(render_line(line) for line in scene.lines)
        parts.append("")
    parts.append(f"结尾钩子：{script.cliffhanger}")
    return "\n".join(parts).strip()


def render_round_summary(script_batch: ScriptBatch, quality_report: QualityReport) -> str:
    scores = quality_report.scores
    return "\n".join(
        [
            f"质量结论：{quality_report.status.value}",
            f"Hook: {scores.hook}",
            f"Conflict: {scores.conflict}",
            f"Cliffhanger: {scores.cliffhanger}",
            f"Continuity: {scores.continuity}",
            f"Video Feasibility: {scores.video_feasibility}",
            "",
            *[render_episode(episode) for episode in script_batch.episodes],
        ]
    )
```

- [ ] **Step 5: Implement CLI**

Create `src/novel_drama_engine/cli.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from novel_drama_engine.llm import OpenAIJsonLLM
from novel_drama_engine.models import NextRoundContext
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.storage import ProjectStore

app = typer.Typer(help="Novel-to-short-drama MVP CLI")


def build_llm() -> OpenAIJsonLLM:
    return OpenAIJsonLLM()


@app.command()
def run(
    input: Annotated[Path, typer.Option("--input", "-i", exists=True, readable=True, help="Novel source text file.")],
    context: Annotated[Optional[Path], typer.Option("--context", "-c", exists=True, readable=True, help="Previous next_round_context JSON.")] = None,
    project_dir: Annotated[Path, typer.Option("--project-dir", help="Directory for JSON artifacts.")] = Path(".drama_project"),
    project_id: Annotated[str, typer.Option("--project-id", help="Project identifier stored in round_result.json.")] = "local",
    round_number: Annotated[int, typer.Option("--round-number", min=1, help="Generation round number.")] = 1,
) -> None:
    source_text = input.read_text(encoding="utf-8")
    store = ProjectStore(project_dir)
    previous_context = store.read_next_round_context(context) if context else None
    pipeline = RoundPipeline(llm=build_llm(), store=store)
    try:
        result = pipeline.run(
            project_id=project_id,
            round_number=round_number,
            source_text=source_text,
            previous_context=previous_context,
        )
    except EmptySourceError as exc:
        raise typer.BadParameter(str(exc)) from exc

    rendered = render_round_summary(result.script_batch, result.quality_report)
    store.write_text_artifact(round_number, "rendered_scripts.md", rendered)
    typer.echo(f"Episode range: {result.episode_context.target_episode_range}")
    typer.echo(rendered)
    typer.echo(f"\nArtifacts written to: {store.round_dir(round_number)}")
```

- [ ] **Step 6: Create example source**

Create `examples/haomen_source.txt`:

```text
林晚刚走进林家的生日宴，所有人的目光都落在她身上。
林雪挽着顾承的手，温柔地说：“姐姐，你怎么穿成这样就来了？”
顾承看了一眼林晚手里的邀请函，冷笑一声，当众把邀请函撕成两半。
“把她拖出去。”他说，“她根本不是林家的人。”
林晚低头看着地上的碎纸，手指一点点攥紧。
门口的老管家忽然停住脚步，盯着林晚的脸，声音发颤：“大小姐？”
```

- [ ] **Step 7: Run renderer and CLI tests**

Run:

```bash
pytest tests/test_renderer.py tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit renderer and CLI**

Run:

```bash
git add src/novel_drama_engine/renderer.py src/novel_drama_engine/cli.py tests/test_renderer.py tests/test_cli.py examples/haomen_source.txt
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "feat: add cli and script renderer"
```

Expected: commit succeeds.

### Task 8: Acceptance Fixtures and Final Verification

**Files:**
- Create: `tests/test_acceptance_fixtures.py`
- Modify: `README.md`

- [ ] **Step 1: Write acceptance fixture tests**

Create `tests/test_acceptance_fixtures.py`:

```python
import pytest

from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.storage import ProjectStore


@pytest.mark.parametrize(
    "source_text",
    [
        "林晚在豪门宴会上被未婚夫当众赶走，假千金站在旁边假意求情。",
        "亲子鉴定报告被林雪藏进包里，林晚发现报告编号被换过。",
        "顾承误会林晚害了林雪，三年后才发现自己签下的是假证词。",
        "赘婿叶辰被岳父一家羞辱，下一秒黑卡被银行经理亲自送到门口。",
        "沈青重生回成亲当夜，发现毒酒已经端到自己面前。",
    ],
)
def test_five_genre_fixtures_complete_one_round(tmp_path, source_text, happy_round_outputs):
    result = RoundPipeline(
        llm=StaticJsonLLM(list(happy_round_outputs)),
        store=ProjectStore(tmp_path),
    ).run(project_id="acceptance", round_number=1, source_text=source_text)

    assert result.episode_context.target_episode_range.startswith("EP")
    assert result.script_batch.episodes[0].hook_3s
    assert result.script_batch.episodes[0].cliffhanger
    assert result.next_round_context.current_episode >= 1
```

- [ ] **Step 2: Update README with test and CLI commands**

Replace `README.md` with:

````markdown
# Novel Drama Engine

Round-based MVP for turning Chinese novel text into short-drama scripts.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Test

```bash
pytest
```

## Run

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-5.5"
novel-drama run --input examples/haomen_source.txt --project-dir .drama_project --project-id demo --round-number 1
```

The command writes:

- `.drama_project/round_001/source_analysis.json`
- `.drama_project/round_001/episode_context.json`
- `.drama_project/round_001/story_bible.json`
- `.drama_project/round_001/script_batch.json`
- `.drama_project/round_001/quality_report.json`
- `.drama_project/round_001/round_result.json`
- `.drama_project/round_001/next_round_context.json`
- `.drama_project/round_001/rendered_scripts.md`

## Continue A Second Round

```bash
novel-drama run \
  --input examples/haomen_source.txt \
  --context .drama_project/round_001/next_round_context.json \
  --project-dir .drama_project \
  --project-id demo \
  --round-number 2
```
````

- [ ] **Step 3: Run the full test suite**

Run:

```bash
pytest
```

Expected: PASS.

- [ ] **Step 4: Run package import smoke test**

Run:

```bash
python -c "from novel_drama_engine.pipeline import RoundPipeline; print(RoundPipeline.__name__)"
```

Expected output:

```text
RoundPipeline
```

- [ ] **Step 5: Run CLI help**

Run:

```bash
novel-drama --help
```

Expected: command exits 0 and prints Typer help including the `run` command.

- [ ] **Step 6: Commit acceptance tests and docs**

Run:

```bash
git add tests/test_acceptance_fixtures.py README.md
git -c user.name='Codex' -c user.email='codex@openai.com' commit -m "test: add acceptance fixture coverage"
```

Expected: commit succeeds.

## Self-Review

Spec coverage:

- Source Parser is implemented by Task 5.
- Episode Context Resolver is implemented by Task 5 and verified through Task 6/8.
- Internal Story Bible is implemented by Task 5 and stored by Task 6.
- Script batch generation is implemented by Task 5 and rendered by Task 7.
- Quality gate and single rewrite are implemented by Task 6.
- State writeback is implemented by Task 5 and persisted by Task 6.
- User-visible CLI output is implemented by Task 7.
- Five fixture smoke cases are implemented by Task 8.

Scope check:

- No web UI.
- No account system.
- No payment system.
- No localization.
- No video generation.
- No 50-episode full planner.
- No user confirmation gate for Story Bible.

Type consistency:

- `SourceAnalysis`, `EpisodeContext`, `StoryBible`, `ScriptBatch`, `QualityReport`, `NextRoundContext`, and `RoundResult` are defined once in `models.py`.
- Round classes use the same model names that tests and pipeline use.
- CLI reads and writes `NextRoundContext` using the same storage API as the pipeline.

Verification commands:

```bash
pytest
python -c "from novel_drama_engine.pipeline import RoundPipeline; print(RoundPipeline.__name__)"
novel-drama --help
```
