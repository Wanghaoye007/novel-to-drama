# UI Functional QA - 2026-07-23

## Scope

Isolated local runtime with a temporary SQLite database, mock round engine, and background job worker. Browser checks used the real Next.js pages and API routes; no operations data was modified.

## Interaction matrix

| Area | Controls checked | Result |
| --- | --- | --- |
| Project creation | name, target episodes, strategy, repair budget, episodes per round, model, multipart upload | Pass. Browser file chooser could not expose a selected file in the automation harness; the same multipart route passed through HTTP upload. |
| Project workspace | episode selection, copy script, manage/rename/target edit, delete, clone | Pass. E03 selection updated the script pane; copy populated the clipboard; destructive delete redirected to the list. |
| Runtime controls | pause, resume, batch run, stop batch, retry | Pass. Status and disabled states refreshed without a manual reload. |
| Round controls | strategy, repair budget, 1-5 episode count, Doubao/Gemini model | Pass. Selected values remained visible and were included in queued jobs. |
| Script tools | AI optimize, edit-impact analysis | Pass for queueing and error/success rendering. AI optimize correctly reported the missing real-model key in the isolated mock environment; edit-impact completed and updated the episode. |
| Export | TXT, Word, video brief, localization profile, delivery preflight, delivery package | Pass. Browser download events are not emitted for the app's programmatic blob download, so success was verified from UI state and API/job completion. |
| Story assets | complete page, Story Bible page | Pass. Generated scripts and internal context rendered. |
| Platform | API key create/revoke, member add/role/remove, plan switch, simulated credit payment, workspace session | Pass after member-form reset fix. |
| Methodology | built-in sync, refresh, source inputs, draft generation, card activation | Pass. |
| Quality regression | refresh, single strategy, three-strategy comparison | Pass for job execution and report rendering. A quality-gate failure remains a valid regression result, not a UI failure. |

## Defects fixed

1. `NOVEL_DRAMA_STORAGE_ROOT` was ignored, so isolated or deployed jobs wrote into the checkout. Storage paths now resolve the configured root at call time.
2. Mock multi-round runs failed when artifact reuse skipped an LLM stage. The deterministic mock now selects the next fixture by requested response model while production LLM behavior remains unchanged.
3. Cloning a one-episode project queued and labelled a five-episode round. Clone and round sizing are now capped by the remaining target episodes, and the initial range is rendered as `EP01-EP01` instead of `Round 1`.
4. The member form retained email and role after an asynchronous submit because it referenced `event.currentTarget` after `await`. The form element is captured before the request and reset after success.
5. Three-strategy quality reports reused `sample_id` as a React key, producing duplicate-key errors and potentially unstable rows. Keys now include the strategy variant.

## Automated evidence

- `npm run check`
- Browser console recheck on the three-strategy report: no errors or warnings after the key fix.
- Regression coverage added for storage root resolution, target-bounded round sizing, async form reset, strategy-scoped keys, and multi-round mock execution with artifact resume disabled.
