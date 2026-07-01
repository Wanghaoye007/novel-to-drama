# Novel-to-Drama

把参差不齐的小说原料自动改编成符合标准格式的短剧脚本，并逐步输出可投放、可本地化、可进入视频生成链路的生产资产。

当前仓库包含两条主线：

- Web v0: Next.js 16 + React 19 + Tailwind 4 + shadcn/ui + SQLite + Drizzle + Anthropic SDK。
- Python Engine MVP: round-based CLI 引擎，支持小说到短剧脚本、批量任务、视频 brief、本地化 package。

## Web App v0

完整流水线 M1 -> M6 + 轮次 5 集/轮 + 跨轮上下文衔接 + 三视角自查 + zip 导出。

Spec: `docs/specs/2026-05-14-novel-to-drama-design.md`
Plan: `docs/superpowers/plans/2026-05-15-novel-to-drama-v0.md`
Smoke: `e2e/smoke.md`

### Start Web App

```bash
cp .env.local.example .env.local
# Fill ANTHROPIC_API_KEY

npm install
npm run db:migrate
npm run dev
# Visit http://localhost:3000
```

Optional LLM smoke:

```bash
npx tsx scripts/test-llm.ts
```

### Web Flow

1. 首页点「新建项目」。
2. 上传 txt/docx 小说 + 选目标集数，等待进入 Bible 页。
3. 审 Bible，可手改后点「开始第 1 轮」。
4. 轮次进度页轮询，看 score 和红/绿标。
5. 红标可重跑。
6. 跑完点「开始下一轮」，跨轮上下文自动衔接。
7. 全跑完后在完成页下载 zip。

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
headline scores, episode titles, open hooks, artifacts, delivery preflight
state, and the latest context file. Use `--json-output` for the machine-readable
`project_status.v1` snapshot that Web can consume without reimplementing round
logic.

### Run Quality Sample Backtests

Use the default five-genre sample set to run at least two rounds per genre and
check hook, conflict, cliffhanger, character knowledge, secret reveal control,
and shootability.

```bash
novel-drama quality-samples \
  --mock \
  --manifest examples/quality_samples.json \
  --projects-dir .drama_quality_samples
```

The command writes per-sample round artifacts plus
`.drama_quality_samples/quality_sample_report.json`. Use `--strict` to fail
automation when any check fails, or `--json-output` for machine-readable output.
The same run is available through `POST /quality-samples/run-mock` or
`POST /quality-samples/run`.

### Manage Localization Profiles

List platform and region profiles:

```bash
novel-drama localization-profiles --json-output
```

Default profiles live in `examples/localization_profiles` and include
`us_tiktok`, `us_reela`, `jp_reela`, and `sea_tiktok`.

## Run The API

```bash
novel-drama serve --reload
```

This wraps `uvicorn novel_drama_engine.api:app`.
If `novel-drama` is not on `PATH`, use `python3 -m novel_drama_engine serve --reload`.

Useful read-only endpoints:

- `GET /health`
- `GET /localization-profiles?profiles_dir=examples/localization_profiles`
- `GET /localization-profiles/{profile_id}?profiles_dir=examples/localization_profiles`
- `GET /jobs?jobs_dir=.drama_jobs`
- `GET /jobs/{job_id}?jobs_dir=.drama_jobs`
- `GET /projects?project_root=.drama_projects&jobs_dir=.drama_jobs`
- `GET /projects/status?project_dir=.drama_project&jobs_dir=.drama_jobs`
- `GET /projects/delivery?project_dir=.drama_project&round_number=1`
- `GET /projects/delivery/package?project_dir=.drama_project&round_number=1`
- `GET /projects/artifacts?project_dir=.drama_project&round_number=1`
- `GET /projects/artifact?project_dir=.drama_project&round_number=1&name=rendered_scripts.md`
- `GET /projects/{project_id}/status?project_root=.drama_projects&jobs_dir=.drama_jobs`
- `GET /projects/{project_id}/rounds/{round_number}/artifacts?project_root=.drama_projects`
- `GET /projects/{project_id}/rounds/{round_number}/delivery?project_root=.drama_projects`
- `GET /projects/{project_id}/rounds/{round_number}/delivery/package?project_root=.drama_projects`

Generation endpoints for platform wiring:

- `POST /jobs/batch-run` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /jobs/batch-run-mock` (returns a persisted async job record)
- `POST /jobs/{job_id}/cancel?jobs_dir=.drama_jobs`
- `POST /jobs/{job_id}/retry?jobs_dir=.drama_jobs`
- `POST /quality-samples/run` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /quality-samples/run-mock`
- `POST /projects/batch-run` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /projects/batch-run-mock`
- `POST /projects/run` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /projects/run-full` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /projects/run-mock`
- `POST /projects/run-full-mock`
- `POST /projects/localize` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /projects/localize-mock`
- `POST /projects/ad-assets` (uses `OPENAI_API_KEY`, optional request `model`)
- `POST /projects/ad-assets-mock`
- `POST /projects/export-video-brief`
- `POST /projects/export-delivery`
- `POST /projects/{project_id}/rounds/{round_number}/delivery/export?project_root=.drama_projects`

Full run body:

```json
{
  "project_dir": ".drama_project",
  "project_id": "demo",
  "source_text": "林晚被赶出生日宴。",
  "locale": "en-US",
  "platform": "TikTok",
  "deliverables": ["localization", "ad_assets", "video_brief"],
  "duration_seconds": 75,
  "aspect_ratio": "9:16"
}
```

Async mock batch body:

```json
{
  "jobs_dir": ".drama_jobs",
  "project_root": ".drama_projects",
  "jobs": [
    {
      "project_id": "demo",
      "source_text": "林晚被赶出生日宴。",
      "deliverables": ["localization", "ad_assets", "video_brief"]
    }
  ]
}
```

The API writes one job status JSON file under `jobs_dir` and returns `job_id`,
`jobs_dir`, and `job_path`. Poll `GET /jobs/{job_id}?jobs_dir=.drama_jobs` until
`status` is `succeeded` or `failed`.

Batch run body:

```json
{
  "project_root": ".drama_projects",
  "jobs": [
    {
      "project_id": "haomen-us",
      "source_text": "林晚被赶出生日宴。",
      "locale": "en-US",
      "platform": "TikTok",
      "deliverables": ["localization", "ad_assets", "video_brief"]
    }
  ]
}
```

Batch API calls also write `batch_report.json` under `project_root`.

## Localize A Generated Round

```bash
novel-drama localize \
  --mock \
  --project-dir .drama_project \
  --round-number 1 \
  --locale en-US \
  --platform TikTok
```

The localization command reads `round_result.json`, adapts the script for the
target locale and platform, and writes:

- `localization_<locale>_<platform>.json`
- `localized_scripts_<locale>_<platform>.md`

If `--round-number` is omitted, the latest completed round is localized.

## Generate Localized Ad Assets

```bash
novel-drama ad-assets \
  --mock \
  --project-dir .drama_project \
  --locale en-US \
  --platform TikTok
```

The ad assets command reads the round result and, when available, the matching
localized script. It writes:

- `marketing_assets_<locale>_<platform>.json`
- `marketing_assets_<locale>_<platform>.md`

The output includes campaign angle, titles, short descriptions, opening hooks,
hashtags, CTA, audience notes, and compliance notes.

## Export A Video Production Brief

```bash
novel-drama export-video-brief \
  --project-dir .drama_project \
  --round-number 1 \
  --duration-seconds 75 \
  --aspect-ratio 9:16
```

The video brief command reads `round_result.json` and writes:

- `video_brief.json`
- `video_brief.md`

The output is a deterministic downstream production brief with episode hooks,
cliffhangers, vertical shot prompts, camera notes, audio notes, dialogue beats,
characters, scene headings, and asset requirements.

## Batch Run A Source Directory

```bash
novel-drama batch \
  --mock \
  --input-dir examples \
  --project-root .drama_projects
```

The batch command finds matching source files, creates one project directory per
source file, runs the same round pipeline, and prints one status line per source.
Use `--pattern "**/*.txt"` to include nested source folders.

You can also drive batch jobs from a manifest:

```json
{
  "jobs": [
    {
      "source": "novels/haomen.txt",
      "project_id": "haomen-cn",
      "project_dir": "haomen-cn",
      "round_number": 1,
      "locale": "en-US",
      "platform": "TikTok",
      "deliverables": ["localization", "ad_assets"]
    }
  ]
}
```

```bash
novel-drama batch \
  --mock \
  --manifest batch.json \
  --project-root .drama_projects
```

Manifest `source` and `context` paths are resolved relative to the manifest file.
Relative `project_dir` values are resolved under `--project-root`.
When `deliverables` includes `localization` or `ad_assets`, batch also writes the
matching localized scripts and marketing assets for the job's locale and platform.

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

You can also select a managed profile by id:

```bash
novel-drama export-localization \
  --project-dir .drama_project \
  --profile-id us_tiktok
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

### Export A Delivery Package

Check whether a round is deliverable before packaging:

```bash
novel-drama check-delivery --project-dir .drama_project
```

Use `--strict` when you want CI or automation to fail on warnings.
The same preflight is available to Web through `GET /projects/delivery` or
`GET /projects/{project_id}/rounds/{round_number}/delivery`.

Package a completed round into one zip for handoff to production, localization,
or platform delivery workflows.

```bash
novel-drama export-delivery --project-dir .drama_project
```

The command writes `.drama_project/round_001/delivery_round_001.zip` with a
`delivery_manifest.json` and all non-zip artifacts from that round.
The same export is available through `POST /projects/export-delivery` or
`POST /projects/{project_id}/rounds/{round_number}/delivery/export`.

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

### CLI Path Note

If `novel-drama` is not on `PATH`, use the installed script path printed by pip. On this machine it is:

```bash
/Users/wangzipeng/Library/Python/3.14/bin/novel-drama --help
```

## 来源

设计灵感和方法论来自 `~/Documents/DJ_Project/` 短剧改编方法论库。
