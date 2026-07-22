# Legacy TypeScript Engine

早期仓库曾包含一套直接由 Next.js 调用 Anthropic 的 M1-M6 小说改编流程：

```text
anthropic.ts
m1-normalize.ts
m2-bible.ts
m3-round.ts
m4-review.ts
m5-format.ts
m6-export.ts
round-runner.ts
```

这些生成实现已经退出正式代码，`@anthropic-ai/sdk` 也已移除。历史设计仍可在 `docs/superpowers/plans/2026-05-15-novel-to-drama-v0.md` 查看，但不得作为当前实现依据。

当前唯一改编主链路是：

```text
Next.js Web / jobs
  -> src/lib/engine-runner.ts
  -> python3 -m novel_drama_engine.cli
  -> src/novel_drama_engine/
```

原 `m6-export.ts` 中仍有调用的分集文件写入逻辑已重命名为 `src/lib/episode-artifacts.ts`；未调用的旧 Bible/ZIP helper 没有归档保留。
