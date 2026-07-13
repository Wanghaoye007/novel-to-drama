import { accessSync, constants, mkdirSync } from "fs";
import { dirname, resolve } from "path";

export type DeploymentReadinessCheck = {
  key: string;
  status: "pass" | "warn" | "fail";
  message: string;
};

export type DeploymentReadiness = {
  mode: "local" | "online";
  status: "ready" | "warning" | "blocked";
  checks: DeploymentReadinessCheck[];
};

export function resolveDatabasePath(): string {
  return process.env.NOVEL_DRAMA_DB_PATH?.trim() || "db.sqlite";
}

export function ensureDatabaseDirectory(dbPath = resolveDatabasePath()): void {
  mkdirSync(dirname(resolve(dbPath)), { recursive: true });
}

function canWriteDatabaseDirectory(dbPath = resolveDatabasePath()): boolean {
  try {
    ensureDatabaseDirectory(dbPath);
    accessSync(dirname(resolve(dbPath)), constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

function check(
  key: string,
  status: DeploymentReadinessCheck["status"],
  message: string
): DeploymentReadinessCheck {
  return { key, status, message };
}

export function deploymentReadiness(): DeploymentReadiness {
  const onlineMode =
    process.env.NOVEL_DRAMA_ONLINE_MODE === "1" ||
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET === "production";
  const mockMode = process.env.NOVEL_DRAMA_WEB_MOCK === "1";
  const realModelReady = Boolean(process.env.OPENAI_API_KEY && process.env.OPENAI_MODEL);
  const browserAccessProtected = Boolean(process.env.NOVEL_DRAMA_ACCESS_TOKEN);
  const externalApiProtected = process.env.NOVEL_DRAMA_REQUIRE_API_KEY === "1";
  const dbPath = resolveDatabasePath();
  const checks: DeploymentReadinessCheck[] = [
    check(
      "llm",
      mockMode ? (onlineMode ? "fail" : "warn") : realModelReady ? "pass" : "fail",
      mockMode
        ? "当前是 mock 模式，只适合演示页面流程。"
        : realModelReady
          ? "真实模型 key 与模型名已配置。"
          : "真实模型需要 OPENAI_API_KEY 和 OPENAI_MODEL。"
    ),
    check(
      "database",
      canWriteDatabaseDirectory(dbPath)
        ? process.env.NOVEL_DRAMA_DB_PATH || !onlineMode
          ? "pass"
          : "warn"
        : "fail",
      process.env.NOVEL_DRAMA_DB_PATH
        ? `数据库路径已配置：${dbPath}`
        : onlineMode
          ? "线上模式建议显式配置 NOVEL_DRAMA_DB_PATH 到持久盘。"
          : "使用默认本地 db.sqlite。"
    ),
    check(
      "access_token",
      process.env.NOVEL_DRAMA_ACCESS_TOKEN
        ? "pass"
        : onlineMode
          ? "fail"
          : "warn",
      process.env.NOVEL_DRAMA_ACCESS_TOKEN
        ? "浏览器访问令牌已配置。"
        : "公网部署前需要 NOVEL_DRAMA_ACCESS_TOKEN，或确认部署在私有网络后。"
    ),
    check(
      "api_auth",
      browserAccessProtected || externalApiProtected
        ? "pass"
        : onlineMode
          ? "fail"
          : "warn",
      browserAccessProtected && externalApiProtected
        ? "浏览器访问令牌与 API Key 保护均已开启。"
        : browserAccessProtected
          ? "浏览器访问令牌已保护页面和 API；外部程序 API Key 可按需开启。"
          : externalApiProtected
            ? "API Key 保护已开启；浏览器入口建议另配 NOVEL_DRAMA_ACCESS_TOKEN。"
            : "公网部署前需要 NOVEL_DRAMA_ACCESS_TOKEN、API Key 保护，或确认部署在私有网络后。"
    ),
    check(
      "credits",
      process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1" ? "pass" : "warn",
      process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1"
        ? "点数扣费门禁已开启。"
        : "点数扣费门禁未开启，上线早期可内测，开放给外部用户前应开启。"
    ),
  ];
  const hasFailure = checks.some((item) => item.status === "fail");
  const hasWarning = checks.some((item) => item.status === "warn");
  return {
    mode: onlineMode ? "online" : "local",
    status: hasFailure ? "blocked" : hasWarning ? "warning" : "ready",
    checks,
  };
}
