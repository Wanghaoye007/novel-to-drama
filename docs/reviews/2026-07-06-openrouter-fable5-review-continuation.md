# OpenRouter Fable 5 Review Continuation

- Model: `anthropic/claude-fable-5`
- Generated: 2026-07-06T20:58:25
- Pack: `2026-07-06-openrouter-fable5-review-pack.md`
- Finish reason: `stop`
- Usage: `{"prompt_tokens": 41681, "completion_tokens": 6748, "total_tokens": 48429, "cost": 0.75421, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.75421, "upstream_inference_prompt_cost": 0.41681, "upstream_inference_completions_cost": 0.3374}, "completion_tokens_details": {"reasoning_tokens": 780, "image_tokens": 0, "audio_tokens": 0}}`

---

- 修复（续 P1-2）：`rewrite_instruction` 保持为空；新增 `QualityReport.advisory_notes: list[str]`（或复用 `DramaQualityReport.advisory_warnings` 透传到 artifact），advisory 文本只进 notes 与 `drama_quality_report.md`。补测试：USABLE + 低分 advisory 时 `merged.rewrite_instruction == ""` 且 `advisory_notes` 非空；同时补一条集成断言：episode repair 目标解析对含 advisory 的报告返回空目标集。

- **[P1-3] 轮次以终态 `NEEDS_REWRITE` 收尾时 run-all 仍会继续排下一轮，缺陷在链上滚雪球**
  - 文件：`src/novel_drama_engine/pipeline.py`（无修复目标时直接 `return repaired_batch, current_quality_report`）+ `src/lib/engine-runner.ts`（`scheduleNextRoundIfRunAll` 不看 `qualityStatus`）
  - 问题：本次把"无修复目标 → NEEDS_HUMAN_REVIEW"改成原样返回，配合 `NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK=none` 默认，一轮可以以 `needs_rewrite` 终态结束（测试 `test_pipeline_strong_source_cost_control_blocks_fallback_repair` 已确认）。但 `executeEngineRound` 成功路径无条件调 `scheduleNextRoundIfRunAll`，下一轮会基于未达标剧本的 state/context 继续生成，缺陷跨轮传播且无人介入点。
  - 修复：`completionResult.qualityStatus` 为 `needs_rewrite`/`needs_human_review` 时，run-all 暂停调度（项目置 `needs_attention` 或在 job result 写 `runAllPaused: true` + 原因），由用户显式恢复。补 TS 测试：quality 终态非 usable → 不创建下一轮 job。

- **[P1-4] `reconcileStaleJobs` 对 round_generation 只失败 round、项目保持 running，且无自动 requeue，等价于静默卡死**
  - 文件：`src/lib/jobs.ts`，`reconcileStaleJobs`；`tests/p0_platform.test.ts` 反而把这个行为断言成了期望
  - 问题：stale job 被置 failed、round 置 failed、项目仍 running，但没有任何路径自动 `requeueRetryableJob`，也没有把项目标记为需要处理。与 P0-3 是同一类"失败不可见"，只是入口不同（stale 回收 vs 执行异常）。
  - 修复：reconcile 后对 round_generation 走统一决策：attempts < maxAttempts → 自动 requeue（复用 `restoreRoundGenerationRetryState`）；否则项目置 `failed`/`needs_attention`。更新 p0_platform 测试断言为"自动重排或项目进入可见异常态"，而不是 `project.status === "running"` 且无活跃 job。

- **[P1-5] `createJob` 的唯一冲突判定正则过宽，且预检查+插入非原子**
  - 文件：`src/lib/jobs.ts`，`createJob` catch 分支 `/jobs_active_round_generation_unique|unique/i`
  - 问题：`UNIQUE constraint failed: jobs.id`（uuid 撞或测试 fixture 重复插入）也会被误报为 "active job already exists"，掩盖真实错误。预检查 findFirst + insert 之间的窗口靠索引兜底是对的，但错误分类要精确。
  - 修复：正则收敛为 `/jobs_active_round_generation_unique/`；未命中时原样 rethrow。补测试：重复主键插入不被误分类。

- **[P1-6] TS 测试不做类型检查，`tests/p0_platform.test.ts` 正在写入 schema 里不存在的列**
  - 文件：`tests/p0_platform.test.ts`（多处 `maxAttempts: 3`）、`package.json`（`test:ts` 用 tsx，无 typecheck）、`src/db/schema.ts`
  - 问题：`schema.jobs` 没有 `maxAttempts` 列（diff 中 jobs 表无此字段），tsx 不做类型检查，drizzle 运行时静默丢弃未知键——测试"通过"但断言的重试语义（attempts vs maxAttempts）根本没有被数据支撑。这直接影响 P0-3 修复的可验证性。
  - 修复：要么给 jobs 表补 `max_attempts` 列（迁移 0009）并让 `isJobRetryable`/终态判断真正读取它，要么删掉测试里的伪字段；`test:ts` 前置 `tsc --noEmit`（`package.json` 加 `"typecheck": "tsc --noEmit"` 并入 CI）。

---

## 4. P2 跟进项

- **[P2-1] evidence span 的 `status="matched"` 只看 script_line，允许 `source_line=None` 仍算 matched**
  - 文件：`src/novel_drama_engine/source_evidence.py`，`_evidence_span_for_asset`
  - 语义不一致：一个"原文侧都找不到落点"的资产可以被判 matched，削弱"强原文轻改可追溯"的证明力。修复：matched 要求 source 与 script 两侧都有 span；只有 script 侧命中的标 `script_only` 或降级 warning。

- **[P2-2] 中文 token 匹配启发式脆弱：`compact[4:]` 硬切前 4 字符会切断词边界**
  - 文件：`src/novel_drama_engine/source_evidence.py` `_has_specific_asset_overlap`、`adaptation_quality.py` `_has_late_event_overlap`
  - "前 4 字符≈人名"的假设对三字名+动词（"许念念举起…"第 4 字是动词首字）会漏切/误切；同义改写（"解约协议"→"终止合同"）必然 missing，产生噪音。修复：用 bible 中的人物名单显式剔除人名 token，而不是位置切片；对 missing 项在报告里区分 "paraphrase-suspected" 供人工快速复核。补边界测试：2 字名、4 字名、资产被同义改写。

- **[P2-3] `restoreRoundGenerationRetryState` 无条件清空 `rounds.summaryJson`**
  - 文件：`src/lib/jobs.ts`
  - 若 summaryJson 里除错误外还存有诊断信息，重试即丢失、不可追溯。修复：清空前把旧 summary 追加到 job 的 `errorText`/history，或只清 error 字段。

- **[P2-4] `test:ts` glob 依赖 shell 展开，node --test 在无匹配/多平台下行为不稳**
  - 文件：`package.json`
  - 修复：改 `node --test --import tsx "tests/"` 或显式列文件；`import.meta.dirname` 需 Node ≥20.11，在 engines 字段声明。

- **[P2-5] health 路由从 `engine-runner` 导入，可能拖入重依赖**
  - 文件：`src/app/api/health/route.ts`
  - `resolveEngineMode` 应下沉到独立轻量模块（如 `src/lib/engine-mode.ts`），engine-runner 与 health 共同引用，避免 health 端点冷启动加载整个 runner。

---

## 5. 质量链风险（能否证明优于直接 LLM 改写）

当前链**尚不能闭环证明**优于 direct LLM rewrite：

1. **有的证据**：`source_evidence_report.md` 的 span 级追溯（原文行→脚本行→改写原因）是正确方向；`test_drama_quality_comparison_requires_pipeline_to_beat_baseline` 说明存在 baseline 比较门。
2. **缺失一：baseline 产物不落盘**。没有看到每轮持久化 "direct LLM rewrite baseline" 的实际输出与其 quality/evidence 报告——比较门只有分数没有可复核样本，无法向外证明。建议每 N 轮（或 experiment mode 下每轮）生成 baseline artifact 并跑同一套确定性 gate + source evidence，产出对照表。
3. **缺失二：LLM 质检瘦身后的规则覆盖矩阵**。`prompts.py` 从 LLM prompt 删掉了逐行硬指标（action 格式、22 字对白、最后 4 行 cliffhanger 落地等），声称"本地确定性 gate 负责"，但没有一张"删除的 prompt 规则 → 对应本地 gate 函数 → 对应测试"的映射。至少 "cliffhanger 必须出现在最后一场最后 4 行" 这条从 prompt 弱化成了 "tail_lines 可见承接"，需确认本地 gate 有等价检查，否则是净回退。
4. **缺失三：coverage_score 无消费方**。`SourceEvidenceReport.coverage_score` 与 span missing 率没有接入 quality gate 或 run-all 决策，只是报告——"保真"仍不构成硬约束。
5. **缺失四：P1-2 的 advisory 污染与 P1-3 的 needs_rewrite 继续跑，会让 A/B 数据本身失真**（下一轮 prompt 被 advisory 文本污染、缺陷剧本进入对照组）。

结论：可追溯性 ✅ 显著改善；可证明性 ❌ 仍缺 baseline 落盘 + 规则覆盖矩阵 + 保真硬门槛。

---

## 6. 下一步应检查/修改的文件

**P0（先改）**
- `src/novel_drama_engine/pipeline.py` — `prior_run_manifest_compatible` 兼容 key 收敛 + 跳过复用写 warning
- `drizzle/migrations/0008_material_silvermane.sql` — 前置脏数据清洗
- `src/lib/engine-runner.ts` — 终态失败项目状态判定；run-all 质量门（含 P1-3）
- `tests/test_pipeline.py`、`tests/p0_platform.test.ts` — 对应回归测试

**P1**
- `src/novel_drama_engine/drama_quality.py`、`src/novel_drama_engine/models.py` — advisory_notes 字段
- `src/lib/jobs.ts` — reconcile 自动重排/可见异常态；unique 错误分类收敛
- `src/lib/platform-credits.ts` — mock 旁路加生产防护
- `src/db/schema.ts` + 新迁移 0009 — 决定 max_attempts 列去留
- `package.json` — typecheck 接入

**P2**
- `src/novel_drama_engine/source_evidence.py` — span 状态语义、token 启发式
- `src/app/api/health/route.ts` + 新建 `src/lib/engine-mode.ts`
- `docs/PROMPT_SKILL_ARCHITECTURE.md` — 补规则覆盖矩阵章节

---

## 7. 最小行动计划

1. **修 manifest 兼容判断**：`pipeline.py` 兼容 key 收敛为语义集（schema_version/project_id/source_sha256/target_episode_count），env 缺失键按默认值归一，跳过复用写 warning artifact。补"旧 manifest + 新代码仍复用 bible"测试。验证：`python3 -m pytest tests/test_pipeline.py -q`
2. **修迁移 0008**：加脏数据清洗 UPDATE（同 round 活跃 job 保留最新一条），补脏库迁移测试。验证：构造含重复活跃 job 的 sqlite 后 `npx drizzle-kit migrate`，再 `npm run test:ts`
3. **修终态失败可见性**：`engine-runner.ts` catch 分支按是否终态决定项目状态；`jobs.ts` reconcile 对 round_generation 自动 requeue 或置可见异常态。更新 `tests/p0_platform.test.ts` 断言。验证：`npm run test:ts`
4. **修 run-all 质量门**：`qualityStatus` 非 usable 时不排下一轮，写 pause 原因。补 TS 测试。验证：`npm run test:ts`
5. **修 advisory 污染 + webhook 旁路防护**：`drama_quality.py` 增 `advisory_notes`；`platform-credits.ts` 旁路加 `!isProductionLikeDeployment() && provider==="mock"`。验证：`python3 -m pytest tests/test_drama_quality.py -q && npm run test:ts`
6. **接入 typecheck，清理伪字段**：`package.json` 加 `tsc --noEmit`，解决 `maxAttempts` 列的真伪问题（补列或删引用）。验证：`npm run typecheck && npm run test:ts`
7. **补质量链证明材料**：experiment mode 下落盘 direct-rewrite baseline artifact + 同套 gate 对照报告；在 docs 里补"删除的 LLM 质检规则 → 本地 gate → 测试"覆盖矩阵。验证：`python3 -m pytest -q`
8. **全量回归**：`python3 -m pytest -q && npm run typecheck && npm run test:ts && npm run build && git diff --check`

完成 1–4 后可复审升级为 `ready_with_followups`；5–8 为发布前收尾。
