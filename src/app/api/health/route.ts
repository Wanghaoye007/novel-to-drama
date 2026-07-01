export async function GET() {
  return Response.json({
    ok: true,
    app: "novel-to-drama",
    mode: process.env.NOVEL_DRAMA_WEB_MOCK === "1" ? "mock" : "real",
    autoWorker: process.env.NOVEL_DRAMA_AUTO_WORKER ?? "default",
    timestamp: new Date().toISOString(),
  });
}
