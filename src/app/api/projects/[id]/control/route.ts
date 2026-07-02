import { NextRequest, NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import {
  scheduleNextRoundIfRunAll,
  startNextEngineRound,
} from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { updateProjectMeta } from "@/lib/project-controls";

type ProjectControlAction = "pause" | "resume" | "run_all" | "stop_run_all";

type ProjectControlBody = {
  action?: ProjectControlAction;
  generationVariant?: string | null;
  repairBudget?: string | null;
};

async function readBody(req: NextRequest): Promise<ProjectControlBody> {
  try {
    return (await req.json()) as ProjectControlBody;
  } catch {
    return {};
  }
}

async function markQueuedJobsPaused(projectId: string): Promise<void> {
  await db
    .update(schema.jobs)
    .set({
      message: "项目已暂停，等待继续",
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(schema.jobs.projectId, projectId),
        eq(schema.jobs.kind, "round_generation"),
        eq(schema.jobs.status, "queued")
      )
    );
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const body = await readBody(req);
    const project = await findTenantProject(id, context.tenant.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });
    if (
      project.status === "done" &&
      (body.action === "pause" ||
        body.action === "resume" ||
        body.action === "run_all")
    ) {
      return NextResponse.json(
        { error: "项目已完成，不能继续调度" },
        { status: 409, headers: platformHeaders(context) }
      );
    }

    const now = new Date();
    if (body.action === "pause") {
      await db
        .update(schema.projects)
        .set({ status: "paused", updatedAt: now })
        .where(eq(schema.projects.id, id));
      await markQueuedJobsPaused(id);
      return NextResponse.json(
        { status: "paused" },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "resume") {
      await db
        .update(schema.projects)
        .set({ status: "running", updatedAt: now })
        .where(eq(schema.projects.id, id));
      const nextJob = await scheduleNextRoundIfRunAll(id);
      kickJobWorker();
      return NextResponse.json(
        { status: "running", nextJob },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "run_all") {
      await updateProjectMeta(id, (meta) => ({
        ...meta,
        control: {
          ...(meta.control ?? {}),
          runAll: {
            enabled: true,
            generationVariant: body.generationVariant ?? null,
            repairBudget: body.repairBudget ?? null,
            requestedAt: new Date().toISOString(),
          },
        },
      }));
      await db
        .update(schema.projects)
        .set({ status: "running", updatedAt: now })
        .where(eq(schema.projects.id, id));
      const nextJob = await startNextEngineRound(id, {
        generationVariant: body.generationVariant,
        repairBudget: body.repairBudget,
      });
      kickJobWorker();
      return NextResponse.json(
        { status: "running", runAll: true, nextJob },
        { headers: platformHeaders(context) }
      );
    }

    if (body.action === "stop_run_all") {
      await updateProjectMeta(id, (meta) => ({
        ...meta,
        control: {
          ...(meta.control ?? {}),
          runAll: {
            ...(meta.control?.runAll ?? {}),
            enabled: false,
          },
        },
      }));
      return NextResponse.json(
        { runAll: false },
        { headers: platformHeaders(context) }
      );
    }

    return NextResponse.json({ error: "unknown action" }, { status: 400 });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
