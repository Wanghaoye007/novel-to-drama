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
2. 上传 txt/docx 小说 + 选目标集数。
3. 系统自动生成 Story Bible 和第 1 轮脚本。
4. 轮次页轮询 Engine 状态，查看质量分、上下文和脚本。
5. 跑完点「开始下一轮」，系统按原文和 context 自动识别集数。
6. 每轮可生成视频 brief、本地化包、交付预检和 delivery zip。
7. Story Bible 页面仅展示系统状态，不作为用户确认门。
8. 首页「质量门禁」可运行五类样本评估，查看通过/失败、每轮分数和 warning。
9. Engine 轮次和质量门禁都会写入 job 状态，页面可查看进度、完成时间和错误。

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

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-5.5"
novel-drama run --input examples/haomen_source.txt --project-dir .drama_project --project-id demo --round-number 1
```

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
- `.drama_project/round_001/script_batch.json`
- `.drama_project/round_001/quality_report.json`
- `.drama_project/round_001/round_result.json`
- `.drama_project/round_001/next_round_context.json`
- `.drama_project/round_001/rendered_scripts.md`

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

The Web app exposes the same gate at `/quality`. It stores reports under
`storage/system/quality_samples/tenants/<tenant-id>/` by default, follows the
same mock/real mode selection as project generation, and records a tenant-scoped
job row for progress/error tracking.

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

You can scope worker runs:

```bash
npm run jobs:work -- --kind round_generation --limit 5
npm run jobs:work -- --kind quality_samples --limit 1
```

### CLI Path Note

If `novel-drama` is not on `PATH`, use the installed script path printed by pip. On this machine it is:

```bash
/Users/wangzipeng/Library/Python/3.14/bin/novel-drama --help
```

## 来源

设计灵感和方法论来自 `~/Documents/DJ_Project/` 短剧改编方法论库。
