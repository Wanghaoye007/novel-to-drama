# Archived: Novel-to-Drama Web v0 Plan

This file used to contain the first Web v0 implementation plan. That plan
described a TypeScript M1-M5 generation chain and a direct legacy Claude SDK
wrapper.
It is archived because the current production architecture has converged on a
single generation runtime:

- Web owns projects, jobs, permissions, operator UI, and exports.
- Python Engine owns source packets, Story Bible, prompts, script generation,
  quality gates, repair, and artifacts.
- Web job workers call `python3 -m novel_drama_engine.cli`; TypeScript does not
  implement novel-to-script generation.

Current implementation references:

- `README.md`
- `src/lib/engine-runner.ts`
- `src/novel_drama_engine/`
- `docs/OPERATIONS_MVP.md`
