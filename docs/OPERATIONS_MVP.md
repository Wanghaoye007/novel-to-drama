# 运营体验环境

这个环境用于让运营同学直接打开浏览器体验小说改编短剧脚本流程，不需要接触命令行。

## 访问地址

- 同一台 Mac: http://localhost:3000
- 同一局域网: http://MacBook-Pro.local:3000
- 局域网备用 IP: http://10.10.2.106:3000
- 健康检查: http://MacBook-Pro.local:3000/api/health

如果 `MacBook-Pro.local` 在某台电脑上打不开，优先使用备用 IP。备用 IP 会随网络变化，`.local` 地址通常更稳定。

## 当前体验模式

- 默认使用 mock engine，适合快速体验页面流程，不消耗模型额度。
- Story Bible 由系统自动生成，不需要运营确认。
- 创建项目后自动启动第 1 轮，后续轮次根据原文和上一轮 context 继续。
- 平台里的点数、账单、API Key、成员管理是模板能力，首轮体验不用操作。

## 运营体验路径

1. 打开首页。
2. 点击新建项目。
3. 上传 txt/docx 小说，填写目标集数。
4. 等待第 1 轮完成。
5. 在轮次页查看脚本、质量分和 warning。
6. 继续下一轮，或进入完成页导出视频 brief、本地化包、交付预检和 zip。

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

## 切换真实模型

当前常驻环境默认是 mock。要切换真实模型，需要在 LaunchAgent 或 `.env.local` 里配置：

```bash
NOVEL_DRAMA_WEB_MOCK=0
OPENAI_API_KEY=...
```

真实模型模式建议等运营确认页面流程后再打开，避免早期调试消耗额度。

## 公网稳定 URL

当前这个版本解决的是“运营不用命令行，在同一网络打开稳定地址”。如果要外部人员访问公网 URL，需要再接一个托管平台：

- Render/Fly: 适合这个项目当前的 SQLite + 本地文件 + Node/Python 组合。
- Vercel: 页面托管方便，但当前后台 worker、SQLite 和文件存储需要改成托管 DB/对象存储。
- Cloudflare Tunnel/ngrok 固定域名: 最快给公网访问，但需要账号和固定域名配置。
