# Novel-to-Drama v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working Next.js webapp that takes a Chinese novel and produces standardized dialogue-drama scripts in [SCENE]/[ACTION]/[SPEAKER] format, round-by-round (5 episodes per round) with cross-round memory.

**Architecture:** Single Next.js 14 App Router app. SQLite + Drizzle for persistence. Anthropic SDK calls Claude Opus/Sonnet/Haiku. Background work runs in same Node process (no queue). Storage on local disk.

**Tech Stack:** Next.js 14, TypeScript, Tailwind, shadcn/ui, SQLite (better-sqlite3), Drizzle ORM, Anthropic SDK, mammoth (docx parser), archiver (zip writer).

**TDD note:** Per spec §10.1, v0 skips unit tests. Each task uses implement → manual smoke check → commit. E2E verification consolidated in Phase 10.

**Repo:** `~/Documents/novel-to-drama/` (already git-initialized, remote `Wanghaoye007/novel-to-drama`)

---

## Phase 0: Scaffolding

### Task 0.1: Next.js project init

**Files:**
- Create: `package.json`, `tsconfig.json`, `next.config.js`, `tailwind.config.ts`, `postcss.config.js`, `src/app/layout.tsx`, `src/app/page.tsx`, `src/app/globals.css`

- [ ] **Step 1: Initialize Next.js**

Run from `~/Documents/novel-to-drama/`:
```bash
npx create-next-app@latest . --typescript --tailwind --app --src-dir --no-eslint --import-alias "@/*" --use-npm
```

When prompted about overwriting README.md/.gitignore, choose **No** (we already have customized versions).

- [ ] **Step 2: Verify dev server starts**

```bash
npm run dev
```

Open `http://localhost:3000`. Expected: Default Next.js welcome page renders.

- [ ] **Step 3: Replace home page with placeholder**

Edit `src/app/page.tsx`:
```tsx
export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Novel-to-Drama</h1>
      <p className="text-gray-600 mt-2">v0 scaffolding</p>
    </main>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: scaffold Next.js + Tailwind app"
git push
```

---

### Task 0.2: shadcn/ui setup

**Files:**
- Create: `components.json`
- Add: `src/components/ui/` (button, input, textarea, card, label, dialog, progress, badge)

- [ ] **Step 1: Run shadcn init**

```bash
npx shadcn@latest init -d
```

Accept defaults (slate theme, src/ structure).

- [ ] **Step 2: Add the 8 components we need**

```bash
npx shadcn@latest add button input textarea card label dialog progress badge
```

- [ ] **Step 3: Smoke check**

Edit `src/app/page.tsx`:
```tsx
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Novel-to-Drama</h1>
      <Button>Test Button</Button>
    </main>
  );
}
```

Run `npm run dev`, verify the styled button renders.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: add shadcn/ui components"
git push
```

---

### Task 0.3: Database + Drizzle setup

**Files:**
- Create: `drizzle.config.ts`, `src/db/schema.ts`, `src/db/client.ts`

- [ ] **Step 1: Install dependencies**

```bash
npm install better-sqlite3 drizzle-orm uuid
npm install -D drizzle-kit @types/better-sqlite3 @types/uuid
```

- [ ] **Step 2: Write schema**

Create `src/db/schema.ts`:
```typescript
import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

export const projects = sqliteTable("projects", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  pipelineType: text("pipeline_type", { enum: ["A", "B"] }).notNull().default("A"),
  novelText: text("novel_text").notNull(),
  metaJson: text("meta_json"),
  targetLanguage: text("target_language"),
  targetEpisodeCount: integer("target_episode_count").notNull(),
  status: text("status", {
    enum: ["draft", "bible_ready", "running", "done", "failed"],
  }).notNull().default("draft"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const bibles = sqliteTable("bibles", {
  id: text("id").primaryKey(),
  projectId: text("project_id")
    .notNull()
    .references(() => projects.id, { onDelete: "cascade" }),
  channel: text("channel", { enum: ["male", "female"] }),
  sixAssetsJson: text("six_assets_json"),
  charactersMd: text("characters_md"),
  episodePlanMd: text("episode_plan_md"),
  prevRoundSummaryJson: text("prev_round_summary_json"),
  nameMappingJson: text("name_mapping_json"),
  cultureMappingJson: text("culture_mapping_json"),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const rounds = sqliteTable("rounds", {
  id: text("id").primaryKey(),
  projectId: text("project_id")
    .notNull()
    .references(() => projects.id, { onDelete: "cascade" }),
  roundNum: integer("round_num").notNull(),
  epRange: text("ep_range").notNull(),
  summaryJson: text("summary_json"),
  status: text("status", {
    enum: ["pending", "running", "done", "failed"],
  }).notNull().default("pending"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const episodes = sqliteTable("episodes", {
  id: text("id").primaryKey(),
  projectId: text("project_id")
    .notNull()
    .references(() => projects.id, { onDelete: "cascade" }),
  roundId: text("round_id")
    .notNull()
    .references(() => rounds.id, { onDelete: "cascade" }),
  epNum: integer("ep_num").notNull(),
  draftMd: text("draft_md"),
  scriptTxt: text("script_txt"),
  score: real("score"),
  reviewJson: text("review_json"),
  epSummaryJson: text("ep_summary_json"),
  retryCount: integer("retry_count").notNull().default(0),
  status: text("status", {
    enum: ["pending", "running", "green", "red", "failed"],
  }).notNull().default("pending"),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});
```

- [ ] **Step 3: Drizzle config**

Create `drizzle.config.ts`:
```typescript
import type { Config } from "drizzle-kit";

export default {
  schema: "./src/db/schema.ts",
  out: "./drizzle/migrations",
  dialect: "sqlite",
  dbCredentials: {
    url: "./db.sqlite",
  },
} satisfies Config;
```

- [ ] **Step 4: DB client**

Create `src/db/client.ts`:
```typescript
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as schema from "./schema";

const sqlite = new Database("db.sqlite");
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });
export { schema };
```

- [ ] **Step 5: Add scripts to package.json**

Edit `package.json` scripts section:
```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "db:generate": "drizzle-kit generate",
  "db:migrate": "drizzle-kit migrate",
  "db:studio": "drizzle-kit studio"
}
```

- [ ] **Step 6: Generate + apply initial migration**

```bash
npm run db:generate
npm run db:migrate
ls drizzle/migrations/
ls db.sqlite
```

Expected: migration sql file generated under `drizzle/migrations/`, `db.sqlite` exists.

- [ ] **Step 7: Smoke check**

```bash
sqlite3 db.sqlite ".tables"
```

Expected output: `bibles episodes projects rounds __drizzle_migrations`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(db): set up SQLite + Drizzle schema"
git push
```

---

### Task 0.4: Anthropic SDK wrapper

**Files:**
- Create: `.env.local.example`, `src/lib/anthropic.ts`

- [ ] **Step 1: Install Anthropic SDK**

```bash
npm install @anthropic-ai/sdk
```

- [ ] **Step 2: Env example**

Create `.env.local.example`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

User must `cp .env.local.example .env.local` and fill in their key.

- [ ] **Step 3: SDK wrapper with retry**

Create `src/lib/anthropic.ts`:
```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export const MODELS = {
  opus: "claude-opus-4-7",
  sonnet: "claude-sonnet-4-6",
  haiku: "claude-haiku-4-5-20251001",
} as const;

export type ModelKey = keyof typeof MODELS;

export class LLMCallError extends Error {
  constructor(message: string, public cause?: unknown) {
    super(message);
    this.name = "LLMCallError";
  }
}

interface CallOptions {
  model: ModelKey;
  system?: string;
  user: string;
  maxTokens?: number;
  temperature?: number;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function callLLM(opts: CallOptions): Promise<string> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await client.messages.create({
        model: MODELS[opts.model],
        max_tokens: opts.maxTokens ?? 8192,
        temperature: opts.temperature ?? 0.7,
        system: opts.system,
        messages: [{ role: "user", content: opts.user }],
      });
      const text = res.content
        .filter((b): b is Anthropic.TextBlock => b.type === "text")
        .map((b) => b.text)
        .join("\n");
      if (!text) throw new Error("empty response");
      return text;
    } catch (e) {
      lastErr = e;
      if (attempt < 2) await sleep(1000 * Math.pow(2, attempt));
    }
  }
  throw new LLMCallError("LLM call failed after 3 attempts", lastErr);
}
```

- [ ] **Step 4: Smoke check**

Create `scripts/test-llm.ts`:
```typescript
import { callLLM } from "../src/lib/anthropic";

(async () => {
  const out = await callLLM({
    model: "haiku",
    user: "Say 'hello world' and nothing else.",
  });
  console.log("LLM said:", out);
})();
```

Run:
```bash
npx tsx scripts/test-llm.ts
```

Expected: "hello world" printed (after user has set ANTHROPIC_API_KEY).

If `tsx` not installed: `npm install -D tsx` first.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(llm): add Anthropic SDK wrapper with retry"
git push
```

---

### Task 0.5: Storage directory + utility

**Files:**
- Create: `src/lib/storage.ts`

- [ ] **Step 1: Implement**

Create `src/lib/storage.ts`:
```typescript
import fs from "fs/promises";
import path from "path";

const STORAGE_ROOT = path.join(process.cwd(), "storage");

export async function ensureProjectDir(projectId: string): Promise<string> {
  const dir = path.join(STORAGE_ROOT, "projects", projectId);
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

export async function writeProjectFile(
  projectId: string,
  filename: string,
  content: string | Buffer
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  const filePath = path.join(dir, filename);
  await fs.writeFile(filePath, content);
  return filePath;
}

export async function readProjectFile(
  projectId: string,
  filename: string
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  return fs.readFile(path.join(dir, filename), "utf-8");
}

export function projectDir(projectId: string): string {
  return path.join(STORAGE_ROOT, "projects", projectId);
}
```

- [ ] **Step 2: Smoke check**

```bash
mkdir -p storage
node -e "require('fs').writeFileSync('storage/.gitkeep', '')"
ls storage
```

Expected: `.gitkeep` visible. Confirm `storage/` is in `.gitignore`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(storage): add local disk storage helpers"
git push
```

---

## Phase 1: M1 - Input Normalization

### Task 1.1: File parsers (txt/docx)

**Files:**
- Create: `src/lib/m1-normalize.ts`

- [ ] **Step 1: Install mammoth**

```bash
npm install mammoth
```

- [ ] **Step 2: Implement**

Create `src/lib/m1-normalize.ts`:
```typescript
import mammoth from "mammoth";

export interface NovelMeta {
  charCount: number;
  lineCount: number;
  chapterCount: number;
  completeness: "complete" | "ongoing" | "outline" | "unknown";
  genre: "webnovel" | "adapted-script" | "outline" | "unknown";
  channelHint: "male" | "female" | "unknown";
  anomalies: string[];
}

export async function parseUpload(
  filename: string,
  buffer: Buffer
): Promise<string> {
  const ext = filename.toLowerCase().split(".").pop();
  if (ext === "txt") {
    return buffer.toString("utf-8");
  }
  if (ext === "docx") {
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  }
  throw new Error(`Unsupported file type: .${ext}`);
}

export function extractRuleBasedMeta(novelText: string): Pick<
  NovelMeta,
  "charCount" | "lineCount" | "chapterCount"
> {
  const charCount = novelText.length;
  const lineCount = novelText.split("\n").length;
  const chapterMatches = novelText.match(/第[\d零一二三四五六七八九十百千]+[章回节]/g);
  const chapterCount = chapterMatches?.length ?? 0;
  return { charCount, lineCount, chapterCount };
}
```

- [ ] **Step 3: Smoke check**

Create `scripts/test-m1.ts`:
```typescript
import { extractRuleBasedMeta } from "../src/lib/m1-normalize";

const sample = `第一章 开始
这是测试内容。

第二章 继续
更多内容。`;

console.log(extractRuleBasedMeta(sample));
```

Run:
```bash
npx tsx scripts/test-m1.ts
```

Expected: `{ charCount: 24, lineCount: 4, chapterCount: 2 }` (numbers may vary slightly).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(m1): add file parsers and rule-based meta extraction"
git push
```

---

### Task 1.2: LLM-based normalization judgments

**Files:**
- Modify: `src/lib/m1-normalize.ts`
- Create: `src/lib/prompts/m1-judge.ts`

- [ ] **Step 1: Judge prompt**

Create `src/lib/prompts/m1-judge.ts`:
```typescript
export const M1_JUDGE_PROMPT = `你是短剧改编专家。对给定的小说文本做以下判断，输出 JSON：

1. completeness（完整度）：
   - "complete" 完结作品
   - "ongoing" 连载未完
   - "outline" 大纲或碎片
   - "unknown" 无法判断

2. genre（体裁）：
   - "webnovel" 网络小说原文
   - "adapted-script" 已改编过的剧本
   - "outline" 大纲或人设文档
   - "unknown" 无法判断

3. channelHint（频道粗判）：
   - "male" 男频（信息差打脸/降维碾压/主角主动出击）
   - "female" 女频（共情虐心/反派被惩/护场）
   - "unknown" 不确定

4. anomalies（异常列表，可空数组）：广告位、章节缺失、乱码等

输出格式（严格 JSON，无任何额外文字）：
{
  "completeness": "...",
  "genre": "...",
  "channelHint": "...",
  "anomalies": []
}

小说文本（前 6000 字）：
<<<NOVEL>>>`;

export function buildM1JudgePrompt(novelText: string): string {
  const excerpt = novelText.slice(0, 6000);
  return M1_JUDGE_PROMPT.replace("<<<NOVEL>>>", excerpt);
}
```

- [ ] **Step 2: Plug into m1-normalize**

Add to `src/lib/m1-normalize.ts`:
```typescript
import { callLLM, LLMCallError } from "./anthropic";
import { buildM1JudgePrompt } from "./prompts/m1-judge";

export async function judgeNovel(
  novelText: string
): Promise<Pick<NovelMeta, "completeness" | "genre" | "channelHint" | "anomalies">> {
  try {
    const raw = await callLLM({
      model: "sonnet",
      user: buildM1JudgePrompt(novelText),
      maxTokens: 512,
      temperature: 0.2,
    });
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error("no JSON in response");
    return JSON.parse(jsonMatch[0]);
  } catch (e) {
    if (e instanceof LLMCallError) {
      return {
        completeness: "unknown",
        genre: "unknown",
        channelHint: "unknown",
        anomalies: ["llm_judge_failed"],
      };
    }
    throw e;
  }
}

export async function normalizeNovel(
  filename: string,
  buffer: Buffer
): Promise<{ text: string; meta: NovelMeta }> {
  const text = await parseUpload(filename, buffer);
  const ruleMeta = extractRuleBasedMeta(text);
  const llmMeta = await judgeNovel(text);
  return {
    text,
    meta: { ...ruleMeta, ...llmMeta },
  };
}
```

- [ ] **Step 3: Smoke check**

Create `scripts/test-m1-full.ts`:
```typescript
import fs from "fs/promises";
import { normalizeNovel } from "../src/lib/m1-normalize";

(async () => {
  // Use the first novel from 木木给的脚本 as a fixture
  const path = "/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt";
  const buffer = await fs.readFile(path);
  const result = await normalizeNovel("祖母穿越女.txt", buffer);
  console.log("Meta:", JSON.stringify(result.meta, null, 2));
  console.log("Text length:", result.text.length);
})();
```

Run:
```bash
npx tsx scripts/test-m1-full.ts
```

Expected: meta JSON with channelHint, completeness, genre filled. Text length > 1000.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(m1): add LLM-based novel judgment"
git push
```

---

## Phase 2: M2 - Bible Generation

### Task 2.1: Bible prompts

**Files:**
- Create: `src/lib/prompts/m2-bible.ts`

- [ ] **Step 1: Implement four sub-prompts**

Create `src/lib/prompts/m2-bible.ts`:
```typescript
export const M2_CHANNEL_CONFIRM_PROMPT = `你是短剧改编专家。基于以下小说原文和初步判断，给出最终的频道结论。

【初步判断】
{{HINT}}

【小说原文（前 8000 字）】
{{NOVEL}}

输出严格 JSON：
{
  "channel": "male" 或 "female",
  "reason": "一句话依据"
}`;

export const M2_SIX_ASSETS_PROMPT = `你是短剧改编专家。从以下小说中抽取「六大资产」——改编时必须守住不能改的核心。

频道：{{CHANNEL}}

【小说原文】
{{NOVEL}}

输出严格 JSON：
{
  "protagonist_motivation": "主角核心动机，1-2 句",
  "iconic_scenes": [
    { "name": "场面名", "summary": "1-2 句", "cold_open_candidate": true|false }
  ],
  "key_lines": ["金句1", "金句2", "..."],
  "emotion_curve": "全季情绪曲线，5-10 个节点串成一句话",
  "relationships": [
    { "from": "角色A", "to": "角色B", "type": "爱/恨/帮/敌/亲", "note": "可选" }
  ],
  "premise": "故事前提/世界观设定，1-2 句"
}`;

export const M2_CHARACTERS_PROMPT = `你是短剧改编专家。为这部短剧的所有主要角色（主角+主要配角，5-8 个）写人物小传。

频道：{{CHANNEL}}
六大资产：
{{SIX_ASSETS}}

【小说原文】
{{NOVEL}}

每个角色按以下 Markdown 模板输出，多个角色用 \\n\\n--- \\n\\n 分隔：

### 【角色名】
- 年龄/外貌/标志性特征：
- 身份：主角/反派/配角
- 性格：表面 X，实则 Y
- 经历 → 导致现在的性格/动机：
- 与主角关系 + 关键节点：
- 人物弧光：从 X 变成 Y
- 台词风格 + 2 个示例台词：
- 在剧中功能：压/装/打/爆/拉
{{FEMALE_EXTRA}}

直接输出，不加额外说明。`;

export const M2_EPISODE_PLAN_PROMPT = `你是短剧改编专家。设计本剧的轮次切分和分集大纲。

约束：
- 每轮固定 5 集
- 目标总集数：{{TARGET_EP_COUNT}}
- 频道：{{CHANNEL}}

参考信息：
六大资产：
{{SIX_ASSETS}}

【小说原文】
{{NOVEL}}

输出 Markdown，结构：

## 第 1 轮（E01-E05）
本轮情绪曲线：xxx
本轮钩子方向：xxx

### E01
- 主线事件：
- 情绪标签：
- 钩子方向：

### E02
...（同 E01 结构）

...

## 第 2 轮（E06-E10）
...

直到覆盖所有 {{TARGET_EP_COUNT}} 集。`;

export function fill(template: string, vars: Record<string, string>): string {
  let out = template;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{{${k}}}`, v);
  }
  return out;
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(m2): add Bible generation prompts"
git push
```

---

### Task 2.2: M2 orchestrator

**Files:**
- Create: `src/lib/m2-bible.ts`

- [ ] **Step 1: Implement**

Create `src/lib/m2-bible.ts`:
```typescript
import { callLLM } from "./anthropic";
import {
  M2_CHANNEL_CONFIRM_PROMPT,
  M2_SIX_ASSETS_PROMPT,
  M2_CHARACTERS_PROMPT,
  M2_EPISODE_PLAN_PROMPT,
  fill,
} from "./prompts/m2-bible";
import type { NovelMeta } from "./m1-normalize";

export interface SixAssets {
  protagonist_motivation: string;
  iconic_scenes: { name: string; summary: string; cold_open_candidate: boolean }[];
  key_lines: string[];
  emotion_curve: string;
  relationships: { from: string; to: string; type: string; note?: string }[];
  premise: string;
}

export interface BibleDraft {
  channel: "male" | "female";
  sixAssets: SixAssets;
  charactersMd: string;
  episodePlanMd: string;
}

function extractJson(raw: string): any {
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in response");
  return JSON.parse(match[0]);
}

export async function generateBible(
  novelText: string,
  meta: NovelMeta,
  targetEpisodeCount: number
): Promise<BibleDraft> {
  const novelExcerpt = novelText.slice(0, 15000);

  // 1. Channel confirm
  const channelRaw = await callLLM({
    model: "sonnet",
    user: fill(M2_CHANNEL_CONFIRM_PROMPT, {
      HINT: meta.channelHint,
      NOVEL: novelExcerpt,
    }),
    maxTokens: 256,
    temperature: 0.2,
  });
  const { channel } = extractJson(channelRaw) as { channel: "male" | "female" };

  // 2. Six assets
  const sixAssetsRaw = await callLLM({
    model: "sonnet",
    user: fill(M2_SIX_ASSETS_PROMPT, {
      CHANNEL: channel,
      NOVEL: novelExcerpt,
    }),
    maxTokens: 2048,
    temperature: 0.4,
  });
  const sixAssets = extractJson(sixAssetsRaw) as SixAssets;

  // 3. Characters
  const femaleExtra =
    channel === "female"
      ? "\\n【女频额外要求】每个会背叛/劝忍的角色，必须写明：为什么他的背叛特别痛——具体的关系背景。"
      : "";
  const charactersMd = await callLLM({
    model: "sonnet",
    user: fill(M2_CHARACTERS_PROMPT, {
      CHANNEL: channel,
      SIX_ASSETS: JSON.stringify(sixAssets, null, 2),
      NOVEL: novelExcerpt,
      FEMALE_EXTRA: femaleExtra,
    }),
    maxTokens: 4096,
    temperature: 0.5,
  });

  // 4. Episode plan
  const episodePlanMd = await callLLM({
    model: "sonnet",
    user: fill(M2_EPISODE_PLAN_PROMPT, {
      TARGET_EP_COUNT: String(targetEpisodeCount),
      CHANNEL: channel,
      SIX_ASSETS: JSON.stringify(sixAssets, null, 2),
      NOVEL: novelExcerpt,
    }),
    maxTokens: 6000,
    temperature: 0.5,
  });

  return { channel, sixAssets, charactersMd, episodePlanMd };
}
```

- [ ] **Step 2: Smoke check**

Create `scripts/test-m2.ts`:
```typescript
import fs from "fs/promises";
import { normalizeNovel } from "../src/lib/m1-normalize";
import { generateBible } from "../src/lib/m2-bible";

(async () => {
  const path = "/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt";
  const buffer = await fs.readFile(path);
  const { text, meta } = await normalizeNovel("祖母穿越女.txt", buffer);
  console.log("Generating Bible...");
  const bible = await generateBible(text, meta, 10);
  console.log("Channel:", bible.channel);
  console.log("Six assets:", JSON.stringify(bible.sixAssets, null, 2).slice(0, 800));
  console.log("Characters (first 500 chars):", bible.charactersMd.slice(0, 500));
  console.log("Episode plan (first 500 chars):", bible.episodePlanMd.slice(0, 500));
})();
```

Run:
```bash
npx tsx scripts/test-m2.ts
```

Expected: channel printed, six assets JSON visible, characters + episode plan partial output. Takes ~2-3 min.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(m2): add Bible generation orchestrator"
git push
```

---

## Phase 3: M3 - Round Adapter

### Task 3.1: Episode adaptation prompt

**Files:**
- Create: `src/lib/prompts/m3-adapt.ts`

- [ ] **Step 1: Implement**

Create `src/lib/prompts/m3-adapt.ts`:
```typescript
export const M3_ADAPT_PROMPT = `你是专业短剧编剧（{{CHANNEL}}方向），正在改编第 {{EP_NUM}} 集。

【人物小传】
{{CHARACTERS}}

【六大资产】（守住不动）
{{SIX_ASSETS}}

【前情概要】
{{PREV_CONTEXT}}

【本集规划】
{{EP_PLAN}}

【原文参考】
{{NOVEL_EXCERPT}}

===== 格式规范 =====
- 场次头：X-X 日/夜 内/外 地点-细分场景 / 人物：角色A、角色B
- 动作行：△[镜头/动作指令]
- 台词行：角色名（情绪）：台词
- OS：角色名OS：内容

===== 改编规则 =====
{{CHANNEL_RULES}}

===== 台词规则 =====
- 超过两句的段落必须有内在递进弧线
- 反派台词不能纯骂街，要有自洽歪理
- 情绪最高点用最短台词，论证段用最长台词排比
- 禁止旁白/narrator，背景信息靠第三方嘴碎传递

===== △行规则 =====
- △行是三层结构：动作+情绪+心理转折
- 示例：△秦峰脸上闪过一抹心疼，张嘴想要阻止，话到嘴边却变成了威胁。

===== 硬性规格 =====
- 开篇 3 行内必须有强冲突事件
- 全集字数 500-1000
- 场景数 ≤ 4
- 每集 ≤ 25 行△ + ≤ 20 句台词
- 结尾必须是「情绪钉子」（悬念/反转/情绪极点）

直接输出剧本正文。结尾附一行钩子说明。不要输出分析或自检。`;

export const FEMALE_RULES = `===== 女频专项 =====
- 对话场景是核心战场，每轮对话必须让情绪往更深走一步
- 每个背叛/劝忍角色必须用 1-2 行台词或 OS 交代关系背景
- 背叛逐层升级
- 主角至少有 1 个主动抗争时刻
- OS 三种合法功能（至少占一项）：行动依据 / 阴谋解说 / 背景揭示`;

export const MALE_RULES = `===== 男频专项 =====
- 主角每集至少 3 个主动决策+物理动作
- 不能在一个房间站着说话超过半集
- 至少两种不同方向的情绪
- OS = 行动依据，OS 出现 → 下一行必须是对应动作`;

export const M3_EP_SUMMARY_PROMPT = `从以下短剧脚本中抽取「集摘要」，给下一集参考。

【剧本】
{{SCRIPT}}

输出严格 JSON：
{
  "character_state_changes": "本集结尾各主要人物的状态变化，1-2 句",
  "unresolved_threads": ["未解伏笔1", "未解伏笔2", "..."],
  "hook_direction": "本集钩子指向下集什么方向，1 句"
}

控制在 200 字内。`;

export const M3_ROUND_SUMMARY_PROMPT = `从以下 5 集的集摘要聚合成「轮次摘要」，给下一轮参考。

【5 集摘要】
{{EP_SUMMARIES}}

输出严格 JSON：
{
  "round_arc": "本轮整体情绪/剧情曲线，2-3 句",
  "character_states": "本轮结束时所有人物状态，3-5 句",
  "open_threads": ["跨轮未解伏笔1", "..."],
  "next_round_hook": "下一轮第一集应该如何承接"
}`;
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(m3): add episode adaptation + summary prompts"
git push
```

---

### Task 3.2: M3 single episode + cross-episode memory

**Files:**
- Create: `src/lib/m3-round.ts`

- [ ] **Step 1: Implement**

Create `src/lib/m3-round.ts`:
```typescript
import { callLLM } from "./anthropic";
import {
  M3_ADAPT_PROMPT,
  M3_EP_SUMMARY_PROMPT,
  M3_ROUND_SUMMARY_PROMPT,
  FEMALE_RULES,
  MALE_RULES,
} from "./prompts/m3-adapt";
import { fill } from "./prompts/m2-bible";

export interface EpSummary {
  character_state_changes: string;
  unresolved_threads: string[];
  hook_direction: string;
}

export interface RoundSummary {
  round_arc: string;
  character_states: string;
  open_threads: string[];
  next_round_hook: string;
}

export interface AdaptEpisodeInput {
  channel: "male" | "female";
  epNum: number;
  characters: string;
  sixAssets: string;
  epPlan: string;
  novelExcerpt: string;
  prevRoundSummary: RoundSummary | null;
  prevEpSummariesInRound: EpSummary[];
}

function buildPrevContext(
  prevRound: RoundSummary | null,
  prevEps: EpSummary[]
): string {
  const parts: string[] = [];
  if (prevRound) {
    parts.push("【上一轮摘要】");
    parts.push(`轮整体：${prevRound.round_arc}`);
    parts.push(`人物状态：${prevRound.character_states}`);
    parts.push(`跨轮伏笔：${prevRound.open_threads.join("；")}`);
    parts.push(`本轮承接：${prevRound.next_round_hook}`);
  }
  if (prevEps.length > 0) {
    parts.push("\\n【本轮已跑过的集】");
    prevEps.forEach((s, i) => {
      parts.push(
        `第${i + 1}集：${s.character_state_changes}；未解：${s.unresolved_threads.join("、")}；钩子：${s.hook_direction}`
      );
    });
  }
  if (parts.length === 0) return "（无前情，本集为本剧第 1 集）";
  return parts.join("\\n");
}

export async function adaptEpisode(input: AdaptEpisodeInput): Promise<string> {
  const channelRules = input.channel === "female" ? FEMALE_RULES : MALE_RULES;
  const prevContext = buildPrevContext(
    input.prevRoundSummary,
    input.prevEpSummariesInRound
  );
  const prompt = fill(M3_ADAPT_PROMPT, {
    CHANNEL: input.channel === "female" ? "女频" : "男频",
    EP_NUM: String(input.epNum),
    CHARACTERS: input.characters,
    SIX_ASSETS: input.sixAssets,
    PREV_CONTEXT: prevContext,
    EP_PLAN: input.epPlan,
    NOVEL_EXCERPT: input.novelExcerpt.slice(0, 8000),
    CHANNEL_RULES: channelRules,
  });

  return callLLM({
    model: "opus",
    user: prompt,
    maxTokens: 4096,
    temperature: 0.7,
  });
}

export async function extractEpSummary(script: string): Promise<EpSummary> {
  const raw = await callLLM({
    model: "haiku",
    user: fill(M3_EP_SUMMARY_PROMPT, { SCRIPT: script }),
    maxTokens: 512,
    temperature: 0.3,
  });
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in ep summary");
  return JSON.parse(match[0]);
}

export async function extractRoundSummary(
  epSummaries: EpSummary[]
): Promise<RoundSummary> {
  const raw = await callLLM({
    model: "haiku",
    user: fill(M3_ROUND_SUMMARY_PROMPT, {
      EP_SUMMARIES: JSON.stringify(epSummaries, null, 2),
    }),
    maxTokens: 1024,
    temperature: 0.3,
  });
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in round summary");
  return JSON.parse(match[0]);
}

export function extractEpisodePlan(planMd: string, epNum: number): string {
  // Parse out "### E0X" section from full plan
  const regex = new RegExp(
    `###\\s*E${String(epNum).padStart(2, "0")}[\\s\\S]*?(?=###\\s*E\\d|##\\s|$)`,
    ""
  );
  const match = planMd.match(regex);
  return match ? match[0].trim() : `（第 ${epNum} 集在大纲中未找到，请按通用流程改编）`;
}
```

- [ ] **Step 2: Smoke check**

Create `scripts/test-m3.ts`:
```typescript
import fs from "fs/promises";
import { normalizeNovel } from "../src/lib/m1-normalize";
import { generateBible } from "../src/lib/m2-bible";
import { adaptEpisode, extractEpisodePlan, extractEpSummary } from "../src/lib/m3-round";

(async () => {
  const path = "/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt";
  const buffer = await fs.readFile(path);
  const { text, meta } = await normalizeNovel("祖母穿越女.txt", buffer);
  const bible = await generateBible(text, meta, 5);

  const epPlan = extractEpisodePlan(bible.episodePlanMd, 1);
  console.log("E01 plan:", epPlan);

  console.log("\\nAdapting E01...");
  const script = await adaptEpisode({
    channel: bible.channel,
    epNum: 1,
    characters: bible.charactersMd,
    sixAssets: JSON.stringify(bible.sixAssets),
    epPlan,
    novelExcerpt: text,
    prevRoundSummary: null,
    prevEpSummariesInRound: [],
  });
  console.log("\\n=== E01 SCRIPT ===\\n", script);

  console.log("\\nExtracting summary...");
  const sum = await extractEpSummary(script);
  console.log("Summary:", sum);
})();
```

Run:
```bash
npx tsx scripts/test-m3.ts
```

Expected: E01 script (~500-1000 字 cn drama format) + summary JSON. Takes ~3-5 min.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(m3): add episode adapter + summary extractors"
git push
```

---

## Phase 4: M4 - Quality Review

### Task 4.1: Review prompts (3 agents)

**Files:**
- Create: `src/lib/prompts/m4-review.ts`

- [ ] **Step 1: Implement**

Create `src/lib/prompts/m4-review.ts`:
```typescript
export const M4_WRITER_REVIEW = `你是资深短剧编剧。给这一集打分（0-10），重点看：

- 戏剧引擎是否清晰
- △行是否三层结构（动作+情绪+心理）
- 台词是否有递进弧线
- 反派台词是否有歪理
- 结尾是否情绪钉子
- 是否有旁白偷懒

【剧本】
{{SCRIPT}}

输出严格 JSON：
{
  "score": 0-10 浮点数,
  "strengths": ["优点1", "优点2"],
  "issues": ["问题1", "问题2"],
  "verdict": "通过|需改"
}`;

export const M4_AUDIENCE_REVIEW = `你是抖音短剧重度观众。给这一集打分（0-10），重点看：

- 开篇 3 行有没有抓人
- 情绪点够不够爽/痛
- 节奏是不是拖沓
- 结尾让不让人想看下集

【剧本】
{{SCRIPT}}

输出严格 JSON：
{
  "score": 0-10 浮点数,
  "strengths": ["优点1"],
  "issues": ["问题1"],
  "verdict": "通过|需改"
}`;

export const M4_VILLAIN_REVIEW = `你是反派逻辑审查员。给这一集打分（0-10），重点看：

- 反派的动机是否自洽
- 反派的歪理是否有说服力（哪怕错的，要内部自圆其说）
- 是否单纯脸谱化坏

【剧本】
{{SCRIPT}}

输出严格 JSON：
{
  "score": 0-10 浮点数,
  "strengths": ["优点1"],
  "issues": ["问题1"],
  "verdict": "通过|需改"
}`;
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(m4): add 3-agent review prompts"
git push
```

---

### Task 4.2: M4 review orchestrator

**Files:**
- Create: `src/lib/m4-review.ts`

- [ ] **Step 1: Implement**

Create `src/lib/m4-review.ts`:
```typescript
import { callLLM } from "./anthropic";
import {
  M4_WRITER_REVIEW,
  M4_AUDIENCE_REVIEW,
  M4_VILLAIN_REVIEW,
} from "./prompts/m4-review";
import { fill } from "./prompts/m2-bible";

export interface ReviewDimension {
  score: number;
  strengths: string[];
  issues: string[];
  verdict: "通过" | "需改";
}

export interface ReviewResult {
  overall_score: number;
  writer: ReviewDimension;
  audience: ReviewDimension;
  villain: ReviewDimension;
  status: "green" | "red";
}

async function runOne(template: string, script: string): Promise<ReviewDimension> {
  const raw = await callLLM({
    model: "haiku",
    user: fill(template, { SCRIPT: script }),
    maxTokens: 768,
    temperature: 0.3,
  });
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no JSON in review");
  return JSON.parse(match[0]);
}

export async function reviewScript(script: string): Promise<ReviewResult> {
  const [writer, audience, villain] = await Promise.all([
    runOne(M4_WRITER_REVIEW, script),
    runOne(M4_AUDIENCE_REVIEW, script),
    runOne(M4_VILLAIN_REVIEW, script),
  ]);
  const overall = (writer.score + audience.score + villain.score) / 3;
  return {
    overall_score: Math.round(overall * 10) / 10,
    writer,
    audience,
    villain,
    status: overall >= 9.0 ? "green" : "red",
  };
}
```

- [ ] **Step 2: Smoke check**

Append to `scripts/test-m3.ts` (or create `scripts/test-m4.ts`):
```typescript
import { reviewScript } from "../src/lib/m4-review";

// after generating a script in test-m3:
const review = await reviewScript(script);
console.log("Review:", JSON.stringify(review, null, 2));
```

Run:
```bash
npx tsx scripts/test-m4.ts
```

Expected: overall_score number, three dimension breakdowns, status green/red.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(m4): add parallel 3-agent review"
git push
```

---

## Phase 5: M5 - Atomic Shot Format

### Task 5.1: Format conversion prompt + module

**Files:**
- Create: `src/lib/prompts/m5-format.ts`, `src/lib/m5-format.ts`

- [ ] **Step 1: Prompt**

Create `src/lib/prompts/m5-format.ts`:
```typescript
export const M5_FORMAT_PROMPT = `你是短剧脚本格式转换工程师。把以下半结构化剧本转换成原子 shot 格式。

===== 输出格式严格规则 =====
每一个 shot 占 3 行：
[SCENE] 场景描述（地点+时间+氛围）
[ACTION] 角色微动作（一句，可演的）
[SPEAKER] 角色名: 台词（或 OS）

一个 ACTION 对应一个 SPEAKER；如果是纯动作无台词，则 SPEAKER 行为空字符串。
SPEAKER 前必须贴微动作 ACTION 并状态呼应。
不要合并多个动作到一个 ACTION 里。

===== 输入剧本 =====
{{DRAFT}}

===== 输出 =====
直接输出转换后的脚本，不要任何额外说明或标题。`;
```

- [ ] **Step 2: Module**

Create `src/lib/m5-format.ts`:
```typescript
import { callLLM } from "./anthropic";
import { M5_FORMAT_PROMPT } from "./prompts/m5-format";
import { fill } from "./prompts/m2-bible";

export async function formatToAtomicShots(draftMd: string): Promise<string> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const out = await callLLM({
        model: "sonnet",
        user: fill(M5_FORMAT_PROMPT, { DRAFT: draftMd }),
        maxTokens: 4096,
        temperature: 0.2,
      });
      // Validate: must contain at least one [SCENE], [ACTION], [SPEAKER]
      if (
        out.includes("[SCENE]") &&
        out.includes("[ACTION]") &&
        out.includes("[SPEAKER]")
      ) {
        return out;
      }
      throw new Error("output missing required tags");
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(`M5 format failed: ${String(lastErr)}`);
}
```

- [ ] **Step 3: Smoke check**

Create `scripts/test-m5.ts`:
```typescript
import { formatToAtomicShots } from "../src/lib/m5-format";

const sampleDraft = `1-1 日 内 客厅 / 人物：祖母、祖父

△祖母端坐主位，神色平静。

祖母（淡淡）：四十载，我独守你一人。

△祖父猛地起身，杯子摔在地上。

祖父（震怒）：你疯了！`;

(async () => {
  const out = await formatToAtomicShots(sampleDraft);
  console.log(out);
})();
```

Run:
```bash
npx tsx scripts/test-m5.ts
```

Expected: 4+ shots with [SCENE]/[ACTION]/[SPEAKER] tags.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(m5): add atomic-shot format converter"
git push
```

---

## Phase 6: M6 - Export

### Task 6.1: Export module

**Files:**
- Create: `src/lib/m6-export.ts`

- [ ] **Step 1: Install archiver**

```bash
npm install archiver
npm install -D @types/archiver
```

- [ ] **Step 2: Implement**

Create `src/lib/m6-export.ts`:
```typescript
import fs from "fs/promises";
import { createWriteStream } from "fs";
import path from "path";
import archiver from "archiver";
import { ensureProjectDir, projectDir } from "./storage";

export async function writeEpisodeTxt(
  projectId: string,
  epNum: number,
  scriptTxt: string
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  const filename = `E${String(epNum).padStart(2, "0")}.txt`;
  const filePath = path.join(dir, filename);
  await fs.writeFile(filePath, scriptTxt);
  return filePath;
}

export async function writeBibleMd(
  projectId: string,
  charactersMd: string,
  episodePlanMd: string,
  sixAssetsJson: string
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  const filePath = path.join(dir, "Bible.md");
  const content = `# Bible

## 六大资产

\\`\\`\\`json
${sixAssetsJson}
\\`\\`\\`

## 人物小传

${charactersMd}

## 集数规划

${episodePlanMd}
`;
  await fs.writeFile(filePath, content);
  return filePath;
}

export async function buildProjectZip(
  projectId: string,
  projectName: string
): Promise<string> {
  const dir = projectDir(projectId);
  const zipPath = path.join(dir, `${projectName}.zip`);

  await new Promise<void>((resolve, reject) => {
    const output = createWriteStream(zipPath);
    const archive = archiver("zip", { zlib: { level: 9 } });

    output.on("close", () => resolve());
    archive.on("error", (err) => reject(err));

    archive.pipe(output);

    // Include all .txt and .md in project dir
    archive.glob("E*.txt", { cwd: dir });
    archive.glob("Bible.md", { cwd: dir });

    archive.finalize();
  });

  return zipPath;
}
```

- [ ] **Step 3: Smoke check**

Create `scripts/test-m6.ts`:
```typescript
import { writeEpisodeTxt, writeBibleMd, buildProjectZip } from "../src/lib/m6-export";

(async () => {
  const pid = "smoke-test";
  await writeEpisodeTxt(pid, 1, "[SCENE] test\\n[ACTION] test\\n[SPEAKER] test");
  await writeBibleMd(pid, "characters md", "ep plan md", "{}");
  const zip = await buildProjectZip(pid, "smoke");
  console.log("Zip:", zip);
})();
```

Run:
```bash
npx tsx scripts/test-m6.ts
unzip -l storage/projects/smoke-test/smoke.zip
rm -rf storage/projects/smoke-test
```

Expected: zip contains E01.txt + Bible.md.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(m6): add txt export and project zip"
git push
```

---

## Phase 7: Round Orchestration

### Task 7.1: Round runner (the engine that ties M3-M6 together)

**Files:**
- Create: `src/lib/round-runner.ts`

- [ ] **Step 1: Implement**

Create `src/lib/round-runner.ts`:
```typescript
import { v4 as uuid } from "uuid";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import {
  adaptEpisode,
  extractEpSummary,
  extractRoundSummary,
  extractEpisodePlan,
  type EpSummary,
  type RoundSummary,
} from "./m3-round";
import { reviewScript } from "./m4-review";
import { formatToAtomicShots } from "./m5-format";
import { writeEpisodeTxt } from "./m6-export";

const EPS_PER_ROUND = 5;

export async function runRound(
  projectId: string,
  roundNum: number
): Promise<{ roundId: string }> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, projectId),
  });
  if (!project || !bible) throw new Error("project or bible not found");

  const startEp = (roundNum - 1) * EPS_PER_ROUND + 1;
  const endEp = startEp + EPS_PER_ROUND - 1;
  const epRange = `E${String(startEp).padStart(2, "0")}-E${String(endEp).padStart(2, "0")}`;

  const roundId = uuid();
  const now = new Date();
  await db.insert(schema.rounds).values({
    id: roundId,
    projectId,
    roundNum,
    epRange,
    status: "running",
    createdAt: now,
  });

  const prevRoundSummary: RoundSummary | null = bible.prevRoundSummaryJson
    ? JSON.parse(bible.prevRoundSummaryJson)
    : null;
  const epSummariesInRound: EpSummary[] = [];

  for (let i = 0; i < EPS_PER_ROUND; i++) {
    const epNum = startEp + i;
    const epId = uuid();
    await db.insert(schema.episodes).values({
      id: epId,
      projectId,
      roundId,
      epNum,
      status: "running",
      updatedAt: new Date(),
    });

    try {
      const epPlan = extractEpisodePlan(bible.episodePlanMd ?? "", epNum);
      const draftMd = await adaptEpisode({
        channel: (bible.channel ?? "female") as "male" | "female",
        epNum,
        characters: bible.charactersMd ?? "",
        sixAssets: bible.sixAssetsJson ?? "{}",
        epPlan,
        novelExcerpt: project.novelText,
        prevRoundSummary,
        prevEpSummariesInRound: epSummariesInRound,
      });

      const review = await reviewScript(draftMd);
      const scriptTxt = await formatToAtomicShots(draftMd).catch(() => draftMd);
      await writeEpisodeTxt(projectId, epNum, scriptTxt);

      const epSummary = await extractEpSummary(draftMd);
      epSummariesInRound.push(epSummary);

      await db
        .update(schema.episodes)
        .set({
          draftMd,
          scriptTxt,
          score: review.overall_score,
          reviewJson: JSON.stringify(review),
          epSummaryJson: JSON.stringify(epSummary),
          status: review.status,
          updatedAt: new Date(),
        })
        .where(eq(schema.episodes.id, epId));
    } catch (e) {
      await db
        .update(schema.episodes)
        .set({
          status: "failed",
          reviewJson: JSON.stringify({ error: String(e) }),
          updatedAt: new Date(),
        })
        .where(eq(schema.episodes.id, epId));
    }
  }

  // Aggregate round summary
  let roundSummary: RoundSummary | null = null;
  try {
    if (epSummariesInRound.length > 0) {
      roundSummary = await extractRoundSummary(epSummariesInRound);
    }
  } catch (e) {
    // non-fatal
  }

  await db
    .update(schema.rounds)
    .set({
      summaryJson: roundSummary ? JSON.stringify(roundSummary) : null,
      status: "done",
    })
    .where(eq(schema.rounds.id, roundId));

  if (roundSummary) {
    await db
      .update(schema.bibles)
      .set({
        prevRoundSummaryJson: JSON.stringify(roundSummary),
        updatedAt: new Date(),
      })
      .where(eq(schema.bibles.projectId, projectId));
  }

  return { roundId };
}

export async function retryEpisode(episodeId: string): Promise<void> {
  const ep = await db.query.episodes.findFirst({
    where: eq(schema.episodes.id, episodeId),
  });
  if (!ep) throw new Error("episode not found");
  if (ep.retryCount >= 2) throw new Error("retry limit reached");

  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, ep.projectId),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, ep.projectId),
  });
  if (!project || !bible) throw new Error("project or bible not found");

  // Gather previous episodes in same round (those with epNum < this.epNum)
  const sameRoundEps = await db.query.episodes.findMany({
    where: eq(schema.episodes.roundId, ep.roundId),
  });
  const prevEpSummaries: EpSummary[] = sameRoundEps
    .filter((e) => e.epNum < ep.epNum && e.epSummaryJson)
    .sort((a, b) => a.epNum - b.epNum)
    .map((e) => JSON.parse(e.epSummaryJson!));

  const prevRoundSummary: RoundSummary | null = bible.prevRoundSummaryJson
    ? JSON.parse(bible.prevRoundSummaryJson)
    : null;

  const epPlan = extractEpisodePlan(bible.episodePlanMd ?? "", ep.epNum);
  const draftMd = await adaptEpisode({
    channel: (bible.channel ?? "female") as "male" | "female",
    epNum: ep.epNum,
    characters: bible.charactersMd ?? "",
    sixAssets: bible.sixAssetsJson ?? "{}",
    epPlan,
    novelExcerpt: project.novelText,
    prevRoundSummary,
    prevEpSummariesInRound: prevEpSummaries,
  });
  const review = await reviewScript(draftMd);
  const scriptTxt = await formatToAtomicShots(draftMd).catch(() => draftMd);
  await writeEpisodeTxt(ep.projectId, ep.epNum, scriptTxt);
  const epSummary = await extractEpSummary(draftMd);

  await db
    .update(schema.episodes)
    .set({
      draftMd,
      scriptTxt,
      score: review.overall_score,
      reviewJson: JSON.stringify(review),
      epSummaryJson: JSON.stringify(epSummary),
      status: review.status,
      retryCount: ep.retryCount + 1,
      updatedAt: new Date(),
    })
    .where(eq(schema.episodes.id, episodeId));
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: round runner orchestrates M3-M6 per episode"
git push
```

---

## Phase 8: API Routes

### Task 8.1: Project create + list

**Files:**
- Create: `src/app/api/projects/route.ts`

- [ ] **Step 1: Implement**

Create `src/app/api/projects/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { v4 as uuid } from "uuid";
import { desc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { normalizeNovel } from "@/lib/m1-normalize";
import { generateBible } from "@/lib/m2-bible";

export async function GET() {
  const list = await db.query.projects.findMany({
    orderBy: [desc(schema.projects.createdAt)],
  });
  return NextResponse.json(list);
}

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const name = form.get("name") as string;
  const targetEpStr = form.get("targetEpisodeCount") as string;
  const file = form.get("file") as File;
  if (!name || !file) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }
  const targetEpisodeCount = parseInt(targetEpStr || "10", 10);

  const buffer = Buffer.from(await file.arrayBuffer());
  const { text, meta } = await normalizeNovel(file.name, buffer);

  const projectId = uuid();
  const now = new Date();

  await db.insert(schema.projects).values({
    id: projectId,
    name,
    pipelineType: "A",
    novelText: text,
    metaJson: JSON.stringify(meta),
    targetEpisodeCount,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });

  const bible = await generateBible(text, meta, targetEpisodeCount);
  await db.insert(schema.bibles).values({
    id: uuid(),
    projectId,
    channel: bible.channel,
    sixAssetsJson: JSON.stringify(bible.sixAssets),
    charactersMd: bible.charactersMd,
    episodePlanMd: bible.episodePlanMd,
    prevRoundSummaryJson: null,
    updatedAt: now,
  });
  await db
    .update(schema.projects)
    .set({ status: "bible_ready", updatedAt: new Date() })
    .where(eq(schema.projects.id, projectId));

  return NextResponse.json({ id: projectId });
}

import { eq } from "drizzle-orm";
```

Note: move the `import { eq }` to the top of the file.

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(api): project create + list endpoints"
git push
```

---

### Task 8.2: Project detail + Bible read/update

**Files:**
- Create: `src/app/api/projects/[id]/route.ts`, `src/app/api/projects/[id]/bible/route.ts`

- [ ] **Step 1: Project detail GET**

Create `src/app/api/projects/[id]/route.ts`:
```typescript
import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, params.id),
  });
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, params.id),
  });
  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, params.id),
  });
  const episodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, params.id),
  });

  return NextResponse.json({ project, bible, rounds, episodes });
}
```

- [ ] **Step 2: Bible update PATCH**

Create `src/app/api/projects/[id]/bible/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  await db
    .update(schema.bibles)
    .set({
      charactersMd: body.charactersMd,
      episodePlanMd: body.episodePlanMd,
      sixAssetsJson: body.sixAssetsJson,
      updatedAt: new Date(),
    })
    .where(eq(schema.bibles.projectId, params.id));
  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(api): project detail + bible PATCH"
git push
```

---

### Task 8.3: Round start + retry + export

**Files:**
- Create: `src/app/api/projects/[id]/rounds/start/route.ts`, `src/app/api/episodes/[id]/retry/route.ts`, `src/app/api/projects/[id]/export/route.ts`

- [ ] **Step 1: Round start (async fire-and-forget)**

Create `src/app/api/projects/[id]/rounds/start/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { runRound } from "@/lib/round-runner";

export async function POST(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, params.id),
  });
  if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

  const existing = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, params.id),
  });
  const roundNum = existing.length + 1;

  // Fire and forget - the worker runs in the same Node process,
  // user polls the GET /projects/[id] for progress.
  runRound(params.id, roundNum).catch((e) => {
    console.error("[round-runner] failed:", e);
  });

  return NextResponse.json({ roundNum, status: "started" });
}
```

- [ ] **Step 2: Episode retry**

Create `src/app/api/episodes/[id]/retry/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { retryEpisode } from "@/lib/round-runner";

export async function POST(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await retryEpisode(params.id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 400 });
  }
}
```

- [ ] **Step 3: Export zip**

Create `src/app/api/projects/[id]/export/route.ts`:
```typescript
import { NextRequest } from "next/server";
import fs from "fs/promises";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { buildProjectZip, writeBibleMd } from "@/lib/m6-export";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, params.id),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, params.id),
  });
  if (!project || !bible) return new Response("not found", { status: 404 });

  await writeBibleMd(
    params.id,
    bible.charactersMd ?? "",
    bible.episodePlanMd ?? "",
    bible.sixAssetsJson ?? "{}"
  );
  const zipPath = await buildProjectZip(params.id, project.name);
  const buf = await fs.readFile(zipPath);
  return new Response(buf, {
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${project.name}.zip"`,
    },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(api): round start + episode retry + project export"
git push
```

---

## Phase 9: Web UI

### Task 9.1: Project list page

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Implement**

Edit `src/app/page.tsx`:
```tsx
import Link from "next/link";
import { desc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const dynamic = "force-dynamic";

export default async function Home() {
  const projects = await db.query.projects.findMany({
    orderBy: [desc(schema.projects.createdAt)],
  });

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Novel-to-Drama</h1>
        <Link href="/projects/new">
          <Button>新建项目</Button>
        </Link>
      </header>

      {projects.length === 0 ? (
        <p className="text-gray-500">还没有项目。点上方「新建项目」开始。</p>
      ) : (
        <ul className="space-y-3">
          {projects.map((p) => (
            <li key={p.id}>
              <Link href={`/projects/${p.id}/bible`}>
                <Card className="p-4 hover:bg-gray-50 transition">
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="font-medium">{p.name}</h2>
                      <p className="text-sm text-gray-500">
                        目标 {p.targetEpisodeCount} 集 · {new Date(p.createdAt).toLocaleString()}
                      </p>
                    </div>
                    <Badge>{p.status}</Badge>
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Smoke check**

Run `npm run dev`, open `localhost:3000`. Expected: empty state with "新建项目" button.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(ui): project list page"
git push
```

---

### Task 9.2: New project page

**Files:**
- Create: `src/app/projects/new/page.tsx`

- [ ] **Step 1: Implement**

Create `src/app/projects/new/page.tsx`:
```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewProjectPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const res = await fetch("/api/projects", { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      router.push(`/projects/${data.id}/bible`);
    } catch (e) {
      setError(String(e));
      setSubmitting(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">新建项目</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <Label htmlFor="name">项目名</Label>
          <Input id="name" name="name" required />
        </div>
        <div>
          <Label htmlFor="targetEpisodeCount">目标集数</Label>
          <Input
            id="targetEpisodeCount"
            name="targetEpisodeCount"
            type="number"
            defaultValue={10}
            min={5}
            max={100}
          />
        </div>
        <div>
          <Label htmlFor="file">上传小说（txt 或 docx）</Label>
          <Input id="file" name="file" type="file" accept=".txt,.docx" required />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "生成 Bible 中... (2-3 分钟)" : "上传并生成 Bible"}
        </Button>
      </form>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(ui): new project upload page"
git push
```

---

### Task 9.3: Bible editor page

**Files:**
- Create: `src/app/projects/[id]/bible/page.tsx`, `src/app/projects/[id]/bible/BibleClient.tsx`

- [ ] **Step 1: Server page**

Create `src/app/projects/[id]/bible/page.tsx`:
```tsx
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { BibleClient } from "./BibleClient";

export const dynamic = "force-dynamic";

export default async function BiblePage({
  params,
}: {
  params: { id: string };
}) {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, params.id),
  });
  const bible = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, params.id),
  });
  if (!project || !bible) notFound();
  return <BibleClient project={project} bible={bible} />;
}
```

- [ ] **Step 2: Client component**

Create `src/app/projects/[id]/bible/BibleClient.tsx`:
```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export function BibleClient({
  project,
  bible,
}: {
  project: any;
  bible: any;
}) {
  const router = useRouter();
  const [chars, setChars] = useState(bible.charactersMd ?? "");
  const [plan, setPlan] = useState(bible.episodePlanMd ?? "");
  const [assets, setAssets] = useState(bible.sixAssetsJson ?? "{}");
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);

  async function save() {
    setSaving(true);
    await fetch(`/api/projects/${project.id}/bible`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        charactersMd: chars,
        episodePlanMd: plan,
        sixAssetsJson: assets,
      }),
    });
    setSaving(false);
  }

  async function startRound() {
    setStarting(true);
    await save();
    const res = await fetch(`/api/projects/${project.id}/rounds/start`, {
      method: "POST",
    });
    const data = await res.json();
    router.push(`/projects/${project.id}/rounds/${data.roundNum}`);
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{project.name} · Bible</h1>
        <p className="text-sm text-gray-500">
          频道：{bible.channel} · 目标 {project.targetEpisodeCount} 集
        </p>
      </header>

      <section>
        <Label>六大资产（JSON）</Label>
        <Textarea
          value={assets}
          onChange={(e) => setAssets(e.target.value)}
          rows={10}
          className="font-mono text-xs"
        />
      </section>

      <section>
        <Label>人物小传</Label>
        <Textarea
          value={chars}
          onChange={(e) => setChars(e.target.value)}
          rows={18}
        />
      </section>

      <section>
        <Label>集数规划</Label>
        <Textarea
          value={plan}
          onChange={(e) => setPlan(e.target.value)}
          rows={22}
        />
      </section>

      <div className="flex gap-2">
        <Button variant="outline" onClick={save} disabled={saving}>
          {saving ? "保存中" : "保存"}
        </Button>
        <Button onClick={startRound} disabled={starting}>
          {starting ? "启动中" : "开始第 1 轮"}
        </Button>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(ui): Bible editor page"
git push
```

---

### Task 9.4: Round progress + review page

**Files:**
- Create: `src/app/projects/[id]/rounds/[n]/page.tsx`, `src/app/projects/[id]/rounds/[n]/RoundClient.tsx`

- [ ] **Step 1: Server page**

Create `src/app/projects/[id]/rounds/[n]/page.tsx`:
```tsx
import { eq, and } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { RoundClient } from "./RoundClient";

export const dynamic = "force-dynamic";

export default async function RoundPage({
  params,
}: {
  params: { id: string; n: string };
}) {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, params.id),
  });
  if (!project) notFound();
  return <RoundClient projectId={params.id} roundNum={parseInt(params.n)} project={project} />;
}
```

- [ ] **Step 2: Client component with polling**

Create `src/app/projects/[id]/rounds/[n]/RoundClient.tsx`:
```tsx
"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function RoundClient({
  projectId,
  roundNum,
  project,
}: {
  projectId: string;
  roundNum: number;
  project: any;
}) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    let stopped = false;
    async function poll() {
      while (!stopped) {
        const res = await fetch(`/api/projects/${projectId}`);
        const d = await res.json();
        setData(d);
        const round = d.rounds.find((r: any) => r.roundNum === roundNum);
        if (round?.status === "done" || round?.status === "failed") break;
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, [projectId, roundNum]);

  if (!data) return <main className="p-8">加载中...</main>;

  const round = data.rounds.find((r: any) => r.roundNum === roundNum);
  const eps = data.episodes
    .filter((e: any) => e.roundId === round?.id)
    .sort((a: any, b: any) => a.epNum - b.epNum);

  const totalRounds = Math.ceil(project.targetEpisodeCount / 5);
  const allDone =
    data.rounds.length >= totalRounds &&
    data.rounds.every((r: any) => r.status === "done");

  async function retry(epId: string) {
    await fetch(`/api/episodes/${epId}/retry`, { method: "POST" });
    // page polls and will update
  }

  async function nextRound() {
    await fetch(`/api/projects/${projectId}/rounds/start`, { method: "POST" });
    window.location.href = `/projects/${projectId}/rounds/${roundNum + 1}`;
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">
            {project.name} · 第 {roundNum} 轮
          </h1>
          <p className="text-sm text-gray-500">{round?.epRange}</p>
        </div>
        <Badge>{round?.status ?? "pending"}</Badge>
      </header>

      <div className="space-y-3">
        {eps.map((ep: any) => (
          <Card key={ep.id} className="p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">
                    E{String(ep.epNum).padStart(2, "0")}
                  </h3>
                  <Badge variant={ep.status === "green" ? "default" : "destructive"}>
                    {ep.status}
                  </Badge>
                  {ep.score != null && (
                    <span className="text-sm text-gray-500">
                      score: {ep.score}
                    </span>
                  )}
                </div>
                {ep.scriptTxt && (
                  <pre className="mt-2 text-xs bg-gray-50 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap">
                    {ep.scriptTxt.slice(0, 600)}
                    {ep.scriptTxt.length > 600 && "..."}
                  </pre>
                )}
              </div>
              {ep.status === "red" && ep.retryCount < 2 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => retry(ep.id)}
                >
                  重跑 ({2 - ep.retryCount} 次剩)
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      {round?.status === "done" && (
        <div className="flex gap-2 pt-4">
          {!allDone && roundNum * 5 < project.targetEpisodeCount && (
            <Button onClick={nextRound}>开始第 {roundNum + 1} 轮</Button>
          )}
          {allDone && (
            <Link href={`/projects/${projectId}/complete`}>
              <Button>项目完成 · 查看导出</Button>
            </Link>
          )}
          <Link href={`/projects/${projectId}/bible`}>
            <Button variant="outline">回到 Bible</Button>
          </Link>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(ui): round progress + review page with polling"
git push
```

---

### Task 9.5: Project complete page

**Files:**
- Create: `src/app/projects/[id]/complete/page.tsx`

- [ ] **Step 1: Implement**

Create `src/app/projects/[id]/complete/page.tsx`:
```tsx
import { eq, asc } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { notFound } from "next/navigation";
import { Card } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default async function CompletePage({
  params,
}: {
  params: { id: string };
}) {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, params.id),
  });
  if (!project) notFound();

  const episodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.projectId, params.id),
    orderBy: [asc(schema.episodes.epNum)],
  });

  const greenCount = episodes.filter((e) => e.status === "green").length;
  const redCount = episodes.filter((e) => e.status === "red").length;
  const failedCount = episodes.filter((e) => e.status === "failed").length;

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">{project.name} · 完成</h1>
      <Card className="p-4">
        <p className="text-sm">总集数：{episodes.length}</p>
        <p className="text-sm text-green-600">通过 (绿)：{greenCount}</p>
        <p className="text-sm text-red-600">红标：{redCount}</p>
        <p className="text-sm text-gray-500">失败：{failedCount}</p>
      </Card>
      <a
        href={`/api/projects/${params.id}/export`}
        className="inline-block px-4 py-2 bg-black text-white rounded font-medium"
      >
        下载项目 zip
      </a>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(ui): project completion page with export"
git push
```

---

## Phase 10: E2E Verification

### Task 10.1: Smoke run with a real fixture

**Files:**
- Create: `e2e/smoke.md`

- [ ] **Step 1: Smoke checklist**

Create `e2e/smoke.md`:
```markdown
# Smoke E2E

Run manually after `npm run dev` is up.

Fixture: `/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt`
(Or pick any from `~/Documents/DJ_Project/木木给的脚本/`)

## Steps

1. Open http://localhost:3000
2. Click "新建项目"
3. Name: "祖母穿越女 smoke", target episode count: 10
4. Upload the fixture txt
5. Wait 2-3 min for Bible page to appear
6. Verify:
   - [ ] Channel detected (likely 女频)
   - [ ] Characters list shows 4-8 characters
   - [ ] Episode plan covers E01-E10
7. Click "开始第 1 轮"
8. Wait ~15-25 min while polling refresh
9. Verify:
   - [ ] 5 episodes appear E01-E05
   - [ ] Each has a score
   - [ ] Each has script preview in [SCENE]/[ACTION]/[SPEAKER] format
10. Click "开始第 2 轮"
11. Wait ~15-25 min
12. Verify:
    - [ ] E06-E10 produced
    - [ ] If you check the prompt sent to E06 in logs, "上一轮摘要" should be present
13. Click "项目完成 · 查看导出"
14. Click "下载项目 zip"
15. Open zip in Finder:
    - [ ] E01.txt through E10.txt all present
    - [ ] Bible.md present
    - [ ] Open one .txt - format is [SCENE]/[ACTION]/[SPEAKER]

## Pass criteria

- Pipeline completes without crash
- At least 60% episodes score ≥ 9.0
- Zip downloads and contents look right
- Cross-round memory visible in 2nd round's first episode (manual log inspection)
```

- [ ] **Step 2: Run smoke**

Execute the steps in `e2e/smoke.md` manually. Record results.

- [ ] **Step 3: Document any deltas**

If smoke reveals issues, create follow-up tasks in this plan or open issues. Don't push fixes until Phase 11.

- [ ] **Step 4: Commit checklist + result note**

```bash
git add -A
git commit -m "test(e2e): smoke checklist + first run results"
git push
```

---

## Phase 11: Polish (only if smoke flags issues)

This phase is open-ended — only fill in tasks if Phase 10 surfaces concrete bugs. For each bug:

### Task 11.N: [Bug name]

**Files:**
- Modify: [specific file]

- [ ] **Step 1: Reproduce manually**
- [ ] **Step 2: Fix**
- [ ] **Step 3: Re-run smoke for that scenario**
- [ ] **Step 4: Commit**

---

## Acceptance gate (from spec §11)

Before declaring v0 complete, all of these must be checked:

- [ ] Web flows end-to-end: upload → Bible → 2 rounds → export zip
- [ ] At least 3 fixture novels (male/female/historical) tested
- [ ] Red-flag retry mechanism works
- [ ] Cross-round context carry: round 2's first episode prompt contains round 1 summary (verified via console.log or DB inspection)
- [ ] All txt in exported zip are in [SCENE]/[ACTION]/[SPEAKER] format
- [ ] At least 2-3 teammates have tried it and reported quality vs. their current workflow

---

## Notes for the executor

- **Model availability:** spec uses Opus 4.7 / Sonnet 4.6 / Haiku 4.5. If SDK rejects these IDs because of staleness, fall back to `claude-opus-4-7-1m` / `claude-sonnet-4-6-1m` / `claude-haiku-4-5-20251001` or to the latest in those tiers. The `MODELS` constant in `src/lib/anthropic.ts` is the only place to update.
- **Long-running requests:** Next.js API routes have default 60-300s timeouts in some envs (Vercel). v0 runs locally so this should be fine. If deploying to Vercel later, replace `runRound` fire-and-forget with an external worker.
- **Concurrency:** `runRound` is async and not de-duped. If a user clicks "开始下一轮" twice fast, two rounds will run concurrently and corrupt state. v0 punts on this — UI button is disabled after first click in the round page (already handled via `starting` state in Bible page, but the round page should also be hardened in polish).
- **Cost expectation:** A 10-episode run uses approx 50-100k tokens (Opus heavy). Use cost-aware models in env-controlled fallback if needed.
- **No auth:** v0 has no login. If running on shared network, run on localhost only, or add basic auth via middleware later.
