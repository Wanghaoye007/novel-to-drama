import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const testsDir = path.join(repoRoot, "tests");
const files = readdirSync(testsDir)
  .filter((file) => file.endsWith(".test.ts"))
  .sort()
  .map((file) => path.join("tests", file));

if (files.length === 0) {
  console.error("No TypeScript test files found under tests/*.test.ts");
  process.exit(1);
}

const result = spawnSync(
  process.execPath,
  ["--test", "--import", "tsx", ...files],
  {
    cwd: repoRoot,
    stdio: "inherit",
  }
);

process.exit(result.status ?? 1);
