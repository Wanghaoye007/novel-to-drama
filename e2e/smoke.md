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
novel-drama evaluate-samples --mock --samples examples/quality_samples.json --projects-dir /tmp/novel-drama-quality-smoke --rounds 2
```

Optional worker split:

```bash
NOVEL_DRAMA_WEB_MOCK=1 NOVEL_DRAMA_AUTO_WORKER=0 npm run dev
npm run jobs:work
```

Optional tenant headers for API smoke:

```bash
curl \
  -H "x-novel-user-email: smoke@example.com" \
  -H "x-novel-tenant: smoke-studio" \
  "http://localhost:3000/api/projects"
curl \
  -H "x-novel-user-email: other@example.com" \
  -H "x-novel-tenant: other-studio" \
  "http://localhost:3000/api/projects"
```

The two responses should show separate project lists.

Optional API key smoke:

```bash
TOKEN=$(
  curl -sS \
    -H "x-novel-user-email: smoke@example.com" \
    -H "x-novel-tenant: smoke-studio" \
    -H "Content-Type: application/json" \
    -d '{"name":"Smoke key"}' \
    "http://localhost:3000/api/platform/api-keys" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])'
)
curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/api/projects"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/api/platform/usage"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/api/platform/billing"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/api/platform/credits"

SESSION=$(
  curl -sS \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"packageSlug":"credits_100","provider":"mock"}' \
    "http://localhost:3000/api/platform/checkout" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)
curl \
  -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/platform/checkout/$SESSION/complete"
```

## Steps

1. Open http://localhost:3000
2. Click "质量门禁", then "运行样本质检".
3. Verify the quality page shows a queued/running/completed job card.
4. Verify the quality page shows passed/failed counts and sample round rows.
5. Return to the project list.
6. Click "平台设置".
7. Create an API key and verify the plaintext token appears once.
8. Verify the plan card shows the current plan, billable units, and estimated total.
9. Verify the credit wallet shows the current balance, packages, ledger, and invoices.
10. Click "模拟支付" on a credit package and verify the balance increases.
11. Return to the project list.
12. Click "新建项目"
13. Fill: name "祖母穿越女 smoke", target episode count 6
14. Upload the fixture txt
15. Submit. The app should navigate directly to `/rounds/1`.
16. Round progress page polls every 3s while the Engine generates artifacts.
17. Verify the round page shows a generation job card with queued/running/completed progress.
18. After round 1 done, verify:
   - [ ] Episode cards appear for the Engine-selected range
   - [ ] Each has a numeric score (0-10)
   - [ ] Script preview uses the short-drama rendered format
   - [ ] Context card shows current episode and open hooks
19. Click "系统 Bible":
   - [ ] Story Bible JSON is present
   - [ ] Context mapping is read-only
   - [ ] There is no user confirmation gate
20. Return to the round page.
21. Click "生成视频 brief", choose a localization profile, then click "生成本地化包", then "交付预检".
22. Verify delivery preflight shows ready or explicit warnings.
23. Click "开始第 2 轮".
24. Verify `bibles.prev_round_summary_json` updates after the next round.
25. Click "下载交付包".
26. In Finder, open the downloaded zip:
    - [ ] `delivery_manifest.json` is present
    - [ ] `round_result.json` is present
    - [ ] `rendered_scripts.md` is present
    - [ ] `video_brief.*` and `localization_*` are present if generated

## Pass criteria

- Pipeline completes without crash
- Web flow does not require Story Bible confirmation
- Round 2 starts from stored context automatically
- Quality gate runs from Web and surfaces sample-level warnings
- Round and quality-gate jobs expose progress, attempts, success/failure, and error text
- With `NOVEL_DRAMA_AUTO_WORKER=0`, `npm run jobs:work` can consume queued jobs
- `/api/projects`, `/api/jobs`, quality jobs, and project export APIs stay scoped to the current tenant context
- API keys can authenticate `/api/projects` and `/api/platform/usage`
- `/api/platform/billing` returns active plan, subscription period, billable units, and estimated total
- `/api/platform/credits` returns credit packages, balance, ledger entries, checkout sessions, and invoices
- mock checkout completion adds credits and writes a paid invoice plus top-up ledger entry
- billable usage writes credit debit entries and can be blocked with `NOVEL_DRAMA_REQUIRE_CREDITS=1`
- `/platform` shows API key status, current-month usage events, billing estimate, and credit wallet
- Delivery preflight and zip use Engine artifacts
- `bibles.prev_round_summary_json` is populated after round 1

## Known cost expectation

- Mock mode is free and deterministic.
- Real mode uses the OpenAI model configured by `OPENAI_MODEL`.
- Each round runs the Python Engine's six structured stages.
- Payment template mode uses mock checkout; `1 billable unit = 1 credit` before real provider fees or taxes.
