import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import { deliveryZipPath, startDeliveryExportJob } from "@/lib/engine-runner";
import { kickJobWorker } from "@/lib/job-worker";
import { attachmentDisposition } from "@/lib/script-export";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";
import { recordUsageEvent } from "@/lib/platform-usage";

function requestUrl(req: NextRequest): URL {
  return req.nextUrl ?? new URL(req.url);
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(_req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
    if (!project) return new Response("not found", { status: 404 });

    const url = requestUrl(_req);
    const round = url.searchParams.get("round");
    const roundNumber = round ? Number.parseInt(round, 10) : undefined;
    const zipPath = await deliveryZipPath(
      id,
      roundNumber
    );
    let buf: Buffer;
    try {
      buf = await fs.readFile(zipPath);
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      if (code === "ENOENT") {
        return new Response("delivery export is not ready; create an export job first", {
          status: 409,
          headers: platformHeaders(context),
        });
      }
      throw error;
    }
    return new Response(new Uint8Array(buf), {
      headers: {
        ...platformHeaders(context),
        "Content-Type": "application/zip",
        "Content-Disposition": attachmentDisposition(`${project.name}.zip`),
      },
    });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const url = requestUrl(req);
    const round = url.searchParams.get("round");
    const roundNumber = round ? Number.parseInt(round, 10) : null;
    const allowIssues = url.searchParams.get("allowIssues") === "1";
    const idempotencyKey =
      req.headers.get("idempotency-key") ??
      req.headers.get("x-idempotency-key") ??
      null;
    const job = await startDeliveryExportJob(id, {
      roundNumber,
      allowIssues,
      idempotencyKey,
    });
    kickJobWorker();
    await recordUsageEvent({
      context,
      eventType: "delivery_export",
      projectId: id,
      jobId: job.id,
      metadata: {
        round: roundNumber,
        allowIssues,
      },
    });

    return NextResponse.json(
      {
        status: job.status === "succeeded" ? "succeeded" : "queued",
        jobId: job.id,
        kind: job.kind,
      },
      { status: 202, headers: platformHeaders(context) }
    );
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
