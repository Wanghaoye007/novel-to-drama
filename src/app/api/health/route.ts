export async function GET() {
  const mockMode = process.env.NOVEL_DRAMA_WEB_MOCK === "1";
  let baseUrlHost: string | null = null;
  if (process.env.OPENAI_BASE_URL) {
    try {
      baseUrlHost = new URL(process.env.OPENAI_BASE_URL).host;
    } catch {
      baseUrlHost = "invalid-url";
    }
  }
  return Response.json({
    ok: true,
    app: "novel-to-drama",
    mode: mockMode ? "mock" : "real",
    autoWorker: process.env.NOVEL_DRAMA_AUTO_WORKER ?? "default",
    llm: {
      ready: mockMode || Boolean(process.env.OPENAI_API_KEY),
      provider: process.env.NOVEL_DRAMA_LLM_PROVIDER ?? null,
      model: process.env.OPENAI_MODEL ?? null,
      baseUrlHost,
      hasApiKey: Boolean(process.env.OPENAI_API_KEY),
    },
    timestamp: new Date().toISOString(),
  });
}
