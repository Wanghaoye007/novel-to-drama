# 运营体验环境

这个环境用于让运营同学直接打开浏览器体验小说改编短剧脚本流程，不需要接触命令行。

## 访问地址

- 同一台 Mac: http://localhost:3000
- 同一局域网: http://MacBook-Pro.local:3000
- 局域网备用 IP: http://192.168.0.108:3000
- 健康检查: http://MacBook-Pro.local:3000/api/health

如果 `MacBook-Pro.local` 在某台电脑上打不开，优先使用备用 IP。备用 IP 会随网络变化，`.local` 地址通常更稳定。

## 当前体验模式

- 当前运营环境使用真实模型：OpenRouter `google/gemini-3.1-flash-lite`。
- 默认改编策略为「强剧情优先」：保留分集戏剧设计，跳过慢速 SOP 全剧结构规划。SOP 全链路作为慢速精修档保留给回归测试或小样本精修。
- 批量运行默认 5 集/轮，30 集项目会按 EP01-EP05、EP06-EP10 继续。
- Story Bible 由系统自动生成，不需要运营确认。
- 创建项目后自动启动第 1 轮，后续轮次根据原文和上一轮 context 继续。
- 后台会自动检查同轮跨集重复：如果多集只是换标题/换台词但场景骨架、动作链、对白句式或结尾钩子重复，会进入重写或人工复核。
- 平台里的点数、账单、API Key、成员管理是模板能力，首轮体验不用操作。

## 运营体验路径

1. 打开首页。
2. 点击新建项目。
3. 上传 txt/docx 小说，填写目标集数。
4. 等待第 1 轮完成。
5. 在轮次页查看脚本、质量分和 warning。
6. 继续下一轮，或进入完成页导出视频 brief、本地化包、交付预检和 zip。

## 项目控制

- 复制项目：在项目列表或轮次页点击「复制」，系统会复制小说原文、目标集数和项目配置，生成一个独立新项目，并自动启动第 1 轮。
- 暂停项目：点击「暂停项目」后，worker 不再领取该项目的新轮次任务。若当前 LLM 调用已经开始，会等当前 Engine 进程结束后停在下一轮边界，避免损坏中间产物。
- 继续项目：点击「继续项目」后，queued 任务会重新被 worker 领取；如果已开启批量运行，系统会继续补排下一轮。
- 批量运行：点击「批量运行」后，系统会在每轮完成后自动判断是否到达目标集数，未完成则自动排下一轮，不需要运营一轮一轮点。
- 按集可见：Engine 默认先生成连贯整轮首稿，再按集写入页面和做失败修复；整轮质量复检完成前状态显示为「生成中」，最终再更新为 green/red。

## 服务常驻方式

本机通过 macOS LaunchAgent 常驻运行：

- Label: `com.novel-to-drama.ops-web`
- 配置文件: `~/Library/LaunchAgents/com.novel-to-drama.ops-web.plist`
- 运行时目录: `~/.novel-to-drama-ops/app`
- 日志:
  - `~/.novel-to-drama-ops/app/logs/ops-web.out.log`
  - `~/.novel-to-drama-ops/app/logs/ops-web.err.log`

如果机器重启或用户重新登录，服务会自动启动。服务异常退出后也会自动拉起。
由于 macOS 对 `Documents` 目录有隐私限制，LaunchAgent 跑的是运行时副本。
源代码更新后，重新安装运营服务会同步最新代码到运行时目录。
Engine 命令统一使用 `python3 -m novel_drama_engine.cli` module 入口；`novel-drama`
只是 editable install 后的 console-script 简写。Web runner 默认使用 module 入口，
避免不同机器 PATH 不一致导致 worker 找不到命令。

## 模型配置

常驻环境的模型配置在本机私有文件
`~/.novel-to-drama-ops/secrets.env` 里配置，避免把 key 写入 git：

```bash
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_LLM_PROVIDER=openrouter
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=google/gemini-3.1-flash-lite
OPENAI_MAX_TOKENS=20000
OPENAI_TIMEOUT=300
NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS=240
NOVEL_DRAMA_GENERATION_VARIANT=drama_engine_first
NOVEL_DRAMA_DB_PATH=/Users/wangzipeng/.novel-to-drama-ops/app/db.sqlite
NOVEL_DRAMA_ACCESS_TOKEN=change-me
OPENAI_API_KEY=...
```

如果使用 Kimi/Moonshot API，配置 OpenAI-compatible endpoint：

```bash
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_LLM_PROVIDER=kimi
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-128k
OPENAI_MAX_TOKENS=20000
OPENAI_TIMEOUT=300
NOVEL_DRAMA_LLM_CALL_TIMEOUT_SECONDS=240
OPENAI_API_KEY=...
```

服务启动脚本会自动读取 `~/.novel-to-drama-ops/secrets.env`。

如需临时零成本演示，可把 `NOVEL_DRAMA_WEB_MOCK=1` 后重新安装运营服务。

## 上线就绪检查

访问 `/api/health` 可查看 `readiness`：

- `ready`: 可以上线。
- `warning`: 内测可用，但仍有上线前建议项。
- `blocked`: 不应公网开放。

也可以在部署机器上先跑一次静态检查：

```bash
npm run ops:online-readiness
```

这个命令会读取 `~/.novel-to-drama-ops/secrets.env`，强制按线上模式检查，并在 `readiness.status !== "ready"` 时返回失败。

公网或外部团队访问前建议配置：

```bash
NOVEL_DRAMA_ONLINE_MODE=1
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_REQUIRE_API_KEY=1
NOVEL_DRAMA_REQUIRE_CREDITS=1
NOVEL_DRAMA_DB_PATH=/persistent/novel-to-drama/db.sqlite
NOVEL_DRAMA_ACCESS_TOKEN=<shared-ops-access-token>
NOVEL_DRAMA_ACCESS_COOKIE_SECURE=1
```

如果只是给运营浏览器访问，`NOVEL_DRAMA_ACCESS_TOKEN` 已经会保护页面和 `/api/*`；如果后续开放外部程序调用，再开启 `NOVEL_DRAMA_REQUIRE_API_KEY=1`。

配置访问令牌后，首次打开：

```text
https://your-domain.example/?access_token=<shared-ops-access-token>
```

浏览器会写入 7 天 Cookie，之后无需在 URL 里继续带 token。

## 公网稳定 URL

当前这个版本解决的是“运营不用命令行，在同一网络打开稳定地址”。如果要外部人员访问公网 URL，需要再接一个托管平台：

- Render/Fly: 适合这个项目当前的 SQLite + 本地文件 + Node/Python 组合。
- Vercel: 页面托管方便，但当前后台 worker、SQLite 和文件存储需要改成托管 DB/对象存储。
- Cloudflare Tunnel/ngrok 固定域名: 最快给公网访问，但需要账号和固定域名配置。
