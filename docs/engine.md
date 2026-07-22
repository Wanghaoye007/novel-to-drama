# Python Engine

`src/novel_drama_engine/` 是仓库唯一的小说改编引擎。Web 通过 `src/lib/engine-runner.ts` 启动 CLI，并把结构化产物同步到 SQLite；Web 不维护第二套 Prompt 或生成流程。

## 安装与验证

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
python3 -m novel_drama_engine.cli --help
```

## 运行一轮

真实模型：

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_MODEL="bytedance-seed/seed-2.0-mini"

python3 -m novel_drama_engine.cli run \
  --input examples/haomen_source.txt \
  --project-dir .drama_project \
  --project-id demo \
  --round-number 1
```

确定性 mock：

```bash
python3 -m novel_drama_engine.cli run \
  --mock \
  --input examples/haomen_source.txt \
  --project-dir .drama_mock \
  --project-id demo \
  --round-number 1
```

也可以使用 `npm run engine -- --help`。

## 每轮主要产物

```text
round_001/
├── source_analysis.json
├── source_spans.json
├── episode_source_packets.json
├── story_bible.json
├── episode_plan.json
├── script_batch.json
├── creative_script.md
├── shooting_script.md
├── source_evidence_report.json
├── quality_report.json
├── runtime_report.json
├── next_round_context.json
└── round_result.json
```

原始模型输出、Prompt trace、修复 packet 和重复度报告会按实际执行阶段追加。`round_result.json` 是 Web 同步和后续导出的轮次契约。

## 连续生成

对同一个 `--project-dir` 再次执行 `run`，CLI 会读取上一轮 `next_round_context.json` 并自动确定下一轮集数。Story Bible、开放钩子、人物知识状态和人工修改记录是连续性约束；下一轮不能覆盖已有集。

```bash
python3 -m novel_drama_engine.cli run \
  --input examples/haomen_source.txt \
  --project-dir .drama_project \
  --project-id demo
```

## 修复边界

- 当前集旧稿是修复的唯一文本基准。
- SourceSpan、Episode Packet、Story Bible 和分集计划提供事实与连续性约束。
- 修复使用节点级、旧文本 hash 校验的受限 Patch；非目标节点保持不变。
- 软质量问题只进入审计，不应把已生成剧本伪装成 Engine 失败。
- 缺集、严重短缺或结构崩坏才允许整集重写。

## 缓存与实验

生产运行允许复用兼容产物。修改 Prompt、模型或质量策略做实验时使用：

```bash
NOVEL_DRAMA_EXPERIMENT_MODE=1 python3 -m novel_drama_engine.cli run ...
```

实验模式关闭陈旧产物复用并保留完整 Prompt trace。评估质量时应固定源文本，比较当前 pipeline 与 direct baseline；mock 样本只能证明流程和格式稳定。

```bash
python3 -m novel_drama_engine.cli evaluate-samples \
  --samples examples/quality_samples.json \
  --projects-dir .drama_quality_eval \
  --rounds 1 \
  --direct-baseline
```

## 暂停扩建的下游能力

Engine 中仍保留 localization、video brief、delivery 和 batch 命令，以兼容现有运营任务。这些模块不是 v0.1 的开发优先级；除非阻塞剧本查看或导出，不继续增加能力。
