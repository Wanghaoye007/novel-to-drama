# Novel-to-Drama

把参差不齐的小说原料自动改编成符合标准格式的对白短剧脚本。

## 当前状态 v0

代码已 ship。Next.js 16 + React 19 + Tailwind 4 + shadcn/ui + SQLite + Drizzle + Anthropic SDK。完整流水线 M1→M6 + 轮次 5 集/轮 + 跨轮上下文衔接 + 三视角自查 + zip 导出。

Spec: `docs/specs/2026-05-14-novel-to-drama-design.md`
Plan: `docs/superpowers/plans/2026-05-15-novel-to-drama-v0.md`
Smoke: `e2e/smoke.md`

## 启动

```bash
cp .env.local.example .env.local
# 填上 ANTHROPIC_API_KEY

npm install
npm run db:migrate
npm run dev
# 访问 http://localhost:3000
```

可选先验证 LLM 通：

```bash
npx tsx scripts/test-llm.ts
```

## 流程

1. 首页点「新建项目」
2. 上传 txt/docx 小说 + 选目标集数 → 等 2-3 分钟 → Bible 页
3. 审 Bible（六大资产 / 人物 / 集数规划），可手改后点「开始第 1 轮」
4. 轮次进度页轮询，~15-25 分钟跑 5 集，看 score 和红/绿标
5. 红标可重跑（上限 2 次）
6. 跑完点「开始下一轮」，跨轮上下文自动衔接
7. 全跑完 → 完成页 → 下载 zip（含 N 个 E\*.txt + Bible.md）

## 来源

设计灵感和方法论来自 `~/Documents/DJ_Project/` 短剧改编方法论库。
