import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "..");

function read(relativePath: string): string {
  return readFileSync(path.join(repoRoot, relativePath), "utf-8");
}

test("Zeabur image packages Node, Python, SQLite tooling and one supervised entrypoint", () => {
  const dockerfile = read("Dockerfile");
  const packageJson = JSON.parse(read("package.json")) as {
    scripts?: Record<string, string>;
  };

  assert.match(dockerfile, /FROM node:22-bookworm-slim/);
  assert.match(dockerfile, /python3/);
  assert.match(dockerfile, /sqlite3/);
  assert.match(dockerfile, /tini/);
  assert.match(dockerfile, /npm run build/);
  assert.match(dockerfile, /npm prune --omit=dev/);
  assert.match(dockerfile, /pip install .*\./);
  assert.match(dockerfile, /EXPOSE 8080/);
  assert.match(dockerfile, /ENTRYPOINT \["\/usr\/bin\/tini", "--"\]/);
  assert.match(dockerfile, /CMD \["scripts\/start-zeabur\.sh"\]/);
  assert.match(packageJson.scripts?.build ?? "", /NOVEL_DRAMA_DB_PATH=:memory:/);
});

test("Zeabur startup requires a volume and starts Web plus the durable worker", () => {
  const script = read("scripts/start-zeabur.sh");
  const readinessScript = read("scripts/ops-online-readiness.sh");

  assert.match(script, /mountpoint -q "\$PERSIST_ROOT"/);
  assert.match(readinessScript, /^#!\/usr\/bin\/env bash/);
  assert.match(script, /NOVEL_DRAMA_DB_PATH=.*\/data\/db\.sqlite/);
  assert.match(script, /NOVEL_DRAMA_STORAGE_ROOT=.*\/data\/storage/);
  assert.match(script, /NOVEL_DRAMA_BACKUP_DIR=.*\/data\/backups/);
  assert.ok(script.indexOf("npm run db:migrate:runtime") < script.indexOf("ops:backup"));
  assert.ok(script.indexOf("ops:backup") < script.indexOf("ops:online-readiness"));
  assert.match(script, /npm run start -- -H 0\.0\.0\.0 -p "\$PORT"/);
  assert.match(script, /npm run jobs:watch -- --poll-ms/);
  assert.match(script, /--recover-interrupted/);
  assert.match(script, /trap shutdown TERM INT EXIT/);
  assert.match(script, /wait -n/);
});

test("Zeabur runtime migration uses the production ORM instead of drizzle-kit", () => {
  const packageJson = JSON.parse(read("package.json")) as {
    scripts?: Record<string, string>;
  };
  const migrationScript = read("src/scripts/migrate-db.ts");

  assert.equal(packageJson.scripts?.["db:migrate:runtime"], "tsx src/scripts/migrate-db.ts");
  assert.match(migrationScript, /drizzle-orm\/better-sqlite3\/migrator/);
  assert.match(migrationScript, /migrationsFolder/);
  assert.match(migrationScript, /sqlite\.close\(\)/);
});

test("Zeabur build context excludes secrets and all mutable local data", () => {
  const dockerIgnore = read(".dockerignore");

  for (const required of [
    ".env",
    ".env.local",
    "*.sqlite",
    "*.sqlite-wal",
    "storage/",
    "uploads/",
    ".git/",
  ]) {
    assert.match(dockerIgnore, new RegExp(required.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("Zeabur environment example is production-real and keeps secrets empty", () => {
  const env = read("deploy/zeabur.env.example");

  assert.match(env, /NOVEL_DRAMA_WEB_MOCK=0/);
  assert.match(env, /NOVEL_DRAMA_ONLINE_MODE=1/);
  assert.match(env, /NOVEL_DRAMA_ACCESS_COOKIE_SECURE=1/);
  assert.match(env, /NOVEL_DRAMA_ALLOW_SESSION_SWITCH=0/);
  assert.match(env, /OPENAI_API_KEY=\n/);
  assert.match(env, /NOVEL_DRAMA_ACCESS_TOKEN=\n/);
  assert.match(env, /NOVEL_DRAMA_SESSION_SECRET=\n/);
  assert.doesNotMatch(env, /sk-[A-Za-z0-9_-]{12,}/);
});

test("public health probe exposes status without deployment internals", async () => {
  const previous = {
    dbPath: process.env.NOVEL_DRAMA_DB_PATH,
    apiKey: process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL,
    baseUrl: process.env.OPENAI_BASE_URL,
  };
  try {
    process.env.NOVEL_DRAMA_DB_PATH = path.join(os.tmpdir(), "private.sqlite");
    process.env.OPENAI_API_KEY = "health-check-secret";
    process.env.OPENAI_MODEL = "private-model";
    process.env.OPENAI_BASE_URL = "https://private-provider.example/v1";

    const { GET } = await import("../src/app/api/health/route");
    const response = await GET();
    const body = JSON.stringify(await response.json());

    assert.equal(response.status, 200);
    assert.doesNotMatch(body, /private\.sqlite/);
    assert.doesNotMatch(body, /private-model/);
    assert.doesNotMatch(body, /private-provider/);
    assert.doesNotMatch(body, /hasApiKey|baseUrlHost|checks/);
    assert.match(body, /"readiness":"(?:ready|warning|blocked)"/);
  } finally {
    if (previous.dbPath === undefined) delete process.env.NOVEL_DRAMA_DB_PATH;
    else process.env.NOVEL_DRAMA_DB_PATH = previous.dbPath;
    if (previous.apiKey === undefined) delete process.env.OPENAI_API_KEY;
    else process.env.OPENAI_API_KEY = previous.apiKey;
    if (previous.model === undefined) delete process.env.OPENAI_MODEL;
    else process.env.OPENAI_MODEL = previous.model;
    if (previous.baseUrl === undefined) delete process.env.OPENAI_BASE_URL;
    else process.env.OPENAI_BASE_URL = previous.baseUrl;
  }
});

test("public health probe returns 503 when production readiness is blocked", async () => {
  const previous = {
    nodeEnv: process.env.NODE_ENV,
    onlineMode: process.env.NOVEL_DRAMA_ONLINE_MODE,
    accessToken: process.env.NOVEL_DRAMA_ACCESS_TOKEN,
    sessionSecret: process.env.NOVEL_DRAMA_SESSION_SECRET,
  };
  try {
    Reflect.set(process.env, "NODE_ENV", "production");
    process.env.NOVEL_DRAMA_ONLINE_MODE = "1";
    delete process.env.NOVEL_DRAMA_ACCESS_TOKEN;
    delete process.env.NOVEL_DRAMA_SESSION_SECRET;

    const { GET } = await import("../src/app/api/health/route");
    const response = await GET();
    const body = await response.json();

    assert.equal(response.status, 503);
    assert.equal(body.readiness, "blocked");
  } finally {
    if (previous.nodeEnv === undefined) Reflect.deleteProperty(process.env, "NODE_ENV");
    else Reflect.set(process.env, "NODE_ENV", previous.nodeEnv);
    if (previous.onlineMode === undefined) delete process.env.NOVEL_DRAMA_ONLINE_MODE;
    else process.env.NOVEL_DRAMA_ONLINE_MODE = previous.onlineMode;
    if (previous.accessToken === undefined) delete process.env.NOVEL_DRAMA_ACCESS_TOKEN;
    else process.env.NOVEL_DRAMA_ACCESS_TOKEN = previous.accessToken;
    if (previous.sessionSecret === undefined) delete process.env.NOVEL_DRAMA_SESSION_SECRET;
    else process.env.NOVEL_DRAMA_SESSION_SECRET = previous.sessionSecret;
  }
});

test("production export creates a real Word archive", async () => {
  const { buildEpisodeWordDocument } = await import("../src/lib/script-export");
  const document = await buildEpisodeWordDocument(
    "部署验证",
    "# EPISODE 1\n\n1-1 夜-内-客厅\n角色：台词"
  );

  assert.ok(document.length > 500);
  assert.equal(document.subarray(0, 2).toString("ascii"), "PK");
});
