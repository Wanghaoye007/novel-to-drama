import {
  deploymentReadiness,
  resolveDatabasePath,
} from "@/lib/deployment-readiness";
import { resolveEngineMode } from "@/lib/engine-runner";

export async function GET() {
  const engineMode = resolveEngineMode();
  const mockMode = engineMode.mode === "mock";
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
    mode: engineMode.mode,
    explicitMock: engineMode.explicitMock,
    autoWorker: process.env.NOVEL_DRAMA_AUTO_WORKER ?? "default",
    db: {
      path: resolveDatabasePath(),
      configured: Boolean(process.env.NOVEL_DRAMA_DB_PATH),
    },
    llm: {
      ready: mockMode || Boolean(process.env.OPENAI_API_KEY),
      provider: process.env.NOVEL_DRAMA_LLM_PROVIDER ?? null,
      model: process.env.OPENAI_MODEL ?? null,
      baseUrlHost,
      hasApiKey: Boolean(process.env.OPENAI_API_KEY),
    },
    readiness: deploymentReadiness(),
    timestamp: new Date().toISOString(),
  });
}
