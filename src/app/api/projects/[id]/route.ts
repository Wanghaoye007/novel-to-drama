import { NextResponse } from "next/server";
import { and, asc, desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { listJobViews } from "@/lib/jobs";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { removeProjectDir } from "@/lib/storage";
import { projectWorkspaceView } from "@/lib/project-view";

type ProjectPatchBody = {
  name?: unknown;
  targetEpisodeCount?: unknown;
};

export const dynamic = "force-dynamic";
export const revalidate = 0;

function projectStateHeaders(context: Awaited<ReturnType<typeof resolvePlatformContext>>) {
  return {
    ...platformHeaders(context),
    "Cache-Control": "no-store, max-age=0",
  };
}

function normalizeProjectName(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const name = value.trim();
  return name.length > 0 ? name : null;
}

function normalizeTargetEpisodeCount(value: unknown): number | null {
  if (value == null || value === "") return null;
  const count =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number(value)
        : Number.NaN;
  if (!Number.isInteger(count) || count < 1 || count > 100) return null;
  return count;
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
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
      ownerUserId: context.user.id,
      projectId: id,
      limit: 8,
    });

    return NextResponse.json(
      { project: projectWorkspaceView(project), bible, rounds, episodes, jobs },
      { headers: projectStateHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const body = (await req.json().catch(() => ({}))) as ProjectPatchBody;
    const hasName = Object.prototype.hasOwnProperty.call(body, "name");
    const hasTargetEpisodeCount = Object.prototype.hasOwnProperty.call(
      body,
      "targetEpisodeCount"
    );
    const name = normalizeProjectName(body.name);
    const targetEpisodeCount = normalizeTargetEpisodeCount(body.targetEpisodeCount);

    if (!hasName && !hasTargetEpisodeCount) {
      return NextResponse.json(
        { error: "至少需要修改项目名或目标集数" },
        { status: 400, headers: platformHeaders(context) }
      );
    }
    if (hasName && !name) {
      return NextResponse.json(
        { error: "项目名不能为空" },
        { status: 400, headers: platformHeaders(context) }
      );
    }
    if (hasTargetEpisodeCount && targetEpisodeCount == null) {
      return NextResponse.json(
        { error: "目标集数必须是 1-100 的整数" },
        { status: 400, headers: platformHeaders(context) }
      );
    }

    if (targetEpisodeCount != null) {
      const latestEpisode = await db.query.episodes.findFirst({
        where: eq(schema.episodes.projectId, id),
        orderBy: [desc(schema.episodes.epNum)],
      });
      const generatedEpisodeCount = latestEpisode?.epNum ?? 0;
      if (targetEpisodeCount < generatedEpisodeCount) {
        return NextResponse.json(
          {
            error: `目标集数不能低于已输出集数 ${generatedEpisodeCount}`,
          },
          { status: 409, headers: platformHeaders(context) }
        );
      }
    }

    await db
      .update(schema.projects)
      .set({
        ...(name ? { name } : {}),
        ...(targetEpisodeCount != null ? { targetEpisodeCount } : {}),
        updatedAt: new Date(),
      })
      .where(and(eq(schema.projects.id, id), eq(schema.projects.tenantId, context.tenant.id)));

    const updated = await findTenantProject(id, context.tenant.id, context.user.id);
    return NextResponse.json(
      { project: updated },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const runningJob = await db.query.jobs.findFirst({
      where: and(
        eq(schema.jobs.projectId, id),
        eq(schema.jobs.kind, "round_generation"),
        eq(schema.jobs.status, "running")
      ),
    });
    if (runningJob) {
      return NextResponse.json(
        { error: "项目有正在执行的任务，任务结束后再删除" },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    await db
      .delete(schema.projects)
      .where(and(eq(schema.projects.id, id), eq(schema.projects.tenantId, context.tenant.id)));
    await removeProjectDir(id);

    return NextResponse.json(
      { status: "deleted" },
      { headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
