# Novel-to-Drama 设计 spec

版本 v0 (MVP)
日期 2026-05-14
作者 杯子（王紫鹏）
状态 草案 待用户复核

---

## 1 背景与目标

### 1.1 问题陈述

对白短剧的最终生产质量瓶颈在「输入文本」。团队拿到的小说和脚本素材在体裁形态、剧本质量、频道题材、体量完整度四个维度上都严重参差不齐。直接进入下游生产链后产出参差不齐，靠下游 prompt 模板和自动化能力补不回来。

### 1.2 目标

做一个工具，把参差不齐的小说原料自动改编成符合标准格式、可直接交付下游生产的对白短剧脚本。

### 1.3 非目标

- 不替代下游短剧生产工具（视频生成 / 镜头执行 / TTS）
- 不做面向 C 端的 SaaS（v0 仅为内部团队工具）
- 不做爆款选题判断或热榜推荐（这是上游工作）
- 不做视频生成（这是下游职责）

---

## 2 用户与场景

### 2.1 目标用户

短剧团队（编剧 / 运营 / 制作）。v0 默认使用者为作者本人和同事。

### 2.2 核心场景

**A 路（v0 范围）** 国内小说 → 国内对白短剧
团队成员拿到一本网文小说 → 上传工具 → 系统出 Bible 和分轮规划 → 审一下 Bible → 系统按轮次 5 集/批跑 → 审完一轮决定下一轮 → 跑完 N 轮导出 txt → 灌入下游生产平台。

**B 路（v0 不实现，留架构位）** 国内短剧 → 海外短剧
轻本地化：翻译 + 人名映射 + 文化梗映射，结构不动。

---

## 3 范围

### 3.1 v0 In scope

- 单一 pipeline A（小说改对白短剧）
- 单用户，无登录或最简单 basic auth
- 单进程 worker，单集顺序跑
- 5 集/轮固定，多轮跑，跨轮上下文衔接
- 6 模块：归一化 / 诊断+Bible / 轮次改编 / 自查 / 格式化 / 导出
- 导出为 txt（每集一个文件 + 项目维度 zip）
- 用户在 Bible 阶段可编辑，轮次中可重跑某集（上限 2 次）
- 本机 SQLite 持久化

### 3.2 v0 Out of scope（写下来防止 scope creep）

- B 路 prompt 实现（只留 `pipeline_type` 字段和路由空架子）
- 多用户、权限、协作、评论
- 实时通知、webhook、外部 API 调用
- 中途取消任务
- 加密 / 云存储 / 多副本
- 5 集/轮以外的粒度配置
- 重跑上限以外的可配置项
- 多剧种（仅对白短剧）
- 自动接下游生产平台 API

### 3.3 后续演进（已识别但不做）

- v1 增加 B 路 prompt（翻译 + 本地化映射表）
- v1 增加多剧种模板（古言 / 现代甜宠 / 暗托）
- v2 接下游 Planner JSON schema 一键灌入
- v3 接下游 API 直调

---

## 4 架构概览

```
[Web UI 上传/管理项目]
        ↓
M1 输入归一化   ← txt/docx → 统一文本 + 元数据；过滤章标/水印；长度/完整度判断；频道粗识别
        ↓
M2 诊断+Bible 生成   ← 6 大资产、人物小传、情绪曲线、轮次规划（每轮 5 集）；输出可编辑 Bible
        ↓
[用户确认页：可改 Bible]
        ↓
M3 轮次改编 worker（5 集/轮，顺序跑）   ← 对白剧改编 prompt + 5 守 5 改；跨集传「前集摘要」；跨轮传「上轮摘要」
        ↓
M4 质量自查   ← 评审套路 + 9.0 阈值；不达标打红标，不自动重跑
        ↓
M5 原子 shot 格式化   ← 套已落地的格式转换 v5，转 [SCENE]/[ACTION]/[SPEAKER]
        ↓
M6 导出 txt   ← 单集 txt + 项目 zip
        ↓
[本轮 5 集完成 → 用户审阅页 → 决定下一轮 / 调 Bible / 重跑某集]
```

### 4.1 模块与现有资产映射

- M1 全新模块
- M2 复用 DJ_Project pipeline 的 stage1+2+3（频道+人物小传+结构）
- M3 复用现有对白剧改编 prompt 资产 + 5 守 5 改方法论
- M4 复用评测迭代法（3 agent 并行打分 + 9.0 阈值）
- M5 复用已落地的格式转换 v5（`~/Desktop/脚本格式转换引擎.txt`）
- M6 全新模块，Node.js 直接写文件

---

## 5 模块详解

### 5.1 M1 输入归一化

输入：用户上传的 txt 或 docx
输出：`projects.novel_text`（统一纯文本）+ `projects.meta_json`（长度/完整度/频道粗判）

规则部分（Node.js 纯代码）
- 文件格式识别（按扩展名 + magic bytes）
- docx 用 mammoth 或 docx 库转纯文本
- 字符数统计、行数统计、章节数提取（正则匹配「第\\d+章」）
- 编码统一为 UTF-8

LLM 部分（Sonnet 4.6 单次调用）
- 频道粗判（男频 / 女频 / 不确定）
- 完整度判断（完结 / 连载 / 大纲碎片）
- 体裁判断（网文 / 已改编剧本 / 大纲）
- 异常标记（含大量广告位、章节缺失等）

失败处理 LLM 不可用时回落只输出规则部分结果，频道标记为「待 M2 判断」。

### 5.2 M2 诊断 + Bible 生成

输入 `projects.novel_text` + M1 元数据
输出 `bibles` 表的所有字段

子任务（一次串行的 LLM 调用链，全用 Sonnet 4.6）
1. 频道确认（基于 M1 粗判，给最终结论）
2. 6 大资产抽取：主角动机 / 标志性场面 / 金句 / 情绪曲线 / 人物关系 / 故事前提
3. 人物小传（主角 + 主要配角，每人 8 字段，沿用 DJ_Project SOP）
4. 情绪曲线规划（按集数粒度，每集情绪标签）
5. 轮次切分：根据小说体量和目标集数算 N 轮 × 5 集 = N×5 集，输出每集的「主线事件 + 钩子方向」

输出 Bible 字段
- `channel`（男 / 女）
- `six_assets_json`
- `characters_md`（Markdown 富文本，可编辑）
- `episode_plan_md`（Markdown 富文本，可编辑，含轮次切分）
- `prev_round_summary_json`（初始空，每轮跑完后填）

用户编辑入口
- Web 上 Bible 页 = 三个 Markdown 编辑器（characters / episode_plan / 自由备注）
- 编辑 + 保存即生效，无校验
- 提供「重新生成此节」按钮（调 M2 子任务）

### 5.3 M3 轮次改编 worker

触发：用户在审阅页点「开始下一轮」
范围：每次跑 5 集，顺序跑（不并发）

单集流程
```
对每集 i：
  1. 构造 prompt = Bible + 上轮摘要 + 本轮前 i-1 集摘要 + 本集 episode_plan
  2. 调 Opus 4.7 输出对白剧本草稿（Markdown 半结构化）
  3. 调用 M4 自查
  4. 调用 M5 格式化（转 [SCENE]/[ACTION]/[SPEAKER]）
  5. 调用 Haiku 4.5 抽取本集摘要（人设状态变化 / 未解伏笔 / 钩子方向，目标 ~200 字 JSON）
  6. 入库 episodes
跑完 5 集后：
  7. 调 Haiku 抽取「本轮摘要」（聚合 5 集摘要），存 rounds.summary_json
  8. 把 rounds.summary_json 回写到 bibles.prev_round_summary_json 供下一轮用
```

prompt 模板路径
- 主 prompt 引用现有对白剧改编 prompt 资产（v8 版本作为起点）
- 跨集记忆字段固定为 `<前情概要>` block，prompt 内有明确位置

并发策略 v0 不并发。一个 project 同时只跑一轮。

### 5.4 M4 自查

输入 M3 单集草稿 + Bible
输出 `episodes.score` (0-10) + `episodes.review_json`（多维打分细节）

实现
- 调 3 个 Haiku agent 并行打分（编剧视角 / 观众视角 / 反派逻辑视角）
- 三分平均作为 score
- score < 9.0 标 `episodes.status=red`，但不自动重跑（避免烧 token）
- 用户在审阅页看到红标 → 手动点「重跑」最多 2 次

### 5.5 M5 原子 shot 格式化

输入 M3+M4 通过的草稿
输出 符合原子 shot 格式的 txt（[SCENE] / [ACTION] / [SPEAKER]）

实现
- 复用 `~/Desktop/脚本格式转换引擎.txt` v5 prompt
- 调 Sonnet 4.6 一次性转换
- 解析失败重试 1 次，仍失败则保留 M3 原文并标红

### 5.6 M6 导出

入口
- 单集 txt 下载（在 Web 单集页点按钮）
- 整项目 zip（包含 N 集 txt + Bible.md + 元数据 README.md）

实现
- Node.js 用 `fs/promises` 写文件 + `archiver` 打 zip
- 文件名 `E01.txt` `E02.txt` `...` `Bible.md` `README.md`

---

## 6 数据流 + 用户交互流

### 6.1 阶段 1 立项 + 诊断（< 5 分钟）

```
[Web 首页] 点「新建项目」
   ↓
[新建项目页] 填项目名 + 上传 txt/docx + 选目标集数（可空让系统建议）
   ↓ 提交
后台：M1 归一化（10s）→ M2 生成 Bible（2-3 分钟）
   ↓
[Bible 页] 三个 Markdown 编辑器 + 「开始第一轮」按钮
   ↓ 用户改完点开始
跳转到阶段 2
```

### 6.2 阶段 2 轮次循环（每轮 10-25 分钟）

```
[轮次进度页] 进度条 + 5 集卡片（每集出炉立刻可预览）
   ↓ 5 集跑完
[轮次审阅页] 5 集列表：每集显示 score 和红/绿标
   用户操作选项：
     - 通过 → 点「开始下一轮」
     - 重跑红标某集（上限 2）
     - 改 Bible → 已跑集打「Bible 已变更」提示但不自动重跑
   ↓ 通过
回到 [轮次进度页] 跑下一轮
   ↓ 所有规划集跑完
[项目完成页] 显示总体 score 分布 + 下载 zip 按钮
```

### 6.3 跨集 / 跨轮记忆

- **跨集** 本轮内每集跑完抽摘要（Haiku，~200 字 JSON），下一集 prompt 自动注入
- **跨轮** 本轮 5 集跑完后聚合成「轮次摘要」，写回 `bibles.prev_round_summary_json`，下一轮第一集自动注入
- 用户改 Bible 不影响已跑集的摘要数据，只影响后续集

### 6.4 异常流

- LLM 单次调用失败 SDK 重试 + wrapper 重试 2 次
- 单集跑挂 `episodes.status=failed`，不阻塞同轮其他集
- 整轮跑挂 `rounds.status=failed`，用户可点「重跑本轮」
- 用户中途关浏览器 worker 不停（同进程跑完为止），用户回来刷新 Web 看进度
- M5 解析失败 保留 M3 原文 + 红标

---

## 7 数据模型

```
projects
  id (uuid)
  name (text)
  pipeline_type (enum: A | B)  -- v0 只用 A
  novel_text (text)
  meta_json (jsonb)  -- M1 输出
  target_language (text, nullable)  -- B 路才用
  target_episode_count (int)
  status (enum: draft | bible_ready | running | done | failed)
  created_at (timestamp)
  updated_at (timestamp)

bibles
  id (uuid)
  project_id (fk projects)
  channel (enum: male | female)
  six_assets_json (jsonb)
  characters_md (text)
  episode_plan_md (text)
  prev_round_summary_json (jsonb)  -- 跨轮记忆，跑完一轮回写
  name_mapping_json (jsonb, nullable)  -- B 路预留
  culture_mapping_json (jsonb, nullable)  -- B 路预留
  updated_at (timestamp)

rounds
  id (uuid)
  project_id (fk projects)
  round_num (int)  -- 1, 2, 3...
  ep_range (text)  -- "E01-E05"
  summary_json (jsonb)  -- 本轮聚合摘要
  status (enum: pending | running | done | failed)
  created_at (timestamp)

episodes
  id (uuid)
  project_id (fk projects)
  round_id (fk rounds)
  ep_num (int)
  draft_md (text)  -- M3 输出
  script_txt (text)  -- M5 输出
  score (float)  -- M4 输出
  review_json (jsonb)  -- M4 多维打分
  ep_summary_json (jsonb)  -- 跨集摘要，给同轮下一集用
  retry_count (int, default 0)
  status (enum: pending | running | green | red | failed)
  updated_at (timestamp)
```

---

## 8 技术栈

> 本文是早期 Web v0 设计草案，生成链路部分已经被当前实现替换。当前生产生成链路以
> `README.md` 和 `src/novel_drama_engine/` 为准：Web job worker 只调用 Python Engine。

- 前端 Next.js App Router + Tailwind
- 后端 Next.js API Routes + job worker
- DB SQLite + Drizzle ORM（本地 db.sqlite 文件）
- LLM OpenAI-compatible provider，由 Python Engine 统一调用
- 任务执行使用 jobs 表和独立 worker 状态机
- 文件存储 本地 disk（`./storage/projects/<project_id>/`）
- 部署选项
  - 本机跑：`npm run dev`，团队通过你机器 IP 访问
  - 内网 server：Mac mini 或公司开发机
  - Vercel + Turso（远程 SQLite）

为什么不上 Postgres / Redis / 队列 v0 单用户串行跑，复杂度负担 > 收益。

---

## 9 错误处理

### 9.1 LLM 调用层

- SDK 自带重试不动
- wrapper 再加 2 次指数退避重试
- 仍失败抛 `LLMCallError`，上层模块决定怎么处理

### 9.2 模块层

- M1 规则部分必须成功；LLM 部分失败 → 元数据缺失但流程继续
- M2 子任务任一失败 → 标 project status=failed，整体重跑
- M3 单集失败 → episode status=failed，跳过继续跑同轮其他集
- M4 失败 → score=null，episode 默认绿标但带 warning
- M5 失败 → 保留 M3 原文 + 红标
- M6 失败 → 弹错给用户，让用户重试导出

### 9.3 用户层

- 红标重跑上限 2 次（写死）
- 整轮失败提供「重跑本轮」按钮
- 整项目失败提供「克隆为新项目」按钮（保留 novel + Bible，episodes 全清空）

---

## 10 测试策略

### 10.1 v0 不写单元测试

理由 vibecode 阶段代码变动快，写 unit test 维护成本 > 收益。

### 10.2 E2E 验证

准备 3 部 fixture 小说（从 DJ_Project/木木给的脚本 挑）
- 男频 1 部
- 女频 1 部
- 古言 1 部

验证标准
- 跑完一个完整项目（至少 2 轮 = 10 集）不报错
- 抽样 3 集人工对比 DJ_Project pipeline v3 跑过的同小说脚本
- 抽样 3 集 score ≥ 9.0
- 整项目 zip 能下载，解压后文件名规整

### 10.3 性能基线

- 单集 M3 跑通时间 < 3 分钟
- 单轮 5 集端到端 < 25 分钟
- M2 Bible 生成 < 3 分钟

---

## 11 验收清单

v0 可以交付的判定标准
- [ ] Web 能跑通：上传 → Bible → 跑 2 轮 → 导出 zip
- [ ] 3 部 fixture 小说全跑通
- [ ] 红标重跑机制工作
- [ ] 跨轮上下文衔接验证：第 2 轮第 1 集 prompt 里能看到第 1 轮摘要
- [ ] 项目 zip 解压后所有 txt 符合 [SCENE]/[ACTION]/[SPEAKER] 原子 shot 格式
- [ ] 团队 2-3 个同事拿真实小说试用，反馈优于现有直接生产流程

---

## 12 已知风险与缓解

1. **LLM 跨集记忆失真** 摘要可能丢人设细节
缓解 v0 用 Haiku 抽 ~200 字摘要 + Bible 兜底；如果 e2e 测出失真则改成「摘要 + 上集原文」混合
2. **Opus 4.7 改编质量未必稳定打 9.0** 现有对白剧 prompt 在某些频道可能掉分
缓解 v0 接受 80% 集子达 9.0，剩下 20% 红标人工重跑；如果命中率 < 50% 则要回到 prompt 工程层迭代
3. **Vibecode 出来的代码可能没架构** Next.js 全堆 API routes 后期难维护
缓解 v0 不管，先 ship；v1 起做 module 拆分
4. **B 路接口预留可能浪费** 留位置但永远不实现
缓解 v0 字段加上但代码路由空着，写 100 行内的空架子，删除成本低

---

## 13 决策日志（本次 brainstorming 关键拍板）

- 目标用户：短剧团队（编剧 / 运营 / 制作）；v0 默认作者本人和同事
- 输出剧种：对白短剧（v0 唯一覆盖剧种），未来可扩 1-2 剧种
- 功能边界：全链小说→多集脚本（vs 单集改编 / 仅格式化 / 模块自选）
- 输入痛点：四维度全参差（体裁、质量、频道、体量）
- 产品形态：独立 Web + vibecode（vs 团队后台集成 / Skill 化）
- B 路本质：轻本地化，MVP 不重构（vs 翻译 / 重构 / 混合）
- MVP 起跑：先 A，B 留架构位（vs 仅 B / A+B 同上 / A 不留 B）
- 产出单位：轮次制 5 集/轮，多轮跑（vs 一次一集 / 全量 / 双模式）
- 交付接口：txt 导出，手动接入下游生产平台（vs docx / Planner JSON / API）
- 定位：去名不去身份——产品独立、概念通用，默认使用者仍是作者和同事

---

## 附录 A 相关已有资产路径

- DJ_Project pipeline `/Users/wangzipeng/Documents/DJ_Project/pipeline/run.sh`
- DJ_Project SOP `/Users/wangzipeng/Documents/DJ_Project/00_改编SOP总纲.md`
- fixture 小说 `/Users/wangzipeng/Documents/DJ_Project/木木给的脚本/`
- 脚本格式转换 v5 `~/Desktop/脚本格式转换引擎.txt`
- 现有对白剧改编 prompt v8（位于作者本地 prompt 库 / skill 内）
