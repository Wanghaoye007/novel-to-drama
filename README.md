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

## Export A Video Brief

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

## Run A Batch

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

## CLI Path Note

If `novel-drama` is not on `PATH`, use the installed script path printed by pip. On this machine it is:

```bash
/Users/wangzipeng/Library/Python/3.14/bin/novel-drama --help
```
