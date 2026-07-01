import { NextResponse } from "next/server";
import { asc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { listJobViews } from "@/lib/jobs";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const bible = await db.query.bibles.findFirst({
      where: eq(schema.bibles.projectId, id),
    });
    const rounds = await db.query.rounds.findMany({
      where: eq(schema.rounds.projectId, id),
      orderBy: [asc(schema.rounds.roundNum)],
    });
    const episodes = await db.query.episodes.findMany({
      where: eq(schema.episodes.projectId, id),
      orderBy: [asc(schema.episodes.epNum)],
    });
    const jobs = await listJobViews({
      tenantId: context.tenant.id,
      projectId: id,
      limit: 8,
    });

    return NextResponse.json(
      { project, bible, rounds, episodes, jobs },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
