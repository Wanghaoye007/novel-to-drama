import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "..");

function read(relativePath: string): string {
  return readFileSync(path.join(repoRoot, relativePath), "utf-8");
}

test("app shell exposes the internal operations console", () => {
  const shell = read("src/components/app-shell.tsx");

  assert.match(shell, /href:\s*"\/ops"/);
  assert.match(shell, /label:\s*"任务运维"/);
  assert.match(shell, /pathname\.startsWith\("\/ops"\)/);
});

test("ops console renders compact summary, filters, actions, and detail timeline", () => {
  const client = read("src/app/ops/OpsConsoleClient.tsx");

  for (const label of [
    "Worker",
    "排队 / 运行",
    "失败任务",
    "上线准备度",
    "任务 ID / 项目",
    "全部状态",
    "全部类型",
    "事件时间线",
    "复制任务 ID",
    "重试任务",
    "取消排队",
  ]) {
    assert.match(client, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(client, /\/api\/ops\/overview/);
  assert.match(client, /\/api\/ops\/jobs/);
  assert.match(client, /\/retry/);
  assert.match(client, /\/cancel/);
});

test("ops polling is visibility-aware and preserves five-second cadence", () => {
  const client = read("src/app/ops/OpsConsoleClient.tsx");

  assert.match(client, /document\.visibilityState\s*!==\s*"visible"/);
  assert.match(client, /window\.setInterval\([\s\S]*5_000/);
  assert.match(client, /visibilitychange/);
});

