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

Optional browser workspace session smoke:

```bash
curl -i \
  -H "Content-Type: application/json" \
  -d '{"email":"session-smoke@example.com","tenantSlug":"session-smoke","tenantName":"Session Smoke"}' \
  "http://localhost:3000/api/platform/session"
curl -b "novel_user_email=session-smoke%40example.com; novel_tenant_slug=session-smoke; novel_tenant_name=Session%20Smoke" \
  "http://localhost:3000/api/platform/session"
```

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

MEMBER=$(
  curl -sS \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"email":"member-smoke@example.com","role":"member"}' \
    "http://localhost:3000/api/platform/members" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)
curl \
  -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}' \
  "http://localhost:3000/api/platform/members/$MEMBER"
curl \
  -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/platform/members/$MEMBER"
```

## Steps

1. Open http://localhost:3000
2. Click "质量门禁", then "运行样本质检".
3. Verify the quality page shows a queued/running/completed job card.
4. Verify the quality page shows passed/failed counts and sample round rows.
5. Return to the project list.
6. Click "平台设置".
7. Change the workspace session to a smoke email and slug.
8. Verify the page refreshes into that workspace and the header shows the new email.
9. Create an API key and verify the plaintext token appears once.
10. Add a team member, switch their role, then remove them.
11. Verify the plan card shows the current plan, billable units, and estimated total.
12. Verify the credit wallet shows the current balance, packages, ledger, and invoices.
13. Click "模拟支付" on a credit package and verify the balance increases.
14. Return to the project list.
15. Click "新建项目"
16. Fill: name "祖母穿越女 smoke", target episode count 6
17. Upload the fixture txt
18. Submit. The app should navigate directly to `/rounds/1`.
19. Round progress page polls every 3s while the Engine generates artifacts.
20. Verify the round page shows a generation job card with queued/running/completed progress.
21. After round 1 done, verify:
   - [ ] Episode cards appear for the Engine-selected range
   - [ ] Each has a numeric score (0-10)
   - [ ] Script preview uses the short-drama rendered format
   - [ ] Context card shows current episode and open hooks
22. Click "系统 Bible":
   - [ ] Story Bible JSON is present
   - [ ] Context mapping is read-only
   - [ ] There is no user confirmation gate
23. Return to the round page.
24. Click "生成视频 brief", choose a localization profile, then click "生成本地化包", then "交付预检".
25. Verify delivery preflight shows ready or explicit warnings.
26. Click "开始第 2 轮".
27. Verify `bibles.prev_round_summary_json` updates after the next round.
28. Click "下载交付包".
29. In Finder, open the downloaded zip:
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
- `/api/platform/session` can set and clear the current browser workspace
- Home, `/platform`, project round, Bible, and completion pages all respect the browser workspace cookie
- `/api/platform/members` lists members and lets owner/admin add members
- `/api/platform/members/:id` can update roles and remove non-current members while keeping one owner
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
