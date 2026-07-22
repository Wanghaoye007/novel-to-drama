# Prompt Trace Analysis

- Round: 2
- Cache: completed (fresh run completed)
- Experiment mode: False
- Prompt trace: no
- Raw outputs: yes
- LLM calls: 6 total / 0 abnormal
- Quality: usable / drama 9.0
- Suspected failure stage: -

## Artifact Coverage

- OK run_manifest.json
- OK runtime_report.json
- MISSING prompt_trace.json
- OK raw_llm_output.jsonl
- OK quality_report.json
- OK drama_quality_report.json
- OK creative_script.md
- OK shooting_script.md
- OK round_result.json

## LLM Call Map

| Call | Stage | Response | Status | Prompt chars | Duration | Notes |
|---:|---|---|---|---:|---:|---|
| 0 | source_analysis | SourceAnalysis | succeeded | - | 0 | missing prompt trace |
| 1 | episode_context | EpisodeContext | succeeded | - | 0 | missing prompt trace |
| 2 | episode_plan | EpisodePlan | succeeded | - | 0 | missing prompt trace |
| 3 | script_batch | ScriptBatch | succeeded | - | 0 | missing prompt trace |
| 4 | quality_report | QualityReport | succeeded | - | 0 | missing prompt trace |
| 5 | next_round_context | NextRoundContext | succeeded | - | 1 | missing prompt trace |

## Recommendations

- 下次质量实验请开启 NOVEL_DRAMA_TRACE_PROMPTS=1 或 NOVEL_DRAMA_EXPERIMENT_MODE=1，才能复盘每个 agent 的实际 system/user prompt。
