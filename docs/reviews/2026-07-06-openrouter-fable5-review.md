# OpenRouter Fable 5 Review

- Model: `anthropic/claude-fable-5`
- Generated: 2026-07-06T20:56:02
- Pack: `2026-07-06-openrouter-fable5-review-pack.md`
- Usage: `{"prompt_tokens": 39208, "completion_tokens": 9000, "total_tokens": 48208, "cost": 0.84208, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.84208, "upstream_inference_prompt_cost": 0.39208, "upstream_inference_completions_cost": 0.45}, "completion_tokens_details": {"reasoning_tokens": 2333, "image_tokens": 0, "audio_tokens": 0}}`

---

# OpenRouter Fable 5 架构评审报告

## 1. 总体结论

**`not_ready`**

本轮修复方向正确（mock 默认、job 唯一性、webhook 签名、advisory 不阻断、span 级证据都是对的），但有三个会在部署当天就发生的真实生产问题：manifest 兼容性判断会让**所有存量项目**在下一轮静默重生成 Story Bible；轮次失败后项目被无条件置为 `running` 导致终态失败永远不可见；唯一索引迁移在存量脏数据上会直接失败。

---

## 2. P0 阻断项

- **[P0-1] 跨轮 manifest 兼容判断在本次部署后必然全量失配，静默重建 Story Bible**
  - 文件：`src/novel_drama_engine/pipeline.py`，`RoundPipeline.run` 内 `prior_run_manifest_compatible`
  - 问题：兼容判断对 `"code"` 和整个 `"env"` dict 做全等比较。本次改动本身就（a）改了代码指纹，（b）向 `CACHE_RELEVANT_ENV` 新增了 `NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK`（且默认值从 `first` 改为 `none`）。结果是：**所有已有项目的 round_00N manifest 在部署后全部判为不兼容**，下一轮 `story_bible` 复用被跳过，走 LLM 重新生成——人物名、主线、关系状态都可能漂移，直接违反"Story Bible 系统持有、跨轮稳定"的产品契约。且跳过是 `continue` 静默进行，没有任何 warning artifact，不可追溯。
  - 修复：跨轮复用的兼容 key 应限定为**语义兼容集**（`schema_version`、`project_id`、`source_sha256`、`target_episode_count`，模型可选），排除 `code` 与逐轮生成相关的 env（repair fallback 属于轮内缓存指纹，不属于跨轮 bible 兼容性）；env 比较需对缺失 key 用默认值归一；跳过复用时必须写 warning 到 runtime_report/artifact。补测试：旧格式 manifest（无新 env key）+ 新代码仍能复用 bible。

- **[P0-2] 迁移 0008 在存量脏数据上会失败**
  - 文件：`drizzle/migrations/0008_material_silvermane.sql`
  - 问题：直接 `CREATE UNIQUE INDEX ... WHERE status in ('queued','running')`。任何一个存量库里同一 round 已有 ≥2 个 queued/running 的 round_generation job（这正是本次要修的历史 bug 遗留的数据形态），索引创建即抛错，整个迁移中断，服务起不来。
  - 修复：迁移文件内先做清洗——同 round 的活跃 job 只保留最新一条，其余 `UPDATE jobs SET status='failed', error_text='superseded by dedup migration' ...`，再建索引。补一个针对脏数据库的迁移测试。

- **[P0-3] 轮次失败后项目被无条件置为 `running`，终态失败永远不可见**
  - 文件：`src/lib/engine-runner.ts`，`executeEngineRound` 的 catch 分支
  - 问题：原来 `status: "failed"` 被改成无条件 `status: "running"`，同时 `reconcileStaleJobs` 对 round_generation 也不再把项目置 failed。组合效果：一个 job 耗尽 `maxAttempts` 彻底失败后，round 是 failed，但项目永远显示 running，且没有活跃 job——用户和运维都看不到任何需要介入的信号，run-all 链也不会恢复。
  - 修复：`failJob` 后判断该失败是否终态（attempts >= maxAttempts 且未自动重试）：终态则将项目置为 `failed`（或新增 `needs_attention` 状态）；非终态才保持 `running`。补测试：终态失败 → 项目 failed；可重试失败 → 项目 running。

---

## 3. P1 重要修复

- **[P1-1] 未签名 webhook 的 mock 旁路没有生产环境防护**
  - 文件：`src/lib/platform-credits.ts`，`processPaymentWebhook`
  - 问题：`NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS=1` 一个 env 就能在任何环境（含生产）放行未签名 webhook 并入账 credits，属于单点配置错误即变现漏洞。
  - 修复：旁路生效前必须同时满足 `!isProductionLikeDeployment()` 且 `payload.provider === "mock"`，否则 throw。补 p0_platform 测试：生产 env + bypass env 仍拒绝。

- **[P1-2] drama advisory 文本注入 `rewrite_instruction` 会污染下游解析**
  - 文件：`src/novel_drama_engine/drama_quality.py`，`merge_drama_quality_into_report`
  - 问题：USABLE 报告的 `rewrite_instruction` 被塞入 "drama_quality advisory: overall 6/10；…"。凡是把非空 `rewrite_instruction` 当"存在待修问题"的下游（episode repair 目标解析对"第几集"字样做提取、UI 展示、下一轮 prompt 拼装）都会被 advisory 文本误触发。
  - 修复：新增 `advisory_notes: list[str]` 字段承载 advisory，`rewrite_instruction` 保持空；补测试断言 USABLE 时 `
