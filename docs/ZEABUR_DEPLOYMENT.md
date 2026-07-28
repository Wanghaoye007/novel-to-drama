# Zeabur 内部运营部署

这套部署用于让运营通过公网 HTTPS 地址使用当前 MVP。它仍是单实例内部生产，不是开放注册的多租户 SaaS。

## 运行结构

一个 Zeabur Git Service 同时运行：

- Next.js Web
- 持久化任务 Worker
- Python Novel Drama Engine
- SQLite 数据库与生成文件

Web 和 Worker 必须共享同一个 `/data` Volume。当前阶段不要拆成两个 Service，否则 SQLite 和生成文件无法安全共享。

## 1. 准备服务器

建议起步配置：

- 2 vCPU
- 4 GB RAM
- 40 GB 或更大的系统盘
- 优先选择运营访问稳定的亚洲区域

在 Zeabur 购买或接入服务器后，在这台服务器上创建 Project。

## 2. 创建 Git Service

1. 在 Project 中选择 `Add Service`。
2. 选择 GitHub 仓库与要发布的稳定分支。
3. Zeabur 会自动识别仓库根目录的 `Dockerfile`。
4. 不要配置自定义 Start Command，镜像默认入口已经负责迁移、门禁、Web、Worker 和备份。

每次目标分支有新提交时，Zeabur 会重新构建并发布镜像。

## 3. 挂载持久卷

发布前先为这个 Service 创建一个 Volume：

```text
Volume ID: novel-drama-data
Mount path: /data
```

容器会拒绝在没有 `/data` 挂载的情况下启动，防止 SQLite、上传小说和生成结果在重新发布后消失。

Volume 会保存：

```text
/data/db.sqlite
/data/storage/
/data/backups/
```

## 4. 配置变量

在 Service 的 Variables 页面使用 `deploy/zeabur.env.example` 作为模板批量填写。以下三项必须单独生成，不能复用：

```bash
openssl rand -hex 24  # NOVEL_DRAMA_ACCESS_TOKEN
openssl rand -hex 32  # NOVEL_DRAMA_SESSION_SECRET
```

必须填写：

```text
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL
NOVEL_DRAMA_ACCESS_TOKEN
NOVEL_DRAMA_SESSION_SECRET
```

保持以下线上值：

```text
NOVEL_DRAMA_WEB_MOCK=0
NOVEL_DRAMA_ONLINE_MODE=1
NOVEL_DRAMA_ACCESS_COOKIE_SECURE=1
NOVEL_DRAMA_ALLOW_SESSION_SWITCH=0
NOVEL_DRAMA_DB_PATH=/data/db.sqlite
NOVEL_DRAMA_STORAGE_ROOT=/data/storage
NOVEL_DRAMA_BACKUP_DIR=/data/backups
```

不要把任何 key 写入 Git、Dockerfile 或 Zeabur 构建日志。

## 5. 域名与健康检查

先绑定 Zeabur 提供的 HTTPS 域名。Service 必须使用 Zeabur 自动注入的 `PORT`，容器会监听 `0.0.0.0:$PORT`。

在 Service 设置中将 HTTP Health Check Path 配置为：

```text
/api/health
```

探活接口只返回 `ready`、`warning` 或 `blocked`，不会暴露数据库路径、模型名和 provider。详细门禁只在容器启动日志中的 `ops:online-readiness` 输出。

## 6. 首次启动

容器会按顺序执行：

1. 确认 `/data` 是真实挂载点。
2. 执行 Drizzle 数据库迁移。
3. 创建 SQLite 与生成文件一致性备份。
4. 运行线上门禁，任一关键项不满足就停止启动。
5. 启动 Next.js Web 和一个顺序任务 Worker。
6. 每 24 小时创建一次本地一致性备份。

首次打开：

```text
https://<your-domain>/?access_token=<NOVEL_DRAMA_ACCESS_TOKEN>
```

浏览器写入 Secure Cookie 后，应改用不带令牌的普通地址。不要把含令牌的地址发到群聊或截图中。

## 7. 发布验收

每次上线至少验证：

1. `/api/health` 返回 `ok: true` 和 `readiness: ready`。
2. 不带访问令牌打开首页会被拒绝。
3. 带令牌首次登录后，刷新页面仍可访问。
4. 上传一份短小说并生成 1 集，页面状态能从排队更新到完成。
5. 重启 Service 后，项目、剧本和任务历史仍存在。
6. `/data/backups` 中有最新 `.sqlite`、资产压缩包和校验文件。

## 8. 备份与回滚

`/data/backups` 与数据库位于同一 Volume，只能防止迁移或应用操作造成的数据损坏，不能防止整台服务器或 Volume 丢失。正式给运营使用前，应在 Zeabur 开启服务器/Volume 备份，或定期把备份同步到独立对象存储。

Zeabur 的代码回滚不会回滚数据库和 Volume。涉及数据库迁移时必须先保留备份，再回滚镜像，并按需要人工恢复数据库。

## 当前容量边界

- 单实例、单顺序 Worker，优先保证 SQLite 一致性和任务可恢复。
- 一个长剧生成任务运行时，导出和优化任务会排队等待。
- 当并发运营明显增加时，再迁移到 PostgreSQL、对象存储和独立队列；不要在 SQLite 上盲目增加 Worker 数。
