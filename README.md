# Novel-to-Drama

## 产品目标

Novel-to-Drama 是一个小说转竖屏短剧工具。当前唯一目标是：用户上传一份中文小说，系统基于原文稳定生成可读、可编辑、可检查、可导出的短剧剧本。

项目只有一套改编核心：`src/novel_drama_engine/` 下的 Python Engine。Next.js 只负责项目页面、异步任务、状态展示和导出，不承担另一套小说改写逻辑。

## 当前 MVP 能力

- 上传 `.txt` 或 `.docx` 小说，设置目标集数、首轮集数、模型和改编策略。
- 系统自动完成原文拆解、Story Bible、分集规划和首轮剧本生成。
- 按集展示生成结果、来源一致性和质量状态，质量问题不伪装成 Engine 故障。
- 支持单集 AI 优化，以及把人工修改作为后续剧情的连续性基准。
- 支持按轮继续生成；已生成或人工修改的集不会被下一轮覆盖。
- 导出 TXT、Word 和结构化 Engine 产物。
- 使用持久化异步 Worker；页面可查看排队、运行、成功和失败状态。

平台账户、成员、API Key、额度、积分和模拟支付代码仍保留用于内部环境，但已冻结，不属于当前 MVP 主线。详见 [docs/platform.md](docs/platform.md)。

## 5 分钟启动

要求：Node.js 24、Python 3.11+、SQLite。

```bash
cp .env.local.example .env.local
npm install
python3 -m pip install -e ".[dev]"
npm run db:migrate
```

零成本本地体验：

```bash
NOVEL_DRAMA_WEB_MOCK=1 npm run dev
```

打开 [http://localhost:3000](http://localhost:3000)，新建项目并上传小说。真实模型运行需要在 `.env.local` 配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`，并设置 `NOVEL_DRAMA_WEB_MOCK=0`。

开发时 Web 会自动认领一个队列任务。需要模拟生产的 Web/Worker 分离时：

```bash
NOVEL_DRAMA_AUTO_WORKER=0 npm run dev
npm run jobs:watch
```

提交前统一执行：

```bash
npm run check
```

## 核心用户流程

1. 新建项目并上传小说。
2. 系统异步解析原文，建立系统持有的 Story Bible。
3. Engine 将目标集映射到对应原文片段，生成分集计划与连续剧本。
4. 页面按集显示结果；来源证据、连续性和戏剧质量作为审计信号。
5. 运营可优化单集或提交人工改稿，后续集从最新有效剧情继续。
6. 通过后导出剧本；需要更多集时再启动下一轮。

稳定主链路：

```text
小说原文
  -> SourceSpan / Episode Packet
  -> Story Bible / 当前剧情状态
  -> 分集计划
  -> Python Engine 剧本生成
  -> 来源与质量检查
  -> 人工编辑或受限修复
  -> 导出
```

Engine CLI、产物结构、缓存和 A/B 方法见 [docs/engine.md](docs/engine.md)。运营部署见 [docs/OPERATIONS_MVP.md](docs/OPERATIONS_MVP.md)。

## 项目目录

```text
src/
├── app/                    Next.js 页面与 API
├── components/             Web UI 组件
├── db/                     SQLite / Drizzle 数据模型
├── lib/                    Web 服务、任务和 Engine 适配层
├── novel_drama_engine/     唯一小说改编引擎（Python）
└── scripts/                Worker 入口
tests/                      Python 与 TypeScript 回归测试
docs/                       Engine、平台和运维说明
drizzle/                    数据库迁移
examples/                   示例小说、样本和方法论卡
ops/                        内部运营 LaunchAgent
archive/                    已退出主线的历史实现说明
```

旧 Anthropic/M1-M6 TypeScript 生成流程已经退出正式代码；历史边界见 [archive/legacy-typescript-engine/README.md](archive/legacy-typescript-engine/README.md)。

## 当前未完成事项

- 真实模型写作质量仍需用固定小说样本持续与“单次模型直改”做人工 A/B，mock 通过只证明链路可运行。
- 前端已有 TypeScript 行为测试和生产构建，但尚未建立完整的 Playwright 浏览器 E2E。
- 当前运营部署是内部单机版本；公网 SaaS 仍缺正式 IdP、域名/TLS、托管数据库与对象存储、真实支付和异地灾备。
- Platform、Billing、Credits、Payment、本地化、视频 Brief 和批量生产暂不继续扩建，除非它们阻塞小说改编主流程。
- 产品北极星是原文忠实且连续的可用剧本；新功能不能以牺牲这一指标为代价。
