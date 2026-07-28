import { deploymentReadiness } from "@/lib/deployment-readiness";

export async function GET() {
  const readiness = deploymentReadiness();
  return Response.json(
    {
      ok: true,
      app: "novel-to-drama",
      readiness: readiness.status,
      timestamp: new Date().toISOString(),
    },
    {
      status: readiness.status === "blocked" ? 503 : 200,
      headers: {
        "Cache-Control": "no-store",
      },
    }
  );
}
