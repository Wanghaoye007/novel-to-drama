import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");

test("novel context retrieval can select a later relevant chapter instead of fixed opening", async () => {
  const { buildNovelContext } = await import("../src/lib/source-context");
  const source = [
    "第1章 开端\n林挽清在宴会门口被拦下。".repeat(120),
    "第2章 过渡\n公司会议里所有人沉默。".repeat(120),
    "第3章 雪夜\n霍庭琛把选择权交还给她，雪中吻只发生在证据交接之后。".repeat(80),
  ].join("\n\n");

  const context = buildNovelContext(source, {
    maxChars: 1200,
    query: "雪中吻 证据交接 霍庭琛 给她选择权",
    targetEpisode: 8,
    targetEpisodeCount: 20,
    stateLedger: "上一集停在证据交接前。",
  });

  assert.match(context, /第3章 雪夜/);
  assert.match(context, /雪中吻/);
  assert.match(context, /上一集停在证据交接前/);
  assert.ok(context.indexOf("第3章 雪夜") < context.length - 50);
});

test("legacy TypeScript prompts no longer use fixed opening-only source slices", () => {
  const files = [
    "src/lib/m2-bible.ts",
    "src/lib/m3-round.ts",
    "src/lib/prompts/m1-judge.ts",
    "src/lib/prompts/m2-bible.ts",
  ];
  const source = files
    .map((file) => readFileSync(path.join(repoRoot, file), "utf-8"))
    .join("\n");

  assert.doesNotMatch(source, /slice\(0,\s*(6000|8000|15000)\)/);
  assert.doesNotMatch(source, /前\s*(6000|8000|15000)\s*字/);
});
