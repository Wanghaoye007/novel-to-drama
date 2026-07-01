# Smoke E2E

Run manually after `npm run dev` is up. Use `NOVEL_DRAMA_WEB_MOCK=1` for a fast
local UI smoke, or set `OPENAI_API_KEY` and `NOVEL_DRAMA_WEB_MOCK=0` for a real
Engine run.

Fixture: `/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt`
(Or pick any from `~/Documents/DJ_Project/木木给的脚本/`)

## Prerequisites

```bash
cd ~/Documents/novel-to-drama
cp .env.local.example .env.local
# Optional real run: add OPENAI_API_KEY and NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_WEB_MOCK=1 npm run dev
```

Optional CLI pre-flight:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
novel-drama --help
```

## Steps

1. Open http://localhost:3000
2. Click "新建项目"
3. Fill: name "祖母穿越女 smoke", target episode count 6
4. Upload the fixture txt
5. Submit. The app should navigate directly to `/rounds/1`.
6. Round progress page polls every 3s while the Engine generates artifacts.
7. After round 1 done, verify:
   - [ ] Episode cards appear for the Engine-selected range
   - [ ] Each has a numeric score (0-10)
   - [ ] Script preview uses the short-drama rendered format
   - [ ] Context card shows current episode and open hooks
8. Click "系统 Bible":
   - [ ] Story Bible JSON is present
   - [ ] Context mapping is read-only
   - [ ] There is no user confirmation gate
9. Return to the round page.
10. Click "生成视频 brief", then "生成本地化包", then "交付预检".
11. Verify delivery preflight shows ready or explicit warnings.
12. Click "开始第 2 轮".
13. Verify `bibles.prev_round_summary_json` updates after the next round.
14. Click "下载交付包".
15. In Finder, open the downloaded zip:
    - [ ] `delivery_manifest.json` is present
    - [ ] `round_result.json` is present
    - [ ] `rendered_scripts.md` is present
    - [ ] `video_brief.*` and `localization_*` are present if generated

## Pass criteria

- Pipeline completes without crash
- Web flow does not require Story Bible confirmation
- Round 2 starts from stored context automatically
- Delivery preflight and zip use Engine artifacts
- `bibles.prev_round_summary_json` is populated after round 1

## Known cost expectation

- Mock mode is free and deterministic.
- Real mode uses the OpenAI model configured by `OPENAI_MODEL`.
- Each round runs the Python Engine's six structured stages.
