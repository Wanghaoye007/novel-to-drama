# Internal Methodology Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal methodology knowledge engine that stores reusable short-drama methods, classifies source strength, controls adaptation intensity, injects active method cards into generation, and surfaces internal-only methodology state.

**Architecture:** Keep the user-facing creation and round flows unchanged. Add Python engine models and artifacts for source strength and method context, file/DB-backed methodology records for internal management, and a small internal Next.js workspace for source/card review. Method cards are draft by default and only active cards can affect prompt context or quality gates.

**Tech Stack:** Python 3.14, Pydantic, pytest, Next.js 16 App Router, TypeScript, Drizzle SQLite, existing job/artifact storage.

---

## File Structure

Create:

- `src/novel_drama_engine/methodology.py`
  Owns methodology source/card helpers, deterministic card extraction for v1, active-card retrieval, and prompt rendering helpers.

- `src/novel_drama_engine/source_strength.py`
  Owns deterministic source-strength scoring and adaptation-intensity recommendation.

- `examples/methodology_sources/strong_source_light_adaptation.md`
  Seed internal method source for strong-original protection.

- `examples/methodology_cards.json`
  Seed active method cards used by CLI/web generation until the internal DB has cards.

- `tests/test_methodology.py`
  Covers method card extraction, status filtering, stage retrieval, and prompt rendering.

- `tests/test_source_strength.py`
  Covers strong/medium/weak source classification and adaptation intensity.

- `src/lib/methodology.ts`
  TypeScript data access for internal methodology DB rows, seed fallback, parsing, status updates, and view models.

- `src/app/api/methodology/route.ts`
  Internal API for listing and creating methodology sources/cards.

- `src/app/api/methodology/cards/[id]/route.ts`
  Internal API for changing card status.

- `src/app/methodology/page.tsx`
  Server entry for the internal methodology workspace.

- `src/app/methodology/MethodologyClient.tsx`
  Client UI for sources, cards, filters, status toggles, and source/card detail.

Modify:

- `src/novel_drama_engine/models.py`
  Add methodology and source-strength schemas. Add optional `source_strength_profile`, `methodology_context`, and `methodology_quality_report` to `RoundResult`. Add optional `methodology_cards` to `RuntimeReport`.

- `src/novel_drama_engine/prompts.py`
  Add methodology context rendering and optional `methodology_context` parameters to relevant stage prompts.

- `src/novel_drama_engine/rounds.py`
  Pass methodology context into prompt builders.

- `src/novel_drama_engine/pipeline.py`
  Classify source strength after source analysis/viral assets, retrieve active method cards, write artifacts, pass context through stages, and include artifacts in `RoundResult`.

- `src/novel_drama_engine/demo.py`
  Add deterministic demo source-strength and methodology context outputs for mock runs.

- `src/novel_drama_engine/adaptation_quality.py`
  Add strong-source/light-adaptation quality checks and methodology issue reporting.

- `src/novel_drama_engine/cli.py`
  Add optional `--methodology-cards` path and print source-strength/adaptation-intensity summary.

- `src/db/schema.ts`
  Add `methodology_sources`, `methodology_cards`, and `methodology_runs`.

- `src/components/app-shell.tsx`
  Add internal-only navigation item `内部方法论`.

- `src/lib/engine-types.ts`
  Add TypeScript interfaces for source strength, methodology context, and methodology quality report.

- `src/lib/engine-runner.ts`
  Include methodology artifacts in sync/runtime summaries when present.

---

## Task 1: Python Schemas and Fixtures

**Files:**
- Modify: `src/novel_drama_engine/models.py`
- Modify: `src/novel_drama_engine/demo.py`
- Create: `examples/methodology_sources/strong_source_light_adaptation.md`
- Create: `examples/methodology_cards.json`
- Test: `tests/test_models.py`

- [ ] **Step 1: Add failing model tests**

Append these tests to `tests/test_models.py`:

```python
from novel_drama_engine.models import (
    AdaptationIntensity,
    MethodologyCard,
    MethodologyContext,
    MethodologySource,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
    SourceStrengthProfile,
)


def test_source_strength_profile_model_accepts_light_strong_profile():
    profile = SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=10,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["原文已有强开场钩子和公开压迫名场面"],
    )

    assert profile.overall_level == SourceStrengthLevel.STRONG
    assert profile.recommended_intensity == AdaptationIntensity.LIGHT


def test_methodology_card_defaults_to_draft_and_tracks_stage():
    source = MethodologySource(
        id="method_source_001",
        title="短剧改编 SOP 总纲",
        source_type="sop",
        raw_text="强原文轻改，弱原文重构。",
        origin_path="/Users/wangzipeng/Documents/DJ_Project/00_改编SOP总纲.md",
        status=MethodologyStatus.DRAFT,
    )
    card = MethodologyCard(
        id="method_card_001",
        source_id=source.id,
        name="强原文轻改规则",
        category="source_fidelity",
        applies_to_channel=["female", "male", "mixed"],
        applies_to_genre=["revenge", "identity"],
        applies_to_stage=[MethodologyStage.SCRIPT_GENERATION, MethodologyStage.QUALITY_GATE],
        trigger="原文已具备强冲突、强钩子、强反差或高情绪名场面",
        generation_rule="只做视听化、压缩和镜头补强，不改变主动方和因果顺序。",
        quality_rule="删除 C1 名场面或改变 C0 主动方时必须 needs_rewrite。",
    )

    context = MethodologyContext(
        source_strength_level=SourceStrengthLevel.STRONG,
        adaptation_intensity=AdaptationIntensity.LIGHT,
        cards=[card],
    )

    assert card.status == MethodologyStatus.DRAFT
    assert MethodologyStage.SCRIPT_GENERATION in card.applies_to_stage
    assert context.cards[0].name == "强原文轻改规则"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_models.py::test_source_strength_profile_model_accepts_light_strong_profile tests/test_models.py::test_methodology_card_defaults_to_draft_and_tracks_stage -q
```

Expected: FAIL with `ImportError` for the new schema names.

- [ ] **Step 3: Add model schemas**

Insert these classes in `src/novel_drama_engine/models.py` after `GenerationVariant`:

```python
class SourceStrengthLevel(StrEnum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class AdaptationIntensity(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class MethodologyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class MethodologyStage(StrEnum):
    SOURCE_ANALYSIS = "source_analysis"
    VIRAL_ASSET = "viral_asset"
    EPISODE_CONTEXT = "episode_context"
    STORY_BIBLE = "story_bible"
    SERIES_STRUCTURE = "series_structure"
    EPISODE_PLAN = "episode_plan"
    SCRIPT_GENERATION = "script_generation"
    QUALITY_GATE = "quality_gate"


class MethodologySource(BaseModel):
    id: str
    title: str
    source_type: str
    raw_text: str
    origin_path: str | None = None
    status: MethodologyStatus = MethodologyStatus.DRAFT
    created_at: str | None = None
    updated_at: str | None = None


class MethodologyCard(BaseModel):
    id: str
    source_id: str
    name: str
    category: str
    applies_to_channel: list[str] = Field(default_factory=list)
    applies_to_genre: list[str] = Field(default_factory=list)
    applies_to_stage: list[MethodologyStage] = Field(default_factory=list)
    trigger: str
    generation_rule: str
    quality_rule: str
    positive_examples: list[str] = Field(default_factory=list)
    negative_examples: list[str] = Field(default_factory=list)
    status: MethodologyStatus = MethodologyStatus.DRAFT
    version: int = Field(default=1, ge=1)


class SourceStrengthProfile(BaseModel):
    conflict_strength: int = Field(ge=0, le=10)
    hook_strength: int = Field(ge=0, le=10)
    character_tag_strength: int = Field(ge=0, le=10)
    emotion_asset_strength: int = Field(ge=0, le=10)
    signature_scene_strength: int = Field(ge=0, le=10)
    visualization_readiness: int = Field(ge=0, le=10)
    overall_level: SourceStrengthLevel
    recommended_intensity: AdaptationIntensity
    reasons: list[str] = Field(default_factory=list)


class MethodologyContext(BaseModel):
    source_strength_level: SourceStrengthLevel
    adaptation_intensity: AdaptationIntensity
    cards: list[MethodologyCard] = Field(default_factory=list)


class MethodologyQualityIssue(BaseModel):
    card_id: str
    card_name: str
    severity: Literal["advisory", "blocking"]
    episode: int | None = None
    message: str
    evidence: list[str] = Field(default_factory=list)


class MethodologyQualityReport(BaseModel):
    issues: list[MethodologyQualityIssue] = Field(default_factory=list)
    rewrite_instruction: str = ""
```

Then extend `RuntimeReport` in `src/novel_drama_engine/models.py`:

```python
class RuntimeReport(BaseModel):
    generation_variant: GenerationVariant
    repair_budget: str
    total_duration_ms: int = Field(ge=0)
    stages: list[PipelineStageMetric] = Field(default_factory=list)
    llm_calls: list[LLMCallMetric] = Field(default_factory=list)
    methodology_cards: list[str] = Field(default_factory=list)
```

Then extend `RoundResult`:

```python
class RoundResult(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    source_analysis: SourceAnalysis
    episode_context: EpisodeContext
    viral_asset_report: ViralAssetReport | None = None
    source_strength_profile: SourceStrengthProfile | None = None
    methodology_context: MethodologyContext | None = None
    story_bible: StoryBible
    series_structure_plan: SeriesStructurePlan | None = None
    episode_plan: EpisodePlan | None = None
    script_batch: ScriptBatch
    quality_report: QualityReport
    next_round_context: NextRoundContext
    adaptation_quality_report: AdaptationQualityReport | None = None
    methodology_quality_report: MethodologyQualityReport | None = None
    story_state_ledger: StoryStateLedger | None = None
    runtime_report: RuntimeReport | None = None
```

- [ ] **Step 4: Add seed methodology fixture files**

Create `examples/methodology_sources/strong_source_light_adaptation.md`:

```markdown
# 强原文轻改规则

当小说原文本身已经具备强冲突、强钩子、强反差、强人设和高情绪名场面时，不要大改。

生成规则：
- 保留原文主动方、因果顺序、核心决定时机、强钩子和名场面。
- 只做视听化、镜头补强、短台词化、低价值段落压缩和断点精修。
- 原文的克制、冰冷、决绝不能改成歇斯底里。

质检规则：
- 删除 C1 名场面必须阻断。
- 改变 C0 主动方、动机或决定时机必须阻断。
- 新增会改变剧情解法的道具、狠话或动作必须阻断。
```

Create `examples/methodology_cards.json`:

```json
[
  {
    "id": "method_card_strong_source_light_v1",
    "source_id": "method_source_strong_source_light_v1",
    "name": "强原文轻改规则",
    "category": "source_fidelity",
    "applies_to_channel": ["female", "male", "mixed"],
    "applies_to_genre": ["revenge", "identity", "billionaire", "male_counterattack", "unknown"],
    "applies_to_stage": ["episode_plan", "script_generation", "quality_gate"],
    "trigger": "原文已具备强冲突、强钩子、强反差或高情绪名场面",
    "generation_rule": "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩、镜头补强和短台词化。",
    "quality_rule": "如果脚本删除 C1 名场面、改变 C0 主动方、把克制情绪改成歇斯底里或新增 C4 编造道具/动作/狠话，必须 needs_rewrite。",
    "positive_examples": ["保留原著暧昧危险开场，用遮挡、手部、衣料和反应特写合规视听化。"],
    "negative_examples": ["把原文预谋解约改成现场赌气解约。"],
    "status": "active",
    "version": 1
  }
]
```

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
python3 -m pytest tests/test_models.py::test_source_strength_profile_model_accepts_light_strong_profile tests/test_models.py::test_methodology_card_defaults_to_draft_and_tracks_stage -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/novel_drama_engine/models.py src/novel_drama_engine/demo.py examples/methodology_sources/strong_source_light_adaptation.md examples/methodology_cards.json tests/test_models.py
git commit -m "Add methodology engine schemas"
```

---

## Task 2: Source Strength Classifier

**Files:**
- Create: `src/novel_drama_engine/source_strength.py`
- Modify: `src/novel_drama_engine/pipeline.py`
- Modify: `src/novel_drama_engine/demo.py`
- Test: `tests/test_source_strength.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing source-strength tests**

Create `tests/test_source_strength.py`:

```python
from novel_drama_engine.models import (
    AdaptationIntensity,
    SourceAnalysis,
    SourceStrengthLevel,
    ViralAssetReport,
)
from novel_drama_engine.source_strength import classify_source_strength


def viral_report(signature_scenes=None, small_highlights=None):
    return ViralAssetReport(
        channel="female",
        genre_tags=["revenge", "identity"],
        core_setting="娱乐圈颁奖礼背叛",
        core_dilemma="女主台下被羞辱，台上替身获奖",
        protagonist_goal="体面离开并完成反击",
        main_conflict="情人背叛与公开羞辱",
        signature_scenes=signature_scenes
        or ["危险暧昧开场", "台上光鲜台下狼狈", "提前准备解约协议"],
        small_highlights=small_highlights
        or ["镜头扫过手", "害怕被拍", "获奖僵住", "心碎 OS", "冷静离开"],
        golden_lines=["给你准备了惊喜"],
        emotion_curve=["危险", "期待", "羞辱", "心碎", "决绝"],
        adaptation_risks=[],
        risk_treatments=[],
        low_value_removal_rules=[],
    )


def test_classify_strong_source_recommends_light_adaptation():
    analysis = SourceAnalysis(
        characters=["林挽清", "路淮北", "许念念"],
        events=["颁奖礼后台暧昧压迫", "许念念获奖", "林挽清早已准备解约"],
        conflicts=["公开背叛", "台上台下强反差", "情人主动羞辱"],
        visual_moments=["抱坐腿上害怕镜头拍到", "台上光鲜台下狼狈", "解约协议放在办公室"],
        low_value_passages=["日常寒暄"],
        candidate_hooks=["谁敢碰她一下", "镜头快扫到两人"],
    )

    profile = classify_source_strength(analysis, viral_report())

    assert profile.overall_level == SourceStrengthLevel.STRONG
    assert profile.recommended_intensity == AdaptationIntensity.LIGHT
    assert profile.hook_strength >= 8
    assert any("强钩子" in reason for reason in profile.reasons)


def test_classify_weak_source_recommends_heavy_adaptation():
    analysis = SourceAnalysis(
        characters=["小夏"],
        events=["她回到家"],
        conflicts=[],
        visual_moments=[],
        low_value_passages=["大量日常吃饭聊天"],
        candidate_hooks=[],
    )

    profile = classify_source_strength(analysis, None)

    assert profile.overall_level == SourceStrengthLevel.WEAK
    assert profile.recommended_intensity == AdaptationIntensity.HEAVY
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_source_strength.py -q
```

Expected: FAIL with `ModuleNotFoundError: novel_drama_engine.source_strength`.

- [ ] **Step 3: Implement deterministic classifier**

Create `src/novel_drama_engine/source_strength.py`:

```python
from __future__ import annotations

from novel_drama_engine.models import (
    AdaptationIntensity,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    ViralAssetReport,
)

STRONG_HOOK_TOKENS = (
    "羞辱",
    "背叛",
    "当众",
    "镜头",
    "获奖",
    "解约",
    "危险",
    "暧昧",
    "压迫",
    "身份",
    "真相",
    "反转",
)


def _score_count(count: int, *, strong_at: int) -> int:
    if count <= 0:
        return 0
    return min(10, round((count / strong_at) * 10))


def _token_score(items: list[str], tokens: tuple[str, ...]) -> int:
    text = "\n".join(items)
    hits = sum(1 for token in tokens if token in text)
    return min(10, hits * 2)


def classify_source_strength(
    source_analysis: SourceAnalysis,
    viral_asset_report: ViralAssetReport | None = None,
) -> SourceStrengthProfile:
    conflict_strength = max(
        _score_count(len(source_analysis.conflicts), strong_at=4),
        _token_score(source_analysis.conflicts, STRONG_HOOK_TOKENS),
    )
    hook_strength = max(
        _score_count(len(source_analysis.candidate_hooks), strong_at=3),
        _token_score(source_analysis.candidate_hooks, STRONG_HOOK_TOKENS),
    )
    character_tag_strength = _score_count(len(source_analysis.characters), strong_at=4)
    emotion_asset_strength = _score_count(
        len(viral_asset_report.emotion_curve) if viral_asset_report else 0,
        strong_at=5,
    )
    signature_scene_strength = max(
        _score_count(len(source_analysis.visual_moments), strong_at=4),
        _score_count(len(viral_asset_report.signature_scenes) if viral_asset_report else 0, strong_at=3),
    )
    visualization_readiness = _score_count(len(source_analysis.visual_moments), strong_at=5)

    average = round(
        (
            conflict_strength
            + hook_strength
            + character_tag_strength
            + emotion_asset_strength
            + signature_scene_strength
            + visualization_readiness
        )
        / 6
    )
    reasons: list[str] = []
    if hook_strength >= 8:
        reasons.append("原文已有强钩子，优先保护核心张力。")
    if signature_scene_strength >= 8:
        reasons.append("原文已有高价值名场面，适合轻改视听化。")
    if conflict_strength >= 8:
        reasons.append("原文冲突密度高，不应重构主动方和因果链。")
    if average >= 7 or (hook_strength >= 8 and signature_scene_strength >= 8):
        level = SourceStrengthLevel.STRONG
        intensity = AdaptationIntensity.LIGHT
    elif average >= 4:
        level = SourceStrengthLevel.MEDIUM
        intensity = AdaptationIntensity.MEDIUM
        reasons.append("原文有可用设定或冲突，但需要节奏优化。")
    else:
        level = SourceStrengthLevel.WEAK
        intensity = AdaptationIntensity.HEAVY
        reasons.append("原文短剧资产不足，需要更强结构重构。")

    return SourceStrengthProfile(
        conflict_strength=conflict_strength,
        hook_strength=hook_strength,
        character_tag_strength=character_tag_strength,
        emotion_asset_strength=emotion_asset_strength,
        signature_scene_strength=signature_scene_strength,
        visualization_readiness=visualization_readiness,
        overall_level=level,
        recommended_intensity=intensity,
        reasons=reasons,
    )
```

- [ ] **Step 4: Integrate classifier into pipeline artifacts**

In `src/novel_drama_engine/pipeline.py`, import:

```python
from novel_drama_engine.source_strength import classify_source_strength
```

After `viral_asset_report` is resolved and before `cached_episode_context`, add:

```python
        source_strength_profile = cached_stage(
            "source_strength_profile",
            "source_strength_profile",
            SourceStrengthProfile,
            lambda: classify_source_strength(source_analysis, viral_asset_report),
        )
```

Also import `SourceStrengthProfile` from `novel_drama_engine.models`.

When constructing `RoundResult`, include:

```python
            source_strength_profile=source_strength_profile,
```

- [ ] **Step 5: Add pipeline test for artifact persistence**

Append to `tests/test_pipeline.py`:

```python
def test_pipeline_persists_source_strength_profile(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.source_strength_profile is not None
    assert result.source_strength_profile.recommended_intensity in {"light", "medium", "heavy"}
    assert (tmp_path / "round_001" / "source_strength_profile.json").exists()
```

- [ ] **Step 6: Run tests**

Run:

```bash
python3 -m pytest tests/test_source_strength.py tests/test_pipeline.py::test_pipeline_persists_source_strength_profile -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/novel_drama_engine/source_strength.py src/novel_drama_engine/pipeline.py tests/test_source_strength.py tests/test_pipeline.py
git commit -m "Add source strength classifier"
```

---

## Task 3: Methodology Card Ingest and Retrieval

**Files:**
- Create: `src/novel_drama_engine/methodology.py`
- Modify: `src/novel_drama_engine/cli.py`
- Test: `tests/test_methodology.py`

- [ ] **Step 1: Write failing methodology tests**

Create `tests/test_methodology.py`:

```python
from pathlib import Path

from novel_drama_engine.methodology import (
    extract_method_cards,
    load_methodology_cards,
    retrieve_methodology_context,
    render_methodology_context,
)
from novel_drama_engine.models import (
    AdaptationIntensity,
    MethodologyCard,
    MethodologySource,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
    SourceStrengthProfile,
)


def test_extract_method_cards_creates_draft_card_from_source_text():
    source = MethodologySource(
        id="method_source_001",
        title="强原文轻改规则",
        source_type="sop",
        raw_text="强原文轻改。生成规则：保留主动方。质检规则：删除名场面必须阻断。",
    )

    cards = extract_method_cards(source)

    assert len(cards) == 1
    assert cards[0].status == MethodologyStatus.DRAFT
    assert cards[0].source_id == source.id
    assert "保留主动方" in cards[0].generation_rule


def test_retrieve_methodology_context_uses_active_stage_cards_only(tmp_path):
    card_path = tmp_path / "cards.json"
    card_path.write_text(
        MethodologyCard(
            id="active_card",
            source_id="source",
            name="强原文轻改规则",
            category="source_fidelity",
            applies_to_channel=["female"],
            applies_to_genre=["identity"],
            applies_to_stage=[MethodologyStage.SCRIPT_GENERATION],
            trigger="强原文",
            generation_rule="轻改",
            quality_rule="不改 C0",
            status=MethodologyStatus.ACTIVE,
        ).model_dump_json(),
        encoding="utf-8",
    )
    profile = SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=9,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["强钩子"],
    )

    cards = load_methodology_cards(card_path)
    context = retrieve_methodology_context(
        cards,
        stage=MethodologyStage.SCRIPT_GENERATION,
        channel="female",
        genre_tags=["identity"],
        source_strength_profile=profile,
    )

    assert [card.id for card in context.cards] == ["active_card"]
    assert context.adaptation_intensity == AdaptationIntensity.LIGHT
    assert "强原文轻改规则" in render_methodology_context(context)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_methodology.py -q
```

Expected: FAIL with `ModuleNotFoundError: novel_drama_engine.methodology`.

- [ ] **Step 3: Implement methodology helpers**

Create `src/novel_drama_engine/methodology.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from novel_drama_engine.models import (
    MethodologyCard,
    MethodologyContext,
    MethodologySource,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthProfile,
)


def extract_method_cards(source: MethodologySource) -> list[MethodologyCard]:
    text = source.raw_text.strip()
    generation_rule = "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩和镜头补强。"
    quality_rule = "删除 C1 名场面、改变 C0 主动方或新增 C4 编造内容时必须阻断。"
    if "生成规则" in text:
        generation_rule = text.split("生成规则", 1)[1].split("质检规则", 1)[0].strip("：: \n-")
    if "质检规则" in text:
        quality_rule = text.split("质检规则", 1)[1].strip("：: \n-")
    return [
        MethodologyCard(
            id=f"{source.id}_card_001",
            source_id=source.id,
            name=source.title,
            category="source_fidelity",
            applies_to_channel=["female", "male", "mixed"],
            applies_to_genre=["unknown"],
            applies_to_stage=[
                MethodologyStage.EPISODE_PLAN,
                MethodologyStage.SCRIPT_GENERATION,
                MethodologyStage.QUALITY_GATE,
            ],
            trigger="原文具备强冲突、强钩子、强反差或高情绪名场面",
            generation_rule=generation_rule,
            quality_rule=quality_rule,
        )
    ]


def load_methodology_cards(path: Path | str | None) -> list[MethodologyCard]:
    if path is None:
        default_path = Path("examples/methodology_cards.json")
        path = default_path if default_path.exists() else None
    if path is None:
        return []
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = [raw]
    return [MethodologyCard.model_validate(item) for item in raw]


def _matches(values: list[str], requested: list[str]) -> bool:
    if not values or "unknown" in values:
        return True
    return bool(set(values) & set(requested))


def retrieve_methodology_context(
    cards: list[MethodologyCard],
    *,
    stage: MethodologyStage,
    channel: str,
    genre_tags: list[str],
    source_strength_profile: SourceStrengthProfile,
    limit: int = 5,
) -> MethodologyContext:
    active_cards = [
        card
        for card in cards
        if card.status == MethodologyStatus.ACTIVE
        and stage in card.applies_to_stage
        and _matches(card.applies_to_channel, [channel, "mixed"])
        and _matches(card.applies_to_genre, [*genre_tags, "unknown"])
    ]
    active_cards.sort(
        key=lambda card: (
            0 if card.category == "source_fidelity" else 1,
            -card.version,
            card.name,
        )
    )
    return MethodologyContext(
        source_strength_level=source_strength_profile.overall_level,
        adaptation_intensity=source_strength_profile.recommended_intensity,
        cards=active_cards[:limit],
    )


def render_methodology_context(context: MethodologyContext | None) -> str:
    if context is None or not context.cards:
        return "内部方法论卡：无"
    blocks = [
        (
            f"- 名称：{card.name}\n"
            f"  触发条件：{card.trigger}\n"
            f"  本阶段生成规则：{card.generation_rule}\n"
            f"  本阶段质检规则：{card.quality_rule}"
        )
        for card in context.cards
    ]
    return "\n".join(
        [
            f"原文强度：{context.source_strength_level.value}",
            f"改编强度：{context.adaptation_intensity.value}",
            "内部方法论卡：",
            *blocks,
        ]
    )
```

- [ ] **Step 4: Add CLI option for methodology card path**

In `src/novel_drama_engine/cli.py`, add run option:

```python
    methodology_cards: Annotated[
        Optional[Path],
        typer.Option(
            "--methodology-cards",
            exists=True,
            readable=True,
            help="Optional methodology card JSON file.",
        ),
    ] = None,
```

Pass it to `RoundPipeline.run(...)` as:

```python
            methodology_cards_path=methodology_cards,
```

In Task 4, `RoundPipeline.run` will accept this argument.

- [ ] **Step 5: Run tests**

Run:

```bash
python3 -m pytest tests/test_methodology.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/novel_drama_engine/methodology.py src/novel_drama_engine/cli.py tests/test_methodology.py
git commit -m "Add methodology card retrieval"
```

---

## Task 4: Prompt Injection and Pipeline Context

**Files:**
- Modify: `src/novel_drama_engine/prompts.py`
- Modify: `src/novel_drama_engine/rounds.py`
- Modify: `src/novel_drama_engine/pipeline.py`
- Modify: `src/novel_drama_engine/demo.py`
- Test: `tests/test_prompts.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing prompt test**

Append to `tests/test_prompts.py`:

```python
from novel_drama_engine.models import (
    AdaptationIntensity,
    MethodologyCard,
    MethodologyContext,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
)


def test_script_prompt_includes_internal_methodology_without_user_strategy_selector():
    outputs = demo_round_outputs(include_sop_stack=True, include_episode_plan=True, target_episode_count=30)
    source_analysis, episode_context, story_bible, viral_asset, series_plan, episode_plan = (
        outputs[0],
        outputs[1],
        outputs[2],
        outputs[3],
        outputs[4],
        outputs[5],
    )
    context = MethodologyContext(
        source_strength_level=SourceStrengthLevel.STRONG,
        adaptation_intensity=AdaptationIntensity.LIGHT,
        cards=[
            MethodologyCard(
                id="card",
                source_id="source",
                name="强原文轻改规则",
                category="source_fidelity",
                applies_to_stage=[MethodologyStage.SCRIPT_GENERATION],
                trigger="强原文",
                generation_rule="只做视听化和镜头补强。",
                quality_rule="删除 C1 名场面必须阻断。",
                status=MethodologyStatus.ACTIVE,
            )
        ],
    )

    prompt = prompts.script_user(
        "原文已有强开场。",
        source_analysis,
        episode_context,
        story_bible,
        None,
        "",
        episode_plan=episode_plan,
        viral_asset_report=viral_asset,
        series_structure_plan=series_plan,
        methodology_context=context,
    )

    assert "内部方法论卡" in prompt
    assert "强原文轻改规则" in prompt
    assert "只做视听化和镜头补强" in prompt
    assert "用户选择方法论" not in prompt
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_prompts.py::test_script_prompt_includes_internal_methodology_without_user_strategy_selector -q
```

Expected: FAIL with `TypeError` for unexpected `methodology_context`.

- [ ] **Step 3: Add prompt rendering**

In `src/novel_drama_engine/prompts.py`, import:

```python
from novel_drama_engine.methodology import render_methodology_context
from novel_drama_engine.models import MethodologyContext
```

Add optional `methodology_context: MethodologyContext | None = None` to:

- `episode_context_user`
- `bible_user`
- `series_structure_user`
- `episode_plan_user`
- `script_user`
- `script_episode_user`
- `quality_user`
- `episode_repair_user`

In each prompt block, add:

```python
        section("内部方法论", render_methodology_context(methodology_context)),
```

Place it after `section("全局框架", GLOBAL_PROFESSIONAL_FRAME)` so it is visible but not confused with user input.

- [ ] **Step 4: Thread methodology context through stage classes**

In `src/novel_drama_engine/rounds.py`, import `MethodologyContext` and add optional `methodology_context` to class methods that call the prompt functions:

```python
    def run(
        self,
        source_text: str,
        previous_context: NextRoundContext | None,
        source_analysis: SourceAnalysis,
        round_number: int = 1,
        target_episode_count: int | None = None,
        episodes_per_round: int = 5,
        viral_asset_report: ViralAssetReport | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> EpisodeContext:
```

Pass `methodology_context=methodology_context` into `prompts.episode_context_user(...)`.

Repeat the same pattern for:

- `InternalBibleBuilder.run`
- `SeriesStructurePlanner.run`
- `EpisodeBeatPlanner.run`
- `ScriptBatchGenerator.run`
- `ScriptBatchGenerator.run_episode_batch`
- `ScriptBatchGenerator.run_episode`
- `ContinuityBoomChecker.run`

- [ ] **Step 5: Retrieve methodology context in pipeline**

In `src/novel_drama_engine/pipeline.py`, import:

```python
from pathlib import Path
from novel_drama_engine.methodology import load_methodology_cards, retrieve_methodology_context
from novel_drama_engine.models import MethodologyContext, MethodologyStage, SourceStrengthProfile
```

Add `methodology_cards_path: Path | str | None = None` to `RoundPipeline.run`.

After `source_strength_profile`, add:

```python
        methodology_cards = load_methodology_cards(
            Path(methodology_cards_path) if methodology_cards_path else None
        )

        def methodology_context_for(stage: MethodologyStage) -> MethodologyContext:
            channel = viral_asset_report.channel if viral_asset_report else "mixed"
            genre_tags = viral_asset_report.genre_tags if viral_asset_report else ["unknown"]
            return retrieve_methodology_context(
                methodology_cards,
                stage=stage,
                channel=channel,
                genre_tags=genre_tags,
                source_strength_profile=source_strength_profile,
            )
```

Before each stage call, get a stage-specific context and write it once:

```python
        script_methodology_context = methodology_context_for(MethodologyStage.SCRIPT_GENERATION)
        self.store.write_round_artifact(
            round_number,
            "methodology_context",
            script_methodology_context,
        )
```

Pass the matching contexts into stage calls. Use:

- `MethodologyStage.EPISODE_CONTEXT` for `EpisodeContextResolver`.
- `MethodologyStage.STORY_BIBLE` for `InternalBibleBuilder`.
- `MethodologyStage.SERIES_STRUCTURE` for `SeriesStructurePlanner`.
- `MethodologyStage.EPISODE_PLAN` for `EpisodeBeatPlanner`.
- `MethodologyStage.SCRIPT_GENERATION` for script generation and repair.
- `MethodologyStage.QUALITY_GATE` for quality checks.

In `runtime_report`, add:

```python
                methodology_cards=[
                    card.id for card in script_methodology_context.cards
                ],
```

When constructing `RoundResult`, include:

```python
            methodology_context=script_methodology_context,
```

- [ ] **Step 6: Add pipeline test**

Append to `tests/test_pipeline.py`:

```python
def test_pipeline_writes_methodology_context_artifact(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True, include_episode_plan=True, target_episode_count=30)
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚在颁奖礼后台被公开羞辱，台上许念念光鲜获奖。",
        target_episode_count=30,
        generation_variant=GenerationVariant.SOP_FULL_STACK,
    )

    assert result.methodology_context is not None
    assert any(card.status == "active" for card in result.methodology_context.cards)
    assert (tmp_path / "round_001" / "methodology_context.json").exists()
```

- [ ] **Step 7: Run tests**

Run:

```bash
python3 -m pytest tests/test_prompts.py::test_script_prompt_includes_internal_methodology_without_user_strategy_selector tests/test_pipeline.py::test_pipeline_writes_methodology_context_artifact -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/novel_drama_engine/prompts.py src/novel_drama_engine/rounds.py src/novel_drama_engine/pipeline.py src/novel_drama_engine/demo.py tests/test_prompts.py tests/test_pipeline.py
git commit -m "Inject methodology context into generation"
```

---

## Task 5: Strong-Source Quality Gate

**Files:**
- Modify: `src/novel_drama_engine/adaptation_quality.py`
- Modify: `src/novel_drama_engine/pipeline.py`
- Test: `tests/test_adaptation_quality.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing quality test**

Append to `tests/test_adaptation_quality.py`:

```python
from novel_drama_engine.models import (
    AdaptationIntensity,
    MethodologyCard,
    MethodologyContext,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
    SourceStrengthProfile,
)
from novel_drama_engine.adaptation_quality import build_methodology_quality_report


def test_methodology_quality_blocks_strong_source_hook_loss():
    analysis = make_source_analysis(hook="后台镜头快扫到她坐在他腿上")
    bible = make_bible()
    episode = make_episode(
        episode=1,
        title="平淡颁奖礼",
        first_action="△中近景推近林挽清站在走廊里，灯光平静，切到她低头看手机。",
        final_line="她转身离开。",
    )
    script_batch = ScriptBatch(episodes=[episode])
    profile = SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=9,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["强钩子"],
    )
    context = MethodologyContext(
        source_strength_level=SourceStrengthLevel.STRONG,
        adaptation_intensity=AdaptationIntensity.LIGHT,
        cards=[
            MethodologyCard(
                id="card",
                source_id="source",
                name="强原文轻改规则",
                category="source_fidelity",
                applies_to_stage=[MethodologyStage.QUALITY_GATE],
                trigger="强原文",
                generation_rule="轻改",
                quality_rule="删除 C1 名场面必须阻断。",
                status=MethodologyStatus.ACTIVE,
            )
        ],
    )

    report = build_methodology_quality_report(
        source_analysis=analysis,
        story_bible=bible,
        script_batch=script_batch,
        source_strength_profile=profile,
        methodology_context=context,
    )

    assert report.issues
    assert report.issues[0].severity == "blocking"
    assert "强原文" in report.rewrite_instruction
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_adaptation_quality.py::test_methodology_quality_blocks_strong_source_hook_loss -q
```

Expected: FAIL with `ImportError` for `build_methodology_quality_report`.

- [ ] **Step 3: Implement methodology quality report**

In `src/novel_drama_engine/adaptation_quality.py`, import:

```python
from novel_drama_engine.models import (
    MethodologyContext,
    MethodologyQualityIssue,
    MethodologyQualityReport,
    SourceStrengthProfile,
    SourceStrengthLevel,
    AdaptationIntensity,
)
```

Add:

```python
def build_methodology_quality_report(
    *,
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    source_strength_profile: SourceStrengthProfile | None,
    methodology_context: MethodologyContext | None,
) -> MethodologyQualityReport:
    if source_strength_profile is None or methodology_context is None:
        return MethodologyQualityReport()
    if (
        source_strength_profile.overall_level != SourceStrengthLevel.STRONG
        or source_strength_profile.recommended_intensity != AdaptationIntensity.LIGHT
    ):
        return MethodologyQualityReport()

    script_text = _all_script_text(script_batch)
    issues: list[MethodologyQualityIssue] = []
    source_hooks = [hook for hook in source_analysis.candidate_hooks if hook.strip()]
    source_visuals = [moment for moment in source_analysis.visual_moments if moment.strip()]
    protected_assets = [*source_hooks, *source_visuals]

    for asset in protected_assets:
        anchor = asset[:12]
        if anchor and anchor not in script_text:
            card = methodology_context.cards[0] if methodology_context.cards else None
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id if card else "source_strength_light",
                    card_name=card.name if card else "强原文轻改规则",
                    severity="blocking",
                    message=f"强原文轻改模式下疑似丢失 C1 原文资产：{asset}",
                    evidence=[asset],
                )
            )
            break

    rewrite_instruction = ""
    if issues:
        rewrite_instruction = (
            "强原文轻改失败：必须回到原文 C1 强钩子/名场面，保留主动方和因果顺序，"
            "只做视听化、镜头补强、短台词化，不要用新道具或新狠话替代原文资产。"
        )
    return MethodologyQualityReport(issues=issues, rewrite_instruction=rewrite_instruction)
```

- [ ] **Step 4: Integrate report into pipeline**

In `src/novel_drama_engine/pipeline.py`, import:

```python
from novel_drama_engine.adaptation_quality import build_methodology_quality_report
```

After `adaptation_quality_report` is written, add:

```python
        methodology_quality_report = run_stage(
            "methodology_quality_report",
            lambda: build_methodology_quality_report(
                source_analysis=source_analysis,
                story_bible=story_bible,
                script_batch=script_batch,
                source_strength_profile=source_strength_profile,
                methodology_context=methodology_context_for(MethodologyStage.QUALITY_GATE),
            ),
        )
        self.store.write_round_artifact(
            round_number,
            "methodology_quality_report",
            methodology_quality_report,
        )
        if methodology_quality_report.issues:
            quality_report = run_stage(
                "merge_methodology_quality",
                lambda: quality_report.model_copy(
                    update={
                        "status": QualityStatus.NEEDS_REWRITE,
                        "blocking_issues": [
                            *quality_report.blocking_issues,
                            *[issue.message for issue in methodology_quality_report.issues],
                        ],
                        "rewrite_instruction": methodology_quality_report.rewrite_instruction
                        or quality_report.rewrite_instruction,
                    }
                ),
            )
            self.store.write_round_artifact(round_number, "quality_report", quality_report)
```

Include in `RoundResult`:

```python
            methodology_quality_report=methodology_quality_report,
```

- [ ] **Step 5: Run quality tests**

Run:

```bash
python3 -m pytest tests/test_adaptation_quality.py::test_methodology_quality_blocks_strong_source_hook_loss -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/novel_drama_engine/adaptation_quality.py src/novel_drama_engine/pipeline.py tests/test_adaptation_quality.py
git commit -m "Add strong source methodology quality gate"
```

---

## Task 6: Internal Methodology DB, API, and UI

**Files:**
- Modify: `src/db/schema.ts`
- Create: Drizzle migration via `npm run db:generate`
- Create: `src/lib/methodology.ts`
- Create: `src/app/api/methodology/route.ts`
- Create: `src/app/api/methodology/cards/[id]/route.ts`
- Create: `src/app/methodology/page.tsx`
- Create: `src/app/methodology/MethodologyClient.tsx`
- Modify: `src/components/app-shell.tsx`

- [ ] **Step 1: Add schema tables**

In `src/db/schema.ts`, add after `usageEvents`:

```ts
export const methodologySources = sqliteTable("methodology_sources", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  sourceType: text("source_type").notNull(),
  rawText: text("raw_text").notNull(),
  originPath: text("origin_path"),
  status: text("status", {
    enum: ["draft", "active", "archived", "rejected"],
  })
    .notNull()
    .default("draft"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const methodologyCards = sqliteTable("methodology_cards", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  sourceId: text("source_id")
    .notNull()
    .references(() => methodologySources.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  category: text("category").notNull(),
  appliesToChannelJson: text("applies_to_channel_json").notNull(),
  appliesToGenreJson: text("applies_to_genre_json").notNull(),
  appliesToStageJson: text("applies_to_stage_json").notNull(),
  trigger: text("trigger").notNull(),
  generationRule: text("generation_rule").notNull(),
  qualityRule: text("quality_rule").notNull(),
  positiveExamplesJson: text("positive_examples_json"),
  negativeExamplesJson: text("negative_examples_json"),
  status: text("status", {
    enum: ["draft", "active", "archived", "rejected"],
  })
    .notNull()
    .default("draft"),
  version: integer("version").notNull().default(1),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const methodologyRuns = sqliteTable("methodology_runs", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  projectId: text("project_id").references(() => projects.id, { onDelete: "cascade" }),
  roundId: text("round_id").references(() => rounds.id, { onDelete: "set null" }),
  sourceStrengthJson: text("source_strength_json"),
  methodologyContextJson: text("methodology_context_json"),
  methodologyQualityJson: text("methodology_quality_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});
```

- [ ] **Step 2: Generate migration**

Run:

```bash
npm run db:generate
```

Expected: a new `drizzle/migrations/0007_*.sql` plus metadata snapshot.

- [ ] **Step 3: Implement TypeScript data layer**

Create `src/lib/methodology.ts`:

```ts
import { desc, eq } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";

export type MethodologyStatus = "draft" | "active" | "archived" | "rejected";

export type MethodologyCardView = {
  id: string;
  sourceId: string;
  name: string;
  category: string;
  status: MethodologyStatus;
  appliesToChannel: string[];
  appliesToGenre: string[];
  appliesToStage: string[];
  trigger: string;
  generationRule: string;
  qualityRule: string;
  positiveExamples: string[];
  negativeExamples: string[];
  version: number;
};

export type MethodologySourceView = {
  id: string;
  title: string;
  sourceType: string;
  rawText: string;
  originPath: string | null;
  status: MethodologyStatus;
  cardCount: number;
  createdAt: number;
  updatedAt: number;
};

function parseArray(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

function cardToView(row: typeof schema.methodologyCards.$inferSelect): MethodologyCardView {
  return {
    id: row.id,
    sourceId: row.sourceId,
    name: row.name,
    category: row.category,
    status: row.status,
    appliesToChannel: parseArray(row.appliesToChannelJson),
    appliesToGenre: parseArray(row.appliesToGenreJson),
    appliesToStage: parseArray(row.appliesToStageJson),
    trigger: row.trigger,
    generationRule: row.generationRule,
    qualityRule: row.qualityRule,
    positiveExamples: parseArray(row.positiveExamplesJson),
    negativeExamples: parseArray(row.negativeExamplesJson),
    version: row.version,
  };
}

export async function listMethodology() {
  const [sources, cards] = await Promise.all([
    db.query.methodologySources.findMany({
      orderBy: [desc(schema.methodologySources.updatedAt)],
    }),
    db.query.methodologyCards.findMany({
      orderBy: [desc(schema.methodologyCards.updatedAt)],
    }),
  ]);
  const countBySource = new Map<string, number>();
  for (const card of cards) {
    countBySource.set(card.sourceId, (countBySource.get(card.sourceId) || 0) + 1);
  }
  return {
    sources: sources.map((source) => ({
      id: source.id,
      title: source.title,
      sourceType: source.sourceType,
      rawText: source.rawText,
      originPath: source.originPath,
      status: source.status,
      cardCount: countBySource.get(source.id) || 0,
      createdAt: source.createdAt.getTime(),
      updatedAt: source.updatedAt.getTime(),
    })),
    cards: cards.map(cardToView),
  };
}

export async function createMethodologySource(input: {
  title: string;
  sourceType: string;
  rawText: string;
  originPath?: string | null;
}) {
  const now = new Date();
  const sourceId = uuid();
  await db.insert(schema.methodologySources).values({
    id: sourceId,
    title: input.title,
    sourceType: input.sourceType,
    rawText: input.rawText,
    originPath: input.originPath || null,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });
  const cardId = uuid();
  await db.insert(schema.methodologyCards).values({
    id: cardId,
    sourceId,
    name: input.title,
    category: "source_fidelity",
    appliesToChannelJson: JSON.stringify(["female", "male", "mixed"]),
    appliesToGenreJson: JSON.stringify(["unknown"]),
    appliesToStageJson: JSON.stringify(["episode_plan", "script_generation", "quality_gate"]),
    trigger: "原文具备强冲突、强钩子、强反差或高情绪名场面",
    generationRule: "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩、镜头补强和短台词化。",
    qualityRule: "删除 C1 名场面、改变 C0 主动方或新增 C4 编造内容时必须阻断。",
    positiveExamplesJson: JSON.stringify([]),
    negativeExamplesJson: JSON.stringify([]),
    status: "draft",
    version: 1,
    createdAt: now,
    updatedAt: now,
  });
  return { sourceId, cardId };
}

export async function updateMethodologyCardStatus(id: string, status: MethodologyStatus) {
  await db
    .update(schema.methodologyCards)
    .set({ status, updatedAt: new Date() })
    .where(eq(schema.methodologyCards.id, id));
}
```

- [ ] **Step 4: Implement API routes**

Create `src/app/api/methodology/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";
import {
  createMethodologySource,
  listMethodology,
} from "@/lib/methodology";

export async function GET() {
  return NextResponse.json(await listMethodology());
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as {
    title?: string;
    sourceType?: string;
    rawText?: string;
    originPath?: string | null;
  };
  if (!body.title?.trim() || !body.rawText?.trim()) {
    return NextResponse.json({ error: "missing title or rawText" }, { status: 400 });
  }
  const result = await createMethodologySource({
    title: body.title.trim(),
    sourceType: body.sourceType?.trim() || "sop",
    rawText: body.rawText,
    originPath: body.originPath || null,
  });
  return NextResponse.json(result);
}
```

Create `src/app/api/methodology/cards/[id]/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";
import {
  type MethodologyStatus,
  updateMethodologyCardStatus,
} from "@/lib/methodology";

const statuses = new Set(["draft", "active", "archived", "rejected"]);

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = (await req.json()) as { status?: string };
  if (!body.status || !statuses.has(body.status)) {
    return NextResponse.json({ error: "invalid status" }, { status: 400 });
  }
  await updateMethodologyCardStatus(id, body.status as MethodologyStatus);
  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 5: Implement internal page and client**

Create `src/app/methodology/page.tsx`:

```tsx
import { listMethodology } from "@/lib/methodology";
import { MethodologyClient } from "./MethodologyClient";

export const dynamic = "force-dynamic";

export default async function MethodologyPage() {
  const data = await listMethodology();
  return <MethodologyClient initialData={data} />;
}
```

Create `src/app/methodology/MethodologyClient.tsx`:

```tsx
"use client";

import { useState } from "react";
import { BookOpen, Plus, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { MethodologyCardView, MethodologySourceView } from "@/lib/methodology";

type MethodologyData = {
  sources: MethodologySourceView[];
  cards: MethodologyCardView[];
};

export function MethodologyClient({ initialData }: { initialData: MethodologyData }) {
  const [data, setData] = useState(initialData);
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const res = await fetch("/api/methodology");
    setData((await res.json()) as MethodologyData);
  }

  async function createSource() {
    setBusy(true);
    try {
      const res = await fetch("/api/methodology", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, sourceType: "sop", rawText }),
      });
      if (!res.ok) throw new Error(await res.text());
      setTitle("");
      setRawText("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function setCardStatus(id: string, status: MethodologyCardView["status"]) {
    setBusy(true);
    try {
      const res = await fetch(`/api/methodology/cards/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error(await res.text());
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-shell">
      <header className="page-header">
        <div>
          <div className="page-kicker">Internal Knowledge</div>
          <h1 className="page-title">内部方法论</h1>
          <p className="page-description">
            这里沉淀平台内部短剧改编知识。普通用户不会看到这些配置。
          </p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={busy}>
          <RefreshCw className="size-4" />
          刷新
        </Button>
      </header>

      <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="p-5">
          <div className="flex items-center gap-2 font-semibold">
            <Plus className="size-4 text-[color:var(--reela-pink)]" />
            导入方法论
          </div>
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="方法论标题"
          />
          <Textarea
            value={rawText}
            onChange={(event) => setRawText(event.target.value)}
            placeholder="粘贴 SOP、拆剧笔记或规则片段"
            className="min-h-52"
          />
          <Button onClick={createSource} disabled={busy || !title || !rawText}>
            <BookOpen className="size-4" />
            生成 draft 方法卡
          </Button>
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="text-lg font-semibold">方法论来源</h2>
            <div className="mt-3 space-y-2">
              {data.sources.map((source) => (
                <div key={source.id} className="rounded-[var(--radius-md)] border border-border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <strong>{source.title}</strong>
                    <Badge variant="outline">{source.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {source.sourceType} · {source.cardCount} 张卡
                  </p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-lg font-semibold">方法卡</h2>
            <div className="mt-3 space-y-3">
              {data.cards.map((card) => (
                <div key={card.id} className="rounded-[var(--radius-md)] border border-border p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <strong>{card.name}</strong>
                      <p className="mt-1 text-sm text-muted-foreground">{card.trigger}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge>{card.status}</Badge>
                      {(["draft", "active", "archived", "rejected"] as const).map((status) => (
                        <Button
                          key={status}
                          size="xs"
                          variant={card.status === status ? "default" : "outline"}
                          disabled={busy}
                          onClick={() => setCardStatus(card.id, status)}
                        >
                          {status}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6">{card.generationRule}</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{card.qualityRule}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </section>
    </section>
  );
}
```

- [ ] **Step 6: Add navigation**

Modify `src/components/app-shell.tsx` imports:

```ts
  BookOpen,
```

Add nav item:

```ts
  { href: "/methodology", label: "内部方法论", icon: BookOpen },
```

Update `pageLabel`:

```ts
  if (pathname.startsWith("/methodology")) return "内部方法论";
```

- [ ] **Step 7: Build check**

Run:

```bash
npm run build
```

Expected: exit 0. Existing Turbopack NFT warning may appear; no TypeScript errors.

- [ ] **Step 8: Commit**

```bash
git add src/db/schema.ts drizzle/migrations src/lib/methodology.ts src/app/api/methodology src/app/methodology src/components/app-shell.tsx
git commit -m "Add internal methodology workspace"
```

---

## Task 7: Engine/Web Sync and End-to-End Verification

**Files:**
- Modify: `src/lib/engine-types.ts`
- Modify: `src/lib/engine-runner.ts`
- Test: `tests/test_cli.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Extend engine TypeScript types**

In `src/lib/engine-types.ts`, add:

```ts
export interface EngineSourceStrengthProfile {
  conflict_strength: number;
  hook_strength: number;
  character_tag_strength: number;
  emotion_asset_strength: number;
  signature_scene_strength: number;
  visualization_readiness: number;
  overall_level: "strong" | "medium" | "weak";
  recommended_intensity: "light" | "medium" | "heavy";
  reasons: string[];
}

export interface EngineMethodologyCard {
  id: string;
  source_id: string;
  name: string;
  category: string;
  trigger: string;
  generation_rule: string;
  quality_rule: string;
  status: "draft" | "active" | "archived" | "rejected";
  version: number;
}

export interface EngineMethodologyContext {
  source_strength_level: "strong" | "medium" | "weak";
  adaptation_intensity: "light" | "medium" | "heavy";
  cards: EngineMethodologyCard[];
}
```

Add optional fields to `EngineRoundResult`:

```ts
  source_strength_profile?: EngineSourceStrengthProfile | null;
  methodology_context?: EngineMethodologyContext | null;
  methodology_quality_report?: {
    issues: Array<{
      card_id: string;
      card_name: string;
      severity: "advisory" | "blocking";
      episode?: number | null;
      message: string;
      evidence: string[];
    }>;
    rewrite_instruction: string;
  } | null;
```

- [ ] **Step 2: Include methodology in job result**

In `src/lib/engine-runner.ts`, after reading `result`, include in `succeedJob` result:

```ts
        sourceStrength: result.source_strength_profile?.overall_level || null,
        adaptationIntensity:
          result.source_strength_profile?.recommended_intensity || null,
        methodologyCards:
          result.methodology_context?.cards?.map((card) => card.name) || [],
```

Also write methodology run rows when `result.methodology_context` exists:

```ts
  if (result.methodology_context || result.source_strength_profile) {
    await db.insert(schema.methodologyRuns).values({
      id: uuid(),
      tenantId: project.tenantId,
      projectId: project.id,
      roundId,
      sourceStrengthJson: result.source_strength_profile
        ? JSON.stringify(result.source_strength_profile)
        : null,
      methodologyContextJson: result.methodology_context
        ? JSON.stringify(result.methodology_context)
        : null,
      methodologyQualityJson: result.methodology_quality_report
        ? JSON.stringify(result.methodology_quality_report)
        : null,
      createdAt: new Date(),
    });
  }
```

- [ ] **Step 3: Add CLI smoke test**

Append to `tests/test_cli.py`:

```python
def test_cli_mock_run_prints_source_strength(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = tmp_path / "source.txt"
    source.write_text("后台镜头快扫到她坐在他腿上，台上许念念光鲜获奖。", encoding="utf-8")
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--mock",
            "--input",
            str(source),
            "--project-dir",
            str(project_dir),
            "--project-id",
            "demo",
            "--target-episode-count",
            "30",
        ],
    )

    assert result.exit_code == 0
    assert "Source strength:" in result.stdout
    output = json.loads(
        (project_dir / "round_001" / "round_result.json").read_text(encoding="utf-8")
    )
    assert output["source_strength_profile"]["recommended_intensity"] in {
        "light",
        "medium",
        "heavy",
    }
```

- [ ] **Step 4: Implement CLI summary**

In `src/novel_drama_engine/cli.py`, after `Repair budget` echo:

```python
    if result.source_strength_profile:
        typer.echo(
            "Source strength: "
            f"{result.source_strength_profile.overall_level.value} / "
            f"{result.source_strength_profile.recommended_intensity.value}"
        )
    if result.methodology_context:
        typer.echo(
            "Methodology cards: "
            + ", ".join(card.name for card in result.methodology_context.cards)
        )
```

- [ ] **Step 5: Run complete verification**

Run:

```bash
python3 -m pytest -q
npm run build
npm run ops:install
npm run ops:health
```

Expected:

- `pytest` exits 0.
- `next build` exits 0. Existing Turbopack NFT warning is acceptable.
- `ops:health` returns JSON with `"ok": true`.

- [ ] **Step 6: Commit and push**

```bash
git add src/lib/engine-types.ts src/lib/engine-runner.ts src/novel_drama_engine/cli.py tests/test_cli.py
git commit -m "Sync methodology artifacts to web runtime"
git push
```

---

## Self-Review Checklist

- Spec coverage:
  - Internal-only method workspace: Task 6.
  - Method sources and cards: Tasks 1, 3, 6.
  - Draft by default and active-only production: Tasks 1, 3, 6.
  - Source strength classifier: Task 2.
  - Adaptation intensity control: Tasks 1, 2, 4.
  - Prompt injection capped by retrieval: Tasks 3, 4.
  - Strong-original quality gate: Task 5.
  - Runtime tracking: Tasks 1, 4, 7.
  - User UI remains unaware: Tasks 4 and 6 avoid project/new and round controls.

- Placeholder scan:
  - No unfinished-marker or deferred-stub placeholders.
  - Each task contains explicit files, snippets, commands, and expected results.

- Type consistency:
  - Python enum values match JSON and TypeScript strings: `strong/medium/weak`, `light/medium/heavy`, `draft/active/archived/rejected`.
  - Artifact names match spec: `source_strength_profile.json`, `methodology_context.json`, `methodology_quality_report.json`.
  - DB table names match spec: `methodology_sources`, `methodology_cards`, `methodology_runs`.
