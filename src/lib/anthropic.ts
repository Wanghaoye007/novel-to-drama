import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export const MODELS = {
  opus: "claude-opus-4-7",
  sonnet: "claude-sonnet-4-6",
  haiku: "claude-haiku-4-5-20251001",
} as const;

export type ModelKey = keyof typeof MODELS;

export class LLMCallError extends Error {
  constructor(message: string, public cause?: unknown) {
    super(message);
    this.name = "LLMCallError";
  }
}

interface CallOptions {
  model: ModelKey;
  system?: string;
  user: string;
  maxTokens?: number;
  temperature?: number;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function callLLM(opts: CallOptions): Promise<string> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await client.messages.create({
        model: MODELS[opts.model],
        max_tokens: opts.maxTokens ?? 8192,
        temperature: opts.temperature ?? 0.7,
        system: opts.system,
        messages: [{ role: "user", content: opts.user }],
      });
      const text = res.content
        .filter((b): b is Anthropic.TextBlock => b.type === "text")
        .map((b) => b.text)
        .join("\n");
      if (!text) throw new Error("empty response");
      return text;
    } catch (e) {
      lastErr = e;
      if (attempt < 2) await sleep(1000 * Math.pow(2, attempt));
    }
  }
  throw new LLMCallError("LLM call failed after 3 attempts", lastErr);
}
