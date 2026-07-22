# Platform 与商业化底座

本文件记录仓库中已经存在的平台能力。它们用于内部运营兼容和未来验证，当前处于冻结状态，不属于小说转短剧 v0.1 的产品主线。

## 当前边界

- 内部生产环境：共享访问令牌 + 固定服务端运营身份。
- 本地开发：可显式允许浏览器切换 workspace。
- 公网多用户：尚未完成，必须接正式 IdP 或受信身份代理。
- 支付：只有内部数据模型与 mock provider，不代表真实收款能力。

任何平台改动都必须直接解除小说上传、剧本生成、编辑或导出的阻塞，否则暂不开发。

## Tenant、Owner 与成员

服务端上下文解析用户、tenant 和 membership。项目列表、详情、任务和导出必须同时校验 tenant 与 owner；列表响应不能返回完整小说文本。

本地默认值：

```bash
NOVEL_DRAMA_USER_EMAIL=local@novel-drama.local
NOVEL_DRAMA_TENANT_SLUG=local
NOVEL_DRAMA_TENANT_NAME="Local Workspace"
```

线上默认关闭任意身份切换：

```bash
NOVEL_DRAMA_ONLINE_MODE=1
NOVEL_DRAMA_ALLOW_SESSION_SWITCH=0
NOVEL_DRAMA_SESSION_SECRET=<independent-secret-at-least-32-characters>
```

成员接口保留在：

```text
GET/POST     /api/platform/members
PATCH/DELETE /api/platform/members/:id
```

角色包括 `owner`、`admin` 和 `member`，至少保留一个 owner。

## API Key 与访问保护

API Key 只保存 hash，明文仅在创建时返回一次：

```text
GET/POST /api/platform/api-keys
DELETE   /api/platform/api-keys/:id
```

机器调用可使用：

```bash
curl -H "Authorization: Bearer <ndk_token>" \
  http://localhost:3000/api/projects
```

`NOVEL_DRAMA_REQUIRE_API_KEY=1` 会要求 API 请求提供 key。浏览器内部运营入口由 `NOVEL_DRAMA_ACCESS_TOKEN` 保护，两者用途不同。

## Usage、Billing 与 Credits

以下接口仍存在，但当前只作为模板与内部审计：

```text
GET  /api/platform/usage
GET  /api/platform/billing
POST /api/platform/billing
GET  /api/platform/credits
POST /api/platform/checkout
POST /api/platform/checkout/:id/complete
POST /api/platform/payments/webhook
```

数据层包含 plan、subscription、usage event、credit ledger、checkout、invoice 和 webhook event。当前约定 `1 billable unit = 1 credit`，但内部运营环境默认 `NOVEL_DRAMA_REQUIRE_CREDITS=0`。

只有真实商业化验证启动后，才应开启点数门禁并接入实际套餐规则。

## Mock 支付与 Webhook

mock checkout 用于验证幂等、记账和状态流转，不得被描述为真实支付。Webhook 使用 HMAC-SHA256；生产环境缺少 secret、签名缺失或签名不匹配时必须拒绝。

```bash
PLATFORM_PAYMENT_WEBHOOK_SECRET=<shared-secret>
# 或 NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET
```

真实 Stripe、微信支付、支付宝或人工开票仍未接入。接入前需要独立安全审查、回调验签、退款/冲正和财务对账设计。

## 公网上线前置条件

- 域名、TLS 和 Secure Cookie。
- 正式 IdP 或受信身份代理，不能以浏览器填写的邮箱作为身份。
- 托管数据库、对象存储和异地备份。
- 真实支付 provider、签名密钥管理和财务流程。
- 审计日志、告警、速率限制和数据保留策略。

这些条件未满足前，只能称为内部生产工具，不能称为已开放的公网 SaaS。
