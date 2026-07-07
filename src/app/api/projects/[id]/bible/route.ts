import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import {
  findTenantProject,
  platformHeaders,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { platformErrorResponse } from "@/lib/platform-route";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const context = await resolvePlatformContext(req);
    const project = await findTenantProject(id, context.tenant.id, context.user.id);
    if (!project) return NextResponse.json({ error: "not found" }, { status: 404 });

    const body = await req.json();
    await db
      .update(schema.bibles)
      .set({
        charactersMd: body.charactersMd,
        episodePlanMd: body.episodePlanMd,
        sixAssetsJson: body.sixAssetsJson,
        updatedAt: new Date(),
      })
      .where(eq(schema.bibles.projectId, id));
    return NextResponse.json({ ok: true }, { headers: platformHeaders(context) });
  } catch (error) {
    const response = platformErrorResponse(error);
    if (response) return response;
    throw error;
  }
}
