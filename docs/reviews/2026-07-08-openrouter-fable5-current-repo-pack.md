# Current Repo Review Pack for OpenRouter Fable 5

- Generated: 2026-07-08T16:50:53.803067

- HEAD: `f0962f0`

## Git Status
```
## codex/unify-platform-flow...origin/codex/unify-platform-flow
?? .review_branch_mock/
?? .review_branch_quality/
?? docs/reviews/2026-07-06-openrouter-fable5-current-flow-pack.md
?? docs/reviews/2026-07-06-openrouter-fable5-current-flow-response.json
?? docs/reviews/2026-07-06-openrouter-fable5-current-flow-review-attempt.md
```

## Recent Commits
```
f0962f0 fix: scope quality repair instructions by episode
7f3ba03 fix: add ops workers for async exports
1374679 Merge remote-tracking branch 'origin/codex/unify-platform-flow' into codex/unify-platform-flow
0004301 fix: harden async jobs and source context isolation
c6435ee feat: tighten source-grounded generation workflow
fafcedd Finish platform controls and source fidelity gates
5d2a2e5 Strengthen traceable drama quality repair gates
3da0c02 Harden platform generation workflow
ce8664e Harden traceable drama generation workflow
7e71082 Strengthen adaptation quality gates and methodology ingest
381bc51 Omit episode title lines from script exports
4b0c762 Keep round pages polling during batch runs
```

## Test Commands Recently Run
- python3 -m pytest -q
- npm run test:ts
- npm run typecheck
- npm run build


## Review Focus

请作为架构/代码/产品质量总审查，重点看小说转短剧的北极星：输入小说，输出必须显著保留原文 C0/C1、高价值名场面、人物动机、主动方、因果顺序和情绪递进；强原文只允许轻改，不能为了爽点大改或自己编。请输出 P0/P1/P2，精确到文件/函数，并给链路收敛方案。特别关注：
- 第二集以后和原文相差过大、信息丢失、模型自己编。
- source_to_episode_mapping、episode_source_packets、episode_cut_table 是否正确成为生成基准。
- quality gate 是否在生成前约束，而不是事后打分。
- repair 是否会跨集污染或洗掉已写好的内容。
- prompt 是否过重、资产是否重复/冲突、是否需要更优雅收敛。
- 测试是否真实证明质量，而不是 mock 假绿。


## File: `README.md`
```
# Novel-to-Drama

把参差不齐的小说原料自动改编成符合标准格式的短剧脚本，并逐步输出可投放、可本地化、可进入视频生成链路的生产资产。

当前仓库包含两条主线：

- Web v0: Next.js 16 + React 19 + Tailwind 4 + shadcn/ui + SQLite + Drizzle + Anthropic SDK。
- Python Engine MVP: round-based CLI 引擎，支持小说到短剧脚本、批量任务、视频 brief、本地化 package。

## Web App v0

Web v0 now uses the Python Engine contract as the product spine: upload a novel,
automatically start round 1, keep Story Bible as system-owned state, continue
rounds from stored context, and export production assets from the same
`round_result.json` artifacts.

Spec: `docs/specs/2026-05-14-novel-to-drama-design.md`
Plan: `docs/superpowers/plans/2026-05-15-novel-to-drama-v0.md`
Smoke: `e2e/smoke.md`

### Start Web App

```bash
cp .env.local.example .env.local
# Optional real run: set OPENAI_API_KEY and NOVEL_DRAMA_WEB_MOCK=0.
# Fast local UI smoke: set NOVEL_DRAMA_WEB_MOCK=1.

npm install
npm run db:migrate
npm run dev
# Visit http://localhost:3000
```

For local development, Web requests automatically kick one queued job unless
`NOVEL_DRAMA_AUTO_WORKER=0` is set. For a production-like split, run the Web app
and worker separately:

```bash
NOVEL_DRAMA_AUTO_WORKER=0 npm run dev
npm run jobs:watch
```

### Web Flow

1. 首页点「新建项目」。
2. 上传 txt/docx 小说 + 选目标集数、改编策略和修复预算。
3. 系统自动生成 Story Bible 和第 1 轮脚本。
4. 轮次页轮询 Engine 状态，查看质量分、上下文和脚本。
5. 跑完点「开始下一轮」，系统按原文和 context 自动识别集数；每轮可切换策略做 A/B。
6. 每轮可生成视频 brief、本地化包、交付预检和 delivery zip。
7. Story Bible 页面仅展示系统状态，不作为用户确认门。
8. 首页「质量门禁」可运行五类样本评估，查看通过/失败、每轮分数和 warning。
9. Engine 轮次和质量门禁都会写入 job 状态，页面可查看进度、策略、耗时、调用数、完成时间和错误。

For local UI demos without an OpenAI key, set:

```bash
NOVEL_DRAMA_WEB_MOCK=1 npm run dev
```

Set `NOVEL_DRAMA_WEB_MOCK=0` and `OPENAI_API_KEY` to force real Engine calls.

### Platform Context MVP

The Web app now has the first platform boundary for opening the tool to other
users. Each request resolves a user, tenant, membership, and quota envelope
before reading or mutating projects and jobs.

Default local context:

- user: `local@novel-drama.local`
- tenant slug: `local`
- tenant name: `Local Workspace`
- project limit: `25`
- monthly job limit: `200`

Override context per API request:

```bash
curl \
  -H "x-novel-user-email: demo@example.com" \
  -H "x-novel-tenant: demo-studio" \
  -H "x-novel-tenant-name: Demo Studio" \
  "http://localhost:3000/api/projects"
```

Or set defaults for a local dev server:

```bash
NOVEL_DRAMA_USER_EMAIL=demo@example.com \
NOVEL_DRAMA_TENANT_SLUG=demo-studio \
NOVEL_DRAMA_TENANT_NAME="Demo Studio" \
npm run dev
```

For browser-based use, the home page and `/platform` include a workspace
session panel. Enter an email, workspace slug, and display name to store the
current browser workspace in HTTP-only cookies:

```bash
curl \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","tenantSlug":"demo-studio","tenantName":"Demo Studio"}' \
  "http://localhost:3000/api/platform/session"
```

Inspect or clear the browser workspace session:

```bash
curl "http://localhost:3000/api/platform/session"
curl -X DELETE "http://localhost:3000/api/platform/session"
```

Legacy rows with no tenant are attached to the first resolved tenant by
default. Set `NOVEL_DRAMA_BACKFILL_LEGACY_TENANT=0` if you want to inspect or
migrate them manually.

Current scope: this is not full authentication yet. It is the server-side
tenant, ownership, and quota primitive that can later sit behind a login,
payment, or API-key gateway. Browser workspace cookies are a product template
for low-friction trials; API keys remain the machine-to-machine authentication
primitive.

Workspace members are visible on `/platform`. The first member of a workspace is
created as `owner`; later browser-session joins default to `member`. Owners and
admins can add members by email, switch roles between `owner`, `admin`, and
`member`, and remove members while keeping at least one owner in the workspace.
This is still a platform template, not a full invite-email or identity-provider
flow.

### API Keys, Usage, Billing, And Credits

Open `/platform` to view the active tenant, quotas, API keys, current-month
usage, billing estimate, credit balance, payment packages, ledger entries, and
mock invoices. API keys are stored as hashes; the plaintext token is returned
only once at creation time.

Create a key:

```bash
curl \
  -H "x-novel-user-email: demo@example.com" \
  -H "x-novel-tenant: demo-studio" \
  -H "Content-Type: application/json" \
  -d '{"name":"Production key"}' \
  "http://localhost:3000/api/platform/api-keys"
```

Use the returned token on later requests:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/projects"
```

Inspect current-month usage:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/platform/usage"
```

Inspect or manage workspace members:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/platform/members"

curl \
  -H "Authorization: Bearer <ndk_token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"writer@example.com","role":"member"}' \
  "http://localhost:3000/api/platform/members"

curl \
  -X PATCH \
  -H "Authorization: Bearer <ndk_token>" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}' \
  "http://localhost:3000/api/platform/members/<member_id>"

curl \
  -X DELETE \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/platform/members/<member_id>"
```

Inspect the active plan, subscription period, billable units, and estimated
invoice:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/platform/billing"
```

Inspect the tenant credit wallet:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/platform/credits"
```

Create a mock checkout session for a credit package:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  -H "Content-Type: application/json" \
  -d '{"packageSlug":"credits_100","provider":"mock"}' \
  "http://localhost:3000/api/platform/checkout"
```

Complete the mock checkout session and credit the wallet:

```bash
curl \
  -X POST \
  -H "Authorization: Bearer <ndk_token>" \
  "http://localhost:3000/api/platform/checkout/<session_id>/complete"
```

Send a mock provider webhook:

```bash
curl \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock","eventType":"checkout.paid","checkoutSessionId":"<session_id>"}' \
  "http://localhost:3000/api/platform/payments/webhook"
```

Switch the tenant to another internal plan:

```bash
curl \
  -H "Authorization: Bearer <ndk_token>" \
  -H "Content-Type: application/json" \
  -d '{"planSlug":"studio"}' \
  "http://localhost:3000/api/platform/billing"
```

Set `NOVEL_DRAMA_REQUIRE_API_KEY=1` to require API keys for `/api/*` routes.
Keep it at `0` for local Web UI smoke until a real login layer can propagate
tenant credentials into browser API calls.

For the payment template, `1 billable unit = 1 credit`. Each active plan grants
its included billable units into the credit ledger once per tenant billing
period, top-ups add credits through checkout/invoice records, and usage events
write debit ledger entries. Set `NOVEL_DRAMA_REQUIRE_CREDITS=1` to reject new
billable usage when the tenant wallet does not have enough credits. The current
payment provider is `mock`; real Stripe, WeChat Pay, Alipay, or manual invoicing
can reuse the same customer, checkout, invoice, webhook event, and ledger
tables after adding provider signature validation.

## Python Engine MVP

Round-based MVP for turning Chinese novel text into short-drama scripts.

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

### Test

```bash
python3 -m pytest
```

### Run

The stable local CLI entrypoint is the Python module form. `novel-drama` is the
same command after `python3 -m pip install -e ".[dev]"` puts the console script on
your `PATH`; `npm run engine -- ...` is a convenient wrapper around the module
entrypoint.

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-5.5"
python3 -m novel_drama_engine.cli run --input examples/haomen_source.txt --project-dir .drama_project --project-id demo --round-number 1
```

For OpenAI-compatible providers such as Kimi/Moonshot, set the base URL and model:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
export OPENAI_MODEL="moonshot-v1-128k"
export OPENAI_MAX_TOKENS="20000"
export OPENAI_TIMEOUT="300"
export NOVEL_DRAMA_LLM_PROVIDER="kimi"
export NOVEL_DRAMA_GENERATION_VARIANT="sop_full_stack"
export NOVEL_DRAMA_REPAIR_BUDGET="episode"
export NOVEL_DRAMA_SCRIPT_EPISODE_FIRST="0"
export NOVEL_DRAMA_EXPERIMENT_MODE="1" # prompt/model/quality experiments only
python3 -m novel_drama_engine.cli run --input examples/haomen_source.txt --project-dir .drama_project --project-id demo --round-number 1
```

`NOVEL_DRAMA_SCRIPT_EPISODE_FIRST=0` is the default first-draft path: the script
stage generates the round as a connected batch, then failed or underfilled
episodes can be repaired one by one. Set it to `1` only for controlled A/B runs,
long-project recovery, or provider-specific failure repair where per-episode
JSON stability matters more than cross-episode flow.

For prompt/model/quality experiments, use `NOVEL_DRAMA_EXPERIMENT_MODE=1`. It
disables stale artifact reuse and enables full prompt tracing, so the generated
round can be compared against the current prompt and model instead of an older
cached `round_result.json`.

You can also pass the model directly:

```bash
novel-drama run --input examples/haomen_source.txt --project-dir .drama_project --model gpt-5.5
```

If `OPENAI_API_KEY` is missing, the CLI exits with a short error and suggests `--mock`.

### Run Without An API Key

Use `--mock` to run the complete local pipeline with deterministic demo outputs:

```bash
novel-drama run --mock --input examples/haomen_source.txt --project-dir .drama_mock --project-id demo --round-number 1
```

The command writes:

- `.drama_project/round_001/source_analysis.json`
- `.drama_project/round_001/episode_context.json`
- `.drama_project/round_001/story_bible.json`
- `.drama_project/round_001/viral_asset_report.json` when using `sop_full_stack`
- `.drama_project/round_001/series_structure_plan.json` when using `sop_full_stack`
- `.drama_project/round_001/episode_plan.json` when using `drama_engine_first` or `sop_full_stack`
- `.drama_project/round_001/script_batch.json`
- `.drama_project/round_001/creative_script.md` for the human-facing script draft
- `.drama_project/round_001/shooting_script.md` for the AI-video execution draft
- `.drama_project/round_001/raw_llm_output.jsonl` for raw model responses
- `.drama_project/round_001/prompt_trace_analysis.md` for cache/prompt/raw-output diagnosis
- `.drama_project/round_001/script_novelty_report.md` for cross-episode repetition and novelty diagnosis
- `.drama_project/round_001/source_evidence_report.md` for source-span evidence that links retained source assets to source lines, script lines, and adaptation reasons

To regenerate the diagnosis report for an existing round:

```bash
novel-drama analyze-trace --project-dir .drama_project --round-number 1
```
- `.drama_project/round_001/quality_report.json`
- `.drama_project/round_001/script_novelty_report.json`
- `.drama_project/round_001/runtime_report.json`
- `.drama_project/round_001/round_result.json`
- `.drama_project/round_001/next_round_context.json`
- `.drama_project/round_001/rendered_scripts.md`

`runtime_report.json` records per-stage duration, LLM call duration, token usage
when the provider returns it, the active generation variant, and the active
repair budget. It is written during the run, so it can still identify the last
completed stage when a real provider call is slow or fails.

### Repair Budget

Quality repair is configurable so real Kimi/OpenAI-compatible runs do not get
stuck in expensive repair loops:

- `none`: run first draft and quality check only. If quality fails, mark for
  human review.
- `rewrite`: allow one whole-batch rewrite, then mark for human review if it
  still fails.
- `episode`: default strict mode. Allow one whole-batch rewrite, one per-episode
  repair pass, one bounded local-quality polish pass, and one focused
  hook/dialogue polish pass for episodes that still fail tail-hook or dialogue
  density checks. The focused pass also forces `cliffhanger` to copy the
  performed final hook line/action instead of writing explanatory summaries.

Set it per command or environment:

```bash
novel-drama run \
  --input examples/haomen_source.txt \
  --project-dir .drama_project \
  --generation-variant sop_full_stack \
  --repair-budget episode
```

### Continue A Second Round

Run the command again with the same `--project-dir`. The CLI automatically loads
the latest `next_round_context.json` and writes the next `round_XXX` directory:

```bash
novel-drama run \
  --input examples/haomen_source.txt \
  --project-dir .drama_project \
  --project-id demo
```

You can still override either value explicitly:

```bash
novel-drama run \
  --input examples/haomen_source.txt \
  --context .drama_project/round_001/next_round_context.json \
  --project-dir .drama_project \
  --round-number 2
```

### Check Project Status

```bash
novel-drama status --project-dir .drama_project
```

The status command lists completed rounds, target episode ranges, quality status,
headline scores, episode titles, open hooks, and the latest context file.

### Export A Video Brief

After a round is generated, export a downstream production brief for video
generation tools. This reads `round_result.json` and does not require image or
media inputs.

```bash
novel-drama export-video-brief \
  --project-dir .drama_project \
  --duration-seconds 90
```

The command writes:

- `.drama_project/round_001/video_brief.json`
- `.drama_project/round_001/video_brief.md`

The brief includes the 9:16 target, episode duration, visual prompts, camera and
audio notes, dialogue beats, characters, scene headings, and asset requirements.

### Export A Localization Package

Localization profiles define the target locale, platform, duration, replacements,
forbidden terms, compliance notes, and production notes. This deterministic MVP
does not translate with an LLM yet; it creates an auditable package that can feed
translation, review, or platform-specific delivery later.

```bash
novel-drama export-localization \
  --project-dir .drama_project \
  --profile examples/localization_profiles/us_tiktok.json
```

To let the configured OpenAI model rewrite the localized episodes, add:

```bash
novel-drama export-localization \
  --rewrite-with-llm \
  --project-dir .drama_project \
  --profile examples/localization_profiles/us_tiktok.json \
  --model gpt-5.5
```

The command writes:

- `.drama_project/round_001/localization_us_tiktok.json`
- `.drama_project/round_001/localization_us_tiktok.md`

Example profiles live under `examples/localization_profiles/`:

- `us_tiktok.json`
- `jp_reels.json`
- `sea_tiktok.json`

### Export A Delivery Package

Check whether a round is deliverable before packaging:

```bash
novel-drama check-delivery --project-dir .drama_project
```

Use `--strict` when you want CI or automation to fail on warnings.

Package a completed round into one zip for handoff to production, localization,
or platform delivery workflows.

```bash
novel-drama export-delivery --project-dir .drama_project
```

The command writes `.drama_project/round_001/delivery_round_001.zip` with a
`delivery_manifest.json` and all non-zip artifacts from that round.

By default, delivery is blocked when quality is not `usable` or localization
packages still contain review issues. Use `--allow-issues` only when you
intentionally want to hand off a package with warnings.

### Run A Batch

Create a manifest with one or more projects:

```json
{
  "projects": [
    {"project_id": "haomen-demo-a", "input": "haomen_source.txt"},
    {"project_id": "haomen-demo-b", "input": "haomen_source.txt"}
  ]
}
```

Paths inside the manifest are resolved relative to the manifest file.

```bash
novel-drama batch-run \
  --mock \
  --manifest examples/batch_manifest.json \
  --projects-dir .drama_projects
```

Each project gets its own artifact directory under `.drama_projects/`, and the
batch writes `.drama_projects/batch_report.json`.

### Evaluate Quality Samples

Run the five-sample quality gate across multiple rounds:

```bash
novel-drama evaluate-samples \
  --mock \
  --samples examples/quality_samples.json \
  --projects-dir .drama_quality_eval \
  --rounds 2
```

The command writes `.drama_quality_eval/quality_sample_report.json` and one
artifact project per sample. In real mode, remove `--mock` and configure
`OPENAI_API_KEY`.

To prove the pipeline beats a direct free-rewrite baseline in the same run,
enable `--direct-baseline`. Round 1 writes
`baseline_direct_free_rewrite.json`, `baseline_direct_free_rewrite.md`, and
`baseline_comparison_report.json`; the sample fails unless the pipeline is at
least 2 drama-quality points better than the direct baseline:

```bash
NOVEL_DRAMA_EXPERIMENT_MODE=1 novel-drama evaluate-samples \
  --samples examples/quality_samples.json \
  --projects-dir .drama_quality_eval_ab \
  --rounds 1 \
  --generation-variants current_density,drama_engine_first,sop_full_stack \
  --direct-baseline
```

The Web app exposes the same gate at `/quality`. It stores reports under
`storage/system/quality_samples/tenants/<tenant-id>/` by default, follows the
same mock/real mode selection as project generation, and records a tenant-scoped
job row for progress/error tracking.

### A/B Test Generation Variants

The engine supports three script-generation variants:

- `current_density`: the baseline path. It writes scripts directly from source
  analysis, context, and Story Bible, then relies on rewrite/quality gates.
- `drama_engine_first`: the single-episode planning path. It first writes
  `episode_plan.json` with drama engine, information gap, three pull beats,
  false payoff, planted key, strongest line, and cliffhanger design; script
  generation then follows that plan.
- `sop_full_stack`: the SOP planning path. It first writes
  `viral_asset_report.json` for channel, strong setting, core dilemma,
  signature scenes, high-value highlights, risks, and removal rules; then writes
  `series_structure_plan.json` for character profiles, three-layer conflicts,
  global emotion curve, episode outlines, information increments, and hook
  cadence; finally it writes `episode_plan.json` and scripts from those plans.

In the Web app, `/projects/new` lets operators pick the generation variant and
repair budget for round 1. A completed round page exposes the same controls
before starting the next round, so the same source can be compared round by
round without changing server environment variables. Successful jobs write the
selected variant, repair budget, runtime, and LLM call count into `resultJson`;
finished rounds also expose `runtime_report.json` through `summaryJson`.

Run the same sample set into separate output directories:

```bash
novel-drama evaluate-samples \
  --samples examples/quality_samples.json \
  --projects-dir .drama_quality_eval_current \
  --rounds 2 \
  --generation-variant current_density

novel-drama evaluate-samples \
  --samples examples/quality_samples.json \
  --projects-dir .drama_quality_eval_drama_engine \
  --rounds 2 \
  --generation-variant drama_engine_first

novel-drama evaluate-samples \
  --samples examples/quality_samples.json \
  --projects-dir .drama_quality_eval_sop \
  --rounds 2 \
  --generation-variant sop_full_stack
```

Compare each directory's `quality_sample_report.json`, then manually review the
generated `rendered_scripts.md` and the intermediate planning artifacts. The
stable ops web service defaults to
`NOVEL_DRAMA_GENERATION_VARIANT=sop_full_stack`,
`NOVEL_DRAMA_REPAIR_BUDGET=episode`, and
`NOVEL_DRAMA_ENGINE_TIMEOUT_MS=1800000`. The stable LaunchAgent setup runs Web
and worker as separate services; the worker defaults
`NOVEL_DRAMA_SCRIPT_EPISODE_FIRST=0`, so jobs generate a connected round first
and reserve per-episode calls for repair/recovery or explicit A/B experiments.
Override those environment variables to switch the live URL back to baseline,
tighten repairs, or change the worker timeout for a controlled run.

### Payment Webhook Safety

Before exposing payment callbacks online, configure one of:

```bash
export PLATFORM_PAYMENT_WEBHOOK_SECRET="shared-secret"
# or
export NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET="shared-secret"
```

The webhook endpoint verifies `x-novel-drama-signature` (or
`x-webhook-signature` / `x-signature`) as `HMAC-SHA256(rawBody, secret)`. In
production, missing secret or missing/mismatched signatures are rejected. If
`externalEventId` is present, already processed provider events are treated as
idempotent replays and do not grant credits twice.

### Job Status

The Web app records long-running work in the `jobs` table. Web routes enqueue
jobs with a durable `payload_json`; workers claim queued jobs and update
progress, attempts, success/failure, result JSON, and error text.

- `round_generation`: Engine round generation for a project round.
- `quality_samples`: system quality-gate runs from `/quality`.

Query recent jobs with:

```bash
curl "http://localhost:3000/api/jobs?limit=20"
curl "http://localhost:3000/api/jobs?projectId=<project-id>"
curl -H "x-novel-tenant: demo-studio" "http://localhost:3000/api/jobs?limit=20"
```

Run queued jobs once:

```bash
npm run jobs:work
```

Keep a worker alive:

```bash
npm run jobs:watch
```

For the stable local URL, `npm run ops:install` installs Web plus dedicated
workers for round generation, quality samples, delivery ZIP, video brief, and
localization exports. Web enqueues jobs; workers consume the queue continuously.

You can scope worker runs:

```bash
npm run jobs:work -- --kind round_generation --limit 5
npm run jobs:work -- --kind quality_samples --limit 1
npm run jobs:work -- --kind delivery_export --limit 1
npm run jobs:work -- --kind video_brief_export --limit 1
npm run jobs:work -- --kind localization_export --limit 1
```

### CLI Path Note

If `novel-drama` is not on `PATH`, use either stable module form:

```bash
python3 -m novel_drama_engine.cli --help
npm run engine -- --help
```

Every README example that starts with `novel-drama ...` can be run as
`python3 -m novel_drama_engine.cli ...` without changing arguments.

## 来源

设计灵感和方法论来自 `~/Documents/DJ_Project/` 短剧改编方法论库。

```


## File: `package.json`
```
{
  "name": "novel-to-drama",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "engine": "python3 -m novel_drama_engine.cli",
    "typecheck": "tsc --noEmit",
    "test:ts": "node scripts/run-ts-tests.mjs",
    "ops:start": "scripts/start-ops-server.sh",
    "ops:install": "scripts/install-ops-launchagent.sh",
    "ops:health": "scripts/ops-health-check.sh",
    "ops:online-readiness": "scripts/ops-online-readiness.sh",
    "jobs:work": "tsx src/scripts/job-worker.ts",
    "jobs:watch": "tsx src/scripts/job-worker.ts --watch",
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:studio": "drizzle-kit studio"
  },
  "dependencies": {
    "@anthropic-ai/sdk": "^0.96.0",
    "@radix-ui/react-dialog": "^1.1.15",
    "@radix-ui/react-label": "^2.1.8",
    "@radix-ui/react-progress": "^1.1.8",
    "@radix-ui/react-slot": "^1.2.4",
    "archiver": "^7.0.1",
    "better-sqlite3": "^12.10.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "drizzle-orm": "^0.45.2",
    "lucide-react": "^1.16.0",
    "mammoth": "^1.12.0",
    "next": "16.2.6",
    "radix-ui": "^1.4.3",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "tailwind-merge": "^3.6.0",
    "tsx": "^4.22.0",
    "uuid": "^14.0.0"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4",
    "@types/archiver": "^7.0.0",
    "@types/better-sqlite3": "^7.6.13",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@types/uuid": "^10.0.0",
    "drizzle-kit": "^0.31.10",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}

```


## File: `src/novel_drama_engine/pipeline.py`
```
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Event, Lock, Thread
from time import monotonic
from typing import Callable, TypeVar

from pydantic import BaseModel

from novel_drama_engine.adaptation_quality import (
    build_adaptation_quality_report,
    build_methodology_quality_report,
    merge_adaptation_quality_into_report,
    merge_methodology_quality_into_report,
)
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    merge_drama_quality_into_report,
    render_drama_quality_report,
)
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.lean_flow import (
    build_episode_cut_table,
    build_production_spec,
    build_source_annotation,
)
from novel_drama_engine.models import (
    EpisodeCutTable,
    EpisodeContext,
    EpisodePlan,
    EpisodeScript,
    EpisodeSourcePackets,
    LLMCallMetric,
    LLMUsageMetrics,
    GenerationVariant,
    MethodologyContext,
    MethodologyStage,
    NextRoundContext,
    PipelineStageMetric,
    ProductionSpec,
    QualityReport,
    QualityStatus,
    RoundResult,
    RuntimeReport,
    ScriptBatch,
    SourceAnnotation,
    SeriesStructurePlan,
    SourceAnalysis,
    SourceStrengthProfile,
    StoryBible,
    ViralAssetReport,
)
from novel_drama_engine.quality_text import (
    filter_quality_text_for_episode,
    merge_rewrite_instructions,
)
from novel_drama_engine.methodology import (
    load_methodology_cards,
    retrieve_methodology_context,
)
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeBeatPlanner,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SeriesStructurePlanner,
    SourceParser,
    StateWriter,
    ViralAssetExtractor,
)
from novel_drama_engine.renderer import (
    render_creative_round,
    render_round_summary,
    render_shooting_round,
)
from novel_drama_engine.script_quality import (
    build_current_episode_repair_packet,
    build_script_novelty_report,
    episode_needs_hook_dialogue_polish,
    episode_quality_warnings,
    episode_repair_instruction,
    hook_dialogue_polish_instruction,
    merge_script_novelty_into_quality_report,
    render_script_novelty_report,
)
from novel_drama_engine.source_packets import (
    build_episode_source_packets,
    handoff_from_episode,
    normalize_story_bible_against_source_packets,
    packet_for_episode,
    sanitize_episode_plan_against_source_packets,
    story_bible_source_packet_conflicts,
)
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
    merge_source_evidence_into_quality_report,
    render_source_evidence_report,
)
from novel_drama_engine.source_strength import classify_source_strength
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.trace_analysis import (
    analyze_round_trace_artifacts,
    render_prompt_trace_analysis,
)

EPISODES_PER_ROUND = 5
RUN_MANIFEST_SCHEMA_VERSION = "run_manifest.v2.traceable_quality_experiment"
CACHE_FINGERPRINT_FILES = (
    "prompts.py",
    "models.py",
    "script_quality.py",
    "adaptation_quality.py",
    "source_packets.py",
    "lean_flow.py",
    "source_evidence.py",
)
CACHE_RELEVANT_ENV = (
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "NOVEL_DRAMA_LLM_PROVIDER",
    "NOVEL_DRAMA_GENERATION_VARIANT",
    "NOVEL_DRAMA_REPAIR_BUDGET",
    "NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK",
    "NOVEL_DRAMA_SCRIPT_EPISODE_FIRST",
    "NOVEL_DRAMA_SCRIPT_PROMPT_MODE",
    "NOVEL_DRAMA_STRICT_SHOOTING_QUALITY",
    "NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL",
    "NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH",
)
T = TypeVar("T", bound=BaseModel)


class EmptySourceError(ValueError):
    pass


class RepairBudgetError(ValueError):
    pass


class EpisodesPerRoundError(ValueError):
    pass


class RepairBudget:
    NONE = "none"
    REWRITE = "rewrite"
    EPISODE = "episode"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pipeline_code_fingerprint() -> dict[str, str | None]:
    base_dir = Path(__file__).parent
    return {
        name: _read_file_sha256(base_dir / name)
        for name in CACHE_FINGERPRINT_FILES
    }


def experiment_mode_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_EXPERIMENT_MODE", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on", "experiment"}


def raw_output_trace_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_TRACE_RAW_OUTPUTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _json_fingerprint(payload: dict[str, object]) -> str:
    return _sha256_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    )


def normalize_repair_budget(value: str | None) -> str:
    raw = value or os.environ.get("NOVEL_DRAMA_REPAIR_BUDGET", RepairBudget.EPISODE)
    normalized = raw.strip().lower().replace("-", "_")
    aliases = {
        "0": RepairBudget.NONE,
        "off": RepairBudget.NONE,
        "none": RepairBudget.NONE,
        "skip": RepairBudget.NONE,
        "1": RepairBudget.REWRITE,
        "batch": RepairBudget.REWRITE,
        "rewrite": RepairBudget.REWRITE,
        "whole": RepairBudget.REWRITE,
        "2": RepairBudget.EPISODE,
        "episode": RepairBudget.EPISODE,
        "episode_repair": RepairBudget.EPISODE,
        "strict": RepairBudget.EPISODE,
        "full": RepairBudget.EPISODE,
    }
    if normalized not in aliases:
        allowed = ", ".join(sorted(set(aliases)))
        raise RepairBudgetError(f"unknown repair budget: {value}. Allowed: {allowed}")
    return aliases[normalized]


def normalize_episodes_per_round(value: int | str | None = None) -> int:
    raw = value
    if raw is None:
        raw = os.environ.get("NOVEL_DRAMA_EPISODES_PER_ROUND", EPISODES_PER_ROUND)
    try:
        normalized = int(raw)
    except (TypeError, ValueError) as exc:
        raise EpisodesPerRoundError(
            f"episodes per round must be between 1 and {EPISODES_PER_ROUND}: {raw}"
        ) from exc
    if normalized < 1 or normalized > EPISODES_PER_ROUND:
        raise EpisodesPerRoundError(
            f"episodes per round must be between 1 and {EPISODES_PER_ROUND}: {raw}"
        )
    return normalized


def elapsed_ms(start: float) -> int:
    return max(0, round((monotonic() - start) * 1000))


class InstrumentedJsonLLM:
    def __init__(
        self,
        llm: JsonLLM,
        *,
        on_update: Callable[[], None] | None = None,
        on_prompt: Callable[[dict[str, object]], None] | None = None,
        on_raw: Callable[[dict[str, object]], None] | None = None,
        heartbeat_seconds: float | None = None,
    ) -> None:
        self.llm = llm
        self.current_stage = "unknown"
        self.calls: list[LLMCallMetric] = []
        self.on_update = on_update
        self.on_prompt = on_prompt
        self.on_raw = on_raw
        self.heartbeat_seconds = (
            heartbeat_seconds
            if heartbeat_seconds is not None
            else float(os.environ.get("NOVEL_DRAMA_RUNTIME_HEARTBEAT_SECONDS", "5"))
        )
        self._lock = Lock()

    def _write_update(self) -> None:
        if self.on_update is None:
            return
        self.on_update()

    def _replace_call(self, index: int, metric: LLMCallMetric) -> None:
        with self._lock:
            self.calls[index] = metric
        self._write_update()

    def snapshot_calls(self) -> list[LLMCallMetric]:
        with self._lock:
            return list(self.calls)

    def _write_prompt_trace(
        self,
        *,
        call_index: int,
        system: str,
        user: str,
        response_model: type[BaseModel],
    ) -> None:
        if self.on_prompt is None:
            return
        self.on_prompt(
            {
                "call_index": call_index,
                "stage": self.current_stage,
                "response_model": response_model.__name__,
                "system_prompt_sha256": hashlib.sha256(
                    system.encode("utf-8")
                ).hexdigest(),
                "user_prompt_sha256": hashlib.sha256(user.encode("utf-8")).hexdigest(),
                "system_prompt_chars": len(system),
                "user_prompt_chars": len(user),
                "system_prompt": system,
                "user_prompt": user,
            }
        )

    def _write_raw_trace(
        self,
        *,
        call_index: int,
        response_model: type[BaseModel],
        status: str,
        error: str | None = None,
    ) -> None:
        if self.on_raw is None:
            return
        raw_response = getattr(self.llm, "last_raw_response", None)
        self.on_raw(
            {
                "call_index": call_index,
                "stage": self.current_stage,
                "response_model": response_model.__name__,
                "status": status,
                "error": error,
                "raw_response_sha256": _sha256_text(
                    json.dumps(raw_response, ensure_ascii=False, default=str)
                )
                if raw_response is not None
                else None,
                "raw_response": raw_response,
            }
        )

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        start = monotonic()
        with self._lock:
            call_index = len(self.calls)
            self.calls.append(
                LLMCallMetric(
                    stage=self.current_stage,
                    response_model=response_model.__name__,
                    duration_ms=0,
                    status="running",
                )
            )
        self._write_prompt_trace(
            call_index=call_index,
            system=system,
            user=user,
            response_model=response_model,
        )
        self._write_update()

        stop_heartbeat = Event()

        def heartbeat() -> None:
            while not stop_heartbeat.wait(max(0.1, self.heartbeat_seconds)):
                self._replace_call(
                    call_index,
                    LLMCallMetric(
                        stage=self.current_stage,
                        response_model=response_model.__name__,
                        duration_ms=elapsed_ms(start),
                        status="running",
                    ),
                )

        heartbeat_thread = Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        try:
            result = self.llm.complete(
                system=system,
                user=user,
                response_model=response_model,
            )
        except Exception as exc:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=0.2)
            self._write_raw_trace(
                call_index=call_index,
                response_model=response_model,
                status="failed",
                error=str(exc),
            )
            self._replace_call(
                call_index,
                LLMCallMetric(
                    stage=self.current_stage,
                    response_model=response_model.__name__,
                    duration_ms=elapsed_ms(start),
                    status="failed",
                    error=str(exc),
                )
            )
            raise

        stop_heartbeat.set()
        heartbeat_thread.join(timeout=0.2)
        self._write_raw_trace(
            call_index=call_index,
            response_model=response_model,
            status="succeeded",
        )
        usage = getattr(self.llm, "last_usage", None)
        if usage is not None and not isinstance(usage, LLMUsageMetrics):
            usage = LLMUsageMetrics.model_validate(usage)
        self._replace_call(
            call_index,
            LLMCallMetric(
                stage=self.current_stage,
                response_model=response_model.__name__,
                duration_ms=elapsed_ms(start),
                status="succeeded",
                usage=usage,
            )
        )
        return result


def episode_range_label(start_episode: int, end_episode: int) -> str:
    return f"EP{start_episode:02d}-EP{end_episode:02d}"


def episode_window(
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> tuple[int, int]:
    start_episode = (
        previous_context.current_episode + 1
        if previous_context is not None
        else (round_number - 1) * episodes_per_round + 1
    )
    planned_end = start_episode + episodes_per_round - 1
    if target_episode_count is not None and target_episode_count >= start_episode:
        planned_end = min(planned_end, target_episode_count)
    return start_episode, planned_end


def normalize_episode_context_range(
    episode_context: EpisodeContext,
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> EpisodeContext:
    start_episode, end_episode = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
        episodes_per_round=episodes_per_round,
    )
    target_range = episode_range_label(start_episode, end_episode)
    if episode_context.target_episode_range == target_range:
        return episode_context

    return episode_context.model_copy(
        update={
            "target_episode_range": target_range,
            "adaptation_actions": [
                *episode_context.adaptation_actions,
                f"系统已将本轮集数范围规范为 {target_range}，不得输出未编号或重复集数。",
            ],
        },
    )


def expected_episode_numbers(
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> list[int]:
    start_episode, end_episode = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
        episodes_per_round=episodes_per_round,
    )
    return list(range(start_episode, end_episode + 1))


def variant_uses_episode_plan(generation_variant: GenerationVariant) -> bool:
    return generation_variant in {
        GenerationVariant.DRAMA_ENGINE_FIRST,
        GenerationVariant.SOP_FULL_STACK,
    }


def variant_uses_sop_stack(generation_variant: GenerationVariant) -> bool:
    return generation_variant == GenerationVariant.SOP_FULL_STACK


def use_episode_first_script_generation() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", "")
    return raw.strip().lower() in {"1", "true", "yes", "on", "episode", "episode_first"}


def prompt_trace_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_TRACE_PROMPTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def blocking_optional_polish_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on", "blocking", "strict"}


def source_strength_cost_control_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def strong_source_light_adaptation(
    source_strength_profile: SourceStrengthProfile,
    generation_variant: GenerationVariant,
) -> bool:
    return (
        source_strength_cost_control_enabled()
        and generation_variant
        in {
            GenerationVariant.DRAMA_ENGINE_FIRST,
            GenerationVariant.SOP_FULL_STACK,
        }
        and source_strength_profile.overall_level.value == "strong"
        and source_strength_profile.recommended_intensity.value == "light"
    )


def fallback_episode_repair_targets(episode_numbers: list[int]) -> set[int]:
    raw = os.environ.get("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "none")
    normalized = raw.strip().lower().replace("-", "_")
    if normalized in {"all", "full", "every", "全部"}:
        return set(episode_numbers)
    if normalized in {"none", "skip", "off", "0"}:
        return set()
    if not episode_numbers:
        return set()
    return {episode_numbers[0]}


def resume_artifacts_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_RESUME_ARTIFACTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def build_run_manifest(
    *,
    project_id: str,
    round_number: int,
    source_text: str,
    target_episode_count: int | None,
    episodes_per_round: int,
    generation_variant: GenerationVariant,
    repair_budget: str,
    llm: JsonLLM,
    methodology_cards_path: Path | str | None,
) -> dict[str, object]:
    llm_model = getattr(llm, "_model", None) or os.environ.get("OPENAI_MODEL")
    fingerprint_payload: dict[str, object] = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "project_id": project_id,
        "round_number": round_number,
        "source_sha256": _sha256_text(source_text),
        "source_chars": len(source_text),
        "target_episode_count": target_episode_count,
        "episodes_per_round": episodes_per_round,
        "generation_variant": generation_variant.value,
        "repair_budget": repair_budget,
        "llm_class": llm.__class__.__name__,
        "llm_model": llm_model,
        "llm_provider": os.environ.get("NOVEL_DRAMA_LLM_PROVIDER"),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL"),
        "env": {name: os.environ.get(name) for name in CACHE_RELEVANT_ENV},
        "code": pipeline_code_fingerprint(),
        "methodology_cards_path": str(methodology_cards_path)
        if methodology_cards_path
        else None,
    }
    return {
        **fingerprint_payload,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_mode": experiment_mode_enabled(),
        "resume_requested": resume_artifacts_enabled(),
        "trace_prompts": prompt_trace_enabled() or experiment_mode_enabled(),
        "trace_raw_outputs": raw_output_trace_enabled(),
        "cache_fingerprint": _json_fingerprint(fingerprint_payload),
    }


EPISODE_RANGE_PATTERNS = (
    re.compile(
        r"\bEP\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(r"第\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*0*(\d{1,3})\s*集"),
)

EPISODE_REF_PATTERNS = (
    re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"第\s*0*(\d{1,3})\s*集"),
)


def episode_numbers_mentioned_in_quality(
    quality_report: QualityReport,
    valid_episode_numbers: list[int],
) -> set[int]:
    valid = set(valid_episode_numbers)
    text = "\n".join(
        [*quality_report.blocking_issues, quality_report.rewrite_instruction]
    )
    mentioned: set[int] = set()
    for pattern in EPISODE_RANGE_PATTERNS:
        for start_text, end_text in pattern.findall(text):
            start, end = int(start_text), int(end_text)
            if end < start:
                start, end = end, start
            mentioned.update(
                number for number in range(start, end + 1) if number in valid
            )
    for pattern in EPISODE_REF_PATTERNS:
        mentioned.update(
            number
            for number in (int(match) for match in pattern.findall(text))
            if number in valid
        )
    return mentioned


def source_evidence_targets_for_episode(
    quality_report: QualityReport,
    episode_number: int,
) -> list[str]:
    prefix = f"EP{episode_number:02d}"
    text = "\n".join(
        [*quality_report.blocking_issues, quality_report.rewrite_instruction]
    )
    matches = re.findall(
        rf"{re.escape(prefix)}\s*缺少原文资产[：:][^；;\n]+",
        text,
    )
    return list(dict.fromkeys(match.strip() for match in matches))


def quality_instruction_for_episode(
    quality_report: QualityReport,
    episode_number: int,
) -> str:
    merged = merge_rewrite_instructions(
        [*quality_report.blocking_issues, quality_report.rewrite_instruction],
        blocking=quality_report.status != QualityStatus.USABLE
        or bool(quality_report.blocking_issues),
    )
    return filter_quality_text_for_episode(merged, episode_number)


def provisional_next_round_context(
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None = None,
) -> NextRoundContext:
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)
    current_episode = episodes[-1].episode if episodes else 0
    open_hooks = [episodes[-1].cliffhanger] if episodes else []
    prop_states: list[str] = []
    relationship_changes: list[str] = []
    foreshadowing_ledger: list[str] = []
    character_knowledge: dict[str, list[str]] = {}

    for episode in episodes:
        for key, value in episode.state_update.items():
            text = f"EP{episode.episode:02d} {key}: {value}"
            normalized_key = str(key).lower()
            if "relationship" in normalized_key or "关系" in str(key):
                relationship_changes.append(text)
            elif "foreshadow" in normalized_key or "伏笔" in str(key):
                foreshadowing_ledger.append(text)
            elif "character" in normalized_key or "knowledge" in normalized_key:
                character_knowledge.setdefault("system", []).append(text)
            else:
                prop_states.append(text)

    return NextRoundContext(
        summary=(
            f"临时质检上下文：已生成到 EP{current_episode:02d}。"
            if current_episode
            else "临时质检上下文：暂无已生成集。"
        ),
        current_episode=current_episode,
        open_hooks=open_hooks,
        forbidden_reveals=(
            previous_context.forbidden_reveals if previous_context else []
        ),
        character_knowledge=character_knowledge,
        relationship_changes=relationship_changes,
        prop_states=prop_states,
        foreshadowing_ledger=foreshadowing_ledger,
    )


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
        target_episode_count: int | None = None,
        episodes_per_round: int | str | None = None,
        generation_variant: GenerationVariant | str = GenerationVariant.CURRENT_DENSITY,
        repair_budget: str | None = None,
        methodology_cards_path: Path | str | None = None,
    ) -> RoundResult:
        if not source_text.strip():
            raise EmptySourceError("source_text is empty")
        generation_variant = GenerationVariant(generation_variant)
        resolved_episodes_per_round = normalize_episodes_per_round(episodes_per_round)
        resolved_repair_budget = normalize_repair_budget(repair_budget)
        effective_repair_budget = resolved_repair_budget
        stages: list[PipelineStageMetric] = []
        pipeline_start = monotonic()
        tracked_llm: InstrumentedJsonLLM
        runtime_methodology_cards: list[str] = []
        light_source_cost_control = False
        expected_manifest = build_run_manifest(
            project_id=project_id,
            round_number=round_number,
            source_text=source_text,
            target_episode_count=target_episode_count,
            episodes_per_round=resolved_episodes_per_round,
            generation_variant=generation_variant,
            repair_budget=resolved_repair_budget,
            llm=self.llm,
            methodology_cards_path=methodology_cards_path,
        )
        should_trace_prompts = prompt_trace_enabled() or experiment_mode_enabled()
        prompt_trace_entries: list[dict[str, object]] = []
        raw_trace_entries: list[dict[str, object]] = []

        def write_run_manifest(cache_status: str, reason: str | None = None) -> None:
            self.store.write_text_artifact(
                round_number,
                "run_manifest.json",
                json.dumps(
                    {
                        **expected_manifest,
                        "cache_status": cache_status,
                        "cache_status_reason": reason,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        def cached_manifest_status() -> tuple[bool, str]:
            path = self.store.project_dir / f"round_{round_number:03d}" / "run_manifest.json"
            if experiment_mode_enabled():
                return False, "experiment mode disables artifact resume"
            if not resume_artifacts_enabled():
                return False, "NOVEL_DRAMA_RESUME_ARTIFACTS disabled"
            if not path.exists():
                return False, "run_manifest.json missing"
            try:
                raw_manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return False, "run_manifest.json is invalid JSON"
            if raw_manifest.get("cache_fingerprint") != expected_manifest["cache_fingerprint"]:
                return False, "run_manifest cache fingerprint mismatch"
            return True, "run_manifest cache fingerprint matched"

        def runtime_report() -> RuntimeReport:
            return RuntimeReport(
                generation_variant=generation_variant,
                repair_budget=effective_repair_budget,
                llm_model=getattr(self.llm, "_model", None) or os.environ.get("OPENAI_MODEL"),
                total_duration_ms=elapsed_ms(pipeline_start),
                stages=stages,
                llm_calls=tracked_llm.snapshot_calls(),
                methodology_cards=runtime_methodology_cards,
            )

        def write_runtime_report() -> RuntimeReport:
            report = runtime_report()
            self.store.write_round_artifact(round_number, "runtime_report", report)
            return report

        def write_prompt_trace(entry: dict[str, object]) -> None:
            prompt_trace_entries.append(entry)
            self.store.write_text_artifact(
                round_number,
                "prompt_trace.json",
                json.dumps(prompt_trace_entries, ensure_ascii=False, indent=2),
            )

        def write_raw_trace(entry: dict[str, object]) -> None:
            raw_trace_entries.append(entry)
            self.store.write_text_artifact(
                round_number,
                "raw_llm_output.jsonl",
                "\n".join(
                    json.dumps(item, ensure_ascii=False, default=str)
                    for item in raw_trace_entries
                )
                + "\n",
            )

        def write_trace_analysis() -> None:
            report = analyze_round_trace_artifacts(
                self.store.project_dir / f"round_{round_number:03d}",
                round_number=round_number,
            )
            self.store.write_text_artifact(
                round_number,
                "prompt_trace_analysis.json",
                report.model_dump_json(indent=2),
            )
            self.store.write_text_artifact(
                round_number,
                "prompt_trace_analysis.md",
                render_prompt_trace_analysis(report),
            )

        tracked_llm = InstrumentedJsonLLM(
            self.llm,
            on_update=write_runtime_report,
            on_prompt=write_prompt_trace if should_trace_prompts else None,
            on_raw=write_raw_trace if raw_output_trace_enabled() else None,
        )
        should_resume_artifacts, resume_reason = cached_manifest_status()
        should_reuse_prior_round_artifacts = (
            resume_artifacts_enabled() and not experiment_mode_enabled()
        )
        write_run_manifest(
            "resume_enabled" if should_resume_artifacts else "resume_disabled",
            resume_reason,
        )
        if should_resume_artifacts:
            cached_result = self.store.read_round_artifact(
                round_number,
                "round_result",
                RoundResult,
            )
            if cached_result is not None:
                write_run_manifest("round_result_cache_hit", resume_reason)
                write_trace_analysis()
                return cached_result

        def repair_instruction_for_episode(
            episode_number: int,
            existing_episode,
            base_instruction: str,
        ) -> str:
            if existing_episode is None:
                return base_instruction
            return episode_repair_instruction(
                existing_episode,
                base_instruction,
                allow_full_rewrite=not light_source_cost_control,
            )

        def write_episode_artifact(episode: EpisodeScript) -> None:
            self.store.write_round_artifact(
                round_number,
                f"episode_{episode.episode:03d}",
                episode,
            )

        def run_stage(name: str, fn: Callable[[], T]) -> T:
            tracked_llm.current_stage = name
            stage_start = monotonic()
            try:
                result = fn()
            except Exception as exc:
                stages.append(
                    PipelineStageMetric(
                        name=name,
                        duration_ms=elapsed_ms(stage_start),
                        status="failed",
                        error=str(exc),
                    )
                )
                write_runtime_report()
                raise
            stages.append(
                PipelineStageMetric(
                    name=name,
                    duration_ms=elapsed_ms(stage_start),
                    status="succeeded",
                )
            )
            write_runtime_report()
            return result

        def read_cached_artifact(name: str, model_type: type[T]) -> T | None:
            if not should_resume_artifacts:
                return None
            return self.store.read_round_artifact(round_number, name, model_type)

        def read_prior_round_artifact(name: str, model_type: type[T]) -> T | None:
            if not should_reuse_prior_round_artifacts:
                return None
            prior_round_numbers = [
                candidate
                for candidate in self.store.existing_round_numbers()
                if candidate < round_number
            ]
            for prior_round_number in reversed(prior_round_numbers):
                if not prior_run_manifest_compatible(prior_round_number):
                    continue
                artifact = self.store.read_round_artifact(
                    prior_round_number,
                    name,
                    model_type,
                )
                if artifact is not None:
                    return artifact
            return None

        def prior_run_manifest_compatible(prior_round_number: int) -> bool:
            path = self.store.project_dir / f"round_{prior_round_number:03d}" / "run_manifest.json"
            if not path.exists():
                return False
            try:
                prior_manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return False

            # Prior-round artifacts such as Story Bible represent story facts, not
            # an exact replay cache. Code fingerprints, provider env, repair
            # budgets, and generation variants are allowed to change without
            # invalidating reusable source-grounded planning assets.
            comparable_keys = (
                "schema_version",
                "project_id",
                "source_sha256",
                "source_chars",
                "target_episode_count",
            )
            return all(
                prior_manifest.get(key) == expected_manifest.get(key)
                for key in comparable_keys
            )

        def record_cached_stage(name: str) -> None:
            stages.append(
                PipelineStageMetric(
                    name=name,
                    duration_ms=0,
                    status="cached",
                )
            )
            write_runtime_report()

        def record_skipped_stage(name: str, reason: str | None = None) -> None:
            stages.append(
                PipelineStageMetric(
                    name=name,
                    duration_ms=0,
                    status="skipped",
                    error=reason,
                )
            )
            write_runtime_report()

        def cached_stage(
            name: str,
            artifact_name: str,
            model_type: type[T],
            fn: Callable[[], T],
        ) -> T:
            cached = read_cached_artifact(artifact_name, model_type)
            if cached is not None:
                record_cached_stage(name)
                return cached
            result = run_stage(name, fn)
            self.store.write_round_artifact(round_number, artifact_name, result)
            return result

        source_analysis = cached_stage(
            "source_analysis",
            "source_analysis",
            SourceAnalysis,
            lambda: SourceParser(tracked_llm).run(source_text),
        )

        viral_asset_report = None
        if variant_uses_sop_stack(generation_variant):
            viral_asset_report = cached_stage(
                "viral_asset_report",
                "viral_asset_report",
                ViralAssetReport,
                lambda: ViralAssetExtractor(tracked_llm).run(
                    source_text,
                    source_analysis,
                    target_episode_count,
                ),
            )

        source_strength_profile = cached_stage(
            "source_strength_profile",
            "source_strength_profile",
            SourceStrengthProfile,
            lambda: classify_source_strength(source_analysis, viral_asset_report),
        )
        light_source_cost_control = strong_source_light_adaptation(
            source_strength_profile,
            generation_variant,
        )
        if light_source_cost_control and resolved_repair_budget == RepairBudget.REWRITE:
            effective_repair_budget = RepairBudget.EPISODE
        self.store.write_text_artifact(
            round_number,
            "cost_control_decision.json",
            json.dumps(
                {
                    "enabled": source_strength_cost_control_enabled(),
                    "mode": "strong_source_light_adaptation"
                    if light_source_cost_control
                    else "standard",
                    "source_strength_level": source_strength_profile.overall_level.value,
                    "adaptation_intensity": source_strength_profile.recommended_intensity.value,
                    "requested_repair_budget": resolved_repair_budget,
                    "effective_repair_budget": effective_repair_budget,
                    "allow_repair_fallback": not light_source_cost_control,
                    "allow_optional_polish": (
                        blocking_optional_polish_enabled()
                        and not light_source_cost_control
                    ),
                    "reason": (
                        "强原文本身具备钩子/冲突/名场面，禁止默认大改和无目标返工。"
                        if light_source_cost_control
                        else "按标准修复预算执行。"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        methodology_cards = load_methodology_cards(
            Path(methodology_cards_path) if methodology_cards_path else None
        )
        methodology_channel = viral_asset_report.channel if viral_asset_report else "mixed"
        methodology_genres = viral_asset_report.genre_tags if viral_asset_report else ["unknown"]

        def methodology_context_for(stage: MethodologyStage) -> MethodologyContext:
            return retrieve_methodology_context(
                methodology_cards,
                stage=stage,
                channel=methodology_channel,
                genre_tags=methodology_genres,
                source_strength_profile=source_strength_profile,
            )

        cached_episode_context = read_cached_artifact("episode_context", EpisodeContext)
        if cached_episode_context is not None:
            record_cached_stage("episode_context")
            episode_context = cached_episode_context
        else:
            episode_context = run_stage(
                "episode_context",
                lambda: EpisodeContextResolver(tracked_llm).run(
                    source_text,
                    previous_context,
                    source_analysis,
                    round_number,
                    target_episode_count,
                    resolved_episodes_per_round,
                    viral_asset_report=viral_asset_report,
                    methodology_context=methodology_context_for(
                        MethodologyStage.EPISODE_CONTEXT,
                    ),
                ),
            )
            episode_context = run_stage(
                "normalize_episode_context",
                lambda: normalize_episode_context_range(
                    episode_context,
                    round_number=round_number,
                    previous_context=previous_context,
                    target_episode_count=target_episode_count,
                    episodes_per_round=resolved_episodes_per_round,
                ),
            )
            self.store.write_round_artifact(round_number, "episode_context", episode_context)

        cached_story_bible = read_cached_artifact("story_bible", StoryBible)
        if cached_story_bible is not None:
            record_cached_stage("story_bible")
            story_bible = cached_story_bible
        else:
            prior_story_bible = read_prior_round_artifact("story_bible", StoryBible)
            if prior_story_bible is not None:
                record_cached_stage("story_bible")
                story_bible = prior_story_bible
                self.store.write_round_artifact(round_number, "story_bible", story_bible)
            else:
                story_bible = run_stage(
                    "story_bible",
                    lambda: InternalBibleBuilder(tracked_llm).run(
                        source_text,
                        source_analysis,
                        episode_context,
                        viral_asset_report=viral_asset_report,
                        methodology_context=methodology_context_for(
                            MethodologyStage.STORY_BIBLE,
                        ),
                    ),
                )
                self.store.write_round_artifact(round_number, "story_bible", story_bible)

        series_structure_plan = None
        if viral_asset_report is not None:
            cached_series_structure_plan = read_cached_artifact(
                "series_structure_plan",
                SeriesStructurePlan,
            )
            if cached_series_structure_plan is not None:
                record_cached_stage("series_structure_plan")
                series_structure_plan = cached_series_structure_plan
            else:
                series_structure_plan = run_stage(
                    "series_structure_plan",
                    lambda: SeriesStructurePlanner(tracked_llm).run(
                        source_text,
                        source_analysis,
                        episode_context,
                        story_bible,
                        viral_asset_report,
                        previous_context,
                        target_episode_count,
                        methodology_context=methodology_context_for(
                            MethodologyStage.SERIES_STRUCTURE,
                        ),
                    ),
                )
                series_structure_plan = run_stage(
                    "normalize_series_structure_plan",
                    lambda: series_structure_plan.model_copy(
                        update={
                            "target_episode_count": target_episode_count,
                            "target_episode_range": episode_context.target_episode_range,
                        },
                    ),
                )
                self.store.write_round_artifact(
                    round_number,
                    "series_structure_plan",
                    series_structure_plan,
                )

        episode_source_packets = cached_stage(
            "episode_source_packets",
            "episode_source_packets",
            EpisodeSourcePackets,
            lambda: build_episode_source_packets(
                source_text=source_text,
                episode_context=episode_context,
                series_structure_plan=series_structure_plan,
                target_episode_count=target_episode_count,
            ),
        )
        source_bible_conflicts = run_stage(
            "source_bible_conflicts",
            lambda: story_bible_source_packet_conflicts(
                story_bible,
                episode_source_packets,
            ),
        )
        if source_bible_conflicts:
            self.store.write_text_artifact(
                round_number,
                "source_bible_conflicts.md",
                "\n".join(
                    [
                        "# Source/Bible Contract Conflicts",
                        "",
                        "以下 Story Bible forbidden_changes 与当前集 source packet 必留资产冲突，"
                        "本轮按原文 source packet 优先处理，并从 Bible 禁止项中移除：",
                        "",
                        *[f"- {rule}" for rule in source_bible_conflicts],
                    ]
                ),
            )
            story_bible = run_stage(
                "normalize_story_bible_against_source_packets",
                lambda: normalize_story_bible_against_source_packets(
                    story_bible,
                    episode_source_packets,
                ),
            )
            self.store.write_round_artifact(round_number, "story_bible", story_bible)

        production_spec = cached_stage(
            "production_spec",
            "production_spec",
            ProductionSpec,
            build_production_spec,
        )
        source_annotation = cached_stage(
            "source_annotation",
            "source_annotation",
            SourceAnnotation,
            lambda: build_source_annotation(
                source_text=source_text,
                source_analysis=source_analysis,
                episode_context=episode_context,
                story_bible=story_bible,
                episode_source_packets=episode_source_packets,
            ),
        )
        episode_cut_table = cached_stage(
            "episode_cut_table",
            "episode_cut_table",
            EpisodeCutTable,
            lambda: build_episode_cut_table(
                episode_context=episode_context,
                episode_source_packets=episode_source_packets,
            ),
        )

        episode_plan = None
        if variant_uses_episode_plan(generation_variant):
            cached_episode_plan = read_cached_artifact("episode_plan", EpisodePlan)
            if cached_episode_plan is not None:
                record_cached_stage("episode_plan")
                episode_plan = cached_episode_plan
            else:
                episode_plan = run_stage(
                    "episode_plan",
                    lambda: EpisodeBeatPlanner(tracked_llm).run(
                        source_text,
                        source_analysis,
                        episode_context,
                        story_bible,
                        previous_context,
                        viral_asset_report=viral_asset_report,
                        series_structure_plan=series_structure_plan,
                        methodology_context=methodology_context_for(
                            MethodologyStage.EPISODE_PLAN,
                        ),
                    ),
                )
                episode_plan = run_stage(
                    "normalize_episode_plan",
                    lambda: episode_plan.model_copy(
                        update={
                            "variant": generation_variant,
                            "target_episode_range": episode_context.target_episode_range,
                        },
                    ),
                )
                self.store.write_round_artifact(round_number, "episode_plan", episode_plan)

        methodology_context = cached_stage(
            "methodology_context",
            "methodology_context",
            MethodologyContext,
            lambda: methodology_context_for(MethodologyStage.SCRIPT_GENERATION),
        )
        runtime_methodology_cards = [card.name for card in methodology_context.cards]
        script_methodology_context: MethodologyContext | None = None
        write_runtime_report()

        if episode_plan is not None:
            episode_plan = run_stage(
                "sanitize_episode_plan",
                lambda: sanitize_episode_plan_against_source_packets(
                    episode_plan,
                    episode_source_packets,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                "episode_plan_sanitized",
                episode_plan,
            )

        script_generator = ScriptBatchGenerator(
            tracked_llm,
            episode_writer=write_episode_artifact,
        )
        script_batch = cached_stage(
            "script_batch",
            "script_batch",
            ScriptBatch,
            lambda: (
                script_generator.run_episode_batch(
                    source_text,
                    source_analysis,
                    episode_context,
                    story_bible,
                    previous_context,
                    "",
                    episode_plan=episode_plan,
                    viral_asset_report=viral_asset_report,
                    series_structure_plan=series_structure_plan,
                    methodology_context=script_methodology_context,
                    episode_source_packets=episode_source_packets,
                    production_spec=production_spec,
                    source_annotation=source_annotation,
                    episode_cut_table=episode_cut_table,
                )
                if use_episode_first_script_generation()
                else script_generator.run(
                    source_text,
                    source_analysis,
                    episode_context,
                    story_bible,
                    previous_context,
                    "",
                    round_number,
                    target_episode_count,
                    episode_plan=episode_plan,
                    viral_asset_report=viral_asset_report,
                    series_structure_plan=series_structure_plan,
                    methodology_context=script_methodology_context,
                    episode_source_packets=episode_source_packets,
                    production_spec=production_spec,
                    source_annotation=source_annotation,
                    episode_cut_table=episode_cut_table,
                )
            ),
        )
        quality_methodology_context = methodology_context_for(MethodologyStage.QUALITY_GATE)

        checker = ContinuityBoomChecker(tracked_llm)
        quality_report = run_stage(
            "quality_report",
            lambda: checker.run(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                episode_plan=episode_plan,
                methodology_context=quality_methodology_context,
            ),
        )

        def apply_local_quality_gates(
            current_script_batch: ScriptBatch,
            current_quality_report: QualityReport,
            artifact_prefix: str,
        ) -> QualityReport:
            provisional_context = provisional_next_round_context(
                current_script_batch,
                previous_context,
            )
            local_adaptation_quality = run_stage(
                f"{artifact_prefix}_adaptation_quality",
                lambda: build_adaptation_quality_report(
                    source_text=source_text,
                    source_analysis=source_analysis,
                    episode_context=episode_context,
                    story_bible=story_bible,
                    script_batch=current_script_batch,
                    next_round_context=provisional_context,
                    previous_context=previous_context,
                    viral_asset_report=viral_asset_report,
                    episode_plan=episode_plan,
                    series_structure_plan=series_structure_plan,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_adaptation_quality",
                local_adaptation_quality,
            )
            local_methodology_quality = run_stage(
                f"{artifact_prefix}_methodology_quality",
                lambda: build_methodology_quality_report(
                    source_analysis=source_analysis,
                    script_batch=current_script_batch,
               

... [TRUNCATED FOR REVIEW PACK] ...

```


## File: `src/novel_drama_engine/prompts.py`
```
from __future__ import annotations

import json
import os
import re

from pydantic import BaseModel

from novel_drama_engine.methodology import render_methodology_context
from novel_drama_engine.models import MethodologyContext


def dump_model(name: str, model: BaseModel | None) -> str:
    if model is None:
        return f"{name}: null"
    return f"{name}: {model.model_dump_json(indent=2)}"


def section(title: str, body: str) -> str:
    return f"【{title}】\n{body.strip()}"


def prompt_block(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def lean_flow_authority_section() -> str:
    return section(
        "P0 轻链路主输入",
        "\n".join(
            [
                "source_annotation 是首稿最高优先级基准；任何 episode_plan、series_structure_plan、methodology_context 与它冲突时，以 source_annotation 和 episode_source_packets 为准。",
                "episode_cut_table 决定本轮分集边界、核心冲突和 60-90s 目标；不得跨集挪用。",
                "production_spec 决定创作稿格式、VO/OS、对白和交付规则；首稿先写 creative_script。",
                "episode_plan / series_structure_plan / methodology_context 只作辅助，不得覆盖原文标注稿。",
            ]
        ),
    )


def _scene_line_digest(line: object) -> str:
    kind = str(getattr(line, "kind", "") or "")
    speaker = getattr(line, "speaker", None)
    emotion = getattr(line, "emotion", None)
    text = str(getattr(line, "text", "") or "")
    label = kind
    if speaker:
        label += f"/{speaker}"
    if emotion:
        label += f"({emotion})"
    return f"{label}: {text}"


def _episode_lines(episode: object) -> list[object]:
    lines: list[object] = []
    for scene in getattr(episode, "scenes", []) or []:
        lines.extend(getattr(scene, "lines", []) or [])
    return lines


def render_script_batch_digest(
    name: str,
    script_batch: BaseModel | None,
    *,
    opening_lines: int = 8,
    tail_lines: int = 12,
) -> str:
    if script_batch is None:
        return f"{name}: null"
    episodes = []
    for episode in getattr(script_batch, "episodes", []) or []:
        lines = _episode_lines(episode)
        scenes = [
            {
                "heading": getattr(scene, "heading", ""),
                "characters": getattr(scene, "characters", []),
                "line_count": len(getattr(scene, "lines", []) or []),
            }
            for scene in getattr(episode, "scenes", []) or []
        ]
        episodes.append(
            {
                "episode": getattr(episode, "episode", None),
                "title": getattr(episode, "title", ""),
                "hook_3s": getattr(episode, "hook_3s", ""),
                "main_emotion": getattr(episode, "main_emotion", ""),
                "scene_count": len(getattr(episode, "scenes", []) or []),
                "visible_line_count": len(lines),
                "scene_skeleton": scenes,
                "opening_lines": [
                    _scene_line_digest(line) for line in lines[:opening_lines]
                ],
                "tail_lines": [
                    _scene_line_digest(line) for line in lines[-tail_lines:]
                ],
                "cliffhanger": getattr(episode, "cliffhanger", ""),
                "state_update": getattr(episode, "state_update", {}),
            }
        )
    return f"{name}: {json.dumps({'episodes': episodes}, ensure_ascii=False, indent=2)}"


def script_prompt_mode() -> str:
    raw = os.environ.get("NOVEL_DRAMA_SCRIPT_PROMPT_MODE", "creative")
    normalized = raw.strip().lower().replace("-", "_")
    if normalized in {"full", "legacy", "shooting", "strict"}:
        return "full"
    return "creative"


def stage_system(
    role: str,
    mission: str,
    method: str,
    output_discipline: str,
    failure_modes: str,
) -> str:
    return prompt_block(
        section("岗位", role),
        section(
            "Skill 边界",
            (
                "本阶段按一个可复用内部 Skill 包运行：只消费本阶段输入资产，只产出 schema 要求的结构化 artifact；"
                "不与用户对话，不增加确认门，不把内部分析字段写进用户可见正片。"
            ),
        ),
        section("任务", mission),
        section("专业方法", method),
        section("输出纪律", output_discipline),
        section(
            "验收门",
            (
                "交付前自检：输入资产已被引用，执行步骤可复现，输出字段满足 schema，"
                "关键结论有原文/上游 artifact 依据，失败模式已被主动规避。"
            ),
        ),
        section("失败模式", failure_modes),
    )


def stage_instruction(
    task: str,
    decision_order: str,
    output_contract: str,
    craft_standard: str,
    forbidden: str,
) -> str:
    return prompt_block(
        section(
            "Skill 包运行规范",
            (
                "这是生产流水线中的一个内部 Skill：先明确输入资产，再按步骤执行，"
                "再按输出契约生成 schema artifact，最后用验收门自检。不等待用户确认，不输出过程解释。"
            ),
        ),
        section("任务", task),
        section(
            "输入资产",
            (
                "只能使用本 prompt 中提供的小说原文、previous_context、source_analysis、"
                "viral_asset_report、episode_context、story_bible、series_structure_plan、"
                "episode_plan、script_batch、quality_report 等资产。缺失资产要在允许范围内保守推断，"
                "不得凭空引入与原文冲突的人物、地点、道具、身份线或平台卖点。"
            ),
        ),
        section("通用改编合同", SOURCE_ADAPTATION_CONTRACT),
        section("决策顺序", decision_order),
        section("执行步骤", decision_order),
        section("输出契约", output_contract),
        section("专业标准", craft_standard),
        section(
            "验收门",
            (
                "输出前逐项检查：是否覆盖目标集数/目标字段；是否有可见动作、证据、道具、信息差或关系变化；"
                "是否避免抽象词和模板串戏；是否能被下一阶段直接消费。任何不满足项都要在本次输出内自修正。"
            ),
        ),
        section(
            "失败修复",
            (
                "如果发现内容太短、缺集、题材错配、镜头不可执行、结尾钩子说明化、内部字段外露、"
                "或信息增量不足，必须直接重写对应字段/集数，不要解释原因，也不要把问题留给用户。"
            ),
        ),
        section("禁止事项", forbidden),
    )


GLOBAL_PROFESSIONAL_FRAME = (
    "本系统采用“题材诊断 -> 爆款资产提纯 -> 集数/上下文解析 -> 系统 Story Bible -> "
    "全剧结构 -> 单集戏剧工程 -> 可拍摄脚本 -> 质量门禁 -> 状态回写”的流水线。"
    "每一阶段都只做自己的专业职责，不能越权写成下一阶段成稿，也不能要求用户确认。"
)

SOURCE_ASSET_TAXONOMY_RULE = (
    "原文资产分级：C0 不可改事实（人物动机、主动方、因果顺序、关键决定、关系状态、已存在证据）；"
    "C1 必保名场面（高刺激开场、强反差画面、情绪爆点、关键道具、原文金句、公开羞辱/打脸节点）；"
    "C2 可视听化资产（内心戏、长叙述、环境描写、感官细节，可转成特写、OS、动作、音效、镜头遮挡）；"
    "C3 可压缩资产（过渡、寒暄、背景补充、低信息支线，可合并进对白或动作）；"
    "C4 禁止新增（会改变动机、主动方、决策时机、证据来源、人物性格、关系结论或剧情解法的编造动作/道具/狠话）。"
)

HOOK_STRATEGY_RULE = (
    "开场钩子双模式：先判断原文是否已有 C1 天然钩子。"
    "原文有强钩子时，必须保护钩子的核心危险、反差、羞辱、误会、身份或证据张力，只能合规视听化，不能删除或降级成普通开场；"
    "遇到敏感/暧昧/暴力/压迫型钩子，用手部、道具、衣料/遮挡、镜头扫过、声音先入、反应特写和空间压迫表达，不把冲突拿掉。"
    "原文无强钩子时，系统必须补一个事实兼容型钩子，可选结果前置、冲突前置、信息差前置、道具前置、关系错位前置、威胁前置；"
    "补钩子只能从 C0/C1/C2 推导，不能凭空制造主角没有的欲望、对手没有的行为、原文不存在且改变因果的证据或道具。"
)

ADAPTATION_LICENSE_RULE = (
    "改编许可边界：允许前置、压缩、换场、合并低价值段落、增加镜头细节、补动作衔接、把内心戏转 OS/特写/沉默决定；"
    "谨慎允许补短对白、补反应镜头、补中间动作，但必须服务原文已有情绪或信息；"
    "禁止改变 C0：不得改变主动方、人物核心动机、核心决定发生时机、因果顺序、关系状态、既有承诺/证据/协议/身份归属；"
    "不得把深思熟虑改成临时起意、把被动承受改成主动索取、把克制决绝改成歇斯底里、把原文强反差改成泛化冲突。"
)

FIDELITY_DRIFT_RULE = (
    "通用跑偏阻断：如果原文是“对手主动承诺/诱导/准备惊喜”，不得改成主角主动索要资源、名分、奖项或好处；"
    "如果原文是“协议/证据/离开决定早已准备”，不得改成现场赌气、临时起意或一怒之下；"
    "如果原文人物是沉默、僵住、克制、冰冷、决绝，不得改成喊口号式宣战或歇斯底里狠话；"
    "如果原文开场含暧昧、危险、被镜头拍到、身体距离、衣料/手部/遮挡等高张力资产，必须合规视听化保留压力，"
    "不能直接删除成普通对话开场。"
)

THREE_THREE_THREE_RHYTHM_RULE = (
    "3-3-3 节奏规则：前 3 秒必须用可见冲突、悬念或反转留人；"
    "每约 30 秒必须有情绪波动、信息增量或剧情推进之一；"
    "每集结尾必须用反转、危机或选择钩子截断，并能被下一集开头承接。"
    "不满足的段落视为水段，必须删除、压缩或改成可拍冲突。"
)

RELATIONSHIP_READABILITY_RULE = (
    "人物关系可读性：任何两个角色第一次同框、关系身份发生反转，或角色使用昵称/姐/哥/嫂子/霍总等熟称时，"
    "必须在同场前 3-5 行用一个可拍动作、称呼回应或短台词交代观众需要知道的表层关系。"
    "如果戏剧点是“认识这个人但不知道真实身份/资源/阵营”，台词必须限定疑问对象，例如"
    "“我知道你是小雅，可你哪来的私人飞机？”“你不是我的助理吗？”"
    "禁止写成先亲密称呼、后又泛问“你到底是谁/我们认识吗”的矛盾表达，"
    "否则观众会看不懂两人到底认不认识。"
    "隐藏身份可以留悬念，但表层关系、角色已知信息和未知层级必须清楚。"
)

CHARACTER_AGENCY_RULE = (
    "人物行动权规则：主角必须按原文情绪资产递进，尤其是受压、震惊、僵住、心碎、克制、清醒、决绝等阶段，"
    "要写成“承受/识别 -> 做决定 -> 采取动作 -> 付代价或反击”的可拍链路；"
    "不得在原文没有重生、预知、马甲、提前布局或明确信息差时，把主角过早写成全知全能式开杀。"
    "支持型角色只能提供选择权、证据、退路、后盾和安全感，不能替主角签字、替主角决定、替主角报仇或一手解决核心冲突；"
    "对手/反派每轮必须有主动设局、反制、施压、毁证、挑拨、封锁或升级动作，不能只写惊慌、陪衬或躲在强者身边。"
)

EVENT_LEDGER_RULE = (
    "全局事件账本：高价值名场面和关键结果必须按“首次兑现 -> 后果承接 -> 反扑升级”推进，"
    "不能在不同集重复写成新的同类事件。亲密关系公开/曝光、不可逆解约/离婚/退婚/辞职、"
    "身份/真相结论公开、权威裁决、机构/法务/舆论清算等一旦首次演出，"
    "后续只能写人物反应、舆论余波、对手反扑、证据推进或代价扩大，不能重新再演一遍。"
    "身份坐实、机构处罚、舆论反转、平台封禁、家族/公司/宗门/朝廷清算必须有可见证据链："
    "证据来源 -> 保存/验证/公证/权威确认 -> 公开或裁决节点 -> 外界反应 -> 对手后果，"
    "禁止一句“资本出手/热搜爆了/权威一句话”直接解决。"
)

SOURCE_ADAPTATION_CONTRACT = prompt_block(
    SOURCE_ASSET_TAXONOMY_RULE,
    HOOK_STRATEGY_RULE,
    ADAPTATION_LICENSE_RULE,
    FIDELITY_DRIFT_RULE,
    THREE_THREE_THREE_RHYTHM_RULE,
    RELATIONSHIP_READABILITY_RULE,
    CHARACTER_AGENCY_RULE,
    EVENT_LEDGER_RULE,
    (
        "所有阶段必须先保护 C0/C1，再做爆款化；爆款化不是编造新因果，而是把原文资产前置、压缩、视听化、节奏化。"
        "如果上游未显式给出分级，本阶段要在本 prompt 内临时完成分级并按分级执行。"
    ),
)

SOURCE_FIDELITY_QUALITY_RULE = (
    "原著保真质检：逐集核对是否删除了 C1 天然钩子、强反差或情绪爆点；"
    "是否把 C0 的主动方、动机、因果顺序、关键决定时机、证据来源改掉；"
    "是否新增 C4 编造道具/动作/狠话并让它改变剧情；"
    "是否让角色说出与 Story Bible 台词风格或原文欲望相反的话。"
    "必须检查人物关系可读性：第一次同框、熟称、身份反转或阵营反转时，观众能否在同场前 3-5 行看懂"
    "他们表层上是否认识、各自知道什么、不知道什么。"
    "如果出现“先叫小雅/姐姐/哥/霍总等熟称，后又泛问你到底是谁/我们认识吗”，"
    "但没有限定是在问真实身份、资源来源或隐藏阵营，必须 needs_rewrite。"
    "必须硬拦通用跑偏：对手主动承诺被改成主角主动索取、预谋决定被改成现场冲动、克制决绝被改成歇斯底里、"
    "暧昧/危险/镜头拍到等高张力开场被删除或降级。"
    "必须检查人物行动权：原文存在受压/震惊/克制递进时，脚本不得过早全知全能式开杀；"
    "支持型角色不得替主角做核心决定；对手/反派不得只惊慌陪衬，必须有可见主动反制。"
    "任一项命中必须 needs_rewrite，rewrite_instruction 要写明回到哪条 C0/C1 资产、删除哪条 C4 编造、如何用镜头补强而不是改因果。"
)

SOURCE_FIDELITY_GENERATION_RULE = (
    "source_fidelity_target：每集源文相似度不得低于 5/10；低于 5/10 的稿件视为无效输出。"
    "这是小说改剧本的生成期硬指标，不是后置质检备注；写稿时必须先满足源文保真，再做爆款化、镜头化和节奏强化。"
    "必须把本集 source packet / 原文片段里的 C0 不可改事实、C1 必保名场面和 C2 可视听化资产显性落到正片的画面、对白、道具、行动或 OS 中。"
    "不得用新人物、新证据、新道具、新狠话、新解法替代原文核心钩子、人物动机、主动方逻辑、关系状态或关键决定时机。"
    "每集返回 EpisodeScript 前必须先自检 source_fidelity_target：若本集与 source packet / 原文片段严重不符、缺少 C0/C1、或新增 C4 改变因果，"
    "必须在生成阶段立即重写该集，不要把问题留给质量门禁或用户。"
)

SHOT_LINKAGE_RULE = (
    "镜头衔接硬验收：整集至少 3 条 action 必须原文包含以下任一衔接词："
    "切到、切回、反打、接、视线匹配、声音先入、音效、BGM、道具特写、前景。"
    "不要只写“中近景，人物做事”；要写“中近景推近A，杯子占前景，切到B发白的指节”。"
)

ACTION_LINE_TEMPLATE_RULE = (
    "action 行硬格式：每条 action.text 必须以“△景别+运镜”开头，例如"
    "“△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节”。"
    "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头。"
)

FINAL_TWO_LINE_RULE = (
    "最后两行硬模板：倒数第 2 行必须是 action，写清景别+运镜+道具/动作+衔接词；"
    "最后 1 行必须是强对白/强 OS/强 VO，或一个动作未完成的道具特写。"
    "最后两行禁止黑屏、转场、画面定格、旁白总结、普通 OS、看点说明或只写情绪。"
)

INFO_INCREMENT_RULE = (
    "信息增量硬验收：每集必须把 SeriesEpisodeOutline.information_increment 和 "
    "EpisodeDramaPlan.audience_information_gap 演成可见事件、证据、关系变化、敌方策略或道具状态。"
    "从第 2 集开始，不能只延续上一集争执，至少新增 1 个观众之前不知道、角色当场不知道或角色误判的信息差。"
)

VISIBLE_SCRIPT_DENSITY_RULE = (
    "正片密度硬验收：本地质检只统计 scene.lines 渲染出来的用户可见正片文本，"
    "不统计 hook_3s、main_emotion、watch_reason、cliffhanger、state_update 或其他 JSON 字段长度。"
    "不能用长 watch_reason、长 state_update、长标题或长 cliffhanger 冒充正片字数。"
    "每集 scenes 必须 2-5 场；每集 scene.lines 合计至少 28 行，其中 action 至少 10 行、"
    "dialogue/os/vo 至少 18 行；单场不要少于 8 行。"
)


def episode_range_contract(episode_context: BaseModel) -> str:
    raw_range = str(getattr(episode_context, "target_episode_range", "") or "")
    match = re.fullmatch(r"EP(\d+)(?:-EP(\d+))?", raw_range.strip())
    if not match:
        return (
            "episodes 数组必须完整覆盖 episode_context.target_episode_range；"
            "不得缺集、跳集、合并集数或只输出摘要。"
        )
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    numbers = list(range(start, end + 1))
    ep_codes = "、".join(f"EP{number:02d}" for number in numbers)
    raw_numbers = "、".join(str(number) for number in numbers)
    return (
        f"episode_context.target_episode_range={raw_range}，episodes 数组必须正好包含 "
        f"{len(numbers)} 个 EpisodeScript，episode 字段必须按顺序等于 {raw_numbers}（即 {ep_codes}）。"
        "不得少集、跳集、重复集、合并多集到一集，也不得输出范围外集数。缺任一集就是失败。"
    )


def source_material_section(
    source_text: str | None,
    *,
    episode_source_packet: BaseModel | None = None,
    episode_source_packets: BaseModel | None = None,
) -> str:
    if episode_source_packet is not None:
        return section(
            "本集原文包",
            prompt_block(
                dump_model("episode_source_packet", episode_source_packet),
                (
                    "脚本阶段只能把 source_excerpt、C0/C1/C2/C3/C4、golden_lines 和 "
                    "handoff_requirement 当作本集原文依据；不得回到全文自由寻找新剧情。"
                ),
            ),
        )
    if episode_source_packets is not None:
        return section(
            "本轮原文包",
            prompt_block(
                dump_model("episode_source_packets", episode_source_packets),
                (
                    "整批脚本阶段必须逐集使用对应 packet，不得跨集挪用原文资产，"
                    "不得把其他 packet 的事件提前写入当前集。"
                ),
            ),
        )
    return f"小说原文：\n{source_text or ''}"


def _compact_values(value: object, *, limit: int = 5) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        raw_items = [f"{key}: {item}" for key, item in value.items()]
    elif isinstance(value, (list, tuple, set)):
        raw_items = [str(item) for item in value]
    else:
        raw_items = [str(value)]
    return [item for item in raw_items if item.strip()][:limit]


def script_reference_context_section(
    *,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    previous_context: BaseModel | None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
) -> str:
    source_summary = {
        "characters": _compact_values(getattr(source_analysis, "characters", None)),
        "conflicts": _compact_values(getattr(source_analysis, "conflicts", None), limit=3),
        "candidate_hooks": _compact_values(
            getattr(source_analysis, "candidate_hooks", None),
            limit=3,
        ),
    }
    context_summary = {
        "target_episode_range": getattr(episode_context, "target_episode_range", ""),
        "story_stage": str(getattr(episode_context, "story_stage", "")),
        "must_carry_context": _compact_values(
            getattr(episode_context, "must_carry_context", None),
            limit=3,
        ),
        "forbidden_reveals": _compact_values(
            getattr(episode_context, "forbidden_reveals", None),
            limit=3,
        ),
    }
    previous_summary = None
    if previous_context is not None:
        previous_summary = {
            "current_episode": getattr(previous_context, "current_episode", None),
            "open_hooks": _compact_values(getattr(previous_context, "open_hooks", None), limit=3),
            "relationship_changes": _compact_values(
                getattr(previous_context, "relationship_changes", None),
                limit=3,
            ),
        }
    upstream_notes = {
        "source_analysis_digest": source_summary,
        "episode_context_boundary": context_summary,
        "previous_context_handoff_digest": previous_summary,
        "viral_asset_report": "仅作名场面/题材参考；必须能被 source_annotation 或当前集 source packet 证明。"
        if viral_asset_report is not None
        else None,
        "series_structure_plan": "仅作全剧节奏参考；本集剧情边界以 episode_cut_table 和 source_annotation 为准。"
        if series_structure_plan is not None
        else None,
    }
    return section(
        "脚本阶段受控参考",
        json.dumps(upstream_notes, ensure_ascii=False, indent=2, default=str),
    )


def _is_source_contract_repair_packet(packet: BaseModel | None) -> bool:
    if packet is None:
        return False
    targets = getattr(packet, "source_evidence_targets", None) or []
    baseline_policy = str(getattr(packet, "baseline_policy", "") or "")
    return bool(targets) or "原文契约" in baseline_policy or "唯一内容基准" in baseline_policy


def repair_packet_baseline_instruction(packet: BaseModel | None) -> str:
    if _is_source_contract_repair_packet(packet):
        return (
            "current_episode_repair_packet.baseline_policy 是修复基准；"
            "若 baseline_policy 写明“当前集原文契约是唯一内容基准”，"
            "baseline_episode_text 只用于定位旧稿失败，不得保护其中无 source packet/source_annotation 证明的标题、场景、道具、台词或因果。"
            "protected_elements 只保留 episode 和可被当前集原文证明的承接边界，不能照抄旧稿错误。"
            "current_episode_repair_packet.source_evidence_targets 是本集必须补回的原文证据；"
            "只能把这些资产补成可见动作、道具、关系反应或短对白，不能借此新增无原文依据的新因果。"
        )
    return (
        "current_episode_repair_packet.baseline_episode_text 是当前集旧稿的文本基准；"
        "除 editable_targets 指向的缺口外，protected_elements 必须照抄或语义等价保留。"
        "current_episode_repair_packet.source_evidence_targets 是本集必须补回的原文证据；"
        "只能把这些资产补成可见动作、道具、关系反应或短对白，不能借此新增无原文依据的新因果。"
    )


def polish_scope_instruction(packet: BaseModel | None) -> str:
    if _is_source_contract_repair_packet(packet):
        return (
            "若 current_episode_repair_packet.baseline_policy 写明原文契约基准，"
            "existing_episode 只用于定位旧稿问题；润色只能保留可由当前集 source packet/source_annotation 证明的"
            "场景、人物、动作、对白、信息状态和主线事实。"
            "必须优先遵守 current_episode_repair_packet.allowed_change_scope，"
            "source_evidence_targets 是本集必须补回的原文证据；不得为了钩子保留旧稿中无原文依据的新因果。"
        )
    return (
        "current_episode_repair_packet.baseline_episode_text 是局部润色文本基准；"
        "除最后 8-12 行、必要短对白/OS/VO 补足、OS 后紧跟动作外，必须保留 existing_episode 的"
        "标题、场景顺序、人物、已合格 action、信息状态和主线事实。"
        "必须优先遵守 current_episode_repair_packet.allowed_change_scope，"
        "current_episode_repair_packet.source_evidence_targets 是本集必须补回的原文证据；"
        "只能补成可见动作、道具、关系反应或短对白，不能新增无原文依据的新因果。"
        "不得改动 protected_elements 中的事实、人物关系、主动方、证据来源和上下集边界。"
    )


SOURCE_PARSER_SYSTEM = stage_system(
    "你是短剧小说解析器和素材清洗器，负责把原文拆成可拍摄生产资产。",
    (
        "只输出符合 schema 的可拍摄生产资产，不是剧情总结，不写读后感、不写人物小传、"
        "不做用户确认。每个资产都要服务拍摄、剪辑或 AI 视频后链路。"
    ),
    (
        "按“题材模板识别 -> 原文资产 C0-C4 分级 -> 主角欲望/阻力定位 -> 可见动作拆分 -> "
        "道具/场景/强对白提取 -> 低价值段落处理”的顺序工作。candidate_hooks 只能是可见动作、"
        "强对白、道具露出、威胁或反转，不能写成“观众想看什么”的抽象看点。"
    ),
    (
        "优先提取人物关系、场景、道具、可见动作、强对白、威胁、反转和低价值段落处理方式。"
        "每条信息都要能被后续阶段消费。"
    ),
    (
        "题材模板错配是严重错误：男频穿越、大宋、武大郎、金莲、西门庆、经商护妻类不得套"
        "真假千金、豪门宴会或现代豪门继承模板；古言宅斗、真假千金、赘婿战神等也不能混套。"
    ),
)
VIRAL_ASSET_SYSTEM = stage_system(
    "你是网文改爆款竖屏短剧的前置评估器，负责提纯爆款基因而不是写宣传文案。",
    (
        "提纯可被拍出来的强设定、核心困境、名场面、情绪资产、金句和改编风险。"
        "ViralAssetReport 是系统内部生产资产。"
    ),
    (
        "按“频道/题材/爽感诊断 -> 核心困境提炼 -> 原文资产 C0-C4 分级 -> 名场面分级 -> 情绪曲线抽样 -> "
        "风险替换策略”的顺序工作。"
    ),
    (
        "只服务后续 episode_context、Story Bible、SeriesStructurePlan、EpisodeDramaPlan 和脚本生成；"
        "名场面必须能落到人物、地点、动作和后果。"
    ),
    "不能写成用户可见卖点文案、投放文案、封面标题或推荐语，不能把抽象情绪当名场面。",
)
EPISODE_CONTEXT_SYSTEM = stage_system(
    "你是短剧集数和上下文解析器，负责把原文自动路由到本轮集数。",
    (
        "必须根据原文、目标总集数、round_number 和 previous_context 系统自动识别本轮轮次、"
        "本轮对应集数、原文锚点和承接约束；不得让用户确认或选择方向。"
    ),
    (
        "按“读取 previous_context.current_episode -> 计算剩余集数 -> 定义 EP 范围 -> "
        "映射原文事件 -> 写承接/禁止揭示/改编动作”的顺序工作。"
    ),
    (
        "previous_context 存在时，本轮必须从 previous_context.current_episode + 1 开始，只向后推进，"
        "不得重复已完成集数。source_to_episode_mapping 和 adaptation_actions 必须是可执行映射。"
    ),
    "不能泛写“承接上一轮/推进剧情”，不能让男频穿越/大宋/武大郎套真假千金或豪门宴会模板。",
)
BIBLE_SYSTEM = stage_system(
    "你是短剧 Story Bible 构建器，负责维护系统内部人物和世界状态合同。",
    (
        "Story Bible 是系统自动维护的内部状态，用于锁定主线、人设标签、关系、说话方式、"
        "不可改事实和禁区；不要请求用户确认。"
    ),
    (
        "按“C0 不可改事实 -> 人物功能合同 -> 关系张力 -> 台词风格 -> 禁止改动项”的顺序工作。"
    ),
    (
        "人物档案必须可被后续轮次直接执行，不能写成读者分析或等待人工补充。"
        "每个核心角色都要服务戏剧功能和短台词生成。"
    ),
    "不能把功能性配角写成多功能慢热人物，不能给反派复杂洗白，不能提前公开尚未演出的悬念。",
)
SERIES_STRUCTURE_SYSTEM = stage_system(
    "你是爆款竖屏短剧全剧结构设计师，负责把线性小说改造成可连续生产的剧集结构。",
    (
        "把原文重构为全剧节奏、每集信息增量、断点类型、原文锚点和禁水集规则。"
        "SeriesStructurePlan 是后续脚本生成的内部 SOP 环节。"
    ),
    (
        "按“全剧体量 -> 开篇钩子双模式 -> 三层冲突 -> 情绪曲线 -> 小/大高潮节拍 -> "
        "逐集信息增量 -> 断点设计”的顺序工作。"
    ),
    (
        "episode_outlines 必须可直接喂给单集设计和脚本阶段；ending_hook 要能写成最后 2 行的动作、"
        "对白或道具特写。"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "不写文学梗概，不制造水集，不增加用户确认门，不用“身份悬念推进/观众要看”代替具体断点。",
)
EPISODE_PLAN_SYSTEM = stage_system(
    "你是 EpisodeDramaPlan 戏剧工程师，负责把集纲转成单集戏剧机械图。",
    (
        "只做单集戏剧工程设计，不写正片脚本、分场正文或完整对白。每集必须锁定戏剧引擎、"
        "误认知/真相差、信息差、3 个以上物理动作链、场景动态、至少 2 次情绪转向、"
        "三波拉扯、假打脸、钥匙预埋、最狠短台词和结尾截断。"
    ),
    (
        "按“原文资产分级 -> 主角误认知 -> 行动链 -> 对手反制 -> 假打脸 -> 钥匙预埋 -> "
        "临门截断”的顺序设计。"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "所有字段都要可执行，并能被 Script 阶段直接改写成镜头、动作和短台词。",
    "不能写“增强爽感/制造悬念/推进剧情”这类抽象词，不能把单集设计写成完整剧本。",
)
SCRIPT_SYSTEM = stage_system(
    "你是爆款竖屏短剧分镜编剧，负责输出可直接拍摄、可交给 AI 视频后链路执行的剧本。",
    (
        "正片必须强冲突开场、短台词、镜头动作详细、镜头衔接清楚、每集留强钩。"
        "Hook、main_emotion、主情绪、watch_reason、消费理由等字段只作为内部元数据，"
        "禁止作为用户可见 scene lines 展示。"
    ),
    (
        "按“原文钩子保护/事实兼容补钩 -> 前三秒可见冲突 -> 三波拉扯 -> 假打脸/钥匙兑现 -> 反派最后一装 -> "
        "动作或证据截断”的顺序写。"
    ),
    (
        "每条 action 都要能指导 AI 视频：景别、运镜、构图/光线、道具、表情、声音/BGM 和切镜衔接缺一不可。"
        "结尾钩子必须在最后一场最后 2 行用动作、对白或道具特写演出。"
        f"{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "不能写旁白式总结、消费理由说明、观众要看、本集看点、抽象心理或说明式结尾钩子。",
)
QUALITY_SYSTEM = stage_system(
    "你是短剧质检器，负责像制作总监一样判断脚本是否能拍、能留人、能进入后链路。",
    (
        "按竖屏短剧成片标准检查：3 秒留人、冲突密度、信息差、人物一致性、结尾追更、"
        "台词长度、镜头可执行性、镜头衔接和是否外露分析字段。"
    ),
    (
        "按“结构完整性 -> 原文保真 -> 开篇冲突 -> 信息增量 -> 视听可执行 -> 台词效率 -> "
        "结尾追更 -> 连续性/题材一致性”的顺序审核。"
    ),
    (
        "只要不满足可拍摄脚本标准，就必须要求重写；rewrite_instruction 要给逐集、可执行的修复方向。"
        f"{THREE_THREE_THREE_RHYTHM_RULE}"
    ),
    "必须拦截外露分析词、抽象动作、镜头衔接不足、题材模板错配和说明式结尾钩子。",
)
STATE_SYSTEM = stage_system(
    "你是短剧状态回写器，负责把本轮正片演出的事实沉淀为下一轮可继承状态。",
    (
        "只把本轮已经在剧中演出的事实、人物认知、关系变化、伏笔、道具状态和下一轮 open_hooks "
        "写回结构化状态；不得改写已锁定 Story Bible，不得补写未演出的设定。"
    ),
    (
        "按“已演事实 -> 三层认知 -> 关系变化 -> 道具/证据状态 -> 伏笔账本 -> "
        "下一轮 open hooks/forbidden reveals”的顺序回写。"
    ),
    (
        "必须区分 audience_known（观众已知）、protagonist_known（主角已知）、villain_known（反派已知），"
        "防止下一轮重复揭示或错用信息差。"
    ),
    "不能把营销看点写成 open_hook，不能把已揭示信息再次当悬念，不能改写 Story Bible。",
)


def source_parser_user(source_text: str) -> str:
    return prompt_block(
        f"小说原文：\n{source_text}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        stage_instruction(
            "提取人物、事件、冲突、可视频化场面、低价值段落和候选 Hook。输出目标是拍摄/剪辑/AI 视频可直接消费的生产资产，不是剧情总结。",
            (
                "先判定题材和主角欲望，再拆事件的主体、动作、对象和后果；随后提取可见场面、"
                "强对白、道具、威胁和反转；最后标记低价值段落的删除、压缩或视听化方式。"
            ),
            (
                "人物要写明身份、关系、可拍标签和当场欲望；事件要拆成主体、动作、对象、"
                "地点/道具/对白和当场后果；冲突要能落到镜头动作或短台词。"
            ),
            (
                "candidate_hooks 必须是可见动作、强对白、道具露出、身份误会、威胁或反转，"
                "能被剪成前三秒画面/声音。必须在可用字段中体现原文资产 C0-C4："
                "C0/C1 写入事件、冲突、候选 hook、道具或强对白；C2/C3 写入低价值段落处理；"
                "C4 写入风险/禁止改动。低价值段落要给出删除、合并、转 OS 或转动作的处理策略。"
            ),
            (
                "不能写成“观众想看什么”“制造悬念”“爽点升级”这类概念句。"
                "题材模板保护：如果原文是男频穿越/大宋/武大郎/金莲/西门庆/经商护妻，"
                "只能围绕现代认知差、误会反转、护妻或经商打脸提取资产，"
                "不得套真假千金、豪门宴会、现代豪门继承模板。"
            ),
        ),
    )


def viral_asset_user(
    source_text: str,
    source_analysis: BaseModel,
    target_episode_count: int | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        f"小说原文：\n{source_text}",
        f"目标总集数：{target_text}",
        dump_model("source_analysis", source_analysis),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        stage_instruction(
            "生成 ViralAssetReport。必须按网文改爆款竖屏短剧 SOP 做前置评估。",
            (
                "先判断频道、题材标签和核心爽感；再提炼反差世界观/强设定、核心困境、主角目标、主冲突；"
                "接着筛出大高潮名场面、小高光节点、金句和情绪曲线；最后写风险替换和删减规则。"
            ),
            (
                "这是系统内部资产，只供后续集数解析、Story Bible、全剧结构、单集设计和脚本生成消费；"
                "不得增加用户确认门。至少保留 3 个大高潮名场面和 5 个小高光节点。"
            ),
            (
                "signature_scenes 和 small_highlights 每一条都必须写成“人物 + 地点 + 可见动作 + 当场后果”，"
                "例如“林晚在宴会厅撕开亲子鉴定，宾客当场倒向她”。signature_scenes 要优先承载 C1 必保名场面；"
                "risk_treatments 必须写清 C0 不可改事实、C4 禁止新增内容，以及无天然钩子时可用的事实兼容型钩子方向。"
                "改编风险必须给替换/合并方案。"
            ),
            (
                "不得写成用户可见卖点文案、平台简介、投放文案或封面标题；不能写成抽象情绪、爽感、主题或观念；"
                "明确禁止题材模板错配，例如男频穿越/大宋不能套真假千金宴会模板。"
                "整条 SOP 全链路服务于后续脚本生成，不要要求用户确认，不要输出用户可见说明。"
            ),
        ),
    )


def episode_context_user(
    source_text: str,
    previous_context: BaseModel | None,
    source_analysis: BaseModel,
    round_number: int = 1,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
    viral_asset_report: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        f"小说原文：\n{source_text}",
        f"当前轮次：第 {round_number} 轮",
        f"目标总集数：{target_text}",
        f"本轮目标集数：最多 {episodes_per_round} 集",
        dump_model("previous_context", previous_context),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "判断 target_episode_range、story_stage、must_carry_context、forbidden_reveals、source_to_episode_mapping、adaptation_actions，并给 confidence。",
            (
                "先读取 previous_context.current_episode，再计算本轮起止集；然后把原文事件映射到 EP，"
                "最后写本轮必须承接、禁止提前揭示和需要改编的动作。"
            ),
            (
                "必须由系统自动识别轮次和本轮范围，不得要求用户确认、不得让用户选择方向。"
                "如果 previous_context 存在，本轮必须从 previous_context.current_episode + 1 开始，"
                "target_episode_range 的起点必须等于这个下一集；不得重复已完成集数，"
                "也不得把已完成集数再次放入 source_to_episode_mapping。"
            ),
            (
                "如果目标总集数剩余不足本轮目标集数，则只覆盖剩余集数。"
                "target_episode_range 必须使用 EP 两位格式，例如 EP01-EP05；"
                "source_to_episode_mapping 必须写成可执行映射：每条包含原文段落/事件、目标 EP、"
                "保留的画面/对白/道具、删改理由、本集承担的信息增量，以及该映射涉及的 C0/C1/C2/C3/C4 分级。"
                "adaptation_actions 必须是可执行动作：提前、合并、删除、视听化、改断点、补信息差；"
                "每条都要标注属于允许改编、谨慎补强还是禁止改动。"
            ),
            (
                "禁止输出 1-5、第1-5集、第一轮 等非标准范围。不能泛泛写“承接上一轮”。"
                "每条 adaptation_actions 都要写明对象、动作、目标集数和预期效果，不能写“增强爽感、推进节奏”。"
                "题材模板保护：男频穿越/大宋/武大郎/金莲/西门庆类必须围绕现代认知差、"
                "误会反转、护妻/经商打脸分配集数，不能套真假千金、豪门宴会模板。"
            ),
        ),
    )


def bible_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    viral_asset_report: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    return prompt_block(
        f"小说原文：\n{source_text}",
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "生成内部 Story Bible。不要要求用户确认。",
            (
                "先锁定主线和不可变事实，再为每个主要角色建立人物合同，随后定义关系张力、"
                "短台词风格、戏剧功能、immutable_facts 和 forbidden_changes。"
            ),
            (
                "这是系统自动维护的内部状态，不向用户发起确认、选择或二次补充。"
                "characters 中每个主要人物必须按“姓名｜基础身份｜强记忆标签｜核心反差｜"
                "核心诉求｜终极执念｜戏剧功能”锁定，缺一项就补足。"
            ),
            (
                "speech_styles 中每个主要角色必须写短台词风格，并包含 2 个 15 字以内示例短句；"
                "台词要能指导拍摄，不写文学化长句。戏剧功能只能使用清晰职责，例如压、装、打、暴、发、拉、递证、误导、见证。"
                "immutable_facts 必须吸收 C0 不可改事实；forbidden_changes 必须吸收 C4 禁止新增和禁止改动项，"
                "尤其锁定主动方、核心动机、关键决定时机、关系状态和证据来源。"
            ),
            (
                "功能性配角只承担一个功能，不要写成多功能慢热人物。反派必须写直白动机和当场压迫手段，"
                "禁止复杂洗白、苦衷包装或长篇成长线。immutable_facts 和 forbidden_changes 只锁定不可乱改的已知事实、"
                "关系和禁区，不要把尚未演出的悬念提前公开。"
            ),
        ),
    )


def series_structure_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    viral_asset_report: BaseModel,
    previous_context: BaseModel | None,
    target_episode_count: int | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    return prompt_block(
        f"小说原文：\n{source_text}",
        f"目标总集数：{target_text}",
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "生成 SeriesStructurePlan。必须把线性原文重构为可连续生产的全剧集纲。",
            (
                "先确定总集数结构和本轮 target_episode_range，再写 opening_contract、三层冲突、"
                "全局情绪曲线、小/大高潮节拍，最后落到逐集 episode_outlines 和 forbidden_slowdowns。"
            ),
            (
                "这是 SOP 中连接 Story Bible 与后续脚本生成的内部结构层，必须自动完成；"
                "不得新增用户确认门、方向选择门或人工审核节点。target_episode_range 必须等于 episode_context.target_episode_range；"
                "target_episode_count 使用用户目标；如果未指定，也要说明本轮结构依据。"
            ),
            (
                "opening_contract 至少 3 条，覆盖前 3 集的“抛设定 -> 制造困境 -> 主角行动”。"
                "opening_contract 必须显式判断开场钩子双模式：原文有 C1 天然钩子时写保护/视听化方式；"
                "原文无天然钩子时写事实兼容型钩子的来源、前置方式和不改变 C0 的理由。"
                "global_emotion_curve、small_climax_cadence、big_climax_cadence 必须共同约束全剧节奏，"
                "按平均每 3 集一个小高潮、每 8 集一个大高潮规划，不能只写本轮局部剧情。"
                "每集必须有独立信息增量：新增证据、关系变化、身份认知、道具状态、敌我策略或不可逆后果。"
                "character_profiles 必须按身份、标签、反差、诉求、执念、功能、台词风格输出；"
                "conflict_stack 必须包含表层事件冲突、中层情感冲突、深层价值/宿命冲突。"
                "episode_outlines 至少覆盖本轮 target_episode_range 内全部集数，若目标总集数不超过 40，优先覆盖全剧所有集数。"
                "每集必须有核心事件、情绪节点、信息增量、结尾断点类型、具体断点、原文锚点。"
                "ending_hook_type 必须是可执行断点类型，如动作未完成、强台词截断、证据露出、身份将揭未揭、威胁落下、反转前一秒；"
                "source_anchor 必须指向原文具体段落/事件/台词/场面。"
            ),
            (
                "forbidden_slowdowns 明确禁止无冲突过渡、长篇内心、泛化场景、连续水集、换场不换信息、只抒情不推进；"
                "任何 episode_outline 都不能成为水集，不能只重复上一集情绪。"
                "episode_outlines 的 ending_hook 必须是画面/动作/台词级断点，必须能直接被下一步脚本写成最后 2 行；"
                "不能写“观众想看”“身份悬念推进”“等待揭晓”“持续升级”“引发期待”这类概念，不能写“原文相关”。"
                "这是系统内部规划，不向用户请求确认，不输出用户可见说明。"
            ),
        ),
    )


def episode_plan_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    return prompt_block(
        f"小说原文：\n{source_text}",
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "为 episode_context.target_episode_range 内每一集生成 EpisodeDramaPlan。这一步只做戏剧工程设计，不写正片脚本；保留旧约束：只做改编设计，不写完整台词剧本。",
            (
                "逐集按“误认知 -> 主角动作 -> 对手反制 -> 假打脸 -> 钥匙预埋 -> 情绪转向 -> 临门截断”设计。"
                "如果 series_structure_plan 不为空，先找到对应 SeriesEpisodeOutline，再承接 core_event、information_increment、ending_hook_type、source_anchor。"
            ),
            (
                "不要输出分场正文、连续对白、旁白成稿或成片脚本。每集必须按 EpisodeDramaPlan 字段逐项填写："
                "1. episode/title：对应本轮目标集数，标题写成可拍的冲突名；"
                "2. drama_engine：戏剧引擎，写主角基于什么误认知采取什么行动，以及这个行动如何逼出对手反制；"
                "3. protagonist_misbelief 和 truth_gap：误认知/真相差必须成对出现，说明主角以为 A、事实却是 B；"
                "4. physical_action_chain：3 个以上物理动作链，不能只写看/听/想，每一条都必须包含“主体 + 动作 + 对象 + 当场后果”；"
                "5. scene_dynamics：场景动态必须写清人物如何移动、抢夺、躲避、逼近、堵门、亮证、摔物或改换空间位置；"
                "6. emotional_turns：至少 2 次情绪转向，写清从哪种情绪转到哪种情绪，由哪一个动作/证据触发；"
                "7. audience_information_gap：观众知道但角色不知道的信息差，必须能驱动等待、误会或反打；"
                "8. three_pull_beats：三波拉扯必须是第一波压迫、第二波升级、第三波临门截断，每波都要有具体动作和即时后果；"
                "9. false_payoff：至少一次假打脸/期待落空，写清观众以为要赢，但哪一件事让胜利被重置；"
                "10. planted_key：一个早埋晚用的道具、证据、身份钥匙或口头承诺，写明本集怎么埋、后面怎么用；"
                "11. strongest_line：全集最狠的一句短台词，必须有血压感，短于 18 个汉字，不要写成解释句；"
                "12. cliffhanger_design：结尾截断必须停在动作、证据、身份或关系爆点前一秒，逼观众看下一集；"
                "13. source_assets_to_keep：按 C0/C1/C2/C3 写原文必须保留、视听化或压缩的名场面、金句、人物关系或道具；"
                "14. forbidden_shortcuts：必须写 C4 禁止新增/禁止改动，包括不得改变主动方、动机、关键决定时机、证据来源、关系状态；"
                "15. 必须写清本集高价值事件是首次兑现、后果承接还是反扑升级；已兑现的吻戏/曝光/解约/发布会类名场面不得重复演。"
            ),
            (
                "所有 EpisodeDramaPlan 字段都必须是可执行设计；必须能被 Script 阶段直接翻译成镜头、动作、台词、道具和剪辑点。"
                "如果原文无强钩子，本阶段必须在 drama_engine 或 cliffhanger_design 中补事实兼容型钩子；"
                "如果原文已有强钩子，source_assets_to_keep 必须写明保护方式。"
            ),
            (
                "禁止抽象词如“增强爽感”、“制造悬念”、“推进剧情”、“强化冲突”、“情绪拉满”，必须改成谁做什么、对谁做、造成什么当场后果。"
                "不得写成与全剧节奏无关的孤立桥段。保持题材 guard：如果是男频穿越 / 大宋 / 武大郎 / 金莲 / 西门庆类，"
                "drama_engine 必须走现代认知差、轻喜误会反转、护妻/经商打脸，不得套真假千金、豪门认亲、宴会验亲或亲哥哥救场模板。"
            ),
        ),
    )


def script_user(
    source_text: str,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    rewrite_instruction: str,
    round_number: int = 1,
    target_episode_count: int | None = None,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
    episode_source_packets: BaseModel | None = None,
    production_spec: BaseModel | None = None,
    source_annotation: BaseModel | None = None,
    episode_cut_table: BaseModel | None = None,
) -> str:
    target_text = str(target_episode_count) if target_episode_count else "未指定"
    if script_prompt_mode() == "creative":
        return prompt_block(
            source_material_section(
                source_text,
                episode_source_packets=episode_source_packets,
            ),
            f"当前轮次：第 {round_number} 轮",
            f"目标总集数：{target_text}",
            section("本轮集数硬清单", episode_range_contract(episode_context)),
            lean_flow_authority_section(),
            dump_model("production_spec", production_spec),
            dump_model("source_annotation", source_annotation),
            dump_model("episode_cut_table", episode_cut_table),
            script_reference_context_section(
                source_analysis=source_analysis,
                episode_context=episode_context,
                previous_context=previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
            ),
            dump_model("story_bible", story_bible),
            dump_model("episode_plan", episode_plan),
            f"rewrite_instruction: {rewrite_instruction}",
            section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
            section("内部方法论", render_methodology_context(methodology_context)),
            section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
            stage_instruction(
                "输出 episode_context.target_episode_range 覆盖的全部 EpisodeScript。先写创作稿质量：一场戏要成立，再考虑后续执行稿补镜头。",
                (
                    "逐集先确认原文片段、C0 不可改事实、C1 必保名场面、Story Bible 人物动机和 episode_plan 的本集目标；"
                    "source packet 是当前集原文边界，EpisodeDramaPlan 只能在当前集 source packet 边界内执行；"
                    "若 episode_plan 的动作、道具、证据、台词或断点无法在当前集 packet.source_excerpt/C0/C1/C2 中追溯，必须丢弃或改回原文当前集。"
                    "再决定哪些内心戏转成动作/OS/短对白，哪些过渡删除，哪些钩子需要事实兼容地补强。"
                    "如果 series_structure_plan 不为空，必须对齐本集核心事件、信息增量、断点类型和原文锚点。"
                ),
                (
                    "必须输出 ScriptBatch schema。每集填写 episode/title/hook_3s/main_emotion/watch_reason/scenes/cliffhanger/state_update；"
                    "hook_3s/main_emotion/watch_reason 是内部字段，不能作为用户可见说明行。"
                    "Hook/main_emotion/watch_reason/消费理由只允许出现在 EpisodeScript 结构化字段中。"
                    "Hook/main_emotion/watch_reason/消费理由不得出现在任何 scene.lines 的 action/dialogue/os/vo/transition 文本里。"
                    "scenes 是正片创作稿：scene.heading 必须严格写成“集数-场次 日/夜-内/外-具体地点”；"
                    "禁止只写 豪华宴会厅、走廊、房间、街上 这类泛化场景头。"
                    "action 写可看见的动作、道具、表情、空间压迫、声音或转场，但不要为了凑指标堆景别运镜；"
                    "dialogue/os/vo 必须短、像真人、带潜台词，不能用长句解释背景。"
                    "执行稿参考密度：每集 scene.lines 合计至少 28 行可在 shooting repair 阶段补齐，首稿优先保证戏成立。"
                    f"{VISIBLE_SCRIPT_DENSITY_RULE}"
                    "后置执行稿参考：每条 action 必须写清景别、主体位置、镜头运动、构图/光线、关键道具、人物表情、声音/BGM 或镜头衔接；"
                    "每条 action 必须显式包含一个景别词和一个运镜词，但首稿优先保证动作因果和人物状态。"
                    f"{ACTION_LINE_TEMPLATE_RULE}{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
                    "对白一句不超过 22 个汉字，只表达一个动作或情绪。"
                    "不合格 action 示例：△武植在床上睁开眼。/ △宴会厅内，灯光璀璨，众人震惊。"
                ),
                (
                    "第一场前三行必须让观众立刻看到冲突/危险/羞辱/误会/反差/强选择之一。"
                    "如果原文已有天然钩子，第一场必须保留其核心张力并合规视听化；如果原文没有钩子，只补不违背事实和动机的事实兼容型钩子。"
                    "每集至少有一次情绪转向或信息增量，结尾必须停在观众最想看下一秒的位置。"
                    "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作。"
                ),
                (
                    "禁止改变主角核心动机、主动方、关键决定时机、证据来源和关系状态。"
                    "禁止为了爽点新增无原文依据的道具、狠话、身份、资本解法或法务结果。"
                    "禁止把克制人物写成歇斯底里，把深思熟虑写成临场冲动，把对手主动欺骗改成主角主动索要。"
                    "最后一场最后 2 行必须把 cliffhanger 以对白、动作或道具特写演出来。"
                    "禁止旁白式总结、价值观说明、消费理由说明、观众要看、本集看点、本集钩子等外露分析。"
                    "禁止外露“3秒 Hook/主情绪/消费理由/观众要看/本集看点”。"
                ),
            ),
        )
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packets=episode_source_packets,
        ),
        f"当前轮次：第 {round_number} 轮",
        f"目标总集数：{target_text}",
        section("本轮集数硬清单", episode_range_contract(episode_context)),
        lean_flow_authority_section(),
        dump_model("production_spec", production_spec),
        dump_model("source_annotation", source_annotation),
        dump_model("episode_cut_table", episode_cut_table),
        script_reference_context_section(
            source_analysis=source_analysis,
            episode_context=episode_context,
            previous_context=previous_context,
            viral_asset_report=viral_asset_report,
            series_structure_plan=series_structure_plan,
        ),
        dump_model("story_bible", story_bible),
        dump_model("episode_plan", episode_plan),
        f"rewrite_instruction: {rewrite_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
        stage_instruction(
            "必须输出 episode_context.target_episode_range 覆盖的全部集数，最多 5 集。",
            (
                "逐集先读 EpisodeDramaPlan 和 SeriesEpisodeOutline，确认本集核心事件、信息增量、断点类型和原文锚点；"
                "source packet 是当前集原文边界，EpisodeDramaPlan 只能在当前集 source packet 边界内执行；"
                "若计划动作、道具、证据或断点不属于当前集 packet.source_excerpt/C0/C1/C2，必须丢弃或改回原文当前集；"
                "再按原文资产分级决定“保护 C0/C1、视听化 C2、压缩 C3、删除 C4”，"
                "最后写前三秒可见冲突、三波拉扯、假打脸/钥匙兑现、反派最后一装和结尾截断。"
            ),
            (
                "如果 episode_plan 不为空，只能在当前集 source packet 边界内逐集执行对应 EpisodeDramaPlan：drama_engine 决定本集动作逻辑，"
                "three_pull_beats 决定场景推进，false_payoff/planted_key/cliffhanger_design 必须在剧本中兑现或预埋。"
                "如果 series_structure_plan 不为空，必须逐集执行对应 SeriesEpisodeOutline 的核心事件、信息增量、断点类型和原文锚点；"
                "不能为了写爽点而断开全剧结构。如果 viral_asset_report 不为空，至少保留本轮相关名场面/金句/情绪资产，"
                "并按 risk_treatments 避开敏感设定和慢热支线。"
                "如果原文已有 C1 天然钩子，第一场必须保留其核心张力并合规视听化；"
                "如果原文没有天然钩子，第一场必须补事实兼容型钩子，并在动作/对白里能追溯到 source_anchor 或 C0/C1/C2。"
                "任何新增动作、道具、证据、狠话都必须只补镜头或衔接，不能改变主角欲望、主动方、因果顺序或关键决定时机。"
                "必须执行事件账本：同一高价值名场面不能跨集重复兑现；身份/机构/舆论/权威裁决类结果必须先写清证据来源和流程，再写结果。"
                "episode 字段必须是数字集数；scene.heading 必须严格写成 “集数-场次 日/夜-内/外-具体地点”，例如 1-1 夜-内-武家卧室，"
                "禁止只写 豪华宴会厅、走廊、房间、街上 这类泛化场景头。"
            ),
            (
                "每集仍需填充 3 秒 Hook、主情绪、watch_reason、cliffhanger、state_update，"
                "但这些是系统内部字段，不能在剧本文本里以“3秒 Hook/主情绪/消费理由/观众要看”单独展示；"
                "必须把 hook 融入第一场的第一组动作、VO/OS 或对白。"
                "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作，"
                "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
                "Hook/main_emotion/watch_reason/消费理由只允许出现在 EpisodeScript 结构化字段中，"
                "不得出现在任何 scene.lines 的 action/dialogue/os/vo/transition 文本里。"
                "watch_reason 只能写给系统分析，禁止把“观众想看/消费理由/看点”写入任何 scene line。"
                f"{VISIBLE_SCRIPT_DENSITY_RULE}"
                "每集优先 3 个可拍摄场景，最低 2 场。参照标杆短剧密度：每集 800-1700 字，"
                "2-5 场，至少 10 条 △/镜头动作行，至少 18 条对白/OS/VO。"
                "前 8 个 beat 必须爆出危机、羞辱、误会、威胁或强反击，至少 2 句高压短台词，"
                "结尾钩子必须是强疑问、威胁、反转或动作未完成。OS 后必须紧跟物理动作或明确决定，不能只做心理解释。"
                "对白尽量短，一句不超过 22 个汉字，只表达一个动作或情绪；不能用解释型长句、书面复句、价值观总结，长 OS 必须拆成多行。"
                "每条 action 必须写清景别、主体位置、镜头运动、构图/光线、关键道具、人物表情、声音或 BGM 触发点，"
                "并用切镜、反打、视线匹配、声音先入、道具特写或动作接动作说明镜头衔接，方便后链路 AI 执行。"
                "每条 action 必须显式包含一个景别词（全景/中景/中近景/近景/特写/俯拍/仰拍/长焦）"
                "和一个运镜词（推近/拉远/横移/跟拍/摇向/甩向/切到/扫过/快剪/拉焦/环绕/上移/定格/慢镜头）。"
                f"{ACTION_LINE_TEMPLATE_RULE}"
                f"{SHOT_LINKAGE_RULE}"
                f"{INFO_INCREMENT_RULE}"
                "如果一条 action 写不下全部生产信息，就拆成连续 action；不得省略道具、表情、声音/BGM 或镜头衔接。"
                "合格 action 示例：△中近景推近武植侧脸，油灯在画面左上晃动，药碗占前景，他一把压住碗沿，切到金莲发白的指节。"
                "不合格 action 示例：△武植在床上睁开眼。/ △宴会厅内，灯光璀璨，众人震惊。"
            ),
            (
                "不能先写背景介绍。第一场前三行建议为：△强画面动作 -> 反派/危机短台词 -> 主角动作或 OS+动作。"
                "不能把主角写出原文没有的功利诉求、求取目标或歇斯底里狠话；台词风格必须服从 Story Bible 和 C0 人物动机。"
                "不得把预谋决定写成临场冲动，不得把对手主动承诺/欺骗改成主角主动索要，不得用编造道具替代原文证据。"
                "最后一场最后 2 行必须把 cliffhanger 以对白、动作或道具特写演出来，不要只把 cliffhanger 填在字段里，"
                "也不要新增“结尾钩子：/cliffhanger：”说明行。"
                f"{FINAL_TWO_LINE_RULE}"
                "禁止旁白式总结、价值观说明、消费理由说明、观众要看、本集看点、本集钩子等外露分析。"
                "如果原文是男频穿越/大宋/武大郎/金莲/西门庆类，必须使用现代认知 OS + 立刻动作 + 轻喜打脸节奏，"
                "不能套用真假千金/豪门模板。"
            ),
        ),
    )


def script_episode_user(
    source_text: str | None,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    existing_episode: BaseModel | None,
    episode_number: int,
    rewrite_instruction: str,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
    episode_source_packet: BaseModel | None = None,
    previous_episode_handoff: BaseModel | None = None,
    current_episode_repair_packet: BaseModel | None = None,
    production_spec: BaseModel | None = None,
    source_annotation: BaseModel | None = None,
    episode_cut_table: BaseModel | None = None,
) -> str:
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packet=episode_source_packet,
        ),
        f"只生成第 {episode_number} 集。不要输出其他集数。",
        lean_flow_authority_section(),
        dump_model("production_spec", production_spec),
        dump_model("source_annotation", source_annotation),
        dump_model("episode_cut_table", episode_cut_table),
        dump_model("previous_episode_handoff", previous_episode_handoff),
        script_reference_context_section(
            source_analysis=source_analysis,
            episode_context=episode_context,
            previous_context=previous_context,
            viral_asset_report=viral_asset_report,
            series_structure_plan=series_structure_plan,
        ),
        dump_model("story_bible", story_bible),
        dump_model("existing_episode_to_rewrite", existing_episode),
        dump_model("current_episode_repair_packet", current_episode_repair_packet),
        dump_model("episode_plan", episode_plan),
        f"rewrite_instruction: {rewrite_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        section("生成期源文保真硬指标", SOURCE_FIDELITY_GENERATION_RULE),
        stage_instruction(
            (
                f"输出必须是一个 EpisodeScript；episode 字段必须等于 {episode_number}。"
                "这是按问题类型执行的定向修复，不是默认整集重写。"
                "必须先读取 rewrite_instruction 里的“修复级别”，再决定允许改动范围。"
                "如果 current_episode_repair_packet 不为空，必须优先遵守 current_episode_repair_packet.allowed_change_scope。"
            ),
            (
                "先定位 existing_episode 的失败点和 rewrite_instruction 的硬伤；"
                "如果修复级别是格式局部修复，只修不合格 action/标题/外露分析行；"
                "如果是结尾钩子局部修复，只修最后一场最后 8-12 行和必要短对白；"
                "如果是单集创作修复，才回到本集 EpisodeDramaPlan / SeriesEpisodeOutline / source packet "
                "修 OOC、原文偏离、情绪递进或冲突因果；"
                "只有修复级别明确写结构崩坏整集重写时，才允许重写整集。"
            ),
            (
                "如果 episode_plan 不为空，必须优先执行本集 EpisodeDramaPlan 的 drama_engine、"
                "three_pull_beats、false_payoff、planted_key、strongest_line 和 cliffhanger_design。"
                "source packet 是当前集原文边界，EpisodeDramaPlan 只能在当前集 source packet 边界内执行；"
                "若计划项和 packet.source_excerpt/C0/C1/C2 冲突，必须服从 source packet；"
                "existing_episode 只有在可被当前集 source packet/source_annotation 证明时才可保留。"
                "如果 series_structure_plan 不为空，必须对齐本集 SeriesEpisodeOutline 的 "
                "core_event、information_increment、ending_hook_type 和 source_anchor。"
                "如果 episode_source_packet 不为空，必须优先使用 packet.source_excerpt 和 C0/C1/C2/C4，"
                "不得从全文或其他集 packet 自由补剧情。"
                "如果 previous_episode_handoff 不为空，第一场前 3-6 行必须照应上一集最后钩子，"
                "不能重开一个无关场面。"
                f"{repair_packet_baseline_instruction(current_episode_repair_packet)}"
                "定向修复必须是“回到原文资产 + 修指定缺口”，不能把修复写成新剧情或整集洗稿。"
                "若 existing_episode 删除了 C1 天然钩子，要恢复并合规视听化；若原文没有天然钩子，只能补事实兼容型钩子。"
                "必须删除 C4 编造动作/道具/台词，尤其是改变主动方、动机、关键决定时机、证据来源或关系状态的内容。"
                f"scene.heading 必须严格写成 “{episode_number}-场次 日/夜-内/外-具体地点”，例如 {episode_number}-1 夜-内-武家卧室。"
                "只有结构崩坏整集重写时才强制执行完整密度目标。"
                f"{VISIBLE_SCRIPT_DENSITY_RULE}"
                "局部修复时保留 existing_episode 已合格密度，不要为了补指标增加水对白、空镜或新支线。"
            ),
            (
                "第一场前 8 个 beat 必须有危机、误会、羞辱、威胁或强反击。"
                "每条 action 必须以 △ 开头，并写清景别、主体位置、镜头运动、构图/光线、关键道具、"
                "人物表情、音效/BGM 触发和切镜衔接。每条 action 必须显式包含一个景别词"
                "（全景/中景/中近景/近景/特写/俯拍/仰拍/长焦）和一个运镜词"
                "（推近/拉远/横移/跟拍/摇向/甩向/切到/扫过/快剪/拉焦/环绕/上移/定格/慢镜头）。"
                f"{ACTION_LINE_TEMPLATE_RULE}"
                f"{SHOT_LINKAGE_RULE}"
                f"{INFO_INCREMENT_RULE}"
                "OS 后必须紧跟物理动作或明确决定；对白一句不超过 22 个汉字，只表达一个动作或情绪。"
                "hook_3s/main_emotion/watch_reason 只是内部字段，必须把 hook 融入第一场的动作、OS/VO 或对白。"
                "cliffhanger 字段必须直接填写最后一场最后 4 行里已经演出来的钩子台词或动作，"
                "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
                "Hook/main_emotion/watch_reason/消费理由不得出现在任何 scene line 文本里。"
                "结尾钩子必须是强疑问、威胁、反转或动作未完成，并在最后一场最后 2 行演出来；"
                "最后两行不能是“结尾钩子/看点/消费理由”的说明文字。"
                f"{FINAL_TWO_LINE_RULE}"
            ),
            (
                "禁止写“△ 武植在床上睁开眼”这种无景别、无运镜的动作行。"
                "禁止为了修复烈度而改变 C0，禁止把预谋改成冲动、把被动承受改成主动索取、把克制人物改成歇斯底里。"
                "不能出现“3秒 Hook/主情绪/消费理由/观众要看/本集看点”等外露分析。"
                "不能为了修复字数而加背景介绍、价值观总结、泛场景、空镜拖时或解释型长对白。"
                "不能用黑屏、转场、画面定格、普通 OS 作为最后两行钩子。"
                "如果原文是男频穿越/大宋/武大郎/金莲/西门庆类，修复必须回到现代认知差、轻喜误会反转、"
                "护妻/经商打脸，不能套真假千金、豪门宴会、总裁认亲模板。"
            ),
        ),
    )


def hook_dialogue_polish_user(
    source_text: str | None,
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    previous_context: BaseModel | None,
    existing_episode: BaseModel,
    episode_number: int,
    polish_instruction: str,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
    episode_source_packet: BaseModel | None = None,
    previous_episode_handoff: BaseModel | None = None,
    current_episode_repair_packet: BaseModel | None = None,
    production_spec: BaseModel | None = None,
    source_annotation: BaseModel | None = None,
    episode_cut_table: BaseModel | None = None,
) -> str:
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packet=episode_source_packet,
        ),
        f"只二次编译第 {episode_number} 集的结尾钩子和对白密度。不要输出其他集数。",
        lean_flow_authority_section(),
        dump_model("production_spec", production_spec),
        dump_model("source_annotation", source_annotation),
        dump_model("episode_cut_table", episode_cut_table),
        dump_model("previous_epis

... [TRUNCATED FOR REVIEW PACK] ...

```


## File: `src/novel_drama_engine/source_packets.py`
```
from __future__ import annotations

import os
import re
from collections.abc import Iterable

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeDramaPlan,
    EpisodeHandoff,
    EpisodeScript,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SeriesEpisodeOutline,
    SeriesStructurePlan,
    EpisodePlan,
    StoryBible,
)


DEFAULT_EXCERPT_CHARS = 12000
FORBIDDEN_RULE_NOISE = (
    "不得",
    "不能",
    "禁止",
    "不要",
    "新增",
    "加入",
    "添加",
    "改成",
    "提前",
    "泄露",
    "公开",
)


def _max_excerpt_chars() -> int:
    raw = os.environ.get("NOVEL_DRAMA_SOURCE_PACKET_CHARS", str(DEFAULT_EXCERPT_CHARS))
    try:
        return max(2000, int(raw))
    except ValueError:
        return DEFAULT_EXCERPT_CHARS


def _episode_numbers_from_range(target_episode_range: str) -> list[int]:
    match = re.fullmatch(r"EP(\d+)(?:-EP(\d+))?", target_episode_range.strip())
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    if end < start:
        return []
    return list(range(start, end + 1))


def _target_episode_number(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"(?:EP|E|第)?\s*0*(\d{1,3})\s*(?:集)?", value, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _split_assets(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        item.strip()
        for item in re.split(r"[、,，;；\n]", value)
        if item.strip()
    ]


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join(str(item).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_for_match(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


GENERIC_CJK_TERMS = {
    "当前",
    "原文",
    "动作",
    "场面",
    "调度",
    "保留",
    "使用",
    "只用",
    "本集",
    "可见",
    "事件",
    "不要",
    "不得",
    "不能",
    "禁止",
    "提前",
    "新增",
    "改成",
    "成为",
    "通过",
    "结果",
    "观众",
    "以为",
}


def _cjk_terms(value: str) -> list[str]:
    terms: set[str] = set()
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", value):
        if len(chunk) >= 4 and chunk not in GENERIC_CJK_TERMS:
            terms.add(chunk)
        max_size = min(4, len(chunk))
        for size in range(2, max_size + 1):
            for index in range(0, len(chunk) - size + 1):
                term = chunk[index : index + size]
                if term in GENERIC_CJK_TERMS:
                    continue
                terms.add(term)
    return sorted(terms, key=lambda item: (-len(item), item))


def _supported_by_excerpt(asset: str, source_excerpt: str) -> bool:
    normalized_asset = _normalize_for_match(asset)
    if len(normalized_asset) < 2:
        return False
    normalized_excerpt = _normalize_for_match(source_excerpt)
    if normalized_asset in normalized_excerpt:
        return True
    cjk_terms = _cjk_terms(asset)
    if not cjk_terms:
        return False
    hits = [term for term in cjk_terms if term in source_excerpt]
    return any(len(term) >= 4 for term in hits) or (
        len(hits) / max(len(cjk_terms), 1)
    ) >= 0.2


def _packet_support_terms(packet: EpisodeSourcePacket) -> list[str]:
    terms = [
        packet.source_anchor,
        *packet.c0_facts,
        *packet.c1_must_keep_assets,
        *packet.golden_lines,
    ]
    normalized: list[str] = []
    for term in terms:
        item = _normalize_for_match(term)
        if len(item) >= 2:
            normalized.append(item)
    return _dedupe(normalized)


def _supported_by_packet(asset: str, packet: EpisodeSourcePacket) -> bool:
    normalized_asset = _normalize_for_match(asset)
    if len(normalized_asset) < 2:
        return False
    if _supported_by_excerpt(asset, packet.source_excerpt):
        return True
    return any(
        term in normalized_asset or normalized_asset in term
        for term in _packet_support_terms(packet)
    )


def _filter_plan_assets(
    assets: list[str],
    packet: EpisodeSourcePacket | None,
) -> list[str]:
    if packet is None:
        return assets
    return [asset for asset in assets if _supported_by_packet(asset, packet)]


def _filter_excerpt_assets(
    assets: list[str],
    source_excerpt: str,
) -> list[str]:
    return [asset for asset in assets if _supported_by_excerpt(asset, source_excerpt)]


def _source_snippets(packet: EpisodeSourcePacket) -> list[str]:
    raw_candidates = [
        *packet.c1_must_keep_assets,
        *packet.c0_facts,
        *re.split(r"[。！？!?；;\n]+", packet.source_excerpt),
        packet.source_anchor,
    ]
    candidates: list[str] = []
    for candidate in raw_candidates:
        stripped = candidate.strip(" \t\r\n。！？!?；;")
        if not stripped:
            continue
        if EPISODE_HEADING_RE.match(stripped):
            continue
        if re.fullmatch(r"#*\s*(?:EP|E|Episode|第)\s*0*\d{1,3}\s*(?:集|章)?", stripped, re.IGNORECASE):
            continue
        candidates.append(stripped)
    return [
        item
        for item in _dedupe(candidates)
        if item
    ]


def _fill_with_source_grounded_items(
    items: list[str],
    *,
    packet: EpisodeSourcePacket | None,
    min_length: int,
    label: str,
) -> list[str]:
    if len(items) >= min_length or packet is None:
        return items
    filled = list(items)
    for snippet in _source_snippets(packet):
        candidate = snippet
        if candidate not in filled:
            filled.append(candidate)
        if len(filled) >= min_length:
            break
    while len(filled) < min_length:
        fallback = f"{label}：只使用当前集原文可见事件，不借用后续集资产。"
        candidate = fallback if fallback not in filled else f"{fallback}#{len(filled) + 1}"
        filled.append(candidate)
    return filled


def _first_source_snippet(packet: EpisodeSourcePacket) -> str:
    for snippet in _source_snippets(packet):
        if snippet:
            return snippet
    return f"EP{packet.episode:02d} 当前集原文。"


def _source_grounded_scalar(
    value: str,
    *,
    packet: EpisodeSourcePacket | None,
    label: str,
) -> str:
    if packet is None or _supported_by_packet(value, packet):
        return value
    return f"{label}：{_first_source_snippet(packet)}。"


EPISODE_HEADING_RE = re.compile(
    r"(?im)^(?:\s{0,3}(?:#{1,6}\s*)?)"
    r"(?:EP|E|Episode|第)\s*0*(\d{1,3})\s*(?:集|章)?(?:\b|[：:.\-、\s])"
)


def _heading_sections(source_text: str) -> dict[int, tuple[int, int]]:
    matches = list(EPISODE_HEADING_RE.finditer(source_text))
    sections: dict[int, tuple[int, int]] = {}
    for index, match in enumerate(matches):
        episode = int(match.group(1))
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source_text)
        sections.setdefault(episode, (start, end))
    return sections


def _compact(text: str, max_chars: int) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    head = max_chars * 2 // 3
    tail = max_chars - head
    return (
        stripped[:head].rstrip()
        + "\n\n...[中间原文已压缩，保留首尾承接]...\n\n"
        + stripped[-tail:].lstrip()
    )


def _window(source_text: str, start: int, end: int, max_chars: int) -> str:
    if end <= start:
        end = start + 1
    span = end - start
    if span >= max_chars:
        return _compact(source_text[start:end], max_chars)
    padding = max(0, (max_chars - span) // 2)
    left = max(0, start - padding)
    right = min(len(source_text), end + padding)
    return _compact(source_text[left:right], max_chars)


def _find_asset_window(
    source_text: str,
    assets: list[str],
    max_chars: int,
) -> str | None:
    positions: list[tuple[int, int]] = []
    for asset in assets:
        candidate = asset.strip()
        if len(candidate) < 4:
            continue
        found = source_text.find(candidate)
        if found >= 0:
            positions.append((found, found + len(candidate)))
    if not positions:
        return None
    return _window(source_text, min(pos[0] for pos in positions), max(pos[1] for pos in positions), max_chars)


def _proportional_excerpt(
    source_text: str,
    *,
    episode: int,
    target_episode_count: int | None,
    fallback_episode_count: int,
    max_chars: int,
) -> str:
    total_episodes = max(target_episode_count or fallback_episode_count, episode, 1)
    length = len(source_text)
    start = int(length * (episode - 1) / total_episodes)
    end = int(length * episode / total_episodes)
    overlap = min(1200, max_chars // 5)
    return _compact(source_text[max(0, start - overlap) : min(length, end + overlap)], max_chars)


def _mapping_for_episode(
    mappings: list[EpisodeSourceMapping],
    episode: int,
) -> EpisodeSourceMapping | None:
    explicit = [
        mapping
        for mapping in mappings
        if _target_episode_number(mapping.target_episode) == episode
    ]
    if explicit:
        return explicit[0]
    for mapping in mappings:
        if re.search(rf"\bEP\s*0*{episode}\b|第\s*{episode}\s*集", mapping.source, re.IGNORECASE):
            return mapping
    return None


def _normalized_contract_text(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.strip())
    for token in FORBIDDEN_RULE_NOISE:
        normalized = normalized.replace(token, "")
    return re.sub(r"[，。、“”‘’：:；;,.!?！？\-—_（）()《》<>]", "", normalized)


def _source_packet_required_assets(
    episode_source_packets: EpisodeSourcePackets,
) -> list[str]:
    assets: list[str] = []
    for packet in episode_source_packets.packets:
        assets.extend(
            [
                *packet.c1_must_keep_assets,
                *packet.c2_visual_assets,
                *packet.golden_lines,
            ]
        )
    return list(dict.fromkeys(asset.strip() for asset in assets if asset.strip()))


def _rule_overlaps_required_asset(rule: str, required_assets: list[str]) -> bool:
    normalized_rule = _normalized_contract_text(rule)
    if len(normalized_rule) < 2:
        return False
    for asset in required_assets:
        normalized_asset = _normalized_contract_text(asset)
        if len(normalized_asset) < 2:
            continue
        if normalized_asset in normalized_rule or normalized_rule in normalized_asset:
            return True
    return False


def story_bible_source_packet_conflicts(
    story_bible: StoryBible,
    episode_source_packets: EpisodeSourcePackets,
) -> list[str]:
    required_assets = _source_packet_required_assets(episode_source_packets)
    return [
        rule
        for rule in story_bible.forbidden_changes
        if _rule_overlaps_required_asset(rule, required_assets)
    ]


def normalize_story_bible_against_source_packets(
    story_bible: StoryBible,
    episode_source_packets: EpisodeSourcePackets,
) -> StoryBible:
    conflicts = set(
        story_bible_source_packet_conflicts(story_bible, episode_source_packets)
    )
    if not conflicts:
        return story_bible
    return story_bible.model_copy(
        update={
            "forbidden_changes": [
                rule for rule in story_bible.forbidden_changes if rule not in conflicts
            ]
        }
    )


def _outline_for_episode(
    series_structure_plan: SeriesStructurePlan | None,
    episode: int,
) -> SeriesEpisodeOutline | None:
    if series_structure_plan is None:
        return None
    return next(
        (outline for outline in series_structure_plan.episode_outlines if outline.episode == episode),
        None,
    )


def _plan_for_episode(
    episode_plan: EpisodePlan | None,
    episode: int,
) -> EpisodeDramaPlan | None:
    if episode_plan is None:
        return None
    return next((plan for plan in episode_plan.episodes if plan.episode == episode), None)


def build_episode_source_packets(
    *,
    source_text: str,
    episode_context: EpisodeContext,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
    target_episode_count: int | None = None,
) -> EpisodeSourcePackets:
    episode_numbers = _episode_numbers_from_range(episode_context.target_episode_range)
    if not episode_numbers:
        episode_numbers = list(range(1, 2))
    max_chars = _max_excerpt_chars()
    heading_sections = _heading_sections(source_text)
    fallback_count = len(episode_numbers)
    packets: list[EpisodeSourcePacket] = []
    seen_fallback_required_assets: set[str] = set()

    for episode in episode_numbers:
        mapping = _mapping_for_episode(episode_context.source_to_episode_mapping, episode)
        outline = _outline_for_episode(series_structure_plan, episode)
        retained_assets = _split_assets(mapping.retained_assets if mapping else None)
        c1_assets = _dedupe(retained_assets)
        requested_source_anchor = (
            (outline.source_anchor if outline else "")
            or (mapping.source if mapping else "")
            or f"EP{episode:02d}"
        )

        if episode in heading_sections:
            start, end = heading_sections[episode]
            source_excerpt = _compact(source_text[start:end], max_chars)
        else:
            source_excerpt = _find_asset_window(
                source_text,
                [requested_source_anchor, *(c1_assets or [])],
                max_chars,
            ) or _proportional_excerpt(
                source_text,
                episode=episode,
                target_episode_count=target_episode_count
                or series_structure_plan.target_episode_count
                if series_structure_plan
                else target_episode_count,
                fallback_episode_count=fallback_count,
                max_chars=max_chars,
            )

        source_anchor = (
            requested_source_anchor
            if _supported_by_excerpt(requested_source_anchor, source_excerpt)
            else f"EP{episode:02d} 当前集原文"
        )
        filtered_c1_assets = _filter_excerpt_assets(c1_assets, source_excerpt)
        source_window_is_reliable = episode in heading_sections or len(
            _normalize_for_match(source_excerpt)
        ) >= 80
        grounded_c1_assets = (
            _fill_with_source_grounded_items(
                filtered_c1_assets,
                packet=EpisodeSourcePacket(
                    episode=episode,
                    source_anchor=source_anchor,
                    source_excerpt=source_excerpt,
                ),
                min_length=1,
                label="当前集原文必留",
            )
            if filtered_c1_assets or source_window_is_reliable
            else []
        )
        if not filtered_c1_assets:
            unique_fallback_c1_assets: list[str] = []
            for asset in grounded_c1_assets:
                normalized_asset = _normalize_for_match(asset)
                if normalized_asset in seen_fallback_required_assets:
                    continue
                seen_fallback_required_assets.add(normalized_asset)
                unique_fallback_c1_assets.append(asset)
            grounded_c1_assets = unique_fallback_c1_assets
        grounded_c0_facts = _fill_with_source_grounded_items(
            _filter_excerpt_assets(
                _dedupe(
                    [
                        mapping.information_increment if mapping else "",
                        outline.information_increment if outline else "",
                    ]
                ),
                source_excerpt,
            ),
            packet=EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
            ),
            min_length=1,
            label="当前集原文事实",
        )
        grounded_c2_assets = _fill_with_source_grounded_items(
            _filter_excerpt_assets(
                _dedupe([mapping.adaptation_action if mapping else ""]),
                source_excerpt,
            ),
            packet=EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
            ),
            min_length=1,
            label="当前集原文可视听",
        )
        grounded_golden_lines = _filter_excerpt_assets(
            _dedupe([outline.ending_hook if outline else ""]),
            source_excerpt,
        )

        packets.append(
            EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
                c0_facts=grounded_c0_facts,
                c1_must_keep_assets=grounded_c1_assets,
                source_evidence_assets=filtered_c1_assets,
                c2_visual_assets=grounded_c2_assets,
                c3_compress_assets=_dedupe(
                    [
                        *(episode_context.adaptation_actions or []),
                        *(series_structure_plan.forbidden_slowdowns if series_structure_plan else []),
                    ]
                ),
                c4_forbidden_additions=_dedupe(
                    [
                        *(episode_context.forbidden_reveals or []),
                    ]
                ),
                golden_lines=grounded_golden_lines,
                handoff_requirement=grounded_golden_lines[0]
                if grounded_golden_lines
                else None,
            )
        )

    return EpisodeSourcePackets(packets=packets)


def sanitize_episode_plan_against_source_packets(
    episode_plan: EpisodePlan,
    packets: EpisodeSourcePackets,
) -> EpisodePlan:
    """Drop plan assets that cannot be traced to the current episode source packet."""
    packets_by_episode = {packet.episode: packet for packet in packets.packets}
    episodes: list[EpisodeDramaPlan] = []
    for plan in episode_plan.episodes:
        packet = packets_by_episode.get(plan.episode)
        physical_action_chain = _fill_with_source_grounded_items(
            _filter_plan_assets(plan.physical_action_chain, packet),
            packet=packet,
            min_length=3,
            label="当前集原文动作",
        )
        scene_dynamics = _fill_with_source_grounded_items(
            _filter_plan_assets(plan.scene_dynamics, packet),
            packet=packet,
            min_length=2,
            label="当前集场面调度",
        )
        plan_data = plan.model_dump()
        plan_data.update(
            {
                "drama_engine": _source_grounded_scalar(
                    plan.drama_engine,
                    packet=packet,
                    label="当前集戏剧引擎",
                ),
                "protagonist_misbelief": _source_grounded_scalar(
                    plan.protagonist_misbelief,
                    packet=packet,
                    label="当前集主角认知",
                ),
                "truth_gap": _source_grounded_scalar(
                    plan.truth_gap,
                    packet=packet,
                    label="当前集真相差",
                ),
                "audience_information_gap": _source_grounded_scalar(
                    plan.audience_information_gap,
                    packet=packet,
                    label="当前集信息差",
                ),
                "source_assets_to_keep": _filter_plan_assets(
                    plan.source_assets_to_keep,
                    packet,
                ),
                "physical_action_chain": physical_action_chain,
                "scene_dynamics": scene_dynamics,
                "three_pull_beats": _fill_with_source_grounded_items(
                    _filter_plan_assets(plan.three_pull_beats, packet),
                    packet=packet,
                    min_length=3,
                    label="当前集三波拉扯",
                ),
                "false_payoff": _source_grounded_scalar(
                    plan.false_payoff,
                    packet=packet,
                    label="当前集假兑现",
                ),
                "planted_key": _source_grounded_scalar(
                    plan.planted_key,
                    packet=packet,
                    label="当前集钥匙",
                ),
                "strongest_line": _source_grounded_scalar(
                    plan.strongest_line,
                    packet=packet,
                    label="当前集短台词",
                ),
                "cliffhanger_design": _source_grounded_scalar(
                    plan.cliffhanger_design,
                    packet=packet,
                    label="当前集断点",
                ),
            }
        )
        episodes.append(EpisodeDramaPlan.model_validate(plan_data))
    episode_plan_data = episode_plan.model_dump()
    episode_plan_data["episodes"] = [episode.model_dump() for episode in episodes]
    return EpisodePlan.model_validate(episode_plan_data)


def packet_for_episode(
    packets: EpisodeSourcePackets | None,
    episode: int,
) -> EpisodeSourcePacket | None:
    if packets is None:
        return None
    return next((packet for packet in packets.packets if packet.episode == episode), None)


def handoff_from_episode(episode: EpisodeScript | None) -> EpisodeHandoff | None:
    if episode is None:
        return None
    final_lines = [
        line.text
        for scene in episode.scenes[-1:]
        for line in scene.lines[-10:]
        if line.text.strip()
    ]
    return EpisodeHandoff(
        previous_episode=episode.episode,
        previous_title=episode.title,
        previous_cliffhanger=episode.cliffhanger,
        previous_final_lines=final_lines,
        previous_state_update=episode.state_update,
    )

```


## File: `src/novel_drama_engine/adaptation_quality.py`
```
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any, Literal

from novel_drama_engine.models import (
    AdaptationQualityReport,
    AdaptationIntensity,
    ContinuityAuditReport,
    ContinuityLinkReport,
    EpisodeContext,
    EpisodePlan,
    EpisodeScript,
    MethodologyContext,
    MethodologyQualityIssue,
    MethodologyQualityReport,
    NextRoundContext,
    QualityStatus,
    ScriptBatch,
    SeriesStructurePlan,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    SourceFidelityCheck,
    SourceFidelityReport,
    StoryBible,
    StoryStage,
    StoryStateEntry,
    StoryStateLedger,
    ViralAssetReport,
)
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    merge_rewrite_instructions,
)
from novel_drama_engine.renderer import render_episode


PUNCTUATION_RE = re.compile(r"[\s，。！？、；：：“”‘’（）()《》【】\[\]·,.!?;:'\"<>-]+")
CHINESE_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{2,}")
FORBIDDEN_PREFIX_RE = re.compile(
    r"^(?:不得|禁止|不能|不要|严禁|避免|拒绝|不许|不可|不应|不准|别)"
)
WEAK_FORBIDDEN_WORDS = {
    "新增",
    "提前",
    "一次性",
    "全部",
    "完全",
    "无代价",
    "机械",
    "模板",
    "救场",
    "退场",
    "真相",
    "公开",
    "本轮",
    "过早",
    "完整",
    "结果",
    "泄露",
    "揭露",
}
GENERIC_CHARACTER_NAMES = {
    "黑幕",
    "画外",
    "旁白",
    "VO",
    "OS",
    "众人",
    "宾客",
    "围观百姓",
    "录音",
    "主持人",
    "保安",
    "护士",
    "医生",
    "值班医生",
    "检验员",
    "档案员",
    "司机",
    "黑衣司机",
    "工作人员",
    "店员",
    "服务员",
    "助理",
    "秘书",
    "记者",
    "路人",
    "警察",
    "法务",
}

INTENT_DRIFT_RULES: tuple[tuple[str, str, str], ...] = (
    (
        r"(?:给你准备了?惊喜|准备了?惊喜|他说[^。！？]{0,16}惊喜)",
        r"(?:你答应过|不是说好|说好的)[^。！？\n]{0,24}(?:影后|女一|新戏|资源|奖)",
        "对手主动承诺/诱导被改成主角主动索取，容易让人物显得功利或 OOC",
    ),
    (
        r"(?:早就|提前|已经|放在|压在|抽屉|办公室)[^。！？\n]{0,40}(?:解约协议|离婚协议|辞职信|退婚书)",
        r"(?:现场|当场|现在|马上|临时|一怒之下)[^。！？\n]{0,24}(?:解约|离婚|辞职|退婚|签字)",
        "深思熟虑的预谋决定被改成现场冲动决定，改变了人物逻辑和关键决定时机",
    ),
    (
        r"(?:沉默|僵住|克制|冷静|冰冷|决绝|平静)[^。！？\n]{0,40}(?:离开|签下|看着|转身|收起)",
        r"(?:我要你们|你们都给我|我跟你们拼了|你们等着|我会让你们后悔|我绝不会放过)",
        "克制决绝型情绪被改成歇斯底里狠话，偏离原文人物气质",
    ),
)

OPENING_TENSION_SOURCE_RE = re.compile(
    r"(?:抱坐|坐在[^。！？\n]{0,12}腿|腿上|手[^。！？\n]{0,16}(?:衣服|腰|领口|裙|衬衫)|"
    r"衣服里|镜头[^。！？\n]{0,16}(?:拍到|扫到|对准)|摄像机|直播)",
)
OPENING_TENSION_SCRIPT_RE = re.compile(
    r"(?:腿|衣服|领口|腰|手(?!机)|手指|手掌|指尖|镜头|摄像|直播|遮|贴近|压住|躲开|拍到|扫过)",
)
SOURCE_VULNERABILITY_RE = re.compile(
    r"(?:僵住|怔住|愣住|震惊|心碎|发抖|手抖|呼吸一滞|沉默|压住|忍住|克制|冷静|"
    r"平静|冰冷|羞辱|狼狈|被迫|被逼|害怕|不敢|无助|清醒|意识到|决定离开|"
    r"早已准备|深思熟虑)"
)
SOURCE_PREEXISTING_POWER_RE = re.compile(
    r"(?:重生|穿越|系统|预知|读档|回档|觉醒|早就知道|提前知道|提前布|早已布|"
    r"早已准备|提前准备|准备好|布好局|掌控全局|扮猪吃虎|隐藏身份|马甲|"
    r"黑卡|银行卡|银行经理|赘婿|龙王|战神归来|大佬回归|带着记忆|"
    r"上辈子|前世)"
)
SCRIPT_OMNISCIENT_COUNTERATTACK_RE = re.compile(
    r"(?:我早就知道|我全都知道|一切都在我掌控|全在我掌控|我已经安排好|"
    r"所有证据都在我手里|证据都在我手里|今天就是你们的死期|你们完了|"
    r"我等这一天很久了|我早就布好局|我已经布好局|我会让你们全部付出代价)"
)
SUPPORT_TAKEOVER_RE = re.compile(
    r"(?:我替你(?:决定|处理|签|解决|报仇|出面|解约|离婚)|替你(?:决定|处理|签|解决|报仇)|"
    r"不用你管|你不用出面|你只要站在我身后|剩下交给我|交给我就行|"
    r"我已经替你(?:签|退|解约|离婚|处理)|从现在起你听我的|这事我说了算|我替你选择)"
)
SUPPORT_CHOICE_RE = re.compile(
    r"(?:你自己决定|你来选|选择权在你|如果你愿意|我只是给你(?:退路|后盾|证据)|"
    r"我给你(?:退路|撑腰|证据|后盾)|你想怎么做|我陪你|你说了算)"
)
OPPONENT_CONTEXT_RE = re.compile(
    r"(?:反派|对手|敌人|压迫|羞辱|陷害|威胁|封杀|抢|夺|骗|背叛|争夺|打压|"
    r"诬陷|假千金|渣男|恶婆婆|仇|死敌|追杀|谋害|设计|冲突)"
)
OPPONENT_ACTIVE_RE = re.compile(
    r"(?:设局|布局|买通|威胁|栽赃|反咬|抢走|扣下|封锁|曝光|造谣|挑拨|"
    r"藏起|毁掉|撕掉|偷走|换掉|下药|绑架|追杀|举报|拉黑|逼迫|拦住|推搡|"
    r"砸向|摔碎|骗|挑衅|命令|安排人|派人|报警|撤资|封杀|夺权|诬陷|陷害|"
    r"反扑|反制|删掉|删除|截断|伪造|串供)"
)
OPPONENT_PASSIVE_RE = re.compile(
    r"(?:反派|对手|敌人|压迫者)[^。！？\n]{0,24}"
    r"(?:慌|惊慌|脸色发白|脸白|发抖|后退|躲在|只会哭|求救|不敢说话|惊恐|愣住)"
)
INTIMACY_RE = re.compile(r"(?:吻|亲吻|拥吻|激吻|吻住|吻上|亲上|抱住|拥抱|贴近)")
PUBLIC_EXPOSURE_RE = re.compile(
    r"(?:直播|曝光|热搜|偷拍|照片|镜头|全网|传出|拍到|上传|流出|公开视频|公开画面)"
)
HIGH_IMPACT_STAGE_RE = re.compile(
    r"(?:雨|雪|烟火|烟花|焰火|婚礼|订婚|生日宴|宴会|颁奖|领奖|发布会|庆典|"
    r"舞台|直播|热搜|镜头|法庭|刑场|城门|大殿|灵堂|产房|手术室|战场|擂台)"
)
IRREVERSIBLE_EXIT_RE = re.compile(
    r"(?=.*(?:解约|离婚|退婚|辞职|断亲|断绝关系|退圈|退赛|离开|分手|休书|和离))"
    r"(?=.*(?:协议|合同|签字|签下|递出|放在|抽屉|办公室|宣布|决定|摊牌|收好))",
    flags=re.S,
)
IDENTITY_REVEAL_RESULT_RE = re.compile(
    r"(?:身份|真相|亲子鉴定|血缘|真千金|假千金|继承人|少主|皇子|公主|"
    r"大佬|战神|神医|首富|凶手|幕后人|卧底|亲生)"
    r"[\s\S]{0,32}(?:公开|公布|揭穿|揭晓|承认|全场知道|被证实|坐实|验明|证明|确认)"
    r"|(?:公开|公布|揭穿|揭晓|承认|全场知道|被证实|坐实|验明|证明|确认)"
    r"[\s\S]{0,32}(?:身份|真相|亲子鉴定|血缘|真千金|假千金|继承人|少主|皇子|公主|"
    r"大佬|战神|神医|首富|凶手|幕后人|卧底|亲生)",
    flags=re.S,
)
INSTITUTIONAL_RECKONING_RE = re.compile(
    r"(?:法务|律师函|公证|警方|警察|法院|法庭|调查组|平台|董事会|家族|宗门|朝廷|"
    r"公司|资本|发布会|热搜|全网|舆论|官方|监管|仲裁|评委|裁判|鉴定机构)"
    r"[\s\S]{0,80}(?:倒台|封杀|解约潮|全面反转|反转|停摆|下架|停职|处罚|认罪|道歉|退圈|"
    r"破产|除名|废黜|判决|宣判|认证|证实|认输|败诉|被抓)"
    r"|(?:倒台|封杀|解约潮|全面反转|反转|停摆|下架|停职|处罚|认罪|道歉|退圈|"
    r"破产|除名|废黜|判决|宣判|认证|证实|认输|败诉|被抓)"
    r"[\s\S]{0,80}(?:法务|律师函|公证|警方|警察|法院|法庭|调查组|平台|董事会|家族|宗门|朝廷|"
    r"公司|资本|发布会|热搜|全网|舆论|官方|监管|仲裁|评委|裁判|鉴定机构)",
    flags=re.S,
)
EVIDENCE_SOURCE_RE = re.compile(
    r"(?:录音|视频|原始视频|监控|照片|合同|协议|账本|转账|流水|聊天记录|邮件|"
    r"诊断书|鉴定书|亲子鉴定|检测报告|数据包|后台记录|证词|证人|物证|印章|玉佩|"
    r"令牌|密信|圣旨|账册|原件|备份|账号|授权书|律师函|法务函|公证|报案回执|"
    r"证据来源|证据链)",
)

EVENT_LABELS = {
    "high_ritual_intimacy": "仪式化/高场面亲密节点",
    "public_intimacy_exposure": "亲密关系公开/曝光节点",
    "irreversible_exit_decision": "不可逆关系/合同决定",
    "identity_reveal_result": "身份/真相结论公开",
    "institutional_reckoning": "机构/法务/舆论清算结果",
}
EVIDENCE_REQUIRED_EVENTS = {
    "identity_reveal_result",
    "institutional_reckoning",
}


def normalize_text(value: str) -> str:
    return PUNCTUATION_RE.sub("", value).lower()


def _tokens(value: str) -> list[str]:
    raw = [token for token in CHINESE_TOKEN_RE.findall(value) if len(token) >= 2]
    expanded: list[str] = []
    for token in raw:
        if token in WEAK_FORBIDDEN_WORDS or token.isdigit():
            continue
        expanded.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", token):
            expanded.extend(
                chunk
                for chunk in (token[index : index + 2] for index in range(0, len(token) - 1))
                if chunk not in WEAK_FORBIDDEN_WORDS
            )
    return list(dict.fromkeys(expanded))


def _loose_contains(haystack: str, needle: str) -> bool:
    normalized_needle = normalize_text(needle)
    if not normalized_needle:
        return True
    normalized_haystack = normalize_text(haystack)
    if normalized_needle in normalized_haystack:
        return True

    tokens = _tokens(needle)
    if not tokens:
        return True
    if len(tokens) == 1:
        return tokens[0].lower() in normalized_haystack
    matched = sum(1 for token in tokens if normalize_text(token) in normalized_haystack)
    return matched >= min(2, len(tokens))


def _evidence_for(haystack: str, needle: str, *, limit: int = 2) -> list[str]:
    evidence: list[str] = []
    lines = [line.strip() for line in haystack.splitlines() if line.strip()]
    tokens = _tokens(needle)
    for line in lines:
        if _loose_contains(line, needle) or any(_loose_contains(line, token) for token in tokens):
            evidence.append(line[:100])
            if len(evidence) >= limit:
                break
    return evidence


def _episode_texts(script_batch: ScriptBatch) -> dict[int, str]:
    return {
        episode.episode: render_episode(episode)
        for episode in script_batch.episodes
    }


def _all_script_text(script_batch: ScriptBatch) -> str:
    return "\n\n".join(_episode_texts(script_batch).values())


def _opening_text(episode: EpisodeScript, line_count: int = 8) -> str:
    lines: list[str] = [episode.title, episode.hook_3s]
    for scene in episode.scenes[:1]:
        lines.append(scene.heading)
        for line in scene.lines[:line_count]:
            if line.speaker:
                lines.append(f"{line.speaker} {line.text}")
            else:
                lines.append(line.text)
    return "\n".join(lines)


def _target_episode_number(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"(?:EP|第)?\s*0*(\d{1,3})", value, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _mapping_assets(mapping: object) -> list[tuple[int | None, str]]:
    if isinstance(mapping, str):
        return [(None, mapping)]
    if not hasattr(mapping, "model_dump"):
        return []
    data = mapping.model_dump()
    episode_number = _target_episode_number(data.get("target_episode"))
    assets: list[str] = []
    for key in ["source", "information_increment", "adaptation_action"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            assets.append(value.strip())
    retained_assets = data.get("retained_assets")
    if isinstance(retained_assets, str):
        assets.extend(asset.strip() for asset in re.split(r"[、,，;；]", retained_assets) if asset.strip())
    elif isinstance(retained_assets, list):
        assets.extend(str(asset).strip() for asset in retained_assets if str(asset).strip())
    return [(episode_number, asset) for asset in assets if asset]


def _mapping_required_assets(mapping: object) -> list[tuple[int | None, str]]:
    if isinstance(mapping, str):
        # Legacy string mappings are usually observational outlines such as
        # "A -> EP01"; keep them out of hard source fidelity scoring.
        return []
    if not hasattr(mapping, "model_dump"):
        return []
    data = mapping.model_dump()
    episode_number = _target_episode_number(data.get("target_episode"))
    retained_assets = data.get("retained_assets")
    assets: list[str] = []
    if isinstance(retained_assets, str):
        assets.extend(asset.strip() for asset in re.split(r"[、,，;；]", retained_assets) if asset.strip())
    elif isinstance(retained_assets, list):
        assets.extend(str(asset).strip() for asset in retained_assets if str(asset).strip())
    return [(episode_number, asset) for asset in assets if asset]


def _mapping_context_assets(mapping: object) -> list[tuple[int | None, str]]:
    if isinstance(mapping, str):
        return [(None, mapping)]
    if not hasattr(mapping, "model_dump"):
        return []
    data = mapping.model_dump()
    episode_number = _target_episode_number(data.get("target_episode"))
    assets: list[str] = []
    for key in ["source", "information_increment"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            assets.append(value.strip())
    return [(episode_number, asset) for asset in assets if asset]


def _forbidden_term(rule: str) -> str:
    term = FORBIDDEN_PREFIX_RE.sub("", rule.strip())
    term = re.sub(r"[，,。；;].*$", "", term).strip()
    for word in sorted(WEAK_FORBIDDEN_WORDS | {"在", "把", "写成", "改成"}, key=len, reverse=True):
        term = term.replace(word, "")
    tokens = [token for token in _tokens(term) if token not in WEAK_FORBIDDEN_WORDS]
    if len(tokens) >= 2:
        return "".join(tokens[:2])
    if tokens:
        return tokens[0]
    return term


def _character_name(value: str) -> str:
    name = re.sub(r"^(?:录音里的|电话里的|年轻|老|小)", "", value.strip())
    name = re.sub(r"(?:OS|VO)$", "", name, flags=re.IGNORECASE)
    return name.strip()


def _script_characters(script_batch: ScriptBatch) -> set[str]:
    names: set[str] = set()
    for episode in script_batch.episodes:
        for scene in episode.scenes:
            names.update(_character_name(character) for character in scene.characters)
            for line in scene.lines:
                if line.speaker:
                    names.add(_character_name(line.speaker))
    return {name for name in names if name and name not in GENERIC_CHARACTER_NAMES}


def _known_character_match(name: str, known_names: Iterable[str]) -> bool:
    normalized = normalize_text(name)
    if not normalized:
        return True
    for known in known_names:
        normalized_known = normalize_text(known)
        if normalized == normalized_known:
            return True
        if normalized in normalized_known or normalized_known in normalized:
            return True
    return False


def _detect_intent_drift(source_text: str, script_text: str) -> list[str]:
    warnings: list[str] = []
    for source_pattern, script_pattern, warning in INTENT_DRIFT_RULES:
        if re.search(source_pattern, source_text, flags=re.S) and re.search(
            script_pattern,
            script_text,
            flags=re.S,
        ):
            warnings.append(warning)
    return warnings


def _early_script_text(script_batch: ScriptBatch, *, max_episodes: int = 2) -> str:
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)[:max_episodes]
    return "\n\n".join(render_episode(episode) for episode in episodes)


def _detect_agency_ramp_drift(
    *,
    source_text: str,
    episode_context: EpisodeContext,
    script_batch: ScriptBatch,
) -> list[str]:
    early_stages = {
        StoryStage.OPENING_PRESSURE,
        StoryStage.IDENTITY_HOOK,
        StoryStage.FIRST_COUNTERATTACK,
    }
    if episode_context.story_stage not in early_stages:
        return []

    source_sample = source_text[:3000]
    if not SOURCE_VULNERABILITY_RE.search(source_sample):
        return []
    if SOURCE_PREEXISTING_POWER_RE.search(source_sample):
        return []
    if not SCRIPT_OMNISCIENT_COUNTERATTACK_RE.search(_early_script_text(script_batch)):
        return []
    return [
        "主角情绪/主动权递进漂移：原文存在受压、震惊、克制或逐步清醒阶段，"
        "脚本过早写成全知全能式开杀。必须按“承受/识别 -> 决定 -> 行动 -> 反击”递进，"
        "除非原文本身已明确重生、预知、马甲或提前布局。"
    ]


def _detect_support_takeover(script_text: str) -> list[str]:
    if not SUPPORT_TAKEOVER_RE.search(script_text):
        return []
    if SUPPORT_CHOICE_RE.search(script_text):
        return []
    return [
        "支持型角色主动权越界：脚本出现替主角决定、替主角签字/解决冲突或“站我身后”式接管，"
        "但缺少给主角选择权、证据、退路或后盾的表达。必须让支持角色提供资源和安全感，"
        "核心决定与关键反击仍由主角完成。"
    ]


def _has_opponent_pressure(
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
) -> bool:
    context = "\n".join(
        [
            *source_analysis.events,
            *source_analysis.conflicts,
            story_bible.mainline,
            *story_bible.relationships,
            *story_bible.immutable_facts,
        ]
    )
    return bool(OPPONENT_CONTEXT_RE.search(context))


def _detect_opponent_passivity(
    *,
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
    script_text: str,
) -> list[str]:
    if not _has_opponent_pressure(source_analysis, story_bible):
        return []
    if OPPONENT_ACTIVE_RE.search(script_text):
        return []
    if not OPPONENT_PASSIVE_RE.search(script_text):
        return []
    return [
        "对手行动线空心：上游资产存在外部压迫/对抗，但脚本只写对手惊慌、后退或陪衬，"
        "没有主动设局、反制、施压、毁证、挑拨或升级动作。必须补一个可拍的对手主动动作，"
        "让主角反击有阻力和代价。"
    ]


def _forbidden_reveal_leaked(haystack: str, reveal: str) -> bool:
    normalized_reveal = normalize_text(reveal)
    if len(normalized_reveal) < 3:
        return False
    normalized_haystack = normalize_text(haystack)
    if normalized_reveal in normalized_haystack:
        return True

    identity_match = re.fullmatch(
        r"(?P<subject>[\u4e00-\u9fffA-Za-z0-9]{2,8})(?:是|才是|就是|为)"
        r"(?P<predicate>[\u4e00-\u9fffA-Za-z0-9]{2,12})",
        normalized_reveal,
    )
    if identity_match:
        subject = identity_match.group("subject")
        predicate = identity_match.group("predicate")
        direct_patterns = (
            rf"{re.escape(subject)}[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"(?:是|才是|就是|身份是)[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"{re.escape(predicate)}",
            rf"{re.escape(predicate)}[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"(?:是|属于|指向)[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"{re.escape(subject)}",
        )
        return any(re.search(pattern, normalized_haystack) for pattern in direct_patterns)

    return False


def _is_timing_or_result_forbidden_rule(rule: str) -> bool:
    return any(
        token in rule
        for token in (
            "提前",
            "过早",
            "一次性",
            "全部",
            "完全",
            "公开",
            "完整",
            "结果",
            "真相",
            "揭露",
            "揭晓",
            "坐实",
            "证实",
        )
    )


def _is_policy_forbidden_rule(rule: str) -> bool:
    return any(
        token in rule
        for token in (
            "主动性",
            "主动方",
            "人物性格",
            "性格",
            "软弱",
            "克制",
            "歇斯底里",
            "动机",
            "决定时机",
            "关键决定",
            "因果顺序",
            "证据来源",
            "关系状态",
        )
    )


def _concrete_forbidden_term(rule: str) -> str:
    text = FORBIDDEN_PREFIX_RE.sub("", rule.strip())
    text = re.sub(r"[，,。；;].*$", "", text).strip()
    for verb in ("凭空引入", "凭空制造", "新增", "引入", "加入", "添加", "套用"):
        if verb in text:
            return text.split(verb, 1)[1].strip()
    for verb in ("替换成", "写成", "改成"):
        if verb in text:
            candidate = text.split(verb, 1)[1].strip()
            if candidate and not _is_policy_forbidden_rule(candidate):
                return candidate
    return ""


def _identity_reveal_term(rule: str) -> str:
    for term in (
        "亲子鉴定",
        "真千金",
        "假千金",
        "身份",
        "血缘",
        "亲生",
        "继承人",
        "凶手",
        "幕后人",
    ):
        if term in rule:
            return term
    return _forbidden_term(rule)


def _identity_result_is_performed(script_text: str, term: str) -> bool:
    if len(normalize_text(term)) < 2:
        return False
    if not _loose_contains(script_text, term):
        return False
    if not IDENTITY_REVEAL_RESULT_RE.search(script_text):
        return False
    pending_patterns = (
        rf"{re.escape(term)}[\s\S]{{0,16}}(?:出来前|出结果前|结果出来前|未出|没出|还没出|等待|加急|要四小时)",
        rf"(?:出来前|出结果前|结果出来前|未出|没出|还没出|等待|加急|要四小时)[\s\S]{{0,16}}{re.escape(term)}",
    )
    return not any(re.search(pattern, script_text) for pattern in pending_patterns)


def _forbidden_rule_leaked(script_text: str, rule: str) -> bool:
    if _forbidden_reveal_leaked(script_text, rule):
        return True
    if _is_timing_or_result_forbidden_rule(rule):
        term = _identity_reveal_term(rule)
        return _identity_result_is_performed(script_text, term)
    if _is_policy_forbidden_rule(rule):
        return False
    term = _concrete_forbidden_term(rule) or _forbidden_term(rule)
    if len(normalize_text(term)) < 2:
        return False
    return _loose_contains(script_text, term)


def _forbidden_change_leaked(script_text: str, rule: str) -> bool:
    if _is_timing_or_result_forbidden_rule(rule):
        return _forbidden_rule_leaked(script_text, rule)

    if "洗白" in rule or "苦衷" in rule:
        return bool(
            re.search(
                r"(?:苦衷|不得已|逼不得已|为了保护|其实我有原因|我这么做是为了你|我也很痛苦)",
                script_text,
            )
        )

    if "暧昧" in rule:
        return bool(
            re.search(
                r"(?:暧昧|心动|脸红|接吻|亲吻|拥吻|十指相扣|靠进怀里|抱在怀里)",
                script_text,
            )
        )

    if "替" in rule and re.search(r"(?:决定|完成核心决定|签字|签了|报仇|做主|处理)", rule):
        return bool(SUPPORT_TAKEOVER_RE.search(script_text))

    if "留恋" in rule or "尚有感情" in rule or "还有感情" in rule:
        return bool(
            re.search(
                r"(?:还爱|舍不得|放不下|我没有忘|别离开我|求你别走|我还是爱你)",
                script_text,
            )
        )

    if "暴力反击" in rule:
        return bool(
            re.search(
                r"(?:一巴掌|扇了|抡起|砸向|捅向|掐住脖子|打断腿|打到吐血)",
                script_text,
            )
        )

    if "新增" in rule:
        term = _forbidden_term(rule)
        if len(normalize_text(term)) >= 3:
            return _loose_contains(script_text, term)

    # Conservative by default: broad negative guidance such as "不要狗血" is a
    # prompt constraint, not reliable deterministic evidence of a source leak.
    return False


def _contains(pattern: re.Pattern[str], text: str) -> bool:
    return bool(pattern.search(text))


def _story_event_markers(text: str) -> list[tuple[str, str]]:
    markers: list[tuple[str, str]] = []
    has_intimacy = _contains(INTIMACY_RE, text)
    if has_intimacy and _contains(HIGH_IMPACT_STAGE_RE, text):
        markers.append(
            (
                "high_ritual_intimacy",
                EVENT_LABELS["high_ritual_intimacy"],
            )
        )
    if has_intimacy and _contains(PUBLIC_EXPOSURE_RE, text):
        markers.append(
            (
                "public_intimacy_exposure",
                EVENT_LABELS["public_intimacy_exposure"],
            )
        )
    if _contains(IRREVERSIBLE_EXIT_RE, text):
        markers.append(
            (
                "irreversible_exit_decision",
                EVENT_LABELS["irreversible_exit_decision"],
            )
        )
    if _contains(IDENTITY_REVEAL_RESULT_RE, text):
        markers.append(
            ("identity_reveal_result", EVENT_LABELS["identity_reveal_result"])
        )
    if _contains(INSTITUTIONAL_RECKONING_RE, text):
        markers.append(
            ("institutional_reckoning", EVENT_LABELS["institutional_reckoning"])
        )
    return markers


def _audit_story_events(
    *,
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None,
    episode_context: EpisodeContext | None = None,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
) -> tuple[list[StoryStateEntry], list[str], list[str]]:
    entries: list[StoryStateEntry] = []
    blocking: list[str] = []
    advisory: list[str] = []
    events_by_key: dict[str, list[int]] = {}
    cumulative_evidence_text = ""
    if previous_context is not None:
        cumulative_evidence_text = "\n".join(
            [
                previous_context.summary,
                *previous_context.prop_states,
                *previous_context.foreshadowing_ledger,
                *previous_context.relationship_changes,
            ]
        )

    for episode in sorted(script_batch.episodes, key=lambda item: item.episode):
        visible_text = render_episode(episode)
        audit_text = visible_text
        episode_markers = _story_event_markers(audit_text)
        for key, label in episode_markers:
            events_by_key.setdefault(key, []).append(episode.episode)
            entries.append(
                StoryStateEntry(
                    episode=episode.episode,
                    kind="story_event",
                    key=key,
                    value=label,
                    status="active",
                    source="local_story_event_audit",
                )
            )

        for key, label in episode_markers:
            if key not in EVIDENCE_REQUIRED_EVENTS:
                continue
            if _contains(
                EVIDENCE_SOURCE_RE,
                "\n".join([cumulative_evidence_text, audit_text]),
            ):
                continue
            blocking.append(
                f"EP{episode.episode:02d} {label} 缺少可见证据链："
                "必须先交代证据来源、保存/验证方式和公开/裁决流程，"
                "再进入身份坐实、机构处罚、舆论反转或对手倒台结果。"
            )
        cumulative_evidence_text = "\n".join([cumulative_evidence_text, audit_text])

    for key, episodes in sorted(events_by_key.items()):
        unique_episodes = sorted(set(episodes))
        if len(unique_episodes) <= 1:
            continue
        label = EVENT_LABELS.get(key, key)
        joined = "、".join(f"EP{episode:02d}" for episode in unique_episodes)
        blocking.append(
            f"故事事件账本阻断：{label} 在 {joined} 重复兑现。"
            "同一高价值名场面只能首次演出一次；后续只能承接后果、反应或反扑，"
            "不能重复写成新的同类公开、裁决、曝光、身份揭晓或关键决定。"
        )

    if len(entries) == 0 and script_batch.episodes:
        advisory.append("story event ledger found no high-impact event markers")
    return entries, blocking, advisory


def build_source_fidelity_report(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    viral_asset_report: ViralAssetReport | None = None,
) -> SourceFidelityReport:
    del viral_asset_report
    checks: list[SourceFidelityCheck] = []
    blocking: list[str] = []
    advisory: list[str] = []
    script_text = _all_script_text(script_batch)
    episode_texts = _episode_texts(script_batch)
    rendered_episode_numbers = set(episode_texts)

    for fact in story_bible.immutable_facts[:8]:
        evidence = _evidence_for(script_text, fact)
        checks.append(
            SourceFidelityCheck(
                category="C0_immutable_fact",
                anchor=fact,
                status="passed" if evidence else "advisory",
                evidence=evidence,
                warning=None if evidence else "immutable fact tracked but not directly surfaced in this round",
            )
        )

    required_asset_total = 0
    required_asset_hits = 0
    for episode_number, asset in [
        pair
        for mapping in episode_context.source_to_episode_mapping
        for pair in _mapping_required_assets(mapping)
    ]:
        if len(normalize_text(asset)) < 4:
            continue
        if episode_number is not None and episode_number not in rendered_episode_numbers:
            continue
        required_asset_total += 1
        target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
        if _loose_contains(target_text, asset):
            required_asset_hits += 1
            checks.append(
                SourceFidelityCheck(
                    category="source_mapping_required",
                    anchor=asset,
                    episode=episode_number,
                    status="passed",
                    evidence=_evidence_for(target_text, asset),
                )
            )
            continue
        warning = f"source anchor not evidenced in script: {asset[:80]}"
        is_generic_planning_anchor = "->" in asset and re.search(
            r"(上一轮|开场|起势|继续|承接|推进)",
            asset,
        )
        if is_generic_planning_anchor:
            advisory.append(warning)
            status = "advisory"
        else:
            blocking.append(warning)
            status = "blocking"
        checks.append(
            SourceFidelityCheck(
                category="source_mapping_required",
                anchor=asset,
                episode=episode_number,
                status=status,
                warning=warning,
            )
        )

    for episode_number, asset in [
        pair
        for mapping in episode_context.source_to_episode_mapping
        for pair in _mapping_context_assets(mapping)
    ]:
        if len(normalize_text(asset)) < 4:
            continue
        if episode_number is not None and episode_number not in rendered_episode_numbers:
            continue
        target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
        if _loose_contains(target_text, asset):
            checks.append(
                SourceFidelityCheck(
                    category="source_mapping_context",
                    anchor=asset,
                    episode=episode_number,
                    status="passed",
                    evidence=_evidence_for(target_text, asset),
                )
            )
            continue
        checks.append(
            SourceFidelityCheck(
                category="source_mapping_context",
                anchor=asset,
                episode=episode_number,
                status="advisory",
                warning=f"source context not directly evidenced in script: {asset[:80]}",
            )
        )

    visual_hits = 0
    for moment in source_analysis.visual_moments[:10]:
        if _loose_contains(script_text, moment):
            visual_hits += 1
            checks.append(
                SourceFidelityCheck(
                    category="C2_visual_asset",
                    anchor=moment,
                    status="passed",
                    evidence=_evidence_for(script_text, moment),
                )
            )
    if source_analysis.visual_moments and visual_hits == 0:
        warning = "no source visual moment is preserved in the visible script"
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="C2_visual_asset",
                anchor="; ".join(source_analysis.visual_moments[:3]),
                status="advisory",
                warning=warning,
            )
        )

    first_episode = script_batch.episodes[0] if script_batch.episodes else None
    first_opening = _opening_text(first_episode) if first_episode else ""
    original_hook_preserved = False
    for hook in source_analysis.candidate_hooks[:3]:
        if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
            original_hook_preserved = True
            checks.append(
                SourceFidelityCheck(
                    category="hook_preservation",
                    anchor=hook,
                    episode=first_episode.episode if first_episode else None,
                    status="passed",
                    evidence=_evidence_for(first_opening or script_text, hook),
                )
            )
            break
    if source_analysis.candidate_hooks and not original_hook_preserved:
        warning = (
            "original strong hook appears dropped instead of being preserved or visibly upgraded"
        )
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="hook_preservation",
                anchor="; ".join(source_analysis.candidate_hooks[:3]),
                episode=first_episode.episode if first_episode else None,
                status="blocking",
                warning=warning,
            )
        )

    source_opening = source_text[:1600]
    if (
        first_episode is not None
        and OPENING_TENSION_SOURCE_RE.search(source_opening)
        and not OPENING_TENSION_SCRIPT_RE.search(first_opening)
    ):
        warning = (
            "source opening tension asset was removed instead of being safely visualized"
        )
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="opening_tension_preservation",
                anchor=source_opening[:160],
                episode=first_episode.episode,
                status="blocking",
                warning=warning,
            )
        )

    for warning in _detect_intent_drift(source_text, script_text):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="intent_drift",
                anchor=warning,
                status="blocking",
                warning=warning,
            )
        )

    for warning in _detect_agency_ramp_drift(
        source_text=source_text,
        episode_context=episode_context,
        script_batch=script_batch,
    ):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="agency_ramp",
                anchor=source_text[:160],
                status="blocking",
                evidence=_evidence_for(_early_script_text(script_batch), "早就知道"),
                warning=warning,
            )
        )

    for warning in _detect_support_takeover(script_text):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="support_role_boundary",
                anchor="support_role_agency_boundary",
                status="blocking",
                warning=warning,
            )
        )

    for warning in _detect_opponent_passivity(
        source_analysis=source_analysis,
        story_bible=story_bible,
        script_text=script_text,
    ):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="opponent_agency",
                anchor="opponent_active_countermove",
                status="blocking",
                warning=warning,
            )
        )

    for rule in story_bible.forbidden_changes:
        if _forbidden_change_leaked(script_text, rule):
            warning = f"forbidden addition/reveal may have leaked into script: {rule}"
            blocking.append(warning)
            checks.append(
                SourceFidelityCheck(
                    category="C4_forbidden_addition",
                    anchor=rule,
                    status="blocking",
                    evidence=_evidence_for(script_text, _forbidden_term(rule)),
                    warning=warning,
                )
            )

    for rule in episode_context.forbidden_reveals:
        term = _forbidden_term(rule)
        if len(normalize_text(term)) < 2:
            continue
        if _forbidden_rule_leaked(script_text, rule):
            warning = f"forbidden addition/reveal may have leaked into script: {rule}"
            blocking.append(warning)
            checks.append(
                SourceFidelityCheck(
                    category="C4_forbidden_addition",
                    anchor=rule,
                    status="blocking",
                    evidence=_evidence_for(script_text, term),
                    warning=warning,
                )
            )

    known_names = set(source_analysis.characters) | set(story_bible.characters)
    unknown_names = sorted(
        name
        for name in _script_characters(script_batch)
        if not _known_character_match(name, known_names)
    )
    if len(unknown_names) >= 4:
        warning = "新增多个未追踪说话角色，疑似替模型补剧情：" + "、".join(unknown_names[:6])
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="character_integrity",
                anchor="、".join(unknown_names[:6]),
                status="advisory",
                warning=warning,
            )
        )

    if source_text and not any(_loose_contains(script_text, token) for token in _tokens(source_text)[:12]):
        warning = "script has weak lexical overlap with the uploaded source"
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="C1_must_keep_scene",
                anchor=source_text[:80],
                status="advisory",
                warning=warning,
            )
        )

    asset_score = (
        round((required_asset_hits / required_asset_total) * 100)
        if required_asset_total
        else 100
    )
    non_asset_blockers = [
        warning
        for warning in blocking
        if not warning.startswith("source anchor not evidenced in script:")
    ]
    penalty_score = max(0, 100 - len(non_asset_blockers) * 18 - len(advisory) * 4)
    score = min(asset_score, penalty_score)
    return SourceFidelityReport(
        score=score,
        preserved_original_hook=original_hook_preserved,
        checks=checks,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
    )


def _tail_text(episode: EpisodeScript, line_count: int = 4) -> str:
    lines: list[str] = [episode.cliffhanger]
    if episode.scenes:
        for line in episode.scenes[-1].lines[-line_count:]:
            lines.append(f"{line.speaker or ''} {line.text}".strip())
    return "\n".join(line for line in lines if line.strip())


def _token_overlap(left: str, right: str) -> int:
    left_tokens = Counter(token for token in _tokens(left) if len(token) >= 2)
    right_tokens = Counter(token for token in _tokens(right) if len(token) >= 2)
    return sum((left_tokens & right_tokens).values())


def _token_match_strength(needle: str, haystack: str) -> tuple[int, int]:
    normalized_haystack = normalize_text(haystack)
    tokens = [token for token in _tokens(needle) if len(token) >= 2]
    matched = sum(1 for token in tokens if normalize_text(token) in normalized_haystack)
    return matched, len(tokens)


def _has_late_event_overlap(needle: str, haystack: str) -> bool:
    compact = normalize_text(needle)
    if len(compact) <= 4:
        return True
    late_segment = compact[4:]
    return any(normalize_text(token) in normalize_text(haystack) for token in _tokens(late_segment))


def build_continuity_audit_report(
    *,
    episode_context: EpisodeContext,
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None,
) -> ContinuityAuditReport:
    del episode_context
    links: list[ContinuityLinkReport] = []
    blocking: list[str] = []
    advisory: list[str] = []
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)

    if previous_context:
        first_episode = episodes[0] if episodes else None
        first_opening = _opening_text(first_episode) if first_episode else ""
        for hook in previous_context.open_hooks[:4]:
            if not hook.strip():
                continue
            if not _hook_acknowledged(hook, first_opening):
                advisory.append(
                    f"previous open hook is not acknowledged in this round opening: {hook[:80]}"
                )
        all_text = _all_script_text(script_batch)
        for reveal in previous_context.forbidden_reveals[:8]:
            if reveal.strip() and _forbidden_reveal_leaked(all_text, reveal):
                blocking.append(f"forbidden reveal leaked from previous context: {reveal}")

    for previous, current in zip(episodes, episodes[1:]):
        tail = _tail_text(previous)
        opening = _opening_text(current)
        warnings: list[str] = []
        status: Literal["passed", "advisory", "blocking"] = "passed"
        if previous.cliffhanger.strip() and not _hook_acknowledged(
            previous.cliffhanger,
            opening,
        ):
            warnings.append(
                "next episode opening does not visibly acknowledge previous cliffhanger"
            )
            advisory.append(
                f"EP{previous.episode:02d}->EP{current.episode:02d} may need opening linkage"
            )
            status = "advisory"
        links.append(
            ContinuityLinkReport(
                previous_episode=previous.episode,
                next_episode=current.episode,
                previous_cliffhanger=tail[:240],
                next_opening=opening[:240],
                status=status,
                warnings=warnings,
            )
        )

    score = max(0, 100 - len(blocking) * 25 - len(advisory) * 5)
    return ContinuityAuditReport(
        score=score,
        links=links,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
    )


def _entry_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return repr(value)


def _hook_acknowledged(hook: str, text: str) -> bool:
    if not (hook.strip() and text.strip()):
        return False
    if normalize_text(hook) in normalize_text(text):
        return True
    matched, total = _token_match_strength(hook, text)
    if total <= 2:
        return matched == total and matched > 0
    return matched >= 3 and (matched / total) >= 0.25 and _has_late_event_overlap(hook, text)


def build_story_state_ledger(
    *,
    script_batch: ScriptBatch,
    next_round_context: NextRoundContext,
    previous_context: NextRoundContext | None,
    episode_context: EpisodeContext | None = None,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
) -> StoryStateLedger:
    entries: list[StoryStateEntry] = []
    warnings: list[str] = []
    blocking_warnings: list[str] = []
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)

    if previous_context:
        first_episode = episodes[0] if episodes else None
        first_opening = _opening_text(first_episode) if first_episode else ""
        for hook in previous_context.open_hooks:
            acknowledged = _hook_acknowledged(hook, first_opening)
            entries.append(
                StoryStateEntry(
                    kind="open_hook",
                    key=hook[:40],
                    value=hook,
                    status="closed" if acknowledged else "open",
                    source="previous_context",
                )
            )
        for reveal in previous_context.forbidden_reveals:
            entries.append(
                StoryStateEntry(
                    kind="forbidden_reveal",
                    key=reveal[:40],
                    value=reveal,
                    status="forbidden",
                    source="previous_context",
                )
            )

    for index, episode in enumerate(episodes):
        if not episode.state_update:
            warnings.append(f"EP{episode.episode:02d} missing state_update")
        next_episode = episodes[index + 1] if index + 1 < len(episodes) else None
        hook_status: Literal["open", "closed"] = "open"
        if next_episode and _hook_acknowledged(
            episode.cliffhanger,
            _opening_text(next_episode),
        ):
            hook_status = "closed"
        entries.append(
            StoryStateEntry(
                episode=episode.episode,
                kind="open_hook",
                key=episode.cliffhanger[:40],
                value=episode.cliffhanger,
                status=hook_status,
                source="episode.cliffhanger",
            )
        )
        for key, value in episode.state_update.items():
            entries.append(
                StoryStateEntry(
                    episode=episode.episode,
                    kind="episode_state",
                    key=str(key),
                    value=_entry_value(value),
                    status="active",
                    source="episode.state_update",
                )
            )

    for reveal in next_round_context.forbidden_reveals:
        entries.append(
            StoryStateEntry(
                kind="forbidden_reveal",
                key=reveal[:40],
                value=reveal,
                status="forbidden",
                source="next_round_context",
            )
        )
    for character, facts in next_round_context.character_knowledge.items():
        for fact in facts:
            entries.append(
                StoryStateEntry(
                    kind="character_knowledge",
                    key=character,
                    value=fact,
                    status="active",
                    source="next_round_context",
                )
            )
    for change in next_round_context.relationship_changes:
        entries.append(
            StoryStateEntry(
                kind="relationship_change",
                key=change[:40],
                value=change,
                status="active",
                source="next_round_context",
            )
        )
    for prop in next_round_context.prop_states:
        entries.append(
            StoryStateEntry(
                kind="prop_state",
                key=prop[:40],
                value=prop,
                status="active",
                source="next_round_context",
            )
        )
    for item in next_round_context.foreshadowing_ledger:
        entries.append(
            StoryStateEntry(
                kind="foreshadowing",
                key=item[:40],
                value=item,
                status="open",
                source="next_round_context",
            )
        )

    (
        story_event_entries,
        story_event_blocking,
        story_event_advisory,
    ) = _audit_story_events(
        script_batch=script_batch,
        previous_context=previous_context,
        episode_context=episode_context,
        episode_plan=episode_plan,
        series_structure_plan=series_structure_plan,
    )
    entries.extend(story_event_entries)
    blocking_warnings.extend(story_event_blocking)
    warnings.extend(story_event_advisory)

    if len(next_round_context.open_hooks) > 8:
        warnings.append("too many open hooks; next round may lose focus")
    final_cliffhanger = episodes[-1].cliffhanger if episodes else ""
    if final_cliffhanger and not any(
        _hook_acknowledged(final_cliffhanger, hook)
        for hook in next_round_context.open_hooks
    ):
        warnings.append(
            "next_round_context open_hooks does not carry the final episode cliffhanger"
        )

    return StoryStateLedger(
        current_episode=next_round_context.current_episode,
        entries=entries,
        open_hooks=next_round_context.open_hooks,
        forbidden_reveals=next_round_context.forbidden_reveals,
        character_knowledge=next_round_context.character_knowledge,
        relationship_changes=next_round_context.relationship_changes,
        prop_states=next_round_context.prop_states,
        foreshadowing_ledger=next_round_context.foreshadowing_ledger,
        blocking_warnings=blocking_warnings,
        warnings=warnings,
    )


def build_adaptation_quality_report(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    next_round_context: NextRoundContext,
    previous_context: NextRoundContext | None,
    viral_asset_report: ViralAssetReport | None = None,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
) -> AdaptationQualityReport:
    source_fidelity = build_source_fidelity_report(
        source_text=source_text,
        source_analysis=source_analysis,
        episode_context=episode_context,
        story_bible=story_bible,
        script_batch=script_batch,
        viral_asset_report=viral_asset_report,
    )
    continuity = build_continuity_audit_report(
        episode_context=episode_context,
        script_batch=script_batch,
        previous_context=previous_context,
    )
    ledger = build_story_state_ledger(
        script_batch=script_batch,
        next_round_context=next_round_context,
        previous_context=previous_context,
        episode_context=episode_context,
        episode_plan=episode_plan,
        series_structure_plan=series_structure_plan,
    )
    blocking = dedupe_quality_items([
        *source_fidelity.blocking_warnings,
        *continuity.blocking_warnings,
        *ledger.blocking_warnings,
    ])
    advisory = dedupe_quality_items([
        *source_fidelity.advisory_warnings,
        *continuity.advisory_warnings,
        *ledger.warnings,
    ])
    rewrite_instruction = ""
    if blocking:
        rewrite_instruction = (
            "改编一致性阻断：必须保留原著强钩子/名场面/主动方逻辑，不得泄露 forbidden reveal，"
            "不得新增 story bible 禁止项；必须遵守故事事件账本，同一高价值名场面不得重复兑现，"
            "身份/机构/舆论/权威裁决类结果必须先交代证据来源和流程；"
            "必须守住主角情绪递进、支持角色选择权边界和对手主动反制。具体问题："
            + "；".join(blocking[:6])
        )
    return AdaptationQualityReport(
        source_fidelity=source_fidelity,
        continuity=continuity,
        story_state_ledger=ledger,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
        rewrite_instruction=rewrite_instruction,
    )


def build_methodology_quality_report(
    *,
    source_analysis: SourceAnalysis,
    script_batch: ScriptBatch,
    source_strength_profile: SourceStrengthProfile,
    methodology_context: MethodologyContext | None,
    viral_asset_report: ViralAssetReport | None = None,
) -> MethodologyQualityReport:
    if (
        source_strength_profile.overall_level != SourceStrengthLevel.STRONG
        or source_strength_profile.recommended_intensity != AdaptationIntensity.LIGHT
        or methodology_context is None
    ):
        return MethodologyQualityReport()

    source_fidelity_cards = [
        card
        for card in methodology_context.cards
        if card.category == "source_fidelity"
    ]
    if not source_fidelity_cards:
        return MethodologyQualityReport()

    card = source_fidelity_cards[0]
    script_text = _all_script_text(script_batch)
    first_episode = script_batch.episodes[0] if script_batch.episodes else None
    is_opening_round = first_episode is None or first_episode.episode <= 1
    first_opening = _opening_text(first_episode) if first_episode else ""
    issues: list[MethodologyQualityIssue] = []

    if is_opening_round:
        for hook in source_analysis.candidate_hooks[:3]:
            if not hook.strip():
                continue
            if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
                continue
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id,
                    card_name=card.name,
                    severity="blocking",
                    episode=first_episode.episode if first_episode else None,
                    message=f"强原文轻改失败：原文开场钩子未被保留或视听化：{hook}",
                    evidence=_evidence_for(script_text, hook),
                )
            )

        high_value_assets = list(source_analysis.visual_moments[:8])
        if viral_asset_report is not None:
            high_value_assets.extend(viral_asset_report.signature_scenes[:5])
        high_value_assets = list(
            dict.fromkeys(asset for asset in high_value_assets if asset.strip())
        )
        if high_value_assets and not any(
            _loose_contains(script_text, asset) for asset in high_value_assets
        ):
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id,
                    card_name=card.name,
                    severity="blocking",
                    e

... [TRUNCATED FOR REVIEW PACK] ...

```


## File: `src/novel_drama_engine/source_evidence.py`
```
from __future__ import annotations

import re

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    QualityReport,
    QualityStatus,
    ScriptBatch,
    SourceEvidenceItem,
    SourceEvidenceReport,
    SourceEvidenceSpan,
)
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    merge_rewrite_instructions,
)
from novel_drama_engine.renderer import render_shooting_episode


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def _split_assets(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[、,，；;|\n]+", value)
    else:
        parts = value
    ignored = {"none", "null", "nil", "-", "无", "暂无"}
    return [
        part.strip()
        for part in parts
        if part and part.strip() and part.strip().lower() not in ignored
    ]


def _asset_needles(asset: str) -> list[str]:
    compact = _compact(asset)
    if not compact:
        return []
    needles = [compact]
    cjk_runs = re.findall(r"[\u4e00-\u9fff]{3,}", compact)
    for run in cjk_runs:
        for size in (4, 3):
            for index in range(0, len(run) - size + 1):
                needles.append(run[index : index + size])
    return list(dict.fromkeys(needles))


def _asset_tokens(asset: str) -> list[str]:
    compact = _compact(asset)
    tokens: list[str] = []
    for run in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", compact):
        tokens.append(run)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", run):
            tokens.extend(run[index : index + 2] for index in range(0, len(run) - 1))
    return list(dict.fromkeys(token for token in tokens if len(token) >= 2))


def _has_specific_asset_overlap(line: str, asset: str) -> bool:
    compact_asset = _compact(asset)
    if len(compact_asset) <= 4:
        return False
    compact_line = _compact(line)
    late_tokens = _asset_tokens(compact_asset[4:])
    return any(token in compact_line for token in late_tokens)


def _line_matches_asset(line: str, asset: str) -> bool:
    compact_line = _compact(line)
    if not compact_line:
        return False
    compact_asset = _compact(asset)
    if compact_asset and compact_asset in compact_line:
        return True
    if len(compact_asset) <= 4:
        return any(needle in compact_line for needle in _asset_needles(asset))

    tokens = _asset_tokens(asset)
    if not tokens:
        return False
    matched = sum(1 for token in tokens if token in compact_line)
    coverage = matched / max(1, len(tokens))
    return matched >= 3 and coverage >= 0.25 and _has_specific_asset_overlap(line, asset)


def _asset_match_score(line: str, asset: str) -> float:
    compact_line = _compact(line)
    compact_asset = _compact(asset)
    if not compact_line:
        return 0
    if compact_asset and compact_asset in compact_line:
        return 1000 + len(compact_asset)
    tokens = _asset_tokens(asset)
    if not tokens:
        return 0
    matched = sum(1 for token in tokens if token in compact_line)
    coverage = matched / max(1, len(tokens))
    if not _line_matches_asset(line, asset):
        return 0
    late_bonus = 2 if _has_specific_asset_overlap(line, asset) else 0
    return matched + coverage + late_bonus


def _script_line_entries(script: EpisodeScript) -> list[tuple[int, str]]:
    rendered = render_shooting_episode(script)
    return [
        (index, line.strip())
        for index, line in enumerate(rendered.splitlines(), start=1)
        if line.strip()
    ]


def _script_lines(script: EpisodeScript) -> list[str]:
    return [line for _, line in _script_line_entries(script)]


def _line_entry_for_asset(
    entries: list[tuple[int, str]],
    asset: str,
) -> tuple[int | None, str | None]:
    candidates = [
        (_asset_match_score(line, asset), index, line)
        for index, line in entries
    ]
    candidates = [candidate for candidate in candidates if candidate[0] > 0]
    if not candidates:
        return None, None
    _, index, line = max(candidates, key=lambda item: item[0])
    return index, line


def _source_line_for_asset(
    packet: EpisodeSourcePacket,
    asset: str,
) -> tuple[int | None, str | None]:
    lines = [line.strip() for line in packet.source_excerpt.splitlines() if line.strip()]
    candidates = [
        (_asset_match_score(line, asset), index, line)
        for index, line in enumerate(lines, start=1)
    ]
    candidates = [candidate for candidate in candidates if candidate[0] > 0]
    if candidates:
        _, index, line = max(candidates, key=lambda item: item[0])
        return index, line
    anchor = packet.source_anchor.strip()
    if anchor and _line_matches_asset(anchor, asset):
        return 1, anchor
    return None, None


def _evidence_span_for_asset(
    packet: EpisodeSourcePacket,
    asset: str,
    script_entries: list[tuple[int, str]],
    adaptation_reason: str,
) -> SourceEvidenceSpan:
    source_line_index, source_line = _source_line_for_asset(packet, asset)
    script_line_index, script_line = _line_entry_for_asset(script_entries, asset)
    return SourceEvidenceSpan(
        asset=asset,
        source_anchor=packet.source_anchor,
        source_excerpt=packet.source_excerpt,
        source_line=source_line,
        source_line_index=source_line_index,
        script_line=script_line,
        script_line_index=script_line_index,
        adaptation_reason=adaptation_reason,
        status="matched" if script_line else "missing",
    )


def _packet_assets(packet: EpisodeSourcePacket) -> list[str]:
    if packet.source_evidence_assets is not None:
        return _split_assets(packet.source_evidence_assets)
    return _split_assets(packet.c1_must_keep_assets)


def _is_system_placeholder_anchor(anchor: str) -> bool:
    return bool(
        re.fullmatch(
            r"EP\d{2,3}\s+当前集原文",
            anchor.strip(),
            flags=re.IGNORECASE,
        )
    )


def _packet_reason(packet: EpisodeSourcePacket) -> str:
    if packet.c1_must_keep_assets:
        return "保留原文必留资产：" + "、".join(packet.c1_must_keep_assets[:4])
    if packet.c0_facts:
        return "承接原文关键信息：" + "、".join(packet.c0_facts[:3])
    return "追踪原文锚点是否落到正片。"


def _episode_number_from_mapping(mapping: EpisodeSourceMapping) -> int | None:
    value = mapping.target_episode
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return None


def _mapping_packets(episode_context: EpisodeContext) -> list[EpisodeSourcePacket]:
    packets: list[EpisodeSourcePacket] = []
    fallback_episode = 1
    for mapping in episode_context.source_to_episode_mapping:
        episode = _episode_number_from_mapping(mapping) or fallback_episode
        fallback_episode = episode + 1
        retained_assets = _split_assets(mapping.retained_assets)
        packets.append(
            EpisodeSourcePacket(
                episode=episode,
                source_anchor=mapping.source,
                source_excerpt=mapping.source,
                c0_facts=_split_assets(mapping.information_increment),
                c1_must_keep_assets=retained_assets,
                c2_visual_assets=_split_assets(mapping.adaptation_action),
            )
        )
    return packets


def build_source_evidence_report(
    script_batch: ScriptBatch,
    *,
    episode_source_packets: EpisodeSourcePackets | None = None,
    episode_context: EpisodeContext | None = None,
) -> SourceEvidenceReport:
    scripts = {script.episode: script for script in script_batch.episodes}
    packets = (
        episode_source_packets.packets
        if episode_source_packets is not None
        else _mapping_packets(episode_context)
        if episode_context is not None
        else []
    )

    items: list[SourceEvidenceItem] = []
    missing_items: list[str] = []
    matched_count = 0
    total_count = 0

    for packet in packets:
        script = scripts.get(packet.episode)
        if script is None:
            continue
        hard_assets = _packet_assets(packet)
        assets = hard_assets
        if not assets:
            assets = _split_assets(packet.c1_must_keep_assets)
        if not assets:
            assets = _split_assets(packet.c0_facts)
        if not assets and not _is_system_placeholder_anchor(packet.source_anchor):
            assets = [packet.source_anchor]

        adaptation_reason = _packet_reason(packet)
        line_entries = _script_line_entries(script) if script is not None else []
        evidence_spans = [
            _evidence_span_for_asset(
                packet,
                asset,
                line_entries,
                adaptation_reason,
            )
            for asset in assets
        ]

        total_count += len(evidence_spans)
        matched_spans = [span for span in evidence_spans if span.status == "matched"]
        missing_spans = [span for span in evidence_spans if span.status == "missing"]
        matched_count += len(matched_spans)
        script_evidence = [
            span.script_line for span in matched_spans if span.script_line
        ]
        unique_evidence = list(dict.fromkeys(script_evidence))[:6]
        if missing_spans and hard_assets:
            missing_items.extend(
                f"EP{packet.episode:02d} 缺少原文资产：{span.asset}"
                for span in missing_spans
            )

        if matched_spans and missing_spans:
            status = "partial"
        elif matched_spans:
            status = "matched"
        else:
            status = "missing"

        items.append(
            SourceEvidenceItem(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                adaptation_reason=adaptation_reason,
                retained_assets=assets,
                script_evidence=unique_evidence,
                evidence_spans=evidence_spans,
                status=status,
            )
        )

    coverage_score = round((matched_count / total_count) * 100) if total_count else 100
    rewrite_instruction = ""
    if missing_items:
        rewrite_instruction = (
            "原文证据未落到正片：请优先把缺失的必留资产转成可见动作、道具、"
            "关系反应或短对白；强原文本身已有爆款冲突时，只做视听化增强，不要另起新冲突。"
        )

    return SourceEvidenceReport(
        coverage_score=coverage_score,
        items=items,
        missing_items=missing_items,
        rewrite_instruction=rewrite_instruction,
    )


def merge_source_evidence_into_quality_report(
    quality_report: QualityReport,
    source_evidence_report: SourceEvidenceReport,
) -> QualityReport:
    if not source_evidence_report.missing_items:
        return quality_report
    missing_preview = "；".join(source_evidence_report.missing_items[:5])
    blocking_issue = f"source_evidence: {missing_preview}"
    blocking_issues = dedupe_quality_items([*quality_report.blocking_issues, blocking_issue])
    rewrite_instruction = merge_rewrite_instructions(
        [
            quality_report.rewrite_instruction,
            source_evidence_report.rewrite_instruction,
            missing_preview,
        ],
        blocking=True,
    )
    return quality_report.model_copy(
        update={
            "status": QualityStatus.NEEDS_REWRITE,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )


def render_source_evidence_report(report: SourceEvidenceReport) -> str:
    parts = [
        "# Source Evidence Report",
        "",
        f"- Coverage: {report.coverage_score}%",
        f"- Missing: {len(report.missing_items)}",
    ]
    if report.rewrite_instruction:
        parts.extend(["", f"Rewrite: {report.rewrite_instruction}"])
    for item in report.items:
        parts.extend(
            [
                "",
                f"## EP{item.episode:02d} · {item.status}",
                f"- Source: {item.source_anchor}",
                f"- Reason: {item.adaptation_reason}",
                f"- Assets: {'、'.join(item.retained_assets) if item.retained_assets else '-'}",
            ]
        )
        if item.script_evidence:
            parts.append("- Script Evidence:")
            parts.extend(f"  - {line}" for line in item.script_evidence)
        if item.evidence_spans:
            parts.append("- Source Span Evidence:")
            for span in item.evidence_spans:
                source_ref = (
                    f"source L{span.source_line_index}: {span.source_line}"
                    if span.source_line_index and span.source_line
                    else "source missing"
                )
                script_ref = (
                    f"script L{span.script_line_index}: {span.script_line}"
                    if span.script_line_index and span.script_line
                    else "script missing"
                )
                parts.append(
                    f"  - {span.status} · {span.asset} · {source_ref} -> {script_ref}"
                )
    if report.missing_items:
        parts.extend(["", "## Missing Items"])
        parts.extend(f"- {item}" for item in report.missing_items)
    return "\n".join(parts).strip() + "\n"

```


## File: `src/novel_drama_engine/drama_quality.py`
```
from __future__ import annotations

from collections import Counter

from novel_drama_engine.models import (
    AdaptationQualityReport,
    DramaQualityComparison,
    DramaQualityDimension,
    DramaQualityReport,
    EpisodeScript,
    QualityReport,
    QualityStatus,
    ScriptBatch,
)
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    merge_rewrite_instructions,
)
from novel_drama_engine.script_quality import (
    episode_quality_metrics,
    episode_quality_warnings,
    has_explanatory_or_value_summary,
)


SOURCE_FIDELITY_BLOCKING_WARNING_TOKENS = (
    "未追踪",
    "新增多个",
    "替模型补剧情",
    "原文偏离",
    "OOC",
    "主动方",
    "主动权",
    "动机",
    "全知全能",
    "证据链",
    "时间线",
    "现场冲动",
    "主动索取",
    "开场张力",
    "opening tension",
    "untracked",
    "introduced multiple",
    "speaking characters",
)


def _clamp(value: int) -> int:
    return max(0, min(10, value))


def _dimension_status(score: int, *, blocking_at: int = 5) -> str:
    if score <= blocking_at:
        return "blocking"
    if score <= 7:
        return "advisory"
    return "passed"


def _dimension(
    name,
    score: int,
    *,
    evidence: list[str] | None = None,
    suggestion: str = "",
    blocking_at: int = 5,
) -> DramaQualityDimension:
    score = _clamp(score)
    return DramaQualityDimension(
        name=name,
        score=score,
        status=_dimension_status(score, blocking_at=blocking_at),
        evidence=evidence or [],
        suggestion=suggestion,
    )


def _all_episode_warnings(script_batch: ScriptBatch) -> list[str]:
    return [
        warning
        for episode in script_batch.episodes
        for warning in episode_quality_warnings(episode)
    ]


def _line_texts(episode: EpisodeScript, *, kinds: set[str] | None = None) -> list[str]:
    texts: list[str] = []
    for scene in episode.scenes:
        for line in scene.lines:
            if kinds is not None and line.kind not in kinds:
                continue
            if line.speaker:
                texts.append(f"{line.speaker} {line.emotion or ''} {line.text}".strip())
            else:
                texts.append(line.text)
    return texts


def _dialogue_samples(script_batch: ScriptBatch, limit: int = 4) -> list[str]:
    samples: list[str] = []
    for episode in script_batch.episodes:
        for text in _line_texts(episode, kinds={"dialogue", "os", "vo"}):
            if has_explanatory_or_value_summary(text) or len(text) > 34:
                samples.append(f"EP{episode.episode:02d} {text[:80]}")
                if len(samples) >= limit:
                    return samples
    return samples


def _emotion_turn_count(episode: EpisodeScript) -> int:
    emotions = [episode.main_emotion.strip()] if episode.main_emotion.strip() else []
    for scene in episode.scenes:
        for line in scene.lines:
            if line.emotion and line.emotion.strip():
                emotions.append(line.emotion.strip())
    return len(set(emotions))


def _score_from_metrics(script_batch: ScriptBatch, quality_report: QualityReport | None) -> tuple[list[DramaQualityDimension], list[str]]:
    warnings = _all_episode_warnings(script_batch)
    warning_text = "\n".join(warnings)
    metrics = [episode_quality_metrics(episode) for episode in script_batch.episodes]
    episode_count = max(1, len(metrics))

    avg_long_voiced = sum(item.long_voiced_lines for item in metrics) / episode_count
    avg_explanatory = sum(item.explanatory_voiced_lines for item in metrics) / episode_count
    avg_strong_lines = sum(item.strong_lines for item in metrics) / episode_count
    avg_opening_conflict = sum(item.opening_conflict_lines for item in metrics) / episode_count
    avg_action_lines = sum(item.action_lines for item in metrics) / episode_count
    avg_voiced_lines = sum(item.voiced_lines for item in metrics) / episode_count
    avg_emotion_turns = sum(_emotion_turn_count(ep) for ep in script_batch.episodes) / episode_count
    critically_underfilled = avg_action_lines < 3 or avg_voiced_lines < 5

    character_penalty = 0
    for token in ["intent_drift", "character", "OOC", "动机", "主动方", "人物"]:
        if token in warning_text:
            character_penalty += 1
    character_score = 8 - character_penalty

    conflict_base = quality_report.scores.conflict if quality_report else 7
    conflict_score = conflict_base
    if avg_action_lines < 6 or avg_voiced_lines < 8:
        conflict_score -= 2
    if critically_underfilled:
        conflict_score = min(conflict_score, 4)
    if avg_opening_conflict < 1:
        conflict_score -= 1

    emotion_score = 6 + min(3, int(avg_emotion_turns))
    if any("OS at" in warning for warning in warnings):
        emotion_score -= 1
    if avg_strong_lines < 1:
        emotion_score -= 1
    if critically_underfilled:
        emotion_score = min(emotion_score, 4)

    dialogue_score = 9 - int(avg_long_voiced) - int(avg_explanatory)
    if avg_voiced_lines < 5:
        dialogue_score = min(dialogue_score, 5)
    if _dialogue_samples(script_batch):
        dialogue_score -= 1

    hook_score = (
        round((quality_report.scores.hook + quality_report.scores.cliffhanger) / 2)
        if quality_report
        else 7
    )
    if any("cliffhanger" in warning for warning in warnings):
        hook_score -= 1
    if critically_underfilled:
        hook_score = min(hook_score, 5)

    dimensions = [
        _dimension(
            "character_integrity",
            character_score,
            evidence=[warning for warning in warnings if "character" in warning or "动机" in warning][:3],
            suggestion="回到 Story Bible 和 C0 事实，修正人物主动方、动机和说话气质。",
        ),
        _dimension(
            "conflict_causality",
            conflict_score,
            evidence=[
                f"avg_action_lines={avg_action_lines:.1f}",
                f"avg_voiced_lines={avg_voiced_lines:.1f}",
            ],
            suggestion="补清楚谁主动做了什么、对手如何反制、当场后果是什么。",
        ),
        _dimension(
            "emotional_progression",
            emotion_score,
            evidence=[f"avg_emotion_turns={avg_emotion_turns:.1f}"],
            suggestion="补足震惊、克制、反击、失落或爽点的递进，不要一上来全知全能开杀。",
        ),
        _dimension(
            "dialogue_naturalness",
            dialogue_score,
            evidence=_dialogue_samples(script_batch),
            suggestion="删掉解释型长句，把信息藏进短对白、停顿、动作和潜台词。",
        ),
        _dimension(
            "hook_and_cliffhanger",
            hook_score,
            evidence=[warning for warning in warnings if "cliffhanger" in warning][:3],
            suggestion="把开场钩子和结尾钩子写成已经演出来的动作/道具/短台词。",
        ),
    ]
    return dimensions, warnings


def _source_asset_dimension(
    adaptation_quality_report: AdaptationQualityReport | None,
) -> DramaQualityDimension:
    if adaptation_quality_report is None:
        return _dimension(
            "source_asset_preservation",
            7,
            evidence=["no adaptation_quality_report"],
            suggestion="需要结合原文 C0/C1 和 source fidelity report 复核。",
            blocking_at=4,
        )

    fidelity = adaptation_quality_report.source_fidelity
    score = round(fidelity.score / 10)
    evidence = [
        *fidelity.blocking_warnings[:2],
        *fidelity.advisory_warnings[:2],
    ]
    if fidelity.score < 50:
        evidence.insert(0, f"source similarity below 5/10: {fidelity.score}/100")
        score = min(score, 4)
    evidence_text = "\n".join(evidence)
    has_source_blocker = bool(fidelity.blocking_warnings) or any(
        token in evidence_text for token in SOURCE_FIDELITY_BLOCKING_WARNING_TOKENS
    )
    if has_source_blocker:
        score = min(score, 4)
    return _dimension(
        "source_asset_preservation",
        score,
        evidence=evidence,
        suggestion="恢复原文强冲突、关键情绪和不可改事实，避免为了爽点改掉核心逻辑。",
        blocking_at=4,
    )


def _overall(dimensions: list[DramaQualityDimension]) -> int:
    if not dimensions:
        return 0
    weights = Counter(
        {
            "character_integrity": 2,
            "conflict_causality": 2,
            "emotional_progression": 2,
            "dialogue_naturalness": 1,
            "source_asset_preservation": 2,
            "hook_and_cliffhanger": 1,
        }
    )
    weighted_total = sum(item.score * weights[item.name] for item in dimensions)
    total_weight = sum(weights[item.name] for item in dimensions)
    return _clamp(round(weighted_total / total_weight))


def _baseline_score(script_batch: ScriptBatch) -> int:
    dimensions, _ = _score_from_metrics(script_batch, None)
    dimensions.append(_dimension("source_asset_preservation", 7, blocking_at=4))
    return _overall(dimensions)


def _comparison(
    *,
    pipeline_score: int,
    baseline_script_batch: ScriptBatch | None,
) -> DramaQualityComparison | None:
    if baseline_script_batch is None:
        return None
    baseline_score = _baseline_score(baseline_script_batch)
    delta = pipeline_score - baseline_score
    if delta >= 2:
        verdict = "pipeline_clearly_better"
        reason = "pipeline overall score is at least 2 points above the direct baseline."
    elif delta == 1:
        verdict = "pipeline_slightly_better"
        reason = "pipeline is better, but the margin is not yet a clear win."
    elif delta == 0:
        verdict = "tie"
        reason = "pipeline did not beat the direct baseline."
    else:
        verdict = "baseline_better"
        reason = "direct baseline scored higher than the pipeline output."
    return DramaQualityComparison(
        baseline_overall_score=baseline_score,
        pipeline_overall_score=pipeline_score,
        delta=delta,
        verdict=verdict,
        reason=reason,
    )


def _blocking_issue_text(dimension: DramaQualityDimension) -> str:
    issue = f"{dimension.name}: {dimension.suggestion}"
    if dimension.evidence:
        issue += " 证据：" + "；".join(dimension.evidence[:3])
    return issue


def build_drama_quality_report(
    *,
    script_batch: ScriptBatch,
    quality_report: QualityReport | None = None,
    adaptation_quality_report: AdaptationQualityReport | None = None,
    baseline_script_batch: ScriptBatch | None = None,
) -> DramaQualityReport:
    dimensions, warnings = _score_from_metrics(script_batch, quality_report)
    source_asset_dimension = _source_asset_dimension(adaptation_quality_report)
    dimensions.append(source_asset_dimension)
    overall = _overall(dimensions)
    if source_asset_dimension.status == "blocking":
        overall = min(overall, 5 if source_asset_dimension.score <= 2 else 6)
    blocking_issues = dedupe_quality_items([
        _blocking_issue_text(dimension)
        for dimension in dimensions
        if dimension.status == "blocking"
    ])
    advisory_warnings = dedupe_quality_items([
        f"{dimension.name}: {dimension.suggestion}"
        for dimension in dimensions
        if dimension.status == "advisory"
    ])
    if overall < 7 and not blocking_issues:
        advisory_warnings.append("overall drama quality below delivery target")
    comparison = _comparison(
        pipeline_score=overall,
        baseline_script_batch=baseline_script_batch,
    )
    if comparison and comparison.verdict in {"tie", "baseline_better"}:
        blocking_issues.append(
            "pipeline output is not better than the direct LLM baseline"
        )
    elif comparison and comparison.verdict == "pipeline_slightly_better":
        advisory_warnings.append(
            "pipeline output only slightly beats the direct LLM baseline"
        )

    rewrite_parts = dedupe_quality_items([
        issue.replace(": ", "：") for issue in [*blocking_issues, *advisory_warnings]
    ])
    if warnings:
        rewrite_parts.append("本地戏剧质检证据：" + "；".join(warnings[:5]))

    return DramaQualityReport(
        overall_score=overall,
        dimensions=dimensions,
        blocking_issues=blocking_issues,
        advisory_warnings=advisory_warnings,
        rewrite_instruction="；".join(rewrite_parts),
        baseline_comparison=comparison,
    )


def merge_drama_quality_into_report(
    quality_report: QualityReport,
    drama_quality_report: DramaQualityReport,
) -> QualityReport:
    if not drama_quality_report.blocking_issues and drama_quality_report.overall_score >= 7:
        return quality_report
    if not drama_quality_report.blocking_issues:
        return quality_report
    issues = [*quality_report.blocking_issues]
    issues.extend(
        f"drama_quality: {issue}"
        for issue in drama_quality_report.blocking_issues
    )
    if drama_quality_report.overall_score < 7:
        issues.append(
            f"drama_quality overall below target: {drama_quality_report.overall_score}/10"
        )
    rewrite_instruction = merge_rewrite_instructions(
        [
            quality_report.rewrite_instruction,
            drama_quality_report.rewrite_instruction,
        ],
        blocking=True,
    )
    status = quality_report.status
    if status == QualityStatus.USABLE:
        status = QualityStatus.NEEDS_HUMAN_REVIEW
    return quality_report.model_copy(
        update={
            "status": status,
            "blocking_issues": dedupe_quality_items(issues),
            "rewrite_instruction": rewrite_instruction,
        }
    )


def render_drama_quality_report(report: DramaQualityReport) -> str:
    lines = [f"戏剧质量总分：{report.overall_score}/10"]
    if report.baseline_comparison:
        comparison = report.baseline_comparison
        lines.append(
            "Baseline 对照："
            f"pipeline {comparison.pipeline_overall_score}/10 vs "
            f"direct {comparison.baseline_overall_score}/10，"
            f"delta={comparison.delta}，{comparison.verdict}"
        )
    lines.append("")
    for dimension in report.dimensions:
        lines.append(
            f"- {dimension.name}: {dimension.score}/10 {dimension.status}"
        )
        if dimension.evidence:
            lines.append(f"  证据：{'；'.join(dimension.evidence[:3])}")
        if dimension.suggestion:
            lines.append(f"  建议：{dimension.suggestion}")
    if report.blocking_issues:
        lines.append("")
        lines.append("阻断：")
        lines.extend(f"- {item}" for item in report.blocking_issues)
    if report.advisory_warnings:
        lines.append("")
        lines.append("建议关注：")
        lines.extend(f"- {item}" for item in report.advisory_warnings)
    return "\n".join(lines)

```


## File: `src/novel_drama_engine/script_quality.py`
```
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Literal

from novel_drama_engine.models import (
    CrossEpisodeSimilarityIssue,
    CurrentEpisodeRepairPacket,
    EpisodeNoveltyProfile,
    EpisodeScript,
    QualityReport,
    QualityStatus,
    SceneLine,
    ScriptBatch,
    ScriptNoveltyReport,
)
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    merge_rewrite_instructions,
)
from novel_drama_engine.renderer import render_episode

MIN_EPISODE_CHARS = 800
MAX_EPISODE_CHARS = 1700
MIN_SCENES = 2
MAX_SCENES = 5
MIN_TOTAL_SCENE_LINES = 28
MIN_ACTION_LINES = 10
MIN_VOICED_LINES = 18
MIN_SHOT_LANGUAGE_LINES = 8
MIN_STRONG_LINES = 2
MAX_VOICED_LINE_CHARS = 34
SUGGESTED_VOICED_LINE_CHARS = 22
NOVELTY_BLOCKING_SCORE = 0.72
NOVELTY_ADVISORY_SCORE = 0.62
NOVELTY_SCENE_SKELETON_BLOCKING_SCORE = 0.82
NOVELTY_ACTION_BLOCKING_SCORE = 0.76
NOVELTY_DIALOGUE_BLOCKING_SCORE = 0.78
NOVELTY_CLIFFHANGER_BLOCKING_SCORE = 0.78
SCENE_HEADING_RE = re.compile(r"^\d+-\d+\s+(日|夜)-+[内外]-+.+")
ABNORMAL_REPEATED_PHRASE_RE = re.compile(r"([\u4e00-\u9fff]{2,6})\1{2,}")
ABNORMAL_REPEATED_CHAR_RE = re.compile(r"([\u4e00-\u9fff])\1{3,}")
EPISODE_MARKER_RE = re.compile(r"(?:EP\s*\d+|第\s*\d+\s*集|\d+-\d+)", re.IGNORECASE)
SHOT_PREFIX_CLEAN_RE = re.compile(
    r"△?\s*(?:EP\d{2,}\s+)?(?:全景|中景|中近景|近景|特写|俯拍|仰拍|长焦)?"
    r"(?:推近|推移|拉远|拉紧|横移|跟拍|摇向|甩向|反打|切到|扫过|快剪|拉焦|环绕|上移|下移|定格|定镜|慢镜头)?"
)
CHINESE_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")
ACTION_OPENING_BANNED_RE = re.compile(
    r"^△\s*(女主|男主|他|她|门外|突然|众人|大家|甲|乙|丙|丁|温铮|温舟|林晚|林雪|武植|金莲)"
)

CAMERA_TOKENS = (
    "△",
    "特写",
    "镜头",
    "定格",
    "快剪",
    "切",
    "黑屏",
    "上移",
    "下半身",
    "手指",
    "眼神",
)

SHOT_SIZE_TOKENS = (
    "全景",
    "中景",
    "中近景",
    "近景",
    "特写",
    "俯拍",
    "仰拍",
    "长焦",
)

MOVEMENT_TOKENS = (
    "推近",
    "推移",
    "拉远",
    "拉紧",
    "横移",
    "跟拍",
    "摇向",
    "甩向",
    "反打",
    "切到",
    "扫过",
    "快剪",
    "拉焦",
    "环绕",
    "缓慢推向",
    "上移",
    "下移",
    "定格",
    "定镜",
    "慢镜头",
)

FRAMING_TOKENS = (
    "前景",
    "画面",
    "侧脸",
    "下半身",
    "额头",
    "指节",
    "反光",
    "占",
    "左上",
    "右上",
    "门外",
    "门内",
)

SHOT_LINK_TOKENS = (
    "切到",
    "切回",
    "反打",
    "接",
    "视线",
    "声音先入",
    "音效",
    "BGM",
    "道具",
    "前景",
    "J-cut",
)

EXPOSED_ANALYSIS_TOKENS = (
    "3秒 Hook",
    "三秒 Hook",
    "Hook",
    "hook",
    "Hook：",
    "Hook:",
    "hook：",
    "hook:",
    "主情绪",
    "消费理由",
    "main_emotion",
    "watch_reason",
    "hook_3s",
    "观看理由",
    "看点分析",
    "观众要看",
    "观众想看",
    "本集看点",
    "本集钩子",
    "留下悬念",
    "悬念",
    "埋下伏笔",
    "为下一集",
)

ABSTRACT_ACTION_TOKENS = (
    "众人震惊",
    "众人哗然",
    "气氛凝固",
    "场面混乱",
    "开始争吵",
    "很害怕",
    "很紧张",
    "很震惊",
    "很生气",
    "若有所思",
    "眼神复杂",
    "陷入沉思",
    "空气安静",
    "意识到",
    "决定反击",
    "情绪爆发",
)

EXPLANATORY_SUMMARY_TOKENS = (
    "这说明",
    "这就是",
    "这才是",
    "道理",
    "价值观",
    "价值",
    "意义",
    "人生",
    "命运",
    "尊严",
    "真正的",
    "我终于明白",
    "我们应该",
    "你要明白",
    "因为",
    "所以",
)

EXPLANATORY_CLIFFHANGER_TOKENS = (
    "悬念",
    "留下",
    "关于",
    "关系",
    "感到",
    "准备",
    "面对",
    "气氛",
    "达到顶点",
    "似乎",
    "决定",
    "背叛",
    "真实身份",
    "未解",
    "引出",
    "继续",
    "后续",
)

SONG_WORLD_TOKENS = (
    "武植",
    "武大郎",
    "大郎",
    "金莲",
    "潘金莲",
    "西门庆",
    "大宋",
    "清河",
    "武家",
)

URBAN_IDENTITY_TEMPLATE_TOKENS = (
    "真假千金",
    "真千金",
    "假千金",
    "豪门",
    "宴会厅",
    "生日宴",
    "林家",
    "大小姐",
    "顾承",
    "顾少",
    "总裁",
    "亲子鉴定",
    "鉴定编号",
    "董事长",
    "继承权",
)

ENDING_HOOK_PROP_TOKENS = (
    "特写",
    "道具",
    "手机",
    "药碗",
    "木盒",
    "钥匙",
    "玉佩",
    "录音",
    "屏幕",
    "门",
    "剪刀",
    "血",
    "信",
    "鉴定",
    "帘子",
    "刀",
    "碗",
    "锅",
)

STRONG_TOKENS = (
    "！",
    "？",
    "滚",
    "死",
    "毒",
    "杀",
    "跪",
    "闭嘴",
    "放手",
    "马上",
    "立刻",
    "不配",
    "凭什么",
    "游戏才刚刚开始",
    "这只是开始",
    "废物",
    "狗",
    "一起死",
)

HOOK_DIALOGUE_POLISH_WARNING_TOKENS = (
    "too short",
    "voiced lines",
    "verbose voiced lines",
    "shot-to-shot linkage",
    "OS at",
    "cliffhanger is not performed",
    "cliffhanger is too soft",
    "cliffhanger field",
    "explanatory/value-summary",
)

EpisodeRepairMode = Literal[
    "format_patch",
    "ending_hook_patch",
    "creative_episode_repair",
    "full_episode_rewrite",
]

FORMAT_ONLY_WARNING_TOKENS = (
    "action lines violating",
    "abstract action lines",
    "exposes hook/watch_reason",
    "explanatory/value-summary",
    "invalid scene heading",
    "genre template mismatch",
    "abnormal repeated",
)

ENDING_ONLY_WARNING_TOKENS = (
    "cliffhanger",
    "OS at",
    "shot-to-shot linkage",
    "verbose voiced lines",
)

CREATIVE_REPAIR_TOKENS = (
    "ooc",
    "source",
    "fidelity",
    "原文",
    "人设",
    "动机",
    "主动方",
    "因果",
    "证据来源",
    "关键决定",
    "情绪递进",
    "改编一致性",
    "跨集新鲜度",
    "重复",
)


def strict_shooting_quality_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_STRICT_SHOOTING_QUALITY", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on", "strict", "shooting"}


@dataclass(frozen=True)
class EpisodeQualityMetrics:
    chars: int
    scenes: int
    total_scene_lines: int
    action_lines: int
    voiced_lines: int
    os_lines: int
    camera_lines: int
    shot_language_lines: int
    linked_shot_lines: int
    formatted_action_lines: int
    strong_lines: int
    long_voiced_lines: int
    opening_conflict_lines: int
    invalid_scene_headings: int
    invalid_action_format_lines: int
    exposed_analysis_lines: int
    abstract_action_lines: int
    explanatory_voiced_lines: int
    abnormal_repetition_lines: int
    title_in_action_lines: int


def _line_text(line: SceneLine) -> str:
    if line.speaker:
        return f"{line.speaker} {line.emotion or ''} {line.text}"
    return line.text


def has_camera_language(text: str) -> bool:
    return any(token in text for token in CAMERA_TOKENS)


def has_strong_language(text: str) -> bool:
    return any(token in text for token in STRONG_TOKENS)


def has_executable_shot_language(text: str) -> bool:
    has_shot_size = any(token in text for token in SHOT_SIZE_TOKENS)
    has_motion_or_framing = any(token in text for token in MOVEMENT_TOKENS) or any(
        token in text for token in FRAMING_TOKENS
    )
    return has_shot_size and (has_motion_or_framing or len(text) >= 18)


def has_shot_linkage(text: str) -> bool:
    return any(token in text for token in SHOT_LINK_TOKENS)


def has_action_line_template(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith("△"):
        return False
    body = stripped[1:].lstrip()
    body = re.sub(r"^EP\d{2,}\s+", "", body)
    if ACTION_OPENING_BANNED_RE.match("△" + body):
        return False
    starts_with_shot_size = any(body.startswith(token) for token in SHOT_SIZE_TOKENS)
    has_motion = any(token in body for token in MOVEMENT_TOKENS)
    return starts_with_shot_size and has_motion


def has_exposed_analysis(text: str) -> bool:
    if re.search(r"第\s*\d+\s*集", text):
        return True
    return any(token in text for token in EXPOSED_ANALYSIS_TOKENS)


def has_abstract_action(text: str) -> bool:
    return any(token in text for token in ABSTRACT_ACTION_TOKENS)


def has_explanatory_or_value_summary(text: str) -> bool:
    if len(text) <= SUGGESTED_VOICED_LINE_CHARS:
        return False
    return any(token in text for token in EXPLANATORY_SUMMARY_TOKENS)


def has_explanatory_cliffhanger(text: str) -> bool:
    if len(text.strip()) <= SUGGESTED_VOICED_LINE_CHARS and has_strong_language(text):
        return False
    return any(token in text for token in EXPLANATORY_CLIFFHANGER_TOKENS)


def has_cliffhanger_force(text: str) -> bool:
    return (
        has_strong_language(text)
        or has_executable_shot_language(text)
        or any(token in text for token in ENDING_HOOK_PROP_TOKENS)
    )


def has_template_mismatch(text: str) -> bool:
    return any(token in text for token in SONG_WORLD_TOKENS) and any(
        token in text for token in URBAN_IDENTITY_TEMPLATE_TOKENS
    )


def has_abnormal_repetition(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    return bool(
        ABNORMAL_REPEATED_PHRASE_RE.search(normalized)
        or ABNORMAL_REPEATED_CHAR_RE.search(normalized)
    )


def _compact_visible_text(text: str) -> str:
    return "".join(CHINESE_TOKEN_RE.findall(text))


def has_episode_title_leak(text: str, episode_title: str) -> bool:
    compact_title = _compact_visible_text(episode_title)
    if len(compact_title) < 4:
        return False
    return compact_title in _compact_visible_text(text)


def has_shooting_scene_heading(heading: str) -> bool:
    return bool(SCENE_HEADING_RE.match(heading.strip()))


def _episode_visible_text(episode: EpisodeScript) -> str:
    parts: list[str] = [episode.title]
    for scene in episode.scenes:
        parts.append(scene.heading)
        parts.extend(scene.characters)
        parts.extend(_line_text(line) for line in scene.lines)
    return "\n".join(parts)


def has_performed_ending_hook(episode: EpisodeScript) -> bool:
    if not episode.scenes or not episode.scenes[-1].lines:
        return False

    last_two = episode.scenes[-1].lines[-2:]
    if len(last_two) < 2:
        return False
    if any(has_exposed_analysis(_line_text(line)) for line in last_two):
        return False

    has_action_or_prop = any(
        line.kind == "action"
        and (
            has_executable_shot_language(line.text)
            or any(token in line.text for token in ENDING_HOOK_PROP_TOKENS)
        )
        for line in last_two
    )
    has_hook_dialogue = any(
        line.kind in {"dialogue", "os", "vo"} and has_strong_language(_line_text(line))
        for line in last_two
    )
    return has_action_or_prop or has_hook_dialogue


def final_scene_tail_text(episode: EpisodeScript, line_count: int = 4) -> str:
    if not episode.scenes:
        return ""
    lines = episode.scenes[-1].lines[-line_count:]
    return "\n".join(_line_text(line) for line in lines)


def cliffhanger_field_is_performed(episode: EpisodeScript) -> bool:
    cliffhanger = episode.cliffhanger.strip()
    if not cliffhanger:
        return False
    tail_text = final_scene_tail_text(episode)
    if not tail_text:
        return False
    return cliffhanger in tail_text or tail_text in cliffhanger


def episode_quality_metrics(episode: EpisodeScript) -> EpisodeQualityMetrics:
    lines = [line for scene in episode.scenes for line in scene.lines]
    action_lines = [line for line in lines if line.kind == "action"]
    voiced_lines = [line for line in lines if line.kind in {"dialogue", "os", "vo"}]
    os_lines = [line for line in lines if line.kind == "os"]
    camera_lines = [line for line in action_lines if has_camera_language(line.text)]
    shot_language_lines = [
        line for line in action_lines if has_executable_shot_language(line.text)
    ]
    linked_shot_lines = [line for line in action_lines if has_shot_linkage(line.text)]
    formatted_action_lines = [
        line for line in action_lines if has_action_line_template(line.text)
    ]
    strong_lines = [line for line in voiced_lines if has_strong_language(_line_text(line))]
    long_voiced_lines = [
        line for line in voiced_lines if len(line.text) > MAX_VOICED_LINE_CHARS
    ]
    opening_lines = lines[:8]
    opening_conflict_lines = [
        line for line in opening_lines if has_strong_language(_line_text(line))
    ]
    invalid_scene_headings = [
        scene.heading
        for scene in episode.scenes
        if not has_shooting_scene_heading(scene.heading)
    ]
    exposed_analysis_lines = [
        line for line in lines if has_exposed_analysis(_line_text(line))
    ]
    abstract_action_lines = [
        line for line in action_lines if has_abstract_action(line.text)
    ]
    explanatory_voiced_lines = [
        line for line in voiced_lines if has_explanatory_or_value_summary(line.text)
    ]
    abnormal_repetition_lines = [
        line for line in lines if has_abnormal_repetition(_line_text(line))
    ]
    title_in_action_lines = [
        line for line in action_lines if has_episode_title_leak(line.text, episode.title)
    ]

    return EpisodeQualityMetrics(
        chars=len(render_episode(episode)),
        scenes=len(episode.scenes),
        total_scene_lines=len(lines),
        action_lines=len(action_lines),
        voiced_lines=len(voiced_lines),
        os_lines=len(os_lines),
        camera_lines=len(camera_lines),
        shot_language_lines=len(shot_language_lines),
        linked_shot_lines=len(linked_shot_lines),
        formatted_action_lines=len(formatted_action_lines),
        strong_lines=len(strong_lines),
        long_voiced_lines=len(long_voiced_lines),
        opening_conflict_lines=len(opening_conflict_lines),
        invalid_scene_headings=len(invalid_scene_headings),
        invalid_action_format_lines=len(action_lines) - len(formatted_action_lines),
        exposed_analysis_lines=len(exposed_analysis_lines),
        abstract_action_lines=len(abstract_action_lines),
        explanatory_voiced_lines=len(explanatory_voiced_lines),
        abnormal_repetition_lines=len(abnormal_repetition_lines),
        title_in_action_lines=len(title_in_action_lines),
    )


def episode_quality_warnings(
    episode: EpisodeScript,
    *,
    strict_shooting: bool | None = None,
) -> list[str]:
    if strict_shooting is None:
        strict_shooting = strict_shooting_quality_enabled()
    metrics = episode_quality_metrics(episode)
    prefix = f"EP{episode.episode:02d}"
    warnings: list[str] = []
    underfilled_episode = metrics.chars < MIN_EPISODE_CHARS or metrics.scenes < MIN_SCENES

    if metrics.chars < MIN_EPISODE_CHARS:
        warnings.append(
            f"{prefix} too short: {metrics.chars} chars, expected >= {MIN_EPISODE_CHARS}"
        )
    if metrics.chars > MAX_EPISODE_CHARS:
        warnings.append(
            f"{prefix} too long: {metrics.chars} chars, expected <= {MAX_EPISODE_CHARS}"
        )
    if metrics.scenes < MIN_SCENES:
        warnings.append(f"{prefix} has {metrics.scenes} scenes, expected >= {MIN_SCENES}")
    if metrics.scenes > MAX_SCENES:
        warnings.append(f"{prefix} has {metrics.scenes} scenes, expected <= {MAX_SCENES}")
    if strict_shooting and metrics.total_scene_lines < MIN_TOTAL_SCENE_LINES:
        warnings.append(
            f"{prefix} has {metrics.total_scene_lines} visible scene lines, expected >= {MIN_TOTAL_SCENE_LINES}"
        )
    if metrics.invalid_scene_headings:
        invalid_headings = [
            scene.heading
            for scene in episode.scenes
            if not has_shooting_scene_heading(scene.heading)
        ][:3]
        warnings.append(
            f"{prefix} has non-shooting scene headings: {', '.join(invalid_headings)}; expected like 1-1 夜-内-具体地点"
        )
    if (strict_shooting or underfilled_episode) and metrics.action_lines < MIN_ACTION_LINES:
        warnings.append(
            f"{prefix} has {metrics.action_lines} action lines, expected >= {MIN_ACTION_LINES}"
        )
    if (strict_shooting or underfilled_episode) and metrics.voiced_lines < MIN_VOICED_LINES:
        warnings.append(
            f"{prefix} has {metrics.voiced_lines} voiced lines, expected >= {MIN_VOICED_LINES}"
        )
    if strict_shooting and metrics.camera_lines < MIN_ACTION_LINES:
        warnings.append(
            f"{prefix} has weak camera direction density: {metrics.camera_lines}"
        )
    if strict_shooting and metrics.shot_language_lines < MIN_SHOT_LANGUAGE_LINES:
        warnings.append(
            f"{prefix} lacks executable shot language: {metrics.shot_language_lines}, expected >= {MIN_SHOT_LANGUAGE_LINES}"
        )
    if (strict_shooting or underfilled_episode) and metrics.linked_shot_lines < 3:
        warnings.append(
            f"{prefix} lacks shot-to-shot linkage: {metrics.linked_shot_lines}, expected >= 3"
        )
    if strict_shooting and metrics.invalid_action_format_lines:
        warnings.append(
            f"{prefix} has {metrics.invalid_action_format_lines} action lines violating △景别+运镜 opening format"
        )
    if metrics.strong_lines < MIN_STRONG_LINES:
        warnings.append(
            f"{prefix} lacks high-pressure dialogue: {metrics.strong_lines} strong lines"
        )
    if metrics.long_voiced_lines:
        warnings.append(
            f"{prefix} has {metrics.long_voiced_lines} verbose voiced lines, expected <= {MAX_VOICED_LINE_CHARS} chars each"
        )
    if metrics.opening_conflict_lines < 1:
        warnings.append(f"{prefix} opening does not explode in the first 8 beats")
    if metrics.exposed_analysis_lines:
        warnings.append(
            f"{prefix} exposes hook/watch_reason analysis in user-visible script lines"
        )
    if metrics.abstract_action_lines:
        warnings.append(
            f"{prefix} has abstract action lines instead of executable shots: {metrics.abstract_action_lines}"
        )
    if metrics.explanatory_voiced_lines:
        warnings.append(
            f"{prefix} has explanatory/value-summary voiced lines: {metrics.explanatory_voiced_lines}"
        )
    if metrics.abnormal_repetition_lines:
        warnings.append(
            f"{prefix} has abnormal repeated words/phrases in visible lines: {metrics.abnormal_repetition_lines}"
        )
    if metrics.title_in_action_lines:
        warnings.append(
            f"{prefix} repeats episode title in action lines: {metrics.title_in_action_lines}"
        )
    if has_template_mismatch(_episode_visible_text(episode)):
        warnings.append(f"{prefix} has genre template mismatch in user-visible script lines")
    if not has_performed_ending_hook(episode):
        warnings.append(
            f"{prefix} cliffhanger is not performed in the final scene last 2 lines"
        )

    for scene in episode.scenes:
        for index, line in enumerate(scene.lines[:-1]):
            if line.kind == "os" and scene.lines[index + 1].kind != "action":
                warnings.append(f"{prefix} OS at {scene.heading} is not followed by action")

    if not episode.cliffhanger.strip() or not has_cliffhanger_force(episode.cliffhanger):
        warnings.append(f"{prefix} cliffhanger is too soft")
    if has_explanatory_cliffhanger(episode.cliffhanger):
        warnings.append(
            f"{prefix} cliffhanger field is explanatory; use the performed final hook line/action"
        )
    if not cliffhanger_field_is_performed(episode):
        warnings.append(
            f"{prefix} cliffhanger field is not present in the final scene tail"
        )

    return warnings


def episode_repair_mode(
    episode: EpisodeScript,
    base_instruction: str = "",
    *,
    allow_full_rewrite: bool = True,
) -> EpisodeRepairMode:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    warning_text = "\n".join([*warnings, base_instruction]).lower()
    structural_collapse = (
        metrics.chars < 500
        or metrics.scenes < 2
        or metrics.total_scene_lines < 12
        or metrics.action_lines < 4
        or metrics.voiced_lines < 6
    )
    if structural_collapse and allow_full_rewrite:
        return "full_episode_rewrite"

    if any(token in warning_text for token in CREATIVE_REPAIR_TOKENS):
        return "creative_episode_repair"

    if warnings and all(
        any(token in warning for token in FORMAT_ONLY_WARNING_TOKENS)
        for warning in warnings
    ):
        return "format_patch"

    if warnings and all(
        any(token in warning for token in ENDING_ONLY_WARNING_TOKENS)
        for warning in warnings
    ):
        return "ending_hook_patch"

    if any(token in base_instruction for token in ("结尾", "钩子", "断点", "cliffhanger")):
        return "ending_hook_patch"
    if any(token in base_instruction for token in ("格式", "action", "镜头格式", "场景标题")):
        return "format_patch"
    return "creative_episode_repair"


def build_current_episode_repair_packet(
    episode: EpisodeScript,
    base_instruction: str = "",
    *,
    allow_full_rewrite: bool = True,
    source_evidence_targets: list[str] | None = None,
) -> CurrentEpisodeRepairPacket:
    source_evidence_targets = list(dict.fromkeys(source_evidence_targets or []))
    source_contract_repair = bool(source_evidence_targets) or any(
        token in base_instruction
        for token in (
            "source_evidence",
            "原文证据",
            "源文证据",
            "原文偏离",
            "源文偏离",
            "源文相似",
            "source similarity",
            "source_asset_preservation",
            "方法论阻断",
            "强原文轻改失败",
            "C0/C1",
        )
    )
    mode = episode_repair_mode(
        episode,
        base_instruction,
        allow_full_rewrite=allow_full_rewrite,
    )
    if source_contract_repair and mode in {"format_patch", "ending_hook_patch"}:
        mode = "creative_episode_repair"
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    mode_scope = {
        "format_patch": (
            "只修不合格 action 行、场景标题或外露分析字段；其余场景、对白、人物关系、"
            "事件因果、原文资产和结尾钩子照抄当前集旧稿。"
        ),
        "ending_hook_patch": (
            "只修最后一场最后 8-12 行和必要短对白；前文场景、人物动机、证据来源、"
            "主动方和已演出的原文资产照抄当前集旧稿。"
        ),
        "creative_episode_repair": (
            "只修被质检点名的 OOC、原文偏离、情绪递进、冲突因果或跨集承接问题；"
            "已合格场次和 C1 名场面尽量照抄当前集旧稿。"
        ),
        "full_episode_rewrite": (
            "当前集结构崩坏或严重缺量，允许整集重写；仍必须以当前集已出现的人物、"
            "事件意图、原文锚点和上下集边界为基准。"
        ),
    }
    if source_contract_repair:
        mode_scope[mode] = (
            "回到当前集 source packet、source_annotation 和 episode_cut_table 重建本集内容；"
            "只保留旧稿中能被当前集原文契约证明的对白、动作、人物状态和上下集承接。"
        )
    scene_headings = [scene.heading for scene in episode.scenes]
    characters = sorted({character for scene in episode.scenes for character in scene.characters})
    protected_elements = [
        f"title: {episode.title}",
        "scene_headings: " + " / ".join(scene_headings),
        "characters: " + "、".join(characters),
        f"hook_3s: {episode.hook_3s}",
        f"cliffhanger: {episode.cliffhanger}",
    ]
    if episode.state_update:
        protected_elements.append(
            "state_update_keys: " + "、".join(str(key) for key in episode.state_update)
        )
    if source_contract_repair:
        protected_elements = [
            f"episode: {episode.episode}",
            "existing_episode_to_rewrite 仅用于定位失败，不作为剧情边界或资产边界。",
        ]
    editable_targets = [
        *source_evidence_targets,
        *(warnings or [base_instruction.strip() or "未点名具体本地缺口"]),
    ]
    return CurrentEpisodeRepairPacket(
        episode=episode.episode,
        repair_mode=mode,
        baseline_policy=(
            "当前集原文契约是唯一内容基准。旧稿只作为问题定位参考；"
            "必须用当前集 source packet、source_annotation 和 episode_cut_table 覆盖旧稿中无原文依据的场景、动作、台词、道具和因果。"
            if source_contract_repair
            else (
                "当前集旧稿是唯一文本基准。修复只能在 baseline_episode_text 的基础上做最小必要改动；"
                "不得用 episode_plan、source packet 或全局质检意见覆盖当前集已成立的正片内容。"
            )
        ),
        baseline_episode_text=render_episode(episode),
        allowed_change_scope=mode_scope[mode],
        editable_targets=editable_targets,
        source_evidence_targets=source_evidence_targets,
        protected_elements=protected_elements,
        continuity_requirements=[
            (
                "上一集承接只能保留边界动作和情绪余波，不得把上一集事件、道具、台词或真相挪进当前集。"
                if source_contract_repair
                else "保留当前集已演出的事实、人物关系、主动方、关键决定时机和证据来源。"
            ),
            "如果改动最后钩子导致 handoff 变化，只能向后一集追加承接修复，不能回头洗前文。",
            "不得跨集挪用其他 episode_source_packet 的事件、道具或真相揭示。",
        ],
        forbidden_changes=[
            "不得新增无原文依据的新剧情、新道具、新证据或新狠话",
            "不得把预谋改成冲动、把被动承受改成主动索取、把克制人物改成歇斯底里",
            "不得为了补格式或镜头密度增加水对白、空镜、泛场景或新支线",
        ],
    )


def episode_repair_instruction(
    episode: EpisodeScript,
    base_instruction: str = "",
    *,
    allow_full_rewrite: bool = True,
) -> str:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    mode = episode_repair_mode(
        episode,
        base_instruction,
        allow_full_rewrite=allow_full_rewrite,
    )
    missing_chars = max(0, MIN_EPISODE_CHARS - metrics.chars)
    missing_actions = max(0, MIN_ACTION_LINES - metrics.action_lines)
    missing_voiced = max(0, MIN_VOICED_LINES - metrics.voiced_lines)
    missing_shots = max(0, MIN_SHOT_LANGUAGE_LINES - metrics.shot_language_lines)
    missing_links = max(0, 3 - metrics.linked_shot_lines)

    quality_snapshot = (
        "当前本地质检："
        f"{metrics.chars} 字、{metrics.scenes} 场、"
        f"{metrics.action_lines} 条 action、{metrics.voiced_lines} 条对白/OS/VO、"
        f"{metrics.shot_language_lines} 条可执行镜头、"
        f"{metrics.linked_shot_lines} 条镜头衔接。"
    )
    full_rewrite_parts = [
        "修复级别：结构崩坏整集重写。",
        f"第 {episode.episode} 集结构崩坏或严重缺量，允许整集重写；不要摘要复述 existing_episode。",
        quality_snapshot,
        (
            "本次重写硬目标：900-1500 字、优先 3 场、至少 10 条 action、"
            "至少 18 条 dialogue/os/vo、至少 28 条用户可见 scene line、"
            "至少 8 条 action 同时含景别+运镜、"
            "至少 3 条 action 含切到/切回/反打/声音先入/音效/BGM/道具特写/前景。"
        ),
        (
            "action 行硬格式：每条 action.text 必须以“△景别+运镜”开头，例如"
            "“△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节”。"
            "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头。"
        ),
        (
            "必须补足缺口："
            f"至少增加 {missing_chars} 字、{missing_actions} 条 action、"
            f"{missing_voiced} 条对白/OS/VO、{missing_shots} 条可执行镜头、"
            f"{missing_links} 条镜头衔接。"
        ),
        (
            "结构要求：第一场前 8 个 beat 直接爆冲突；中段必须有一次假打脸或期待落空；"
            "最后一场倒数第 2 行必须是 action，且包含景别、运镜、道具/动作和衔接词；"
            "最后一行必须是强对白/强 OS/强 VO 或动作未完成的道具特写。"
        ),
        (
            "镜头写法禁止抽象：不要写“眼神复杂、气氛凝固、若有所思、转身离开”作为钩子；"
            "要写清镜头怎么拍、道具在哪里、角色手/脸/视线如何变化、声音如何切入下一拍。"
        ),
    ]

    focused_parts_by_mode: dict[EpisodeRepairMode, list[str]] = {
        "format_patch": [
            "修复级别：格式局部修复。",
            f"第 {episode.episode} 集只修不合格 action 行、场景标题或外露分析字段；不要整集重写。",
            quality_snapshot,
            (
                "允许改动范围：只改被本地质检点名的行，以及为保持语义连贯必须同步的极少量相邻行。"
                "标题、场景顺序、人物关系、事件因果、原文资产、结尾钩子和已合格对白必须保留。"
            ),
            (
                "格式目标：action 行以“△景别+运镜”开头，补齐构图/道具/表情/声音/切镜衔接；"
                "不要新增无原文依据的新道具、新证据、新狠话。"
            ),
        ],
        "ending_hook_patch": [
            "修复级别：结尾钩子局部修复。",
            f"第 {episode.episode} 集只修最后一场最后 8-12 行和必要短对白；不要整集重写。",
            quality_snapshot,
            f"当前尾部：{final_scene_tail_text(episode, line_count=8)!r}",
            (
                "允许改动范围：保留前文场景、人物动机、证据来源、主动方和已演出的原文资产；"
                "只把结尾停在身份将揭未揭、证据将爆未爆、威胁将落未落或强问题未回答的位置。"
            ),
            (
                "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作；"
                "禁止写说明句，禁止用转身离开、明天再说、黑屏、普通背影收束。"
            ),
        ],
        "creative_episode_repair": [
            "修复级别：单集创作修复。",
            f"第 {episode.episode} 集回到 source packet、Story Bible 和 existing_episode 做定向修复；不要整集洗稿。",
            quality_snapshot,
            (
                "允许改动范围：只修被点名的 OOC、原文偏离、情绪递进、冲突因果或跨集承接问题。"
                "已合格场次、已保留的 C1 名场面、人物关系和结尾边界必须尽量照抄。"
            ),
            (
                "如果原文本身已有强冲突和爆款属性，只做视听化增强和短台词压缩；"
                "不得为了更爽新增改变主动方、动机、关键决定时机或证据来源的剧情。"
            ),
        ],
        "full_episode_rewrite": full_rewrite_parts,
    }
    parts = focused_parts_by_mode[mode]
    if warnings:
        parts.append("本集本地阻断项：\n- " + "\n- ".join(warnings))
    if base_instruction.strip():
        parts.append("全局修复背景（仅供参考，必须优先执行本集修复级别）：\n" + base_instruction.strip())
    return "\n".join(part for part in parts if part)


def episode_needs_hook_dialogue_polish(episode: EpisodeScript) -> bool:
    warnings = episode_quality_warnings(episode)
    return any(
        any(token in warning for token in HOOK_DIALOGUE_POLISH_WARNING_TOKENS)
        for warning in warnings
    )


def hook_dialogue_polish_instruction(
    episode: EpisodeScript,
    base_instruction: str = "",
) -> str:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    missing_chars = max(0, MIN_EPISODE_CHARS - metrics.chars)
    missing_voiced = max(0, MIN_VOICED_LINES - metrics.voiced_lines)
    missing_links = max(0, 3 - metrics.linked_shot_lines)

    parts = [
        (
            f"第 {episode.episode} 集进入结尾钩子/对白密度二次编译。"
            "这是 focused pass，不要整集重写，不要改掉已经合格的场次、人物关系和镜头动作。"
        ),
        (
            "只允许做三类改动："
            "1. 在最后一场或倒数第二场补短对白/OS/VO，使对白密度达标；"
            "2. 修复 OS 后缺少动作承接的问题；"
            "3. 重写最后一场最后 8-12 行，让结尾停在未回答的问题、身份将揭、证据将爆、威胁将落下或动作未完成。"
        ),
        (
            "当前本地质检："
            f"{metrics.chars} 字、{metrics.voiced_lines} 条对白/OS/VO、"
            f"{metrics.linked_shot_lines} 条镜头衔接、cliffhanger={episode.cliffhanger!r}。"
            f"最后尾部={final_scene_tail_text(episode)!r}。"
        ),
        (
            "本次 focused 目标："
            f"至少补 {missing_chars} 字、{missing_voiced} 条短对白/OS/VO、"
            f"{missing_links} 条镜头衔接；最后两行必须形成追更断点。"
        ),
        (
            "结尾禁止：转身离开、我需要时间、明天再说、画面冻结、普通背影、情绪总结、"
            "把秘密说完、把冲突解决完、让角色退场收束。"
        ),
        (
            "结尾必须：倒数第 2 行是 action，且以“△景别+运镜”开头，包含道具/动作和切到/切回/反打/"
            "声音先入/音效/BGM/道具特写/前景之一；最后 1 行是强对白/强 OS/强 VO，"
            "或一个动作未完成的道具特写。"
        ),
        (
            "cliffhanger 字段硬规则：必须直接填写最后 4 行里已经演出来的钩子台词或动作，"
            "例如“这东西，为什么在你手里？”；禁止写“留下悬念/关于真实身份的悬念/气氛紧张”等说明句。"
        ),
        (
            "推荐最后一句模板："
            "“你敢再说一遍？”、“她不是你能碰的人。”、“这东西，为什么在你手里？”、"
            "“你到底是谁？”、“别信她，她会害死你。”"
        ),
        (
            "输出仍必须是完整 EpisodeScript JSON，但除最后 8-12 行和必要短对白补足外，其余内容照抄 existing_episode。"
        ),
    ]
    if warnings:
        parts.append("本集剩余阻断项：\n- " + "\n- ".join(warnings))
    if base_instruction.strip():
        parts.append("全局修复背景（仅供参考，不得覆盖 focused 目标）：\n" + base_instruction.strip())
    return "\n".join(part for part in parts if part)


def _parse_target_episode_range(target_episode_range: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"EP(\d{2,})-EP(\d{2,})", target_episode_range.strip())
    if not match:
        return None
    start_episode = int(match.group(1))
    end_episode = int(match.group(2))
    if end_episode < start_episode:
        return None
    return start_episode, end_episode


def _normalize_for_similarity(text: str) -> str:
    cleaned = SHOT_PREFIX_CLEAN_RE.sub("", text)
    cleaned = EPISODE_MARKER_RE.sub("", cleaned)
    cleaned = re.sub(r"\b\d+\b", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return "".join(CHINESE_TOKEN_RE.findall(cleaned))


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    normalized = _normalize_for_similarity(text)
    if len(normalized) <= n:
        return {normalized} if normalized else set()
    return {normalized[index : index + n] for index in range(len(normalized) - n + 1)}


def _jaccard_similarity(left: str, right: str, *, n: int = 3) -> float:
    left_tokens = _char_ngrams(left, n)
    right_tokens = _char_ngrams(right, n)
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _line_length_bucket(text: str) -> str:
    length = len(_normalize_for_similarity(text))
    if length <= 8:
        return "S"
    if length <= 18:
        return "M"
    if length <= 32:
        return "L"
    return "XL"


def _episode_action_text(episode: EpisodeScript) -> str:
    return "\n".join(
        line.text
        for scene in episode.scenes
        for line in scene.lines
        if line.kind == "action"
    )


def _episode_dialogue_pattern(episode: EpisodeScript) -> str:
    parts: list[str] = []
    for scene in episode.scenes:
        for line in scene.lines:
            if line.kind not in {"dialogue", "os", "vo"}:
                continue
            speaker = line.speaker or ""
            emotion = line.emotion or ""
            parts.append(
                f"{line.kind}:{speaker}:{emotion}:{_line_length_bucket(line.text)}:"
                f"{_normalize_for_similarity(line.text)[:12]}"
            )
    return "|".join(parts)


def _episode_scene_skeleton(episode: EpisodeScript) -> str:
    parts: list[str] = []
    for scene in episode.scenes:
        heading = EPISODE_MARKER_RE.sub("", scene.heading)
        heading = re.sub(r"\s+", "", heading)
        characters = ",".join(sorted(scene.characters))
        line_kinds = "".join(line.kind[0] for line in scene.lines)
        parts.append(f"{heading}:{characters}:{line_kinds}")
    return "|".join(parts)


def _episode_profile(episode: EpisodeScript) -> EpisodeNoveltyProfile:
    return EpisodeNoveltyProfile(
        episode=episode.episode,
        title=episode.title,
        scene_skeleton=_episode_scene_skeleton(episode),
        action_signature=_normalize_for_similarity(_episode_action_text(episode))[:240],
        dialogue_signature=_episode_dialogue_pattern(episode)[:240],
        cliffhanger_signature=_normalize_for_similarity(episode.cliffhanger),
    )


def _issue_text(issue: CrossEpisodeSimilarityIssue) -> str:
    left, right = issue.episodes
    label = {
        "overall": "整体剧情骨架",
        "scene_skeleton": "场景骨架",
        "action_chain": "动作/镜头链",
        "dialogue_pattern": "对白句式",
        "cliffhanger": "结尾钩子",
    }[issue.kind]
    return (
        f"EP{left:02d}/EP{right:02d} {label}重复度过高 "
        f"({issue.score:.2f})"
    )


def _similarity_issue(
    *,
    left: EpisodeScript,
    right: EpisodeScript,
    kind: Literal[
        "overall",
        "scene_skeleton",
        "action_chain",
        "dialogue_pattern",
        "cliffhanger",
    ],
    score: float,
    threshold: float,
    evidence: list[str],
    suggestion: str,
) -> CrossEpisodeSimilarityIssue | None:
    if score < NOVELTY_ADVISORY_SCORE:
        return None
    severity = "blocking" if score >= threshold else "advisory"
    return CrossEpisodeSimilarityIssue(
        episodes=(left.episode, right.episode),
        kind=kind,
        score=round(score, 3),
        severity=severity,
        evidence=evidence,
        suggestion=suggestion,
    )


def build_script_novelty_report(script_batch: ScriptBatch) -> ScriptNoveltyReport:
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)
    profiles = [_episode_profile(episode) for episode in episodes]
    issues: list[CrossEpisodeSimilarityIssue] = []

    for left_index, left in enumerate(episodes):
        for right in episodes[left_index + 1 :]:
            overall_score = _jaccard_similarity(render_episode(left), render_episode(right))
            scene_score = _jaccard_similarity(
                _episode_scene_skeleton(left),
                _episode_scene_skeleton(right),
                n=2,
            )
            action_score = _jaccard_similarity(
                _episode_action_text(left),
                _episode_action_text(right),
            )
            dialogue_score = _jaccard_similarity(
                _episode_dialogue_pattern(left),
                _episode_dialogue_pattern(right),
                n=2,
            )
            cliffhanger_score = _jaccard_similarity(left.cliffhanger, right.cliffhanger)
            maybe_issues = [
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="overall",
                    score=overall_score,
                    threshold=NOVELTY_BLOCKING_SCORE,
                    evidence=[
                        f"EP{left.episode:02d}: {left.title}",
                        f"EP{right.episode:02d}: {right.title}",
                    ],
                    suggestion=(
                        "重写其中一集的核心事件推进：更换冲突场域、施压方、信息增量和结尾问题，"
                        "避免只替换标题/一句台词。"
                    ),
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="scene_skeleton",
                    score=scene_score,
                    threshold=NOVELTY_SCENE_SKELETON_BLOCKING_SCORE,
                    evidence=[
                        _episode_scene_skeleton(left)[:140],
                        _episode_scene_skeleton(right)[:140],
                    ],
                    suggestion="调整场景顺序、地点、入场人物和每场戏的戏剧功能。",
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="action_chain",
                    score=action_score,
                    threshold=NOVELTY_ACTION_BLOCKING_SCORE,
                    evidence=[
                        _episode_action_text(left).split("\n")[0][:120],
                        _episode_action_text(right).split("\n")[0][:120],
                    ],
                    suggestion="重写动作链和关键视觉道具，不要复用同一套镜头模板。",
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="dialogue_pattern",
                    score=dialogue_score,
                    threshold=NOVELTY_DIALOGUE_BLOCKING_SCORE,
                    evidence=[
                        _episode_dialogue_pattern(left)[:140],
                        _episode_dialogue_pattern(right)[:140],
                    ],
                    suggestion="改变施压/反击对白结构，让角色本集诉求和信息增量发生变化。",
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="cliffhanger",
                    score=cliffhanger_score,
                    threshold=NOVELTY_CLIFFHANGER_BLOCKING_SCORE,
                    evidence=[left.cliffhanger, right.cliffhanger],
                    suggestion="结尾钩子要换成新的未回答问题，避免同类证据/同类威胁连续重复。",
                ),
            ]
            issues.extend(issue for issue in maybe_issues if issue is not None)

    blocking_issues = dedupe_quality_items(
        [_issue_text(issue) for issue in issues if issue.severity == "blocking"]
    )
    advisory_warnings = dedupe_quality_items(
        [_issue_text(issue) for issue in issues if issue.severity == "advisory"]
    )
    if blocking_issues:
        score = max(0, 10 - len(blocking_issues) * 2 - len(advisory_warnings))
    elif advisory_warnings:
        score = max(6, 10 - len(advisory_warnings))
    else:
        score = 10

    rewrite_instruction = ""
    if blocking_issues or advisory_warnings:
        repair_targets = sorted(
            {
                episode
                for issue in issues
                for episode in issue.episodes
                if issue.severity == "blocking"
            }
        )
        target_text = (
            "、".join(f"EP{episode:02d}" for episode in repair_targets)
            if repair_targets
            else "相似度最高的集"
        )
        issue_lines = blocking_issues[:8] or advisory_warnings[:8]
        rewrite_instruction = (
            "跨集新鲜度不足，必须按集重写而不是局部替换台词。优先处理 "
            f"{target_text}。\n"
            "修复规则：每集必须有不同的冲突场域、施压动作、信息增量、视觉道具和结尾未回答问题；"
            "禁止复用同一套场景三段式、同一组人物进出场和同一句式反击。\n"
            "检测到的问题：\n- "
            + "\n- ".join(issue_lines)
        )

    return ScriptNoveltyReport(
        overall_score=score,
        episode_profiles=profiles,
        similarity_issues=issues,
        blocking_issues=blocking_issues,
        advisory_warnings=advisory_warnings,
        rewrite_instruction=rewrite_instruction,
    )


def merge_script_novelty_into_quality_report(
    quality_report: QualityReport,
    novelty_report: ScriptNoveltyReport,
) -> QualityReport:
    if not novelty_report.blocking_issues:
        return quality_report
    blocking_issues = dedupe_quality_items(
        [
            *quality_report.blocking_issues,
            *[
                f"script_novelty: {issue}"
                for issue in novelty_report.blocking_issues
            ],
        ]
    )
    return quality_report.model_copy(
        update={
            "status": QualityStatus.NEEDS_REWRITE
            if quality_report.status == QualityStatus.USABLE
            else quality_report.status,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": merge_rewrite_instructions(
                [
                    quality_report.rewrite_instruction,
                    novelty_report.rewrite_instruction,
                ],
                blocking=True,
            ),
        }
    )


def render_script_novelty_report(report: ScriptNoveltyReport) -> str:
    lines = [
        "# Script Novelty Report",
        "",
        f"- Overall score: {report.overall_score}/10",
        f"- Blocking issues: {len(report.blocking_issues)}",
        f"- Advisory warnings: {len(report.advisory_warnings)}",
        "",
        "## Episode Profiles",
        "",
    ]
    for profile in report.episode_profiles:
        lines.append(
            f"- EP{profile.episode:02d} {profile.title}: "
            f"{profile.scene_skeleton[:120]}"
        )
    if report.similarity_issues:
        lines.extend(
            [
                "",
                "## Similarity Issues",
                "",
                "| Episodes | Kind | Score | Severity | Suggestion |",
                "|---|---|---:|---|---|",
            ]
        )
        for issue in report.similarity_issues:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"EP{issue.episodes[0]:02d}/EP{issue.episodes[1]:02d}",
                        issue.kind,
                        f"{issue.score:.2f}",
                        issue.severity,
                        issue.suggestion.replace("|", "/"),
                    ]
                )
                + " |"
            )
    if report.rewrite_instruction:
        lines.extend(["", "## Rewrite Instruction", "", report.rewrite_instruction])
    lines.append("")
    return "\n".join(lines)


def script_batch_quality_warnings(
    script_batch: ScriptBatch,
    target_episode_range: str,
) -> list[str]:
    parsed_range = _parse_target_episode_range(target_episode_range)
    if parsed_range is None:
        return [
            f"target_episode_range is malformed: {target_episode_range}; expected EP01-EP05"
        ]

    start_episode, end_episode = parsed_range
    expected_episodes = list(range(start_episode, end_episode + 1))
    actual_episodes = [episode.episode for episode in script_batch.episodes]
    warnings: list[str] = []

    if actual_episodes != expected_episodes:
        expected_label = ",".join(f"EP{episode:02d}" for episode in expected_episodes)
        actual_label = ",".join(f"EP{episode:02d}" for episode in actual_episodes)
        warnings.append(
            f"script episodes mismatch target range {target_episode_range}: expected {expected_label}, got {actual_label}"
        )

    if len(actual_episodes) != len(set(actual_episodes)):
        warnings.append("script episodes contain duplicate episode numbers")

    return warnings

```


## File: `src/novel_drama_engine/quality_text.py`
```
from __future__ import annotations

import re
from collections.abc import Iterable


POSITIVE_QUALITY_HINTS = (
    "no blocking issues detected",
    "accurately map",
    "accurately maps",
    "key highlights maintained",
    "ensure that when filming",
    "all checks passed",
    "no blocking",
)

EPISODE_RANGE_PATTERNS = (
    re.compile(
        r"\bEP\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(r"第\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*0*(\d{1,3})\s*集"),
)

EPISODE_REF_PATTERNS = (
    re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"第\s*0*(\d{1,3})\s*集"),
)


def _compact_key(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("：", ":").lower()


def _is_positive_advice(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in POSITIVE_QUALITY_HINTS)


def _clean_segment(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^[-*•]\s*", "", text)
    return text.strip("；; ")


def _segments(text: str) -> list[str]:
    parts: list[str] = []
    for line in re.split(r"[\r\n]+", text):
        line = _clean_segment(line)
        if not line:
            continue
        parts.extend(_clean_segment(part) for part in re.split(r"[；;]+", line))
    return [part for part in parts if part]


def dedupe_quality_items(
    items: Iterable[str],
    *,
    drop_positive: bool = True,
) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = _clean_segment(str(item))
        if not item:
            continue
        if drop_positive and _is_positive_advice(item):
            continue
        key = _compact_key(item)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def merge_rewrite_instructions(
    parts: Iterable[str],
    *,
    blocking: bool,
    max_segments: int = 28,
) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not str(part).strip():
            continue
        for segment in _segments(str(part)):
            if blocking and _is_positive_advice(segment):
                continue
            key = _compact_key(segment)
            if key in seen:
                continue
            seen.add(key)
            merged.append(segment)
            if len(merged) >= max_segments:
                return "；".join(merged)
    return "；".join(merged)


def _episode_refs(text: str) -> set[int]:
    refs: set[int] = set()
    for pattern in EPISODE_RANGE_PATTERNS:
        for start_text, end_text in pattern.findall(text):
            start, end = int(start_text), int(end_text)
            if end < start:
                start, end = end, start
            refs.update(range(start, end + 1))
    for pattern in EPISODE_REF_PATTERNS:
        refs.update(int(match) for match in pattern.findall(text))
    return refs


def filter_quality_text_for_episode(text: str, episode_number: int) -> str:
    scoped: list[str] = []
    for segment in _segments(text):
        refs = _episode_refs(segment)
        if refs and episode_number not in refs:
            continue
        scoped.append(segment)
    return merge_rewrite_instructions(scoped, blocking=True)

```


## File: `src/novel_drama_engine/lean_flow.py`
```
from __future__ import annotations

import re

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeCut,
    EpisodeCutTable,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    ProductionSpec,
    SourceAnalysis,
    SourceAnnotation,
    SourceAnnotationEpisode,
    StoryBible,
)


PSYCHOLOGICAL_MARKERS = (
    "僵",
    "震惊",
    "心碎",
    "屈辱",
    "害怕",
    "克制",
    "冷静",
    "决绝",
    "清醒",
    "委屈",
    "愣",
    "眼眶",
    "泪",
)


def _dedupe(items: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(item.strip() for item in items if item.strip())]


def _sentence_snippets(text: str, markers: tuple[str, ...], *, limit: int = 4) -> list[str]:
    snippets: list[str] = []
    for part in re.split(r"(?<=[。！？!?])|\n+", text):
        cleaned = part.strip()
        if cleaned and any(marker in cleaned for marker in markers):
            snippets.append(cleaned[:120])
        if len(snippets) >= limit:
            break
    return _dedupe(snippets)


def _packet_core_conflict(packet: EpisodeSourcePacket, fallback: str) -> str:
    if packet.source_anchor.strip():
        return packet.source_anchor.strip()
    if packet.c1_must_keep_assets:
        return packet.c1_must_keep_assets[0]
    return fallback


def build_production_spec() -> ProductionSpec:
    return ProductionSpec(
        primary_output="creative_script",
        script_priorities=[
            "创作稿先成立：人物动机、冲突因果、情绪递进和对白真实优先。",
            "原文标注稿与本集 source packet 是首稿最高优先级基准。",
            "执行稿信息后移：景别、运镜、BGM 只补足可拍性，不得污染剧情文本。",
        ],
        format_rules=[
            "第X集 + X-X 日/夜-内/外-具体地点 + 人物 + 正片行。",
            "禁止外露 3秒Hook、主情绪、消费理由、观众要看、本集看点。",
        ],
        vo_os_rules=[
            "OS/VO 必须服务动作或选择，下一行要承接可见动作、沉默决定或关系变化。",
            "屏幕字幕类解释优先转为角色 VO/OS 或短对白，不单独写说明性字幕。",
        ],
        dialogue_rules=[
            "台词短、口语、带潜台词，单句只表达一个动作或情绪。",
            "不得把克制人物写成歇斯底里，不得用解释型长句替代戏。",
        ],
        shooting_rules=[
            "动作行必须可拍，含主体、动作、对象和当场后果。",
            "镜头信息只服务情绪和信息，不为了凑格式增加空镜和水动作。",
        ],
        delivery_rules=[
            "首稿产物是 creative_script；通过质检后再派生 shooting_script/export。",
            "源文相似度低于 5/10 时，必须回到 source_annotation 定向修复。",
        ],
    )


def build_source_annotation(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    episode_source_packets: EpisodeSourcePackets,
) -> SourceAnnotation:
    episodes: list[SourceAnnotationEpisode] = []
    for packet in episode_source_packets.packets:
        must_keep_events = _dedupe([*packet.c0_facts, packet.source_anchor])
        must_keep_assets = _dedupe([*packet.c1_must_keep_assets, *(packet.source_evidence_assets or [])])
        psychological_beats = _sentence_snippets(packet.source_excerpt, PSYCHOLOGICAL_MARKERS)
        removable_passages = _dedupe([*packet.c3_compress_assets, *source_analysis.low_value_passages[:3]])
        episodes.append(
            SourceAnnotationEpisode(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                source_excerpt=packet.source_excerpt,
                core_conflict=_packet_core_conflict(packet, story_bible.mainline),
                must_keep_events=must_keep_events,
                must_keep_assets=must_keep_assets,
                must_keep_lines=packet.golden_lines,
                psychological_beats=psychological_beats,
                visual_assets=_dedupe(packet.c2_visual_assets),
                removable_passages=removable_passages,
                forbidden_changes=_dedupe(
                    [*packet.c4_forbidden_additions, *story_bible.forbidden_changes]
                ),
                active_party=packet.active_party,
                key_decision_timing=packet.key_decision_timing,
            )
        )

    return SourceAnnotation(
        north_star="原文标注稿是首稿最高优先级基准",
        global_must_keep=_dedupe(story_bible.immutable_facts),
        global_forbidden_changes=story_bible.forbidden_changes,
        removable_passages=source_analysis.low_value_passages,
        episodes=episodes,
    )


def build_episode_cut_table(
    *,
    episode_context: EpisodeContext,
    episode_source_packets: EpisodeSourcePackets,
) -> EpisodeCutTable:
    cuts: list[EpisodeCut] = []
    for packet in episode_source_packets.packets:
        core_conflict = _packet_core_conflict(packet, packet.source_excerpt[:40])
        cuts.append(
            EpisodeCut(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                core_conflict=core_conflict,
                title_seed=core_conflict[:18],
                ending_hook_seed=packet.handoff_requirement
                or (packet.c1_must_keep_assets[-1] if packet.c1_must_keep_assets else core_conflict),
            )
        )
    return EpisodeCutTable(
        target_episode_range=episode_context.target_episode_range,
        cuts=cuts,
    )

```


## File: `src/novel_drama_engine/llm.py`
```
from __future__ import annotations

from contextlib import contextmanager
import json
import os
import re
import signal
import threading
from typing import Any, Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from novel_drama_engine.models import LLMUsageMetrics

T = TypeVar("T", bound=BaseModel)


class LLMResponseError(RuntimeError):
    pass


class LLMConfigurationError(LLMResponseError):
    pass


class LLMProviderLimitError(LLMResponseError):
    pass


class LLMProviderAuthError(LLMResponseError):
    pass


@contextmanager
def _hard_timeout(seconds: float):
    if (
        seconds <= 0
        or threading.current_thread() is not threading.main_thread()
        or not hasattr(signal, "SIGALRM")
    ):
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def raise_timeout(_signum, _frame):
        raise TimeoutError(f"LLM call timed out after {seconds:g}s")

    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


def _provider_error_label(exc: Exception) -> tuple[type[LLMResponseError], str] | None:
    text = str(exc)
    normalized = text.lower()
    if any(
        token in normalized
        for token in [
            "key limit exceeded",
            "daily limit",
            "insufficient_quota",
            "quota",
            "credit balance",
            "billing hard limit",
            "limit exceeded",
        ]
    ):
        return (
            LLMProviderLimitError,
            "LLM_PROVIDER_LIMIT: provider quota or key daily limit exceeded",
        )
    if any(
        token in normalized
        for token in [
            "invalid api key",
            "unauthorized",
            "401",
            "api key is not set",
            "authentication",
        ]
    ):
        return (
            LLMProviderAuthError,
            "LLM_PROVIDER_AUTH: provider API key is missing or invalid",
        )
    if "rate limit" in normalized or "too many requests" in normalized or "429" in normalized:
        return (
            LLMProviderLimitError,
            "LLM_PROVIDER_RATE_LIMIT: provider rate limit exceeded",
        )
    return None


def _wrap_provider_exception(
    *,
    prefix: str,
    response_model: type[BaseModel],
    exc: Exception,
) -> LLMResponseError:
    classified = _provider_error_label(exc)
    if classified is not None:
        error_type, label = classified
        return error_type(f"{prefix} while generating {response_model.__name__}: {label}. {exc}")
    return LLMResponseError(f"{prefix} while generating {response_model.__name__}: {exc}")


def _decode_json_object_from_text(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as original_exc:
        decoder = json.JSONDecoder()
        for start, char in enumerate(content):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(content[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise original_exc
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("Expected a JSON object", content, 0)
    return parsed


MISSING_MEMBER_COMMA_RE = re.compile(
    r'(?P<value>\]|\}|"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
    r'(?P<space>\s*\n\s*)'
    r'(?P<key>"[^"\n]+":)'
)


def _repair_missing_member_commas(content: str) -> str:
    return MISSING_MEMBER_COMMA_RE.sub(r"\g<value>,\g<space>\g<key>", content)


def _load_json_object_from_text(content: str) -> dict[str, Any]:
    try:
        return _decode_json_object_from_text(content)
    except json.JSONDecodeError as original_exc:
        repaired = _repair_missing_member_commas(content)
        if repaired == content:
            raise original_exc
        try:
            return _decode_json_object_from_text(repaired)
        except json.JSONDecodeError:
            raise original_exc


def _compact_text(value: str, max_chars: int) -> str:
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    head_chars = max_chars // 2
    tail_chars = max_chars - head_chars
    return (
        value[:head_chars]
        + "\n\n...[truncated for JSON repair]...\n\n"
        + value[-tail_chars:]
    )


class JsonLLM(Protocol):
    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        pass


class StaticJsonLLM:
    def __init__(self, outputs: list[BaseModel | dict[str, Any]]) -> None:
        self._outputs = list(outputs)
        self.last_raw_response: dict[str, Any] | None = None

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        if not self._outputs:
            raise LLMResponseError("No static LLM output remains")
        raw = self._outputs.pop(0)
        raw_payload: Any = raw.model_dump(mode="json") if isinstance(raw, BaseModel) else raw
        self.last_raw_response = {
            "provider": "static",
            "response_model": response_model.__name__,
            "content": raw_payload,
        }
        if isinstance(raw, response_model):
            return raw
        return response_model.model_validate(raw)


class OpenAIJsonLLM:
    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if client is None and not api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not set. Use --mock for a local demo run or set OPENAI_API_KEY.",
            )
        base_url = os.environ.get("OPENAI_BASE_URL")
        provider = os.environ.get("NOVEL_DRAMA_LLM_PROVIDER", "").lower()
        timeout = float(os.environ.get("OPENAI_TIMEOUT", "300"))
        self._call_timeout_seconds = float(
            os.environ.get(
                "NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS",
                os.environ.get("OPENAI_TIMEOUT", "300"),
            )
        )
        self._use_chat_json = bool(base_url) or provider in {
            "kimi",
            "moonshot",
            "openai_compatible",
        }
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=timeout,
        )
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-5.5")
        self._max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", "65536"))
        self._chat_validation_retries = max(
            0,
            int(os.environ.get("NOVEL_DRAMA_LLM_VALIDATION_RETRIES", "2")),
        )
        self._repair_snippet_chars = max(
            1000,
            int(os.environ.get("NOVEL_DRAMA_LLM_REPAIR_SNIPPET_CHARS", "60000")),
        )
        self.last_usage: LLMUsageMetrics | None = None
        self.last_raw_response: dict[str, Any] | None = None

    def _record_usage(self, usage: Any) -> None:
        if usage is None:
            self.last_usage = None
            return
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        self.last_usage = LLMUsageMetrics(
            prompt_tokens=prompt_tokens if prompt_tokens is not None else input_tokens,
            completion_tokens=(
                completion_tokens
                if completion_tokens is not None
                else output_tokens
            ),
            total_tokens=total_tokens,
        )

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        self.last_usage = None
        self.last_raw_response = None
        if self._use_chat_json:
            return self._complete_with_chat_json(
                system=system,
                user=user,
                response_model=response_model,
            )

        try:
            with _hard_timeout(self._call_timeout_seconds):
                response = self._client.responses.parse(
                    model=self._model,
                    input=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    text_format=response_model,
                )
        except Exception as exc:
            raise _wrap_provider_exception(
                prefix="OpenAI request failed",
                response_model=response_model,
                exc=exc,
            ) from exc
        self._record_usage(getattr(response, "usage", None))
        response_payload: Any = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else str(response)
        )
        self.last_raw_response = {
            "provider": "responses",
            "model": self._model,
            "response_model": response_model.__name__,
            "response": response_payload,
        }
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise LLMResponseError(
                f"OpenAI returned no parsed output for {response_model.__name__}"
            )
        if not isinstance(parsed, response_model):
            return response_model.model_validate(parsed)
        return parsed

    def _complete_with_chat_json(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        schema = response_model.model_json_schema()
        top_level_keys = ", ".join(schema.get("properties", {}).keys())
        format_instruction = (
            f"Generate one JSON object instance for {response_model.__name__}. "
            "Return raw data JSON only. The response must start with { and end with }. "
            "Do not output the schema itself. Do not wrap the JSON in markdown. "
            "Do not emit multiple JSON objects, explanations, comments, or trailing prose. "
            f"The top-level keys must be: {top_level_keys}. "
            "If the task asks for a wrapper object, do not output a nested item directly. "
            "Do not include schema-only keys such as properties, required, $defs, type, or title "
            "unless they are explicitly part of the requested data. "
            "Use this JSON Schema only as a validation reference:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        base_messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": format_instruction},
            {"role": "user", "content": user},
        ]
        messages = list(base_messages)
        attempts = self._chat_validation_retries + 1
        raw_attempts: list[dict[str, Any]] = []
        for attempt in range(attempts):
            try:
                with _hard_timeout(self._call_timeout_seconds):
                    response = self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        max_tokens=self._max_tokens,
                    )
            except Exception as exc:
                self.last_raw_response = {
                    "provider": "chat.completions",
                    "model": self._model,
                    "response_model": response_model.__name__,
                    "attempts": raw_attempts,
                    "request_error": str(exc),
                }
                raise _wrap_provider_exception(
                    prefix="OpenAI-compatible request failed",
                    response_model=response_model,
                    exc=exc,
                ) from exc
            self._record_usage(getattr(response, "usage", None))

            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            content = choice.message.content
            raw_attempt: dict[str, Any] = {
                "attempt": attempt + 1,
                "finish_reason": finish_reason,
                "content": content,
            }
            usage = getattr(response, "usage", None)
            if usage is not None:
                raw_attempt["usage"] = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }
            raw_attempts.append(raw_attempt)
            self.last_raw_response = {
                "provider": "chat.completions",
                "model": self._model,
                "response_model": response_model.__name__,
                "attempts": raw_attempts,
            }
            if finish_reason == "length":
                raise LLMResponseError(
                    f"OpenAI-compatible response was truncated while generating {response_model.__name__}"
                )
            if not content:
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        f"OpenAI-compatible provider returned no content for {response_model.__name__}"
                    )
                repair_instruction = (
                    "The previous response had no content."
                )
                messages = self._repair_messages(
                    system=system,
                    user=user,
                    response_model=response_model,
                    schema=schema,
                    top_level_keys=top_level_keys,
                    issue=repair_instruction,
                    previous_response="",
                )
                continue
            try:
                parsed = _load_json_object_from_text(content)
            except json.JSONDecodeError as exc:
                raw_attempt["json_error"] = str(exc)
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        f"OpenAI-compatible provider returned invalid JSON for {response_model.__name__}: {exc}",
                    ) from exc
                messages = self._repair_messages(
                    system=system,
                    user=user,
                    response_model=response_model,
                    schema=schema,
                    top_level_keys=top_level_keys,
                    issue=f"The previous response was invalid JSON.\nJSON parse error:\n{exc}",
                    previous_response=content,
                )
                continue
            try:
                result = response_model.model_validate(parsed)
                raw_attempt["validated"] = True
                self.last_raw_response = {
                    "provider": "chat.completions",
                    "model": self._model,
                    "response_model": response_model.__name__,
                    "attempts": raw_attempts,
                    "validated_json": parsed,
                }
                return result
            except ValidationError as exc:
                raw_attempt["validation_error"] = str(exc)
                if attempt >= attempts - 1:
                    raise LLMResponseError(
                        "OpenAI-compatible provider returned JSON that failed "
                        f"schema validation for {response_model.__name__}: {exc}",
                    ) from exc
                messages = self._repair_messages(
                    system=system,
                    user=user,
                    response_model=response_model,
                    schema=schema,
                    top_level_keys=top_level_keys,
                    issue=f"The previous JSON failed validation.\nValidation error:\n{exc}",
                    previous_response=content,
                )
        raise LLMResponseError(
            f"OpenAI-compatible provider failed to generate {response_model.__name__}"
        )

    def _repair_messages(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        schema: dict[str, Any],
        top_level_keys: str,
        issue: str,
        previous_response: str,
    ) -> list[dict[str, str]]:
        original_task = _compact_text(
            f"SYSTEM PROMPT:\n{system}\n\nUSER PROMPT:\n{user}",
            self._repair_snippet_chars,
        )
        previous = _compact_text(previous_response, self._repair_snippet_chars)
        schema_text = json.dumps(schema, ensure_ascii=False)
        return [
            {
                "role": "system",
                "content": (
                    "You are a strict JSON repair worker for an automated production pipeline. "
                    "Return exactly one valid JSON object and nothing else. No markdown. "
                    "No comments. No explanations. Do not output the JSON Schema itself. "
                    "The object must validate against the requested schema. "
                    "If the previous response is the wrong nesting level, rebuild or wrap it "
                    "into the requested top-level object. If required fields are missing, infer "
                    "the smallest faithful value from the original task and previous response."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Requested model: {response_model.__name__}\n"
                    f"Required top-level keys: {top_level_keys}\n\n"
                    f"JSON Schema:\n{schema_text}\n\n"
                    f"Original generation task excerpt:\n{original_task}\n\n"
                    f"Repair issue:\n{issue}\n\n"
                    f"Previous response:\n{previous}\n\n"
                    "Return only the corrected JSON object."
                ),
            },
        ]

```


## File: `src/novel_drama_engine/models.py`
```
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import re

from pydantic import BaseModel, Field, field_validator, model_validator


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


class BatchItemStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationVariant(StrEnum):
    CURRENT_DENSITY = "current_density"
    DRAMA_ENGINE_FIRST = "drama_engine_first"
    SOP_FULL_STACK = "sop_full_stack"


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


class SourceAnalysis(BaseModel):
    characters: list[str]
    events: list[str]
    conflicts: list[str]
    visual_moments: list[str]
    low_value_passages: list[str]
    candidate_hooks: list[str]


class EpisodeSourceMapping(BaseModel):
    source: str
    target_episode: str | int | None = None
    retained_assets: list[str] | str | None = None
    adaptation_reason: str | None = None
    information_increment: str | None = None
    adaptation_action: str | None = None


class EpisodeContext(BaseModel):
    target_episode_range: str
    story_stage: StoryStage
    source_to_episode_mapping: list[EpisodeSourceMapping]
    must_carry_context: list[str]
    forbidden_reveals: list[str]
    adaptation_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("source_to_episode_mapping", mode="before")
    @classmethod
    def normalize_source_mapping(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized: list[object] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"source": item})
            else:
                normalized.append(item)
        return normalized


class StoryBible(BaseModel):
    genre: str
    mainline: str
    characters: list[str]
    relationships: list[str]
    speech_styles: dict[str, str]
    immutable_facts: list[str]
    forbidden_changes: list[str]


class ProductionSpec(BaseModel):
    primary_output: Literal["creative_script", "shooting_script"] = "creative_script"
    script_priorities: list[str] = Field(default_factory=list)
    format_rules: list[str] = Field(default_factory=list)
    vo_os_rules: list[str] = Field(default_factory=list)
    dialogue_rules: list[str] = Field(default_factory=list)
    shooting_rules: list[str] = Field(default_factory=list)
    delivery_rules: list[str] = Field(default_factory=list)


class SourceAnnotationEpisode(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    source_excerpt: str
    core_conflict: str
    must_keep_events: list[str] = Field(default_factory=list)
    must_keep_assets: list[str] = Field(default_factory=list)
    must_keep_lines: list[str] = Field(default_factory=list)
    psychological_beats: list[str] = Field(default_factory=list)
    visual_assets: list[str] = Field(default_factory=list)
    removable_passages: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    active_party: str | None = None
    key_decision_timing: str | None = None


class SourceAnnotation(BaseModel):
    north_star: str
    global_must_keep: list[str] = Field(default_factory=list)
    global_forbidden_changes: list[str] = Field(default_factory=list)
    removable_passages: list[str] = Field(default_factory=list)
    episodes: list[SourceAnnotationEpisode] = Field(default_factory=list)


class EpisodeCut(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    core_conflict: str
    duration_target: str = "60-90s"
    title_seed: str
    ending_hook_seed: str


class EpisodeCutTable(BaseModel):
    target_episode_range: str
    cuts: list[EpisodeCut] = Field(default_factory=list)


class ViralAssetReport(BaseModel):
    channel: str
    genre_tags: list[str]
    core_setting: str
    core_dilemma: str
    protagonist_goal: str
    main_conflict: str
    signature_scenes: list[str] = Field(min_length=3)
    small_highlights: list[str] = Field(min_length=5)
    golden_lines: list[str]
    emotion_curve: list[str] = Field(min_length=3)
    adaptation_risks: list[str]
    risk_treatments: list[str]
    low_value_removal_rules: list[str]


class CharacterProfile(BaseModel):
    name: str
    base_identity: str
    memory_tag: str
    contrast: str
    core_desire: str
    obsession: str
    drama_function: str
    speech_style: str
    sample_lines: list[str] = Field(min_length=1)


class ConflictStack(BaseModel):
    surface_event_conflict: str
    emotional_conflict: str
    deep_value_conflict: str


class SeriesEpisodeOutline(BaseModel):
    episode: int = Field(ge=1)
    core_event: str
    emotion_node: str
    information_increment: str
    ending_hook_type: str
    ending_hook: str
    source_anchor: str
    climax_role: str = "未标注"


class SeriesStructurePlan(BaseModel):
    target_episode_count: int | None = Field(default=None, ge=1)
    target_episode_range: str
    structure_rationale: str
    opening_contract: list[str] = Field(min_length=3)
    small_climax_cadence: str
    big_climax_cadence: str
    character_profiles: list[CharacterProfile]
    conflict_stack: ConflictStack
    global_emotion_curve: list[str] = Field(min_length=3)
    episode_outlines: list[SeriesEpisodeOutline] = Field(min_length=1)
    adaptation_rules: list[str]
    forbidden_slowdowns: list[str]


class EpisodeDramaPlan(BaseModel):
    episode: int = Field(ge=1)
    title: str
    drama_engine: str
    protagonist_misbelief: str
    truth_gap: str
    physical_action_chain: list[str] = Field(min_length=3)
    scene_dynamics: list[str] = Field(min_length=2)
    emotional_turns: list[str] = Field(min_length=2)
    audience_information_gap: str
    three_pull_beats: list[str] = Field(min_length=3)
    false_payoff: str
    planted_key: str
    strongest_line: str
    cliffhanger_design: str
    source_assets_to_keep: list[str]
    forbidden_shortcuts: list[str]


class EpisodePlan(BaseModel):
    variant: GenerationVariant
    target_episode_range: str
    adaptation_strategy: str
    episodes: list[EpisodeDramaPlan] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def wrap_provider_episode_items(cls, data: object) -> object:
        if isinstance(data, list):
            episode_items = data
        elif isinstance(data, dict) and "episodes" not in data and "episode" in data:
            episode_items = [data]
        else:
            return data

        episode_numbers = [
            item.get("episode")
            for item in episode_items
            if isinstance(item, dict) and isinstance(item.get("episode"), int)
        ]
        if not episode_numbers:
            return data
        start = min(episode_numbers)
        end = max(episode_numbers)
        return {
            "variant": GenerationVariant.DRAMA_ENGINE_FIRST.value,
            "target_episode_range": f"EP{start:02d}-EP{end:02d}",
            "adaptation_strategy": (
                "兼容修复：provider 返回了 EpisodeDramaPlan item，"
                "系统按 EpisodePlan 顶层结构包裹。"
            ),
            "episodes": episode_items,
        }


class EpisodeSourcePacket(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    source_excerpt: str
    c0_facts: list[str] = Field(default_factory=list)
    c1_must_keep_assets: list[str] = Field(default_factory=list)
    source_evidence_assets: list[str] | None = None
    c2_visual_assets: list[str] = Field(default_factory=list)
    c3_compress_assets: list[str] = Field(default_factory=list)
    c4_forbidden_additions: list[str] = Field(default_factory=list)
    golden_lines: list[str] = Field(default_factory=list)
    active_party: str | None = None
    key_decision_timing: str | None = None
    handoff_requirement: str | None = None


class EpisodeSourcePackets(BaseModel):
    packets: list[EpisodeSourcePacket] = Field(min_length=1, max_length=5)


class EpisodeHandoff(BaseModel):
    previous_episode: int = Field(ge=1)
    previous_title: str
    previous_cliffhanger: str
    previous_final_lines: list[str] = Field(default_factory=list)
    previous_state_update: dict[str, Any] = Field(default_factory=dict)


SHOT_SIZE_OPENERS = ("全景", "中景", "中近景", "近景", "特写", "俯拍", "仰拍", "长焦")
SHOT_MOTION_OPENERS = (
    "推近",
    "推移",
    "拉远",
    "拉紧",
    "横移",
    "跟拍",
    "摇向",
    "甩向",
    "切到",
    "扫过",
    "快剪",
    "拉焦",
    "环绕",
    "上移",
    "下移",
    "定格",
    "定镜",
    "慢镜头",
)
SHOT_LINK_OPENERS = ("反打", "切到", "切回", "快剪", "拉焦", "摇向", "扫过")


def _episode_action_prefix(body: str) -> tuple[str, str]:
    match = re.match(r"^(EP\d{2,}\s+)(.+)$", body)
    if not match:
        return "", body
    return match.group(1), match.group(2)


def _normalize_action_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    body = stripped[1:].lstrip() if stripped.startswith("△") else stripped
    ep_prefix, body = _episode_action_prefix(body)

    for shot_size in SHOT_SIZE_OPENERS:
        if not body.startswith(shot_size):
            continue
        rest = body[len(shot_size) :]
        if rest.startswith(("，", ",")):
            return f"△{ep_prefix}{shot_size}定镜{rest}"
        if not rest or not any(rest.startswith(motion) for motion in SHOT_MOTION_OPENERS):
            return f"△{ep_prefix}{shot_size}定镜{rest}"
        return f"△{ep_prefix}{body}"

    for opener in SHOT_LINK_OPENERS:
        if body.startswith(opener):
            return f"△{ep_prefix}中近景{body}"

    return f"△{ep_prefix}中近景推近，{body}"


def _speaker_aliases(speaker: str | None) -> list[str]:
    if not speaker:
        return []
    aliases = [speaker.strip()]
    parts = [part for part in re.split(r"\s+", speaker.strip()) if part]
    if parts:
        aliases.append(parts[0])
    return sorted(set(aliases), key=len, reverse=True)


def _strip_voiced_prefix(
    text: str,
    *,
    speaker: str | None,
    kind: str,
    emotion: str | None,
) -> tuple[str, str | None]:
    stripped = text.strip()
    next_emotion = emotion
    kind_marker = "OS|VO" if kind == "dialogue" else kind.upper()

    for alias in _speaker_aliases(speaker):
        pattern = re.compile(
            rf"^\s*{re.escape(alias)}\s*(?:{kind_marker})?\s*"
            rf"(?:[（(](?P<emotion>[^）)]{{1,24}})[）)])?\s*[：:]\s*(?P<body>.+)$",
            re.IGNORECASE,
        )
        match = pattern.match(stripped)
        if match:
            captured_emotion = (match.group("emotion") or "").strip()
            if captured_emotion and not next_emotion:
                next_emotion = captured_emotion
            return match.group("body").strip(), next_emotion

    return stripped, next_emotion


def _strip_parenthetical_speaker_marker(
    text: str,
    *,
    speaker: str | None,
    kind: str,
    emotion: str | None,
) -> tuple[str, str | None]:
    stripped = text.strip()
    next_emotion = emotion
    marker_pattern = "|".join(re.escape(alias) for alias in _speaker_aliases(speaker))
    if marker_pattern:
        stripped = re.sub(
            rf"^\s*[（(]\s*(?:{marker_pattern})\s*(?:{kind.upper()})?\s*[）)]\s*",
            "",
            stripped,
            flags=re.IGNORECASE,
        ).strip()

    match = re.match(r"^\s*[（(](?P<emotion>[^）)]{1,12})[）)]\s*(?P<body>.+)$", stripped)
    if match and not next_emotion:
        next_emotion = match.group("emotion").strip()
        stripped = match.group("body").strip()

    return stripped, next_emotion


def _normalize_voiced_text(
    text: str,
    *,
    speaker: str | None,
    kind: str,
    emotion: str | None,
) -> tuple[str, str | None]:
    stripped, next_emotion = _strip_voiced_prefix(
        text,
        speaker=speaker,
        kind=kind,
        emotion=emotion,
    )
    stripped, next_emotion = _strip_parenthetical_speaker_marker(
        stripped,
        speaker=speaker,
        kind=kind,
        emotion=next_emotion,
    )
    return stripped, next_emotion


CLIFFHANGER_EXPLANATORY_TOKENS = (
    "悬念",
    "留下",
    "关于",
    "关系",
    "气氛",
    "达到顶点",
    "后续",
    "继续",
)
CLIFFHANGER_STRONG_TOKENS = (
    "！",
    "？",
    "滚",
    "死",
    "杀",
    "跪",
    "闭嘴",
    "放手",
    "不配",
    "凭什么",
    "游戏才刚刚开始",
    "这只是开始",
)
CLIFFHANGER_PROP_TOKENS = (
    "手机",
    "屏幕",
    "录音",
    "消息",
    "钥匙",
    "鉴定",
    "心脏",
    "血",
    "门",
    "刀",
)


SCENE_LINE_TEXT_ALIASES = (
    "dialogue",
    "line",
    "content",
    "description",
    "shot",
    "action",
    "voiceover",
    "voice_over",
    "narration",
    "inner_voice",
    "subtitle",
    "visual",
    "camera",
)


def _coerce_scene_line_text(data: dict[str, Any]) -> str:
    text = data.get("text")
    if isinstance(text, str) and text.strip():
        return text
    for key in SCENE_LINE_TEXT_ALIASES:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    kind = data.get("kind")
    if kind == "action":
        return "△中近景定格人物反应，现场声音压低，切到下一拍。"
    if kind == "transition":
        return "切到下一场。"
    return "……"


class SceneLine(BaseModel):
    kind: Literal["action", "dialogue", "os", "vo", "transition"] = Field(
        description=(
            "action 是可拍摄镜头指令，必须写景别、运镜、构图、道具、表情、声音或衔接；"
            "dialogue/os/vo 是短台词，不能承载分析说明。"
        ),
    )
    text: str = Field(
        description=(
            "用户可见正片文本。action 以 △ 开头；对白/OS/VO 单句尽量短，"
            "不得出现 Hook、主情绪、消费理由、观众要看、本集看点等分析字段。"
        ),
    )
    speaker: str | None = Field(default=None, description="对白/OS/VO 的角色名；action 可为空。")
    emotion: str | None = Field(default=None, description="短情绪提示，例如 冷、怒、压低声音。")

    @model_validator(mode="before")
    @classmethod
    def normalize_provider_line_shape(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        return {**data, "text": _coerce_scene_line_text(data)}

    @model_validator(mode="after")
    def normalize_user_visible_text(self) -> "SceneLine":
        if self.kind == "action":
            self.text = _normalize_action_text(self.text)
        elif self.kind in {"dialogue", "os", "vo"}:
            self.text, self.emotion = _normalize_voiced_text(
                self.text,
                speaker=self.speaker,
                kind=self.kind,
                emotion=self.emotion,
            )
        return self


class Scene(BaseModel):
    heading: str = Field(
        description="拍摄场次头，格式为 集数-场次 日/夜-内/外-具体地点，例如 1-1 夜-内-温家走廊。",
    )
    characters: list[str] = Field(description="本场实际出镜或发声角色。")
    lines: list[SceneLine] = Field(
        description="正片分镜和台词。单场不要只站桩对话，要交替出现 action 与短对白。",
    )


def _scene_line_hook_text(line: SceneLine) -> str:
    return line.text.strip()


def _tail_scene_lines(scenes: list[Scene], line_count: int = 4) -> list[SceneLine]:
    if not scenes:
        return []
    return [line for line in scenes[-1].lines[-line_count:] if line.text.strip()]


def _cliffhanger_needs_sync(cliffhanger: str, tail_lines: list[SceneLine]) -> bool:
    stripped = cliffhanger.strip()
    if not stripped:
        return True
    tail_text = "\n".join(_scene_line_hook_text(line) for line in tail_lines)
    if not tail_text:
        return False
    is_performed = stripped in tail_text or tail_text in stripped
    if not is_performed:
        return True
    return any(token in stripped for token in CLIFFHANGER_EXPLANATORY_TOKENS)


def _best_performed_cliffhanger(tail_lines: list[SceneLine]) -> str | None:
    voiced = [line for line in tail_lines if line.kind in {"dialogue", "os", "vo"}]
    for line in reversed(voiced):
        text = _scene_line_hook_text(line)
        if any(token in text for token in CLIFFHANGER_STRONG_TOKENS):
            return text
    for line in reversed(tail_lines):
        text = _scene_line_hook_text(line)
        if line.kind == "action" and any(token in text for token in CLIFFHANGER_PROP_TOKENS):
            return text
    if voiced:
        return _scene_line_hook_text(voiced[-1])
    for line in reversed(tail_lines):
        if line.kind == "action":
            return _scene_line_hook_text(line)
    if tail_lines:
        return _scene_line_hook_text(tail_lines[-1])
    return None


def _raw_scene_line_text(line: object) -> str:
    if isinstance(line, SceneLine):
        return line.text.strip()
    if isinstance(line, dict):
        text = line.get("text")
        if isinstance(text, str):
            return text.strip()
    return ""


def _raw_scene_line_kind(line: object) -> str:
    if isinstance(line, SceneLine):
        return line.kind
    if isinstance(line, dict):
        kind = line.get("kind")
        if isinstance(kind, str):
            return kind
    return ""


def _raw_scene_lines(scenes: object, line_count: int = 4) -> list[object]:
    if not isinstance(scenes, list) or not scenes:
        return []
    last_scene = scenes[-1]
    if isinstance(last_scene, Scene):
        lines: object = last_scene.lines
    elif isinstance(last_scene, dict):
        lines = last_scene.get("lines")
    else:
        return []
    if not isinstance(lines, list):
        return []
    return [line for line in lines[-line_count:] if _raw_scene_line_text(line)]


def _best_raw_performed_cliffhanger(scenes: object) -> str | None:
    tail_lines = _raw_scene_lines(scenes)
    voiced = [
        line
        for line in tail_lines
        if _raw_scene_line_kind(line) in {"dialogue", "os", "vo"}
    ]
    for line in reversed(voiced):
        text = _raw_scene_line_text(line)
        if any(token in text for token in CLIFFHANGER_STRONG_TOKENS):
            return text
    for line in reversed(tail_lines):
        text = _raw_scene_line_text(line)
        if _raw_scene_line_kind(line) == "action" and any(
            token in text for token in CLIFFHANGER_PROP_TOKENS
        ):
            return text
    if voiced:
        return _raw_scene_line_text(voiced[-1])
    for line in reversed(tail_lines):
        if _raw_scene_line_kind(line) == "action":
            return _raw_scene_line_text(line)
    if tail_lines:
        return _raw_scene_line_text(tail_lines[-1])
    return None


class EpisodeScript(BaseModel):
    episode: int = Field(ge=1)
    title: str = Field(description="本集标题，只写冲突事件，不写分析。")
    hook_3s: str = Field(
        description="系统内部字段：前三秒钩子设计。必须在第一场第一组动作/台词里被演出来。",
    )
    main_emotion: str = Field(description="系统内部字段：本集主情绪，不得作为 scene line 输出。")
    watch_reason: str = Field(
        description="系统内部字段：观看理由，不得作为 scene line 输出，不得写成用户可见消费理由。",
    )
    scenes: list[Scene] = Field(
        description=(
            "完整正片脚本，不是摘要。目标 2-5 场，优先 3 场；"
            "整集至少 8 条 action 和 16 条 dialogue/os/vo。"
        ),
    )
    cliffhanger: str = Field(
        description=(
            "系统内部字段：必须直接填写最后一场最后几行里已经演出来的钩子台词或动作。"
            "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
        ),
    )
    state_update: dict[str, Any] = Field(description="本集已经演出的事实、关系、道具和伏笔状态。")

    @model_validator(mode="before")
    @classmethod
    def fill_missing_cliffhanger_from_final_scene(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cliffhanger = data.get("cliffhanger")
        if isinstance(cliffhanger, str) and cliffhanger.strip():
            return data
        performed = _best_raw_performed_cliffhanger(data.get("scenes"))
        if not performed:
            return data
        return {**data, "cliffhanger": performed}

    @model_validator(mode="after")
    def sync_cliffhanger_with_final_scene(self) -> "EpisodeScript":
        tail_lines = _tail_scene_lines(self.scenes)
        if _cliffhanger_needs_sync(self.cliffhanger, tail_lines):
            performed = _best_performed_cliffhanger(tail_lines)
            if performed:
                self.cliffhanger = performed
        return self


class ScriptBatch(BaseModel):
    episodes: list[EpisodeScript] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def wrap_provider_episode_array(cls, data: object) -> object:
        if isinstance(data, list):
            return {"episodes": data}
        return data


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


class DramaQualityDimension(BaseModel):
    name: Literal[
        "character_integrity",
        "conflict_causality",
        "emotional_progression",
        "dialogue_naturalness",
        "source_asset_preservation",
        "hook_and_cliffhanger",
    ]
    score: int = Field(ge=0, le=10)
    status: Literal["passed", "advisory", "blocking"]
    evidence: list[str] = Field(default_factory=list)
    suggestion: str = ""


class DramaQualityComparison(BaseModel):
    baseline_overall_score: int = Field(ge=0, le=10)
    pipeline_overall_score: int = Field(ge=0, le=10)
    delta: int
    verdict: Literal[
        "pipeline_clearly_better",
        "pipeline_slightly_better",
        "tie",
        "baseline_better",
    ]
    reason: str


class DramaQualityReport(BaseModel):
    overall_score: int = Field(ge=0, le=10)
    dimensions: list[DramaQualityDimension] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""
    baseline_comparison: DramaQualityComparison | None = None


class EpisodeNoveltyProfile(BaseModel):
    episode: int = Field(ge=1)
    title: str
    scene_skeleton: str
    action_signature: str
    dialogue_signature: str
    cliffhanger_signature: str


class CrossEpisodeSimilarityIssue(BaseModel):
    episodes: tuple[int, int]
    kind: Literal[
        "overall",
        "scene_skeleton",
        "action_chain",
        "dialogue_pattern",
        "cliffhanger",
    ]
    score: float = Field(ge=0.0, le=1.0)
    severity: Literal["blocking", "advisory"]
    evidence: list[str] = Field(default_factory=list)
    suggestion: str = ""


class ScriptNoveltyReport(BaseModel):
    overall_score: int = Field(ge=0, le=10)
    episode_profiles: list[EpisodeNoveltyProfile] = Field(default_factory=list)
    similarity_issues: list[CrossEpisodeSimilarityIssue] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class SourceEvidenceSpan(BaseModel):
    asset: str
    source_anchor: str
    source_excerpt: str
    source_line: str | None = None
    source_line_index: int | None = Field(default=None, ge=1)
    script_line: str | None = None
    script_line_index: int | None = Field(default=None, ge=1)
    adaptation_reason: str
    status: Literal["matched", "missing"]


class SourceEvidenceItem(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    adaptation_reason: str
    retained_assets: list[str] = Field(default_factory=list)
    script_evidence: list[str] = Field(default_factory=list)
    evidence_spans: list[SourceEvidenceSpan] = Field(default_factory=list)
    status: Literal["matched", "partial", "missing"]


class SourceEvidenceReport(BaseModel):
    coverage_score: int = Field(ge=0, le=100)
    items: list[SourceEvidenceItem] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class CurrentEpisodeRepairPacket(BaseModel):
    episode: int = Field(ge=1)
    repair_mode: Literal[
        "format_patch",
        "ending_hook_patch",
        "creative_episode_repair",
        "full_episode_rewrite",
    ]
    baseline_policy: str
    baseline_episode_text: str
    allowed_change_scope: str
    editable_targets: list[str] = Field(default_factory=list)
    source_evidence_targets: list[str] = Field(default_factory=list)
    protected_elements: list[str] = Field(default_factory=list)
    continuity_requirements: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)


class LLMUsageMetrics(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class LLMCallMetric(BaseModel):
    stage: str
    response_model: str
    duration_ms: int = Field(ge=0)
    status: str
    usage: LLMUsageMetrics | None = None
    error: str | None = None


class PipelineStageMetric(BaseModel):
    name: str
    duration_ms: int = Field(ge=0)
    status: str
    error: str | None = None


class RuntimeReport(BaseModel):
    generation_variant: GenerationVariant
    repair_budget: str
    llm_model: str | None = None
    total_duration_ms: int = Field(ge=0)
    stages: list[PipelineStageMetric] = Field(default_factory=list)
    llm_calls: list[LLMCallMetric] = Field(default_factory=list)
    methodology_cards: list[str] = Field(default_factory=list)

    @property
    def total_llm_calls(self) -> int:
        return len(self.llm_calls)

    @property
    def total_tokens(self) -> int | None:
        values = [
            call.usage.total_tokens
            for call in self.llm_calls
            if call.usage and call.usage.total_tokens is not None
        ]
        if not values:
            return None
        return sum(values)


class NextRoundContext(BaseModel):
    summary: str
    current_episode: int = Field(ge=0)
    open_hooks: list[str]
    forbidden_reveals: list[str]
    character_knowledge: dict[str, list[str]]
    relationship_changes: list[str]
    prop_states: list[str]
    foreshadowing_ledger: list[str]


class SourceFidelityCheck(BaseModel):
    category: Literal[
        "C0_immutable_fact",
        "C1_must_keep_scene",
        "C2_visual_asset",
        "C4_forbidden_addition",
        "hook_preservation",
        "opening_tension_preservation",
        "intent_drift",
        "agency_ramp",
        "support_role_boundary",
        "opponent_agency",
        "character_integrity",
        "source_mapping",
        "source_mapping_required",
        "source_mapping_context",
    ]
    anchor: str
    status: Literal["passed", "advisory", "blocking"]
    episode: int | None = None
    evidence: list[str] = Field(default_factory=list)
    warning: str | None = None


class SourceFidelityReport(BaseModel):
    score: int = Field(ge=0, le=100)
    preserved_original_hook: bool
    checks: list[SourceFidelityCheck] = Field(default_factory=list)
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)


class ContinuityLinkReport(BaseModel):
    previous_episode: int
    next_episode: int
    previous_cliffhanger: str
    next_opening: str
    status: Literal["passed", "advisory", "blocking"]
    warnings: list[str] = Field(default_factory=list)


class ContinuityAuditReport(BaseModel):
    score: int = Field(ge=0, le=100)
    links: list[ContinuityLinkReport] = Field(default_factory=list)
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)


class StoryStateEntry(BaseModel):
    episode: int | None = None
    kind: Literal[
        "open_hook",
        "forbidden_reveal",
        "character_knowledge",
        "relationship_change",
        "prop_state",
        "foreshadowing",
        "episode_state",
        "story_event",
    ]
    key: str
    value: str
    status: Literal["open", "active", "closed", "forbidden"] = "active"
    source: str | None = None


class StoryStateLedger(BaseModel):
    current_episode: int = Field(ge=0)
    entries: list[StoryStateEntry] = Field(default_factory=list)
    open_hooks: list[str] = Field(default_factory=list)
    forbidden_reveals: list[str] = Field(default_factory=list)
    character_knowledge: dict[str, list[str]] = Field(default_factory=dict)
    relationship_changes: list[str] = Field(default_factory=list)
    prop_states: list[str] = Field(default_factory=list)
    foreshadowing_ledger: list[str] = Field(default_factory=list)
    blocking_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdaptationQualityReport(BaseModel):
    source_fidelity: SourceFidelityReport
    continuity: ContinuityAuditReport
    story_state_ledger: StoryStateLedger
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class RoundResult(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    source_analysis: SourceAnalysis
    episode_context: EpisodeContext
    viral_asset_report: ViralAssetReport | None = None
    source_strength_profile: SourceStrengthProfile | None = None
    methodology_context: MethodologyContext | None = None
    story_bible: StoryBible
    production_spec: ProductionSpec | None = None
    source_annotation: SourceAnnotation | None = None
    episode_cut_table: EpisodeCutTable | None = None
    series_structure_plan: SeriesStructurePlan | None = None
    episode_plan: EpisodePlan | None = None
    episode_source_packets: EpisodeSourcePackets | None = None
    script_batch: ScriptBatch
    quality_report: QualityReport
    next_round_context: NextRoundContext
    adaptation_quality_report: AdaptationQualityReport | None = None
    methodology_quality_report: MethodologyQualityReport | None = None
    drama_quality_report: DramaQualityReport | None = None
    script_novelty_report: ScriptNoveltyReport | None = None
    source_evidence_report: SourceEvidenceReport | None = None
    story_state_ledger: StoryStateLedger | None = None
    runtime_report: RuntimeReport | None = None


class BatchManifestItem(BaseModel):
    project_id: str
    input: Path
    context: Path | None = None
    round_number: int | None = Field(default=None, ge=1)


class BatchManifest(BaseModel):
    projects: list[BatchManifestItem] = Field(min_length=1)


class BatchItemResult(BaseModel):
    project_id: str
    status: BatchItemStatus
    project_dir: str
    round_number: int | None = None
    target_episode_range: str | None = None
    quality_status: QualityStatus | None = None
    error: str | None = None


class BatchRunReport(BaseModel):
    items: list[BatchItemResult]

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self.items if item.status == BatchItemStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == BatchItemStatus.FAILED)


class QualitySample(BaseModel):
    sample_id: str
    label: str
    source_text: str


class QualitySampleManifest(BaseModel):
    samples: list[QualitySample] = Field(min_length=1)


QUALITY_SAMPLE_BLOCKING_WARNING_TOKENS = (
    "LLM_PROVIDER_LIMIT",
    "LLM_PROVIDER_AUTH",
    "quality status is",
    "no episodes generated",
    "missing 3s hook",
    "missing cliffhanger",
    "has no scenes",
    "too short",
    "source_fidelity:",
    "未追踪",
    "原文偏离",
    "OOC",
    "全知全能",
    "主动权",
    "证据链",
    "does not hand off",
    "missing from next",
    "forbidden reveal",
)


def quality_sample_warning_is_blocking(warning: str) -> bool:
    normalized_warning = warning.lower()
    return any(
        token.lower() in normalized_warning
        for token in QUALITY_SAMPLE_BLOCKING_WARNING_TOKENS
    )


class QualitySampleRoundReport(BaseModel):
    round_number: int = Field(ge=1)
    generation_variant: GenerationVariant | None = None
    target_episode_range: str | None = None
    quality_status: QualityStatus | None = None
    hook_score: int | None = None
    conflict_score: int | None = None
    cliffhanger_score: int | None = None
    continuity_score: int | None = None
    video_feasibility_score: int | None = None
    source_fidelity_score: int | None = None
    continuity_audit_score: int | None = None
    baseline_overall_score: int | None = None
    pipeline_overall_score: int | None = None
    baseline_delta: int | None = None
    baseline_verdict: Literal[
        "pipeline_clearly_better",
        "pipeline_slightly_better",
        "tie",
        "baseline_better",
    ] | None = None
    baseline_reason: str | None = None
    source_fidelity_warnings: list[str] = Field(default_factory=list)
    continuity_warnings: list[str] = Field(default_factory=list)
    ledger_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        structured_warnings = [
            *self.source_fidelity_warnings,
            *self.continuity_warnings,
            *self.ledger_warnings,
        ]
        return not (
            self.warnings
            or any(quality_sample_warning_is_blocking(warning) for warning in structured_warnings)
        )


class QualitySampleResult(BaseModel):
    sample_id: str
    label: str
    variant: GenerationVariant = GenerationVariant.CURRENT_DENSITY
    project_dir: str
    rounds: list[QualitySampleRoundReport]

    @property
    def passed(self) -> bool:
        return all(round_report.passed for round_report in self.rounds)


class QualitySampleEvaluationReport(BaseModel):
    samples: list[QualitySampleResult]
    variants: list[GenerationVariant] = Field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for sample in self.samples if sample.passed)

    @property
    def failed_count(self) -> int:
        return len(self.samples) - self.passed_count


class VideoShotBrief(BaseModel):
    shot_id: str
    scene_heading: str
    duration_seconds: int = Field(ge=1)
    aspect_ratio: str
    characters: list[str]
    visual_prompt: str
    dialogue_beats: list[str]
    camera_notes: str
    audio_notes: str
    asset_requirements: list[str]


class VideoEpisodeBrief(BaseModel):
    episode: int = Field(ge=1)
    title: str
    aspect_ratio: str
    target_duration_seconds: int = Field(ge=1)
    hook_3s: str
    main_emotion: str
    cliffhanger: str
    shots: list[VideoShotBrief]


class VideoBrief(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    profile: str
    episodes: list[VideoEpisodeBrief]


class LocalizationProfile(BaseModel):
    profile_id: str
    locale: str
    platform: str
    target_language: str
    aspect_ratio: str = "9:16"
    target_duration_seconds: int = Field(default=90, ge=1)
    tone: str = "high-conflict vertical short drama"
    title_prefix: str | None = None
    replacements: dict[str, str] = Field(default_factory=dict)
    forbidden_terms: list[str] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list)
    production_notes: list[str] = Field(default_factory=list)


class LocalizedScene(BaseModel):
    heading: str
    characters: list[str]
    adapted_lines: list[str]


class LocalizedEpisodePackage(BaseModel):
    episode: int = Field(ge=1)
    title: str
    hook_3s: str
    main_emotion: str
    watch_reason: str
    cliffhanger: str
    scenes: list[LocalizedScene]


class LocalizationIssue(BaseModel):
    term: str
    location: str
    text: str


class LocalizationPackage(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    profile: LocalizationProfile
    episodes: list[LocalizedEpisodePackage]
    issues: list[LocalizationIssue]


class LocalizationRewrite(BaseModel):
    episodes: list[LocalizedEpisodePackage]


class DeliveryFile(BaseModel):
    path: str
    bytes: int = Field(ge=0)


class DeliveryManifest(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    quality_status: QualityStatus
    warnings: list[str] = Field(default_factory=list)
    included_files: list[DeliveryFile]


class DeliveryPreflightReport(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    quality_status: QualityStatus
    ready: bool
    warnings: list[str] = Field(default_factory=list)
    files: list[DeliveryFile]

```


## File: `src/lib/engine-runner.ts`
```
import fs from "fs/promises";
import path from "path";
import { spawn } from "child_process";
import { v4 as uuid } from "uuid";
import { and, desc, eq, ne } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { ensureProjectDir, ensureSystemDir, projectDir } from "./storage";
import { writeEpisodeTxt } from "./m6-export";
import { sourceTextWithManualEditContext } from "./manual-edit-context";
import { assertTenantJobQuota } from "./platform-context";
import { llmModelLabel, normalizeLlmModel } from "./llm-model-options";
import {
  latestRoundForProject,
  projectNeedsNextRound,
  projectRunAllSettings,
  updateProjectMeta,
} from "./project-controls";
import {
  createJob,
  failJob,
  classifyJobFailureText,
  listJobViews,
  parseJobPayload,
  succeedJob,
  updateJob,
  type JobRow,
} from "./jobs";
import {
  type DeliveryPreflightReport,
  type EngineEpisode,
  type EngineRoundResult,
  type EngineRuntimeReport,
  type QualitySampleEvaluationPayload,
  type QualityStatus,
  episodeQualityScore,
  qualityToEpisodeStatus,
  renderEngineEpisode,
  renderInternalPlanningMarkdown,
  renderStoryBibleMarkdown,
} from "./engine-types";

type ProjectRow = typeof schema.projects.$inferSelect;

type RoundGenerationPayload = {
  projectId: string;
  roundId: string;
  roundNumber: number;
  generationVariant?: string;
  repairBudget?: string;
  episodesPerRound?: number;
  llmModel?: string;
};

type QualitySamplesPayload = {
  rounds: number;
  variants?: string[];
};

type DeliveryExportPayload = {
  projectId: string;
  roundNumber?: number | null;
  allowIssues?: boolean;
};

type VideoBriefExportPayload = {
  projectId: string;
  roundNumber?: number | null;
};

type LocalizationExportPayload = {
  projectId: string;
  roundNumber?: number | null;
  profilePath: string;
  profileId: string;
};

type QualitySampleManifest = {
  samples?: Array<{
    sample_id?: string;
    label?: string;
  }>;
};

type QualitySampleProgressTarget = {
  sampleId: string;
  label: string;
  variant: string;
  roundNumber: number;
  runtimeReportPath: string;
  roundResultPath: string;
};

type RoundGenerationOptions = {
  generationVariant?: string | null;
  repairBudget?: string | null;
  episodesPerRound?: number | string | null;
  llmModel?: string | null;
  idempotencyKey?: string | null;
};

type RoundQualityGate = {
  status: QualityStatus | null;
  rewriteInstruction: string | null;
};

type RoundCompletionProjectStatusInput = {
  currentEpisode: number | null | undefined;
  targetEpisodeCount: number;
  qualityStatus: QualityStatus;
  roundNumber: number;
  rewriteInstruction?: string | null;
};

type EpisodeSyncTarget = {
  project: ProjectRow;
  roundId: string;
  roundNumber: number;
  status?: "pending" | "running" | "green" | "red" | "failed";
  reviewJson?: string | null;
};

const generationVariants = new Set([
  "current_density",
  "drama_engine_first",
  "sop_full_stack",
]);
const repairBudgets = new Set(["none", "rewrite", "episode"]);
const MAX_EPISODES_PER_ROUND = 5;

function pythonPathEnv(): NodeJS.ProcessEnv {
  const sourcePath = path.join(/*turbopackIgnore: true*/ process.cwd(), "src");
  const existing = process.env.PYTHONPATH;
  return {
    ...process.env,
    PYTHONPATH: existing ? `${sourcePath}${path.delimiter}${existing}` : sourcePath,
    NOVEL_DRAMA_SCRIPT_EPISODE_FIRST:
      process.env.NOVEL_DRAMA_SCRIPT_EPISODE_FIRST ?? "0",
  };
}

function novelDramaCommand(args: string[]): { command: string; args: string[] } {
  const cli = process.env.NOVEL_DRAMA_CLI;
  if (cli) return { command: cli, args };

  const python = process.env.NOVEL_DRAMA_PYTHON ?? process.env.PYTHON ?? "python3";
  return {
    command: python,
    args: ["-m", "novel_drama_engine.cli", ...args],
  };
}

export function isProductionLikeDeployment(): boolean {
  return (
    process.env.NODE_ENV === "production" ||
    process.env.NOVEL_DRAMA_ONLINE_MODE === "1" ||
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET === "production"
  );
}

export function resolveEngineMode(): { mode: "mock" | "real"; explicitMock: boolean } {
  if (process.env.NOVEL_DRAMA_WEB_MOCK === "1") {
    return { mode: "mock", explicitMock: true };
  }
  if (process.env.NOVEL_DRAMA_WEB_MOCK === "0") {
    return { mode: "real", explicitMock: false };
  }
  if (isProductionLikeDeployment()) {
    return { mode: "real", explicitMock: false };
  }
  return { mode: process.env.OPENAI_API_KEY ? "real" : "mock", explicitMock: false };
}

function shouldUseMockEngine(): boolean {
  return resolveEngineMode().mode === "mock";
}

export function realEngineConfigProblem(model?: string | null): string | null {
  if (shouldUseMockEngine()) return null;
  if (!process.env.OPENAI_API_KEY) {
    return "OPENAI_API_KEY is not set while real Engine mode is enabled";
  }
  if (!model && !process.env.OPENAI_MODEL) {
    return "OPENAI_MODEL is not set while real Engine mode is enabled";
  }
  return null;
}

function redactedProviderConfig(): Record<string, unknown> {
  const engineMode = resolveEngineMode();
  let baseUrlHost: string | null = null;
  if (process.env.OPENAI_BASE_URL) {
    try {
      baseUrlHost = new URL(process.env.OPENAI_BASE_URL).host;
    } catch {
      baseUrlHost = "invalid-url";
    }
  }
  return {
    mode: engineMode.mode,
    explicitMock: engineMode.explicitMock,
    provider: process.env.NOVEL_DRAMA_LLM_PROVIDER ?? null,
    model: process.env.OPENAI_MODEL ?? null,
    baseUrlHost,
    hasApiKey: Boolean(process.env.OPENAI_API_KEY),
  };
}

function generationVariant(value?: string | null): string {
  const candidate = value ?? process.env.NOVEL_DRAMA_GENERATION_VARIANT;
  if (candidate && generationVariants.has(candidate)) return candidate;
  return "drama_engine_first";
}

function repairBudget(value?: string | null): string {
  const candidate = value ?? process.env.NOVEL_DRAMA_REPAIR_BUDGET;
  if (candidate && repairBudgets.has(candidate)) return candidate;
  return "episode";
}

function episodesPerRound(value?: number | string | null): number {
  const raw = value ?? process.env.NOVEL_DRAMA_EPISODES_PER_ROUND ?? MAX_EPISODES_PER_ROUND;
  const parsed = typeof raw === "number" ? raw : Number.parseInt(String(raw), 10);
  if (!Number.isFinite(parsed)) return MAX_EPISODES_PER_ROUND;
  return Math.min(MAX_EPISODES_PER_ROUND, Math.max(1, Math.floor(parsed)));
}

function selectedLlmModel(value?: string | null): string {
  return normalizeLlmModel(value, process.env.OPENAI_MODEL);
}

type EngineRunArgsInput = {
  sourcePath: string;
  engineDir: string;
  projectId: string;
  roundNumber: number;
  targetEpisodeCount: number;
  episodesPerRound: number;
  generationVariant: string;
  repairBudget: string;
  llmModel: string;
  methodologyCardsPath?: string | null;
  mock?: boolean;
};

export function buildEngineRunArgs(input: EngineRunArgsInput): string[] {
  const args = [
    "run",
    "--input",
    input.sourcePath,
    "--project-dir",
    input.engineDir,
    "--project-id",
    input.projectId,
    "--round-number",
    String(input.roundNumber),
    "--target-episode-count",
    String(input.targetEpisodeCount),
    "--episodes-per-round",
    String(input.episodesPerRound),
    "--generation-variant",
    input.generationVariant,
    "--repair-budget",
    input.repairBudget,
    "--model",
    input.llmModel,
  ];
  if (input.methodologyCardsPath) {
    args.push("--methodology-cards", input.methodologyCardsPath);
  }
  if (input.mock) args.push("--mock");
  return args;
}

function qualitySampleRepairBudget(): string {
  const candidate = process.env.NOVEL_DRAMA_QUALITY_REPAIR_BUDGET;
  if (candidate && repairBudgets.has(candidate)) return candidate;
  return "rewrite";
}

function normalizeGenerationVariants(values?: string[] | null): string[] {
  const candidates = values?.length ? values : [generationVariant()];
  const normalized = candidates.filter((value) => generationVariants.has(value));
  return Array.from(new Set(normalized.length ? normalized : [generationVariant()]));
}

function engineTimeoutMs(): number {
  const value = Number(process.env.NOVEL_DRAMA_ENGINE_TIMEOUT_MS ?? "1800000");
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 1800000;
}

function qualitySampleTimeoutMs(): number {
  const value = Number(
    process.env.NOVEL_DRAMA_QUALITY_TIMEOUT_MS ??
      process.env.NOVEL_DRAMA_ENGINE_TIMEOUT_MS ??
      "3600000"
  );
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 3600000;
}

async function runNovelDrama(
  args: string[],
  options: { timeoutMs?: number } = {}
): Promise<string> {
  const { command, args: commandArgs } = novelDramaCommand(args);
  return new Promise((resolve, reject) => {
    const timeoutMs = options.timeoutMs ?? engineTimeoutMs();
    let timedOut = false;
    let timeout: NodeJS.Timeout | null = null;
    let forceKill: NodeJS.Timeout | null = null;
    const child = spawn(command, commandArgs, {
      cwd: /*turbopackIgnore: true*/ process.cwd(),
      env: pythonPathEnv(),
    });
    let stdout = "";
    let stderr = "";
    if (timeoutMs > 0) {
      timeout = setTimeout(() => {
        timedOut = true;
        child.kill("SIGTERM");
        forceKill = setTimeout(() => child.kill("SIGKILL"), 5000);
      }, timeoutMs);
    }
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (timeout) clearTimeout(timeout);
      if (forceKill) clearTimeout(forceKill);
      if (timedOut) {
        reject(
          new Error(
            [
              `novel-drama timed out after ${timeoutMs}ms`,
              stdout.trim(),
              stderr.trim(),
            ]
              .filter(Boolean)
              .join("\n")
          )
        );
        return;
      }
      if (code === 0) {
        resolve(stdout);
        return;
      }
      reject(
        new Error(
          [
            `novel-drama exited with code ${code}`,
            stdout.trim(),
            stderr.trim(),
          ]
            .filter(Boolean)
            .join("\n")
        )
      );
    });
  });
}

export function engineProjectDir(projectId: string): string {
  return path.join(/*turbopackIgnore: true*/ projectDir(projectId), "engine");
}

function roundDirName(roundNumber: number): string {
  return `round_${String(roundNumber).padStart(3, "0")}`;
}

async function writeActiveMethodologyCardsForEngine(
  tenantId: string | null,
  engineDir: string
): Promise<{ path: string | null; activeCount: number; totalCount: number }> {
  if (!tenantId) return { path: null, activeCount: 0, totalCount: 0 };

  const tenantCards = await db.query.methodologyCards.findMany({
    where: eq(schema.methodologyCards.tenantId, tenantId),
    orderBy: [desc(schema.methodologyCards.updatedAt)],
  });
  if (tenantCards.length === 0) {
    return { path: null, activeCount: 0, totalCount: 0 };
  }

  const activeCards = tenantCards
    .filter((card) => card.status === "active")
    .map((card) => ({
      id: card.id,
      source_id: card.sourceId,
      name: card.name,
      category: card.category,
      applies_to_channel: JSON.parse(card.appliesToChannelJson) as string[],
      applies_to_genre: JSON.parse(card.appliesToGenreJson) as string[],
      applies_to_stage: JSON.parse(card.appliesToStageJson) as string[],
      trigger: card.trigger,
      generation_rule: card.generationRule,
      quality_rule: card.qualityRule,
      positive_examples: card.positiveExamplesJson
        ? (JSON.parse(card.positiveExamplesJson) as string[])
        : [],
      negative_examples: card.negativeExamplesJson
        ? (JSON.parse(card.negativeExamplesJson) as string[])
        : [],
      status: card.status,
      version: card.version,
    }));
  const cardsPath = path.join(
    /*turbopackIgnore: true*/
    engineDir,
    "active_methodology_cards.json"
  );
  await fs.writeFile(cardsPath, JSON.stringify(activeCards, null, 2), "utf-8");
  return {
    path: cardsPath,
    activeCount: activeCards.length,
    totalCount: tenantCards.length,
  };
}

const engineStageProgress: Record<string, { progress: number; label: string }> = {
  source_analysis: { progress: 42, label: "源文结构解析" },
  viral_asset_report: { progress: 45, label: "爆款资产提炼" },
  episode_context: { progress: 48, label: "自动识别对应集数和上下文" },
  normalize_episode_context: { progress: 50, label: "校准集数范围" },
  story_bible: { progress: 55, label: "系统 Story Bible" },
  series_structure_plan: { progress: 60, label: "全剧结构规划" },
  normalize_series_structure_plan: { progress: 62, label: "校准全剧结构" },
  episode_plan: { progress: 66, label: "分集爆点规划" },
  normalize_episode_plan: { progress: 68, label: "校准分集规划" },
  episode_source_packets: { progress: 70, label: "生成逐集原文包" },
  source_bible_conflicts: { progress: 70, label: "核对 Bible 与原文包" },
  normalize_story_bible_against_source_packets: {
    progress: 70,
    label: "按原文包校准 Bible",
  },
  production_spec: { progress: 71, label: "生成创作规格" },
  source_annotation: { progress: 71, label: "生成原文标注稿" },
  episode_cut_table: { progress: 71, label: "生成分集切割表" },
  methodology_context: { progress: 71, label: "记录方法论辅助卡" },
  sanitize_episode_plan: { progress: 71, label: "按原文包校准分集规划" },
  script_batch: { progress: 72, label: "生成可拍摄脚本" },
  quality_report: { progress: 76, label: "质量门禁自检" },
  script_batch_rewrite: { progress: 78, label: "整轮脚本改写" },
  quality_report_after_rewrite: { progress: 80, label: "改写后复检" },
  episode_repair: { progress: 81, label: "逐集定向修复" },
  apply_episode_repair: { progress: 82, label: "合并逐集修复" },
  episode_quality_polish: { progress: 83, label: "镜头和台词精修" },
  apply_episode_quality_polish: { progress: 84, label: "合并精修版本" },
  hook_dialogue_polish: { progress: 84, label: "开场对白强化" },
  apply_hook_dialogue_polish: { progress: 84, label: "合并开场强化" },
  quality_report_after_episode_repair: { progress: 84, label: "修复后复检" },
  mark_human_review_after_episode_repair: { progress: 84, label: "标记人工复核" },
  mark_human_review_after_rewrite_budget: { progress: 84, label: "标记人工复核" },
  mark_human_review_without_repair: { progress: 84, label: "标记人工复核" },
  next_round_context: { progress: 84, label: "写入下一轮上下文" },
};

async function readRuntimeReport(
  runtimeReportPath: string
): Promise<EngineRuntimeReport | null> {
  try {
    const raw = await fs.readFile(runtimeReportPath, "utf-8");
    return JSON.parse(raw) as EngineRuntimeReport;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return null;
    if (error instanceof SyntaxError) return null;
    throw error;
  }
}

function runtimeStageUpdate(report: EngineRuntimeReport): {
  progress: number;
  label: string;
  status: string;
} | null {
  const call = report.llm_calls.at(-1);
  if (call?.status === "running") {
    const mapped = engineStageProgress[call.stage];
    if (mapped) {
      return {
        progress: mapped.progress,
        label: `${mapped.label} · ${call.response_model} 请求中 ${formatShortDuration(
          call.duration_ms
        )}`,
        status: "running",
      };
    }
  }
  const stage = report.stages.at(-1);
  if (!stage) return null;
  const mapped = engineStageProgress[stage.name];
  if (!mapped) return null;
  return { progress: mapped.progress, label: mapped.label, status: stage.status };
}

function runtimeReportProgress(
  report: EngineRuntimeReport
): { progress: number; message: string } | null {
  const update = runtimeStageUpdate(report);
  if (!update) return null;
  const suffix =
    update.status === "running" ? "" : update.status === "failed" ? "失败" : "完成";
  return {
    progress: update.progress,
    message: `Engine：${update.label}${suffix}`,
  };
}

function runtimeStageFraction(report: EngineRuntimeReport): number {
  const update = runtimeStageUpdate(report);
  if (!update) return 0;
  return Math.max(0, Math.min(1, (update.progress - 35) / (84 - 35)));
}

function safeSampleDirName(sampleId: string): string {
  return sampleId
    .split("")
    .map((character) =>
      /[a-zA-Z0-9_-]/.test(character) ? character : "_"
    )
    .join("");
}

function formatShortDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return "0s";
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m${String(seconds % 60).padStart(2, "0")}s`;
}

async function qualitySampleTargets(
  manifestPath: string,
  projectsDir: string,
  rounds: number,
  variants: string[] = [generationVariant()]
): Promise<QualitySampleProgressTarget[]> {
  const raw = await fs.readFile(manifestPath, "utf-8");
  const manifest = JSON.parse(raw) as QualitySampleManifest;
  const samples = manifest.samples ?? [];
  return samples.flatMap((sample) => variants.flatMap((variant) => {
    const sampleId = sample.sample_id ?? "sample";
    const safeSampleId = safeSampleDirName(sampleId);
    const sampleDir = path.join(
      /*turbopackIgnore: true*/
      projectsDir,
      safeSampleId,
      variants.length > 1 ? variant : ""
    );
    return Array.from({ length: rounds }, (_, index) => {
      const roundNumber = index + 1;
      const roundDir = path.join(
        /*turbopackIgnore: true*/
        sampleDir,
        roundDirName(roundNumber)
      );
      return {
        sampleId,
        label: sample.label ?? sampleId,
        variant,
        roundNumber,
        runtimeReportPath: path.join(roundDir, "runtime_report.json"),
        roundResultPath: path.join(roundDir, "round_result.json"),
      };
    });
  }));
}

async function isFreshFile(filePath: string, freshAfter: Date): Promise<boolean> {
  try {
    const stat = await fs.stat(filePath);
    return stat.mtime >= freshAfter;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return false;
    throw error;
  }
}

async function clearQualitySampleArtifacts(
  targets: QualitySampleProgressTarget[],
  reportPath: string
): Promise<void> {
  await Promise.all([
    fs.rm(reportPath, { force: true }),
    ...targets.map((target) =>
      fs.rm(path.dirname(target.runtimeReportPath), {
        recursive: true,
        force: true,
      })
    ),
  ]);
}

function createQualitySampleProgressSync({
  jobId,
  targets,
  freshAfter,
}: {
  jobId: string;
  targets: QualitySampleProgressTarget[];
  freshAfter: Date;
}): { tick: () => Promise<void>; stop: () => void } {
  let stopped = false;
  let syncing = false;
  let lastProgress = 25;
  let lastMessage = "";

  const tick = async () => {
    if (stopped || syncing || targets.length === 0) return;
    syncing = true;
    try {
      let completed = 0;
      let message = "";
      let progress = lastProgress;

      for (const target of targets) {
        if (await isFreshFile(target.roundResultPath, freshAfter)) {
          completed += 1;
          continue;
        }

        const runtimeReportIsFresh = await isFreshFile(
          target.runtimeReportPath,
          freshAfter
        );
        if (!runtimeReportIsFresh) break;

        const report = await readRuntimeReport(target.runtimeReportPath);
        const stageUpdate = report ? runtimeStageUpdate(report) : null;
        if (!report || !stageUpdate) break;

        const fraction = runtimeStageFraction(report);
        const suffix =
          stageUpdate.status === "running"
            ? ""
            : stageUpdate.status === "failed"
              ? "失败"
              : "完成";
        progress = Math.min(
          92,
          25 + ((completed + fraction) / targets.length) * 67
        );
        message = `内部回归：${target.label} · ${target.variant} R${target.roundNumber} · ${stageUpdate.label}${suffix}`;

        if (stageUpdate.status === "failed") {
          completed += 1;
          continue;
        }
        break;
      }

      if (!message && completed > 0) {
        progress = Math.min(92, 25 + (completed / targets.length) * 67);
        message = `内部回归：已完成 ${completed}/${targets.length} 轮`;
      }
      if (!message) return;

      const roundedProgress = Math.max(lastProgress, Math.round(progress));
      if (roundedProgress === lastProgress && message === lastMessage) return;
      lastProgress = roundedProgress;
      lastMessage = message;
      await updateJob(jobId, { progress: roundedProgress, message });
    } finally {
      syncing = false;
    }
  };

  const timer = setInterval(() => {
    void tick();
  }, 5000);

  return {
    tick,
    stop: () => {
      stopped = true;
      clearInterval(timer);
    },
  };
}

function createEngineProgressSync(
  jobId: string | undefined,
  runtimeReportPath: string,
  episodeSyncTarget?: EpisodeSyncTarget
): { tick: () => Promise<void>; stop: () => void } {
  let stopped = false;
  let syncing = false;
  let lastProgress = 35;
  let lastMessage = "";

  const tick = async () => {
    if (!jobId || stopped || syncing) return;
    syncing = true;
    try {
      const syncedEpisodes = episodeSyncTarget
        ? await syncIncrementalRoundEpisodes(episodeSyncTarget)
        : 0;
      const report = await readRuntimeReport(runtimeReportPath);
      if (!report) {
        if (syncedEpisodes > 0) {
          await updateJob(jobId, {
            progress: lastProgress,
            message: `已生成 ${syncedEpisodes} 集，正在同步到页面`,
          });
        }
        return;
      }
      const update = runtimeReportProgress(report);
      if (!update) {
        if (syncedEpisodes > 0) {
          await updateJob(jobId, {
            progress: lastProgress,
            message: `已同步 ${syncedEpisodes} 集到页面`,
          });
        }
        return;
      }
      const progress = Math.max(lastProgress, update.progress);
      if (progress === lastProgress && update.message === lastMessage) return;
      lastProgress = progress;
      lastMessage = update.message;
      await updateJob(jobId, { progress, message: update.message });
    } finally {
      syncing = false;
    }
  };

  const timer = jobId
    ? setInterval(() => {
        void tick();
      }, 3000)
    : null;

  return {
    tick,
    stop: () => {
      stopped = true;
      if (timer) clearInterval(timer);
    },
  };
}

function qualitySampleReportName(): string {
  return "quality_sample_report.json";
}

function qualitySamplesPath(): string {
  return path.join(
    /*turbopackIgnore: true*/ process.cwd(),
    "examples",
    "quality_samples.json"
  );
}

async function qualityEvaluationDir(tenantId?: string): Promise<string> {
  const root =
    process.env.NOVEL_DRAMA_QUALITY_DIR ?? (await ensureSystemDir("quality_samples"));
  if (!tenantId) return root;
  const dir = path.join(/*turbopackIgnore: true*/ root, "tenants", tenantId);
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

async function readEngineRoundResult(
  projectId: string,
  roundNumber: number
): Promise<EngineRoundResult> {
  const raw = await fs.readFile(
    path.join(
      /*turbopackIgnore: true*/ engineProjectDir(projectId),
      roundDirName(roundNumber),
      "round_result.json"
    ),
    "utf-8"
  );
  return JSON.parse(raw) as EngineRoundResult;
}

function storyBibleChannel(bibleGenre: string): "male" | "female" | null {
  if (/男频|逆袭|赘婿|修仙|战神/.test(bibleGenre)) return "male";
  if (/女频|豪门|千金|追妻|重生/.test(bibleGenre)) return "female";
  return null;
}

function renderRoundEpisodeSummary(episode: EngineEpisode): string {
  return JSON.stringify(
    {
      episode: episode.episode,
      title: episode.title,
      hook_3s: episode.hook_3s,
      cliffhanger: episode.cliffhanger,
      state_update: episode.state_update,
    },
    null,
    2
  );
}

async function upsertEpisodeRow({
  project,
  roundId,
  episode,
  status,
  score,
  reviewJson,
}: {
  project: ProjectRow;
  roundId: string;
  episode: EngineEpisode;
  status: "pending" | "running" | "green" | "red" | "failed";
  score: number | null;
  reviewJson: string | null;
}): Promise<boolean> {
  const now = new Date();
  const scriptTxt = renderEngineEpisode(episode);
  const values = {
    draftMd: renderRoundEpisodeSummary(episode),
    scriptTxt,
    score,
    reviewJson,
    epSummaryJson: JSON.stringify(episode.state_update, null, 2),
    status,
    updatedAt: now,
  };
  const existing = await db.query.episodes.findFirst({
    where: and(
      eq(schema.episodes.projectId, project.id),
      eq(schema.episodes.roundId, roundId),
      eq(schema.episodes.epNum, episode.episode)
    ),
  });

  if (existing) {
    const changed =
      existing.scriptTxt !== scriptTxt ||
      existing.status !== status ||
      existing.score !== score ||
      existing.reviewJson !== reviewJson;
    await db
      .update(schema.episodes)
      .set(values)
      .where(eq(schema.episodes.id, existing.id));
    if (changed) {
      await writeEpisodeTxt(project.id, episode.episode, scriptTxt);
    }
    return changed;
  }

  const crossRoundExisting = await db.query.episodes.findFirst({
    where: and(
      eq(schema.episodes.projectId, project.id),
      eq(schema.episodes.epNum, episode.episode),
      ne(schema.episodes.roundId, roundId)
    ),
  });
  if (crossRoundExisting) {
    throw new Error(
      `episode E${String(episode.episode).padStart(
        2,
        "0"
      )} already exists in another round; refusing to overwrite existing output`
    );
  }

  await db.insert(schema.episodes).values({
    id: uuid(),
    projectId: project.id,
    roundId,
    epNum: episode.episode,
    retryCount: 0,
    ...values,
  });
  await writeEpisodeTxt(project.id, episode.episode, scriptTxt);
  return true;
}

async function syncIncrementalRoundEpisodes({
  project,
  roundId,
  roundNumber,
  status = "running",
  reviewJson = null,
}: EpisodeSyncTarget): Promise<number> {
  const roundDir = path.join(
    /*turbopackIgnore: true*/
    engineProjectDir(project.id),
    roundDirName(roundNumber)
  );
  let files: string[];
  try {
    files = await fs.readdir(roundDir);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return 0;
    throw error;
  }

  let changed = 0;
  for (const file of files.sort()) {
    if (!/^episode_\d{3}\.json$/.test(file)) continue;
    try {
      const raw = await fs.readFile(path.join(roundDir, file), "utf-8");
      const episode = JSON.parse(raw) as EngineEpisode;
      if (!Number.isFinite(episode.episode) || !episode.scenes) continue;
      const didChange = await upsertEpisodeRow({
        project,
        roundId,
        episode,
        status,
        score: null,
        reviewJson,
      });
      if (didChange) changed += 1;
    } catch (error) {
      if (error instanceof SyntaxError) continue;
      throw error;
    }
  }
  return changed;
}

async function syncBible(projectId: string, result: EngineRoundResult): Promise<void> {
  const existing = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, projectId),
  });
  const values = {
    channel: storyBibleChannel(result.story_bible.genre),
    sixAssetsJson: JSON.stringify(result.story_bible, null, 2),
    charactersMd: renderStoryBibleMarkdown(result.story_bible),
    episodePlanMd: renderInternalPlanningMarkdown(result),
    prevRoundSummaryJson: JSON.stringify(result.next_round_context, null, 2),
    updatedAt: new Date(),
  };

  if (existing) {
    await db
      .update(schema.bibles)
      .set(values)
      .where(eq(schema.bibles.projectId, projectId));
    return;
  }

  await db.insert(schema.bibles).values({
    id: uuid(),
    projectId,
    ...values,
  });
}

async function syncMethodologyRun(
  project: ProjectRow,
  roundId: string,
  result: EngineRoundResult
): Promise<void> {
  if (
    !result.source_strength_profile &&
    !result.methodology_context &&
    !result.methodology_quality_report
  ) {
    return;
  }

  await db
    .delete(schema.methodologyRuns)
    .where(eq(schema.methodologyRuns.roundId, roundId));

  await db.insert(schema.methodologyRuns).values({
    id: uuid(),
    tenantId: project.tenantId,
    projectId: project.id,
    roundId,
    sourceStrengthJson: result.source_strength_profile
      ? JSON.stringify(result.source_strength_profile, null, 2)
      : null,
    methodologyContextJson: result.methodology_context
      ? JSON.stringify(result.methodology_context, null, 2)
      : null,
    methodologyQualityJson: result.methodology_quality_report
      ? JSON.stringify(result.methodology_quality_report, null, 2)
      : null,
    createdAt: new Date(),
  });
}

async function syncEngineRoundToDb(
  project: ProjectRow,
  roundId: string,
  result: EngineRoundResult
): Promise<void> {
  await syncBible(project.id, result);
  await syncMethodologyRun(project, roundId, result);

  const status = qualityToEpisodeStatus(result.quality_report.status);
  const finalEpisodeNumbers = new Set(
    result.script_batch.episodes.map((episode) => episode.episode)
  );
  const existingRows = await db.query.episodes.findMany({
    where: eq(schema.episodes.roundId, roundId),
  });
  await Promise.all(
    existingRows
      .filter((episode) => !finalEpisodeNumbers.has(episode.epNum))
      .map((episode) =>
        db.delete(schema.episodes).where(eq(schema.episodes.id, episode.id))
      )
  );

  for (const episode of result.script_batch.episodes) {
    await upsertEpisodeRow({
      project,
      roundId,
      episode,
      status,
      score: episodeQualityScore(result, episode.episode),
      reviewJson: JSON.stringify(result.quality_report, null, 2),
    });
  }

  await db
    .update(schema.rounds)
    .set({
      epRange: result.episode_context.target_episode_range,
      summaryJson: JSON.stringify(result, null, 2),
      status: "done",
    })
    .where(eq(schema.rounds.id, roundId));
  await reconcileRoundStatusFromEpisodes(roundId);

  await markProjectAfterRoundCompletion(project.id, {
    currentEpisode: result.next_round_context.current_episode,
    targetEpisodeCount: project.targetEpisodeCount,
    qualityStatus: result.quality_report.status,
    roundNumber: result.round_number,
    rewriteInstruction: result.quality_report.rewrite_instruction,
  });
}

export async function reconcileRoundStatusFromEpisodes(roundId: string): Promise<void> {
  const episodes = await db.query.episodes.findMany({
    where: eq(schema.episodes.roundId, roundId),
  });
  if (episodes.length === 0) return;

  const status = episodes.some(
    (episode) => episode.status === "failed" || episode.status === "red"
  )
    ? "failed"
    : episodes.some(
          (episode) => episode.status === "pending" || episode.status === "running"
        )
      ? "running"
      : "done";

  await db
    .update(schema.rounds)
    .set({ status })
    .where(eq(schema.rounds.id, roundId));
}

export async function markProjectAfterRoundCompletion(
  projectId: string,
  input: RoundCompletionProjectStatusInput
): Promise<void> {
  const latestProject = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!latestProject) throw new Error("project not found");
  if (latestProject.status === "paused") return;

  const now = new Date();
  const targetReached =
    typeof input.currentEpisode === "number" &&
    input.currentEpisode >= input.targetEpisodeCount;
  if (input.qualityStatus !== "usable") {
    const pausedAt = now.toISOString();
    await updateProjectMeta(projectId, (meta) => ({
      ...meta,
      control: {
        ...(meta.control ?? {}),
        qualityGate: {
          status: input.qualityStatus,
          round: input.roundNumber,
          pausedAt,
          rewriteInstruction: input.rewriteInstruction ?? null,
        },
      },
    }));
    await db
      .update(schema.projects)
      .set({ status: "failed", updatedAt: now })
      .where(eq(schema.projects.id, projectId));
    return;
  }

  await updateProjectMeta(projectId, (meta) => {
    const control = { ...(meta.control ?? {}) };
    delete (control as Record<string, unknown>).qualityGate;
    return { ...meta, control };
  });
  await db
    .update(schema.projects)
    .set({ status: targetReached ? "done" : "running", updatedAt: now })
    .where(eq(schema.projects.id, projectId));
}

async function executeEngineRound(
  project: ProjectRow,
  roundNumber: number,
  roundId: string,
  jobId?: string,
  options: RoundGenerationOptions = {}
): Promise<void> {
  try {
    const selectedGenerationVariant = generationVariant(options.generationVariant);
    const selectedRepairBudget = repairBudget(options.repairBudget);
    const selectedEpisodesPerRound = episodesPerRound(options.episodesPerRound);
    const selectedModel = selectedLlmModel(options.llmModel);
    const configProblem = realEngineConfigProblem(selectedModel);
    if (configProblem) throw new Error(configProblem);
    await updateJob(jobId, {
      message: `准备小说原文和 Engine 工作目录 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集 · ${llmModelLabel(selectedModel)}`,
      progress: 15,
    });
    const storageDir = await ensureProjectDir(project.id);
    const engineDir = path.join(/*turbopackIgnore: true*/ storageDir, "engine");
    await fs.mkdir(engineDir, { recursive: true });
    const methodologyCards = await writeActiveMethodologyCardsForEngine(
      project.tenantId,
      engineDir
    );
    const runtimeReportPath = path.join(
      /*turbopackIgnore: true*/
      engineDir,
      roundDirName(roundNumber),
      "runtime_report.json"
    );
    await fs.rm(runtimeReportPath, { force: true });
    const sourcePath = path.join(
      /*turbopackIgnore: true*/
      engineDir,
      `source_round_${String(roundNumber).padStart(3, "0")}.txt`
    );
    await fs.writeFile(
      sourcePath,
      sourceTextWithManualEditContext(project.novelText, project.metaJson),
      "utf-8"
    );

    const args = buildEngineRunArgs({
      sourcePath,
      engineDir,
      projectId: project.id,
      roundNumber,
      targetEpisodeCount: project.targetEpisodeCount,
      episodesPerRound: selectedEpisodesPerRound,
      generationVariant: selectedGenerationVariant,
      repairBudget: selectedRepairBudget,
      llmModel: selectedModel,
      methodologyCardsPath: methodologyCards.path,
      mock: shouldUseMockEngine(),
    });

    await updateJob(jobId, {
      message:
        methodologyCards.path && methodologyCards.totalCount > 0
          ? `调用 Engine 生成轮次脚本 · ${llmModelLabel(selectedModel)} · active 方法卡 ${methodologyCards.activeCount}/${methodologyCards.totalCount}`
          : `调用 Engine 生成轮次脚本 · ${llmModelLabel(selectedModel)}`,
      progress: 35,
    });
    const progressSync = createEngineProgressSync(jobId, runtimeReportPath, {
      project,
      roundId,
      roundNumber,
    });
    try {
      await runNovelDrama(args);
    } finally {
      await progressSync.tick();
      progressSync.stop();
    }
    await updateJob(jobId, {
      message: "同步 Engine artifacts 到 Web 数据库",
      progress: 85,
    });
    const result = await readEngineRoundResult(project.id, roundNumber);
    await syncEngineRoundToDb(project, roundId, result);
    const completionResult = {
      projectId: project.id,
      roundId,
      roundNumber,
      targetEpisodeRange: result.episode_context.target_episode_range,
      qualityStatus: result.quality_report.status,
      generationVariant: selectedGenerationVariant,
      repairBudget: selectedRepairBudget,
      episodesPerRound: selectedEpisodesPerRound,
      llmModel: selectedModel,
      runtimeMs: result.runtime_report?.total_duration_ms,
      llmCalls: result.runtime_report?.llm_calls.length,
      sourceStrength: result.source_strength_profile?.overall_level ?? null,
      adaptationIntensity:
        result.source_strength_profile?.recommended_intensity ?? null,
      methodologyCards:
        result.methodology_context?.cards?.map((card) => card.name) ?? [],
      nextJobId: null as string | null,
      nextRoundScheduleError: null as string | null,
    };
    if (result.quality_report.status !== "usable") {
      await failJob(jobId, new Error(result.quality_report.rewrite_instruction), {
        message: "质量门禁未通过",
        errorText:
          result.quality_report.rewrite_instruction ||
          `final quality status: ${result.quality_report.status}`,
        result: {
          ...completionResult,
          failureCategory: "engine_error",
          operatorHint:
            "red/needs_rewrite 剧本不会作为成功任务交付；请使用重试或单集修复后再继续。",
        },
      });
      return;
    }
    await succeedJob(jobId, {
      message: `第 ${roundNumber} 轮完成`,
      result: completionResult,
    });
    try {
      const nextJob = await scheduleNextRoundIfRunAll(project.id);
      if (nextJob) {
        completionResult.nextJobId = nextJob.jobId;
        await updateJob(jobId, { result: completionResult });
      }
    } catch (scheduleError) {
      const scheduleMessage =
        scheduleError instanceof Error ? scheduleError.message : String(scheduleError);
      completionResult.nextRoundScheduleError = scheduleMessage;
      await updateJob(jobId, {
        message: `第 ${roundNumber} 轮完成；下一轮调度失败`,
        result: completionResult,
      });
      console.error("[engine-runner] next round schedule failed:", scheduleError);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const failure = classifyJobFailureText(message);
    const userError = failure
      ? `${failure.userMessage}。${failure.operatorHint}`
      : message;
    let partialEpisodes = 0;
    try {
      partialEpisodes = await syncIncrementalRoundEpisodes({
        project,
        roundId,
        roundNumber,
        status: "red",
        reviewJson: JSON.stringify(
          {
            status: "failed",
            error: userError,
            failureCategory: failure?.category ?? "engine_error",
          },
          null,
          2
        ),
      });
    } catch (syncError) {
      console.error("[engine-runner] partial episode sync failed:", syncError);
    }
    const failureSummary = {
      error: userError,
      rawError: message.slice(0, 4000),
      failureCategory: failure?.category ?? "engine_error",
      operatorHint:
        failure?.operatorHint ??
        "查看错误详情后重试；若连续失败，需要检查 prompt、模型或输入文本。",
      partialEpisodes,
      provider: redactedProviderConfig(),
    };
    await db
      .update(schema.rounds)
      .set({
        status: "failed",
        summaryJson: JSON.stringify(failureSummary, null, 2),
      })
      .where(eq(schema.rounds.id, roundId));
    await db
      .update(schema.projects)
      .set({ status: "failed", updatedAt: new Date() })
      .where(eq(schema.projects.id, project.id));
    await failJob(jobId, error, {
      message: failure?.userMessage ?? "生成失败",
      errorText: userError,
      result: failureSummary,
    });
    console.error("[engine-runner] failed:", error);
  }
}

export async function executeEngineRoundJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<RoundGenerationPayload>(job);
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, payload.projectId),
  });
  if (!project) throw new Error("project not found");
  await executeEngineRound(project, payload.roundNumber, payload.roundId, job.id, {
    generationVariant: payload.generationVariant,
    repairBudget: payload.repairBudget,
    episodesPerRound: payload.episodesPerRound,
    llmModel: payload.llmModel,
  });
}

export async function startEngineRound(
  projectId: string,
  roundNumber: number,
  options: RoundGenerationOptions = {}
): Promise<{ roundId: string; roundNum: number; jobId: string }> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  if (project.status === "paused") throw new Error("project is paused");
  if (project.tenantId) await assertTenantJobQuota(project.tenantId);

  const existing = await db.query.rounds.findFirst({
    where: and(
      eq(schema.rounds.projectId, projectId),
      eq(schema.rounds.roundNum, roundNumber)
    ),
  });

  const roundId = existing?.id ?? uuid();
  if (existing) {
    await db
      .update(schema.rounds)
      .set({ status: "running" })
      .where(eq(schema.rounds.id, roundId));
  } else {
    await db.insert(schema.rounds).values({
      id: roundId,
      projectId,
      roundNum: roundNumber,
      epRange: `Round ${roundNumber}`,
      summaryJson: null,
      status: "running",
      createdAt: new Date(),
    });
  }

  await db
    .update(schema.projects)
    .set({ status: "running", updatedAt: new Date() })
    .where(eq(schema.projects.id, projectId));

  const selectedGenerationVariant = generationVariant(options.generationVariant);
  const selectedRepairBudget = repairBudget(options.repairBudget);
  const selectedEpisodesPerRound = episodesPerRound(options.episodesPerRound);
  const selectedModel = selectedLlmModel(options.llmModel);
  const job = await createJob({
    kind: "round_generation",
    title: `${project.name} · 第 ${roundNumber} 轮 · ${selectedEpisodesPerRound}集`,
    projectId,
    tenantId: project.tenantId,
    roundId,
    idempotencyKey:
      options.idempotencyKey ??
      `round:${projectId}:${roundNumber}:${selectedGenerationVariant}:${selectedRepairBudget}:${selectedEpisodesPerRound}:${selectedModel}`,
    message: `等待 worker 执行 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集 · ${llmModelLabel(selectedModel)}`,
    payload: {
      projectId,
      roundId,
      roundNumber,
      generationVariant: selectedGenerationVariant,
      repairBudget: selectedRepairBudget,
      episodesPerRound: selectedEpisodesPerRound,
      llmModel: selectedModel,
    } satisfies RoundGenerationPayload,
  });

  return { roundId, roundNum: roundNumber, jobId: job.id };
}

export async function startNextEngineRound(
  projectId: string,
  options: RoundGenerationOptions = {}
): Promise<{ roundId: string; roundNum: number; jobId: string } | null> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  if (!(await projectNeedsNextRound(project))) return null;
  const latest = await latestRoundForProject(projectId);
  return startEngineRound(projectId, (latest?.roundNum ?? 0) + 1, options);
}

function qualityGateFromRoundSummary(summaryJson: string | null): RoundQualityGate {
  if (!summaryJson) return { status: null, rewriteInstruction: null };
  try {
    const summary = JSON.parse(summaryJson) as {
      quality_report?: {
        status?: unknown;
        rewrite_instruction?: unknown;
      };
    };
    const status = summary.quality_report?.status;
    const rewriteInstruction = summary.quality_report?.rewrite_instruction;
    if (
      status === "usable" ||
      status === "needs_rewrite" ||
      status === "context_conflict" ||
      status === "needs_human_review"
    ) {
      return {
        status,
        rewriteInstruction:
          typeof rewriteInstruction === "string" && rewriteInstruction.trim()
            ? rewriteInstruction
            : null,
      };
    }
  } catch {
    return { status: null, rewriteInstruction: null };
  }
  return { status: null, rewriteInstruction: null };
}

async function pauseRunAllForQualityGate(
  project: ProjectRow,
  latestRound: NonNullable<Awaited<ReturnType<typeof latestRoundForProject>>>,
  gate: RoundQualityGate
): Promise<void> {
  const pausedAt = new Date().toISOString();
  const status = gate.status ?? "unknown";
  await updateProjectMeta(project.id, (meta) => ({
    ...meta,
    control: {
      ...(meta.control ?? {}),
      runAll: {
        ...(meta.control?.runAll ?? {}),
        enabled: false,
        pausedAt,
        pausedRound: latestRound.roundNum,
        pausedQualityStatus: status,
        pausedReason: `quality_status:${status}`,
        pausedRewriteInstruction: gate.rewriteInstruction,
      },
    },
  }));
  await db
    .update(schema.projects)
    .set({ status: "failed", updatedAt: new Date() })
    .where(eq(schema.projects.id, project.id));
}

export async function scheduleNextRoundIfRunAll(
  projectId: string
): Promise<{ roundId: string; roundNum: number; jobId: string } | null> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  const settings = projectRunAllSettings(project);
  if (!settings.enabled) return null;
  const latest = await latestRoundForProject(projectId);
  if (latest?.status === "done") {
    const gate = qualityGateFromRoundSummary(latest.summaryJson);
    if (gate.status && gate.status !== "usable") {
      await pauseRunAllForQualityGate(project, latest, gate);
      return null;
    }
  }
  return startNextEngineRound(projectId, {
    generationVariant: settings.generationVariant,
    repairBudget: settings.repairBudget,
    episodesPerRound: MAX_EPISODES_PER_ROUND,
    llmModel: settings.llmModel,
  });
}

export async function latestRoundNumber(projectId: string): Promise<number | null> {
  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, projectId),
    orderBy: [desc(schema.rounds.roundNum)],
  });
  return rounds[0]?.roundNum ?? null;
}

export async function getDeliveryPreflight(
  projectId: string,
  roundNumber?: number
): Promise<DeliveryPreflightReport> {
  const args = ["check-delivery", "--project-dir", engineProjectDir(projectId), "--json"];
  if (roundNumber) args.push("--round-number", String(roundNumber));
  const stdout = await runNovelDrama(args);
  return JSON.parse(stdout) as DeliveryPreflightReport;
}

export async function exportDeliveryZip(
  projectId: string,
  roundNumber?: number,
  allowIssues = false
): Promise<string> {
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  const output = await deliveryZipPath(projectId, resolvedRoundNumber);
  const args = [
    "export-delivery",
    "--project-dir",
    engineProjectDir(projectId),
    "--round-number",
    String(resolvedRoundNumber),
    "--output",
    output,
  ];
  if (allowIssues) args.push("--allow-issues");
  await runNovelDrama(args);
  return output;
}

export async function deliveryZipPath(
  projectId: string,
  roundNumber?: number | null
): Promise<string> {
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  return path.join(
    /*turbopackIgnore: true*/
    projectDir(projectId),
    `delivery_round_${String(resolvedRoundNumber).padStart(3, "0")}.zip`
  );
}

export async function exportVideoBrief(
  projectId: string,
  roundNumber?: number
): Promise<{ jsonPath: string; markdownPath: string }> {
  const args = ["export-video-brief", "--project-dir", engineProjectDir(projectId)];
  if (roundNumber) args.push("--round-number", String(roundNumber));
  await runNovelDrama(args);
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  const roundDir = path.join(
    /*turbopackIgnore: true*/
    engineProjectDir(projectId),
    roundDirName(resolvedRoundNumber)
  );
  return {
    jsonPath: path.join(roundDir, "video_brief.json"),
    markdownPath: path.join(roundDir, "video_brief.md"),
  };
}

export async function exportLocalization(
  projectId: string,
  profilePath: string,
  roundNumber?: number,
  profileId = "us_tiktok"
): Promise<{ jsonPath: string; markdownPath: string }> {
  const safeProfileId = profileId.replace(/[^a-zA-Z0-9_-]/g, "_");
  const args = [
    "export-localization",
    "--project-dir",
    engineProjectDir(projectId),
    "--profile",
    profilePath,
  ];
  if (roundNumber) args.push("--round-number", String(roundNumber));
  await runNovelDrama(args);
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  const roundDir = path.join(
    /*turbopackIgnore: true*/
    engineProjectDir(projectId),
    roundDirName(resolvedRoundNumber)
  );
  const baseName = `localization_${safeProfileId}`;
  return {
    jsonPath: path.join(roundDir, `${baseName}.json`),
    markdownPath: path.join(roundDir, `${baseName}.md`),
  };
}

function assertJobProjectMatches(job: JobRow, project: ProjectRow): void {
  if (job.projectId && job.projectId !== project.id) {
    throw new Error("job project mismatch");
  }
  if (job.tenantId && project.tenantId && job.tenantId !== project.tenantId) {
    throw new Error("job tenant mismatch");
  }
}

async function executeDeliveryExportJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<DeliveryExportPayload>(job);
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, payload.projectId),
  });
  if (!project) throw new Error("project not found");
  assertJobProjectMatches(job, project);
  try {
    await updateJob(job.id, {
      message: "生成交付 ZIP",
      progress: 20,
    });
    const zipPath = await exportDeliveryZip(
      project.id,
      payload.roundNumber ?? undefined,
      Boolean(payload.allowIssues)
    );
    await succeedJob(job.id, {
      message: "交付 ZIP 已生成",
      result: {
        projectId: project.id,
        roundNumber: payload.roundNumber ?? (await latestRoundNumber(project.id)),
        allowIssues: Boolean(payload.allowIssues),
        zipPath,
      },
    });
  } catch (error) {
    await failJob(job.id, error, {
      message: "交付 ZIP 导出失败",
    });
    throw e

... [TRUNCATED FOR REVIEW PACK] ...

```


## File: `src/lib/jobs.ts`
```
import { and, asc, desc, eq, inArray, isNull, lt, or, type SQL } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { EngineJob } from "./engine-types";

type JobInsert = typeof schema.jobs.$inferInsert;
export type JobRow = typeof schema.jobs.$inferSelect;
export type JobKind = JobInsert["kind"];
export type JobStatus = NonNullable<JobInsert["status"]>;
export const STALE_RUNNING_JOB_MS = 30 * 60 * 1000;
export const STALE_QUEUED_JOB_MS = 15 * 60 * 1000;

export type JobFailureCategory =
  | "provider_quota"
  | "provider_auth"
  | "provider_rate_limit"
  | "provider_json"
  | "engine_timeout"
  | "worker_stale"
  | "engine_error"
  | "unknown";

export type JobFailureClassification = {
  category: JobFailureCategory;
  userMessage: string;
  operatorHint: string;
  retryableNow: boolean;
};

const failureDefaults: Record<JobFailureCategory, JobFailureClassification> = {
  provider_quota: {
    category: "provider_quota",
    userMessage: "LLM 额度或余额不足，任务已停止",
    operatorHint: "更换可用 key、提高 OpenRouter/模型额度，或先切到 mock 模式后再重试。",
    retryableNow: false,
  },
  provider_auth: {
    category: "provider_auth",
    userMessage: "LLM key 配置不可用，任务已停止",
    operatorHint: "检查 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL 后再重试。",
    retryableNow: false,
  },
  provider_rate_limit: {
    category: "provider_rate_limit",
    userMessage: "LLM 触发限流，任务已停止",
    operatorHint: "等待限流窗口恢复，或切换备用模型/provider 后重试。",
    retryableNow: false,
  },
  provider_json: {
    category: "provider_json",
    userMessage: "模型返回格式不合格，任务已停止",
    operatorHint: "可直接重试；如果连续出现，降低单轮集数或切换 JSON 更稳定的模型。",
    retryableNow: true,
  },
  engine_timeout: {
    category: "engine_timeout",
    userMessage: "生成超时，任务已停止",
    operatorHint: "可重试；如果反复超时，降低单轮集数或检查当前模型响应速度。",
    retryableNow: true,
  },
  worker_stale: {
    category: "worker_stale",
    userMessage: "任务疑似中断，已停止",
    operatorHint: "确认 worker 进程、LLM key 和模型配置后，在页面点击重试。",
    retryableNow: true,
  },
  engine_error: {
    category: "engine_error",
    userMessage: "Engine 执行失败",
    operatorHint: "查看错误详情后重试；若连续失败，需要检查 prompt、模型或输入文本。",
    retryableNow: true,
  },
  unknown: {
    category: "unknown",
    userMessage: "任务失败",
    operatorHint: "查看错误详情后重试；若连续失败，需要检查 worker 日志。",
    retryableNow: true,
  },
};

function isJobFailureCategory(value: unknown): value is JobFailureCategory {
  return typeof value === "string" && value in failureDefaults;
}

function storedFailureFromResultJson(
  resultJson: string | null
): JobFailureClassification | null {
  if (!resultJson) return null;
  try {
    const parsed = JSON.parse(resultJson) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    const result = parsed as {
      failureCategory?: unknown;
      operatorHint?: unknown;
      retryableNow?: unknown;
    };
    if (!isJobFailureCategory(result.failureCategory)) return null;
    const base = failureDefaults[result.failureCategory];
    return {
      ...base,
      operatorHint:
        typeof result.operatorHint === "string" && result.operatorHint.trim()
          ? result.operatorHint
          : base.operatorHint,
      retryableNow:
        typeof result.retryableNow === "boolean" ? result.retryableNow : base.retryableNow,
    };
  } catch {
    return null;
  }
}

function boundedProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function serializeResult(result: unknown): string | null {
  if (result == null) return null;
  return JSON.stringify(result, null, 2);
}

function dateToIso(value: Date | null): string | null {
  return value ? value.toISOString() : null;
}

function ageMs(job: Pick<JobRow, "createdAt" | "updatedAt">, now = new Date()): number {
  return now.getTime() - job.updatedAt.getTime();
}

function formatAge(ms: number): string {
  const minutes = Math.max(1, Math.round(ms / 60000));
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`;
}

function compactErrorText(value: string, limit = 1200): string {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= limit) return compact;
  return `${compact.slice(0, limit)}...`;
}

export function classifyJobFailureText(
  text: string | null | undefined
): JobFailureClassification | null {
  if (!text) return null;
  const normalized = text.toLowerCase();
  if (
    /key limit exceeded|daily limit|quota|insufficient_quota|credit balance|billing hard limit|limit exceeded/.test(
      normalized
    )
  ) {
    return failureDefaults.provider_quota;
  }
  if (
    /unauthorized|invalid api key|api key is not set|openai_api_key|\b401\b/.test(
      normalized
    )
  ) {
    return failureDefaults.provider_auth;
  }
  if (/rate limit|too many requests|\b429\b/.test(normalized)) {
    return failureDefaults.provider_rate_limit;
  }
  if (/invalid json|json that failed schema validation|response was truncated/.test(normalized)) {
    return failureDefaults.provider_json;
  }
  if (/timed out after|timeout|etimedout/.test(normalized)) {
    return failureDefaults.engine_timeout;
  }
  if (/novel-drama exited with code|traceback|exception|error/.test(normalized)) {
    return failureDefaults.engine_error;
  }
  return null;
}

export function isRunningJobStale(
  job: Pick<JobRow, "status" | "updatedAt">,
  now = new Date()
): boolean {
  return (
    job.status === "running" &&
    now.getTime() - job.updatedAt.getTime() > STALE_RUNNING_JOB_MS
  );
}

export function isQueuedJobWaitingTooLong(
  job: Pick<JobRow, "status" | "createdAt">,
  now = new Date()
): boolean {
  return (
    job.status === "queued" &&
    now.getTime() - job.createdAt.getTime() > STALE_QUEUED_JOB_MS
  );
}

export function isJobStale(
  job: Pick<JobRow, "status" | "createdAt" | "updatedAt">,
  now = new Date()
): boolean {
  return isRunningJobStale(job, now) || isQueuedJobWaitingTooLong(job, now);
}

export function isJobRetryable(job: Pick<JobRow, "status" | "updatedAt">): boolean {
  return job.status === "failed" || isRunningJobStale(job);
}

async function restoreRoundGenerationRetryState(job: JobRow): Promise<void> {
  if (job.kind !== "round_generation") return;
  const now = new Date();
  if (job.roundId) {
    await db
      .update(schema.rounds)
      .set({ status: "running", summaryJson: null })
      .where(eq(schema.rounds.id, job.roundId));
  }
  if (job.projectId) {
    await db
      .update(schema.projects)
      .set({ status: "running", updatedAt: now })
      .where(eq(schema.projects.id, job.projectId));
  }
}

export function jobToView(job: JobRow): EngineJob {
  const isRunningStale = isRunningJobStale(job);
  const isQueuedTooLong = isQueuedJobWaitingTooLong(job);
  const isStale = isRunningStale || isQueuedTooLong;
  const errorSource = [job.errorText, job.message, job.resultJson]
    .filter(Boolean)
    .join("\n");
  const failure = classifyJobFailureText(errorSource) ?? storedFailureFromResultJson(job.resultJson);
  const statusReason =
    failure?.userMessage ??
    (isRunningStale
      ? `worker 超过 ${formatAge(ageMs(job))} 没有心跳`
      : isQueuedTooLong
        ? `排队超过 ${formatAge(new Date().getTime() - job.createdAt.getTime())}，可能没有可用 worker 或项目被暂停`
        : null);
  const operatorHint =
    failure?.operatorHint ??
    (isRunningStale
      ? "系统会把该任务标记为失败，确认 worker 和 LLM key 后可重试。"
      : isQueuedTooLong
        ? "确认 round worker/quality worker 正在运行；如果刚更换配置，可刷新后重试。"
        : null);
  return {
    id: job.id,
    kind: job.kind,
    status: job.status,
    projectId: job.projectId,
    tenantId: job.tenantId,
    roundId: job.roundId,
    title: job.title,
    progress: job.progress,
    message: job.message,
    errorText: job.errorText,
    payloadJson: job.payloadJson,
    resultJson: job.resultJson,
    attempts: job.attempts,
    isStale,
    isQueuedTooLong,
    retryable: job.status === "failed" || isRunningStale,
    failureCategory: failure?.category ?? null,
    statusReason,
    operatorHint,
    createdAt: job.createdAt.toISOString(),
    updatedAt: job.updatedAt.toISOString(),
    startedAt: dateToIso(job.startedAt),
    finishedAt: dateToIso(job.finishedAt),
  };
}

export async function createJob({
  kind,
  title,
  projectId,
  tenantId,
  roundId,
  idempotencyKey,
  message,
  payload,
  status = "queued",
  progress = 0,
}: {
  kind: JobKind;
  title: string;
  projectId?: string | null;
  tenantId?: string | null;
  roundId?: string | null;
  idempotencyKey?: string | null;
  message?: string | null;
  payload?: unknown;
  status?: JobStatus;
  progress?: number;
}): Promise<JobRow> {
  const normalizedIdempotencyKey = idempotencyKey?.trim() || null;
  if (normalizedIdempotencyKey) {
    const filters: SQL[] = [
      eq(schema.jobs.kind, kind),
      eq(schema.jobs.idempotencyKey, normalizedIdempotencyKey),
    ];
    if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
    else if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
    const existingJob = await db.query.jobs.findFirst({
      where: and(...filters),
      orderBy: [desc(schema.jobs.createdAt)],
    });
    if (existingJob) return existingJob;
  }
  if (
    kind === "round_generation" &&
    roundId &&
    (status === "queued" || status === "running")
  ) {
    const activeJob = await db.query.jobs.findFirst({
      where: and(
        eq(schema.jobs.kind, kind),
        eq(schema.jobs.roundId, roundId),
        inArray(schema.jobs.status, ["queued", "running"])
      ),
    });
    if (activeJob) {
      throw new Error(
        `active job already exists for round ${roundId}: ${activeJob.id}`
      );
    }
  }
  const now = new Date();
  const row: JobInsert = {
    id: uuid(),
    kind,
    status,
    projectId,
    tenantId,
    roundId,
    title,
    progress: boundedProgress(progress),
    message,
    payloadJson: serializeResult(payload),
    idempotencyKey: normalizedIdempotencyKey,
    createdAt: now,
    updatedAt: now,
    startedAt: status === "running" ? now : null,
  };
  try {
    await db.insert(schema.jobs).values(row);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (
      kind === "round_generation" &&
      roundId &&
      /jobs_active_round_generation_unique/i.test(message)
    ) {
      const activeJob = await db.query.jobs.findFirst({
        where: and(
          eq(schema.jobs.kind, kind),
          eq(schema.jobs.roundId, roundId),
          inArray(schema.jobs.status, ["queued", "running"])
        ),
      });
      throw new Error(
        `active job already exists for round ${roundId}: ${activeJob?.id ?? "unknown"}`
      );
    }
    if (
      normalizedIdempotencyKey &&
      /jobs_tenant_kind_idempotency_unique|unique/i.test(message)
    ) {
      const filters: SQL[] = [
        eq(schema.jobs.kind, kind),
        eq(schema.jobs.idempotencyKey, normalizedIdempotencyKey),
      ];
      if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
      else if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
      const existingJob = await db.query.jobs.findFirst({
        where: and(...filters),
        orderBy: [desc(schema.jobs.createdAt)],
      });
      if (existingJob) return existingJob;
    }
    throw error;
  }
  const created = await db.query.jobs.findFirst({
    where: eq(schema.jobs.id, row.id),
  });
  if (!created) throw new Error("job insert failed");
  return created;
}

export async function updateJob(
  jobId: string | null | undefined,
  values: {
    status?: JobStatus;
    progress?: number;
    message?: string | null;
    errorText?: string | null;
    payload?: unknown;
    result?: unknown;
    startedAt?: Date | null;
    finishedAt?: Date | null;
  }
): Promise<void> {
  if (!jobId) return;
  const update: Partial<JobInsert> = {
    updatedAt: new Date(),
  };
  if (values.status) update.status = values.status;
  if (values.progress != null) update.progress = boundedProgress(values.progress);
  if ("message" in values) update.message = values.message;
  if ("errorText" in values) update.errorText = values.errorText;
  if ("payload" in values) update.payloadJson = serializeResult(values.payload);
  if ("result" in values) update.resultJson = serializeResult(values.result);
  if ("startedAt" in values) update.startedAt = values.startedAt;
  if ("finishedAt" in values) update.finishedAt = values.finishedAt;

  await db.update(schema.jobs).set(update).where(eq(schema.jobs.id, jobId));
}

export async function findJob(jobId: string): Promise<JobRow | null> {
  const job = await db.query.jobs.findFirst({
    where: eq(schema.jobs.id, jobId),
  });
  return job ?? null;
}

export function parseJobPayload<T>(job: JobRow): T {
  if (!job.payloadJson) {
    throw new Error(`job ${job.id} is missing payload`);
  }
  return JSON.parse(job.payloadJson) as T;
}

export async function claimNextQueuedJob({
  kind,
}: {
  kind?: JobKind;
} = {}): Promise<JobRow | null> {
  const filters: SQL[] = [eq(schema.jobs.status, "queued")];
  if (kind) filters.push(eq(schema.jobs.kind, kind));
  const queuedJobs = await db.query.jobs.findMany({
    where: and(...filters),
    orderBy: [asc(schema.jobs.createdAt)],
    limit: 25,
  });
  for (const candidate of queuedJobs) {
    const now = new Date();
    if (isQueuedJobWaitingTooLong(candidate, now)) {
      await stopStaleQueuedJob(candidate, now);
      continue;
    }

    if (candidate.kind === "round_generation" && candidate.projectId) {
      const project = await db.query.projects.findFirst({
        where: eq(schema.projects.id, candidate.projectId),
      });
      if (project?.status === "paused") continue;
    }

    const result = await db
      .update(schema.jobs)
      .set({
        status: "running",
        attempts: candidate.attempts + 1,
        progress: Math.max(candidate.progress, 5),
        message: candidate.message ?? "worker 已认领",
        startedAt: candidate.startedAt ?? now,
        updatedAt: now,
      })
      .where(and(eq(schema.jobs.id, candidate.id), eq(schema.jobs.status, "queued")));
    if (result.changes < 1) continue;

    const claimed = await db.query.jobs.findFirst({
      where: eq(schema.jobs.id, candidate.id),
    });
    if (claimed?.status === "running") return claimed;
  }
  return null;
}

async function stopStaleQueuedJob(job: JobRow, now = new Date()): Promise<void> {
  const age = now.getTime() - job.createdAt.getTime();
  const errorText = `排队超过 ${formatAge(age)} 没有被 worker 认领，系统已停止任务。`;
  const result = {
    failureCategory: "worker_stale",
    operatorHint: "确认 worker 正常运行后，在页面点击重试。",
    recoveredAt: now.toISOString(),
    queuedSince: job.createdAt.toISOString(),
  };

  await updateJob(job.id, {
    status: "failed",
    progress: 100,
    message: "排队超时，任务已停止",
    errorText,
    result,
    finishedAt: now,
  });

  if (job.roundId) {
    await db
      .update(schema.rounds)
      .set({
        status: "failed",
        summaryJson: JSON.stringify(
          {
            error: errorText,
            ...result,
          },
          null,
          2
        ),
      })
      .where(eq(schema.rounds.id, job.roundId));
  }
  if (job.projectId) {
    await db
      .update(schema.projects)
      .set({ status: "failed", updatedAt: now })
      .where(eq(schema.projects.id, job.projectId));
  }
}

export async function requeueRetryableJob(jobId: string): Promise<JobRow> {
  const job = await findJob(jobId);
  if (!job) throw new Error("job not found");
  if (!isJobRetryable(job)) {
    throw new Error(
      `only failed or stale running jobs can be retried; current status: ${job.status}`
    );
  }
  const reason = job.status === "failed" ? "重试" : "恢复队列";

  await restoreRoundGenerationRetryState(job);
  await updateJob(job.id, {
    status: "queued",
    progress: 0,
    message: `等待 worker ${reason} · 已尝试 ${job.attempts} 次`,
    errorText: null,
    result: null,
    startedAt: null,
    finishedAt: null,
  });

  const retried = await findJob(job.id);
  if (!retried) throw new Error("job retry failed");
  return retried;
}

export async function requeueInterruptedRunningJobs({
  kind,
  olderThanMs = 0,
}: {
  kind?: JobKind;
  olderThanMs?: number;
} = {}): Promise<{ requeued: number }> {
  const cutoff = new Date(Date.now() - Math.max(0, olderThanMs));
  const filters: SQL[] = [eq(schema.jobs.status, "running"), lt(schema.jobs.updatedAt, cutoff)];
  if (kind) filters.push(eq(schema.jobs.kind, kind));
  const runningJobs = await db.query.jobs.findMany({
    where: and(...filters),
    orderBy: [asc(schema.jobs.updatedAt)],
  });

  for (const job of runningJobs) {
    await updateJob(job.id, {
      status: "queued",
      progress: 0,
      message: `worker 启动后恢复队列 · 已尝试 ${job.attempts} 次`,
      errorText: null,
      result: null,
      startedAt: null,
      finishedAt: null,
    });

    if (job.roundId) {
      await db
        .update(schema.rounds)
        .set({ status: "running", summaryJson: null })
        .where(eq(schema.rounds.id, job.roundId));
    }
    if (job.projectId) {
      await db
        .update(schema.projects)
        .set({ status: "running", updatedAt: new Date() })
        .where(eq(schema.projects.id, job.projectId));
    }
  }

  return { requeued: runningJobs.length };
}

export async function reconcileStaleJobs({
  olderThanMs = STALE_RUNNING_JOB_MS,
}: {
  olderThanMs?: number;
} = {}): Promise<{ failedRunning: number }> {
  const cutoff = new Date(Date.now() - olderThanMs);
  const staleJobs = await db.query.jobs.findMany({
    where: and(eq(schema.jobs.status, "running"), lt(schema.jobs.updatedAt, cutoff)),
  });
  const now = new Date();

  for (const job of staleJobs) {
    const failure = classifyJobFailureText(
      [job.errorText, job.message, job.resultJson].filter(Boolean).join("\n")
    );
    const fallbackMessage = `worker 超过 ${formatAge(now.getTime() - job.updatedAt.getTime())} 没有心跳，系统已停止自动重排。`;
    const errorText = failure
      ? `${failure.userMessage}。${failure.operatorHint}`
      : fallbackMessage;
    const result = {
      failureCategory: failure?.category ?? "worker_stale",
      operatorHint:
        failure?.operatorHint ??
        "确认 worker 进程、LLM key 和模型配置后，在页面点击重试。",
      recoveredAt: now.toISOString(),
      staleSince: job.updatedAt.toISOString(),
    };

    await updateJob(job.id, {
      status: "failed",
      progress: 100,
      message: failure ? failure.userMessage : "任务疑似中断，已停止",
      errorText,
      result,
      finishedAt: now,
    });

    if (job.roundId) {
      await db
        .update(schema.rounds)
        .set({
          status: "failed",
          summaryJson: JSON.stringify(
            {
              error: errorText,
              ...result,
            },
            null,
            2
          ),
        })
        .where(eq(schema.rounds.id, job.roundId));
    }
    if (job.projectId) {
      await db
        .update(schema.projects)
        .set({ status: "failed", updatedAt: now })
        .where(eq(schema.projects.id, job.projectId));
    }
  }

  return { failedRunning: staleJobs.length };
}

export async function requeueStaleRunningJobs({
  olderThanMs = STALE_RUNNING_JOB_MS,
}: {
  olderThanMs?: number;
} = {}): Promise<void> {
  await reconcileStaleJobs({ olderThanMs });
}

export async function succeedJob(
  jobId: string | null | undefined,
  values: { message?: string | null; result?: unknown } = {}
): Promise<void> {
  await updateJob(jobId, {
    status: "succeeded",
    progress: 100,
    message: values.message ?? "完成",
    errorText: null,
    result: values.result,
    finishedAt: new Date(),
  });
}

export async function failJob(
  jobId: string | null | undefined,
  error: unknown,
  values: {
    message?: string | null;
    errorText?: string | null;
    result?: unknown;
  } = {}
): Promise<void> {
  const rawMessage = error instanceof Error ? error.message : String(error);
  const failure = classifyJobFailureText(rawMessage);
  const message = values.errorText ?? (
    failure
      ? `${failure.userMessage}。${failure.operatorHint}`
      : compactErrorText(rawMessage)
  );
  await updateJob(jobId, {
    status: "failed",
    progress: 100,
    message: values.message ?? failure?.userMessage ?? "失败",
    errorText: message,
    result:
      values.result ??
      (failure
        ? {
            failureCategory: failure.category,
            operatorHint: failure.operatorHint,
            retryableNow: failure.retryableNow,
          }
        : undefined),
    finishedAt: new Date(),
  });
}

export async function listJobs({
  projectId,
  tenantId,
  ownerUserId,
  kind,
  limit = 20,
}: {
  projectId?: string;
  tenantId?: string;
  ownerUserId?: string;
  kind?: JobKind;
  limit?: number;
} = {}): Promise<JobRow[]> {
  await reconcileStaleJobs();
  const filters: SQL[] = [];
  if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
  if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
  if (ownerUserId && tenantId) {
    const ownedProjects = await db.query.projects.findMany({
      columns: { id: true },
      where: and(
        eq(schema.projects.tenantId, tenantId),
        eq(schema.projects.ownerUserId, ownerUserId)
      ),
    });
    const ownedProjectIds = ownedProjects.map((project) => project.id);
    if (projectId && !ownedProjectIds.includes(projectId)) return [];
    if (!projectId) {
      filters.push(
        ownedProjectIds.length > 0
          ? or(isNull(schema.jobs.projectId), inArray(schema.jobs.projectId, ownedProjectIds))!
          : isNull(schema.jobs.projectId)
      );
    }
  }
  if (kind) filters.push(eq(schema.jobs.kind, kind));
  return db.query.jobs.findMany({
    where: filters.length ? and(...filters) : undefined,
    orderBy: [desc(schema.jobs.createdAt)],
    limit: Math.max(1, Math.min(100, Math.floor(limit))),
  });
}

export async function listJobViews(
  options: Parameters<typeof listJobs>[0] = {}
): Promise<EngineJob[]> {
  const rows = await listJobs(options);
  return rows.map(jobToView);
}

```


## File: `src/app/projects/[id]/rounds/[n]/RoundClient.tsx`
```
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Copy,
  Cpu,
  Download,
  FileText,
  Gauge,
  GitCompareArrows,
  Languages,
  ListVideo,
  PackageCheck,
  Pause,
  Play,
  RefreshCw,
  ScrollText,
  Sparkles,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ProjectManageButton } from "@/app/ProjectActionsClient";
import type { EngineJob } from "@/lib/engine-types";
import type { EditImpactReport } from "@/lib/edit-impact";
import {
  DEFAULT_LLM_MODEL,
  llmModelLabel,
  llmModelOptions,
} from "@/lib/llm-model-options";

type Project = {
  id: string;
  name: string;
  targetEpisodeCount: number;
  status: string;
  metaJson?: string | null;
};
type Round = {
  id: string;
  roundNum: number;
  epRange: string;
  status: string;
  summaryJson: string | null;
};
type Episode = {
  id: string;
  roundId: string;
  epNum: number;
  status: string;
  score: number | null;
  scriptTxt: string | null;
  reviewJson?: string | null;
  retryCount: number;
};
type EngineRoundSummary = {
  quality_report?: {
    status: string;
    scores: Record<string, number>;
    blocking_issues: string[];
  };
  runtime_report?: {
    generation_variant?: string;
    repair_budget?: string;
    llm_model?: string | null;
    total_duration_ms?: number;
    stages?: Array<{
      name: string;
      duration_ms: number;
      status: string;
      error?: string | null;
    }>;
    llm_calls?: Array<{
      usage?: {
        prompt_tokens?: number | null;
        completion_tokens?: number | null;
        total_tokens?: number | null;
      } | null;
    }>;
  };
  next_round_context?: {
    current_episode: number;
    summary: string;
    open_hooks: string[];
    forbidden_reveals: string[];
  };
  adaptation_quality_report?: {
    source_fidelity?: {
      score: number;
      blocking_warnings: string[];
      advisory_warnings: string[];
    };
    continuity?: {
      score: number;
      blocking_warnings: string[];
      advisory_warnings: string[];
    };
    blocking_warnings: string[];
    advisory_warnings: string[];
  };
  source_evidence_report?: {
    coverage_score: number;
    missing_items: string[];
  };
  drama_quality_report?: {
    dimensions: Array<{
      name: string;
      score: number;
      status: "passed" | "advisory" | "blocking";
    }>;
  };
  story_state_ledger?: {
    current_episode: number;
    entries: Array<{
      episode?: number | null;
      kind: string;
      key: string;
      value: string;
      status: string;
    }>;
    warnings: string[];
  };
  source_strength_profile?: {
    overall_level: "strong" | "medium" | "weak";
    recommended_intensity: "light" | "medium" | "heavy";
    reasons: string[];
  };
  methodology_context?: {
    source_strength_level: "strong" | "medium" | "weak";
    adaptation_intensity: "light" | "medium" | "heavy";
    cards: Array<{
      id: string;
      name: string;
      category: string;
      trigger: string;
      generation_rule: string;
      quality_rule: string;
    }>;
  };
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
  };
};
type DeliveryPreflight = {
  ready: boolean;
  warnings: string[];
  files: Array<{ path: string; bytes: number }>;
};
type LocalizationProfileOption = {
  id: string;
  label: string;
  locale: string;
  platform: string;
  targetLanguage: string;
};
type ProjectPayload = {
  project: Project;
  rounds: Round[];
  episodes: Episode[];
  jobs: EngineJob[];
};

type ProjectMeta = {
  control?: {
    runAll?: {
      enabled?: boolean;
    };
    qualityGate?: {
      status?: string | null;
      round?: number | null;
      pausedAt?: string | null;
      rewriteInstruction?: string | null;
    };
  };
};

const generationVariantOptions = [
  { value: "drama_engine_first", label: "强剧情优先" },
  { value: "sop_full_stack", label: "SOP 全链路（慢速精修）" },
];

const repairBudgetOptions = [
  { value: "episode", label: "逐集修复" },
  { value: "rewrite", label: "改写一次" },
  { value: "none", label: "不自动修复" },
];

const episodeCountOptions = [1, 2, 3, 4, 5];

const qualityLabels: Record<string, string> = {
  hook: "开场",
  conflict: "冲突",
  cliffhanger: "断点",
  continuity: "连续",
  video_feasibility: "可拍",
};

function parseSummary(round?: Round): EngineRoundSummary | null {
  if (!round?.summaryJson) return null;
  try {
    return JSON.parse(round.summaryJson) as EngineRoundSummary;
  } catch {
    return null;
  }
}

type JobResultSummary = {
  runtimeMs?: number | null;
  llmCalls?: number | null;
  qualityStatus?: string | null;
  targetEpisodeRange?: string | null;
  generationVariant?: string | null;
  repairBudget?: string | null;
  episodesPerRound?: number | null;
  llmModel?: string | null;
  methodologyCards?: string[] | null;
  sourceStrength?: string | null;
  adaptationIntensity?: string | null;
};

function parseJobResult(job?: EngineJob | null): JobResultSummary | null {
  if (!job?.resultJson) return null;
  try {
    return JSON.parse(job.resultJson) as JobResultSummary;
  } catch {
    return null;
  }
}

function parseProjectMeta(project: Project): ProjectMeta {
  if (!project.metaJson) return {};
  try {
    return JSON.parse(project.metaJson) as ProjectMeta;
  } catch {
    return {};
  }
}

function formatDuration(ms?: number | null): string {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return "-";
  if (ms < 1000) return `${Math.max(0, Math.round(ms))} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

function formatNumber(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return Math.round(value).toLocaleString();
}

function clampQualityScore(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(10, value));
}

const GEMINI_FLASH_LITE_INPUT_USD_PER_MILLION = 0.25;
const GEMINI_FLASH_LITE_OUTPUT_USD_PER_MILLION = 1.5;

type RuntimeTokenSummary = {
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  estimatedUsd: number | null;
};

function runtimeTokenSummary(
  calls?: NonNullable<EngineRoundSummary["runtime_report"]>["llm_calls"] | null
): RuntimeTokenSummary {
  if (!calls?.length) {
    return {
      inputTokens: null,
      outputTokens: null,
      totalTokens: null,
      estimatedUsd: null,
    };
  }
  const inputTokens = calls.reduce((sum, call) => {
    const value = call.usage?.prompt_tokens;
    return sum + (typeof value === "number" ? value : 0);
  }, 0);
  const outputTokens = calls.reduce((sum, call) => {
    const value = call.usage?.completion_tokens;
    return sum + (typeof value === "number" ? value : 0);
  }, 0);
  const totalTokens = calls.reduce((sum, call) => {
    const value = call.usage?.total_tokens;
    return sum + (typeof value === "number" ? value : 0);
  }, 0);
  const hasSplitUsage = inputTokens > 0 || outputTokens > 0;
  return {
    inputTokens: inputTokens || null,
    outputTokens: outputTokens || null,
    totalTokens: totalTokens || (hasSplitUsage ? inputTokens + outputTokens : null),
    estimatedUsd: hasSplitUsage
      ? (inputTokens / 1_000_000) * GEMINI_FLASH_LITE_INPUT_USD_PER_MILLION +
        (outputTokens / 1_000_000) * GEMINI_FLASH_LITE_OUTPUT_USD_PER_MILLION
      : null,
  };
}

function formatUsd(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function jobLabel(job: EngineJob): string {
  if (job.status === "queued") return job.isQueuedTooLong ? "等待过久" : "排队中";
  if (job.status === "running") return job.isStale ? "疑似中断" : "运行中";
  if (job.status === "succeeded") return "已完成";
  return "失败";
}

function qualityStatusText(status?: string | null): string {
  if (status === "usable") return "可交付";
  if (status === "needs_human_review") return "待复核";
  if (status === "needs_rewrite") return "需重写";
  if (status === "context_conflict") return "上下文冲突";
  if (status === "failed") return "失败";
  return status ?? "未评估";
}

function parseEpisodeReviewStatus(episode: Episode): string | null {
  if (!episode.reviewJson) return null;
  try {
    const review = JSON.parse(episode.reviewJson) as { status?: string | null };
    return review.status ?? null;
  } catch {
    return null;
  }
}

function episodeDisplay(episode: Episode): {
  label: string;
  tone: "ready" | "active" | "danger" | "muted" | "review";
  badgeVariant: "default" | "destructive" | "outline";
  badgeClassName?: string;
} {
  const status = episode.status;
  const reviewStatus = parseEpisodeReviewStatus(episode);
  if (status === "green") {
    return { label: "通过", tone: "ready", badgeVariant: "default" };
  }
  if (status === "red" && reviewStatus === "needs_human_review") {
    return {
      label: "待复核",
      tone: "review",
      badgeVariant: "outline",
      badgeClassName: "border-amber-200 bg-amber-50 text-amber-700",
    };
  }
  if (status === "red" && reviewStatus) {
    return {
      label: qualityStatusText(reviewStatus),
      tone: "danger",
      badgeVariant: "destructive",
    };
  }
  if (status === "red") {
    return { label: "需修", tone: "danger", badgeVariant: "destructive" };
  }
  if (status === "pending") return { label: "等待", tone: "active", badgeVariant: "outline" };
  if (status === "failed") return { label: "失败", tone: "danger", badgeVariant: "destructive" };
  if (status === "running") return { label: "生成中", tone: "active", badgeVariant: "outline" };
  return { label: status, tone: "muted", badgeVariant: "outline" };
}

function extractEpisodeTitle(ep: Episode): string {
  const fallback = `第 ${ep.epNum} 集`;
  if (!ep.scriptTxt) return fallback;
  const firstLine = ep.scriptTxt
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);
  if (!firstLine) return fallback;
  return firstLine.replace(/^第\s*\d+\s*集\s*/, "").trim() || firstLine;
}

function scriptLineCount(ep?: Episode): number {
  if (!ep?.scriptTxt) return 0;
  return ep.scriptTxt.split(/\r?\n/).filter((line) => line.trim()).length;
}

async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    const copied = document.execCommand("copy");
    if (!copied) throw new Error("copy command failed");
  } finally {
    document.body.removeChild(textarea);
  }
}

function filenameFromDisposition(
  disposition: string | null,
  fallback: string
): string {
  if (!disposition) return fallback;
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded.replace(/^"|"$/g, ""));
    } catch {
      return fallback;
    }
  }
  return disposition.match(/filename="([^"]+)"/i)?.[1] ?? fallback;
}

async function readResponseError(res: Response, fallback: string): Promise<string> {
  const text = await res.text().catch(() => "");
  if (!text) return `${fallback} (${res.status})`;
  try {
    const payload = JSON.parse(text) as { error?: string };
    return payload.error ?? text;
  } catch {
    return text;
  }
}

function episodeCountFromRange(range?: string | null): number | null {
  if (!range) return null;
  const match = range.match(/E(?:P)?0*(\d+)\s*-\s*E(?:P)?0*(\d+)/i);
  if (!match) return null;
  const start = Number(match[1]);
  const end = Number(match[2]);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return null;
  }
  return end - start + 1;
}

function fullSeriesEpisodes(episodes: Episode[], rounds: Round[]): Episode[] {
  const roundNumberById = new Map(rounds.map((round) => [round.id, round.roundNum]));
  const earliestByEpisode = new Map<number, Episode>();
  const orderedEpisodes = [...episodes].sort((a, b) => {
    if (a.epNum !== b.epNum) return a.epNum - b.epNum;
    return (roundNumberById.get(a.roundId) ?? 0) - (roundNumberById.get(b.roundId) ?? 0);
  });
  for (const episode of orderedEpisodes) {
    const current = earliestByEpisode.get(episode.epNum);
    if (!current || (!current.scriptTxt && episode.scriptTxt)) {
      earliestByEpisode.set(episode.epNum, episode);
    }
  }
  return [...earliestByEpisode.values()].sort((a, b) => a.epNum - b.epNum);
}

function visibleScriptCount(episodes: Episode[]): number {
  return episodes.filter((episode) => episode.scriptTxt).length;
}

function activeOrLatestJob(jobs: EngineJob[]): EngineJob | undefined {
  return (
    jobs.find((job) => job.status === "running" || job.status === "queued") ??
    jobs[0]
  );
}

function shouldKeepPollingProject(data: ProjectPayload, roundNum: number): boolean {
  const currentRound = data.rounds.find((round) => round.roundNum === roundNum);
  if (currentRound?.status === "failed") return false;
  if (data.project.status === "done" || data.project.status === "failed") {
    return false;
  }
  const runAllEnabled = parseProjectMeta(data.project).control?.runAll?.enabled === true;
  const hasActiveJob = data.jobs.some(
    (job) => job.status === "running" || job.status === "queued"
  );
  if (data.project.status === "running" && (runAllEnabled || hasActiveJob)) {
    return true;
  }
  if (
    visibleScriptCount(fullSeriesEpisodes(data.episodes, data.rounds)) >=
    data.project.targetEpisodeCount
  ) {
    return false;
  }
  return currentRound?.status !== "done";
}

export function RoundClient({
  projectId,
  roundNum,
  project,
}: {
  projectId: string;
  roundNum: number;
  project: Project;
}) {
  const [data, setData] = useState<ProjectPayload | null>(null);
  const [delivery, setDelivery] = useState<DeliveryPreflight | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [pollKey, setPollKey] = useState(0);
  const [profiles, setProfiles] = useState<LocalizationProfileOption[]>([]);
  const [selectedProfile, setSelectedProfile] = useState("us_tiktok");
  const [selectedEpisodeNum, setSelectedEpisodeNum] = useState<number | null>(
    null
  );
  const [selectedGenerationVariant, setSelectedGenerationVariant] =
    useState("drama_engine_first");
  const [selectedRepairBudget, setSelectedRepairBudget] = useState("episode");
  const [selectedEpisodesPerRound, setSelectedEpisodesPerRound] = useState("5");
  const [selectedLlmModel, setSelectedLlmModel] = useState<string>(DEFAULT_LLM_MODEL);
  const [episodeOptimizeInstruction, setEpisodeOptimizeInstruction] = useState("");
  const [impactDraft, setImpactDraft] = useState("");
  const [impactReport, setImpactReport] = useState<EditImpactReport | null>(null);

  async function loadProjectData(): Promise<ProjectPayload> {
    const res = await fetch(`/api/projects/${projectId}`, {
      cache: "no-store",
      headers: { "cache-control": "no-cache" },
    });
    const d = (await res.json()) as ProjectPayload & { error?: string };
    if (!res.ok) throw new Error(d.error ?? "项目状态加载失败");
    setData(d);
    return d;
  }

  useEffect(() => {
    let stopped = false;
    async function poll() {
      while (!stopped) {
        try {
          const d = await loadProjectData();
          if (!shouldKeepPollingProject(d, roundNum)) {
            break;
          }
        } catch (error) {
          console.warn("[round-poll] project refresh failed; retrying", error);
        }
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, [projectId, roundNum, pollKey]);

  useEffect(() => {
    let cancelled = false;
    async function loadProfiles() {
      const res = await fetch(`/api/projects/${projectId}/localization`);
      if (!res.ok) return;
      const loaded = (await res.json()) as LocalizationProfileOption[];
      if (cancelled) return;
      setProfiles(loaded);
      if (loaded.length > 0 && !loaded.some((item) => item.id === selectedProfile)) {
        setSelectedProfile(loaded[0].id);
      }
    }
    loadProfiles();
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedProfile]);

  useEffect(() => {
    if (!data) return;
    const candidateEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
    if (candidateEpisodes.length === 0) return;
    if (!candidateEpisodes.some((episode) => episode.epNum === selectedEpisodeNum)) {
      setSelectedEpisodeNum(candidateEpisodes[0].epNum);
    }
  }, [data, roundNum, selectedEpisodeNum]);

  useEffect(() => {
    if (!data) return;
    const candidateEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
    const currentEpisode =
      candidateEpisodes.find((episode) => episode.epNum === selectedEpisodeNum) ?? null;
    setImpactDraft(currentEpisode?.scriptTxt ?? "");
    setEpisodeOptimizeInstruction("");
    setImpactReport((currentReport) =>
      currentReport?.episodeId === currentEpisode?.id ? currentReport : null
    );
  }, [data, roundNum, selectedEpisodeNum]);

  if (!data) {
    return (
      <section className="page-shell">
        <Card className="round-loading-card">
          <RefreshCw className="size-4 animate-spin text-[color:var(--reela-pink)]" />
          <span>正在打开剧集工作台...</span>
        </Card>
      </section>
    );
  }

  const round = data.rounds.find((r) => r.roundNum === roundNum);
  const summary = parseSummary(round);
  const quality = summary?.quality_report;
  const context = summary?.next_round_context;
  const runtime = summary?.runtime_report;
  const adaptationQuality = summary?.adaptation_quality_report;
  const sourceEvidence = summary?.source_evidence_report;
  const dramaQuality = summary?.drama_quality_report;
  const storyLedger = summary?.story_state_ledger;
  const sourceStrength = summary?.source_strength_profile;
  const methodologyContext = summary?.methodology_context;
  const roundEpisodes = data.episodes
    .filter((e) => e.roundId === round?.id)
    .sort((a, b) => a.epNum - b.epNum);
  const projectEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
  const latestRound = data.rounds.reduce<Round | undefined>(
    (latest, item) => (!latest || item.roundNum > latest.roundNum ? item : latest),
    undefined
  );
  const eps = projectEpisodes;
  const selectedEpisode =
    eps.find((episode) => episode.epNum === selectedEpisodeNum) ?? eps[0] ?? null;
  const selectedTitle = selectedEpisode
    ? extractEpisodeTitle(selectedEpisode)
    : "暂无剧集";
  const selectedEpisodeDisplay = selectedEpisode
    ? episodeDisplay(selectedEpisode)
    : null;
  const currentRoundJob =
    data.jobs.find((job) => job.roundId === round?.id) ??
    data.jobs.find((job) => job.kind === "round_generation");
  const roundJob = activeOrLatestJob(data.jobs) ?? currentRoundJob;
  const jobResult = parseJobResult(roundJob);
  const tokenSummary = runtimeTokenSummary(runtime?.llm_calls);
  const totalTokens = tokenSummary.totalTokens;
  const runtimeMs = runtime?.total_duration_ms ?? jobResult?.runtimeMs ?? null;
  const llmCalls = runtime?.llm_calls?.length ?? jobResult?.llmCalls ?? null;
  const slowestStage = runtime?.stages?.length
    ? [...runtime.stages].sort((a, b) => b.duration_ms - a.duration_ms)[0]
    : null;

  const projectDone = data.project.status === "done";
  const projectPaused = data.project.status === "paused";
  const projectMeta = parseProjectMeta(data.project);
  const projectQualityGate = projectMeta.control?.qualityGate;
  const runAllEnabled =
    projectMeta.control?.runAll?.enabled === true && !projectDone;
  const reachedTarget =
    (context?.current_episode ?? 0) >= data.project.targetEpisodeCount ||
    visibleScriptCount(projectEpisodes) >= data.project.targetEpisodeCount;
  const expectedEpisodeCount =
    Math.max(data.project.targetEpisodeCount, eps.at(-1)?.epNum ?? 0, 1);
  const visibleEpisodeCount = visibleScriptCount(eps);
  const currentRoundVisibleEpisodeCount = visibleScriptCount(roundEpisodes);
  const currentRoundExpectedEpisodeCount =
    episodeCountFromRange(round?.epRange) ?? Math.max(roundEpisodes.length, 1);
  const latestRoundDone = latestRound?.status === "done";
  const nextRoundNum = (latestRound?.roundNum ?? roundNum) + 1;
  const episodeProgress = Math.round(
    (visibleEpisodeCount / Math.max(expectedEpisodeCount, 1)) * 100
  );
  const rawQualityAverage = quality
    ? Object.values(quality.scores).reduce((sum, value) => sum + value, 0) /
      Math.max(Object.values(quality.scores).length, 1)
    : null;
  const creativeQualityScore =
    rawQualityAverage == null ? null : clampQualityScore(rawQualityAverage);
  const selectedEpisodeCode = selectedEpisode
    ? `E${String(selectedEpisode.epNum).padStart(2, "0")}`
    : "E--";
  const qualityStatusLabel = qualityStatusText(quality?.status);
  const projectStatusLabel = projectQualityGate?.status
    ? qualityStatusText(projectQualityGate.status)
    : data.project.status;
  const projectStatusBadgeClassName = projectQualityGate?.status
    ? "border-amber-200 bg-amber-50 text-amber-700"
    : undefined;
  const qualityBadgeClassName =
    quality?.status === "needs_human_review"
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : undefined;
  const workerStatusLabel = roundJob ? jobLabel(roundJob) : "暂无任务";
  const hasGenerationMetrics =
    runtime || jobResult?.runtimeMs != null || jobResult?.llmCalls != null;
  const exportProjectName = data.project.name || "novel-to-drama";
  const methodologyCards =
    methodologyContext?.cards ??
    jobResult?.methodologyCards?.map((name, index) => ({
      id: `job-methodology-${index}`,
      name,
      category: "runtime",
      trigger: "",
      generation_rule: "",
      quality_rule: "",
    })) ??
    [];
  const scoreEntries = quality
    ? Object.entries(quality.scores).map(([key, value]) => ({
        key,
        label: qualityLabels[key] ?? key,
        value,
      }))
    : [];
  const sourceFidelityScore =
    adaptationQuality?.source_fidelity?.score != null
      ? Math.max(0, Math.min(10, Math.floor(adaptationQuality.source_fidelity.score / 10)))
      : null;
  const sourceEvidenceScore =
    sourceEvidence?.coverage_score != null
      ? clampQualityScore(sourceEvidence.coverage_score / 10)
      : null;
  const dramaSourceScore =
    dramaQuality?.dimensions?.find(
      (dimension) => dimension.name === "source_asset_preservation"
    )?.score ?? null;
  const effectiveSourceScore = [
    sourceFidelityScore,
    sourceEvidenceScore,
    dramaSourceScore,
  ]
    .filter((value): value is number => typeof value === "number")
    .reduce<number | null>(
      (minimum, value) =>
        minimum == null ? clampQualityScore(value) : Math.min(minimum, clampQualityScore(value)),
      null
    );
  const roundGateScore =
    creativeQualityScore == null
      ? null
      : Math.min(
          creativeQualityScore,
          effectiveSourceScore ?? creativeQualityScore
        );
  const sourceDisplayScore = effectiveSourceScore ?? sourceFidelityScore;

  async function nextRound() {
    setBusyAction("next-round");
    setActionMessage(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/rounds/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: Number(selectedEpisodesPerRound),
          llmModel: selectedLlmModel,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const payload = (await res.json()) as { roundNum?: number };
      window.location.href = `/projects/${projectId}/rounds/${
        payload.roundNum ?? roundNum + 1
      }`;
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function retryJob(jobId: string) {
    const actionName = `retry-${jobId}`;
    setBusyAction(actionName);
    setActionMessage(null);
    try {
      const res = await fetch(`/api/jobs/${jobId}/retry`, { method: "POST" });
      let payload: { error?: string } | null = null;
      try {
        payload = (await res.json()) as { error?: string };
      } catch {
        payload = null;
      }
      if (!res.ok) throw new Error(payload?.error ?? "任务重试失败");
      await loadProjectData();
      setPollKey((value) => value + 1);
      setActionMessage("任务已重新排队");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function cloneProject() {
    setBusyAction("clone");
    setActionMessage(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: Number(selectedEpisodesPerRound),
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as {
        id?: string;
        roundNum?: number;
        error?: string;
      };
      if (!res.ok || !payload.id) {
        throw new Error(payload.error ?? "复制项目失败");
      }
      window.location.href = `/projects/${payload.id}/rounds/${
        payload.roundNum ?? 1
      }`;
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function controlProject(
    action: "pause" | "resume" | "run_all" | "stop_run_all"
  ) {
    const actionName = `project-${action}`;
    setBusyAction(actionName);
    setActionMessage(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: action === "run_all" ? 5 : Number(selectedEpisodesPerRound),
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as { error?: string };
      if (!res.ok) throw new Error(payload.error ?? "项目控制失败");
      await loadProjectData();
      setPollKey((value) => value + 1);
      if (action === "pause") setActionMessage("项目已暂停");
      if (action === "resume") setActionMessage("项目已继续");
      if (action === "run_all") setActionMessage("已开启批量运行");
      if (action === "stop_run_all") setActionMessage("已停止批量运行");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function runAction(name: string, action: () => Promise<string>) {
    setBusyAction(name);
    setActionMessage(null);
    try {
      setActionMessage(await action());
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function checkDelivery() {
    const res = await fetch(`/api/projects/${projectId}/delivery?round=${roundNum}`);
    if (!res.ok) throw new Error(await res.text());
    const report = (await res.json()) as DeliveryPreflight;
    setDelivery(report);
    return report.ready ? "交付预检通过" : "交付预检有 warning";
  }

  async function exportVideoBrief() {
    const res = await fetch(`/api/projects/${projectId}/video-brief?round=${roundNum}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());
    setPollKey((value) => value + 1);
    return "视频 brief 导出已排队";
  }

  async function exportLocalization() {
    const res = await fetch(
      `/api/projects/${projectId}/localization?round=${roundNum}&profile=${selectedProfile}`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(await res.text());
    setPollKey((value) => value + 1);
    const profile = profiles.find((item) => item.id === selectedProfile);
    return `${profile?.label ?? selectedProfile} 本地化包导出已排队`;
  }

  async function exportDeliveryPackage() {
    const res = await fetch(
      `/api/projects/${projectId}/export?round=${roundNum}&allowIssues=1`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(await res.text());
    setPollKey((value) => value + 1);
    return "交付包导出已排队";
  }

  async function copySelectedScript() {
    if (!selectedEpisode?.scriptTxt) return;
    try {
      await copyText(selectedEpisode.scriptTxt);
      setActionMessage(`第 ${selectedEpisode.epNum} 集脚本已复制`);
    } catch {
      setActionMessage("复制失败，请直接选中文本复制");
    }
  }

  async function downloadNovelExport(format: "txt" | "word") {
    const actionName = `novel-export-${format}`;
    setBusyAction(actionName);
    setActionMessage(null);
    try {
      const res = await fetch(
        `/api/projects/${projectId}/novel-export?format=${format}`
      );
      if (!res.ok) {
        throw new Error(await readResponseError(res, "导出失败"));
      }
      const blob = await res.blob();
      const ext = format === "word" ? "docx" : "txt";
      const fallback = `${exportProjectName}.${ext}`;
      const filename = filenameFromDisposition(
        res.headers.get("content-disposition"),
        fallback
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setActionMessage(format === "word" ? "Word 已开始下载" : "TXT 已开始下载");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function analyzeImpact() {
    if (!selectedEpisode) return;
    setBusyAction("impact");
    setActionMessage(null);
    try {
      const res = await fetch(`/api/episodes/${selectedEpisode.id}/impact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          editedScriptText: impactDraft,
          applyEdit: true,
          optimizeDownstream: true,
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as EditImpactReport & { error?: string };
      if (!res.ok) throw new Error(payload.error ?? "编辑影响分析失败");
      setImpactReport(payload);
      await loadProjectData();
      setPollKey((value) => value + 1);
      if (payload.applied) {
        const optimizedCount =
          payload.optimizedEpisodes?.filter((item) => item.status === "optimized")
            .length ?? 0;
        setActionMessage(
          optimizedCount > 0
            ? `已应用当前集改稿，并优化 ${optimizedCount} 个后续承接剧集`
            : "已应用当前集改稿，后续承接要求已写入系统上下文"
        );
      }
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function optimizeSelectedEpisode() {
    if (!selectedEpisode?.scriptTxt) return;
    setBusyAction("episode-optimize");
    setActionMessage(null);
    try {
      const res = await fetch(`/api/episodes/${selectedEpisode.id}/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: episodeOptimizeInstruction,
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as {
        scriptTxt?: string;
        error?: string;
      };
      if (!res.ok) throw new Error(payload.error ?? "AI 优化失败");
      if (payload.scriptTxt) {
        setImpactDraft(payload.scriptTxt);
      }
      await loadProjectData();
      setPollKey((value) => value + 1);
      setActionMessage(`第 ${selectedEpisode.epNum} 集已完成 AI 优化，状态已标记为待复核`);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="page-shell round-page">
      <header className="round-hero">
        <div className="round-hero-main">
          <div className="page-kicker">
            {`Round ${roundNum} · ${round?.epRange ?? "等待轮次"} · 全剧已输出 ${visibleEpisodeCount}/${expectedEpisodeCount} 集`}{" "}
            · 目标 {data.project.targetEpisodeCount} 集
          </div>
          <h1 className="page-title">{data.project.name} · 剧集工作台</h1>
          <div className="round-hero-meta">
            <Badge
              variant={projectPaused || projectQualityGate ? "outline" : "default"}
              className={projectStatusBadgeClassName}
            >
              {projectStatusLabel}
            </Badge>
            <Badge variant="outline">
              第 {roundNum} 轮 {round?.status ?? "pending"}
            </Badge>
            <Badge variant="outline">全集累计视图</Badge>
            {runAllEnabled && <Badge variant="outline">批量运行中</Badge>}
            {creativeQualityScore != null && (
              <Badge variant="outline">
                创作均分 {creativeQualityScore.toFixed(1)}
              </Badge>
            )}
            <span className="round-hero-progress">
              已输出 {visibleEpisodeCount}/{expectedEpisodeCount}
              {roundJob ? ` · ${jobLabel(roundJob)}` : ""}
            </span>
          </div>
        </div>
        <div className="round-hero-actions">
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={cloneProject}
          >
            <Copy className="size-4" />
            {busyAction === "clone" ? "复制中" : "复制项目"}
          </Button>
          <ProjectManageButton
            projectId={projectId}
            projectName={data.project.name}
            targetEpisodeCount={data.project.targetEpisodeCount}
            status={data.project.status}
            deleteRedirectHref="/"
            onUpdated={() => {
              void loadProjectData();
            }}
          />
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={() => downloadNovelExport("txt")}
          >
            <Download className="size-4" />
            {busyAction === "novel-export-txt" ? "导出中" : "导出TXT"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={() => downloadNovelExport("word")}
          >
            <Download className="size-4" />
            {busyAction === "novel-export-word" ? "导出中" : "导出Word"}
          </Button>
          {projectPaused ? (
            <Button
              size="sm"
              disabled={busyAction !== null}
              onClick={() => controlProject("resume")}
            >
              <Play className="size-4" />
              {busyAction === "project-resume" ? "处理中" : "继续项目"}
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled={busyAction !== null || projectDone}
              onClick={() => controlProject("pause")}
            >
              <Pause className="size-4" />
              {busyAction === "project-pause" ? "处理中" : "暂停项目"}
            </Button>
          )}
          {runAllEnabled ? (
            <Button
              variant="outline"
              size="sm"
              disabled={busyAction !== null}
              onClick={() => controlProject("stop_run_all")}
            >
              <Pause className="size-4" />
              {busyAction === "project-stop_run_all" ? "处理中" : "停止批量运行"}
            </Button>
          ) : (
            <Button
              size="sm"
              disabled={busyAction !== null || projectDone || reachedTarget}
              onClick={() => controlProject("run_all")}
            >
              <Play className="size-4" />
              {busyAction === "project-run_all" ? "启动中" : "批量运行 · 每轮5集"}
            </Button>
          )}
        </div>
      </header>

      {actionMessage && (
        <div className="status-line round-action-message">{actionMessage}</div>
      )}

      <section className="round-status-strip" aria-label="轮次概览">
        <div className="round-status-cell" data-primary="true">
          <span className="round-status-icon">
            <FileText className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">当前查看</span>
            <strong>{selectedEpisodeCode}</strong>
            <span>{selectedTitle}</span>
          </span>
        </div>
        <div className="round-status-cell">
          <span className="round-status-icon">
            <ListVideo className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">轮次进度</span>
            <strong>
              {visibleEpisodeCount}/{expectedEpisodeCount}
            </strong>
            <span>
              全剧 {episodeProgress}% 已写出 · 本轮{" "}
              {currentRoundVisibleEpisodeCount}/{currentRoundExpectedEpisodeCount}
            </span>
          </span>
        </div>
        <div className="round-status-cell">
          <span className="round-status-icon">
            <Activity className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">Worker</span>
            <strong>{workerStatusLabel}</strong>
            <span>{roundJob?.message ?? "等待任务更新"}</span>
          </span>
        </div>
        <div className="round-status-cell">
          <span className="round-status-icon">
            <Gauge className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">质量门禁</span>
            <strong>
              {roundGateScore != null ? roundGateScore.toFixed(1) : "-"}
            </strong>
            <span>{qualityStatusLabel}</span>
          </span>
        </div>
      </section>

      <section className="round-workbench">
        <Card className="round-episode-panel">
          <div className="round-panel-head">
            <div>
              <div className="round-panel-title">
                <ListVideo className="size-4" />
                全集
              </div>
              <div className="round-panel-sub">
                全剧已输出 {visibleEpisodeCount}/{expectedEpisodeCount} 集
              </div>
            </div>
            <Badge variant="outline">{episodeProgress}%</Badge>
          </div>
          <Progress value={episodeProgress} />
          {eps.length === 0 ? (
            <div className="round-empty">
              <ScrollText className="size-5" />
              worker 开始写出单集后会显示在这里
            </div>
          ) : (
            <div className="round-episode-list">
              {eps.map((ep) => {
                const selected = selectedEpisode?.id === ep.id;
                const display = episodeDisplay(ep);
                return (
                  <button
                    key={ep.id}
                    type="button"
                    className="round-episode-item"
                    data-selected={selected}
                    data-tone={display.tone}
                    onClick={() => setSelectedEpisodeNum(ep.epNum)}
                  >
                    <span className="round-episode-index">
                      E{String(ep.epNum).padStart(2, "0")}
                    </span>
                    <span className="round-episode-copy">
                      <span className="round-episode-title">
                        {extractEpisodeTitle(ep)}
                      </span>
                      <span className="round-episode-meta">
                        {display.label}
                        {ep.score != null ? ` · ${ep.score.toFixed(1)} 分` : ""}
                        {ep.retryCount > 0 ? ` · 重试 ${ep.retryCount}` : ""}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="round-script-panel">
          <div className="round-script-head">
            <div className="min-w-0">
              <div className="round-script-kicker">当前剧本</div>
              <h2>{selectedTitle}</h2>
              {selectedEpisode && selectedEpisodeDisplay && (
                <div className="round-script-meta">
                  <Badge
                    variant={selectedEpisodeDisplay.badgeVariant}
                    className={selectedEpisodeDisplay.badgeClassName}
                  >
                    {selectedEpisodeDisplay.label}
                  </Badge>
                  {selectedEpisode.score != null && (
                    <span>{selectedEpisode.score.toFixed(1)} 分</span>
                  )}
                  <span>{scriptLineCount(selectedEpisode)} 行</span>
                </div>
              )}
            </div>
            <div className="round-script-actions">
              <Button
                variant="outline"
                size="sm"
                disabled={!selectedEpisode?.scriptTxt || busyAction !== null}
                onClick={optimizeSelectedEpisode}
              >
                <Sparkles className="size-4" />
                {busyAction === "episode-optimize" ? "优化中" : "AI优化"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!selectedEpisode?.scriptTxt}
                onClick={copySelectedScript}
              >
                <Copy className="size-4" />
                复制脚本
              </Button>
            </div>
          </div>

          {selectedEpisode?.scriptTxt && (
            <div className="round-optimize-box">
              <label htmlFor="episode-optimize-instruction">
                AI 修改意见
              </label>
              <textarea
                id="episode-optimize-instruction"
                className="round-optimize-input"
                value={episodeOptimizeInstruction}
                onChange={(event) =>
                  setEpisodeOptimizeInstruction(event.target.value)
                }
                placeholder="例如：强化第3场情绪递进，镜头更细，女主台词更克制，不改变前后剧情。"
              />
            </div>
          )}

          {selectedEpisode?.scriptTxt ? (
            <pre className="round-script-reader">{selectedEpisode.scriptTxt}</pre>
          ) : (
            <div className="round-script-empty">
              <FileText className="size-8" />
              <div>
                <h3>还没有可展示的正片脚本</h3>
                <p>任务运行中时，这里会在单集写入后自动出现内容。</p>
              </div>
            </div>
          )}

          {selectedEpisode && (
            <div className="round-impact-box">
              <div className="round-impact-head">
                <div>
                  <div className="round-panel-title">
                    <GitCompareArrows className="size-4" />
                    编辑影响
                  </div>
                  <p>粘贴运营改过的当前集脚本，系统会保存为新基准，并优化后续开头承接和全局剧情点。</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busyAction !== null}
                  onClick={analyzeImpact}
                >
                  <GitCompareArrows className="size-4" />
                  {busyAction === "impact" ? "处理中" : "应用并分析"}
                </Button>
              </div>
              <textarea
                className="round-impact-editor"
                value={impactDraft}
                onChange={(event) => setImpactDraft(event.target.value)}
                aria-label="编辑后的当前集脚本"
              />
              {impactReport && (
                <div className="round-impact-report">
                  <div className="round-impact-summary">
                    <Badge variant={impactReport.changed ? "outline" : "default"}>
                      {impactReport.changed ? "有改动" : "无改动"}
                    </Badge>
                    <span>{impactReport.changeSummary}</span>
                  </div>
                  <div className="round-impact-action">
                    {impactReport.recommendedAction}
                  </div>
                  {impactReport.applied && (
                    <div className="round-impact-action">
                      已保存当前集改稿为新基准；后续轮次会按这版剧情承接。
                    </div>
                  )}
                  {impactReport.optimizedEpisodes?.length ? (
                    <div className="round-impact-list">
                      {impactReport.optimizedEpisodes.map((item) => (
                        <div key={`${item.id}-${item.status}`} className="round-impact-item">
                          <b>E{String(item.epNum).padStart(2, "0")}</b>
                          <span>
                            {item.status === "optimized"
                              ? "已优化承接"
                              : item.status === "failed"
                                ? `优化失败：${item.message}`
                                : item.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {impactReport.continuityInstruction && (
                    <div className="round-impact-action">
                      {impactReport.continuityInstruction}
                    </div>
                  )}
                  {impactReport.impactedEpisodes.length > 0 && (
                    <div className="round-impact-list">
                      {impactReport.impactedEpisodes.map((item) => (
                        <div key={item.id} className="round-impact-item">
                          <b>E{String(item.epNum).padStart(2, "0")}</b>
                          <span>{item.reason}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {impactReport.impactedState.length > 0 && (
                    <div className="round-impact-state">
                      {impactReport.impactedState.slice(0, 6).map((item) => (
                        <Badge key={item} variant="outline">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {impactReport.warnings.length > 0 && (
                    <div className="round-impact-state">
                      <Badge variant="outline">
                        warning {impactReport.warnings.length}
                      </Badge>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>

        <aside className="round-inspector">
          <section className="round-side-panel">
            <div className="round-panel-title">
              <Activity className="size-4" />
              Worker
            </div>
            {roundJob ? (
              <>
                <div className="round-job-row">
                  <div>
                    <div className="round-job-title">{roundJob.title}</div>
                    <div className="round-muted">
                      {roundJob.message ?? "等待状态更新"}
                    </div>
                  </div>
                  <Badge
                    variant={
                      roundJob.status === "failed" || roundJob.isStale
                        ? "destructive"
                        : "outline"
                    }
                  >
                    {jobLabel(roundJob)}
                  </Badge>
                </div>
                <Progress value={roundJob.progress} />
                <div className="round-job-foot">
                  <span>{roundJob.progress}%</span>
                  <span>{new Date(roundJob.updatedAt).toLocaleString()}</span>
                </div>
                {roundJob.retryable && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyAction !== null}
                    onClick={() => retryJob(roundJob.id)}
                  >
                    <RefreshCw className="size-4" />
                    {busyAction === `retry-${roundJob.id}`
                      ? "处理中"
                      : roundJob.isStale
                        ? "恢复队列"
                        : "重试任务"}
                  </Button>
                )}
                {roundJob.errorText && (
                  <div className="round-error">
                    <AlertCircle className="size-4" />
                    {roundJob.errorTe

... [TRUNCATED FOR REVIEW PACK] ...

```


## File: `tests/test_pipeline.py`
```
import json
import time
from typing import Any

import pytest
from pydantic import BaseModel

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import (
    AdaptationIntensity,
    EpisodeContext,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    EpisodeScript,
    GenerationVariant,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
    RoundResult,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    StoryBible,
)
from novel_drama_engine.pipeline import (
    EmptySourceError,
    InstrumentedJsonLLM,
    RepairBudget,
    RoundPipeline,
    build_run_manifest,
    fallback_episode_repair_targets,
    normalize_repair_budget,
    prompt_trace_enabled,
    quality_instruction_for_episode,
    strong_source_light_adaptation,
)
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeBeatPlanner,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
)
from novel_drama_engine.storage import ProjectStore


class RecordingLLM:
    def __init__(self, outputs: list[BaseModel | dict[str, Any] | Exception]) -> None:
        self._outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, system: str, user: str, response_model: type[BaseModel]) -> BaseModel:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "response_model": response_model,
            }
        )
        if not self._outputs:
            raise AssertionError("No static LLM output remains")
        raw = self._outputs.pop(0)
        if isinstance(raw, Exception):
            raise raw
        if isinstance(raw, response_model):
            return raw
        return response_model.model_validate(raw)


class ModelQueuedLLM:
    def __init__(self, outputs_by_model: dict[type[BaseModel], list[BaseModel]]) -> None:
        self._outputs = {
            model.__name__: list(outputs) for model, outputs in outputs_by_model.items()
        }
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, system: str, user: str, response_model: type[BaseModel]) -> BaseModel:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "response_model": response_model,
            }
        )
        outputs = self._outputs.get(response_model.__name__, [])
        if not outputs:
            raise AssertionError(f"No static LLM output remains for {response_model.__name__}")
        return outputs.pop(0)


def test_strong_source_light_protection_applies_to_drama_engine_first():
    profile = SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=9,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["原文已有强冲突，不应重构因果。"],
    )

    assert strong_source_light_adaptation(
        profile,
        GenerationVariant.DRAMA_ENGINE_FIRST,
    )


def test_prompt_trace_is_enabled_by_default_and_can_be_disabled(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_TRACE_PROMPTS", raising=False)

    assert prompt_trace_enabled()

    monkeypatch.setenv("NOVEL_DRAMA_TRACE_PROMPTS", "0")

    assert not prompt_trace_enabled()


def test_instrumented_llm_writes_running_heartbeat_for_slow_calls():
    class TinyModel(BaseModel):
        value: str

    class SlowLLM:
        def complete(
            self,
            *,
            system: str,
            user: str,
            response_model: type[BaseModel],
        ) -> BaseModel:
            time.sleep(0.22)
            return response_model.model_validate({"value": "ok"})

    updates: list[list[dict[str, Any]]] = []

    def on_update() -> None:
        updates.append([call.model_dump() for call in tracked_llm.snapshot_calls()])

    tracked_llm = InstrumentedJsonLLM(
        SlowLLM(),
        on_update=on_update,
        heartbeat_seconds=0.05,
    )
    tracked_llm.current_stage = "script_batch"

    result = tracked_llm.complete(system="system", user="user", response_model=TinyModel)

    assert result.value == "ok"
    assert len(tracked_llm.calls) == 1
    assert tracked_llm.calls[0].status == "succeeded"
    assert tracked_llm.calls[0].stage == "script_batch"
    assert any(
        update
        and update[0]["status"] == "running"
        and update[0]["response_model"] == "TinyModel"
        for update in updates
    )


def test_instrumented_llm_reports_prompt_trace():
    class TinyModel(BaseModel):
        value: str

    traces: list[dict[str, object]] = []
    tracked_llm = InstrumentedJsonLLM(
        StaticJsonLLM([{"value": "ok"}]),
        on_prompt=traces.append,
    )
    tracked_llm.current_stage = "source_analysis"

    result = tracked_llm.complete(
        system="system prompt",
        user="user prompt",
        response_model=TinyModel,
    )

    assert result.value == "ok"
    assert traces[0]["call_index"] == 0
    assert traces[0]["stage"] == "source_analysis"
    assert traces[0]["response_model"] == "TinyModel"
    assert traces[0]["system_prompt"] == "system prompt"
    assert traces[0]["user_prompt"] == "user prompt"
    assert traces[0]["system_prompt_chars"] == len("system prompt")
    assert traces[0]["user_prompt_chars"] == len("user prompt")
    assert isinstance(traces[0]["system_prompt_sha256"], str)
    assert isinstance(traces[0]["user_prompt_sha256"], str)


def test_round_services_consume_llm_outputs_in_order(happy_round_outputs):
    llm = StaticJsonLLM(happy_round_outputs)
    source = SourceParser(llm).run("林晚被赶出生日宴。")
    context = EpisodeContextResolver(llm).run("林晚被赶出生日宴。", None, source)
    bible = InternalBibleBuilder(llm).run("林晚被赶出生日宴。", source, context)
    scripts = ScriptBatchGenerator(llm).run(
        "林晚被赶出生日宴。",
        source,
        context,
        bible,
        None,
        "",
    )
    quality = ContinuityBoomChecker(llm).run(source, context, bible, scripts, None)
    next_context = StateWriter(llm).run(source, context, bible, scripts, quality, None)

    assert source.candidate_hooks == ["把她拖出去！"]
    assert context.target_episode_range == "EP01-EP05"
    assert scripts.episodes[0].hook_3s == "把她拖出去！"
    assert quality.status == "usable"
    assert next_context.current_episode == 5


def test_script_batch_generator_fills_missing_target_episodes(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    partial_batch = ScriptBatch(episodes=[full_batch.episodes[0]])
    llm = RecordingLLM([partial_batch, *full_batch.episodes[1:]])

    result = ScriptBatchGenerator(llm).run(
        "林晚被赶出生日宴。",
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [
        call["response_model"].__name__
        for call in llm.calls
    ] == ["ScriptBatch", "EpisodeScript", "EpisodeScript", "EpisodeScript", "EpisodeScript"]


def test_script_batch_generator_can_generate_episode_first(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    llm = RecordingLLM(full_batch.episodes)
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="EP01",
                source_excerpt="EP01_ONLY_SOURCE",
            ),
            EpisodeSourcePacket(
                episode=2,
                source_anchor="EP02",
                source_excerpt="EP02_ONLY_SECRET",
            ),
            EpisodeSourcePacket(
                episode=3,
                source_anchor="EP03",
                source_excerpt="EP03_ONLY_SOURCE",
            ),
            EpisodeSourcePacket(
                episode=4,
                source_anchor="EP04",
                source_excerpt="EP04_ONLY_SOURCE",
            ),
            EpisodeSourcePacket(
                episode=5,
                source_anchor="EP05",
                source_excerpt="EP05_ONLY_SOURCE",
            ),
        ],
    )

    result = ScriptBatchGenerator(llm).run_episode_batch(
        "FULL_SOURCE_SHOULD_NOT_APPEAR EP02_ONLY_SECRET",
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
        episode_source_packets=packets,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [
        call["response_model"].__name__
        for call in llm.calls
    ] == ["EpisodeScript", "EpisodeScript", "EpisodeScript", "EpisodeScript", "EpisodeScript"]
    assert "逐集优先生成模式" in llm.calls[0]["user"]
    assert "本集原文包" in llm.calls[0]["user"]
    assert "EP01_ONLY_SOURCE" in llm.calls[0]["user"]
    assert "FULL_SOURCE_SHOULD_NOT_APPEAR" not in llm.calls[0]["user"]
    assert "EP02_ONLY_SECRET" not in llm.calls[0]["user"]
    assert full_batch.episodes[0].cliffhanger in llm.calls[1]["user"]


def test_script_batch_generator_emits_each_episode_when_generated():
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    llm = RecordingLLM(full_batch.episodes)
    emitted: list[EpisodeScript] = []

    result = ScriptBatchGenerator(llm, episode_writer=emitted.append).run_episode_batch(
        "林晚被赶出生日宴。",
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [episode.episode for episode in emitted] == [1, 2, 3, 4, 5]


def test_episode_beat_planner_consumes_llm_output(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan = outputs[:4]
    llm = StaticJsonLLM([episode_plan])

    plan = EpisodeBeatPlanner(llm).run("林晚被赶出生日宴。", source, context, bible, None)

    assert plan.variant == GenerationVariant.DRAMA_ENGINE_FIRST
    assert plan.target_episode_range == "EP01-EP05"
    assert plan.episodes[0].physical_action_chain
    assert "信息差" in plan.adaptation_strategy


def test_pipeline_rejects_empty_source_before_llm_call(tmp_path):
    llm = RecordingLLM([])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    with pytest.raises(EmptySourceError):
        pipeline.run(project_id="demo", round_number=1, source_text="   ")

    assert llm.calls == []
    assert not (tmp_path / "round_001").exists()


def test_pipeline_persists_artifacts(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.script_batch.episodes[0].title == "被赶出生日宴"
    for artifact_name in [
        "source_analysis",
        "source_strength_profile",
        "episode_context",
        "story_bible",
        "episode_source_packets",
        "script_batch",
        "runtime_report",
        "run_manifest",
        "quality_report",
        "adaptation_quality_report",
        "methodology_quality_report",
        "drama_quality_report",
        "script_novelty_report",
        "source_evidence_report",
        "story_state_ledger",
        "prompt_trace_analysis",
        "round_result",
        "next_round_context",
    ]:
        assert (tmp_path / "round_001" / f"{artifact_name}.json").exists()
    assert (tmp_path / "round_001" / "creative_script.md").exists()
    assert (tmp_path / "round_001" / "shooting_script.md").exists()
    assert (tmp_path / "round_001" / "rendered_scripts.md").exists()
    assert (tmp_path / "round_001" / "script_novelty_report.md").exists()
    assert (tmp_path / "round_001" / "source_evidence_report.md").exists()
    assert (tmp_path / "round_001" / "prompt_trace_analysis.md").exists()
    assert (tmp_path / "round_001" / "raw_llm_output.jsonl").exists()
    assert result.adaptation_quality_report is not None
    assert result.methodology_quality_report is not None
    assert result.drama_quality_report is not None
    assert result.drama_quality_report.overall_score >= 7
    assert result.script_novelty_report is not None
    assert result.script_novelty_report.overall_score >= 7
    assert result.source_evidence_report is not None
    assert result.source_evidence_report.coverage_score >= 0
    assert any(item.evidence_spans for item in result.source_evidence_report.items)
    assert result.source_strength_profile is not None
    assert result.story_state_ledger is not None
    assert result.runtime_report is not None
    assert result.runtime_report.total_llm_calls == 6


def test_pipeline_source_evidence_missing_assets_downgrades_final_quality(
    tmp_path,
    happy_round_outputs,
):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(
        update={
            "source_to_episode_mapping": [
                EpisodeSourceMapping(
                    source="原文里亲哥哥突然救场。",
                    target_episode="EP01",
                    retained_assets=["亲哥哥救场"],
                    adaptation_reason="必须保留原文亲哥哥救场资产。",
                )
            ]
        },
        deep=True,
    )
    pipeline = RoundPipeline(
        llm=StaticJsonLLM([source, context, bible, scripts, quality, next_context]),
        store=ProjectStore(tmp_path),
    )

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出时，亲哥哥突然出现。",
        repair_budget="none",
    )

    assert result.source_evidence_report is not None
    assert result.source_evidence_report.missing_items == ["EP01 缺少原文资产：亲哥哥救场"]
    assert result.quality_report.status == QualityStatus.NEEDS_REWRITE
    assert any(
        issue.startswith("source_evidence:")
        for issue in result.quality_report.blocking_issues
    )


def test_pipeline_source_evidence_gap_triggers_episode_repair_before_final_gate(
    tmp_path,
    happy_round_outputs,
):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(
        update={
            "target_episode_range": "EP01-EP01",
            "source_to_episode_mapping": [
                EpisodeSourceMapping(
                    source="原文里亲哥哥突然救场。",
                    target_episode="EP01",
                    retained_assets=["亲哥哥救场"],
                    adaptation_reason="必须保留原文亲哥哥救场资产。",
                )
            ],
        },
        deep=True,
    )
    repaired_episode = scripts.episodes[0].model_copy(deep=True)
    repaired_episode.scenes[0].lines[0].text = (
        "△中近景推近林晚侧脸，亲哥哥救场挡在她身前，切到众人僵住。"
    )
    final_quality = quality.model_copy(update={"status": QualityStatus.USABLE})
    llm = RecordingLLM(
        [source, context, bible, scripts, quality, repaired_episode, final_quality, next_context]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出时，亲哥哥突然出现。",
    )

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(episode_calls) == 1
    assert "亲哥哥救场" in episode_calls[0]["user"]
    assert result.quality_report.status == QualityStatus.USABLE
    assert result.source_evidence_report is not None
    assert result.source_evidence_report.missing_items == []
    repair_packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert repair_packets[0]["source_evidence_targets"] == ["EP01 缺少原文资产：亲哥哥救场"]


def test_pipeline_drama_quality_blocker_triggers_episode_repair_before_final_gate(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(update={"target_episode_range": "EP01-EP01"}, deep=True)
    bad_episode = scripts.episodes[0].model_copy(deep=True)
    bad_episode.scenes[0].characters.extend(["周扬", "沈曼", "赵凯", "韩峥"])
    bad_episode.scenes[0].lines.extend(
        [
            SceneLine(kind="dialogue", speaker="周扬", text="我来解释。"),
            SceneLine(kind="dialogue", speaker="沈曼", text="流程都办好了。"),
            SceneLine(kind="dialogue", speaker="赵凯", text="证据在这里。"),
            SceneLine(kind="dialogue", speaker="韩峥", text="结果马上出。"),
        ]
    )
    bad_scripts = ScriptBatch(episodes=[bad_episode])
    repaired_episode = scripts.episodes[0].model_copy(deep=True)
    final_quality = quality.model_copy(update={"status": QualityStatus.USABLE})
    llm = ModelQueuedLLM(
        {
            SourceAnalysis: [source],
            EpisodeContext: [context],
            StoryBible: [bible],
            ScriptBatch: [bad_scripts],
            QualityReport: [quality, final_quality],
            EpisodeScript: [repaired_episode],
            NextRoundContext: [next_context],
        }
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=1,
        episodes_per_round=1,
    )

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(episode_calls) == 1
    assert "source_asset_preservation" in episode_calls[0]["user"]
    assert "未追踪" in episode_calls[0]["user"]
    assert (tmp_path / "round_001" / "pre_repair_drama_quality_report.json").exists()
    assert result.quality_report.status == QualityStatus.USABLE


def test_pipeline_writes_prompt_trace_when_enabled(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_TRACE_PROMPTS", "1")
    monkeypatch.delenv("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", raising=False)
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    trace_path = tmp_path / "round_001" / "prompt_trace.json"
    assert trace_path.exists()
    traces = json.loads(trace_path.read_text(encoding="utf-8"))
    assert traces[0]["stage"] == "source_analysis"
    assert traces[0]["response_model"] == "SourceAnalysis"
    assert "林晚被赶出生日宴" in traces[0]["user_prompt"]
    assert any(trace["stage"] == "script_batch" for trace in traces)
    assert all("system_prompt_sha256" in trace for trace in traces)
    analysis = json.loads(
        (tmp_path / "round_001" / "prompt_trace_analysis.json").read_text(
            encoding="utf-8"
        )
    )
    assert analysis["artifacts_present"]["prompt_trace.json"] is True
    assert analysis["total_llm_calls"] == len(traces)


def test_pipeline_persists_source_strength_profile(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.source_strength_profile is not None
    assert result.source_strength_profile.recommended_intensity in {"light", "medium", "heavy"}
    assert (tmp_path / "round_001" / "source_strength_profile.json").exists()


def test_pipeline_records_methodology_but_scripts_from_lean_source_contract(
    tmp_path,
    happy_round_outputs,
):
    llm = RecordingLLM(happy_round_outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    script_call = next(
        call for call in llm.calls if call["response_model"].__name__ == "ScriptBatch"
    )
    assert result.methodology_context is not None
    card_names = [card.name for card in result.methodology_context.cards]
    assert "强原文轻改规则" in card_names
    assert "动作行三层结构与微型叙事弧" in card_names
    assert "【P0 轻链路主输入】" in script_call["user"]
    assert "source_annotation 是首稿最高优先级基准" in script_call["user"]
    assert "episode_cut_table 决定本轮分集边界" in script_call["user"]
    assert "强原文轻改规则" not in script_call["user"]
    assert "动作行三层结构与微型叙事弧" not in script_call["user"]
    assert result.production_spec is not None
    assert result.source_annotation is not None
    assert result.episode_cut_table is not None
    assert result.runtime_report is not None
    assert "强原文轻改规则" in result.runtime_report.methodology_cards
    assert "动作行三层结构与微型叙事弧" in result.runtime_report.methodology_cards
    assert (tmp_path / "round_001" / "methodology_context.json").exists()


def test_pipeline_resumes_from_cached_round_artifacts(tmp_path, happy_round_outputs):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "source_analysis", source)
    store.write_round_artifact(1, "episode_context", context)
    store.write_round_artifact(1, "story_bible", bible)
    store.write_round_artifact(1, "script_batch", scripts)
    llm = RecordingLLM([quality, next_context])
    pipeline = RoundPipeline(llm=llm, store=store)
    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert [call["response_model"].__name__ for call in llm.calls] == [
        "QualityReport",
        "NextRoundContext",
    ]
    assert result.runtime_report is not None
    assert result.runtime_report.total_llm_calls == 2
    assert any(
        stage.name == "script_batch" and stage.status == "cached"
        for stage in result.runtime_report.stages
    )


def test_run_manifest_tracks_episode_repair_fallback_env(monkeypatch):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    llm = StaticJsonLLM([])

    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )

    assert manifest["env"]["NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK"] == "first"


def test_pipeline_ignores_cached_round_without_matching_manifest(tmp_path, happy_round_outputs):
    source, context, bible, scripts, stale_quality, stale_next_context = happy_round_outputs
    fresh_outputs = demo_round_outputs()
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "source_analysis", source)
    store.write_round_artifact(1, "episode_context", context)
    store.write_round_artifact(1, "story_bible", bible)
    store.write_round_artifact(1, "script_batch", scripts)
    store.write_round_artifact(
        1,
        "round_result",
        RoundResult(
            project_id="demo",
            round_number=1,
            source_analysis=source,
            episode_context=context,
            story_bible=bible,
            script_batch=scripts,
            quality_report=stale_quality,
            next_round_context=stale_next_context,
        ),
    )
    llm = RecordingLLM(fresh_outputs)
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.runtime_report is not None
    assert result.runtime_report.total_llm_calls > 0
    assert llm.calls
    manifest = json.loads((tmp_path / "round_001" / "run_manifest.json").read_text())
    assert manifest["cache_status"] == "completed"


def test_pipeline_reuses_prior_round_story_bible(tmp_path, happy_round_outputs):
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
        include_story_bible=False,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", prior_bible)
    llm = RecordingLLM(round_two_outputs)
    prior_manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(prior_manifest, ensure_ascii=False, indent=2),
    )
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=2,
        source_text="林晚被赶出生日宴。",
        previous_context=previous_context,
    )

    assert result.story_bible == prior_bible
    assert "StoryBible" not in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert (tmp_path / "round_002" / "story_bible.json").exists()
    assert any(
        stage.name == "story_bible" and stage.status == "cached"
        for stage in result.runtime_report.stages
    )


def test_pipeline_reuses_prior_story_bible_when_legacy_manifest_has_stale_code_or_env(
    tmp_path,
    happy_round_outputs,
):
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
        include_story_bible=False,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", prior_bible)
    llm = RecordingLLM(round_two_outputs)
    legacy_manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    legacy_manifest["code"] = {"prompts.py": "legacy-code-fingerprint"}
    legacy_manifest["env"] = {}
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(legacy_manifest, ensure_ascii=False, indent=2),
    )
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=2,
        source_text="林晚被赶出生日宴。",
        previous_context=previous_context,
    )

    assert result.story_bible == prior_bible
    assert "StoryBible" not in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert any(
        stage.name == "story_bible" and stage.status == "cached"
        for stage in result.runtime_report.stages
    )


def test_pipeline_skips_prior_round_story_bible_without_compatible_manifest(
    tmp_path,
    happy_round_outputs,
):
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    stale_bible = prior_bible.model_copy(update={"mainline": "STALE OLD BIBLE"})
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", stale_bible)
    llm = RecordingLLM(round_two_outputs)
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=2,
        source_text="林晚被赶出生日宴。",
        previous_context=previous_context,
    )

    assert result.story_bible.mainline != "STALE OLD BIBLE"
    assert "StoryBible" in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert any(
        stage.name == "story_bible" and stage.status == "succeeded"
        for stage in result.runtime_report.stages
    )


def test_pipeline_drama_engine_variant_persists_episode_plan(tmp_path):
    outputs = demo_round_outputs(include_episode_plan=True)
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        generation_variant=GenerationVariant.DRAMA_ENGINE_FIRST,
    )

    assert result.episode_plan is not None
    assert result.episode_plan.variant == GenerationVariant.DRAMA_ENGINE_FIRST
    assert result.episode_plan.episodes[0].three_pull_beats
    assert (tmp_path / "round_001" / "episode_plan.json").exists()


def test_pipeline_sanitizes_episode_plan_against_source_packets_by_default(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL", "0")
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, plan, script_batch, quality, next_context = outputs
    plan = plan.model_copy(deep=True)
    first_episode = plan.episodes[0].model_copy(
        update={
            "source_assets_to_keep": [
                "宴会公开羞辱",
                "外卖袋未来资产",
            ],
            "physical_action_chain": [
                "宴会公开羞辱中林晚被推到门口。",
                "林婉晴把外卖袋放上餐桌。",
                "傅盈盈被反手别腕。",
            ],
            "scene_dynamics": [
                "宴会公开羞辱形成压迫。",
                "厨房外卖袋成为反击道具。",
            ],
        },
        deep=True,
    )
    plan = plan.model_copy(update={"episodes": [first_episode, *plan.episodes[1:]]})
    llm = RecordingLLM([source, context, bible, plan, script_batch, quality, next_context])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="""
# 第 1 集
宴会公开羞辱。林晚被保安推到门口。

# 第 2 集
林婉晴把外卖袋放上餐桌。
""",
        generation_variant=GenerationVariant.DRAMA_ENGINE_FIRST,
    )

    sanitized_text = (
        tmp_path / "round_001" / "episode_plan_sanitized.json"
    ).read_text(encoding="utf-8")
    assert result.episode_plan is not None
    assert "外卖袋未来资产" not in sanitized_text
    first_episode_text = json.dumps(
        result.episode_plan.episodes[0].model_dump(),
        ensure_ascii=False,
    )
    assert "外卖袋放上餐桌" not in first_episode_text
    assert "反手别腕" not in first_episode_text
    assert "宴会公开羞辱" in sanitized_text


def test_pipeline_sop_full_stack_persists_upstream_plans(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True, target_episode_count=30)
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=30,
        generation_variant=GenerationVariant.SOP_FULL_STACK,
    )

    assert result.viral_asset_report is not None
    assert result.viral_asset_report.signature_scenes
    assert result.series_structure_plan is not None
    assert result.series_structure_plan.target_episode_count == 30
    assert result.series_structure_plan.episode_outlines[0].information_increment
    assert result.episode_plan is not None
    assert result.episode_plan.variant == GenerationVariant.SOP_FULL_STACK
    assert (tmp_path / "round_001" / "viral_asset_report.json").exists()
    assert (tmp_path / "round_001" / "series_structure_plan.json").exists()
    assert (tmp_path / "round_001" / "episode_plan.json").exists()


def test_pipeline_respects_configured_episodes_per_round(tmp_path):
    outputs = demo_round_outputs(
        include_sop_stack=True,
        include_episode_plan=True,
        target_episode_count=30,
        episodes_per_round=2,
    )
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=30,
        episodes_per_round=2,
        generation_variant=GenerationVariant.SOP_FULL_STACK,
    )

    episode_context_call = next(
        call for call in llm.calls if call["response_model"].__name__ == "EpisodeContext"
    )
    assert "本轮目标集数：最多 2 集" in episode_context_call["user"]
    assert result.episode_context.target_episode_range == "EP01-EP02"
    assert [episode.episode for episode in result.script_batch.episodes] == [1, 2]
    assert result.next_round_context.current_episode == 2


def test_pipeline_normalizes_malformed_episode_context_range(tmp_path, happy_round_outputs):
    outputs = list(happy_round_outputs)
    outputs[1] = outputs[1].model_copy(
        update={
            "target_episode_range": "1-5",
            "adaptation_actions": ["先写前五集"],
        }
    )
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        target_episode_count=30,
    )

    script_call = next(
        call for call in llm.calls if call["response_model"].__name__ == "ScriptBatch"
    )
    artifact_text = (tmp_path / "round_001" / "episode_context.json").read_text(
        encoding="utf-8"
    )
    assert result.episode_context.target_episode_range == "EP01-EP05"
    assert any(
        action.startswith("系统已将本轮集数范围规范为 EP01-EP05")
        for action in result.episode_context.adaptation_actions
    )
    assert '"target_episode_range": "EP01-EP05"' in artifact_text
    assert '"target_episode_range": "EP01-EP05"' in script_call["user"]


def test_quality_checker_forces_rewrite_for_underfilled_script(happy_round_outputs):
    source, context, bible = happy_round_outputs[:3]
    weak_script = ScriptBatch(
        episodes=[
            EpisodeScript(
                episode=1,
                title="过短脚本",
                hook_3s="她来了。",
                main_emotion="平",
                watch_reason="信息不足。",
                scenes=[
                    Scene(
                        heading="1-1 日-内-屋内",
                        characters=["甲", "乙"],
                        lines=[
                            SceneLine(kind="action", text="△甲站着。"),
                            SceneLine(kind="dialogue", speaker="甲", emotion="平", text="你好。"),
                            SceneLine(kind="dialogue", speaker="乙", emotion="平", text="嗯。"),
                        ],
                    )
                ],
                cliffhanger="她来了。",
                state_update={},
            )
        ]
    )
    self_reported_usable = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )

    report = ContinuityBoomChecker(StaticJsonLLM([self_reported_usable])).run(
        source,
        context,
        bible,
        weak_script,
        None,
    )

    assert report.status == QualityStatus.NEEDS_REWRITE
    assert any("too short" in issue for issue in report.blocking_issues)
    assert "双层质检" in report.rewrite_instruction


def test_pipeline_default_repair_targets_episode_without_batch_rewrite(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    failed_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["前3秒 Hook 不够强"],
        rewrite_instruction="EP01 前3秒 Hook 不够强，只修第一集开头。",
    )
    repaired_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"hook_3s": "把她拖出去！她不是林家的女儿！"},
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=8,
            continuity=10,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    outputs = outputs[:4] + [failed_quality, repaired_episode, final_quality, outputs[5]]
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.script_batch.episodes[0].hook_3s == "把她拖出去！她不是林家的女儿！"
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert result.quality_report.status == QualityStatus.USABLE
    assert len(script_calls) == 1
    assert len(episode_calls) == 1
    assert failed_quality.rewrite_instruction not in script_calls[0]["user"]
    assert failed_quality.rewrite_instruction in episode_calls[0]["user"]
    assert "current_episode_repair_packet" in episode_calls[0]["user"]
    assert "当前集旧稿是唯一文本基准" in episode_calls[0]["user"]
    assert "baseline_episode_text" in episode_calls[0]["user"]
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    repair_packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert repair_packets[0]["episode"] == 1
    assert "当前集旧稿是唯一文本基准" in repair_packets[0]["baseline_policy"]
    assert "baseline_episode_text" in repair_packets[0]
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_pre_adaptation_gate_rewrites_source_intent_drift(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    outputs = list(happy_round_outputs)
    source_analysis = outputs[0].model_copy(
        update={"candidate_hooks": [], "visual_moments": []}
    )
    episode_context = outputs[1].model_copy(
        update={
            "target_episode_range": "EP01-EP01",
            "source_to_episode_mapping": [],
            "forbidden_reveals": [],
        }
    )
    story_bible = outputs[2].model_copy(
        update={"immutable_facts": [], "forbidden_changes": []}
    )
    drift_episode = outputs[3].episodes[0].model_copy(deep=True)
    repaired_episode = outputs[3].episodes[0].model_copy(deep=True)
    drift_episode.scenes[0].lines[1].text = "你答应过我的影后呢？"
    repaired_episode.scenes[0].lines[1].text = "你给我的惊喜，是她？"
    first_script = ScriptBatch(episodes=[drift_episode])
    self_reported_usable = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    next_context = outputs[5].model_copy(update={"current_episode": 1})
    llm = RecordingLLM(
        [
            source_analysis,
            episode_context,
            story_bible,
            first_script,
            self_reported_usable,
            repaired_episode,
            final_quality,
            next_context,
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="颁奖礼暗处，路淮北低声说：给你准备了惊喜。林挽清只是僵住，没有追问。",
        target_episode_count=1,
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(script_calls) == 1
    assert len(episode_calls) == 1
    assert result.script_batch.episodes[0].scenes[0].lines[1].text == "你给我的惊喜，是她？"
    assert "主动索取" in episode_calls[0]["user"]
    assert "改编一致性阻断" in episode_calls[0]["user"]
    assert (tmp_path / "round_001" / "pre_repair_adaptation_quality.json").exists()
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()


def test_pipeline_episode_first_skips_batch_rewrite_and_repairs_by_episode(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", "1")
    outputs = list(happy_round_outputs)
    source, context, bible, first_script, _, next_context = outputs[:6]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["初版仍需逐集修复"],
        rewrite_instruction="按逐集模式补足 EP01-EP05 镜头。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        [source, context, bible]
        + first_script.episodes
        + [first_quality]
        + first_script.episodes
        + [final_quality, next_context]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.quality_report.status == QualityStatus.USABLE
    assert script_calls == []
    assert len(episode_calls) == 10
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "quality_report_before_episode_repair.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_strong_source_cost_control_blocks_fallback_repair(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True)
    source = outputs[0]
    viral_asset_report = outputs[1]
    context = outputs[2]
    bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    first_script = outputs[6]
    next_context = outputs[8]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=6,
            conflict=8,
            cliffhanger=8,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["整体仍可加强，但没有明确失败集。"],
        rewrite_instruction="增强镜头和情绪，不要改变原文核心因果。",
    )
    llm = RecordingLLM(
        [
            source,
            viral_asset_report,
            context,
            bible,
            series_structure_plan,
            episode_plan,
            first_script,
            first_quality,
            next_context,
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚在颁奖礼被公开羞辱，早已准备好解约协议。",
        generation_variant=GenerationVariant.SOP_FULL_STACK,
        repair_budget="rewrite",
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    )
    decision = (tmp_path / "round_001" / "cost_control_decision.json").read_text(
        encoding="utf-8"
    )
    skipped_stages = {
        stage.name: stage.error
        for stage in result.runtime_report.stages
        if stage.status == "skipped"
    }

    assert result.quality_report.status == QualityStatus.NEEDS_REWRITE
    assert result.runtime_report.repair_budget == RepairBudget.EPISODE
    assert len(script_calls) == 1
    assert episode_calls == []
    assert target_text.startswith("none")
    assert "strong_source_light_adaptation" in decision
    assert "script_batch_rewrite" not in {
        stage.name for stage in result.runtime_report.stages
    }
    assert skipped_stages["episode_repair"] == (
        "Strong-source cost control blocked fallback repair."
    )
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()


def test_episode_repair_fallback_defaults_to_no_speculative_repair(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", raising=False)

    assert fallback_episode_repair_targets([1, 2, 3]) == set()


def test_pipeline_strong_source_cost_control_repairs_named_episode_only(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True)
    source = outputs[0]
    viral_asset_report = outputs[1]
    context = outputs[2]
    bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    first_script = outputs[6]
    repaired_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"title": "只修第一集"},
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    next_context = outputs[8]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=6,
            conflict=8,
            cliffhanger=8,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 开场镜头不够具体。"],
        rewrite_instruction="只修 EP01 的镜头细节，其余集保持原文因果。",
    )
    llm = RecordingLLM(
        [
            source,
            viral_asset_report,
            context,
            bible,
            series_structure_plan,
            episode_plan,
            first_script,
            first_quality,
            repaired_episode,
            final_quality,
            next_context,
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚在颁奖礼被公开羞辱，早已准备好解约协议。",
        generation_variant=GenerationVariant.SOP_FULL_STACK,
        repair_budget="episode",
    )

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    )

    assert result.quality_report.status == QualityStatus.USABLE
    assert len(episode_calls) == 1
    assert result.script_batch.episodes[0].title == "只修第一集"
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert target_text == "EP01"
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_escalates_second_rewrite_to_human_review(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    repaired_episode = first_script.episodes[0].model_copy(deep=True)
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
    )
    second_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=5,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["逐集修复后仍缺少镜头密度"],
        rewrite_instruction="需要人工重构。",
    

... [TRUNCATED FOR REVIEW PACK] ...

```


## File: `tests/test_adaptation_quality.py`
```
from novel_drama_engine.adaptation_quality import (
    build_adaptation_quality_report,
    build_story_state_ledger,
    build_methodology_quality_report,
    merge_methodology_quality_into_report,
    _hook_acknowledged,
)
from novel_drama_engine.models import (
    AdaptationIntensity,
    EpisodeContext,
    EpisodeScript,
    MethodologyCard,
    MethodologyContext,
    MethodologyStage,
    MethodologyStatus,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    StoryBible,
    StoryStage,
)


def make_episode(
    episode: int = 1,
    *,
    title: str = "宴会反击",
    hook: str = "谁敢碰她一下！",
    final: str = "你到底是谁？",
    state_update=None,
) -> EpisodeScript:
    return EpisodeScript(
        episode=episode,
        title=title,
        hook_3s=hook,
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading=f"{episode}-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近林晚被推到宴会中央，宾客手机在前景抬起。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="林晚",
                        emotion="冷",
                        text=hook,
                    ),
                    SceneLine(
                        kind="action",
                        text="△特写推近旧木盒打开，半枚玉佩压在邀请函上。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="林雪",
                        emotion="慌",
                        text=final,
                    ),
                ],
            )
        ],
        cliffhanger=final,
        state_update=state_update or {"open_hook": final, "prop": "旧木盒已公开"},
    )


def make_plain_episode(
    episode: int,
    *,
    hook: str,
    final: str,
    title: str = "关键节点",
) -> EpisodeScript:
    return EpisodeScript(
        episode=episode,
        title=title,
        hook_3s=hook,
        main_emotion="紧张",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading=f"{episode}-1 夜-内-主场景",
                characters=["甲", "乙"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近甲站到灯下，乙在画面边缘抬头。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="甲",
                        emotion="冷",
                        text=hook,
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="乙",
                        emotion="震惊",
                        text=final,
                    ),
                ],
            )
        ],
        cliffhanger=final,
        state_update={"open_hook": final},
    )


def make_context() -> EpisodeContext:
    return EpisodeContext(
        target_episode_range="EP01-EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=["林晚生日宴被羞辱，旧木盒出现 -> EP01"],
        must_carry_context=[],
        forbidden_reveals=["不得提前一次性公开亲子鉴定"],
        adaptation_actions=["保留公开羞辱开场"],
        confidence=0.9,
    )


def make_source_analysis(hook: str = "谁敢碰她一下！") -> SourceAnalysis:
    return SourceAnalysis(
        characters=["林晚", "林雪"],
        events=["林晚生日宴被羞辱，旧木盒出现"],
        conflicts=["真假千金身份冲突"],
        visual_moments=["旧木盒打开"],
        low_value_passages=[],
        candidate_hooks=[hook],
    )


def make_bible() -> StoryBible:
    return StoryBible(
        genre="豪门真假千金",
        mainline="林晚在公开羞辱中逐集反击。",
        characters=["林晚", "林雪"],
        relationships=["林雪压迫林晚"],
        speech_styles={"林晚": "克制短句", "林雪": "温柔带刺"},
        immutable_facts=["林晚被公开羞辱"],
        forbidden_changes=["不得新增亲哥哥救场"],
    )


def make_next_context() -> NextRoundContext:
    return NextRoundContext(
        summary="EP01 停在林雪追问身份。",
        current_episode=1,
        open_hooks=["你到底是谁？"],
        forbidden_reveals=["亲子鉴定完整结果"],
        character_knowledge={"林晚": ["知道旧木盒能推进身份线"]},
        relationship_changes=["林晚与林雪公开对立"],
        prop_states=["旧木盒已公开"],
        foreshadowing_ledger=["玉佩将在 EP02 继续推进"],
    )


def make_strong_profile() -> SourceStrengthProfile:
    return SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=10,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["原文已有强钩子和名场面。"],
    )


def make_methodology_context() -> MethodologyContext:
    return MethodologyContext(
        source_strength_level=SourceStrengthLevel.STRONG,
        adaptation_intensity=AdaptationIntensity.LIGHT,
        cards=[
            MethodologyCard(
                id="method_card_strong_source_light_v1",
                source_id="method_source_strong_source_light_v1",
                name="强原文轻改规则",
                category="source_fidelity",
                applies_to_channel=["female"],
                applies_to_genre=["identity"],
                applies_to_stage=[MethodologyStage.QUALITY_GATE],
                trigger="原文已具备强冲突、强钩子、强反差或高情绪名场面",
                generation_rule="只做视听化、压缩和镜头补强，不改变主动方和因果顺序。",
                quality_rule="删除 C1 名场面必须 needs_rewrite。",
                negative_examples=["把原文预谋解约改成现场赌气解约"],
                status=MethodologyStatus.ACTIVE,
            )
        ],
    )


def test_adaptation_quality_blocks_dropped_original_hook():
    report = build_adaptation_quality_report(
        source_text="生日宴上，林晚被逼到角落。林雪低声说：谁敢碰她一下！",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="欢迎回来。",
                    final="旧木盒怎么会在这里？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert report.source_fidelity.preserved_original_hook is False
    assert any("original strong hook" in item for item in report.blocking_warnings)
    assert report.source_fidelity.score < 100


def test_hook_acknowledgement_requires_specific_event_overlap_not_only_shared_name():
    assert not _hook_acknowledged(
        "许念念举起提前准备好的解约协议",
        "许念念低头喝水，镜头扫过桌面。",
    )
    assert _hook_acknowledged(
        "许念念举起提前准备好的解约协议",
        "许念念从包里抽出解约协议，举到镜头前。",
    )


def test_forbidden_reveal_allows_investigation_before_identity_result():
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="鉴定结果出来前，她不会停手。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_forbidden_reveal_blocks_public_identity_result():
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="亲子鉴定结果公开，林晚才是真千金。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_forbidden_rule_does_not_block_normal_source_faithful_terms():
    bible = make_bible().model_copy(
        update={
            "forbidden_changes": [
                "严禁改变林晚解约的主动性。解约在开场就是谋划好的既定行动，决非临时赌气。",
                "严禁林晚性格软弱。面对电话纠缠时，她必须克制、冷静、坚定。",
            ]
        }
    )
    report = build_adaptation_quality_report(
        source_text="林晚早就把解约协议放在桌上。电话响起时，她克制冷静地说：合作到此为止。",
        source_analysis=make_source_analysis("合作到此为止"),
        episode_context=make_context(),
        story_bible=bible,
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="林晚早就决定解约。",
                    final="合作到此为止。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_source_fidelity_scores_required_assets_without_treating_actions_as_source():
    context = EpisodeContext(
        target_episode_range="EP01-EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "颁奖礼后台羞辱",
                "target_episode": "EP01",
                "retained_assets": "西装手部压迫、包臀裙羞辱、手机短信嘲讽",
                "information_increment": "女主身份、隐藏恋情与背叛危机",
                "adaptation_action": "将内心OS转为紧迫呼吸和局部特写",
            }
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    script = EpisodeScript(
        episode=1,
        title="颁奖台下",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北西装手部压迫林挽清，包臀裙羞辱被聚光灯扫到。",
                    ),
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
                ],
            )
        ],
        cliffhanger="手机在她掌心震动。",
        state_update={},
    )

    report = build_adaptation_quality_report(
        source_text="颁奖礼后台，路淮北用西装手臂压住她，包臀裙被迫皱起，手机后来震动。",
        source_analysis=make_source_analysis("别出声。"),
        episode_context=context,
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[script]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert report.source_fidelity.score == 67
    assert any(check.category == "source_mapping_required" for check in report.source_fidelity.checks)
    assert any(check.category == "source_mapping_context" for check in report.source_fidelity.checks)
    assert not any("将内心OS转为" in item for item in report.blocking_warnings)


def test_source_fidelity_does_not_block_current_round_on_future_episode_assets():
    context = EpisodeContext(
        target_episode_range="EP01-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "颁奖礼后台羞辱",
                "target_episode": "EP01",
                "retained_assets": "路淮北手部压迫、许念念台上领奖",
                "information_increment": "隐藏恋情与背叛危机",
                "adaptation_action": "保留开场压迫",
            },
            {
                "source": "雪地烟火激吻，照片随后被公开",
                "target_episode": "EP08",
                "retained_assets": "雪地烟火激吻、照片被公开",
                "information_increment": "后续公开关系危机",
                "adaptation_action": "未来轮次承接",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    script = EpisodeScript(
        episode=1,
        title="颁奖台下",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北", "许念念"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北手部压迫林挽清，门缝外许念念台上领奖。",
                    ),
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
                ],
            )
        ],
        cliffhanger="主持人的声音压过门缝。",
        state_update={},
    )

    report = build_adaptation_quality_report(
        source_text="颁奖礼后台，路淮北压住她。很久之后，雪地烟火下两人接吻，照片被公开。",
        source_analysis=make_source_analysis("别出声。"),
        episode_context=context,
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[script]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    warning_text = "\n".join(report.blocking_warnings)
    assert "雪地烟火激吻" not in warning_text
    assert "照片被公开" not in warning_text


def test_forbidden_change_detection_does_not_flag_broad_character_name_overlap():
    bible = make_bible()
    bible.forbidden_changes = [
        "禁止在林挽清对路淮北死心前增加暧昧戏份。",
        "严禁将路淮北写出任何洗白情节或苦衷背景。",
    ]

    report = build_adaptation_quality_report(
        source_text="林挽清被路淮北公开羞辱后冷静离开。",
        source_analysis=SourceAnalysis(
            characters=["林挽清", "路淮北"],
            events=["公开羞辱"],
            conflicts=["背叛"],
            visual_moments=[],
            low_value_passages=[],
            candidate_hooks=[],
        ),
        episode_context=EpisodeContext(
            target_episode_range="EP01-EP01",
            story_stage=StoryStage.OPENING_PRESSURE,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=bible,
        script_batch=ScriptBatch(
            episodes=[
                EpisodeScript(
                    episode=1,
                    title="冷静离开",
                    hook_3s="别碰我。",
                    main_emotion="羞辱",
                    watch_reason="系统内部看点",
                    scenes=[
                        Scene(
                            heading="1-1 夜-内-走廊",
                            characters=["林挽清", "路淮北"],
                            lines=[
                                SceneLine(
                                    kind="action",
                                    text="△中景推近林挽清绕开路淮北，指尖攥紧解约协议。",
                                ),
                                SceneLine(kind="dialogue", speaker="林挽清", emotion="冷", text="让开。"),
                            ],
                        )
                    ],
                    cliffhanger="协议被她按在桌上。",
                    state_update={},
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert report.source_fidelity.score >= 90
    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_forbidden_rule_still_blocks_concrete_added_asset():
    report = build_adaptation_quality_report(
        source_text="林晚在生日宴被羞辱，只能靠自己拿出旧木盒反击。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="她亲哥哥冲进来，替她救场。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )

def test_agency_ramp_allows_source_with_hidden_power_setup():
    report = build_adaptation_quality_report(
        source_text="赘婿叶辰被岳父一家羞辱，下一秒黑卡被银行经理亲自送到门口。",
        source_analysis=make_source_analysis("所有证据都在我手里。"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="所有证据都在我手里。",
                    final="谁还敢说他没资格？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("主角情绪/主动权递进漂移" in item for item in report.blocking_warnings)


def test_agency_ramp_ignores_other_character_question_about_prior_knowledge():
    report = build_adaptation_quality_report(
        source_text="林晚在生日宴上被当众羞辱，老管家拿着旧木盒冲进来。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="录像？你们早就知道？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("主角情绪/主动权递进漂移" in item for item in report.blocking_warnings)


def test_methodology_quality_blocks_strong_source_dropped_hook():
    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="欢迎回来。",
                    final="旧木盒怎么会在这里？",
                )
            ]
        ),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    assert methodology_report.issues
    assert methodology_report.issues[0].severity == "blocking"
    assert "原文开场钩子未被保留" in methodology_report.issues[0].message


def test_methodology_quality_does_not_force_opening_scene_after_first_round():
    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    episode=3,
                    title="第三集新推进",
                    hook="档案编号被换过！",
                    final="这份记录，为什么有顾家的章？",
                )
            ]
        ),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    assert methodology_report.issues == []


def test_methodology_quality_merge_marks_needs_rewrite():
    base_report = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(hook=8, conflict=8, cliffhanger=8, continuity=8, video_feasibility=8),
        blocking_issues=[],
        rewrite_instruction="",
    )
    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="欢迎回来。",
                    final="旧木盒怎么会在这里？",
                )
            ]
        ),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    merged = merge_methodology_quality_into_report(base_report, methodology_report)

    assert merged.status == QualityStatus.NEEDS_REWRITE
    assert merged.blocking_issues
    assert "方法论阻断" in merged.rewrite_instruction


def test_story_state_ledger_collects_episode_and_next_context_state():
    episode = make_episode()
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis(),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[episode]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    ledger = report.story_state_ledger
    assert ledger.current_episode == 1
    assert any(entry.kind == "episode_state" for entry in ledger.entries)
    assert "旧木盒已公开" in ledger.prop_states


def test_story_state_ledger_closes_previous_context_hook_when_opening_acknowledges_it():
    previous_context = make_next_context()
    previous_context.open_hooks = ["你到底是谁？"]
    episode = make_episode(hook="你到底是谁？", final="新的证据在哪？")

    ledger = build_story_state_ledger(
        script_batch=ScriptBatch(episodes=[episode]),
        next_round_context=make_next_context(),
        previous_context=previous_context,
    )

    previous_entries = [
        entry
        for entry in ledger.entries
        if entry.kind == "open_hook" and entry.source == "previous_context"
    ]
    assert previous_entries[0].status == "closed"


def test_story_state_ledger_closes_episode_hook_when_next_opening_acknowledges_it():
    first = make_episode(episode=1, final="门外的人是谁？")
    second = make_episode(
        episode=2,
        hook="门外的人是谁？",
        final="盒子里还有什么？",
    )

    ledger = build_story_state_ledger(
        script_batch=ScriptBatch(episodes=[first, second]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    first_hook = next(
        entry
        for entry in ledger.entries
        if entry.kind == "open_hook"
        and entry.source == "episode.cliffhanger"
        and entry.episode == 1
    )
    assert first_hook.status == "closed"
    assert "next_round_context open_hooks does not carry the final episode cliffhanger" in ledger.warnings


def test_continuity_blocks_forbidden_previous_reveal_leak():
    previous_context = make_next_context()
    previous_context.forbidden_reveals = ["亲子鉴定完整结果"]
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis(),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="亲子鉴定完整结果出来了。",
                    final="你到底是谁？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=previous_context,
    )

    assert any("forbidden reveal leaked" in item for item in report.blocking_warnings)


def test_continuity_allows_partial_identity_clue_without_full_reveal():
    previous_context = make_next_context()
    previous_context.forbidden_reveals = ["林晚是真千金"]
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="这块玉佩，只有真千金才有。",
                    final="她到底是不是林家人？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=previous_context,
    )

    assert not any("forbidden reveal leaked" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_passive_promise_rewritten_as_protagonist_demand():
    report = build_adaptation_quality_report(
        source_text="颁奖礼暗处，对手低声说：给你准备了惊喜。主角只是僵住，没有追问。",
        source_analysis=make_source_analysis("给你准备了惊喜"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="你答应过我的影后呢？",
                    final="你到底骗了我多久？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("主动索取" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_preplanned_decision_rewritten_as_impulse():
    report = build_adaptation_quality_report(
        source_text="她早就把解约协议放在办公室抽屉里，这是她深思熟虑后的离开。",
        source_analysis=make_source_analysis("她早就把解约协议放在办公室抽屉里"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="我现在就解约。",
                    final="这字，我当场签。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("现场冲动决定" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_removed_high_tension_opening():
    report = build_adaptation_quality_report(
        source_text=(
            "开场，她被抱坐在路淮北腿上，男人的手擦过衣服边缘。"
            "她僵住，害怕被颁奖礼镜头拍到。"
        ),
        source_analysis=make_source_analysis("害怕被颁奖礼镜头拍到"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="颁奖礼开始了。",
                    final="名单公布了。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("opening tension asset" in item for item in report.blocking_warnings)


def empty_source_analysis() -> SourceAnalysis:
    return SourceAnalysis(
        characters=["甲", "乙", "丙"],
        events=[],
        conflicts=[],
        visual_moments=[],
        low_value_passages=[],
        candidate_hooks=[],
    )


def test_story_event_ledger_blocks_repeated_high_impact_intimacy_exposure():
    report = build_adaptation_quality_report(
        source_text="公开亲密曝光是单次高价值名场面，后续只能承接后果。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP05-EP09",
            story_stage=StoryStage.MISUNDERSTANDING_ESCALATION,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    5,
                    hook="订婚宴舞台上，他低头吻住她，直播镜头亮起。",
                    final="照片已经上热搜。",
                ),
                make_episode(
                    9,
                    hook="庆典镜头前，他再次吻住她，偷拍视频曝光。",
                    final="全网又炸了。",
                ),
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP09 停在二次曝光。",
            current_episode=9,
            open_hooks=["全网又炸了。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert any("仪式化/高场面亲密节点" in item for item in report.blocking_warnings)
    assert any("亲密关系公开/曝光节点" in item for item in report.blocking_warnings)
    assert any(
        entry.kind == "story_event" and entry.key == "public_intimacy_exposure"
        for entry in report.story_state_ledger.entries
    )


def test_story_event_ledger_blocks_institutional_reckoning_without_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="机构清算线需要证据、验证、公开、后果顺序。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP10-EP10",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    10,
                    hook="公司官方发布会开启。",
                    final="全网反转，公司倒台。",
                )
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP10 机构清算。",
            current_episode=10,
            open_hooks=["全网反转，公司倒台。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert any("证据链" in item for item in report.story_state_ledger.blocking_warnings)
    assert any("证据链" in item for item in report.blocking_warnings)


def test_story_event_ledger_allows_institutional_reckoning_after_visible_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="证据先出现，再进入机构清算和舆论反转。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP08-EP09",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    8,
                    hook="录音原件和合同已经公证。",
                    final="律师函递出。",
                ),
                make_plain_episode(
                    9,
                    hook="公司官方发布会开启。",
                    final="全网反转，公司倒台。",
                ),
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP09 机构清算。",
            current_episode=9,
            open_hooks=["全网反转，公司倒台。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert not any("证据链" in item for item in report.blocking_warnings)


def test_story_event_ledger_blocks_identity_reveal_without_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="身份结论公开需要可见证据链。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP06-EP06",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    6,
                    hook="全场公开他的真实身份。",
                    final="少主身份终于坐实。",
                )
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP06 身份公开。",
            current_episode=6,
            open_hooks=["少主身份终于坐实。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert any("身份/真相结论公开" in item for item in report.blocking_warnings)
    assert any("证据链" in item for item in report.blocking_warnings)


def test_story_event_ledger_allows_identity_reveal_after_visible_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="身份结论由令牌和鉴定书支撑。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP05-EP06",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    5,
                    hook="祖传令牌和鉴定书同时亮出。",
                    final="长老要求当众验证。",
                ),
                make_plain_episode(
                    6,
                    hook="全场公开他的真实身份。",
                    final="少主身份终于坐实。",
                ),
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP06 身份公开。",
            current_episode=6,
            open_hooks=["少主身份终于坐实。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=["祖传令牌和鉴定书已公开"],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert not any("身份/真相结论公开" in item for item in report.blocking_warnings)


def character_agency_source_analysis() -> SourceAnalysis:
    return SourceAnalysis(
        characters=["主角", "对手", "支持者"],
        events=["主角在公开压迫中僵住，随后逐步清醒"],
        conflicts=["主角被对手持续压迫"],
        visual_moments=[],
        low_value_passages=[],
        candidate_hooks=[],
    )


def character_agency_bible() -> StoryBible:
    return StoryBible(
        genre="通用强冲突短剧",
        mainline="主角在压迫中逐步清醒并反击。",
        characters=["主角", "对手", "支持者"],
        relationships=["对手持续压迫主角", "支持者给主角后盾"],
        speech_styles={"主角": "克制短句", "对手": "直白施压", "支持者": "短句给后盾"},
        immutable_facts=["主角经历公开压迫"],
        forbidden_changes=["不得让支持者替主角完成核心决定"],
    )


def test_source_fidelity_blocks_early_omniscient_counterattack_when_source_is_vulnerable():
    report = build_adaptation_quality_report(
        source_text="开场主角被公开羞辱，僵住，手指发抖。她没有立刻反击，只是在心碎后逐步清醒。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="我早就知道你们完了。",
                    final="所有证据都在我手里。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("全知全能式开杀" in item for item in report.blocking_warnings)
    assert any(check.category == "agency_ramp" for check in report.source_fidelity.checks)


def test_source_fidelity_allows_omniscient_counterattack_when_source_has_preexisting_power():
    report = build_adaptation_quality_report(
        source_text="主角重生归来，早就知道对手设局，也提前布好证据。她曾被羞辱，这一次要主动破局。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="我早就知道你们完了。",
                    final="所有证据都在我手里。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("全知全能式开杀" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_support_role_taking_over_protagonist_choice():
    report = build_adaptation_quality_report(
        source_text="主角必须自己做离开决定，支持者只能递证据和兜底。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="你不用出面，剩下交给我。",
                    final="我已经替你签了。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("支持型角色主动权越界" in item for item in report.blocking_warnings)
    assert any(check.category == "support_role_boundary" for check in report.source_fidelity.checks)


def test_source_fidelity_allows_support_role_giving_choice_and_backing():
    report = build_adaptation_quality_report(
        source_text="主角必须自己做离开决定，支持者只能递证据和兜底。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="证据给你，你自己决定。",
                    final="我给你撑腰。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("支持型角色主动权越界" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_passive_opponent_without_countermove():
    report = build_adaptation_quality_report(
        source_text="对手一直主动压迫主角，后续必须有反制。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="反派脸色发白，躲在角落发抖。",
                    final="反派不敢说话。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("对手行动线空心" in item for item in report.blocking_warnings)
    assert any(check.category == "opponent_agency" for check in report.source_fidelity.checks)


def test_source_fidelity_allows_opponent_with_active_countermove():
    report = build_adaptation_quality_report(
        source_text="对手一直主动压迫主角，后续必须有反制。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="反派买通媒体，删掉监控。",
                    final="他威胁证人改口。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("对手行动线空心" in item for item in report.blocking_warnings)

```


## File: `tests/test_source_evidence.py`
```
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    Scene,
    SceneLine,
    ScriptBatch,
    QualityReport,
    QualityScores,
    QualityStatus,
)
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
    merge_source_evidence_into_quality_report,
    render_source_evidence_report,
)


def test_source_evidence_report_matches_retained_assets_in_script():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="生日宴上，林晚被拖出去，老管家跪下叫大小姐。",
                source_excerpt="林晚在生日宴被顾承赶出，老管家抱着旧木盒跪下叫她大小姐。",
                c1_must_keep_assets=["老管家", "大小姐", "旧木盒"],
                c2_visual_assets=["宴会厅侧门"],
            )
        ]
    )

    report = build_source_evidence_report(
        script_batch,
        episode_source_packets=packets,
    )

    assert report.coverage_score == 100
    assert report.items[0].status == "matched"
    assert report.items[0].source_anchor.startswith("生日宴")
    assert "保留原文必留资产" in report.items[0].adaptation_reason
    assert any("老管家" in line or "大小姐" in line for line in report.items[0].script_evidence)

    markdown = render_source_evidence_report(report)
    assert "Source Evidence Report" in markdown
    assert "EP01" in markdown
    assert "旧木盒" in markdown


def test_source_evidence_report_flags_missing_source_assets():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="原文里亲哥哥突然救场。",
                source_excerpt="林晚被赶出时，亲哥哥突然出现。",
                c1_must_keep_assets=["亲哥哥救场"],
            )
        ]
    )

    report = build_source_evidence_report(
        script_batch,
        episode_source_packets=packets,
    )

    assert report.coverage_score == 0
    assert report.items[0].status == "missing"
    assert report.items[0].script_evidence == []
    assert report.missing_items == ["EP01 缺少原文资产：亲哥哥救场"]
    assert "原文证据未落到正片" in report.rewrite_instruction


def test_source_evidence_does_not_block_on_observational_anchor_only():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="林晚在生日宴上被当众羞辱。 -> EP01-EP05",
        source_excerpt="林晚在生日宴上被当众羞辱。",
    )
    script = EpisodeScript(
        episode=1,
        title="身份线推进",
        hook_3s="鉴定报告出来了。",
        main_emotion="反转",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-鉴定中心",
                characters=["林晚"],
                lines=[
                    SceneLine(kind="action", text="△中景推近鉴定报告，林晚指尖停在姓名栏。"),
                ],
            )
        ],
        cliffhanger="报告被人抽走。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].status == "missing"
    assert report.missing_items == []
    assert report.rewrite_instruction == ""


def test_source_evidence_tracks_soft_c1_assets_without_blocking_rewrite():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="EP01 当前集原文",
        source_excerpt="宴会公开羞辱。林晚被保安推到门口。",
        c1_must_keep_assets=["宴会公开羞辱"],
        source_evidence_assets=[],
    )
    script = EpisodeScript(
        episode=1,
        title="被赶出生日宴",
        hook_3s="滚出去。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-宴会厅",
                characters=["林晚"],
                lines=[
                    SceneLine(kind="action", text="△中景林晚被保安推到门口。"),
                ],
            )
        ],
        cliffhanger="门外脚步声逼近。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.items[0].evidence_spans
    assert report.missing_items == []
    assert report.rewrite_instruction == ""


def test_source_evidence_missing_assets_downgrades_quality_report():
    script_batch = demo_round_outputs()[3]
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="原文里亲哥哥突然救场。",
                source_excerpt="林晚被赶出时，亲哥哥突然出现。",
                c1_must_keep_assets=["亲哥哥救场"],
            )
        ]
    )
    source_evidence_report = build_source_evidence_report(
        script_batch,
        episode_source_packets=packets,
    )
    quality_report = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )

    merged = merge_source_evidence_into_quality_report(
        quality_report,
        source_evidence_report,
    )

    assert merged.status == QualityStatus.NEEDS_REWRITE
    assert any(issue.startswith("source_evidence:") for issue in merged.blocking_issues)
    assert "亲哥哥救场" in merged.rewrite_instruction


def test_source_evidence_scores_each_asset_not_only_episode_hit():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="颁奖礼后台羞辱",
        source_excerpt="林挽清被藏在后台，路淮北把手探进她礼服。许念念在台上举起奖杯。",
        c1_must_keep_assets=["路淮北把手探进她礼服", "许念念在台上举起奖杯"],
    )
    script = EpisodeScript(
        episode=1,
        title="后台羞辱",
        hook_3s="别出声。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北的手探进林挽清礼服腰侧，舞台掌声从门缝灌进来。",
                    ),
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
                ],
            )
        ],
        cliffhanger="别出声。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 50
    assert report.items[0].status == "partial"
    assert any("许念念在台上举起奖杯" in item for item in report.missing_items)
    assert len(report.items[0].evidence_spans) == 2
    assert [span.status for span in report.items[0].evidence_spans] == [
        "matched",
        "missing",
    ]


def test_source_evidence_skips_packets_without_current_episode_script():
    script = EpisodeScript(
        episode=1,
        title="颁奖台下",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北手部压迫林挽清，门缝外掌声涌进来。",
                    )
                ],
            )
        ],
        cliffhanger="主持人的声音压过门缝。",
        state_update={},
    )
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=8,
                source_anchor="雪地烟火激吻，照片随后被公开。",
                source_excerpt="雪地烟火下两人接吻，照片被公开。",
                source_evidence_assets=["雪地烟火激吻", "照片被公开"],
            )
        ]
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=packets,
    )

    assert report.coverage_score == 100
    assert report.items == []
    assert report.missing_items == []
    assert report.rewrite_instruction == ""


def test_source_evidence_does_not_block_on_visual_methodology_actions():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="颁奖礼后台羞辱",
        source_excerpt="林挽清被藏在后台，路淮北把手探进她礼服。",
        c1_must_keep_assets=["路淮北把手探进她礼服"],
        c2_visual_assets=[
            "将内心OS转为紧迫的呼吸动作与镜头的局部特写，强化被公开处刑的耻辱感"
        ],
    )
    script = EpisodeScript(
        episode=1,
        title="后台羞辱",
        hook_3s="别出声。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北的手探进林挽清礼服腰侧，林挽清屏住呼吸。",
                    ),
                ],
            )
        ],
        cliffhanger="主持人的声音压过后台。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 100
    assert report.missing_items == []
    assert "将内心OS转为" not in "；".join(report.missing_items)
    assert len(report.items[0].evidence_spans) == 1


def test_source_evidence_requires_specific_asset_not_only_character_name():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="许念念早已把解约协议放进包里。",
        source_excerpt="许念念走进办公室，举起提前准备好的解约协议。",
        c1_must_keep_assets=["许念念举起提前准备好的解约协议"],
    )
    script = EpisodeScript(
        episode=1,
        title="办公室对峙",
        hook_3s="门被推开。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-办公室",
                characters=["许念念"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近许念念低头喝水，桌面没有任何文件。",
                    )
                ],
            )
        ],
        cliffhanger="门外传来脚步声。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert report.coverage_score == 0
    assert report.items[0].status == "missing"
    assert report.items[0].script_evidence == []

    script.scenes[0].lines[0].text = "△中景推近许念念从包里抽出解约协议，举到镜头前。"
    matched_report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    assert matched_report.coverage_score == 100
    assert matched_report.items[0].status == "matched"


def test_source_evidence_records_source_span_script_line_and_reason_per_asset():
    packet = EpisodeSourcePacket(
        episode=1,
        source_anchor="办公室解约",
        source_excerpt=(
            "许念念早已把解约协议放进包里。\n"
            "她走进办公室，举起提前准备好的解约协议。"
        ),
        c1_must_keep_assets=["许念念举起提前准备好的解约协议"],
    )
    script = EpisodeScript(
        episode=1,
        title="办公室对峙",
        hook_3s="门被推开。",
        main_emotion="压迫",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 日-内-办公室",
                characters=["许念念"],
                lines=[
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="冷", text="你想清楚。"),
                    SceneLine(
                        kind="action",
                        text="△中景推近许念念从包里抽出解约协议，举到镜头前。",
                    ),
                ],
            )
        ],
        cliffhanger="她把笔压在纸上。",
        state_update={},
    )

    report = build_source_evidence_report(
        ScriptBatch(episodes=[script]),
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    span = report.items[0].evidence_spans[0]
    assert span.asset == "许念念举起提前准备好的解约协议"
    assert span.status == "matched"
    assert span.source_anchor == "办公室解约"
    assert span.source_excerpt == packet.source_excerpt
    assert span.source_line == "她走进办公室，举起提前准备好的解约协议。"
    assert span.source_line_index == 2
    assert span.script_line == "△中景推近许念念从包里抽出解约协议，举到镜头前。"
    assert span.script_line_index == 7
    assert span.adaptation_reason.startswith("保留原文必留资产")

    markdown = render_source_evidence_report(report)
    assert "Source Span Evidence" in markdown
    assert "source L2" in markdown
    assert "script L7" in markdown

```


## File: `tests/test_script_quality.py`
```
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
)
from novel_drama_engine.script_quality import (
    build_script_novelty_report,
    build_current_episode_repair_packet,
    cliffhanger_field_is_performed,
    episode_needs_hook_dialogue_polish,
    episode_quality_metrics,
    episode_quality_warnings,
    has_action_line_template,
    episode_repair_instruction,
    has_abnormal_repetition,
    has_executable_shot_language,
    has_explanatory_cliffhanger,
    hook_dialogue_polish_instruction,
    merge_script_novelty_into_quality_report,
    render_script_novelty_report,
    script_batch_quality_warnings,
    episode_repair_mode,
)


def test_happy_demo_outputs_meet_reference_script_density(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    for episode in script_batch.episodes:
        metrics = episode_quality_metrics(episode)
        assert metrics.chars >= 800
        assert metrics.scenes >= 2
        assert metrics.total_scene_lines >= 28
        assert metrics.action_lines >= 10
        assert metrics.voiced_lines >= 18
        assert metrics.shot_language_lines >= 8
        assert metrics.invalid_action_format_lines == 0
        assert metrics.long_voiced_lines == 0
        assert metrics.invalid_scene_headings == 0
        assert episode_quality_warnings(episode) == []


def test_happy_demo_outputs_pass_cross_episode_novelty_gate(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    report = build_script_novelty_report(script_batch)

    assert report.overall_score >= 7
    assert report.blocking_issues == []
    assert render_script_novelty_report(report).startswith("# Script Novelty Report")


def test_cross_episode_novelty_gate_blocks_repeated_episode_batch(happy_round_outputs):
    source_episode = happy_round_outputs[3].episodes[0]
    script_batch = ScriptBatch(
        episodes=[
            source_episode.model_copy(update={"episode": 1, "title": "重复样本 A"}, deep=True),
            source_episode.model_copy(update={"episode": 2, "title": "重复样本 B"}, deep=True),
            source_episode.model_copy(update={"episode": 3, "title": "重复样本 C"}, deep=True),
        ]
    )

    report = build_script_novelty_report(script_batch)

    assert report.overall_score < 7
    assert report.blocking_issues
    assert any(
        issue.kind in {"overall", "scene_skeleton", "action_chain"}
        and issue.severity == "blocking"
        for issue in report.similarity_issues
    )
    assert "跨集新鲜度不足" in report.rewrite_instruction


def test_cross_episode_novelty_gate_downgrades_usable_quality_report(happy_round_outputs):
    source_episode = happy_round_outputs[3].episodes[0]
    repeated_batch = ScriptBatch(
        episodes=[
            source_episode.model_copy(update={"episode": 1, "title": "重复样本 A"}, deep=True),
            source_episode.model_copy(update={"episode": 2, "title": "重复样本 B"}, deep=True),
        ]
    )
    novelty_report = build_script_novelty_report(repeated_batch)
    quality_report = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )

    merged = merge_script_novelty_into_quality_report(quality_report, novelty_report)

    assert merged.status == QualityStatus.NEEDS_REWRITE
    assert any(issue.startswith("script_novelty:") for issue in merged.blocking_issues)
    assert "禁止复用同一套场景" in merged.rewrite_instruction


def test_quality_warnings_reject_short_static_episode():
    episode = EpisodeScript(
        episode=1,
        title="薄弱样例",
        hook_3s="她来了。",
        main_emotion="平",
        watch_reason="信息不足。",
        scenes=[
            Scene(
                heading="1-1 日-内-屋内",
                characters=["甲", "乙"],
                lines=[
                    SceneLine(kind="action", text="△甲站着。"),
                    SceneLine(kind="dialogue", speaker="甲", emotion="平", text="你好。"),
                    SceneLine(kind="dialogue", speaker="乙", emotion="平", text="嗯。"),
                ],
            )
        ],
        cliffhanger="她来了。",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("too short" in warning for warning in warnings)
    assert any("action lines" in warning for warning in warnings)
    assert any("opening" in warning for warning in warnings)


def test_light_edit_repair_mode_does_not_full_rewrite_structural_shortfall():
    episode = EpisodeScript(
        episode=1,
        title="强原文轻改短稿",
        hook_3s="她把规矩纸折进兜里。",
        main_emotion="克制",
        watch_reason="观众要看她如何借原文冲突反击。",
        scenes=[
            Scene(
                heading="1-1 早-内-傅家餐厅",
                characters=["林婉晴", "李玉芬"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近规矩纸，林婉晴指尖压住纸角。"),
                    SceneLine(kind="dialogue", speaker="李玉芬", emotion="冷", text="这是傅家的规矩。"),
                    SceneLine(kind="dialogue", speaker="林婉晴", emotion="静", text="我记住了。"),
                ],
            )
        ],
        cliffhanger="我记住了。",
        state_update={},
    )

    assert episode_repair_mode(episode) == "full_episode_rewrite"
    assert (
        episode_repair_mode(
            episode,
            "强原文轻改：当前集只能基于原文当前集做最小修复。",
            allow_full_rewrite=False,
        )
        == "creative_episode_repair"
    )


def test_light_edit_current_episode_repair_packet_forbids_full_rewrite():
    episode = EpisodeScript(
        episode=1,
        title="强原文轻改短稿",
        hook_3s="她把规矩纸折进兜里。",
        main_emotion="克制",
        watch_reason="观众要看她如何借原文冲突反击。",
        scenes=[
            Scene(
                heading="1-1 早-内-傅家餐厅",
                characters=["林婉晴", "李玉芬"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近规矩纸，林婉晴指尖压住纸角。"),
                    SceneLine(kind="dialogue", speaker="李玉芬", emotion="冷", text="这是傅家的规矩。"),
                    SceneLine(kind="dialogue", speaker="林婉晴", emotion="静", text="我记住了。"),
                ],
            )
        ],
        cliffhanger="我记住了。",
        state_update={},
    )

    packet = build_current_episode_repair_packet(
        episode,
        "强原文轻改：当前集只能基于原文当前集做最小修复。",
        allow_full_rewrite=False,
    )

    assert packet.repair_mode == "creative_episode_repair"
    assert "最小必要改动" in packet.baseline_policy
    assert "整集重写" not in packet.allowed_change_scope


def test_quality_warnings_reject_generic_scene_heading():
    episode = EpisodeScript(
        episode=1,
        title="泛化场景头",
        hook_3s="谁敢碰她一下！",
        main_emotion="压迫",
        watch_reason="观众要看她反击。",
        scenes=[
            Scene(
                heading="豪华宴会厅",
                characters=["甲", "乙"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近甲，灯光压暗，酒杯占前景。"),
                    SceneLine(kind="dialogue", speaker="甲", emotion="冷", text="滚出去！"),
                    SceneLine(kind="dialogue", speaker="乙", emotion="怒", text="凭什么？"),
                ],
            )
        ],
        cliffhanger="门外传来一声冷笑：谁说她不配？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("non-shooting scene headings" in warning for warning in warnings)
    assert any("1-1 夜-内-具体地点" in warning for warning in warnings)


def test_quality_warnings_reject_exposed_analysis_and_abstract_action():
    episode = EpisodeScript(
        episode=1,
        title="分析外露",
        hook_3s="滚出去！",
        main_emotion="羞辱",
        watch_reason="观众要看女主反击。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近林晚，本集看点是她如何反击，众人震惊。",
                    ),
                    SceneLine(kind="dialogue", speaker="林雪", emotion="冷", text="滚出去！"),
                    SceneLine(kind="dialogue", speaker="林晚", emotion="冷", text="凭什么？"),
                ],
            )
        ],
        cliffhanger="门外有人冷笑：谁敢动她？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("exposes hook/watch_reason analysis" in warning for warning in warnings)
    assert any("abstract action lines" in warning for warning in warnings)


def test_quality_warnings_reject_episode_title_and_hook_explanation_in_action():
    episode = EpisodeScript(
        episode=1,
        title="标题泄漏",
        hook_3s="老管家跪下。",
        main_emotion="身份悬念",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家宴会厅",
                characters=["林晚", "老管家"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中近景推近第1集 被赶出生日宴，林晚被保安推到门口。",
                    ),
                    SceneLine(kind="dialogue", speaker="林晚", emotion="冷", text="放手。"),
                    SceneLine(
                        kind="action",
                        text="△特写推近老管家突然跪下，留下她真实身份的悬念。",
                    ),
                    SceneLine(kind="dialogue", speaker="老管家", emotion="颤声", text="大小姐！"),
                ],
            )
        ],
        cliffhanger="大小姐！",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("exposes hook/watch_reason analysis" in warning for warning in warnings)


def test_quality_warnings_reject_action_that_repeats_episode_title():
    episode = EpisodeScript(
        episode=1,
        title="被赶出生日宴",
        hook_3s="滚出去！",
        main_emotion="羞辱",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近主屏证据页，被赶出生日宴被白光打到所有人脸上。",
                    ),
                    SceneLine(kind="dialogue", speaker="林雪", emotion="冷", text="滚出去！"),
                    SceneLine(kind="dialogue", speaker="林晚", emotion="冷", text="放手。"),
                ],
            )
        ],
        cliffhanger="门外有人冷笑：谁敢动她？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert any("repeats episode title in action lines" in warning for warning in warnings)


def test_batch_quality_warnings_reject_episode_range_mismatch(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    warnings = script_batch_quality_warnings(script_batch, "EP01-EP01")

    assert any("mismatch target range EP01-EP01" in warning for warning in warnings)
    assert any("got EP01,EP02,EP03,EP04,EP05" in warning for warning in warnings)


def test_batch_quality_warnings_accept_expected_episode_range(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    assert script_batch_quality_warnings(script_batch, "EP01-EP05") == []


def test_episode_repair_instruction_names_local_quality_gaps():
    episode = EpisodeScript(
        episode=1,
        title="短稿",
        hook_3s="谁敢拦我！",
        main_emotion="压迫",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="1-1 夜-内-温家走廊",
                characters=["女主", "温舟"],
                lines=[
                    SceneLine(kind="action", text="△中景推近女主，她站在门口。"),
                    SceneLine(kind="dialogue", speaker="女主", text="让开。"),
                    SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                ],
            )
        ],
        cliffhanger="让开。",
        state_update={},
    )

    instruction = episode_repair_instruction(episode, "补足镜头。")

    assert "补足镜头。" in instruction
    assert "当前本地质检" in instruction
    assert "必须补足缺口" in instruction
    assert "action 行硬格式" in instruction
    assert "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头" in instruction
    assert "至少增加" in instruction
    assert "本集本地阻断项" in instruction


def test_episode_repair_instruction_limits_cliffhanger_fix_to_tail(happy_round_outputs):
    episode = happy_round_outputs[3].episodes[0].model_copy(
        deep=True,
        update={"cliffhanger": "明天再说。"},
    )

    instruction = episode_repair_instruction(episode, "EP01 结尾钩子太软。")

    assert "修复级别：结尾钩子局部修复" in instruction
    assert "只修最后一场最后 8-12 行" in instruction
    assert "不要整集重写" in instruction
    assert "必须整集重写" not in instruction


def test_episode_repair_instruction_limits_action_format_to_local_patch(
    happy_round_outputs,
):
    episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
    episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"

    instruction = episode_repair_instruction(episode, "EP01 动作行格式不合格。")

    assert "修复级别：格式局部修复" in instruction
    assert "只修不合格 action 行" in instruction
    assert "不要整集重写" in instruction
    assert "必须整集重写" not in instruction


def test_current_episode_repair_packet_makes_existing_episode_the_baseline(
    happy_round_outputs,
):
    episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
    episode.scenes[0].lines[0].text = "△林晚站在宴会厅门口。"

    packet = build_current_episode_repair_packet(
        episode,
        "EP01 动作行格式不合格。",
    )

    assert packet.episode == 1
    assert packet.repair_mode == "format_patch"
    assert "当前集旧稿是唯一文本基准" in packet.baseline_policy
    assert "只修不合格 action 行" in packet.allowed_change_scope
    assert "△林晚站在宴会厅门口。" in packet.baseline_episode_text
    assert any("action lines violating" in target for target in packet.editable_targets)
    assert "不得新增无原文依据的新剧情、新道具、新证据或新狠话" in packet.forbidden_changes


def test_current_episode_repair_packet_keeps_source_evidence_targets(
    happy_round_outputs,
):
    episode = happy_round_outputs[3].episodes[0]

    packet = build_current_episode_repair_packet(
        episode,
        "原文证据未落到正片。",
        source_evidence_targets=["EP01 缺少原文资产：亲哥哥救场"],
    )

    assert packet.source_evidence_targets == ["EP01 缺少原文资产：亲哥哥救场"]
    assert packet.editable_targets[0] == "EP01 缺少原文资产：亲哥哥救场"
    assert packet.repair_mode == "creative_episode_repair"
    assert "当前集原文契约是唯一内容基准" in packet.baseline_policy
    assert "旧稿只作为问题定位参考" in packet.baseline_policy
    assert "scene_headings:" not in packet.protected_elements
    assert "回到当前集 source packet" in packet.allowed_change_scope


def test_current_episode_repair_packet_uses_source_contract_for_source_asset_gate(
    happy_round_outputs,
):
    episode = happy_round_outputs[3].episodes[0]

    packet = build_current_episode_repair_packet(
        episode,
        "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。方法论阻断：强原文只允许轻改，必须保留 C0/C1。",
    )

    assert packet.repair_mode == "creative_episode_repair"
    assert "当前集原文契约是唯一内容基准" in packet.baseline_policy
    assert "旧稿只作为问题定位参考" in packet.baseline_policy
    assert "回到当前集 source packet" in packet.allowed_change_scope


def test_hook_dialogue_polish_instruction_targets_tail_and_dialogue_gaps():
    episode = EpisodeScript(
        episode=2,
        title="软结尾",
        hook_3s="你到底是谁？",
        main_emotion="悬疑",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="2-1 夜-内-温家玄关",
                characters=["女主", "温铮"],
                lines=[
                    SceneLine(kind="action", text="△中景推近女主，她拉开门。"),
                    SceneLine(kind="dialogue", speaker="温铮", text="你是谁？"),
                    SceneLine(kind="dialogue", speaker="女主", text="明天再说。"),
                    SceneLine(kind="action", text="△中景女主转身离开。"),
                ],
            )
        ],
        cliffhanger="明天再说。",
        state_update={},
    )

    instruction = hook_dialogue_polish_instruction(episode, "结尾太软。")

    assert episode_needs_hook_dialogue_polish(episode)
    assert "结尾钩子/对白密度二次编译" in instruction
    assert "不要整集重写" in instruction
    assert "最后 8-12 行" in instruction
    assert "转身离开" in instruction
    assert "全局修复背景" in instruction


def test_quality_normalizes_explanatory_cliffhanger_field_to_performed_tail():
    episode = EpisodeScript(
        episode=2,
        title="说明化钩子",
        hook_3s="你到底是谁？",
        main_emotion="悬疑",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="2-1 夜-内-温家玄关",
                characters=["女主", "温铮"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。"),
                    SceneLine(kind="dialogue", speaker="女主", text="这东西，为什么在你手里？"),
                ],
            )
        ],
        cliffhanger="温铮震惊，留下关于女主真实身份的悬念。",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert has_explanatory_cliffhanger("温铮震惊，留下关于女主真实身份的悬念。")
    assert episode.cliffhanger == "这东西，为什么在你手里？"
    assert cliffhanger_field_is_performed(episode)
    assert not any("cliffhanger field" in warning for warning in warnings)


def test_quality_accepts_cliffhanger_field_copied_from_final_hook():
    episode = EpisodeScript(
        episode=2,
        title="道具反问",
        hook_3s="你到底是谁？",
        main_emotion="悬疑",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="2-1 夜-内-温家玄关",
                characters=["女主", "温铮"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。"),
                    SceneLine(kind="dialogue", speaker="女主", text="这东西，为什么在你手里？"),
                ],
            )
        ],
        cliffhanger="这东西，为什么在你手里？",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert not has_explanatory_cliffhanger(episode.cliffhanger)
    assert cliffhanger_field_is_performed(episode)
    assert not any("cliffhanger field" in warning for warning in warnings)


def test_quality_accepts_performed_prop_action_cliffhanger():
    episode = EpisodeScript(
        episode=3,
        title="屏幕证据",
        hook_3s="手机亮了。",
        main_emotion="惊",
        watch_reason="系统内部看点。",
        scenes=[
            Scene(
                heading="3-1 夜-内-编辑部",
                characters=["主编"],
                lines=[
                    SceneLine(kind="action", text="△中近景推近主编，手机屏幕占前景，BGM骤停。"),
                    SceneLine(kind="dialogue", speaker="主编", text="谁发来的？"),
                    SceneLine(
                        kind="action",
                        text="△特写定镜，手机屏幕弹出一条新消息：Ellie的心脏还在跳。",
                    ),
                ],
            )
        ],
        cliffhanger="手机屏幕弹出一条新消息：Ellie的心脏还在跳。",
        state_update={},
    )

    warnings = episode_quality_warnings(episode)

    assert not any("cliffhanger is too soft" in warning for warning in warnings)


def test_executable_shot_language_accepts_vertical_camera_moves():
    assert has_executable_shot_language(
        "△特写一只手轻推武植的胳膊，镜头顺手臂上移，定格在金莲担忧的脸上。"
    )


def test_executable_shot_language_accepts_static_closeup():
    assert has_executable_shot_language("△特写武植艰难睁开眼，视线模糊，只剩一点烛光。")


def test_action_line_template_requires_shot_size_and_motion_opening():
    assert has_action_line_template(
        "△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。"
    )
    assert has_action_line_template(
        "△EP01 全景横移过生日宴长桌，水晶灯冷光压下；镜头跟拍保安把林晚推到画面中央。"
    )
    assert not has_action_line_template("△女主站在门口。")
    assert not has_action_line_template("△突然有人冲进来。")


def test_quality_warnings_reject_abnormal_repeated_words(happy_round_outputs):
    episode = happy_round_outputs[3].episodes[0].model_copy(deep=True)
    episode.scenes[0].lines[0].text = (
        "△特写推近师傅贪婪贪婪贪婪张大的嘴，切到现金落满桌面。"
    )

    warnings = episode_quality_warnings(episode)

    assert has_abnormal_repetition("师傅贪婪贪婪贪婪张大嘴")
    assert any("abnormal repeated words/phrases" in warning for warning in warnings)


def test_demo_outputs_song_profile_for_haoheng_dasong_source():
    outputs = demo_round_outputs(
        source_text="《豪横大宋》 武植睁眼看见金莲端药，西门庆在清河施压。",
        target_episode_count=30,
    )
    source_analysis = outputs[0]
    script_batch = outputs[3]
    first = script_batch.episodes[0]

    assert "武植" in source_analysis.characters
    assert "金莲" in first.scenes[0].characters
    assert any(
        line.kind == "os" and line.speaker == "武植"
        for scene in first.scenes
        for line in scene.lines
    )
    assert first.watch_reason.startswith("观众要看现代认知")
    assert episode_quality_warnings(first) == []

```


## File: `tests/test_quality_text.py`
```
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    filter_quality_text_for_episode,
    merge_rewrite_instructions,
)


def test_merge_rewrite_instructions_dedupes_and_filters_positive_advice():
    instruction = merge_rewrite_instructions(
        [
            "方法论阻断：本素材被判定为强原文，只允许轻改。具体问题：强原文轻改失败：脚本疑似命中方法论反例：把原文预谋解约改成现场赌气解约。",
            "The provided scripts accurately map to the source material. No blocking issues detected. Ensure that when filming, emphasize props.",
            "方法论阻断：本素材被判定为强原文，只允许轻改。具体问题：强原文轻改失败：脚本疑似命中方法论反例：把原文预谋解约改成现场赌气解约。",
            "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
            "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
        ],
        blocking=True,
    )

    assert instruction.count("方法论阻断") == 1
    assert instruction.count("source_asset_preservation") == 1
    assert "No blocking issues detected" not in instruction
    assert "Ensure that when filming" not in instruction


def test_dedupe_quality_items_removes_repeated_blocking_issues():
    items = dedupe_quality_items(
        [
            "source anchor not evidenced in script: 晚会昏暗氛围",
            "source anchor not evidenced in script：晚会昏暗氛围",
            "EP01 too short: 664 chars, expected >= 800",
        ]
    )

    assert items == [
        "source anchor not evidenced in script: 晚会昏暗氛围",
        "EP01 too short: 664 chars, expected >= 800",
    ]


def test_filter_quality_text_for_episode_keeps_only_target_episode_and_global_rules():
    text = (
        "方法论阻断：本素材被判定为强原文，只允许轻改；"
        "EP01 too short: 664 chars, expected >= 800；"
        "EP02 has non-shooting scene headings: 2-1 白-内-林挽清公寓；"
        "source_evidence: EP05 缺少原文资产：雪地烟火激吻；"
        "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。"
    )

    scoped = filter_quality_text_for_episode(text, 1)

    assert "方法论阻断" in scoped
    assert "EP01 too short" in scoped
    assert "source_asset_preservation" in scoped
    assert "EP02" not in scoped
    assert "EP05" not in scoped
    assert "雪地烟火激吻" not in scoped

```


## File: `tests/p0_platform.test.ts`
```
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import Database from "better-sqlite3";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import type { EngineSourceEvidenceItem } from "../src/lib/engine-types";

const repoRoot = path.resolve(import.meta.dirname, "..");
const tempRoot = mkdtempSync(path.join(os.tmpdir(), "novel-drama-p0-"));
process.env.NOVEL_DRAMA_DB_PATH = path.join(tempRoot, "db.sqlite");
process.env.NOVEL_DRAMA_BACKFILL_LEGACY_TENANT = "0";

execFileSync("npx", ["drizzle-kit", "migrate"], {
  cwd: repoRoot,
  env: process.env,
  stdio: "ignore",
});

function setEnv(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name];
    return;
  }
  process.env[name] = value;
}

test.after(() => {
  rmSync(tempRoot, { recursive: true, force: true });
});

test("production-like deployment never silently falls back to mock engine", async () => {
  const previous = {
    webMock: process.env.NOVEL_DRAMA_WEB_MOCK,
    nodeEnv: process.env.NODE_ENV,
    target: process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET,
    apiKey: process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL,
  };
  try {
    delete process.env.NOVEL_DRAMA_WEB_MOCK;
    delete process.env.OPENAI_API_KEY;
    delete process.env.OPENAI_MODEL;
    setEnv("NODE_ENV", "production");
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = "production";

    const { resolveEngineMode, realEngineConfigProblem } = await import(
      "../src/lib/engine-runner"
    );

    assert.deepEqual(resolveEngineMode(), { mode: "real", explicitMock: false });
    assert.match(realEngineConfigProblem() ?? "", /OPENAI_API_KEY/);
  } finally {
    process.env.NOVEL_DRAMA_WEB_MOCK = previous.webMock;
    setEnv("NODE_ENV", previous.nodeEnv);
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = previous.target;
    process.env.OPENAI_API_KEY = previous.apiKey;
    process.env.OPENAI_MODEL = previous.model;
  }
});

test("round generation jobs are unique while a round already has an active job", async () => {
  const { db, schema } = await import("../src/db/client");
  const { createJob } = await import("../src/lib/jobs");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0",
    name: "P0 Project",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0",
    projectId: "project-p0",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: now,
  });

  const first = await createJob({
    kind: "round_generation",
    title: "first",
    projectId: "project-p0",
    roundId: "round-p0",
  });

  await assert.rejects(
    () =>
      createJob({
        kind: "round_generation",
        title: "duplicate",
        projectId: "project-p0",
        roundId: "round-p0",
      }),
    /active job already exists/
  );

  assert.equal(first.roundId, "round-p0");
});

test("payment webhook rejects unsigned requests even outside production", async () => {
  const previous = {
    nodeEnv: process.env.NODE_ENV,
    secretA: process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET,
    secretB: process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET,
  };
  try {
    setEnv("NODE_ENV", "development");
    delete process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET;
    delete process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET;

    const { POST } = await import("../src/app/api/platform/payments/webhook/route");
    const res = await POST(
      new Request("http://localhost/api/platform/payments/webhook", {
        method: "POST",
        body: JSON.stringify({
          provider: "mock",
          eventType: "checkout.paid",
          externalEventId: "evt_unsigned",
        }),
      }) as never
    );
    const body = (await res.json()) as { error?: string };

    assert.equal(res.status, 400);
    assert.match(body.error ?? "", /signature|secret|unsigned/i);
  } finally {
    setEnv("NODE_ENV", previous.nodeEnv);
    process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET = previous.secretA;
    process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET = previous.secretB;
  }
});

test("payment webhook processor refuses unsigned direct calls", async () => {
  const { processPaymentWebhook } = await import("../src/lib/platform-credits");

  await assert.rejects(
    () =>
      processPaymentWebhook({
        provider: "mock",
        eventType: "checkout.paid",
        externalEventId: "direct_unsigned",
      }),
    /signature is required/
  );
});

test("payment webhook processor refuses unsigned mock bypass in production-like deployment", async () => {
  const previous = {
    nodeEnv: process.env.NODE_ENV,
    target: process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET,
    allowUnsigned: process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS,
  };
  try {
    setEnv("NODE_ENV", "production");
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = "production";
    process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS = "1";
    const { processPaymentWebhook } = await import("../src/lib/platform-credits");

    await assert.rejects(
      () =>
        processPaymentWebhook({
          provider: "mock",
          eventType: "checkout.paid",
          externalEventId: "prod_unsigned_mock",
        }),
      /signature is required/
    );
  } finally {
    setEnv("NODE_ENV", previous.nodeEnv);
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = previous.target;
    process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS = previous.allowUnsigned;
  }
});

test("run-all pauses visibly when latest round quality is not usable", async () => {
  const { db, schema } = await import("../src/db/client");
  const { scheduleNextRoundIfRunAll } = await import("../src/lib/engine-runner");
  const { parseProjectMeta } = await import("../src/lib/project-controls");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p1-runall-quality",
    name: "P1 RunAll Quality",
    novelText: "source",
    targetEpisodeCount: 20,
    status: "running",
    metaJson: JSON.stringify({
      control: {
        runAll: {
          enabled: true,
          generationVariant: "drama_engine_first",
          repairBudget: "episode",
        },
      },
    }),
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p1-runall-quality",
    projectId: "project-p1-runall-quality",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    summaryJson: JSON.stringify({
      quality_report: {
        status: "needs_rewrite",
        rewrite_instruction: "EP03 人物动机断裂，先修复再继续。",
      },
      next_round_context: {
        current_episode: 5,
      },
    }),
    createdAt: now,
  });

  const next = await scheduleNextRoundIfRunAll("project-p1-runall-quality");

  assert.equal(next, null);
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-runall-quality"),
  });
  const jobs = await db.query.jobs.findMany({
    where: (jobs, { eq }) => eq(jobs.projectId, "project-p1-runall-quality"),
  });
  const meta = parseProjectMeta(project?.metaJson ?? null);
  assert.equal(project?.status, "failed");
  assert.equal(meta.control?.runAll?.enabled, false);
  assert.match(String(meta.control?.runAll?.pausedReason ?? ""), /needs_rewrite/);
  assert.equal(jobs.length, 0);
});

test("single round with human-review quality does not leave project running without active job", async () => {
  const { db, schema } = await import("../src/db/client");
  const { markProjectAfterRoundCompletion } = await import("../src/lib/engine-runner");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-human-review-stop",
    name: "Human Review Stop",
    novelText: "source",
    targetEpisodeCount: 25,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });

  await markProjectAfterRoundCompletion("project-p0-human-review-stop", {
    currentEpisode: 5,
    targetEpisodeCount: 25,
    qualityStatus: "needs_human_review",
    roundNumber: 1,
    rewriteInstruction: "EP05 原文资产缺失，需要人工复核。",
  });

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-human-review-stop"),
  });
  assert.equal(project?.status, "failed");
  assert.match(project?.metaJson ?? "", /needs_human_review/);
  assert.match(project?.metaJson ?? "", /EP05 原文资产缺失/);
});

test("round generation job stores selected Gemini model in payload", async () => {
  const { db, schema } = await import("../src/db/client");
  const { startEngineRound } = await import("../src/lib/engine-runner");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-model-select",
    name: "Model Select",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });

  const started = await startEngineRound("project-p0-model-select", 1, {
    llmModel: "gemini_3_5_flash",
  });

  const job = await db.query.jobs.findFirst({
    where: (jobs, { eq }) => eq(jobs.id, started.jobId),
  });
  const payload = JSON.parse(job?.payloadJson ?? "{}") as { llmModel?: string };
  assert.equal(payload.llmModel, "google/gemini-3.5-flash");
});

test("engine run args include the selected model flag", async () => {
  const { buildEngineRunArgs } = await import("../src/lib/engine-runner");

  const args = buildEngineRunArgs({
    sourcePath: "/tmp/source.txt",
    engineDir: "/tmp/project",
    projectId: "project-model",
    roundNumber: 2,
    targetEpisodeCount: 25,
    episodesPerRound: 5,
    generationVariant: "drama_engine_first",
    repairBudget: "episode",
    llmModel: "google/gemini-3.5-flash",
    methodologyCardsPath: null,
    mock: false,
  });

  const modelIndex = args.indexOf("--model");
  assert.ok(modelIndex > -1);
  assert.equal(args[modelIndex + 1], "google/gemini-3.5-flash");
});

test("episode AI optimize prompt anchors on current draft, bible, and instruction", async () => {
  const { buildEpisodeOptimizationPrompt } = await import(
    "../src/lib/episode-ai-optimize"
  );

  const prompt = buildEpisodeOptimizationPrompt({
    project: {
      name: "名利双收",
      novelText: "原文：女主在颁奖礼后台被羞辱，随后提前放好的解约协议成为反击起点。",
    },
    episode: {
      epNum: 3,
      scriptTxt: "第3集 旧稿\n1-1 后台\n林挽清：我早就准备好了。",
    },
    bible: {
      charactersMd: "人物小传：林挽清克制、清醒，不歇斯底里。",
      episodePlanMd: "分集规划：第3集必须承接第2集结尾。",
      sixAssetsJson: "{\"核心钩子\":\"公开羞辱后的主动离开\"}",
      prevRoundSummaryJson: "{\"open_hooks\":[\"解约协议已埋\"]}",
    },
    round: {
      roundNum: 1,
      summaryJson: "{\"next_round_context\":{\"current_episode\":5}}",
    },
    episodes: [
      { epNum: 2, scriptTxt: "第2集 结尾：她把协议推到桌边。" },
      { epNum: 4, scriptTxt: "第4集 开头：路淮北发现她真的走了。" },
    ],
    instruction: "强化镜头和情绪递进，不要让女主突然全知全能。",
  });

  assert.match(prompt, /旧稿是唯一文本基准/);
  assert.match(prompt, /只优化第 3 集/);
  assert.match(prompt, /强化镜头和情绪递进/);
  assert.match(prompt, /人物小传/);
  assert.match(prompt, /第2集 结尾/);
  assert.match(prompt, /第4集 开头/);
});

test("edit impact applies user draft and optimizes impacted downstream episodes", async () => {
  const { db, schema } = await import("../src/db/client");
  const { applyEpisodeEditImpact } = await import("../src/lib/edit-impact-apply");
  const { parseProjectMeta } = await import("../src/lib/project-controls");
  const now = new Date();

  await db.insert(schema.projects).values({
    id: "project-p0-edit-impact",
    name: "Edit Impact Project",
    novelText: "原文：女主在颁奖礼被羞辱，解约协议提前埋下。",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-edit-impact",
    projectId: "project-p0-edit-impact",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    summaryJson: JSON.stringify({
      next_round_context: {
        open_hooks: ["路淮北还不知道解约协议已经签好"],
        prop_states: ["解约协议在办公室抽屉"],
        foreshadowing_ledger: ["第2集开头要承接协议被推到桌边"],
      },
      story_state_ledger: {
        entries: [
          {
            episode: 1,
            kind: "prop",
            key: "解约协议",
            value: "提前准备",
            status: "open",
          },
        ],
      },
    }),
    createdAt: now,
  });
  await db.insert(schema.bibles).values({
    id: "bible-p0-edit-impact",
    projectId: "project-p0-edit-impact",
    charactersMd: "林挽清：克制、清醒，反击来自深思熟虑。",
    episodePlanMd: "第2集必须承接第1集结尾的解约协议。",
    sixAssetsJson: "{\"核心钩子\":\"公开羞辱后的主动离开\"}",
    prevRoundSummaryJson: "{}",
    updatedAt: now,
  });
  await db.insert(schema.episodes).values([
    {
      id: "episode-p0-impact-1",
      projectId: "project-p0-edit-impact",
      roundId: "round-p0-edit-impact",
      epNum: 1,
      scriptTxt: "第1集\n林挽清：我不要了。\n△结尾她转身离开。",
      draftMd: "第1集\n林挽清：我不要了。\n△结尾她转身离开。",
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
    {
      id: "episode-p0-impact-2",
      projectId: "project-p0-edit-impact",
      roundId: "round-p0-edit-impact",
      epNum: 2,
      scriptTxt: "第2集\n△开头路淮北看着空房间。\n路淮北：她人呢？",
      draftMd: "第2集\n△开头路淮北看着空房间。\n路淮北：她人呢？",
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
  ]);

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-edit-impact"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-edit-impact"),
  });
  const bible = await db.query.bibles.findFirst({
    where: (bibles, { eq }) => eq(bibles.projectId, "project-p0-edit-impact"),
  });
  const episodes = await db.query.episodes.findMany({
    where: (episodesTable, { eq }) =>
      eq(episodesTable.projectId, "project-p0-edit-impact"),
  });
  const episode = episodes.find((item) => item.epNum === 1);
  assert.ok(project);
  assert.ok(round);
  assert.ok(bible);
  assert.ok(episode);

  const editedScript =
    "第1集\n林挽清：（压低声音）协议，我昨晚就签好了。\n△结尾她把解约协议推到路淮北面前。";
  const result = await applyEpisodeEditImpact({
    project,
    round,
    bible,
    episode,
    episodes,
    editedScriptText: editedScript,
    optimizeImpacted: true,
    optimizer: async ({ instruction }) => ({
      scriptText: `第2集\n△开头特写解约协议，承接上集。\n林挽清OS：${(instruction ?? "").slice(0, 18)}`,
      llmModel: "fake-model",
    }),
  });

  assert.equal(result.report.changed, true);
  assert.equal(result.applied, true);
  assert.equal(result.optimizedEpisodes.length, 1);

  const updatedEp1 = await db.query.episodes.findFirst({
    where: (episodesTable, { eq }) => eq(episodesTable.id, "episode-p0-impact-1"),
  });
  const updatedEp2 = await db.query.episodes.findFirst({
    where: (episodesTable, { eq }) => eq(episodesTable.id, "episode-p0-impact-2"),
  });
  const updatedProject = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-edit-impact"),
  });

  assert.equal(updatedEp1?.scriptTxt, editedScript);
  assert.match(updatedEp1?.reviewJson ?? "", /operator_script_edit/);
  assert.match(updatedEp2?.scriptTxt ?? "", /承接上集/);
  assert.match(updatedEp2?.reviewJson ?? "", /upstream_user_edit/);
  assert.match(
    JSON.stringify(parseProjectMeta(updatedProject?.metaJson ?? null)),
    /解约协议/
  );
});

test("legacy per-episode retry helper is disabled instead of regenerating", async () => {
  const { retryEpisode } = await import("../src/lib/round-runner");

  await assert.rejects(
    () => retryEpisode("legacy-episode-id"),
    /legacy episode retry is disabled/i
  );
});

test("round generation unique error classification only matches the named index", () => {
  const source = readFileSync(path.join(repoRoot, "src/lib/jobs.ts"), "utf-8");

  assert.match(source, /jobs_active_round_generation_unique/);
  assert.doesNotMatch(source, /jobs_active_round_generation_unique\|unique/);
});

test("round quality card stays compact and does not render issue lists", () => {
  const source = readFileSync(
    path.join(
      repoRoot,
      "src/app/projects/[id]/rounds/[n]/RoundClient.tsx"
    ),
    "utf-8"
  );
  const qualityStart = source.indexOf("质量门禁");
  const sidePanelStart = source.indexOf("<aside className=\"round-inspector\">");
  const qualitySidePanelStart = source.indexOf("质量门禁", sidePanelStart);
  const runtimeStart = source.indexOf("{hasGenerationMetrics", qualitySidePanelStart);
  assert.ok(qualityStart > -1);
  assert.ok(sidePanelStart > -1);
  assert.ok(qualitySidePanelStart > sidePanelStart);
  assert.ok(runtimeStart > qualitySidePanelStart);
  const qualityPanel = source.slice(qualitySidePanelStart, runtimeStart);

  assert.doesNotMatch(qualityPanel, /round-issue-list/);
  assert.match(qualityPanel, /源文/);
  assert.match(qualityPanel, /创作/);
  assert.match(qualityPanel, /门禁/);
  assert.match(qualityPanel, /承接/);
});

test("effective quality score is capped by final source evidence and drama gates", async () => {
  const { effectiveQualityScore } = await import("../src/lib/engine-types");

  const score = effectiveQualityScore({
    quality_report: {
      status: "needs_rewrite",
      scores: {
        hook: 9,
        conflict: 9,
        cliffhanger: 9,
        continuity: 9,
        video_feasibility: 9,
      },
      blocking_issues: [],
      rewrite_instruction: "source similarity below 5/10",
    },
    source_evidence_report: {
      coverage_score: 0,
      items: [],
      missing_items: ["EP05 缺少原文资产：霍雅偷拍照片"],
      rewrite_instruction: "原文证据未落到正片。",
    },
    drama_quality_report: {
      overall_score: 5,
      dimensions: [
        {
          name: "source_asset_preservation",
          score: 0,
          status: "blocking",
          evidence: ["source similarity below 5/10: 0/100"],
          suggestion: "恢复原文资产。",
        },
      ],
      blocking_issues: ["source_asset_preservation"],
      advisory_warnings: [],
      rewrite_instruction: "恢复原文资产。",
    },
  });

  assert.equal(score, 0);
});

test("episode quality score is not overwritten by round-level source gate", async () => {
  const {
    effectiveQualityScore,
    episodeQualityScore,
    sourceGateScore,
  } = await import("../src/lib/engine-types");
  const result = {
    quality_report: {
      status: "needs_human_review",
      scores: {
        hook: 10,
        conflict: 10,
        cliffhanger: 9,
        continuity: 10,
        video_feasibility: 9,
      },
      blocking_issues: [],
      rewrite_instruction: "source gate failed",
    },
    source_evidence_report: {
      coverage_score: 100,
      items: [
        {
          episode: 1,
          source_anchor: "EP01 source",
          adaptation_reason: "matched",
          retained_assets: ["hook"],
          script_evidence: ["hook"],
          status: "matched",
        },
        {
          episode: 2,
          source_anchor: "EP02 source",
          adaptation_reason: "missing specific anchor",
          retained_assets: ["VIP通道黄色炽热灯光"],
          script_evidence: [],
          status: "matched",
        },
      ],
      missing_items: [],
      rewrite_instruction: "",
    },
    adaptation_quality_report: {
      source_fidelity: {
        score: 10,
        preserved_original_hook: true,
        blocking_warnings: [
          "source anchor not evidenced in script: VIP通道黄色炽热灯光",
          "forbidden addition/reveal may have leaked into script: 严禁改变林挽清解约的主动性。",
        ],
        advisory_warnings: [],
        checks: [
          {
            category: "source_mapping",
            episode: 2,
            status: "blocking",
            warning: "source anchor not evidenced in script: VIP通道黄色炽热灯光",
          },
          {
            category: "C4_forbidden_addition",
            episode: null,
            status: "blocking",
            warning: "forbidden addition/reveal may have leaked into script",
          },
        ],
      },
      continuity: { score: 90, blocking_warnings: [], advisory_warnings: [] },
      story_state_ledger: {
        current_episode: 2,
        entries: [],
        open_hooks: [],
        forbidden_reveals: [],
        character_knowledge: {},
        relationship_changes: [],
        prop_states: [],
        foreshadowing_ledger: [],
        warnings: [],
      },
      blocking_warnings: [],
      advisory_warnings: [],
      rewrite_instruction: "",
    },
    drama_quality_report: {
      overall_score: 5,
      dimensions: [
        {
          name: "source_asset_preservation",
          score: 1,
          status: "blocking",
          evidence: ["source similarity below 5/10: 10/100"],
          suggestion: "restore source",
        },
      ],
      blocking_issues: [],
      advisory_warnings: [],
      rewrite_instruction: "",
    },
  } as never;

  assert.equal(effectiveQualityScore(result), 1);
  assert.equal(sourceGateScore(result), 1);
  assert.equal(episodeQualityScore(result, 1), 9.6);
  assert.equal(episodeQualityScore(result, 2), 4);
});

test("engine sync computes scores per episode instead of copying one round score", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );

  assert.match(source, /episodeQualityScore\(result,\s*episode\.episode\)/);
  assert.doesNotMatch(source, /const score = effectiveQualityScore\(result\);/);
});

test("package exposes typecheck and test:ts avoids shell glob expansion", () => {
  const pkg = JSON.parse(
    readFileSync(path.join(repoRoot, "package.json"), "utf-8")
  ) as { scripts?: Record<string, string> };

  assert.equal(pkg.scripts?.typecheck, "tsc --noEmit");
  assert.equal(pkg.scripts?.["test:ts"], "node scripts/run-ts-tests.mjs");
});

test("active round generation migration deduplicates dirty queued and running jobs", () => {
  const dbPath = path.join(tempRoot, "dirty-migration.sqlite");
  const sqlite = new Database(dbPath);
  try {
    sqlite.exec(`
      create table jobs (
        id text primary key not null,
        kind text not null,
        status text not null,
        round_id text,
        progress integer not null default 0,
        error_text text,
        created_at integer not null,
        updated_at integer not null,
        finished_at integer
      );
      insert into jobs (id, kind, status, round_id, progress, created_at, updated_at)
      values
        ('old-running', 'round_generation', 'running', 'round-dirty', 30, 1000, 1000),
        ('new-queued', 'round_generation', 'queued', 'round-dirty', 0, 2000, 2000),
        ('other-round', 'round_generation', 'queued', 'round-clean', 0, 3000, 3000);
    `);
    const migration = readFileSync(
      path.join(repoRoot, "drizzle/migrations/0008_material_silvermane.sql"),
      "utf-8"
    );
    for (const statement of migration.split("--> statement-breakpoint")) {
      if (statement.trim()) sqlite.exec(statement);
    }

    const rows = sqlite
      .prepare("select id, status, error_text from jobs order by id")
      .all() as Array<{ id: string; status: string; error_text: string | null }>;
    const activeDirtyRows = rows.filter(
      (row) =>
        ["old-running", "new-queued"].includes(row.id) &&
        ["queued", "running"].includes(row.status)
    );
    assert.equal(activeDirtyRows.length, 1);
    assert.equal(activeDirtyRows[0].id, "new-queued");
    assert.match(
      rows.find((row) => row.id === "old-running")?.error_text ?? "",
      /dedup migration/
    );
  } finally {
    sqlite.close();
  }
});

test("stale round generation failure marks the project visibly failed", async () => {
  const { db, schema } = await import("../src/db/client");
  const { reconcileStaleJobs } = await import("../src/lib/jobs");
  const now = new Date();
  const stale = new Date(now.getTime() - 60_000);
  await db.insert(schema.projects).values({
    id: "project-p1-stale",
    name: "P1 Stale",
    novelText: "source",
    targetEpisodeCount: 10,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p1-stale",
    projectId: "project-p1-stale",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: now,
  });
  await db.insert(schema.jobs).values({
    id: "job-p1-stale",
    kind: "round_generation",
    title: "stale round",
    projectId: "project-p1-stale",
    roundId: "round-p1-stale",
    status: "running",
    progress: 42,
    attempts: 1,
    createdAt: stale,
    updatedAt: stale,
    startedAt: stale,
  });

  const result = await reconcileStaleJobs({ olderThanMs: 1 });

  assert.equal(result.failedRunning, 1);
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-stale"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p1-stale"),
  });
  assert.equal(project?.status, "failed");
  assert.equal(round?.status, "failed");
});

test("stale queued round generation is stopped instead of claimed days later", async () => {
  const { db, schema } = await import("../src/db/client");
  const { claimNextQueuedJob, STALE_QUEUED_JOB_MS } = await import("../src/lib/jobs");
  const stale = new Date(Date.now() - STALE_QUEUED_JOB_MS - 60_000);
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-stale-queued",
    name: "Stale Queued Project",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: stale,
    updatedAt: stale,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-stale-queued",
    projectId: "project-p0-stale-queued",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: stale,
  });
  await db.insert(schema.jobs).values({
    id: "job-p0-stale-queued",
    kind: "round_generation",
    title: "stale queued",
    projectId: "project-p0-stale-queued",
    roundId: "round-p0-stale-queued",
    status: "queued",
    progress: 0,
    createdAt: stale,
    updatedAt: now,
  });

  const claimed = await claimNextQueuedJob({ kind: "round_generation" });

  const job = await db.query.jobs.findFirst({
    where: (jobs, { eq }) => eq(jobs.id, "job-p0-stale-queued"),
  });
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-stale-queued"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-stale-queued"),
  });
  assert.notEqual(claimed?.id, "job-p0-stale-queued");
  assert.equal(job?.status, "failed");
  assert.equal(project?.status, "failed");
  assert.equal(round?.status, "failed");
  assert.match(job?.errorText ?? "", /排队超过/);
});

test("direct retry requeues a round job and restores project and round running state", async () => {
  const { db, schema } = await import("../src/db/client");
  const { requeueRetryableJob } = await import("../src/lib/jobs");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p1-retry",
    name: "P1 Retry",
    novelText: "source",
    targetEpisodeCount: 10,
    status: "failed",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p1-retry",
    projectId: "project-p1-retry",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "failed",
    summaryJson: JSON.stringify({ error: "old failure" }),
    createdAt: now,
  });
  await db.insert(schema.jobs).values({
    id: "job-p1-retry",
    kind: "round_generation",
    title: "failed round",
    projectId: "project-p1-retry",
    roundId: "round-p1-retry",
    status: "failed",
    progress: 100,
    attempts: 1,
    errorText: "old failure",
    createdAt: now,
    updatedAt: now,
    finishedAt: now,
  });

  const retried = await requeueRetryableJob("job-p1-retry");

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-retry"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p1-retry"),
  });
  assert.equal(retried.status, "queued");
  assert.equal(project?.status, "running");
  assert.equal(round?.status, "running");
  assert.equal(round?.summaryJson, null);
});

test("round completion is marked succeeded before scheduling the next run-all round", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const syncIndex = source.indexOf("await syncEngineRoundToDb(project, roundId, result);");
  const successIndex = source.indexOf("await succeedJob(jobId", syncIndex);
  const scheduleIndex = source.indexOf(
    "await scheduleNextRoundIfRunAll(project.id)",
    syncIndex
  );

  assert.ok(syncIndex > 0);
  assert.ok(successIndex > syncIndex);
  assert.ok(scheduleIndex > successIndex);
});

test("engine round failure catch marks project failed instead of hiding it as running", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const catchIndex = source.indexOf("} catch (error) {");
  const failureProjectUpdate = source.indexOf(".update(schema.projects)", catchIndex);
  const failedStatusIndex = source.indexOf('.set({ status: "failed"', failureProjectUpdate);
  const runningStatusIndex = source.indexOf('.set({ status: "running"', failureProjectUpdate);

  assert.ok(catchIndex > 0);
  assert.ok(failureProjectUpdate > catchIndex);
  assert.ok(failedStatusIndex > failureProjectUpdate);
  assert.ok(runningStatusIndex === -1 || runningStatusIndex > failedStatusIndex);
});

test("engine round job does not succeed when final quality status is red", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const syncIndex = source.indexOf("await syncEngineRoundToDb(project, roundId, result);");
  const qualityGuardIndex = source.indexOf(
    'if (result.quality_report.status !== "usable")',
    syncIndex
  );
  const failJobIndex = source.indexOf("await failJob(jobId", qualityGuardIndex);
  const succeedIndex = source.indexOf("await succeedJob(jobId", syncIndex);

  assert.ok(syncIndex > 0);
  assert.ok(qualityGuardIndex > syncIndex);
  assert.ok(failJobIndex > qualityGuardIndex);
  assert.ok(succeedIndex > failJobIndex);
});

test("quality sample worker runs direct baseline comparison by default", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const commandIndex = source.indexOf('"evaluate-samples"');
  const baselineFlagIndex = source.indexOf('"--direct-baseline"', commandIndex);

  assert.ok(commandIndex > 0);
  assert.ok(baselineFlagIndex > commandIndex);
});

test("source evidence view type accepts partial item status", () => {
  const item = {
    episode: 1,
    source_anchor: "EP01 原文资产",
    adaptation_reason: "部分保留，部分缺失",
    retained_assets: ["原文钩子", "情绪高潮"],
    script_evidence: ["△ 原文钩子被拍出来。"],
    evidence_spans: [],
    status: "partial",
  } satisfies EngineSourceEvidenceItem;

  assert.equal(item.status, "partial");
});

test("archived project control delete removes the project storage directory", async () => {
  const { POST } = await import("../src/app/api/projects/[id]/control/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import("../src/lib/platform-context");
  const now = new Date();
  const context = await resolvePlatformContextFromInput({
    email: "delete-project@example.com",
    tenantSlug: "delete-project-tenant",
    tenantName: "Delete Project Tenant",
  });
  const projectId = "project-p1-archived-delete-storage";
  const storageDir = path.join(repoRoot, "storage", "projects", projectId);
  mkdirSync(storageDir, { recursive: true });
  writeFileSync(path.join(storageDir, "artifact.txt"), "source and prompt trace");
  await db.insert(schema.projects).values({
    id: projectId,
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Archived Delete Storage",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "paused",
    metaJson: JSON.stringify({ archivedAt: now.toISOString() }),
    createdAt: now,
    updatedAt: now,
  });

  try {
    const res = await POST(
      new Request(`http://localhost/api/projects/${projectId}/control`, {
        method: "POST",
        headers: {
          "x-novel-user-email": "delete-project@example.com",
          "x-novel-tenant": "delete-project-tenant",
          "x-novel-tenant-name": "Delete Project Tenant",
        },
        body: JSON.stringify({ action: "delete" }),
      }) as never,
      { params: Promise.resolve({ id: projectId }) }
    );

    assert.equal(res.status, 200);
    assert.equal(existsSync(storageDir), false);
  } finally {
    rmSync(storageDir, { recursive: true, force: true });
  }
});

test("project list response redacts full novel text", async () => {
  const { GET } = await import("../src/app/api/projects/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const now = new Date();
  const context = await resolvePlatformContextFromInput({
    email: "redact-list@example.com",
    tenantSlug: "redact-list-tenant",
    tenantName: "Redact List Tenant",
  });
  const otherContext = await resolvePlatformContextFromInput({
    email: "other-redact-list@example.com",
    tenantSlug: "redact-list-tenant",
    tenantName: "Redact List Tenant",
  });
  const fullNovel = "这是一整本不应该出现在列表响应里的小说原文。";
  await db.insert(schema.projects).values({
    id: "project-p0-redact-list",
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Redacted List",
    novelText: fullNovel,
    targetEpisodeCount: 5,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.projects).values({
    id: "project-p0-redact-list-other-owner",
    tenantId: otherContext.tenant.id,
    ownerUserId: otherContext.user.id,
    name: "Other Owner Project",
    novelText: "同一个 workspace 里，其他 owner 的小说也不能出现在列表。",
    targetEpisodeCount: 5,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });

  const res = await GET(
    new Request("http://localhost/api/projects", {
      headers: {
        "x-novel-user-email": "redact-list@example.com",
        "x-novel-tenant": "redact-list-tenant",
        "x-novel-tenant-name": "Redact List Tenant",
      },
    }) as never
  );
  const body = (await res.json()) as Array<Record<string, unknown>>;
  const project = body.find((item) => item.id === "project-p0-redact-list");
  const otherProject = body.find(
    (item) => item.id === "project-p0-redact-list-other-owner"
  );

  assert.ok(project);
  assert.equal(otherProject, undefined);
  assert.equal(Object.prototype.hasOwnProperty.call(project, "novelText"), false);
  assert.equal(project.novelExcerpt, undefined);
  assert.equal(project.novelCharCount, fullNovel.length);
});

test("job list is isolated by project owner inside the same tenant", async () => {
  const { GET } = await import("../src/app/api/jobs/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const now = new Date();
  const ownerContext = await resolvePlatformContextFromInput({
    email: "job-owner@example.com",
    tenantSlug: "job-owner-tenant",
    tenantName: "Job Owner Tenant",
  });
  const otherContext = await resolvePlatformContextFromInput({
    email: "job-other@example.com",
    tenantSlug: "job-owner-tenant",
    tenantName: "Job Owner Tenant",
  });
  await db.insert(schema.projects).values([
    {
      id: "project-p0-job-owner-visible",
      tenantId: ownerContext.tenant.id,
      ownerUserId: ownerContext.user.id,
      name: "Visible Job Project",
      novelText: "source",
      targetEpisodeCount: 5,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
    {
      id: "project-p0-job-owner-hidden",
      tenantId: otherContext.tenant.id,
      ownerUserId: otherContext.user.id,
      name: "Hidden Job Project",
      novelText: "other source",
      targetEpisodeCount: 5,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
  ]);
  await db.insert(schema.jobs).values([
    {
      id: "job-p0-owner-visible",
      kind: "delivery_export",
      status: "queued",
      tenantId: ownerContext.tenant.id,
      projectId: "project-p0-job-owner-visible",
      title: "Visible delivery job",
      progress: 0,
      attempts: 0,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: "job-p0-owner-hidden",
      kind: "delivery_export",
      status: "queued",
      tenantId: otherContext.tenant.id,
      projectId: "project-p0-job-owner-hidden",
      title: "Hidden delivery job",
      progress: 0,
      attempts: 0,
      createdAt: now,
      updatedAt: now,
    },
  ]);

  const res = await GET(
    new Request("http://localhost/api/jobs?limit=20", {
      headers: {
        "x-novel-user-email": "job-owner@example.com",
        "x-novel-tenant": "job-owner-tenant",
        "x-novel-tenant-name": "Job Owner Tenant",
      },
    }) as never
  );
  const body = (await res.json()) as Array<{ id: string }>;

  assert.equal(res.status, 200);
  assert.ok(body.some((job) => job.id === "job-p0-owner-visible"));
  assert.equal(body.some((job) => job.id === "job-p0-owner-hidden"), false);
});

test("delivery export request creates an async job instead of running export inline", async () => {
  const { POST } = await import("../src/app/api/projects/[id]/export/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const now = new Date();
  const context = await resolvePlatformContextFromInput({
    email: "async-export@example.com",
    tenantSlug: "async-export-tenant",
    tenantName: "Async Export Tenant",
  });
  await db.insert(schema.projects).values({
    id: "project-p0-async-export",
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Async Export",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "done",
    createdAt: now,
    updatedAt: now,
  });

  const previousAutoWorker = process.env.NOVEL_DRAMA_AUTO_WORKER;
  try {
    process.env.NOVEL_DRAMA_AUTO_WORKER = "0";
    const res = await POST(
      new Request(
        "http://localhost/api/projects/project-p0-async-export/export?round=1&allowIssues=1",
        {
          method: "POST",
          headers: {
            "x-novel-user-email": "async-export@example.com",
            "x-novel-tenant": "async-export-tenant",
            "x-novel-tenant-name": "Async Export Tenant",
            "idempotency-key": "delivery-export-once",
          },
        }
      ) as never,
      { params: Promise.resolve({ id: "project-p0-async-export" }) }
    );
    const body = (await res.json()) as { jobId?: string; status?: string };
    const jobs = await db.query.jobs.findMany({
      where: (jobsTable, { eq }) =>
        eq(jobsTable.projectId, "project-p0-async-export"),
    });

    assert.equal(res.status, 202);
    assert.equal(body.status, "queued");
    assert.ok(body.jobId);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].kind, "delivery_export");
  } finally {
    setEnv("NOVEL_DRAMA_AUTO_WORKER", previousAutoWorker);
  }
});

test("ops worker setup consumes every async export job kind", () => {
  const workerSource = readFileSync(
    path.join(repoRoot, "src/scripts/job-worker.ts"),
    "utf-8"
  );
  const installSource = readFileSync(
    path.join(repoRoot, "scripts/install-ops-launchagent.sh"),
    "utf-8"
  );
  const expectedKinds = [
    "delivery_export",
    "video_brief_export",
    "localization_export",
  ];

  for (const kind of expectedKinds) {
    assert.match(workerSource, new RegExp(kind));
  }
  assert.match(installSource, /ops-delivery-worker\.plist/);
  assert.match(installSource, /ops-video-brief-worker\.plist/);
  assert.match(installSource, /ops-localization-worker\.plist/);
});

test("round status is reconciled from episode status and cannot stay done with failed episode", async () => {
  const { db, schema } = await import("../src/db/client");
  const { reconcileRoundStatusFromEpisodes } = await import(
    "../src/lib/engine-runner"
  );
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-round-status-aggregate",
    name: "Round Aggregate",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "done",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-status-aggregate",
    projectId: "project-p0-round-status-aggregate",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    createdAt: now,
  });
  await db.insert(schema.episodes).values([
    {
      id: "episode-p0-status-green",
      projectId: "project-p0-round-status-aggregate",
      roundId: "round-p0-status-aggregate",
      epNum: 1,
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
    {
      id: "episode-p0-status-failed",
      projectId: "project-p0-round-status-aggregate",
      roundId: "round-p0-status-aggregate",
      epNum: 2,
      status: "failed",
      retryCount: 0,
      updatedAt: now,
    },
  ]);

  await reconcileRoundStatusFromEpisodes("round-p0-status-aggregate");

  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-status-aggregate"),
  });
  assert.equal(round?.status, "failed");
});

test("core one-to-one artifacts have database uniqueness constraints", async () => {
  const { db, schema } = await import("../src/db/client");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-unique-artifacts",
    name: "Unique Artifacts",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.bibles).values({
    id: "bible-p0-unique-1",
    projectId: "project-p0-unique-artifacts",
    updatedAt: now,
  });
  await assert.rejects(
    () =>
      db.insert(schema.bibles).values({
        id: "bible-p0-unique-2",
        projectId: "project-p0-unique-artifacts",
        updatedAt: now,
      }),
    /unique/i
  );

  await db.insert(schema.rounds).values({
    id: "round-p0-unique-1",
    projectId: "project-p0-unique-artifacts",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    createdAt: now,
  });
  await assert.rejects(
    () =>
      db.insert(schema.rounds).values({
        id: "round-p0-unique-2",
        projectId: "project-p0-unique-artifacts",
        roundNum: 1,
        epRange: "EP01-EP05 copy",
        status: "done",
        createdAt: now,
      }),
    /unique/i
  );

  await db.insert(schema.episodes).values({
    id: "episode-p0-unique-1",
    projectId: "project-p0-unique-artifacts",
    roundId: "round-p0-unique-1",
    epNum: 1,
    status: "green",
    retryCount: 0,
    updatedAt: now,
  });
  await assert.rejects(
    () =>
      db.insert(schema.episodes).values({
        id: "episode-p0-unique-2",
        projectId: "project-p0-unique-artifacts",
        roundId: "round-p0-unique-1",
        epNum: 1,
        status: "green",
        retryCount: 0,
        updatedAt: now,
      }),
    /unique/i
  );
});

```
