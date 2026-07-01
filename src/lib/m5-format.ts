import { callLLM } from "./anthropic";
import { M5_FORMAT_PROMPT } from "./prompts/m5-format";
import { fill } from "./prompts/m2-bible";

export async function formatToAtomicShots(draftMd: string): Promise<string> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const out = await callLLM({
        model: "sonnet",
        user: fill(M5_FORMAT_PROMPT, { DRAFT: draftMd }),
        maxTokens: 4096,
        temperature: 0.2,
      });
      // Validate: must contain at least one [SCENE], [ACTION], [SPEAKER]
      if (
        out.includes("[SCENE]") &&
        out.includes("[ACTION]") &&
        out.includes("[SPEAKER]")
      ) {
        return out;
      }
      throw new Error("output missing required tags");
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(`M5 format failed: ${String(lastErr)}`);
}
