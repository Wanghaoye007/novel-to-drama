# Smoke E2E

Run manually after `npm run dev` is up and `.env.local` has `ANTHROPIC_API_KEY` set.

Fixture: `/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt`
(Or pick any from `~/Documents/DJ_Project/木木给的脚本/`)

## Prerequisites

```bash
cd ~/Documents/novel-to-drama
cp .env.local.example .env.local
# Edit .env.local and put your real ANTHROPIC_API_KEY
npm run dev
```

Optional pre-flight LLM check:

```bash
npx tsx scripts/test-llm.ts
# Should print: LLM said: hello world (or similar)
```

## Steps

1. Open http://localhost:3000
2. Click "新建项目"
3. Fill: name "祖母穿越女 smoke", target episode count 10
4. Upload the fixture txt
5. Submit. Wait 2-3 min for Bible page to appear.
6. Verify on Bible page:
   - [ ] Channel detected (likely 女频)
   - [ ] 六大资产 JSON not empty
   - [ ] Characters list shows 4-8 角色 with full bios
   - [ ] Episode plan covers E01-E10 split into 2 rounds (E01-E05 / E06-E10)
7. Click "开始第 1 轮"
8. Round progress page polls every 3s. Wait ~15-25 min while episodes generate.
9. After round 1 done, verify:
   - [ ] 5 episode cards appear E01-E05
   - [ ] Each has a numeric score (0-10)
   - [ ] Each has script preview text in [SCENE]/[ACTION]/[SPEAKER] format
   - [ ] Status badges green for ≥9.0, red for <9.0
10. Click "开始第 2 轮"
11. Verify (via DB or server logs):
    - [ ] On E06's generation, the prompt sent to Opus contains the round 1 summary
       - Quick check: open `db.sqlite` in Drizzle Studio (`npm run db:studio`) or sqlite3 CLI, look at `bibles.prev_round_summary_json` after round 1 — should be populated JSON
12. Wait for round 2 ~15-25 min.
13. After round 2 done, click "项目完成 · 查看导出"
14. Click "下载项目 zip"
15. In Finder, open the downloaded zip:
    - [ ] E01.txt through E10.txt all present
    - [ ] Bible.md present
    - [ ] Open one .txt — format is [SCENE]/[ACTION]/[SPEAKER]

## Pass criteria

- Pipeline completes without crash
- At least 60% of 10 episodes score ≥ 9.0
- Zip downloads and contents look right
- `bibles.prev_round_summary_json` populated after round 1 (cross-round memory verified)

## Known cost expectation

- ~50-100k tokens per 10-episode run
- Opus 4.7 is the heaviest (one call per episode = 10 calls)
- Sonnet for M2 (~5 calls) + M5 (10 calls)
- Haiku for M4 review (30 calls = 3 agents × 10 eps) + summaries (12 calls)
