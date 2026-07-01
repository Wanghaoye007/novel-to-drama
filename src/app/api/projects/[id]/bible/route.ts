import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db, schema } from "@/db/client";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
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
  return NextResponse.json({ ok: true });
}
