import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");

test("home page is a public marketing site outside the console workspace", () => {
  const homePage = readFileSync(
    path.join(repoRoot, "src/app/page.tsx"),
    "utf-8"
  );
  const appShell = readFileSync(
    path.join(repoRoot, "src/components/app-shell.tsx"),
    "utf-8"
  );

  assert.doesNotMatch(homePage, /resolvePlatformPageContext|db\.query\.projects/);
  assert.match(homePage, /小说转短剧|产品演示|作品展示|招商/);
  assert.match(appShell, /pathname === "\/"/);
  assert.match(appShell, /return <>{children}<\/>/);
});
