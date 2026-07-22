# Fable 5 Current Full-Flow Review Pack
- Generated: 2026-07-06T23:17:08
- Requested model: anthropic/claude-fable-5 via OpenRouter
- Scope: current latest repository after P0/P1/P2 fixes, full novel-to-short-drama platform flow
- Important: Review the current state, not the older Fable findings stored under docs/reviews. Those earlier findings may now be fixed.

## Review Questions
1. Is the full workflow now coherent and safe enough for an ops MVP?
2. Find remaining P0/P1/P2 issues with exact file references.
3. Specifically evaluate: Story Bible reuse, run-all scheduling, job state visibility, retry/stale handling, migrations, webhook/payment safety, quality gates, baseline/A-B proof, source evidence, creative vs shooting output separation, and ops deployment.
4. Do not repeat old fixed issues unless they still exist in the current code.
5. Output verdict: ready / ready_with_followups / not_ready, plus precise next actions.

## Git State

```text
## codex/unify-platform-flow...origin/codex/unify-platform-flow
3da0c02 Harden platform generation workflow
3da0c02 Harden platform generation workflow
 README.md                                          |    1 +
 docs/PROMPT_SKILL_ARCHITECTURE.md                  |    1 +
 ...06-openrouter-fable5-response-continuation.json |  495 ++++
 .../2026-07-06-openrouter-fable5-response.json     |  615 +++++
 ...-07-06-openrouter-fable5-review-continuation.md |  106 +
 .../2026-07-06-openrouter-fable5-review-pack.md    | 2595 ++++++++++++++++++++
 .../2026-07-06-openrouter-fable5-review-summary.md |   89 +
 .../reviews/2026-07-06-openrouter-fable5-review.md |   49 +
 drizzle/migrations/0008_material_silvermane.sql    |   32 +
 drizzle/migrations/meta/0008_snapshot.json         | 2359 ++++++++++++++++++
 drizzle/migrations/meta/_journal.json              |    7 +
 package.json                                       |    2 +
 scripts/run-ts-tests.mjs                           |   27 +
 scripts/start-ops-server.sh                        |    2 +-
 scripts/start-ops-worker.sh                        |    2 +-
 src/app/api/health/route.ts                        |    7 +-
 src/app/api/platform/payments/webhook/route.ts     |    6 +-
 src/app/api/projects/[id]/control/route.ts         |   16 +-
 src/db/schema.ts                                   |   73 +-
 src/lib/engine-runner.ts                           |  162 +-
 src/lib/engine-types.ts                            |   13 +
 src/lib/jobs.ts                                    |   61 +-
 src/lib/platform-credits.ts                        |   20 +
 src/lib/project-controls.ts                        |    5 +
 src/novel_drama_engine/adaptation_quality.py       |   26 +-
 src/novel_drama_engine/drama_quality.py            |    2 +
 src/novel_drama_engine/models.py                   |   13 +
 src/novel_drama_engine/pipeline.py                 |   38 +-
 src/novel_drama_engine/prompts.py                  |   28 +-
 src/novel_drama_engine/source_evidence.py          |  169 +-
 tests/p0_platform.test.ts                          |  433 ++++
 tests/test_adaptation_quality.py                   |   12 +
 tests/test_drama_quality.py                        |   41 +-
 tests/test_pipeline.py                             |  142 +-
 tests/test_prompt_script_quality_contract.py       |   15 +-
 tests/test_source_evidence.py                      |  112 +-
 36 files changed, 7619 insertions(+), 157 deletions(-)
```

## Verification Already Run

```text
python3 -m pytest -q: PASS (224 tests)
npm run test:ts: PASS (13 tests)
npm run typecheck: PASS
npm run build: PASS
ops deploy: LaunchAgents running; /api/health 200 in real mode on local ops URL
```

## Top-Level File Map

```text
docs/OPERATIONS_MVP.md
docs/PITFALLS_AUDIT.md
docs/PROMPT_SKILL_ARCHITECTURE.md
docs/reviews/2026-07-06-openrouter-fable5-response-continuation.json
docs/reviews/2026-07-06-openrouter-fable5-response.json
docs/reviews/2026-07-06-openrouter-fable5-review-continuation.md
docs/reviews/2026-07-06-openrouter-fable5-review-pack.md
docs/reviews/2026-07-06-openrouter-fable5-review-summary.md
docs/reviews/2026-07-06-openrouter-fable5-review.md
docs/specs/2026-05-14-novel-to-drama-design.md
docs/superpowers/plans/2026-05-15-novel-to-drama-v0.md
docs/superpowers/plans/2026-06-30-novel-to-short-drama-mvp.md
docs/superpowers/plans/2026-07-02-internal-methodology-engine.md
docs/superpowers/specs/2026-06-30-novel-to-short-drama-mvp-design.md
docs/superpowers/specs/2026-07-02-internal-methodology-engine-design.md
drizzle/migrations/0000_bitter_magma.sql
drizzle/migrations/0001_warm_cable.sql
drizzle/migrations/0002_mature_blindfold.sql
drizzle/migrations/0003_dusty_inhumans.sql
drizzle/migrations/0004_living_ben_urich.sql
drizzle/migrations/0005_lush_magdalene.sql
drizzle/migrations/0006_swift_miek.sql
drizzle/migrations/0007_tough_hulk.sql
drizzle/migrations/0008_material_silvermane.sql
drizzle/migrations/meta/0000_snapshot.json
drizzle/migrations/meta/0001_snapshot.json
drizzle/migrations/meta/0002_snapshot.json
drizzle/migrations/meta/0003_snapshot.json
drizzle/migrations/meta/0004_snapshot.json
drizzle/migrations/meta/0005_snapshot.json
drizzle/migrations/meta/0006_snapshot.json
drizzle/migrations/meta/0007_snapshot.json
drizzle/migrations/meta/0008_snapshot.json
drizzle/migrations/meta/_journal.json
scripts/install-ops-launchagent.sh
scripts/ops-health-check.sh
scripts/ops-online-readiness.sh
scripts/run-ts-tests.mjs
scripts/start-ops-server.sh
scripts/start-ops-worker.sh
scripts/test-llm.ts
scripts/test-m1.ts
src/app/api/episodes/[id]/impact/route.ts
src/app/api/episodes/[id]/retry/route.ts
src/app/api/health/route.ts
src/app/api/jobs/[id]/retry/route.ts
src/app/api/jobs/route.ts
src/app/api/methodology/cards/[id]/route.ts
src/app/api/methodology/route.ts
src/app/api/platform/api-keys/[id]/route.ts
src/app/api/platform/api-keys/route.ts
src/app/api/platform/billing/route.ts
src/app/api/platform/checkout/[id]/complete/route.ts
src/app/api/platform/checkout/route.ts
src/app/api/platform/credits/route.ts
src/app/api/platform/members/[id]/route.ts
src/app/api/platform/members/route.ts
src/app/api/platform/payments/webhook/route.ts
src/app/api/platform/session/route.ts
src/app/api/platform/usage/route.ts
src/app/api/projects/[id]/bible/route.ts
src/app/api/projects/[id]/clone/route.ts
src/app/api/projects/[id]/control/route.ts
src/app/api/projects/[id]/delivery/route.ts
src/app/api/projects/[id]/export/route.ts
src/app/api/projects/[id]/localization/route.ts
src/app/api/projects/[id]/novel-export/route.ts
src/app/api/projects/[id]/rounds/start/route.ts
src/app/api/projects/[id]/route.ts
src/app/api/projects/[id]/video-brief/route.ts
src/app/api/projects/route.ts
src/app/api/quality-samples/route.ts
src/lib/anthropic.ts
src/lib/deployment-readiness.ts
src/lib/edit-impact.ts
src/lib/engine-runner.ts
src/lib/engine-types.ts
src/lib/job-worker.ts
src/lib/jobs.ts
src/lib/localization-profiles.ts
src/lib/m1-normalize.ts
src/lib/m2-bible.ts
src/lib/m3-round.ts
src/lib/m4-review.ts
src/lib/m5-format.ts
src/lib/m6-export.ts
src/lib/methodology.ts
src/lib/platform-billing.ts
src/lib/platform-context.ts
src/lib/platform-credits.ts
src/lib/platform-page-context.ts
src/lib/platform-route.ts
src/lib/platform-usage.ts
src/lib/project-controls.ts
src/lib/prompts/m1-judge.ts
src/lib/prompts/m2-bible.ts
src/lib/prompts/m3-adapt.ts
src/lib/prompts/m4-review.ts
src/lib/prompts/m5-format.ts
src/lib/round-runner.ts
src/lib/script-export.ts
src/lib/storage.ts
src/lib/utils.ts
src/novel_drama_engine/__init__.py
src/novel_drama_engine/adaptation_quality.py
src/novel_drama_engine/baseline.py
src/novel_drama_engine/batch.py
src/novel_drama_engine/cli.py
src/novel_drama_engine/delivery.py
src/novel_drama_engine/demo.py
src/novel_drama_engine/drama_quality.py
src/novel_drama_engine/evaluation.py
src/novel_drama_engine/llm.py
src/novel_drama_engine/localization.py
src/novel_drama_engine/methodology.py
src/novel_drama_engine/models.py
src/novel_drama_engine/pipeline.py
src/novel_drama_engine/prompts.py
src/novel_drama_engine/renderer.py
src/novel_drama_engine/rounds.py
src/novel_drama_engine/script_quality.py
src/novel_drama_engine/source_evidence.py
src/novel_drama_engine/source_packets.py
src/novel_drama_engine/source_strength.py
src/novel_drama_engine/storage.py
src/novel_drama_engine/trace_analysis.py
src/novel_drama_engine/video_brief.py
tests/conftest.py
tests/p0_platform.test.ts
tests/test_acceptance_fixtures.py
tests/test_adaptation_quality.py
tests/test_batch.py
tests/test_cli.py
tests/test_delivery.py
tests/test_drama_quality.py
tests/test_evaluation.py
tests/test_llm.py
tests/test_localization.py
tests/test_methodology.py
tests/test_models.py
tests/test_pipeline.py
tests/test_prompt_bible_state.py
tests/test_prompt_episode_plan.py
tests/test_prompt_professional_structure.py
tests/test_prompt_script_quality_contract.py
tests/test_prompt_source_context.py
tests/test_prompt_viral_series.py
tests/test_prompts.py
tests/test_renderer.py
tests/test_script_quality.py
tests/test_source_evidence.py
tests/test_source_packets.py
tests/test_source_strength.py
tests/test_storage.py
tests/test_trace_analysis.py
tests/test_video_brief.py
```

## File: `README.md`

```md
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
- `drama_engine_first`: th

<!-- truncated 4433 chars -->
```

## File: `docs/OPERATIONS_MVP.md`

```md
# 运营体验环境

这个环境用于让运营同学直接打开浏览器体验小说改编短剧脚本流程，不需要接触命令行。

## 访问地址

- 同一台 Mac: http://localhost:3000
- 同一局域网: http://MacBook-Pro.local:3000
- 局域网备用 IP: http://192.168.0.108:3000
- 健康检查: http://MacBook-Pro.local:3000/api/health

如果 `MacBook-Pro.local` 在某台电脑上打不开，优先使用备用 IP。备用 IP 会随网络变化，`.local` 地址通常更稳定。

## 当前体验模式

- 当前运营环境使用真实模型：OpenRouter `google/gemini-3.1-flash-lite`。
- 默认改编策略为「强剧情优先」：保留分集戏剧设计，跳过慢速 SOP 全剧结构规划。SOP 全链路作为慢速精修档保留给回归测试或小样本精修。
- 批量运行默认 5 集/轮，30 集项目会按 EP01-EP05、EP06-EP10 继续。
- Story Bible 由系统自动生成，不需要运营确认。
- 创建项目后自动启动第 1 轮，后续轮次根据原文和上一轮 context 继续。
- 后台会自动检查同轮跨集重复：如果多集只是换标题/换台词但场景骨架、动作链、对白句式或结尾钩子重复，会进入重写或人工复核。
- 平台里的点数、账单、API Key、成员管理是模板能力，首轮体验不用操作。

## 运营体验路径

1. 打开首页。
2. 点击新建项目。
3. 上传 txt/docx 小说，填写目标集数。
4. 等待第 1 轮完成。
5. 在轮次页查看脚本、质量分和 warning。
6. 继续下一轮，或进入完成页导出视频 brief、本地化包、交付预检和 zip。

## 项目控制

- 复制项目：在项目列表或轮次页点击「复制」，系统会复制小说原文、目标集数和项目配置，生成一个独立新项目，并自动启动第 1 轮。
- 暂停项目：点击「暂停项目」后，worker 不再领取该项目的新轮次任务。若当前 LLM 调用已经开始，会等当前 Engine 进程结束后停在下一轮边界，避免损坏中间产物。
- 继续项目：点击「继续项目」后，queued 任务会重新被 worker 领取；如果已开启批量运行，系统会继续补排下一轮。
- 批量运行：点击「批量运行」后，系统会在每轮完成后自动判断是否到达目标集数，未完成则自动排下一轮，不需要运营一轮一轮点。
- 按集可见：Engine 默认先生成连贯整轮首稿，再按集写入页面和做失败修复；整轮质量复检完成前状态显示为「生成中」，最终再更新为 green/red。

## 服务常驻方式

本机通过 macOS LaunchAgent 常驻运行：

- Label: `com.novel-to-drama.ops-web`
- 配置文件: `~/Library/LaunchAgents/com.novel-to-drama.ops-web.plist`
- 运行时目录: `~/.novel-to-drama-ops/app`
- 日志:
  - `~/.novel-to-drama-ops/app/logs/ops-web.out.log`
  - `~/.novel-to-drama-ops/app/logs/ops-web.err.log`

如果机器重启或用户重新登录，服务会自动启动。服务异常退出后也会自动拉起。
由于 macOS 对 `Documents` 目录有隐私限制，LaunchAgent 跑的是运行时副本。
源代码更新后，重新安装运营服务会同步最新代码到运行时目录。
Engine 命令统一使用 `python3 -m novel_drama_engine.cli` module 入口；`novel-drama`
只是 editable install 后的 console-script 简写。Web runner 默认使用 module 入口，
避免不同机器 PATH 不一致导致 worker 找不到命令。

## 模型配置

常驻环境的模型配置在本机私有文件
`~/.novel-to-drama-ops/secrets.env` 里配置，避免把 key 写入 git：

```bash
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_LLM_PROVIDER=openrouter
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=google/gemini-3.1-flash-lite
OPENAI_MAX_TOKENS=20000
OPENAI_TIMEOUT=300
NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS=240
NOVEL_DRAMA_GENERATION_VARIANT=drama_engine_first
NOVEL_DRAMA_DB_PATH=/Users/wangzipeng/.novel-to-drama-ops/app/db.sqlite
NOVEL_DRAMA_ACCESS_TOKEN=change-me
OPENAI_API_KEY=...
```

如果使用 Kimi/Moonshot API，配置 OpenAI-compatible endpoint：

```bash
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_LLM_PROVIDER=kimi
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-128k
OPENAI_MAX_TOKENS=20000
OPENAI_TIMEOUT=300
NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS=240
OPENAI_API_KEY=...
```

服务启动脚本会自动读取 `~/.novel-to-drama-ops/secrets.env`。

如需临时零成本演示，可把 `NOVEL_DRAMA_WEB_MOCK=1` 后重新安装运营服务。

## 上线就绪检查

访问 `/api/health` 可查看 `readiness`：

- `ready`: 可以上线。
- `warning`: 内测可用，但仍有上线前建议项。
- `blocked`: 不应公网开放。

也可以在部署机器上先跑一次静态检查：

```bash
npm run ops:online-readiness
```

这个命令会读取 `~/.novel-to-drama-ops/secrets.env`，强制按线上模式检查，并在 `readiness.status !== "ready"` 时返回失败。

公网或外部团队访问前建议配置：

```bash
NOVEL_DRAMA_ONLINE_MODE=1
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_REQUIRE_API_KEY=1
NOVEL_DRAMA_REQUIRE_CREDITS=1
NOVEL_DRAMA_DB_PATH=/persistent/novel-to-drama/db.sqlite
NOVEL_DRAMA_ACCESS_TOKEN=<shared-ops-access-token>
NOVEL_DRAMA_ACCESS_COOKIE_SECURE=1
```

如果只是给运营浏览器访问，`NOVEL_DRAMA_ACCESS_TOKEN` 已经会保护页面和 `/api/*`；如果后续开放外部程序调用，再开启 `NOVEL_DRAMA_REQUIRE_API_KEY=1`。

配置访问令牌后，首次打开：

```text
https://your-domain.example/?access_token=<shared-ops-access-token>
```

浏览器会写入 7 天 Cookie，之后无需在 URL 里继续带 token。

## 公网稳定 URL

当前这个版本解决的是“运营不用命令行，在同一网络打开稳定地址”。如果要外部人员访问公网 URL，需要再接一个托管平台：

- Render/Fly: 适合这个项目当前的 SQLite + 本地文件 + Node/Python 组合。
- Vercel: 页面托管方便，但当前后台 worker、SQLite 和文件存储需要改成托管 DB/对象存储。
- Cloudflare Tunnel/ngrok 固定域名: 最快给公网访问，但需要账号和固定域名配置。
```

## File: `docs/PROMPT_SKILL_ARCHITECTURE.md`

```md
# Prompt Skill Architecture

本项目的改编内核按内部 Skill 包组织，而不是把所有要求塞进一个大 prompt。
每个阶段都是一个可替换、可测试、可 A/B 的生产单元。

## Runtime Spine

固定主线：

```text
source analysis -> viral asset extraction -> episode/context resolver
-> system-owned Story Bible -> series structure -> episode drama plan
-> script generation -> quality gate -> state writeback
```

硬约束：

- Story Bible 由系统自动生成和维护，不走用户确认。
- 第二轮及后续轮次根据原文、目标集数和 previous_context 自动识别集数范围。
- Hook、main_emotion、watch_reason、消费理由只允许作为内部字段，不得出现在用户可见剧本文本里。
- 所有阶段必须遵守“原文资产分级 -> 钩子双模式 -> 改编许可边界”：先保护原文不可改资产，再做爆款化增强。
- 每集必须输出可拍摄正片，而不是剧情摘要、看点说明或营销文案。

## Source Fidelity Contract

每个 user prompt 都会注入通用改编合同，避免“为了爽点改坏原文”：

- C0 不可改事实：人物动机、主动方、因果顺序、关键决定、关系状态、已存在证据。
- C1 必保名场面：高刺激开场、强反差画面、情绪爆点、关键道具、原文金句、公开羞辱/打脸节点。
- C2 可视听化资产：内心戏、长叙述、环境描写、感官细节，可转成特写、OS、动作、音效、镜头遮挡。
- C3 可压缩资产：过渡、寒暄、背景补充、低信息支线，可合并进对白或动作。
- C4 禁止新增：会改变动机、主动方、决策时机、证据来源、人物性格、关系结论或剧情解法的编造内容。

开场钩子使用双模式：

- 原文有强钩子：保护核心张力，做合规视听化，不能删除或降级成普通开场。
- 原文无强钩子：补事实兼容型钩子，只能从 C0/C1/C2 推导，可做结果前置、冲突前置、信息差前置、道具前置、关系错位前置。

改编许可边界：

- 允许：前置、压缩、换场、合并低价值段落、增加镜头细节、补动作衔接、把内心戏转 OS/特写/沉默决定。
- 谨慎允许：补短对白、补反应镜头、补中间动作，但必须服务原文已有情绪或信息。
- 禁止：改变 C0；不得把深思熟虑改成临时起意、把被动承受改成主动索取、把克制决绝改成歇斯底里。

## Stage Contract

每个 stage prompt 必须包含以下结构：

- 岗位：本阶段的专业角色。
- Skill 边界：只消费本阶段输入资产，只产出 schema artifact，不越权。
- 任务：本阶段要完成的唯一目标。
- 专业方法：执行方法和判断顺序。
- 输出纪律：字段、格式、可被下游消费的要求。
- 验收门：输出前自检，不合格就在本阶段自修正。
- 失败模式：必须主动规避的问题。

每个 user prompt 必须包含以下结构：

- Skill 包运行规范
- 输入资产
- 决策顺序
- 执行步骤
- 输出契约
- 专业标准
- 验收门
- 失败修复
- 禁止事项

## Script Quality Gate

当前本地硬门槛：

- 单集 800-1700 字。
- 每集 2-5 场，优先 3 场。
- 每集至少 28 行用户可见 scene line。
- 每集至少 10 条 action。
- 每集至少 18 条 dialogue/os/vo。
- 至少 8 条 action 同时具备可执行景别和镜头运动。
- 至少 3 条 action 具备镜头衔接词。
- action 行必须尽量以 `△景别+运镜` 开头，例如：

```text
△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节。
```

禁止示例：

```text
△女主站在门口。
△突然有人冲进来。
△众人震惊。
```

## A/B Test Handles

优先从这些位置做 A/B：

- `GenerationVariant.CURRENT_DENSITY`
- `GenerationVariant.DRAMA_ENGINE_FIRST`
- `GenerationVariant.SOP_FULL_STACK`
- `EPISODE_PLAN_SYSTEM` 的戏剧工程强度
- `SCRIPT_SYSTEM` 的镜头密度和结尾钩子规则
- `QUALITY_SYSTEM` 的阻断阈值
- `script_quality.py` 的本地硬门槛
- `script_novelty_report` 的跨集重复/新鲜度硬门槛：场景骨架、动作链、对白句式、结尾钩子不能连续换皮
- `NOVEL_DRAMA_SCRIPT_EPISODE_FIRST=0` 的整轮首稿路径；设为 `1` 可测试逐集生成/失败修复，但要重点检查上下集承接
- `NOVEL_DRAMA_EXPERIMENT_MODE=1` 的无缓存追踪路径；每次 A/B 都要保留 `prompt_trace.json`、`raw_llm_output.jsonl`、`prompt_trace_analysis.md`
- `creative_script.md` vs `shooting_script.md` 的分离产物；前者评戏，后者评 AI 视频执行可拍性，不能混成一个门槛
- `source_evidence_report.md` 的 source span evidence；每个 retained asset 要能追到原文行、脚本行和改写原因，用来判断强原文轻改是否真的执行
- `quality_user` / `state_user` 默认消费 `script_batch_digest`，只给集数摘要、场景骨架、开头/结尾关键行和状态更新；完整剧本文本留在 artifact 与本地确定性 gate，避免 QA/状态回写 prompt 过载
- Story State Ledger 会把 previous_context 的 open hook 和同轮 episode cliffhanger 标为 open/closed：如果下一轮开头或下一集开头已承接则关闭；如果 next_round_context 没带最终钩子，会写 warning，防止下一轮开头丢承接

推荐 A/B 指标：

- 单集可见字数
- action / dialogue / OS / VO 行数
- 镜头衔接行数
- 内部字段外露次数
- 结尾钩子是否在最后 2 行演出
- 目标集数覆盖率
- 题材模板错配次数
- 跨集重复/新鲜度分：相邻或同轮任意两集的场景骨架、动作链、对白句式、结尾钩子相似度
- C0 被改动次数
- C1 天然钩子/名场面丢失次数
- C4 编造动作/道具/狠话次数
- prompt_trace_analysis 的 suspected_failure_stage
- baseline_comparison_report 的 pipeline_vs_direct verdict
```

## File: `package.json`

```json
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

## File: `scripts/install-ops-launchagent.sh`

```sh
#!/bin/zsh
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${NOVEL_DRAMA_OPS_RUNTIME:-$HOME/.novel-to-drama-ops/app}"
PLIST_NAMES=(
  "com.novel-to-drama.ops-web.plist"
  "com.novel-to-drama.ops-worker.plist"
  "com.novel-to-drama.ops-quality-worker.plist"
)
USER_ID="$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$RUNTIME_ROOT"

if [ "${NOVEL_DRAMA_FORCE_DEPLOY_DURING_JOBS:-0}" != "1" ] && [ -f "$RUNTIME_ROOT/db.sqlite" ]; then
  ACTIVE_JOBS="$(
    RUNTIME_ROOT="$RUNTIME_ROOT" python3 - <<'PY'
import os
import sqlite3

db_path = os.path.join(os.environ["RUNTIME_ROOT"], "db.sqlite")
try:
    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        """
        select title, kind, updated_at
        from jobs
        where status = 'running'
        order by datetime(updated_at) desc
        limit 10
        """
    ).fetchall()
finally:
    try:
        connection.close()
    except Exception:
        pass

for title, kind, updated_at in rows:
    print(f"{kind}\t{updated_at}\t{title}")
PY
  )"
  if [ -n "$ACTIVE_JOBS" ]; then
    cat >&2 <<EOF
Refusing to deploy while jobs are running.

Active jobs:
$ACTIVE_JOBS

Wait for the current round to finish, or set NOVEL_DRAMA_FORCE_DEPLOY_DURING_JOBS=1 to force.
EOF
    exit 3
  fi
fi

rsync -a --delete \
  --exclude ".git/" \
  --exclude ".next/" \
  --exclude "node_modules/" \
  --exclude "logs/" \
  --exclude "storage/" \
  --exclude ".drama_mock/" \
  --exclude ".pytest_cache/" \
  --exclude "*.sqlite" \
  --exclude "*.sqlite-shm" \
  --exclude "*.sqlite-wal" \
  --exclude "*.sqlite-journal" \
  "$SOURCE_ROOT/" "$RUNTIME_ROOT/"

mkdir -p "$RUNTIME_ROOT/logs"
rm -rf "$RUNTIME_ROOT/.next"

chmod +x \
  "$RUNTIME_ROOT/scripts/start-ops-server.sh" \
  "$RUNTIME_ROOT/scripts/start-ops-worker.sh" \
  "$RUNTIME_ROOT/scripts/ops-health-check.sh" \
  "$RUNTIME_ROOT/scripts/ops-online-readiness.sh"

for PLIST_NAME in "${PLIST_NAMES[@]}"; do
  PLIST_SOURCE="$RUNTIME_ROOT/ops/$PLIST_NAME"
  PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"
  LABEL="${PLIST_NAME%.plist}"

  if [ ! -f "$PLIST_SOURCE" ]; then
    echo "Missing $PLIST_SOURCE" >&2
    exit 1
  fi

  cp "$PLIST_SOURCE" "$PLIST_TARGET"
  chmod 644 "$PLIST_TARGET"

  launchctl bootout "gui/$USER_ID" "$PLIST_TARGET" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$USER_ID" "$PLIST_TARGET"
  launchctl kickstart -k "gui/$USER_ID/$LABEL"

  echo "Installed $LABEL"
done
echo "Runtime: $RUNTIME_ROOT"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
LOCAL_NAME="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
if [ -n "$LAN_IP" ]; then
  echo "URL: http://$LAN_IP:3000"
  echo "mDNS fallback: http://$LOCAL_NAME.local:3000"
else
  echo "URL: http://$LOCAL_NAME.local:3000"
fi
```

## File: `scripts/start-ops-server.sh`

```sh
#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PRIVATE_ENV="$HOME/.novel-to-drama-ops/secrets.env"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  source "$PRIVATE_ENV"
  set +a
fi

export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export NODE_ENV="${NODE_ENV:-production}"
export PORT="${PORT:-3000}"
export OPS_HOST="${OPS_HOST:-::}"
export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"
export NOVEL_DRAMA_AUTO_WORKER="${NOVEL_DRAMA_AUTO_WORKER:-0}"
export NOVEL_DRAMA_DB_PATH="${NOVEL_DRAMA_DB_PATH:-$ROOT_DIR/db.sqlite}"
export NOVEL_DRAMA_USER_EMAIL="${NOVEL_DRAMA_USER_EMAIL:-ops@novel-drama.local}"
export NOVEL_DRAMA_TENANT_SLUG="${NOVEL_DRAMA_TENANT_SLUG:-ops-demo}"
export NOVEL_DRAMA_TENANT_NAME="${NOVEL_DRAMA_TENANT_NAME:-Ops Demo Workspace}"
export NOVEL_DRAMA_BACKFILL_LEGACY_TENANT="${NOVEL_DRAMA_BACKFILL_LEGACY_TENANT:-1}"
export NOVEL_DRAMA_REQUIRE_API_KEY="${NOVEL_DRAMA_REQUIRE_API_KEY:-0}"
export NOVEL_DRAMA_REQUIRE_CREDITS="${NOVEL_DRAMA_REQUIRE_CREDITS:-0}"
export NOVEL_DRAMA_INTERNAL_PROJECT_LIMIT="${NOVEL_DRAMA_INTERNAL_PROJECT_LIMIT:-500}"
export NOVEL_DRAMA_INTERNAL_MONTHLY_JOB_LIMIT="${NOVEL_DRAMA_INTERNAL_MONTHLY_JOB_LIMIT:-5000}"
export NOVEL_DRAMA_GENERATION_VARIANT="${NOVEL_DRAMA_GENERATION_VARIANT:-drama_engine_first}"
export NOVEL_DRAMA_REPAIR_BUDGET="${NOVEL_DRAMA_REPAIR_BUDGET:-episode}"
export NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS="${NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS:-240}"
export NOVEL_DRAMA_ENGINE_TIMEOUT_MS="${NOVEL_DRAMA_ENGINE_TIMEOUT_MS:-1800000}"

if [ -x "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
  export NOVEL_DRAMA_PYTHON="${NOVEL_DRAMA_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.14/bin/python3}"
fi

if [ ! -x "node_modules/.bin/next" ] || [ ! -x "node_modules/.bin/drizzle-kit" ]; then
  npm install --include=dev
fi

npm run db:migrate

if [ ! -f ".next/BUILD_ID" ]; then
  npm run build
fi

exec npm run start -- -H "$OPS_HOST" -p "$PORT"
```

## File: `scripts/start-ops-worker.sh`

```sh
#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PRIVATE_ENV="$HOME/.novel-to-drama-ops/secrets.env"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  source "$PRIVATE_ENV"
  set +a
fi

export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export NODE_ENV="${NODE_ENV:-production}"
export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"
export NOVEL_DRAMA_AUTO_WORKER="0"
export NOVEL_DRAMA_DB_PATH="${NOVEL_DRAMA_DB_PATH:-$ROOT_DIR/db.sqlite}"
export NOVEL_DRAMA_USER_EMAIL="${NOVEL_DRAMA_USER_EMAIL:-ops@novel-drama.local}"
export NOVEL_DRAMA_TENANT_SLUG="${NOVEL_DRAMA_TENANT_SLUG:-ops-demo}"
export NOVEL_DRAMA_TENANT_NAME="${NOVEL_DRAMA_TENANT_NAME:-Ops Demo Workspace}"
export NOVEL_DRAMA_BACKFILL_LEGACY_TENANT="${NOVEL_DRAMA_BACKFILL_LEGACY_TENANT:-1}"
export NOVEL_DRAMA_REQUIRE_API_KEY="${NOVEL_DRAMA_REQUIRE_API_KEY:-0}"
export NOVEL_DRAMA_REQUIRE_CREDITS="${NOVEL_DRAMA_REQUIRE_CREDITS:-0}"
export NOVEL_DRAMA_INTERNAL_PROJECT_LIMIT="${NOVEL_DRAMA_INTERNAL_PROJECT_LIMIT:-500}"
export NOVEL_DRAMA_INTERNAL_MONTHLY_JOB_LIMIT="${NOVEL_DRAMA_INTERNAL_MONTHLY_JOB_LIMIT:-5000}"
export NOVEL_DRAMA_GENERATION_VARIANT="${NOVEL_DRAMA_GENERATION_VARIANT:-drama_engine_first}"
export NOVEL_DRAMA_REPAIR_BUDGET="${NOVEL_DRAMA_REPAIR_BUDGET:-episode}"
export NOVEL_DRAMA_SCRIPT_EPISODE_FIRST="${NOVEL_DRAMA_SCRIPT_EPISODE_FIRST:-0}"
export NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS="${NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS:-240}"
export NOVEL_DRAMA_ENGINE_TIMEOUT_MS="${NOVEL_DRAMA_ENGINE_TIMEOUT_MS:-1800000}"
export NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING="${NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING:-1}"
export NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS="${NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS:-0}"

if [ -x "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
  export NOVEL_DRAMA_PYTHON="${NOVEL_DRAMA_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.14/bin/python3}"
fi

if [ ! -x "node_modules/.bin/tsx" ] || [ ! -x "node_modules/.bin/drizzle-kit" ]; then
  npm install --include=dev
fi

npm run db:migrate

JOB_ARGS=("--poll-ms" "${NOVEL_DRAMA_JOB_POLL_MS:-2000}")
if [ -n "${NOVEL_DRAMA_JOB_KIND:-}" ]; then
  JOB_ARGS=("--kind" "$NOVEL_DRAMA_JOB_KIND" "${JOB_ARGS[@]}")
fi

exec npm run jobs:watch -- "${JOB_ARGS[@]}"
```

## File: `scripts/run-ts-tests.mjs`

```mjs
import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const testsDir = path.join(repoRoot, "tests");
const files = readdirSync(testsDir)
  .filter((file) => file.endsWith(".test.ts"))
  .sort()
  .map((file) => path.join("tests", file));

if (files.length === 0) {
  console.error("No TypeScript test files found under tests/*.test.ts");
  process.exit(1);
}

const result = spawnSync(
  process.execPath,
  ["--test", "--import", "tsx", ...files],
  {
    cwd: repoRoot,
    stdio: "inherit",
  }
);

process.exit(result.status ?? 1);
```

## File: `scripts/ops-online-readiness.sh`

```sh
#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PRIVATE_ENV="${NOVEL_DRAMA_OPS_SECRETS:-$HOME/.novel-to-drama-ops/secrets.env}"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  source "$PRIVATE_ENV"
  set +a
fi

export NODE_ENV="${NODE_ENV:-production}"
export NOVEL_DRAMA_ONLINE_MODE="${NOVEL_DRAMA_ONLINE_MODE:-1}"
export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"

if [ ! -x "node_modules/.bin/tsx" ]; then
  npm install --include=dev
fi

node_modules/.bin/tsx -e '
  import { deploymentReadiness } from "./src/lib/deployment-readiness";

  const readiness = deploymentReadiness();
  console.log(JSON.stringify(readiness, null, 2));
  process.exit(readiness.status === "ready" ? 0 : 1);
'
```

## File: `src/db/schema.ts`

```ts
import { sql } from "drizzle-orm";
import {
  sqliteTable,
  text,
  integer,
  real,
  uniqueIndex,
} from "drizzle-orm/sqlite-core";

export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull(),
  name: text("name"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const tenants = sqliteTable("tenants", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull(),
  name: text("name").notNull(),
  projectLimit: integer("project_limit").notNull().default(25),
  monthlyJobLimit: integer("monthly_job_limit").notNull().default(200),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const billingPlans = sqliteTable("billing_plans", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull(),
  name: text("name").notNull(),
  monthlyPriceCents: integer("monthly_price_cents").notNull().default(0),
  currency: text("currency").notNull().default("USD"),
  projectLimit: integer("project_limit").notNull().default(25),
  monthlyJobLimit: integer("monthly_job_limit").notNull().default(200),
  includedBillableUnits: integer("included_billable_units")
    .notNull()
    .default(100),
  overageUnitPriceCents: integer("overage_unit_price_cents")
    .notNull()
    .default(0),
  featuresJson: text("features_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const tenantSubscriptions = sqliteTable("tenant_subscriptions", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  planId: text("plan_id")
    .notNull()
    .references(() => billingPlans.id),
  status: text("status", {
    enum: ["active", "trialing", "past_due", "canceled"],
  })
    .notNull()
    .default("active"),
  currentPeriodStart: integer("current_period_start", {
    mode: "timestamp_ms",
  }).notNull(),
  currentPeriodEnd: integer("current_period_end", {
    mode: "timestamp_ms",
  }).notNull(),
  canceledAt: integer("canceled_at", { mode: "timestamp_ms" }),
  externalCustomerId: text("external_customer_id"),
  externalSubscriptionId: text("external_subscription_id"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentCustomers = sqliteTable("payment_customers", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  externalCustomerId: text("external_customer_id"),
  billingEmail: text("billing_email"),
  status: text("status", { enum: ["active", "disabled"] })
    .notNull()
    .default("active"),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const creditPackages = sqliteTable("credit_packages", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull(),
  name: text("name").notNull(),
  credits: integer("credits").notNull(),
  priceCents: integer("price_cents").notNull(),
  currency: text("currency").notNull().default("USD"),
  active: integer("active", { mode: "boolean" }).notNull().default(true),
  sortOrder: integer("sort_order").notNull().default(0),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const tenantMembers = sqliteTable("tenant_members", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  role: text("role", { enum: ["owner", "admin", "member"] })
    .notNull()
    .default("owner"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const apiKeys = sqliteTable("api_keys", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  createdByUserId: text("created_by_user_id").references(() => users.id, {
    onDelete: "set null",
  }),
  name: text("name").notNull(),
  keyPrefix: text("key_prefix").notNull(),
  keyHash: text("key_hash").notNull(),
  lastUsedAt: integer("last_used_at", { mode: "timestamp_ms" }),
  revokedAt: integer("revoked_at", { mode: "timestamp_ms" }),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const projects = sqliteTable("projects", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  ownerUserId: text("owner_user_id").references(() => users.id, {
    onDelete: "set null",
  }),
  name: text("name").notNull(),
  pipelineType: text("pipeline_type", { enum: ["A", "B"] }).notNull().default("A"),
  novelText: text("novel_text").notNull(),
  metaJson: text("meta_json"),
  targetLanguage: text("target_language"),
  targetEpisodeCount: integer("target_episode_count").notNull(),
  status: text("status", {
    enum: ["draft", "bible_ready", "running", "paused", "done", "failed"],
  })
    .notNull()
    .default("draft"),
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
  })
    .notNull()
    .default("pending"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const jobs = sqliteTable(
  "jobs",
  {
    id: text("id").primaryKey(),
    kind: text("kind", {
      enum: ["round_generation", "quality_samples"],
    }).notNull(),
    status: text("status", {
      enum: ["queued", "running", "succeeded", "failed"],
    })
      .notNull()
      .default("queued"),
    projectId: text("project_id").references(() => projects.id, {
      onDelete: "cascade",
    }),
    tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
    roundId: text("round_id").references(() => rounds.id, { onDelete: "set null" }),
    title: text("title").notNull(),
    progress: integer("progress").notNull().default(0),
    message: text("message"),
    errorText: text("error_text"),
    payloadJson: text("payload_json"),
    resultJson: text("result_json"),
    attempts: integer("attempts").notNull().default(0),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
    startedAt: integer("started_at", { mode: "timestamp_ms" }),
    finishedAt: integer("finished_at", { mode: "timestamp_ms" }),
  },
  (table) => [
    uniqueIndex("jobs_active_round_generation_unique")
      .on(table.roundId)
      .where(
        sql`${table.kind} = 'round_generation' and ${table.roundId} is not null and ${table.status} in ('queued', 'running')`
      ),
  ]
);

export const usageEvents = sqliteTable("usage_events", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  userId: text("user_id").references(() => users.id, { onDelete: "set null" }),
  apiKeyId: text("api_key_id").references(() => apiKeys.id, {
    onDelete: "set null",
  }),
  projectId: text("project_id").references(() => projects.id, {
    onDelete: "set null",
  }),
  jobId: text("job_id").references(() => jobs.id, { onDelete: "set null" }),
  eventType: text("event_type", {
    enum: [
      "project_create",
      "round_start",
      "quality_samples_start",
      "video_brief_export",
      "localization_export",
      "delivery_preflight",
      "delivery_export",
      "episode_txt_export",
      "episode_word_export",
    ],
  }).notNull(),
  quantity: integer("quantity").notNull().default(1),
  billableUnits: integer("billable_units").notNull().default(0),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

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

export const paymentCheckoutSessions = sqliteTable("payment_checkout_sessions", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  packageId: text("package_id").references(() => creditPackages.id, {
    onDelete: "set null",
  }),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  status: text("status", {
    enum: ["open", "paid", "expired", "canceled"],
  })
    .notNull()
    .default("open"),
  credits: integer("credits").notNull(),
  amountCents: integer("amount_cents").notNull(),
  currency: text("currency").notNull().default("USD"),
  checkoutUrl: text("checkout_url"),
  externalSessionId: text("external_session_id"),
  metadataJson: text("metadata_json"),
  expiresAt: integer("expires_at", { mode: "timestamp_ms" }),
  completedAt: integer("completed_at", { mode: "timestamp_ms" }),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentInvoices = sqliteTable("payment_invoices", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  checkoutSessionId: text("checkout_session_id").references(
    () => paymentCheckoutSessions.id,
    { onDelete: "set null" }
  ),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  status: text("status", {
    enum: ["draft", "open", "paid", "void", "refunded"],
  })
    .notNull()
    .default("paid"),
  credits: integer("credits").notNull(),
  amountCents: integer("amount_cents").notNull(),
  currency: text("currency").notNull().default("USD"),
  externalInvoiceId: text("external_invoice_id"),
  hostedInvoiceUrl: text("hosted_invoice_url"),
  metadataJson: text("metadata_json"),
  paidAt: integer("paid_at", { mode: "timestamp_ms" }),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentWebhookEvents = sqliteTable("payment_webhook_events", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, {
    onDelete: "set null",
  }),
  checkoutSessionId: text("checkout_session_id").references(
    () => paymentCheckoutSessions.id,
    { onDelete: "set null" }
  ),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  eventType: text("event_type").notNull(),
  status: text("status", {
    enum: ["received", "processed", "failed"],
  })
    .notNull()
    .default("received"),
  externalEventId: text("external_event_id"),
  payloadJson: text("payload_json"),
  errorText: text("error_text"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  processedAt: integer("processed_at", { mode: "timestamp_ms" }),
});

export const creditLedger = sqliteTable("credit_ledger", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  userId: text("user_id").references(() => users.id, { onDelete: "set null" }),
  sourceType: text("source_type", {
    enum: [
      "monthly_grant",
      "top_up",
      "usage_debit",
      "manual_adjustment",
      "refund",
    ],
  }).notNull(),
  creditsDelta: integer("credits_delta").notNull(),
  balanceAfter: integer("balance_after").notNull(),
  usageEventId: text("usage_event_id").references(() => usageEvents.id, {
    onDelete: "set null",
  }),
  checkoutSessionId: text("checkout_session_id").references(
    () => paymentCheckoutSessions.id,
    { onDelete: "set null" }
  ),
  invoiceId: text("invoice_id").references(() => paymentInvoices.id, {
    onDelete: "set null",
  }),
  referenceKey: text("reference_key"),
  metadataJson: text("metadata_json"),
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
  })
    .notNull()
    .default("pending"),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});
```

## File: `drizzle/migrations/0008_material_silvermane.sql`

```sql
WITH ranked_active_round_generation_jobs AS (
  SELECT
    "id",
    row_number() OVER (
      PARTITION BY "round_id"
      ORDER BY "updated_at" DESC, "created_at" DESC, "id" DESC
    ) AS "active_rank"
  FROM "jobs"
  WHERE "kind" = 'round_generation'
    AND "round_id" IS NOT NULL
    AND "status" IN ('queued', 'running')
)
UPDATE "jobs"
SET
  "status" = 'failed',
  "progress" = 100,
  "error_text" = COALESCE(
    "error_text",
    'round_generation dedup migration: superseded by a newer active job for the same round'
  ),
  "finished_at" = COALESCE(
    "finished_at",
    CAST(strftime('%s', 'now') AS INTEGER) * 1000
  ),
  "updated_at" = CAST(strftime('%s', 'now') AS INTEGER) * 1000
WHERE "id" IN (
  SELECT "id"
  FROM ranked_active_round_generation_jobs
  WHERE "active_rank" > 1
);
--> statement-breakpoint
CREATE UNIQUE INDEX `jobs_active_round_generation_unique` ON `jobs` (`round_id`) WHERE "jobs"."kind" = 'round_generation' and "jobs"."round_id" is not null and "jobs"."status" in ('queued', 'running');
```

## File: `src/lib/engine-runner.ts`

```ts
import fs from "fs/promises";
import path from "path";
import { spawn } from "child_process";
import { v4 as uuid } from "uuid";
import { and, desc, eq, ne } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { ensureProjectDir, ensureSystemDir, projectDir } from "./storage";
import { writeEpisodeTxt } from "./m6-export";
import { assertTenantJobQuota } from "./platform-context";
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
  qualityAverage,
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
};

type QualitySamplesPayload = {
  rounds: number;
  variants?: string[];
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
};

type RoundQualityGate = {
  status: QualityStatus | null;
  rewriteInstruction: string | null;
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

export function realEngineConfigProblem(): string | null {
  if (shouldUseMockEngine()) return null;
  if (!process.env.OPENAI_API_KEY) {
    return "OPENAI_API_KEY is not set while real Engine mode is enabled";
  }
  if (!process.env.OPENAI_MODEL) {
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
  const score = qualityAverage(result.quality_report);
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
      score,
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

  const latestProject = await db.query.projects.findFirst({
    where: eq(schema.projects.id, project.id),
  });
  const targetReached =
    result.next_round_context.current_episode >= project.targetEpisodeCount;
  const projectStatus = targetReached
    ? "done"
    : latestProject?.status === "paused"
      ? "paused"
      : "running";
  await db
    .update(schema.projects)
    .set({ status: projectStatus, updatedAt: new Date() })
    .where(eq(schema.projects.id, project.id));
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
    const configProblem = realEngineConfigProblem();
    if (configProblem) throw new Error(configProblem);
    await updateJob(jobId, {
      message: `准备小说原文和 Engine 工作目录 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集`,
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
    await fs.writeFile(sourcePath, project.novelText, "utf-8");

    const args = [
      "run",
      "--input",
      sourcePath,
      "--project-dir",
      engineDir,
      "--project-id",
      project.id,
      "--round-number",
      String(roundNumber),
      "--target-episode-count",
      String(project.targetEpisodeCount),
      "--episodes-per-round",
      String(selectedEpisodesPerRound),
      "--generation-variant",
      selectedGenerationVariant,
      "--repair-budget",
      selectedRepairBudget,
    ];
    if (methodologyCards.path) {
      args.push("--methodology-cards", methodologyCards.path);
    }
    if (shouldUseMockEngine()) args.push("--mock");

    await updateJob(jobId, {
      message:
        methodologyCards.path && methodologyCards.totalCount > 0
          ? `调用 Engine 生成轮次脚本 · active 方法卡 ${methodologyCards.activeCount}/${methodologyCards.totalCount}`
          : "调用 Engine 生成轮次脚本",
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
  const job = await createJob({
    kind: "round_generation",
    title: `${project.name} · 第 ${roundNumber} 轮 · ${selectedEpisodesPerRound}集`,
    projectId,
    tenantId: project.tenantId,
    roundId,
    message: `等待 worker 执行 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集`,
    payload: {
      projectId,
      roundId,
      roundNumber,
      generationVariant: selectedGenerationVariant,
      repairBudget: selectedRepairBudget,
      episodesPerRound: selectedEpisodesPerRound,
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
  const output = path.join(
    /*turbopackIgnore: true*/
    projectDir(projectId),
    `delivery_round_${String(resolvedRoundNumber).padStart(3, "0")}.zip`
  );
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

export async function getQualitySampleEvaluation(
  tenantId?: string
): Promise<QualitySampleEvaluationPayload> {
  const projectsDir = await qualityEvaluationDir(tenantId);
  const reportPath = path.join(
    /*turbopackIgnore: true*/
    projectsDir,
    qualitySampleReportName()
  );

  let report: QualitySampleEvaluationPayload["report"] = null;
  let updatedAt: string | null = null;
  try {
    const [raw, stat] = await Promise.all([
      fs.readFile(reportPath, "utf-8"),
      fs.stat(reportPath),
    ]);
    report = JSON.parse(raw) as QualitySampleEvaluationPayload["report"];
    updatedAt = stat.mtime.toISOString();
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code !== "ENOENT") throw error;
  }

  return {
    report,
    jobs: await listJobViews({ tenantId, kind: "quality_samples", limit: 8 }),
    reportPath,
    projectsDir,
    samplesPath: qualitySamplesPath(),
    updatedAt,
    mode: shouldUseMockEngine() ? "mock" : "real",
  };
}

async function executeQualitySampleEvaluation(
  rounds: number,
  jobId: string,
  tenantId?: string,
  variants?: string[]
): Promise<void> {
  const projectsDir = await qualityEvaluationDir(tenantId);
  const normalizedRounds = Math.max(1, Math.floor(rounds));
  const samplesPath = qualitySamplesPath();
  const selectedRepairBudget = qualitySampleRepairBudget();
  const selectedVariants = normalizeGenerationVariants(variants);
  const args = [
    "evaluate-samples",
    "--samples",
    samplesPath,
    "--projects-dir",
    projectsDir,
    "--rounds",
    String(normalizedRounds),
    "--generation-variants",
    selectedVariants.join(","),
    "--repair-budget",
    selectedRepairBudget,
  ];
  if (shouldUseMockEngine()) args.push("--mock");

  try {
    const startedAt = Date.now();
    const targets = await qualitySampleTargets(
      samplesPath,
      projectsDir,
      normalizedRounds,
      selectedVariants
    );
    await clearQualitySampleArtifacts(
      targets,
      path.join(projectsDir, qualitySampleReportName())
    );
    const progressSync = createQualitySampleProgressSync({
      jobId,
      targets,
      freshAfter: new Date(startedAt - 1000),
    });
    await updateJob(jobId, {
      message: "运行内部模型/Prompt 回归测试",
      progress: 25,
    });
    try {
      await runNovelDrama(args, { timeoutMs: qualitySampleTimeoutMs() });
    } finally {
      await progressSync.tick();
      progressSync.stop();
    }
    const runtimeMs = Date.now() - startedAt;
    const payload = await getQualitySampleEvaluation(tenantId);
    await succeedJob(jobId, {
      message: "内部回归测试完成",
      result: {
        passed: payload.report?.samples.filter((sample) =>
          sample.rounds.every((round) => round.warnings.length === 0)
        ).length,
        total: payload.report?.samples.length ?? 0,
        rounds: normalizedRounds,
        variants: selectedVariants,
        repairBudget: selectedRepairBudget,
        runtimeMs,
        reportPath: payload.reportPath,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const failure = classifyJobFailureText(message);
    await failJob(jobId, error, {
      message: failure?.userMessage ?? "内部回归失败",
      errorText: failure
        ? `${failure.userMessage}。${failure.operatorHint}`
        : message,
      result: {
        failureCategory: failure?.category ?? "engine_error",
        operatorHint:
          failure?.operatorHint ??
          "查看 quality worker 日志和样本 runtime_report 后重试。",
        reportPath: path.join(projectsDir, qualitySampleReportName()),
        projectsDir,
        variants: selectedVariants,
        rounds: normalizedRounds,
      },
    });
    console.error("[quality-samples] failed:", error);
  }
}

export async function executeQualitySampleJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<QualitySamplesPayload>(job);
  await executeQualitySampleEvaluation(
    payload.rounds,
    job.id,
    job.tenantId ?? undefined,
    payload.variants
  );
}

export async function executePlatformJob(job: JobRow): Promise<void> {
  if (job.kind === "round_generation") {
    await executeEngineRoundJob(job);
    return;
  }
  if (job.kind === "quality_samples") {
    await executeQualitySampleJob(job);
    return;
  }
  throw new Error(`Unsupported job kind: ${job.kind}`);
}

export async function startQualitySampleEvaluation(
  rounds = 2,
  tenantId?: string,
  variants?: string[]
): Promise<QualitySampleEvaluationPayload> {
  const normalizedRounds = Math.max(1, Math.floor(rounds));
  const selectedVariants = normalizeGenerationVariants(variants);
  if (tenantId) await assertTenantJobQuota(tenantId);
  const job = await createJob({
    kind: "quality_samples",
    tenantId,
    title: `内部回归测试 · ${normalizedRounds} 轮 · ${selectedVariants.join("/")}`,
    message: "等待低优先级 worker 执行",
    payload: {
      rounds: normalizedRounds,
      variants: selectedVariants,
    } satisfies QualitySamplesPayload,
  });

  return getQualitySampleEvaluation(tenantId);
}
```

## File: `src/lib/jobs.ts`

```ts
import { and, asc, desc, eq, inArray, lt, type SQL } from "drizzle-orm";
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
  message?: string | null;
  payload?: unknown;
  status?: JobStatus;
  progress?: number;
}): Promise<JobRow> {
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
    if (candidate.kind === "round_generation" && candidate.projectId) {
      const project = await db.query.projects.findFirst({
        where: eq(schema.projects.id, candidate.projectId),
      });
      if (project?.status === "paused") continue;
    }

    const now = new Date();
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
  kind,
  limit = 20,
}: {
  projectId?: string;
  tenantId?: string;
  kind?: JobKind;
  limit?: number;
} = {}): Promise<JobRow[]> {
  await reconcileStaleJobs();
  const filters: SQL[] = [];
  if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
  if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
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

## File: `src/lib/project-controls.ts`

```ts
import { desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";

type ProjectRow = typeof schema.projects.$inferSelect;

export type RunAllSettings = {
  enabled: boolean;
  generationVariant?: string | null;
  repairBudget?: string | null;
  requestedAt?: string;
  pausedAt?: string;
  pausedReason?: string | null;
  pausedRound?: number | null;
  pausedQualityStatus?: string | null;
  pausedRewriteInstruction?: string | null;
};

export type ProjectControlMeta = Record<string, unknown> & {
  control?: {
    runAll?: RunAllSettings;
  };
  clonedFromProjectId?: string;
  archivedAt?: string | null;
  archivedReason?: string | null;
};

type RoundSummary = {
  next_round_context?: {
    current_episode?: number;
  };
};

export function parseProjectMeta(metaJson: string | null): ProjectControlMeta {
  if (!metaJson) return {};
  try {
    const parsed = JSON.parse(metaJson) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as ProjectControlMeta;
    }
  } catch {
    return {};
  }
  return {};
}

export function serializeProjectMeta(meta: ProjectControlMeta): string {
  return JSON.stringify(meta, null, 2);
}

export function projectRunAllSettings(project: ProjectRow): RunAllSettings {
  const meta = parseProjectMeta(project.metaJson);
  const settings = meta.control?.runAll;
  return {
    enabled: settings?.enabled === true,
    generationVariant: settings?.generationVariant ?? null,
    repairBudget: settings?.repairBudget ?? null,
    requestedAt: settings?.requestedAt,
  };
}

export function projectArchivedAt(project: Pick<ProjectRow, "metaJson">): string | null {
  const meta = parseProjectMeta(project.metaJson);
  return typeof meta.archivedAt === "string" && meta.archivedAt
    ? meta.archivedAt
    : null;
}

export function isProjectArchived(project: Pick<ProjectRow, "metaJson">): boolean {
  return Boolean(projectArchivedAt(project));
}

export async function updateProjectMeta(
  projectId: string,
  updater: (meta: ProjectControlMeta) => ProjectControlMeta
): Promise<ProjectControlMeta> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  const nextMeta = updater(parseProjectMeta(project.metaJson));
  await db
    .update(schema.projects)
    .set({ metaJson: serializeProjectMeta(nextMeta), updatedAt: new Date() })
    .where(eq(schema.projects.id, projectId));
  return nextMeta;
}

export function currentEpisodeFromRoundSummary(summaryJson: string | null): number | null {
  if (!summaryJson) return null;
  try {
    const summary = JSON.parse(summaryJson) as RoundSummary;
    const current = summary.next_round_context?.current_episode;
    return Number.isFinite(current) ? Number(current) : null;
  } catch {
    return null;
  }
}

export async function latestRoundForProject(projectId: string) {
  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, projectId),
    orderBy: [desc(schema.rounds.roundNum)],
    limit: 1,
  });
  return rounds[0] ?? null;
}

export async function projectNeedsNextRound(project: ProjectRow): Promise<boolean> {
  if (project.status === "paused" || project.status === "done" || project.status === "failed") {
    return false;
  }
  const latest = await latestRoundForProject(project.id);
  if (latest && latest.status !== "done") return false;
  const currentEpisode = currentEpisodeFromRoundSummary(latest?.summaryJson ?? null);
  return currentEpisode == null || currentEpisode < project.targetEpisodeCount;
}
```

## File: `src/lib/platform-credits.ts`

```ts
import { and, desc, eq } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { PlatformContext } from "./platform-context";

type CreditPackageRow = typeof schema.creditPackages.$inferSelect;
type CreditLedgerRow = typeof schema.creditLedger.$inferSelect;
type CheckoutSessionRow = typeof schema.paymentCheckoutSessions.$inferSelect;
type PaymentInvoiceRow = typeof schema.paymentInvoices.$inferSelect;

export class PaymentRequiredError extends Error {
  status = 402;
}

export type CreditPackageView = {
  id: string;
  slug: string;
  name: string;
  credits: number;
  priceCents: number;
  currency: string;
  active: boolean;
};

export type CreditLedgerView = {
  id: string;
  sourceType: CreditLedgerRow["sourceType"];
  creditsDelta: number;
  balanceAfter: number;
  referenceKey: string | null;
  metadata: unknown;
  createdAt: string;
};

export type CheckoutSessionView = {
  id: string;
  provider: CheckoutSessionRow["provider"];
  status: CheckoutSessionRow["status"];
  credits: number;
  amountCents: number;
  currency: string;
  checkoutUrl: string | null;
  createdAt: string;
  completedAt: string | null;
};

export type PaymentInvoiceView = {
  id: string;
  provider: PaymentInvoiceRow["provider"];
  status: PaymentInvoiceRow["status"];
  credits: number;
  amountCents: number;
  currency: string;
  hostedInvoiceUrl: string | null;
  paidAt: string | null;
  createdAt: string;
};

export type CreditOverview = {
  balance: number;
  packages: CreditPackageView[];
  recentLedger: CreditLedgerView[];
  recentCheckoutSessions: CheckoutSessionView[];
  recentInvoices: PaymentInvoiceView[];
};

const defaultCreditPackages = [
  {
    slug: "credits_100",
    name: "100 credits",
    credits: 100,
    priceCents: 1900,
    currency: "USD",
    sortOrder: 10,
  },
  {
    slug: "credits_500",
    name: "500 credits",
    credits: 500,
    priceCents: 7900,
    currency: "USD",
    sortOrder: 20,
  },
  {
    slug: "credits_2000",
    name: "2000 credits",
    credits: 2000,
    priceCents: 24900,
    currency: "USD",
    sortOrder: 30,
  },
] as const;

function parseMetadata(value: string | null): unknown {
  if (!value) return null;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

function dateToIso(value: Date | null): string | null {
  return value ? value.toISOString() : null;
}

function packageToView(row: CreditPackageRow): CreditPackageView {
  return {
    id: row.id,
    slug: row.slug,
    name: row.name,
    credits: row.credits,
    priceCents: row.priceCents,
    currency: row.currency,
    active: row.active,
  };
}

function ledgerToView(row: CreditLedgerRow): CreditLedgerView {
  return {
    id: row.id,
    sourceType: row.sourceType,
    creditsDelta: row.creditsDelta,
    balanceAfter: row.balanceAfter,
    referenceKey: row.referenceKey,
    metadata: parseMetadata(row.metadataJson),
    createdAt: row.createdAt.toISOString(),
  };
}

function checkoutToView(row: CheckoutSessionRow): CheckoutSessionView {
  return {
    id: row.id,
    provider: row.provider,
    status: row.status,
    credits: row.credits,
    amountCents: row.amountCents,
    currency: row.currency,
    checkoutUrl: row.checkoutUrl,
    createdAt: row.createdAt.toISOString(),
    completedAt: dateToIso(row.completedAt),
  };
}

function invoiceToView(row: PaymentInvoiceRow): PaymentInvoiceView {
  return {
    id: row.id,
    provider: row.provider,
    status: row.status,
    credits: row.credits,
    amountCents: row.amountCents,
    currency: row.currency,
    hostedInvoiceUrl: row.hostedInvoiceUrl,
    paidAt: dateToIso(row.paidAt),
    createdAt: row.createdAt.toISOString(),
  };
}

function isProductionLikeDeployment(): boolean {
  return (
    process.env.NODE_ENV === "production" ||
    process.env.NOVEL_DRAMA_ONLINE_MODE === "1" ||
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET === "production"
  );
}

function allowUnsignedMockWebhook(provider: CheckoutSessionRow["provider"]): boolean {
  return (
    provider === "mock" &&
    process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS === "1" &&
    !isProductionLikeDeployment()
  );
}

async function ensureDefaultCreditPackages(): Promise<CreditPackageRow[]> {
  const rows: CreditPackageRow[] = [];
  for (const pack of defaultCreditPackages) {
    const existing = await db.query.creditPackages.findFirst({
      where: eq(schema.creditPackages.slug, pack.slug),
    });
    const now = new Date();
    const values = {
      name: pack.name,
      credits: pack.credits,
      priceCents: pack.priceCents,
      currency: pack.currency,
      active: true,
      sortOrder: pack.sortOrder,
      updatedAt: now,
    };
    if (existing) {
      await db
        .update(schema.creditPackages)
        .set(values)
        .where(eq(schema.creditPackages.id, existing.id));
      rows.push({ ...existing, ...values });
      continue;
    }
    const id = uuid();
    await db.insert(schema.creditPackages).values({
      id,
      slug: pack.slug,
      ...values,
      createdAt: now,
    });
    const created = await db.query.creditPackages.findFirst({
      where: eq(schema.creditPackages.id, id),
    });
    if (!created) throw new Error("credit package insert failed");
    rows.push(created);
  }
  return rows.sort((a, b) => a.sortOrder - b.sortOrder);
}

export async function getCreditBalance(tenantId: string): Promise<number> {
  const rows = await db.query.creditLedger.findMany({
    where: eq(schema.creditLedger.tenantId, tenantId),
  });
  return rows.reduce((sum, row) => sum + row.creditsDelta, 0);
}

async function writeLedgerEntry({
  tenantId,
  userId,
  sourceType,
  creditsDelta,
  usageEventId,
  checkoutSessionId,
  invoiceId,
  referenceKey,
  metadata,
}: {
  tenantId: string;
  userId?: string | null;
  sourceType: CreditLedgerRow["sourceType"];
  creditsDelta: number;
  usageEventId?: string | null;
  checkoutSessionId?: string | null;
  invoiceId?: string | null;
  referenceKey?: string | null;
  metadata?: unknown;
}): Promise<CreditLedgerRow> {
  const balance = await getCreditBalance(tenantId);
  const row = {
    id: uuid(),
    tenantId,
    userId: userId ?? null,
    sourceType,
    creditsDelta,
    balanceAfter: balance + creditsDelta,
    usageEventId,
    checkoutSessionId,
    invoiceId,
    referenceKey,
    metadataJson: metadata == null ? null : JSON.stringify(metadata, null, 2),
    createdAt: new Date(),
  };
  await db.insert(schema.creditLedger).values(row);
  const created = await db.query.creditLedger.findFirst({
    where: eq(schema.creditLedger.id, row.id),
  });
  if (!created) throw new Error("credit ledger insert failed");
  return created;
}

export async function ensureMonthlyCreditGrant({
  context,
  subscriptionId,
  periodStart,
  credits,
}: {
  context: PlatformContext;
  subscriptionId: string;
  periodStart: string;
  credits: number;
}): Promise<void> {
  if (credits <= 0) return;
  const referencePrefix = `monthly_grant:${periodStart}:`;
  const grantEntries = await db.query.creditLedger.findMany({
    where: eq(schema.creditLedger.tenantId, context.tenant.id),
  });
  const grantedThisPeriod = grantEntries
    .filter(
      (entry) =>
        entry.sourceType === "monthly_grant" &&
        entry.referenceKey?.startsWith(referencePrefix)
    )
    .reduce((sum, entry) => sum + Math.max(0, entry.creditsDelta), 0);
  if (grantedThisPeriod >= credits) return;
  const creditsDelta = credits - grantedThisPeriod;
  await writeLedgerEntry({
    tenantId: context.tenant.id,
    userId: context.user.id,
    sourceType: "monthly_grant",
    creditsDelta,
    referenceKey: `${referencePrefix}subscription:${subscriptionId}:total:${credits}`,
    metadata: { subscriptionId, periodStart, targetCredits: credits },
  });
}

export async function settleUsageCredits({
  context,
  usageEventId,
  billableUnits,
  metadata,
}: {
  context: PlatformContext;
  usageEventId: string;
  billableUnits: number;
  metadata?: unknown;
}): Promise<void> {
  if (billableUnits <= 0) return;
  const balance = await getCreditBalance(context.tenant.id);
  if (
    process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1" &&
    balance < billableUnits
  ) {
    throw new PaymentRequiredError("insufficient credits");
  }
  await writeLedgerEntry({
    tenantId: context.tenant.id,
    userId: context.user.id,
    sourceType: "usage_debit",
    creditsDelta: -billableUnits,
    usageEventId,
    referenceKey: `usage:${usageEventId}`,
    metadata,
  });
}

async function ensurePaymentCustomer(
  context: PlatformContext,
  provider: CheckoutSessionRow["provider"]
): Promise<void> {
  const existing = await db.query.paymentCustomers.findFirst({
    where: and(
      eq(schema.paymentCustomers.tenantId, context.tenant.id),
      eq(schema.paymentCustomers.provider, provider)
    ),
  });
  if (existing) return;
  const now = new Date();
  await db.insert(schema.paymentCustomers).values({
    id: uuid(),
    tenantId: context.tenant.id,
    provider,
    billingEmail: context.user.email,
    metadataJson: JSON.stringify({ source: "platform_template" }, null, 2),
    createdAt: now,
    updatedAt: now,
  });
}

export async function createCreditCheckoutSession(
  context: PlatformContext,
  packageSlug: string,
  provider: CheckoutSessionRow["provider"] = "mock"
): Promise<CheckoutSessionView> {
  const packages = await ensureDefaultCreditPackages();
  const pack = packages.find((item) => item.slug === packageSlug && item.active);
  if (!pack) throw new Error("credit package not found");
  await ensurePaymentCustomer(context, provider);
  const now = new Date();
  const id = uuid();
  const checkoutUrl =
    provider === "mock" ? `/api/platform/checkout/${id}/complete` : null;
  await db.insert(schema.paymentCheckoutSessions).values({
    id,
    tenantId: context.tenant.id,
    packageId: pack.id,
    provider,
    status: "open",
    credits: pack.credits,
    amountCents: pack.priceCents,
    currency: pack.currency,
    checkoutUrl,
    metadataJson: JSON.stringify({ packageSlug }, null, 2),
    expiresAt: new Date(now.getTime() + 30 * 60 * 1000),
    createdAt: now,
    updatedAt: now,
  });
  const created = await db.query.paymentCheckoutSessions.findFirst({
    where: eq(schema.paymentCheckoutSessions.id, id),
  });
  if (!created) throw new Error("checkout session insert failed");
  return checkoutToView(created);
}

async function completeCheckoutSessionInternal(
  session: CheckoutSessionRow,
  userId?: string | null
): Promise<PaymentInvoiceRow> {
  if (session.status === "paid") {
    const existing = await db.query.paymentInvoices.findFirst({
      where: eq(schema.paymentInvoices.checkoutSessionId, session.id),
    });
    if (existing) return existing;
  }
  if (session.status !== "open" && session.status !== "paid") {
    throw new Error(`checkout session is ${session.status}`);
  }
  const now = new Date();
  await db
    .update(schema.paymentCheckoutSessions)
    .set({ status: "paid", completedAt: now, updatedAt: now })
    .where(eq(schema.paymentCheckoutSessions.id, session.id));

  const invoiceId = uuid();
  await db.insert(schema.paymentInvoices).values({
    id: invoiceId,
    tenantId: session.tenantId,
    checkoutSessionId: session.id,
    provider: session.provider,
    status: "paid",
    credits: session.credits,
    amountCents: session.amountCents,
    currency: session.currency,
    hostedInvoiceUrl: `/api/platform/invoices/${invoiceId}`,
    metadataJson: session.metadataJson,
    paidAt: now,
    createdAt: now,
    updatedAt: now,
  });
  const invoice = await db.query.paymentInvoices.findFirst({
    where: eq(schema.paymentInvoices.id, invoiceId),
  });
  if (!invoice) throw new Error("payment invoice insert failed");
  await writeLedgerEntry({
    tenantId: session.tenantId,
    userId,
    sourceType: "top_up",
    creditsDelta: session.credits,
    checkoutSessionId: session.id,
    invoiceId: invoice.id,
    referenceKey: `checkout:${session.id}:paid`,
    metadata: {
      provider: session.provider,
      amountCents: session.amountCents,
      currency: session.currency,
    },
  });
  return invoice;
}

export async function completeCreditCheckoutSession(
  context: PlatformContext,
  sessionId: string
): Promise<CreditOverview> {
  const session = await db.query.paymentCheckoutSessions.findFirst({
    where: and(
      eq(schema.paymentCheckoutSessions.id, sessionId),
      eq(schema.paymentCheckoutSessions.tenantId, context.tenant.id)
    ),
  });
  if (!session) throw new Error("checkout session not found");
  await completeCheckoutSessionInternal(session, context.user.id);
  return getCreditOverview(context);
}

export async function processPaymentWebhook(payload: {
  provider?: CheckoutSessionRow["provider"];
  eventType?: string;
  checkoutSessionId?: string;
  externalEventId?: string;
  signatureVerified?: boolean;
  raw?: unknown;
}): Promise<{ ok: boolean; webhookEventId: string }> {
  const eventId = uuid();
  let tenantId: string | null = null;
  let session: CheckoutSessionRow | undefined;
  if (payload.checkoutSessionId) {
    session = await db.query.paymentCheckoutSessions.findFirst({
      where: eq(schema.paymentCheckoutSessions.id, payload.checkoutSessionId),
    });
    tenantId = session?.tenantId ?? null;
  }
  const provider = payload.provider ?? session?.provider ?? "mock";
  if (payload.signatureVerified !== true && !allowUnsignedMockWebhook(provider)) {
    throw new Error("payment webhook signature is required before processing");
  }
  if (payload.externalEventId) {
    const existing = await db.query.paymentWebhookEvents.findFirst({
      where: and(
        eq(schema.paymentWebhookEvents.provider, provider),
        eq(schema.paymentWebhookEvents.externalEventId, payload.externalEventId)
      ),
    });
    if (existing?.status === "processed" || existing?.status === "received") {
      return { ok: true, webhookEventId: existing.id };
    }
  }
  const now = new Date();
  await db.insert(schema.paymentWebhookEvents).values({
    id: eventId,
    tenantId,
    checkoutSessionId: session?.id ?? null,
    provider,
    eventType: payload.eventType ?? "unknown",
    status: "received",
    externalEventId: payload.externalEventId,
    payloadJson: JSON.stringify(payload.raw ?? payload, null, 2),
    createdAt: now,
  });
  try {
    if (payload.eventType === "checkout.paid" && session) {
      await completeCheckoutSessionInternal(session);
    }
    await db
      .update(schema.paymentWebhookEvents)
      .set({ status: "processed", processedAt: new Date() })
      .where(eq(schema.paymentWebhookEvents.id, eventId));
    return { ok: true, webhookEventId: eventId };
  } catch (error) {
    await db
      .update(schema.paymentWebhookEvents)
      .set({
        status: "failed",
        errorText: error instanceof Error ? error.message : String(error),
        processedAt: new Date(),
      })
      .where(eq(schema.paymentWebhookEvents.id, eventId));
    throw error;
  }
}

export async function getCreditOverview(
  context: PlatformContext
): Promise<CreditOverview> {
  const packages = await ensureDefaultCreditPackages();
  const [balance, ledger, sessions, invoices] = await Promise.all([
    getCreditBalance(context.tenant.id),
    db.query.creditLedger.findMany({
      where: eq(schema.creditLedger.tenantId, context.tenant.id),
      orderBy: [desc(schema.creditLedger.createdAt)],
      limit: 30,
    }),
    db.query.paymentCheckoutSessions.findMany({
      where: eq(schema.paymentCheckoutSessions.tenantId, context.tenant.id),
      orderBy: [desc(schema.paymentCheckoutSessions.createdAt)],
      limit: 10,
    }),
    db.query.paymentInvoices.findMany({
      where: eq(schema.paymentInvoices.tenantId, context.tenant.id),
      orderBy: [desc(schema.paymentInvoices.createdAt)],
      limit: 10,
    }),
  ]);
  return {
    balance,
    packages: packages.map(packageToView),
    recentLedger: ledger.map(ledgerToView),
    recentCheckoutSessions: sessions.map(checkoutToView),
    recentInvoices: invoices.map(invoiceToView),
  };
}
```

## File: `src/app/api/platform/payments/webhook/route.ts`

```ts
import { NextRequest, NextResponse } from "next/server";
import { createHmac, timingSafeEqual } from "crypto";
import { processPaymentWebhook } from "@/lib/platform-credits";

export const runtime = "nodejs";

function webhookSecret(): string | null {
  const value =
    process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET ??
    process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET ??
    "";
  return value.trim() || null;
}

function signatureHeader(req: NextRequest): string | null {
  return (
    req.headers.get("x-novel-drama-signature") ??
    req.headers.get("x-webhook-signature") ??
    req.headers.get("x-signature") ??
    null
  );
}

function normalizeSignature(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  const normalized = trimmed.startsWith("sha256=")
    ? trimmed.slice("sha256=".length)
    : trimmed;
  return /^[a-f0-9]{64}$/i.test(normalized) ? normalized.toLowerCase() : null;
}

function verifyWebhookSignature(req: NextRequest, rawBody: string): boolean {
  const secret = webhookSecret();
  if (!secret) {
    throw new Error("payment webhook secret is not configured; unsigned webhooks are rejected");
  }
  const provided = normalizeSignature(signatureHeader(req));
  if (!provided) {
    throw new Error("missing or invalid payment webhook signature");
  }
  const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
  const providedBuffer = Buffer.from(provided, "hex");
  const expectedBuffer = Buffer.from(expected, "hex");
  if (
    providedBuffer.length !== expectedBuffer.length ||
    !timingSafeEqual(providedBuffer, expectedBuffer)
  ) {
    throw new Error("payment webhook signature mismatch");
  }
  return true;
}

export async function POST(req: NextRequest) {
  const rawBody = await req.text();
  try {
    const body = JSON.parse(rawBody || "{}") as {
      provider?: "mock" | "stripe" | "wechat_pay" | "alipay" | "manual";
      eventType?: string;
      checkoutSessionId?: string;
      externalEventId?: string;
    };
    const signatureVerified = verifyWebhookSignature(req, rawBody);
    return NextResponse.json(
      await processPaymentWebhook({
        ...body,
        signatureVerified,
        raw: {
          ...body,
          signatureVerified,
        },
      })
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 }
    );
  }
}
```

## File: `src/app/api/projects/[id]/control/route.ts`

```ts
import { NextRequest, NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import {
  scheduleNextRoundIfRunAll,
} from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { parseProjectMeta, updateProjectMeta } from "@/lib/project-controls";

type ProjectControlAction =
  | "pause"
  | "resume"
  | "run_all"
  | "stop_run_all"
  | "archive"
  | "restore"
  | "delete";

type ProjectControlBody = {
  action?: ProjectControlAction;
  generationVariant?: string | null;
  repairBudget?: string | null;
  episodesPerRound?: number | string | null;
};

async function readBody(req: NextRequest): Promise<ProjectControlBody> {
  try {
    return (await req.json()) as ProjectControlBody;
  } catch {
    return {};
  }
}

async function markQueuedJobsPaused(projectId: string): Promise<void> {
  await db
    .update(schema.jobs)
    .set({
      message: "项目已暂停，等待继续",
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(schema.jobs.projectId, projectId),
        eq(schema.jobs.kind, "round_generation"),
        eq(schema.jobs.status, "queued")
      )
    );
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const body = await readBody(req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });
    if (
      project.status === "done" &&
      (body.action === "pause" ||
        body.action === "resume" ||
        body.action === "run_all")
    ) {
      return NextResponse.json(
        { error: "项目已完成，不能继续调度" },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const now = new Date();
    if (body.action === "archive") {
      await updateProjectMeta(id, (meta) => ({
        ...meta,
        archivedAt: now.toISOString(),
        archivedReason: "operator_archive",
        control: {
          ...(meta.control ?? {}),
          runAll: {
            ...(meta.control?.runAll ?? {}),
            enabled: false,
          },
        },
      }));
      await db
        .update(schema.projects)
        .set({
          status:
            project.status === "running" || project.status === "draft"
              ? "paused"
              : project.status,
          updatedAt: now,
        })
        .where(eq(schema.projects.id, id));
      await markQueuedJobsPaused(id);
      return NextResponse.json(
        { status: "archived" },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "restore") {
      await updateProjectMeta(id, (meta) => {
        const { archivedAt, archivedReason, ...rest } = meta;
        void archivedAt;
        void archivedReason;
        return rest;
      });
      await db
        .update(schema.projects)
        .set({ updatedAt: now })
        .where(eq(schema.projects.id, id));
      return NextResponse.json(
        { status: project.status },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "delete") {
      const parsedMeta = parseProjectMeta(project.metaJson);
      if (!parsedMeta?.archivedAt) {
        return NextResponse.json(
          { error: "请先归档项目，再删除" },
          { status: 409, headers: platformHeaders(context) }
        );
      }
      await db.delete(schema.projects).where(eq(schema.projects.id, id));
      return NextResponse.json(
        { status: "deleted" },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "pause") {
      await db
        .update(schema.projects)
        .set({ status: "paused", updatedAt: now })
        .where(eq(schema.projects.id, id));
      await markQueuedJobsPaused(id);
      return NextResponse.json(
        { status: "paused" },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "resume") {
      await db
        .update(schema.projects)
        .set({ status: "running", updatedAt: now })
        .where(eq(schema.projects.id, id));
      const nextJob = await scheduleNextRoundIfRunAll(id);
      kickJobWorker();
      return NextResponse.json(
        { status: "running", nextJob },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "run_all") {
      await updateProjectMeta(id, (meta) => ({
        ...meta,
        control: {
          ...(meta.control ?? {}),
          runAll: {
            enabled: true,
            generationVariant: body.generationVariant ?? null,
            repairBudget: body.repairBudget ?? null,
            requestedAt: new Date().toISOString(),
          },
        },
      }));
      await db
        .update(schema.projects)
        .set({ status: "running", updatedAt: now })
        .where(eq(schema.projects.id, id));
      const nextJob = await scheduleNextRoundIfRunAll(id);
      kickJobWorker();
      const refreshed = await db.query.projects.findFirst({
        where: eq(schema.projects.id, id),
      });
      return NextResponse.json(
        {
          status: refreshed?.status ?? (nextJob ? "running" : "failed"),
          runAll: Boolean(nextJob),
          nextJob,
        },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "stop_run_all") {
      await updateProjectMeta(id, (meta) => ({
        ...meta,
        control: {
          ...(meta.control ?? {}),
          runAll: {
            ...(meta.control?.runAll ?? {}),
            enabled: false,
          },
        },
      }));
      return NextResponse.json(
        { runAll: false },
        { headers: platformHeaders(context) }
      );
    }

    return NextResponse.json({ error: "unknown action" }, { status: 400 });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
```

## File: `src/app/api/health/route.ts`

```ts
import {
  deploymentReadiness,
  resolveDatabasePath,
} from "@/lib/deployment-readiness";
import { resolveEngineMode } from "@/lib/engine-runner";

export async function GET() {
  const engineMode = resolveEngineMode();
  const mockMode = engineMode.mode === "mock";
  let baseUrlHost: string | null = null;
  if (process.env.OPENAI_BASE_URL) {
    try {
      baseUrlHost = new URL(process.env.OPENAI_BASE_URL).host;
    } catch {
      baseUrlHost = "invalid-url";
    }
  }
  return Response.json({
    ok: true,
    app: "novel-to-drama",
    mode: engineMode.mode,
    explicitMock: engineMode.explicitMock,
    autoWorker: process.env.NOVEL_DRAMA_AUTO_WORKER ?? "default",
    db: {
      path: resolveDatabasePath(),
      configured: Boolean(process.env.NOVEL_DRAMA_DB_PATH),
    },
    llm: {
      ready: mockMode || Boolean(process.env.OPENAI_API_KEY),
      provider: process.env.NOVEL_DRAMA_LLM_PROVIDER ?? null,
      model: process.env.OPENAI_MODEL ?? null,
      baseUrlHost,
      hasApiKey: Boolean(process.env.OPENAI_API_KEY),
    },
    readiness: deploymentReadiness(),
    timestamp: new Date().toISOString(),
  });
}
```

## File: `src/lib/deployment-readiness.ts`

```ts
import { accessSync, constants, mkdirSync } from "fs";
import { dirname, resolve } from "path";

export type DeploymentReadinessCheck = {
  key: string;
  status: "pass" | "warn" | "fail";
  message: string;
};

export type DeploymentReadiness = {
  mode: "local" | "online";
  status: "ready" | "warning" | "blocked";
  checks: DeploymentReadinessCheck[];
};

export function resolveDatabasePath(): string {
  return process.env.NOVEL_DRAMA_DB_PATH?.trim() || "db.sqlite";
}

export function ensureDatabaseDirectory(dbPath = resolveDatabasePath()): void {
  mkdirSync(dirname(resolve(dbPath)), { recursive: true });
}

function canWriteDatabaseDirectory(dbPath = resolveDatabasePath()): boolean {
  try {
    ensureDatabaseDirectory(dbPath);
    accessSync(dirname(resolve(dbPath)), constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

function check(
  key: string,
  status: DeploymentReadinessCheck["status"],
  message: string
): DeploymentReadinessCheck {
  return { key, status, message };
}

export function deploymentReadiness(): DeploymentReadiness {
  const onlineMode =
    process.env.NOVEL_DRAMA_ONLINE_MODE === "1" ||
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET === "production";
  const mockMode = process.env.NOVEL_DRAMA_WEB_MOCK === "1";
  const realModelReady = Boolean(process.env.OPENAI_API_KEY && process.env.OPENAI_MODEL);
  const browserAccessProtected = Boolean(process.env.NOVEL_DRAMA_ACCESS_TOKEN);
  const externalApiProtected = process.env.NOVEL_DRAMA_REQUIRE_API_KEY === "1";
  const dbPath = resolveDatabasePath();
  const checks: DeploymentReadinessCheck[] = [
    check(
      "llm",
      mockMode ? (onlineMode ? "fail" : "warn") : realModelReady ? "pass" : "fail",
      mockMode
        ? "当前是 mock 模式，只适合演示页面流程。"
        : realModelReady
          ? "真实模型 key 与模型名已配置。"
          : "真实模型需要 OPENAI_API_KEY 和 OPENAI_MODEL。"
    ),
    check(
      "database",
      canWriteDatabaseDirectory(dbPath)
        ? process.env.NOVEL_DRAMA_DB_PATH || !onlineMode
          ? "pass"
          : "warn"
        : "fail",
      process.env.NOVEL_DRAMA_DB_PATH
        ? `数据库路径已配置：${dbPath}`
        : onlineMode
          ? "线上模式建议显式配置 NOVEL_DRAMA_DB_PATH 到持久盘。"
          : "使用默认本地 db.sqlite。"
    ),
    check(
      "access_token",
      process.env.NOVEL_DRAMA_ACCESS_TOKEN
        ? "pass"
        : onlineMode
          ? "fail"
          : "warn",
      process.env.NOVEL_DRAMA_ACCESS_TOKEN
        ? "浏览器访问令牌已配置。"
        : "公网部署前需要 NOVEL_DRAMA_ACCESS_TOKEN，或确认部署在私有网络后。"
    ),
    check(
      "api_auth",
      browserAccessProtected || externalApiProtected
        ? "pass"
        : onlineMode
          ? "fail"
          : "warn",
      browserAccessProtected && externalApiProtected
        ? "浏览器访问令牌与 API Key 保护均已开启。"
        : browserAccessProtected
          ? "浏览器访问令牌已保护页面和 API；外部程序 API Key 可按需开启。"
          : externalApiProtected
            ? "API Key 保护已开启；浏览器入口建议另配 NOVEL_DRAMA_ACCESS_TOKEN。"
            : "公网部署前需要 NOVEL_DRAMA_ACCESS_TOKEN、API Key 保护，或确认部署在私有网络后。"
    ),
    check(
      "credits",
      process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1" ? "pass" : "warn",
      process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1"
        ? "点数扣费门禁已开启。"
        : "点数扣费门禁未开启，上线早期可内测，开放给外部用户前应开启。"
    ),
  ];
  const hasFailure = checks.some((item) => item.status === "fail");
  const hasWarning = checks.some((item) => item.status === "warn");
  return {
    mode: onlineMode ? "online" : "local",
    status: hasFailure ? "blocked" : hasWarning ? "warning" : "ready",
    checks,
  };
}
```

## File: `src/novel_drama_engine/pipeline.py`

```py
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
from novel_drama_engine.models import (
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
    QualityReport,
    QualityStatus,
    RoundResult,
    RuntimeReport,
    ScriptBatch,
    SeriesStructurePlan,
    SourceAnalysis,
    SourceStrengthProfile,
    StoryBible,
    ViralAssetReport,
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
    packet_for_episode,
)
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
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
    raw = os.environ.get("NOVEL_DRAMA_TRACE_PROMPTS", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
        and generation_variant == GenerationVariant.SOP_FULL_STACK
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
            return episode_repair_instruction(existing_episode, base_instruction)

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
        write_runtime_report()

        episode_source_packets = cached_stage(
            "episode_source_packets",
            "episode_source_packets",
            EpisodeSourcePackets,
            lambda: build_episode_source_packets(
                source_text=source_text,
                episode_context=episode_context,
                episode_plan=episode_plan,
                series_structure_plan=series_structure_plan,
                target_episode_count=target_episode_count,
            ),
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
                    methodology_context=methodology_context,
                    episode_source_packets=episode_source_packets,
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
                    methodology_context=methodology_context,
                    episode_source_packets=episode_source_packets,
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
                    source_strength_profile=source_strength_profile,
                    methodology_context=quality_methodology_context,
                    viral_asset_report=viral_asset_report,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_methodology_quality",
                local_methodology_quality,
            )
            local_novelty_report = run_stage(
                f"{artifact_prefix}_script_novelty",
                lambda: build_script_novelty_report(current_script_batch),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_script_novelty_report",
                local_novelty_report,
            )
            self.store.write_text_artifact(
                round_number,
                f"{artifact_prefix}_script_novelty_report.md",
                render_script_novelty_report(local_novelty_report),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_adaptation_quality",
                lambda: merge_adaptation_quality_into_report(
                    current_quality_report,
                    local_adaptation_quality,
                ),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_methodology_quality",
                lambda: merge_methodology_quality_into_report(
                    gated_report,
                    local_methodology_quality,
                ),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_script_novelty",
                lambda: merge_script_novelty_into_quality_report(
                    gated_report,
                    local_novelty_report,
                ),
            )
            return gated_report

        quality_report = apply_local_quality_gates(
            script_batch,
            quality_report,
            "pre_repair",
        )

        def run_episode_repair_cycle(
            current_script_batch: ScriptBatch,
            current_quality_report: QualityReport,
        ) -> tuple[ScriptBatch, QualityReport]:
            self.store.write_round_artifact(
                round_number,
                "quality_report_before_episode_repair",
                current_quality_report,
            )
            current_episodes = {
                episode.episode: episode for episode in current_script_batch.episodes
            }
            current_episode_repair_packet_records: list[dict[str, object]] = []

            def record_current_episode_repair_packet(packet) -> None:
                current_episode_repair_packet_records.append(
                    packet.model_dump(mode="json")
                )
                self.store.write_text_artifact(
                    round_number,
                    "current_episode_repair_packets.json",
                    json.dumps(
                        current_episode_repair_packet_records,
                        ensure_ascii=False,
                        indent=2,
                    ),
                )

            episode_numbers = expected_episode_numbers(
                round_number=round_number,
                previous_context=previous_context,
                target_episode_count=target_episode_count,
                episodes_per_round=resolved_episodes_per_round,
            )
            cached_repaired_batch = read_cached_artifact(
                "script_batch_episode_repair",
                ScriptBatch,
            )
            if cached_repaired_batch is not None:
                record_cached_stage("episode_repair")
                repaired_batch = cached_repaired_batch
            else:
                local_repair_targets = {
                    episode.episode
                    for episode in current_script_batch.episodes
                    if episode.episode in episode_numbers
                    and episode_quality_warnings(episode)
                }
                report_repair_targets = episode_numbers_mentioned_in_quality(
                    current_quality_report,
                    episode_numbers,
                )
                missing_episode_targets = {
                    episode_number
                    for episode_number in episode_numbers
                    if episode_number not in current_episodes
                }
                repair_targets = (
                    local_repair_targets
                    | report_repair_targets
                    | missing_episode_targets
                )
                if not repair_targets and not light_source_cost_control:
                    repair_targets = fallback_episode_repair_targets(episode_numbers)

                self.store.write_text_artifact(
                    round_number,
                    "episode_repair_targets.md",
                    "\n".join(
                        [
                            f"EP{episode_number:02d}"
                            for episode_number in sorted(repair_targets)
                        ]
                        or [
                            "none",
                            "全局质检未点名具体集数，本轮未触发逐集重写。",
                        ]
                    ),
                )
                if repair_targets:
                    def handoff_changed(
                        before: EpisodeScript | None,
                        after: EpisodeScript,
                    ) -> bool:
                        before_handoff = handoff_from_episode(before)
                        after_handoff = handoff_from_episode(after)
                        if before_handoff is None or after_handoff is None:
                            return before_handoff != after_handoff
                        return (
                            before_handoff.previous_cliffhanger
                            != after_handoff.previous_cliffhanger
                            or before_handoff.previous_final_lines
                            != after_handoff.previous_final_lines
                            or before_handoff.previous_state_update
                            != after_handoff.previous_state_update
                        )

                    def repair_episode_sequence() -> list[EpisodeScript]:
                        dynamic_repair_targets = set(repair_targets)
                        repaired: list[EpisodeScript] = []
                        for episode_number in episode_numbers:
                            previous_episode = repaired[-1] if repaired else None
                            if episode_number in dynamic_repair_targets:
                                existing_episode = current_episodes.get(episode_number)
                                current_repair_packet = (
                                    build_current_episode_repair_packet(
                                        existing_episode,
                                        current_quality_report.rewrite_instruction,
                                    )
                                    if existing_episode is not None
                                    else None
                                )
                                if current_repair_packet is not None:
                                    record_current_episode_repair_packet(
                                        current_repair_packet,
                                    )
                                episode = script_generator.run_episode(
                                    source_text,
                                    source_analysis,
                                    episode_context,
                                    story_bible,
                                    previous_context,
                                    existing_episode,
                                    episode_number,
                                    repair_instruction_for_episode(
                                        episode_number,
                                        existing_episode,
                                        current_quality_report.rewrite_instruction,
                                    ),
                                    episode_plan=episode_plan,
                                    viral_asset_report=viral_asset_report,
                                    series_structure_plan=series_structure_plan,
                                    methodology_context=methodology_context,
                                    episode_source_packet=packet_for_episode(
                                        episode_source_packets,
                                        episode_number,
                                    ),
                                    previous_episode_handoff=handoff_from_episode(
                                        previous_episode,
                                    ),
                                    current_episode_repair_packet=current_repair_packet,
                                )
                                if (
                                    not episode_quality_warnings(episode)
                                    and handoff_changed(
                                        current_episodes.get(episode_number),
                                        episode,
                                    )
                                    and episode_number + 1 in episode_numbers
                                ):
                                    dynamic_repair_targets.add(episode_number + 1)
                            else:
                                episode = current_episodes[episode_number]
                            repaired.append(episode)
                        return repaired

                    repaired_episodes = run_stage(
                        "episode_repair",
                        repair_episode_sequence,
                    )
                    repaired_batch = run_stage(
                        "apply_episode_repair",
                        lambda: current_script_batch.model_copy(
                            update={"episodes": repaired_episodes},
                        ),
                    )
                else:
                    record_skipped_stage(
                        "episode_repair",
                        "Strong-source cost control blocked fallback repair."
                        if light_source_cost_control
                        else "No local, reported, missing, or fallback episode targets.",
                    )
                    repaired_batch = current_script_batch
                    return repaired_batch, current_quality_report
                self.store.write_round_artifact(
                    round_number,
                    "script_batch_episode_repair",
                    repaired_batch,
                )

            episodes_after_repair = {
                episode.episode: episode for episode in repaired_batch.episodes
            }
            episodes_needing_polish = {
                episode_number
                for episode_number, episode in episodes_after_repair.items()
                if episode_quality_warnings(episode)
            }
            if episodes_needing_polish:
                cached_polished_batch = read_cached_artifact(
                    "script_batch_episode_polish",
                    ScriptBatch,
                )
                if cached_polished_batch is not None:
                    record_cached_stage("episode_quality_polish")
                    repaired_batch = cached_polished_batch
                else:
                    polish_instructions = [
                        f"EP{episode_number:02d}: "
                        + repair_instruction_for_episode(
                            episode_number,
                            episodes_after_repair[episode_number],
                            current_quality_report.rewrite_instruction,
                        )
                        for episode_number in sorted(episodes_needing_polish)
                    ]
                    self.store.write_text_artifact(
                        round_number,
                        "episode_polish_instructions.md",
                        "\n\n---\n\n".join(polish_instructions),
                    )
                    if (
                        not blocking_optional_polish_enabled()
                        or light_source_cost_control
                    ):
                        record_skipped_stage(
                            "episode_quality_polish",
                            "Strong-source cost control keeps local polish as "
                            "review-only."
                            if light_source_cost_control
                            else "Set NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH=1 "
                            "to run this pass inline.",
                        )
                    else:
                        episode_polish_failures: list[str] = []

                        def polish_episode_or_keep(
                            episode_number: int,
                        ) -> EpisodeScript:
                            if episode_number not in episodes_needing_polish:
                                return episodes_after_repair[episode_number]
                            existing_episode = episodes_after_repair.get(episode_number)
                            current_repair_packet = (
                                build_current_episode_repair_packet(
                                    existing_episode,
                                    current_quality_report.rewrite_instruction,
                                )
                                if existing_episode is not None
                                else None
                            )
                            if current_repair_packet is not None:
                                record_current_episode_repair_packet(current_repair_packet)
                            try:
                                return script_generator.run_episode(
                                    source_text,
                                    source_analysis,
                                    episode_context,
                                    story_bible,
                                    previous_context,
                                    existing_episode,
                                    episode_number,
                                    repair_instruction_for_episode(
                                        episode_number,
                                        existing_episode,
                                        current_quality_report.rewrite_instruction,
                                    ),
                                    episode_plan=episode_plan,
                                    viral_asset_report=viral_asset_report,
                                    series_structure_plan=series_structure_plan,
                                    methodology_context=methodology_context,
                                    episode_source_packet=packet_for_episode(
                                        episode_source_packets,
                                        episode_number,
                                    ),
                                    previous_episode_handoff=handoff_from_episode(
                                        episodes_after_repair.get(episode_number - 1),
                                    ),
                                    current_episode_repair_packet=current_repair_packet,
                                )
                            except Exception as exc:
                                episode_polish_failures.append(
                                    f"EP{episode_number:02d}: {exc}"
                                )
                                return episodes_after_repair[episode_number]

                        polished_episodes = run_stage(
                            "episode_quality_polish",
                            lambda: [
                                polish_episode_or_keep(episode_number)
                                for episode_number in episode_numbers
                            ],
                        )
                        if episode_polish_failures:
                            self.store.write_text_artifact(
                                round_number,
                                "episode_quality_polish_failures.md",
                                "\n".join(episode_polish_failures),
                            )
                        repaired_batch = run_stage(
                            "apply_episode_quality_polish",
                            lambda: repaired_batch.model_copy(
                                update={"episodes": polished_episodes},
                            ),
                        )
                        self.store.write_round_artifact(
                            round_number,
                            "script_batch_episode_polish",
                            repaired_batch,
                        )

            episodes_after_quality_polish = {
                episode.episode: episode for episode in repaired_batch.episodes
            }
            episodes_needing_hook_dialogue = {
                episode_number
                for episode_number, episode in episodes_after_quality_polish.items()
                if episode_needs_hook_dialogue_polish(episode)
            }
            if episodes_needing_hook_dialogue:
                cached_hook_dialogue_batch = read_cached_artifact(
                    "script_batch_hook_dialogue_polish",
                    ScriptBatch,
                )
                if cached_hook_dialogue_batch is not None:
                    record_cached_stage("hook_dialogue_polish")
                    repaired_batch = cached_hook_dialogue_batch
                else:
                    hook_dialogue_instructions = [
                        f"EP{episode_number:02d}: "
                        + hook_dialogue_polish_instruction(
                            episodes_after_quality_polish[episode_number],
                            current_quality_report.rewrite_instruction,
                        )
                        for episode_number in sorted(episodes_needing_hook_dialogue)
                    ]
                    self.store.write_text_artifact(
                        round_number,
                        "hook_dialogue_polish_instructions.md",
                        "\n\n---\n\n".join(hook_dialogue_instructions),
                    )
                    if (
                        not blocking_optional_polish_enabled()
                        or light_source_cost_control
                    ):
                        record_skipped_stage(
                            "hook_dialogue_polish",
                            "Strong-source cost control keeps hook/dialogue polish "
                            "as review-only."
                            if light_source_cost_control
                            else "Set NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH=1 "
                            "to run this pass inline.",
                        )
                    else:
                        hook_dialogue_failures: list[str] = []

                        def hook_dialogue_episode_or_keep(
                            episode_number: int,
                        ) -> EpisodeScript:
                            if episode_number not in episodes_needing_hook_dialogue:
                                return episodes_after_quality_polish[

<!-- truncated 15175 chars -->
```

## File: `src/novel_drama_engine/rounds.py`

```py
from __future__ import annotations

import re
from collections.abc import Callable

from novel_drama_engine import prompts
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeSourcePackets,
    EpisodeContext,
    EpisodePlan,
    MethodologyContext,
    NextRoundContext,
    QualityReport,
    QualityStatus,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
    SeriesStructurePlan,
    ViralAssetReport,
)
from novel_drama_engine.source_packets import handoff_from_episode, packet_for_episode
from novel_drama_engine.script_quality import (
    episode_quality_warnings,
    script_batch_quality_warnings,
)


def expected_episode_numbers_from_context(
    episode_context: EpisodeContext,
) -> list[int]:
    match = re.fullmatch(
        r"EP(\d+)(?:-EP(\d+))?",
        episode_context.target_episode_range.strip(),
    )
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    if end < start:
        return []
    return list(range(start, end + 1))


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
        return self.llm.complete(
            system=prompts.EPISODE_CONTEXT_SYSTEM,
            user=prompts.episode_context_user(
                source_text,
                previous_context,
                source_analysis,
                round_number,
                target_episode_count,
                episodes_per_round,
                viral_asset_report=viral_asset_report,
                methodology_context=methodology_context,
            ),
            response_model=EpisodeContext,
        )


class ViralAssetExtractor:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        target_episode_count: int | None = None,
    ) -> ViralAssetReport:
        return self.llm.complete(
            system=prompts.VIRAL_ASSET_SYSTEM,
            user=prompts.viral_asset_user(
                source_text,
                source_analysis,
                target_episode_count,
            ),
            response_model=ViralAssetReport,
        )


class InternalBibleBuilder:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        viral_asset_report: ViralAssetReport | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> StoryBible:
        return self.llm.complete(
            system=prompts.BIBLE_SYSTEM,
            user=prompts.bible_user(
                source_text,
                source_analysis,
                episode_context,
                viral_asset_report=viral_asset_report,
                methodology_context=methodology_context,
            ),
            response_model=StoryBible,
        )


class SeriesStructurePlanner:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        viral_asset_report: ViralAssetReport,
        previous_context: NextRoundContext | None,
        target_episode_count: int | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> SeriesStructurePlan:
        return self.llm.complete(
            system=prompts.SERIES_STRUCTURE_SYSTEM,
            user=prompts.series_structure_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                viral_asset_report,
                previous_context,
                target_episode_count,
                methodology_context=methodology_context,
            ),
            response_model=SeriesStructurePlan,
        )


class EpisodeBeatPlanner:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> EpisodePlan:
        return self.llm.complete(
            system=prompts.EPISODE_PLAN_SYSTEM,
            user=prompts.episode_plan_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
            ),
            response_model=EpisodePlan,
        )


class ScriptBatchGenerator:
    def __init__(
        self,
        llm: JsonLLM,
        episode_writer: Callable[[EpisodeScript], None] | None = None,
    ) -> None:
        self.llm = llm
        self.episode_writer = episode_writer

    def _emit_episode(self, episode: EpisodeScript) -> EpisodeScript:
        if self.episode_writer is not None:
            self.episode_writer(episode)
        return episode

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
        round_number: int = 1,
        target_episode_count: int | None = None,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packets: EpisodeSourcePackets | None = None,
    ) -> ScriptBatch:
        batch = self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.script_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                rewrite_instruction,
                round_number,
                target_episode_count,
                episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packets=episode_source_packets,
            ),
            response_model=ScriptBatch,
        )
        filled_batch = self._fill_missing_episodes(
            batch,
            source_text,
            source_analysis,
            episode_context,
            story_bible,
            previous_context,
            rewrite_instruction,
            episode_plan,
            viral_asset_report,
            series_structure_plan,
            methodology_context,
            episode_source_packets,
        )
        for episode in filled_batch.episodes:
            self._emit_episode(episode)
        return filled_batch

    def run_episode_batch(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packets: EpisodeSourcePackets | None = None,
    ) -> ScriptBatch:
        expected_numbers = expected_episode_numbers_from_context(episode_context)
        if not expected_numbers:
            return self.run(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                rewrite_instruction,
                episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packets=episode_source_packets,
            )

        episode_first_instruction = "；".join(
            part
            for part in [
                rewrite_instruction,
                (
                    "逐集优先生成模式：本次只生成当前 episode 的完整可拍摄正片，"
                    "不要压缩成提纲，不要引用其他集正文，不要等待整批汇总。"
                ),
            ]
            if part
        )
        episodes: list[EpisodeScript] = []
        previous_episode: EpisodeScript | None = None
        for episode_number in expected_numbers:
            episode = self.run_episode(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                None,
                episode_number,
                episode_first_instruction,
                episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=packet_for_episode(
                    episode_source_packets,
                    episode_number,
                ),
                previous_episode_handoff=handoff_from_episode(previous_episode),
            )
            episodes.append(episode)
            previous_episode = episode
        return ScriptBatch(episodes=episodes)

    def _fill_missing_episodes(
        self,
        batch: ScriptBatch,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packets: EpisodeSourcePackets | None = None,
    ) -> ScriptBatch:
        expected_numbers = expected_episode_numbers_from_context(episode_context)
        if not expected_numbers:
            return batch

        episodes_by_number = {
            episode.episode: episode
            for episode in batch.episodes
            if episode.episode in expected_numbers
        }
        missing_numbers = [
            episode_number
            for episode_number in expected_numbers
            if episode_number not in episodes_by_number
        ]
        if not missing_numbers and len(episodes_by_number) == len(batch.episodes):
            return batch

        fill_instruction = "；".join(
            part
            for part in [
                rewrite_instruction,
                (
                    "整批输出缺集，系统正在逐集补齐。必须完整生成本集正片，"
                    "不能摘要、不能复述其他集、不能把多个 EP 合并。"
                ),
            ]
            if part
        )
        for episode_number in missing_numbers:
            episodes_by_number[episode_number] = self.run_episode(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                None,
                episode_number,
                fill_instruction,
                episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=packet_for_episode(
                    episode_source_packets,
                    episode_number,
                ),
                previous_episode_handoff=handoff_from_episode(
                    episodes_by_number.get(episode_number - 1),
                ),
            )

        return ScriptBatch(
            episodes=[
                episodes_by_number[episode_number]
                for episode_number in expected_numbers
                if episode_number in episodes_by_number
            ]
        )

    def run_episode(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        existing_episode: EpisodeScript | None,
        episode_number: int,
        rewrite_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packet: object | None = None,
        previous_episode_handoff: object | None = None,
        current_episode_repair_packet: object | None = None,
    ) -> EpisodeScript:
        episode = self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.script_episode_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                existing_episode,
                episode_number,
                rewrite_instruction,
                episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=episode_source_packet,
                previous_episode_handoff=previous_episode_handoff,
                current_episode_repair_packet=current_episode_repair_packet,
            ),
            response_model=EpisodeScript,
        )
        if episode.episode != episode_number:
            episode = episode.model_copy(update={"episode": episode_number})
        return self._emit_episode(episode)

    def run_episode_hook_dialogue_polish(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        existing_episode: EpisodeScript,
        episode_number: int,
        polish_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packet: object | None = None,
        previous_episode_handoff: object | None = None,
        current_episode_repair_packet: object | None = None,
    ) -> EpisodeScript:
        episode = self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.hook_dialogue_polish_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                existing_episode,
                episode_number,
                polish_instruction,
                episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=episode_source_packet,
                previous_episode_handoff=previous_episode_handoff,
                current_episode_repair_packet=current_episode_repair_packet,
            ),
            response_model=EpisodeScript,
        )
        if episode.episode != episode_number:
            episode = episode.model_copy(update={"episode": episode_number})
        return self._emit_episode(episode)


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
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        episode_plan: EpisodePlan | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> QualityReport:
        report = self.llm.complete(
            system=prompts.QUALITY_SYSTEM,
            user=prompts.quality_user(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                episode_plan=episode_plan,
                methodology_context=methodology_context,
            ),
            response_model=QualityReport,
        )
        warnings = script_batch_quality_warnings(
            script_batch,
            episode_context.target_episode_range,
        ) + [
            warning
            for episode in script_batch.episodes
            for warning in episode_quality_warnings(episode)
        ]
        if not warnings:
            return report

        blocking_issues = [*report.blocking_issues, *warnings]
        rewrite_instruction = "；".join(
            [
                "按双层质检修复：先保证创作稿成立（人物动机不偏、冲突自然、情绪递进、对白像人话、原文 C0/C1 不丢、结尾钩子已被演出来），再补执行稿需要的动作、道具、声音和镜头衔接；scene.heading 必须是“集数-场次 日/夜-内/外-具体地点”，例如 1-1 夜-内-武家卧室；不要把 hook/主情绪/watch_reason/消费理由/观众要看 当成用户可见说明；禁止“众人震惊、气氛凝固、他很害怕”这类抽象动作；台词/OS 单句尽量短，超长必须拆行",
                *warnings[:6],
                report.rewrite_instruction,
            ]
        ).strip("；")
        status = (
            QualityStatus.NEEDS_REWRITE
            if report.status == QualityStatus.USABLE
            else report.status
        )
        return report.model_copy(
            update={
                "status": status,
                "blocking_issues": blocking_issues,
                "rewrite_instruction": rewrite_instruction,
            },
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
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
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
                episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
            ),
            response_model=NextRoundContext,
        )
```

## File: `src/novel_drama_engine/prompts.py`

```py
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
            dump_model("source_analysis", source_analysis),
            dump_model("viral_asset_report", viral_asset_report),
            dump_model("episode_context", episode_context),
            dump_model("story_bible", story_bible),
            dump_model("series_structure_plan", series_structure_plan),
            dump_model("episode_plan", episode_plan),
            dump_model("previous_context", previous_context),
            f"rewrite_instruction: {rewrite_instruction}",
            section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
            section("内部方法论", render_methodology_context(methodology_context)),
            stage_instruction(
                "输出 episode_context.target_episode_range 覆盖的全部 EpisodeScript。先写创作稿质量：一场戏要成立，再考虑后续执行稿补镜头。",
                (
                    "逐集先确认原文片段、C0 不可改事实、C1 必保名场面、Story Bible 人物动机和 episode_plan 的本集目标；"
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
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("episode_plan", episode_plan),
        dump_model("previous_context", previous_context),
        f"rewrite_instruction: {rewrite_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "必须输出 episode_context.target_episode_range 覆盖的全部集数，最多 5 集。",
            (
                "逐集先读 EpisodeDramaPlan 和 SeriesEpisodeOutline，确认本集核心事件、信息增量、断点类型和原文锚点；"
                "再按原文资产分级决定“保护 C0/C1、视听化 C2、压缩 C3、删除 C4”，"
                "最后写前三秒可见冲突、三波拉扯、假打脸/钥匙兑现、反派最后一装和结尾截断。"
            ),
            (
                "如果 episode_plan 不为空，必须逐集执行对应 EpisodeDramaPlan：drama_engine 决定本集动作逻辑，"
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
) -> str:
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packet=episode_source_packet,
        ),
        f"只生成第 {episode_number} 集。不要输出其他集数。",
        dump_model("previous_episode_handoff", previous_episode_handoff),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("previous_context", previous_context),
        dump_model("existing_episode_to_rewrite", existing_episode),
        dump_model("current_episode_repair_packet", current_episode_repair_packet),
        dump_model("episode_plan", episode_plan),
        f"rewrite_instruction: {rewrite_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
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
                "如果 series_structure_plan 不为空，必须对齐本集 SeriesEpisodeOutline 的 "
                "core_event、information_increment、ending_hook_type 和 source_anchor。"
                "如果 episode_source_packet 不为空，必须优先使用 packet.source_excerpt 和 C0/C1/C2/C4，"
                "不得从全文或其他集 packet 自由补剧情。"
                "如果 previous_episode_handoff 不为空，第一场前 3-6 行必须照应上一集最后钩子，"
                "不能重开一个无关场面。"
                "current_episode_repair_packet.baseline_episode_text 是当前集旧稿的文本基准；"
                "除 editable_targets 指向的缺口外，protected_elements 必须照抄或语义等价保留。"
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
) -> str:
    return prompt_block(
        source_material_section(
            source_text,
            episode_source_packet=episode_source_packet,
        ),
        f"只二次编译第 {episode_number} 集的结尾钩子和对白密度。不要输出其他集数。",
        dump_model("previous_episode_handoff", previous_episode_handoff),
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("previous_context", previous_context),
        dump_model("existing_episode_to_polish", existing_episode),
        dump_model("current_episode_repair_packet", current_episode_repair_packet),
        dump_model("episode_plan", episode_plan),
        f"polish_instruction: {polish_instruction}",
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            (
                f"输出必须是一个完整 EpisodeScript；episode 字段必须等于 {episode_number}。"
                "这是结尾钩子/对白密度二次编译，不是整集重写；不要整集重写。"
                "如果 current_episode_repair_packet 不为空，current_episode_repair_packet.baseline_episode_text 是唯一文本基准。"
            ),
            (
                "先读 polish_instruction 的本地缺口；再定位 existing_episode 最后一场最后 8-12 行；"
                "最后只围绕短对白补足、OS 后动作承接、最后两行追更断点做最小改动。"
                "润色前必须核对本集 C0/C1：能增强镜头和短台词，不能改主角动机、主动方、因果顺序、关键决定时机或证据来源。"
            ),
            (
                "除最后 8-12 行、必要短对白/OS/VO 补足、OS 后紧跟动作外，必须保留 existing_episode 的"
                "标题、场景顺序、人物、已合格 action、信息状态和主线事实。"
                "必须优先遵守 current_episode_repair_packet.allowed_change_scope，"
                "不得改动 protected_elements 中的事实、人物关系、主动方、证据来源和上下集边界。"
                "如果 episode_plan / series_structure_plan 提供 cliffhanger_design 或 ending_hook_type，"
                "最后两行必须优先兑现该设计。"
                "如果 episode_source_packet 不为空，所有新增动作/道具/短对白必须可追溯到 packet 的 C0/C1/C2 或本集已出现内容。"
                "如果 previous_episode_handoff 不为空，不得改掉本集开头对上一集钩子的承接。"
                "如果 existing_episode 已正确保留 C1 名场面，不得为了更强钩子替换成无原文依据的新道具/新狠话；"
                "如果结尾要新增道具特写或威胁，只能使用本集已出现或上游已埋的资产。"
            ),
            (
                "结尾必须停在观众最想看下一秒的位置：身份将揭未揭、证据将爆未爆、威胁将落未落、"
                "关键道具亮出但未解释、强问题抛出但未回答。"
                "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作，"
                "禁止写成“留下悬念/关于真实身份的悬念/气氛紧张”等说明句。"
                f"{ACTION_LINE_TEMPLATE_RULE}{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
                "短对白每句只表达一个动作或情绪，不超过 22 个汉字；为补对白密度可以加入 2-6 行短促拉扯，"
                "但不能写成长解释或价值观总结。"
            ),
            (
                "禁止把结尾写成转身离开、我需要时间、明天再说、改天解释、画面冻结、黑屏、背影收束、"
                "普通离场或冲突解决。禁止新增与 Bible 冲突的设定，禁止为了补字数重讲背景。"
                "禁止在润色阶段新增 C4 内容；禁止把克制台词改成歇斯底里宣战，禁止用编造证据制造钩子。"
            ),
        ),
    )


def quality_user(
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    script_batch: BaseModel,
    previous_context: BaseModel | None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
    episode_plan: BaseModel | None = None,
    methodology_context: MethodologyContext | None = None,
) -> str:
    return prompt_block(
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("episode_plan", episode_plan),
        render_script_batch_digest("script_batch_digest", script_batch),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        section("内部方法论", render_methodology_context(methodology_context)),
        stage_instruction(
            "检查 script_batch 是否达到可交付短剧正片标准。只要出现任一硬伤，status=needs_rewrite，并在 rewrite_instruction 中逐集说明怎么补足。",
            (
                "本地确定性质检已经负责逐行硬指标：字数、行数、scene 数、action/dialogue 数量、"
                "action 格式、景别运镜、对白长度、最后两行模板和 metadata 泄漏。"
                "不要凭摘要声称逐行检查了每条 action 或每句对白，也不要把这些硬指标当成你的主要评分依据。"
            ),
            (
                "只基于 script_batch_digest 可见内容判断：戏剧质量、跨集连续性、人物动机、"
                "原著保真和题材模板一致性。重点看 opening_lines/tail_lines/scene_skeleton 是否显示"
                "冲突递进、信息增量、真实人物反应、原文 C0/C1 资产和可理解的关系状态。"
                "rewrite_instruction 必须指出第几集、哪个戏剧硬伤、回到哪条原文资产或哪段人物逻辑补救。"
                f"{SOURCE_FIDELITY_QUALITY_RULE}"
            ),
            (
                "如果 series_structure_plan 不为空，还要检查每集是否有信息增量、是否匹配对应 ending_hook_type、"
                "是否连续水集、是否偏离人物标签和全局节奏。"
                "cliffhanger 字段必须能在摘要中的 tail_lines 里找到可见承接；"
                "“留下悬念/关于身份的悬念/气氛紧张”等说明句不合格。"
                "必须检查第一场：原文有 C1 天然钩子但脚本删除/降级，或原文无天然钩子但脚本没有事实兼容型钩子，都不合格。"
                "必须检查人物：台词或动作若改变 Story Bible 中的人物动机、说话方式、关系状态，或把 C0 决策时机改掉，都不合格。"
                "如果摘要显示台词在解释价值观、同一情绪反复打转、上一集结尾和下一集开头不照应，必须指出。"
            ),
            (
                "如果用户可见剧本文本里把 hook/主情绪/watch_reason 当成独立说明展示，"
                "或出现“消费理由/观众要看/本集看点”等分析词，或摘要显示动作只是"
                "“众人震惊/气氛凝固/他很害怕”这种抽象描述，或对白显著啰嗦，也必须重写。"
                "题材模板错配必须拦截：男频穿越/大宋/武大郎/金莲/西门庆类不得混入"
                "真假千金/豪门宴会/总裁/亲子鉴定/大小姐模板，反向也不得串戏。"
            ),
        ),
    )


def state_user(
    source_analysis: BaseModel,
    episode_context: BaseModel,
    story_bible: BaseModel,
    script_batch: BaseModel,
    quality_report: BaseModel,
    previous_context: BaseModel | None,
    episode_plan: BaseModel | None = None,
    viral_asset_report: BaseModel | None = None,
    series_structure_plan: BaseModel | None = None,
) -> str:
    return prompt_block(
        dump_model("source_analysis", source_analysis),
        dump_model("viral_asset_report", viral_asset_report),
        dump_model("episode_context", episode_context),
        dump_model("story_bible", story_bible),
        dump_model("series_structure_plan", series_structure_plan),
        dump_model("episode_plan", episode_plan),
        render_script_batch_digest("script_batch_digest", script_batch),
        dump_model("quality_report", quality_report),
        dump_model("previous_context", previous_context),
        section("全局框架", GLOBAL_PROFESSIONAL_FRAME),
        stage_instruction(
            "生成 next_round_context，保留 open_hooks、forbidden_reveals、character_knowledge、relationship_changes、prop_states、foreshadowing_ledger。",
            (
                "先从 script_batch 最后一集向前回看本轮实际演出事实；再分离观众、主角、反派的知识层；"
                "随后记录关系变化、道具/证据状态、已埋/已回收伏笔；最后输出下一轮必须承接的 open_hooks 和 forbidden_reveals。"
            ),
            (
                "只回写 script_batch 中已经拍出来、说出来、露出来或被角色明确发现的内容；"
                "不得改写 story_bible，不得把新设定塞回 Bible，不得把未演出的小说原文当成本轮事实。"
                "character_knowledge 必须至少按 audience_known（观众已知）、protagonist_known（主角已知）、"
                "villain_known（反派已知）三类记录；每条写明谁知道什么、何时知道、哪些人仍不知道，用来维持信息差。"
            ),
            (
                "open_hooks 必须来自剧中实际演出的悬念，例如最后两行的威胁、动作未完成、"
                "道具特写、身份误会或已露出但未解释的证据；不能写营销看点、主题卖点、"
                "观众想看什么，也不能把已经揭示给观众和主角的信息再次列为 hook。"
                "forbidden_reveals 要记录下一轮不能重复揭示、不能提前公开、不能改口的事实。"
                "prop_states 必须保留关键道具/证据/伤口/文件的持有人、可见状态和最后出现位置；"
                "foreshadowing_ledger 必须标记每条伏笔是 seeded、paid_off 还是 still_open，"
                "并说明后续承接集数或禁止乱改的回收方向。"
            ),
            (
                "relationship_changes 只记录本轮已经通过动作或对白发生的关系变化，不写推测。"
                "不得把 quality_report 的问题当成剧情事实；不得把用户看点、平台卖点、主题总结写进 open_hooks；"
                "不得把已经付清的伏笔继续标 still_open，也不得把未出现的道具写入 prop_states。"
            ),
        ),
    )
```

## File: `src/novel_drama_engine/script_quality.py`

```py
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
    if structural_collapse:
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
) -> CurrentEpisodeRepairPacket:
    mode = episode_repair_mode(episode, base_instruction)
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
    editable_targets = warnings or [base_instruction.strip() or "未点名具体本地缺口"]
    return CurrentEpisodeRepairPacket(
        episode=episode.episode,
        repair_mode=mode,
        baseline_policy=(
            "当前集旧稿是唯一文本基准。修复只能在 baseline_episode_text 的基础上做最小必要改动；"
            "不得用 episode_plan、source packet 或全局质检意见覆盖当前集已成立的正片内容。"
        ),
        baseline_episode_text=render_episode(episode),
        allowed_change_scope=mode_scope[mode],
        editable_targets=editable_targets,
        protected_elements=protected_elements,
        continuity_requirements=[
            "保留当前集已演出的事实、人物关系、主动方、关键决定时机和证据来源。",
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
) -> str:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    mode = episode_repair_mode(episode, base_instruction)
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

    blocking_issues = [_issue_text(issue) for issue in issues if issue.severity == "blocking"]
    advisory_warnings = [_issue_text(issue) for issue in issues if issue.severity == "advisory"]
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
    return quality_report.model_copy(
        update={
            "status": QualityStatus.NEEDS_REWRITE
            if quality_report.status == QualityStatus.USABLE
            else quality_report.status,
            "blocking_issues": [
                *quality_report.blocking_issues,
                *[
                    f"script_novelty: {issue}"
                    for issue in novelty_report.blocking_issues
                ],
            ],
            "rewrite_instruction": "\n\n".join(
                part
                for part in [
                    quality_report.rewrite_instruction,
                    novelty_report.rewrite_instruction,
                ]
                if part.strip()
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

## File: `src/novel_drama_engine/adaptation_quality.py`

```py
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
    term = _forbidden_term(rule)
    if len(normalize_text(term)) < 2:
        return False
    return _loose_contains(script_text, term)


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

    for episode_number, asset in [
        pair
        for mapping in episode_context.source_to_episode_mapping
        for pair in _mapping_assets(mapping)
    ]:
        if len(normalize_text(asset)) < 4:
            continue
        target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
        if _loose_contains(target_text, asset):
            checks.append(
                SourceFidelityCheck(
                    category="source_mapping",
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
                category="source_mapping",
                anchor=asset,
                episode=episode_number,
                status=status,
                warning=warning,
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

    for rule in story_bible.forbidden_changes + episode_context.forbidden_reveals:
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
    if len(unknown_names) >= 3:
        warning = "script introduced multiple untracked speaking characters: " + "、".join(unknown_names[:6])
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

    score = max(0, 100 - len(blocking) * 18 - len(advisory) * 6)
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
    blocking = [
        *source_fidelity.blocking_warnings,
        *continuity.blocking_warnings,
        *ledger.blocking_warnings,
    ]
    advisory = [
        *source_fidelity.advisory_warnings,
        *continuity.advisory_warnings,
        *ledger.warnings,
    ]
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
                    episode=first_episode.episode if first_episode else None,
                    message=(
                        "强原文轻改失败：原文高价值画面/名场面没有在正片中被保留，"
                        "不能只重构成泛化冲突。"
                    ),
                    evidence=high_value_assets[:4],
                )
            )

    for negative_example in card.negative_examples[:5]:
        if not negative_example.strip():
            continue
        if _loose_contains(script_text, negative_example):
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id,
                    card_name=card.name,
                    severity="blocking",
                    episode=None,
                    message=f"强原文轻改失败：脚本疑似命中方法论反例：{negative_example}",
                    evidence=_evidence_for(script_text, negative_example),
                )
            )

    rewrite_instruction = ""
    if issues:
        rewrite_instruction = (
            "方法论阻断：本素材被判定为强原文，只允许轻改。必须回到原文 C0/C1："
            "保留开场钩子、主动方、因果顺序、关键决定时机和名场面；"
            "只做镜头视听化、短台词化、压缩和衔接补强。具体问题："
            + "；".join(issue.message for issue in issues[:6])
        )
    return MethodologyQualityReport(issues=issues, rewrite_instruction=rewrite_instruction)


def merge_methodology_quality_into_report(
    report,
    methodology_report: MethodologyQualityReport,
):
    blocking_issues = [
        issue.message
        for issue in methodology_report.issues
        if issue.severity == "blocking"
    ]
    if not blocking_issues:
        return report

    status = (
        QualityStatus.NEEDS_REWRITE
        if report.status == QualityStatus.USABLE
        else report.status
    )
    rewrite_instruction = "；".join(
        part
        for part in [
            methodology_report.rewrite_instruction,
            report.rewrite_instruction,
        ]
        if part
    )
    return report.model_copy(
        update={
            "status": status,
            "blocking_issues": [*report.blocking_issues, *blocking_issues],
            "rewrite_instruction": rewrite_instruction,
        }
    )


def merge_adaptation_quality_into_report(
    report,
    adaptation_report: AdaptationQualityReport,
):
    if not adaptation_report.blocking_warnings:
        return report

    blocking_issues = [
        *report.blocking_issues,
        *adaptation_report.blocking_warnings,
    ]
    rewrite_instruction = "；".join(
        part
        for part in [
            adaptation_report.rewrite_instruction,
            report.rewrite_instruction,
        ]
        if part
    )
    status = (
        QualityStatus.NEEDS_REWRITE
        if report.status == QualityStatus.USABLE
        else report.status
    )
    return report.model_copy(
        update={
            "status": status,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )
```

## File: `src/novel_drama_engine/drama_quality.py`

```py
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
from novel_drama_engine.script_quality import (
    episode_quality_metrics,
    episode_quality_warnings,
    has_explanatory_or_value_summary,
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

    score = round(adaptation_quality_report.source_fidelity.score / 10)
    evidence = [
        *adaptation_quality_report.source_fidelity.blocking_warnings[:2],
        *adaptation_quality_report.source_fidelity.advisory_warnings[:2],
    ]
    return _dimension(
        "source_asset_preservation",
        score,
        evidence=evidence,
        suggestion="恢复原文强冲突、关键情绪和不可改事实，避免为了爽点改掉核心逻辑。",
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


def build_drama_quality_report(
    *,
    script_batch: ScriptBatch,
    quality_report: QualityReport | None = None,
    adaptation_quality_report: AdaptationQualityReport | None = None,
    baseline_script_batch: ScriptBatch | None = None,
) -> DramaQualityReport:
    dimensions, warnings = _score_from_metrics(script_batch, quality_report)
    dimensions.append(_source_asset_dimension(adaptation_quality_report))
    overall = _overall(dimensions)
    blocking_issues = [
        f"{dimension.name}: {dimension.suggestion}"
        for dimension in dimensions
        if dimension.status == "blocking"
    ]
    advisory_warnings = [
        f"{dimension.name}: {dimension.suggestion}"
        for dimension in dimensions
        if dimension.status == "advisory"
    ]
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

    rewrite_parts = [
        issue.replace(": ", "：") for issue in [*blocking_issues, *advisory_warnings]
    ]
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
    rewrite_instruction = "；".join(
        part
        for part in [
            quality_report.rewrite_instruction,
            drama_quality_report.rewrite_instruction,
        ]
        if part.strip()
    )
    status = quality_report.status
    if status == QualityStatus.USABLE:
        status = QualityStatus.NEEDS_HUMAN_REVIEW
    return quality_report.model_copy(
        update={
            "status": status,
            "blocking_issues": issues,
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

## File: `src/novel_drama_engine/source_evidence.py`

```py
from __future__ import annotations

import re

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    ScriptBatch,
    SourceEvidenceItem,
    SourceEvidenceReport,
    SourceEvidenceSpan,
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
    return _split_assets(
        [
            *packet.c1_must_keep_assets,
            *packet.c2_visual_assets,
            *packet.golden_lines,
        ]
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

        line_entries = _script_line_entries(script)
        assets = _packet_assets(packet)
        if not assets:
            assets = [packet.source_anchor]

        adaptation_reason = _packet_reason(packet)
        evidence_spans: list[SourceEvidenceSpan] = []
        for asset in assets:
            evidence_spans.append(
                _evidence_span_for_asset(
                    packet,
                    asset,
                    line_entries,
                    adaptation_reason,
                )
            )

        total_count += 1
        script_evidence = [
            span.script_line for span in evidence_spans if span.script_line
        ]
        unique_evidence = list(dict.fromkeys(script_evidence))[:6]
        if unique_evidence:
            matched_count += 1
            status = "matched"
        else:
            status = "missing"
            missing_items.extend(
                f"EP{packet.episode:02d} 缺少原文资产：{asset}" for asset in assets
            )

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

## File: `src/novel_drama_engine/evaluation.py`

```py
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from inspect import signature
from pathlib import Path

from novel_drama_engine.baseline import run_direct_free_rewrite_baseline
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    render_drama_quality_report,
)
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.llm import LLMProviderAuthError, LLMProviderLimitError
from novel_drama_engine.models import (
    NextRoundContext,
    QualitySample,
    QualitySampleEvaluationReport,
    QualitySampleManifest,
    QualitySampleResult,
    QualitySampleRoundReport,
    QualityStatus,
    GenerationVariant,
    RoundResult,
)
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.renderer import render_creative_round, render_round_summary
from novel_drama_engine.script_quality import episode_quality_warnings
from novel_drama_engine.storage import ProjectStore


def read_quality_sample_manifest(path: Path) -> QualitySampleManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return QualitySampleManifest.model_validate(raw)


def safe_sample_dir_name(sample: QualitySample) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in sample.sample_id
    )


def round_warnings(result: RoundResult) -> list[str]:
    warnings: list[str] = []
    if not result.episode_context.target_episode_range.startswith("EP"):
        warnings.append("target episode range does not start with EP")
    if result.quality_report.status != QualityStatus.USABLE:
        warnings.append(f"quality status is {result.quality_report.status.value}")
    if not result.script_batch.episodes:
        warnings.append("no episodes generated")
    for episode in result.script_batch.episodes:
        if not episode.hook_3s.strip():
            warnings.append(f"EP{episode.episode:02d} missing 3s hook")
        if not episode.cliffhanger.strip():
            warnings.append(f"EP{episode.episode:02d} missing cliffhanger")
        if not episode.scenes:
            warnings.append(f"EP{episode.episode:02d} has no scenes")
        warnings.extend(episode_quality_warnings(episode))
    if result.next_round_context.current_episode < 1:
        warnings.append("next round context did not advance current episode")
    if result.adaptation_quality_report:
        warnings.extend(result.adaptation_quality_report.blocking_warnings)
    comparison = (
        result.drama_quality_report.baseline_comparison
        if result.drama_quality_report
        else None
    )
    if comparison and comparison.verdict != "pipeline_clearly_better":
        warnings.append(
            "pipeline is not clearly better than direct baseline: "
            f"{comparison.verdict} (delta {comparison.delta})"
        )
    return warnings


def build_round_report(
    result: RoundResult,
    generation_variant: GenerationVariant,
) -> QualitySampleRoundReport:
    scores = result.quality_report.scores
    adaptation_report = result.adaptation_quality_report
    comparison = (
        result.drama_quality_report.baseline_comparison
        if result.drama_quality_report
        else None
    )
    return QualitySampleRoundReport(
        round_number=result.round_number,
        generation_variant=generation_variant,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        hook_score=scores.hook,
        conflict_score=scores.conflict,
        cliffhanger_score=scores.cliffhanger,
        continuity_score=scores.continuity,
        video_feasibility_score=scores.video_feasibility,
        source_fidelity_score=(
            adaptation_report.source_fidelity.score if adaptation_report else None
        ),
        continuity_audit_score=(
            adaptation_report.continuity.score if adaptation_report else None
        ),
        baseline_overall_score=(
            comparison.baseline_overall_score if comparison else None
        ),
        pipeline_overall_score=(
            comparison.pipeline_overall_score if comparison else None
        ),
        baseline_delta=comparison.delta if comparison else None,
        baseline_verdict=comparison.verdict if comparison else None,
        baseline_reason=comparison.reason if comparison else None,
        source_fidelity_warnings=(
            [
                *adaptation_report.source_fidelity.blocking_warnings,
                *adaptation_report.source_fidelity.advisory_warnings,
            ]
            if adaptation_report
            else []
        ),
        continuity_warnings=(
            [
                *adaptation_report.continuity.blocking_warnings,
                *adaptation_report.continuity.advisory_warnings,
            ]
            if adaptation_report
            else []
        ),
        ledger_warnings=(
            adaptation_report.story_state_ledger.warnings
            if adaptation_report
            else []
        ),
        warnings=round_warnings(result),
    )


def is_provider_hard_failure(exc: Exception) -> bool:
    return isinstance(exc, (LLMProviderAuthError, LLMProviderLimitError))


@dataclass
class QualitySampleEvaluator:
    projects_dir: Path
    llm_factory: Callable[..., JsonLLM]
    baseline_llm_factory: Callable[..., JsonLLM] | None = None
    rounds_per_sample: int = 2
    generation_variant: GenerationVariant = GenerationVariant.CURRENT_DENSITY
    generation_variants: list[GenerationVariant] | None = None
    repair_budget: str | None = None
    include_direct_baseline: bool = False

    def variants(self) -> list[GenerationVariant]:
        if not self.generation_variants:
            return [self.generation_variant]
        return list(dict.fromkeys(self.generation_variants))

    def make_llm(
        self,
        round_number: int,
        previous_context: NextRoundContext | None,
        sample: QualitySample,
        generation_variant: GenerationVariant,
    ) -> JsonLLM:
        parameters = signature(self.llm_factory).parameters
        accepts_variant = (
            any(param.kind == param.VAR_POSITIONAL for param in parameters.values())
            or len(parameters) >= 4
        )
        if accepts_variant:
            return self.llm_factory(
                round_number,
                previous_context,
                sample,
                generation_variant,
            )
        return self.llm_factory(round_number, previous_context, sample)

    def make_baseline_llm(
        self,
        round_number: int,
        previous_context: NextRoundContext | None,
        sample: QualitySample,
        generation_variant: GenerationVariant,
    ) -> JsonLLM:
        factory = self.baseline_llm_factory or self.llm_factory
        parameters = signature(factory).parameters
        accepts_variant = (
            any(param.kind == param.VAR_POSITIONAL for param in parameters.values())
            or len(parameters) >= 4
        )
        if accepts_variant:
            return factory(
                round_number,
                previous_context,
                sample,
                generation_variant,
            )
        return factory(round_number, previous_context, sample)

    def attach_direct_baseline(
        self,
        *,
        result: RoundResult,
        store: ProjectStore,
        sample: QualitySample,
        generation_variant: GenerationVariant,
        previous_context: NextRoundContext | None,
    ) -> RoundResult:
        if not self.include_direct_baseline or result.round_number != 1:
            return result
        direct_baseline = run_direct_free_rewrite_baseline(
            self.make_baseline_llm(
                result.round_number,
                previous_context,
                sample,
                generation_variant,
            ),
            source_text=sample.source_text,
        )
        store.write_round_artifact(
            result.round_number,
            "baseline_direct_free_rewrite",
            direct_baseline,
        )
        store.write_text_artifact(
            result.round_number,
            "baseline_direct_free_rewrite.md",
            render_creative_round(direct_baseline),
        )
        comparison_report = build_drama_quality_report(
            script_batch=result.script_batch,
            quality_report=result.quality_report,
            adaptation_quality_report=result.adaptation_quality_report,
            baseline_script_batch=direct_baseline,
        )
        store.write_round_artifact(
            result.round_number,
            "baseline_comparison_report",
            comparison_report,
        )
        store.write_text_artifact(
            result.round_number,
            "baseline_comparison_report.md",
            render_drama_quality_report(comparison_report),
        )
        return result.model_copy(update={"drama_quality_report": comparison_report})

    def run(self, manifest_path: Path) -> QualitySampleEvaluationReport:
        manifest = read_quality_sample_manifest(manifest_path)
        results: list[QualitySampleResult] = []
        variants = self.variants()

        def write_report() -> QualitySampleEvaluationReport:
            report = QualitySampleEvaluationReport(samples=results, variants=variants)
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            (self.projects_dir / "quality_sample_report.json").write_text(
                report.model_dump_json(indent=2),
                encoding="utf-8",
            )
            return report

        for sample in manifest.samples:
            for generation_variant in variants:
                project_dir = self.projects_dir / safe_sample_dir_name(sample)
                if len(variants) > 1:
                    project_dir = project_dir / generation_variant.value
                store = ProjectStore(project_dir)
                previous_context: NextRoundContext | None = None
                round_reports: list[QualitySampleRoundReport] = []

                for round_number in range(1, self.rounds_per_sample + 1):
                    try:
                        result = RoundPipeline(
                            llm=self.make_llm(
                                round_number,
                                previous_context,
                                sample,
                                generation_variant,
                            ),
                            store=store,
                        ).run(
                            project_id=sample.sample_id,
                            round_number=round_number,
                            source_text=sample.source_text,
                            previous_context=previous_context,
                            generation_variant=generation_variant,
                            repair_budget=self.repair_budget,
                        )
                        result = self.attach_direct_baseline(
                            result=result,
                            store=store,
                            sample=sample,
                            generation_variant=generation_variant,
                            previous_context=previous_context,
                        )
                        rendered = render_round_summary(
                            result.script_batch,
                            result.quality_report,
                        )
                        store.write_text_artifact(
                            round_number,
                            "rendered_scripts.md",
                            rendered,
                        )
                        previous_context = result.next_round_context
                        round_reports.append(
                            build_round_report(result, generation_variant)
                        )
                    except Exception as exc:
                        round_reports.append(
                            QualitySampleRoundReport(
                                round_number=round_number,
                                generation_variant=generation_variant,
                                warnings=[str(exc)],
                            )
                        )
                        if is_provider_hard_failure(exc):
                            results.append(
                                QualitySampleResult(
                                    sample_id=sample.sample_id,
                                    label=sample.label,
                                    variant=generation_variant,
                                    project_dir=str(project_dir),
                                    rounds=round_reports,
                                )
                            )
                            write_report()
                            raise

                results.append(
                    QualitySampleResult(
                        sample_id=sample.sample_id,
                        label=sample.label,
                        variant=generation_variant,
                        project_dir=str(project_dir),
                        rounds=round_reports,
                    )
                )

        return write_report()
```

## File: `src/novel_drama_engine/baseline.py`

```py
from __future__ import annotations

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import DramaQualityReport, ScriptBatch
from novel_drama_engine.renderer import render_creative_round


BASELINE_DIRECT_SYSTEM = (
    "你是短剧编剧。把小说直接改成竖屏短剧分集脚本。"
    "这是 baseline：不要调用多 agent 链路，不要做复杂结构工程，只根据原文自由改写。"
    "仍需输出合法 ScriptBatch JSON。"
)


def baseline_direct_user(
    source_text: str,
    *,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
) -> str:
    target = str(target_episode_count) if target_episode_count else "未指定"
    return "\n\n".join(
        [
            f"目标总集数：{target}",
            f"本次输出集数：{episodes_per_round}",
            "要求：直接改写，不要解释，不要输出分析字段到 scene lines；保留原文最强冲突、人物动机和关键情绪。",
            "小说原文：",
            source_text,
        ]
    )


def run_direct_free_rewrite_baseline(
    llm: JsonLLM,
    *,
    source_text: str,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
) -> ScriptBatch:
    return llm.complete(
        system=BASELINE_DIRECT_SYSTEM,
        user=baseline_direct_user(
            source_text,
            target_episode_count=target_episode_count,
            episodes_per_round=episodes_per_round,
        ),
        response_model=ScriptBatch,
    )


def render_baseline_comparison(
    *,
    direct_baseline: ScriptBatch,
    pipeline_batch: ScriptBatch,
    drama_quality_report: DramaQualityReport | None = None,
) -> str:
    parts = []
    if drama_quality_report and drama_quality_report.baseline_comparison:
        comparison = drama_quality_report.baseline_comparison
        parts.extend(
            [
                "# Drama Quality Verdict",
                (
                    f"Pipeline {comparison.pipeline_overall_score}/10 vs "
                    f"Direct baseline {comparison.baseline_overall_score}/10 "
                    f"(delta {comparison.delta})"
                ),
                comparison.verdict,
                comparison.reason,
            ]
        )
    parts.extend(
        [
            "# Direct LLM Baseline",
            render_creative_round(direct_baseline),
            "# Current Pipeline",
            render_creative_round(pipeline_batch),
        ]
    )
    return "\n\n".join(parts)
```

## File: `tests/p0_platform.test.ts`

```ts
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import Database from "better-sqlite3";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

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

test("round generation unique error classification only matches the named index", () => {
  const source = readFileSync(path.join(repoRoot, "src/lib/jobs.ts"), "utf-8");

  assert.match(source, /jobs_active_round_generation_unique/);
  assert.doesNotMatch(source, /jobs_active_round_generation_unique\|unique/);
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
```

## File: `tests/test_pipeline.py`

```py
import json
import time
from typing import Any

import pytest
from pydantic import BaseModel

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import (
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    EpisodeScript,
    GenerationVariant,
    QualityReport,
    QualityScores,
    QualityStatus,
    RoundResult,
    Scene,
    SceneLine,
    ScriptBatch,
)
from novel_drama_engine.pipeline import (
    EmptySourceError,
    InstrumentedJsonLLM,
    RepairBudget,
    RoundPipeline,
    build_run_manifest,
    fallback_episode_repair_targets,
    normalize_repair_budget,
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


def test_pipeline_injects_methodology_context_into_script_prompt(tmp_path, happy_round_outputs):
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
    assert "内部方法论卡" in script_call["user"]
    assert "强原文轻改规则" in script_call["user"]
    assert "动作行三层结构与微型叙事弧" in script_call["user"]
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
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, repaired_episode, second_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        repair_budget="episode",
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    quality_path = tmp_path / "round_001" / "quality_report.json"
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert len(script_calls) == 1
    assert len(episode_repair_calls) == 1
    assert "needs_human_review" in quality_path.read_text(encoding="utf-8")
    assert (tmp_path / "round_001" / "round_result.json").exists()
    assert (tmp_path / "round_001" / "next_round_context.json").exists()
    assert (tmp_path / "round_001" / "quality_report_before_episode_repair.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()


def test_pipeline_episode_repair_targets_reported_episode_only(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    repaired_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"title": "定向修复第一集"},
    )
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 镜头密度仍不足"],
        rewrite_instruction="只重修 EP01，其他集保持边界不变。",
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
    llm = RecordingLLM(outputs[:4] + [first_quality, repaired_episode, final_quality, outputs[5]])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        repair_budget="episode",
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    )
    assert len(episode_repair_calls) == 1
    assert result.script_batch.episodes[0].title == "定向修复第一集"
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert target_text == "EP01"


def test_pipeline_polishes_episode_repair_when_local_quality_still_fails(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚，她站在门口。"),
                        SceneLine(kind="dialogue", speaker="林晚", text="让开。"),
                        SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                    ],
                )
            ],
            "cliffhanger": "让开。",
        },
    )
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
    llm = RecordingLLM(
        outputs[:4] + [first_quality, bad_episode, first_script.episodes[0], final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        repair_budget="episode",
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert len(episode_repair_calls) == 2
    assert "当前本地质检" in episode_repair_calls[-1]["user"]
    assert (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert (tmp_path / "round_001" / "episode_polish_instructions.md").exists()


def test_pipeline_skips_optional_polish_by_default(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚，她站在门口。"),
                        SceneLine(kind="dialogue", speaker="林晚", text="让开。"),
                        SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                    ],
                )
            ],
            "cliffhanger": "让开。",
        },
    )
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
    llm = RecordingLLM(outputs[:4] + [first_quality, bad_episode, final_quality, outputs[5]])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        repair_budget="episode",
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    skipped_stages = {
        stage.name
        for stage in result.runtime_report.stages
        if stage.status == "skipped"
    }
    assert len(episode_repair_calls) == 1
    assert "episode_quality_polish" in skipped_stages
    assert (tmp_path / "round_001" / "episode_polish_instructions.md").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()


def test_pipeline_keeps_previous_episode_when_optional_polish_fails(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚，她站在门口。"),
                        SceneLine(kind="dialogue", speaker="林晚", text="让开。"),
                        SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                    ],
                )
            ],
            "cliffhanger": "让开。",
        },
    )
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
    llm = RecordingLLM(
        outputs[:4]
        + [first_quality, bad_episode]
        + [
            RuntimeError("provider returned scene object"),
            RuntimeError("provider returned scene object"),
            final_quality,
            outputs[5],
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出生日宴。",
        repair_budget="episode",
    )

    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert result.script_batch.episodes[0] == bad_episode
    assert (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert (tmp_path / "round_001" / "episode_quality_polish_failures.md").exists()
    assert (tmp_path / "round_001" / "hook_dialogue_polish_failures.md").exists()


def test_pipeline_runs_hook_dialogue_polish_for_soft_tail_after_quality_polish(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    soft_tail_episode = first_script.episodes[0].model_copy(deep=True)
    soft_tail_episode.cliffhanger = "明天再说。"
    soft_tail_episode.scenes[-1].lines[-2:] = [
        SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
        SceneLine(kind="action", text="△中景林晚转身离开。"),
    ]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
       

<!-- truncated 5277 chars -->
```

## File: `tests/test_script_quality.py`

```py
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

## File: `tests/test_adaptation_quality.py`

```py
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

## File: `tests/test_drama_quality.py`

```py
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    merge_drama_quality_into_report,
)
from novel_drama_engine.models import (
    DramaQualityReport,
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
)


def test_drama_quality_report_scores_demo_script_as_deliverable():
    source, context, bible, script_batch, quality_report = demo_round_outputs()[:5]

    report = build_drama_quality_report(
        script_batch=script_batch,
        quality_report=quality_report,
    )

    assert report.overall_score >= 7
    assert not report.blocking_issues
    assert {dimension.name for dimension in report.dimensions} >= {
        "character_integrity",
        "conflict_causality",
        "emotional_progression",
        "dialogue_naturalness",
        "source_asset_preservation",
        "hook_and_cliffhanger",
    }


def test_drama_quality_comparison_requires_pipeline_to_beat_baseline():
    outputs = demo_round_outputs()
    pipeline_batch = outputs[3]
    baseline_batch = ScriptBatch(episodes=[pipeline_batch.episodes[0]])

    report = build_drama_quality_report(
        script_batch=baseline_batch,
        baseline_script_batch=pipeline_batch,
    )

    assert report.baseline_comparison is not None
    assert report.baseline_comparison.verdict in {"tie", "baseline_better"}
    assert any("direct LLM baseline" in issue for issue in report.blocking_issues)


def test_merge_drama_quality_keeps_usable_report_clean_when_only_drama_score_is_low():
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
    drama_report = DramaQualityReport(
        overall_score=6,
        blocking_issues=[],
        advisory_warnings=["情绪递进偏弱"],
        rewrite_instruction="加强情绪递进，但不阻断交付。",
    )
    merged = merge_drama_quality_into_report(quality_report, drama_report)

    assert merged.status == QualityStatus.USABLE
    assert merged.blocking_issues == []
    assert merged.rewrite_instruction == ""
```

## File: `tests/test_source_evidence.py`

```py
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    Scene,
    SceneLine,
    ScriptBatch,
)
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
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
                c2_visual_assets=["宴会厅侧门", "旧木盒打开"],
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

## File: `tests/test_evaluation.py`

```py
import json

import pytest
from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.evaluation import (
    QualitySampleEvaluator,
    read_quality_sample_manifest,
)
from novel_drama_engine.llm import LLMProviderLimitError, StaticJsonLLM
from novel_drama_engine.models import (
    EpisodeScript,
    GenerationVariant,
    Scene,
    SceneLine,
    ScriptBatch,
)


def write_sample_manifest(path):
    path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "sample_id": "haomen",
                        "label": "豪门羞辱",
                        "source_text": "林晚在生日宴上被当众羞辱。",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class FailingLLM:
    def __init__(self, exc):
        self.exc = exc

    def complete(self, *, system, user, response_model):
        raise self.exc


def test_quality_sample_evaluator_runs_multiple_rounds(
    tmp_path,
    happy_round_outputs,
):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    second_round_outputs = demo_round_outputs(
        round_number=2,
        previous_context=happy_round_outputs[-1],
        include_story_bible=False,
    )
    output_sets = iter([happy_round_outputs, second_round_outputs])

    report = QualitySampleEvaluator(
        projects_dir=tmp_path / "eval",
        llm_factory=lambda round_number, previous_context, sample: StaticJsonLLM(
            next(output_sets)
        ),
        rounds_per_sample=2,
    ).run(manifest)

    assert report.passed_count == 1
    assert report.failed_count == 0
    assert len(report.samples[0].rounds) == 2
    assert (tmp_path / "eval" / "quality_sample_report.json").exists()
    assert (
        tmp_path
        / "eval"
        / "haomen"
        / "round_002"
        / "rendered_scripts.md"
    ).exists()


def test_quality_sample_evaluator_records_direct_baseline_comparison(
    tmp_path,
    happy_round_outputs,
):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    weak_baseline = ScriptBatch(
        episodes=[
            EpisodeScript(
                episode=1,
                title="弱 baseline",
                hook_3s="她来了。",
                main_emotion="平",
                watch_reason="baseline",
                scenes=[
                    Scene(
                        heading="1-1 日-内-屋内",
                        characters=["甲"],
                        lines=[
                            SceneLine(kind="action", text="△中景推近甲站着。"),
                            SceneLine(kind="dialogue", speaker="甲", text="来了。"),
                        ],
                    )
                ],
                cliffhanger="她来了。",
                state_update={},
            )
        ]
    )

    report = QualitySampleEvaluator(
        projects_dir=tmp_path / "eval",
        llm_factory=lambda round_number, previous_context, sample: StaticJsonLLM(
            list(happy_round_outputs)
        ),
        baseline_llm_factory=lambda round_number, previous_context, sample: StaticJsonLLM(
            [weak_baseline]
        ),
        rounds_per_sample=1,
        include_direct_baseline=True,
    ).run(manifest)

    round_report = report.samples[0].rounds[0]

    assert report.passed_count == 1
    assert round_report.baseline_verdict == "pipeline_clearly_better"
    assert round_report.baseline_delta is not None
    assert round_report.baseline_delta >= 2
    assert (
        tmp_path
        / "eval"
        / "haomen"
        / "round_001"
        / "baseline_direct_free_rewrite.json"
    ).exists()
    assert (
        tmp_path
        / "eval"
        / "haomen"
        / "round_001"
        / "baseline_comparison_report.json"
    ).exists()


def test_quality_sample_evaluator_fails_fast_on_provider_limit(tmp_path):
    manifest = tmp_path / "samples.json"
    manifest.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "sample_id": "quota_case",
                        "label": "额度失败样本",
                        "source_text": "林晚在生日宴上被当众羞辱。",
                    },
                    {
                        "sample_id": "should_not_run",
                        "label": "不应继续执行",
                        "source_text": "顾承发现鉴定报告被调包。",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    projects_dir = tmp_path / "eval"

    with pytest.raises(LLMProviderLimitError):
        QualitySampleEvaluator(
            projects_dir=projects_dir,
            llm_factory=lambda round_number, previous_context, sample, variant: FailingLLM(
                LLMProviderLimitError(
                    "LLM_PROVIDER_LIMIT: provider quota or key daily limit exceeded"
                )
            ),
            rounds_per_sample=2,
            generation_variants=[
                GenerationVariant.SOP_FULL_STACK,
                GenerationVariant.DRAMA_ENGINE_FIRST,
            ],
        ).run(manifest)

    report = json.loads(
        (projects_dir / "quality_sample_report.json").read_text(encoding="utf-8")
    )
    assert [sample["sample_id"] for sample in report["samples"]] == ["quota_case"]
    assert report["samples"][0]["rounds"][0]["round_number"] == 1
    assert "LLM_PROVIDER_LIMIT" in report["samples"][0]["rounds"][0]["warnings"][0]


def test_read_quality_sample_manifest_validates_samples(tmp_path):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)

    parsed = read_quality_sample_manifest(manifest)

    assert parsed.samples[0].sample_id == "haomen"


def test_cli_evaluate_samples_writes_report(tmp_path):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    projects_dir = tmp_path / "eval"

    result = CliRunner().invoke(
        cli.app,
        [
            "evaluate-samples",
            "--mock",
            "--samples",
            str(manifest),
            "--projects-dir",
            str(projects_dir),
            "--rounds",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "Quality samples: 1 passed, 0 failed" in result.stdout
    assert (projects_dir / "quality_sample_report.json").exists()


def test_quality_sample_evaluator_runs_multiple_variants(tmp_path):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    output_sets = iter(
        [
            demo_round_outputs(include_sop_stack=True, include_episode_plan=True),
            demo_round_outputs(include_episode_plan=True),
        ]
    )

    report = QualitySampleEvaluator(
        projects_dir=tmp_path / "eval",
        llm_factory=lambda round_number, previous_context, sample, variant: StaticJsonLLM(
            next(output_sets)
        ),
        rounds_per_sample=1,
        generation_variants=[
            GenerationVariant.SOP_FULL_STACK,
            GenerationVariant.DRAMA_ENGINE_FIRST,
        ],
    ).run(manifest)

    assert report.variants == [
        GenerationVariant.SOP_FULL_STACK,
        GenerationVariant.DRAMA_ENGINE_FIRST,
    ]
    assert [sample.variant for sample in report.samples] == [
        GenerationVariant.SOP_FULL_STACK,
        GenerationVariant.DRAMA_ENGINE_FIRST,
    ]
    assert (
        tmp_path
        / "eval"
        / "haomen"
        / "sop_full_stack"
        / "round_001"
        / "rendered_scripts.md"
    ).exists()
```
