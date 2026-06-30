# Novel Drama Engine

Round-based MVP for turning Chinese novel text into short-drama scripts.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Test

```bash
python3 -m pytest
```

## Run

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

## Run Without An API Key

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

## Continue A Second Round

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

## Check Project Status

```bash
novel-drama status --project-dir .drama_project
```

The status command lists completed rounds, target episode ranges, quality status,
headline scores, episode titles, open hooks, and the latest context file.

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

## CLI Path Note

If `novel-drama` is not on `PATH`, use the installed script path printed by pip. On this machine it is:

```bash
/Users/wangzipeng/Library/Python/3.14/bin/novel-drama --help
```
