import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");

test("Python Engine is the only source retrieval and generation chain", () => {
  const sourcePackets = readFileSync(
    path.join(repoRoot, "src/novel_drama_engine/source_packets.py"),
    "utf-8"
  );
  const removed = [
    "src/lib/source-context.ts",
    "src/lib/m2-bible.ts",
    "src/lib/m3-round.ts",
    "src/lib/prompts/m1-judge.ts",
  ];

  assert.match(sourcePackets, /CHAPTER_HEADING_RE/);
  assert.match(sourcePackets, /chapter_partition/);
  assert.match(sourcePackets, /asset_window/);
  for (const file of removed) {
    assert.equal(existsSync(path.join(repoRoot, file)), false, file);
  }
});
