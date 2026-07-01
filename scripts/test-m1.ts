import fs from "fs/promises";
import { normalizeNovel, extractRuleBasedMeta } from "../src/lib/m1-normalize";

(async () => {
  const sample = `第一章 开始
这是测试内容。

第二章 继续
更多内容。`;
  console.log("Rule-based:", extractRuleBasedMeta(sample));

  // Full pipeline with fixture (requires ANTHROPIC_API_KEY)
  if (!process.env.ANTHROPIC_API_KEY) {
    console.log("\nSkip LLM portion: set ANTHROPIC_API_KEY to test full normalize.");
    return;
  }
  const path = "/Users/wangzipeng/Documents/DJ_Project/pipeline/input/祖母穿越女.txt";
  const buffer = await fs.readFile(path);
  const result = await normalizeNovel("祖母穿越女.txt", buffer);
  console.log("\nMeta:", JSON.stringify(result.meta, null, 2));
  console.log("Text length:", result.text.length);
})();
