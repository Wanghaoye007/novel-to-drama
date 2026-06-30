# Novel Drama Engine

Round-based MVP for turning Chinese novel text into short-drama scripts.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run

```bash
export OPENAI_API_KEY="your-key"
novel-drama run --input examples/haomen_source.txt --project-dir .drama_project
```

The command writes JSON artifacts and rendered scripts under `.drama_project/`.
