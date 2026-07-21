import { accessSync, constants, mkdirSync, readdirSync, statSync } from "fs";
import { dirname, isAbsolute, resolve } from "path";

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

export function isProductionLike(): boolean {
  return (
    process.env.NODE_ENV === "production" ||
    process.env.NOVEL_DRAMA_ONLINE_MODE === "1" ||
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET === "production"
  );
}

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

function hasStrongSecret(value: string | undefined, disallowed?: string | undefined): boolean {
  const normalized = value?.trim() ?? "";
  return normalized.length >= 32 && (!disallowed || normalized !== disallowed.trim());
}

function backupIsFresh(directory: string | undefined): boolean {
  if (!directory?.trim() || !isAbsolute(directory.trim())) return false;
  try {
    const newest = readdirSync(directory.trim())
      .filter((name) => /\.(?:sqlite|db|tar\.gz|tgz)$/i.test(name))
      .map((name) => statSync(resolve(directory.trim(), name)).mtimeMs)
      .reduce((latest, value) => Math.max(latest, value), 0);
    const maxAgeHours = Math.max(
      1,
      Number.parseInt(process.env.NOVEL_DRAMA_BACKUP_MAX_AGE_HOURS ?? "48", 10) || 48
    );
    return newest > 0 && Date.now() - newest <= maxAgeHours * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

export function deploymentReadiness(): DeploymentReadiness {
  const onlineMode = isProductionLike();
  const publicAudience = process.env.NOVEL_DRAMA_DEPLOYMENT_AUDIENCE === "public";
  const mockMode = process.env.NOVEL_DRAMA_WEB_MOCK === "1";
  const realModelReady = Boolean(process.env.OPENAI_API_KEY && process.env.OPENAI_MODEL);
  const browserAccessProtected = Boolean(process.env.NOVEL_DRAMA_ACCESS_TOKEN);
  const externalApiProtected = process.env.NOVEL_DRAMA_REQUIRE_API_KEY === "1";
  const dbPath = resolveDatabasePath();
  const accessToken = process.env.NOVEL_DRAMA_ACCESS_TOKEN;
  const sessionSecretReady = hasStrongSecret(
    process.env.NOVEL_DRAMA_SESSION_SECRET,
    accessToken
  );
  const trustedProxyReady =
    process.env.NOVEL_DRAMA_AUTH_MODE === "trusted_proxy" &&
    process.env.NOVEL_DRAMA_TRUST_IDENTITY_HEADERS === "1" &&
    hasStrongSecret(process.env.NOVEL_DRAMA_TRUST_PROXY_SECRET);
  const publicPersistenceReady =
    isAbsolute(dbPath) &&
    Boolean(
      process.env.NOVEL_DRAMA_STORAGE_ROOT &&
        isAbsolute(process.env.NOVEL_DRAMA_STORAGE_ROOT)
    );
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
      canWriteDatabaseDirectory(dbPath) && (!onlineMode || isAbsolute(dbPath))
        ? "pass"
        : "fail",
      process.env.NOVEL_DRAMA_DB_PATH && (!onlineMode || isAbsolute(dbPath))
        ? `数据库路径已配置：${dbPath}`
        : onlineMode
          ? "线上模式必须把 NOVEL_DRAMA_DB_PATH 配置为持久盘绝对路径。"
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
      "session_secret",
      sessionSecretReady ? "pass" : onlineMode ? "fail" : "warn",
      sessionSecretReady
        ? "独立的强 Session Secret 已配置。"
        : "线上模式必须配置至少 32 位、且不同于访问令牌的 NOVEL_DRAMA_SESSION_SECRET。"
    ),
    check(
      "secure_cookie",
      publicAudience && process.env.NOVEL_DRAMA_ACCESS_COOKIE_SECURE !== "1"
        ? "fail"
        : "pass",
      publicAudience
        ? "公网部署必须使用 HTTPS 并开启 Secure Cookie。"
        : "内部部署可通过受控网络访问；公网发布时必须开启 Secure Cookie。"
    ),
    check(
      "backup",
      backupIsFresh(process.env.NOVEL_DRAMA_BACKUP_DIR)
        ? "pass"
        : onlineMode
          ? "fail"
          : "warn",
      backupIsFresh(process.env.NOVEL_DRAMA_BACKUP_DIR)
        ? "数据库与资产备份在允许的新鲜度窗口内。"
        : "线上模式必须配置 NOVEL_DRAMA_BACKUP_DIR，并至少保留一份 48 小时内的备份。"
    ),
    check(
      "public_auth",
      publicAudience ? (trustedProxyReady ? "pass" : "fail") : "pass",
      publicAudience
        ? "公网多用户模式必须由受信身份代理注入用户身份，并配置独立代理密钥。"
        : "内部生产版使用共享访问令牌和固定运营身份。"
    ),
    check(
      "public_persistence",
      publicAudience ? (publicPersistenceReady ? "pass" : "fail") : "pass",
      publicAudience
        ? "公网模式必须显式配置持久数据库和 NOVEL_DRAMA_STORAGE_ROOT。"
        : "内部单机版使用本机持久数据库和生成资产。"
    ),
    check(
      "credits",
      process.env.NOVEL_DRAMA_REQUIRE_CREDITS === "1" || !publicAudience
        ? "pass"
        : "warn",
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
