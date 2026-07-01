import { headers } from "next/headers";
import { notFound } from "next/navigation";
import {
  findTenantProject,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { RoundClient } from "./RoundClient";

export const dynamic = "force-dynamic";

export default async function RoundPage({
  params,
}: {
  params: Promise<{ id: string; n: string }>;
}) {
  const { id, n } = await params;
  const context = await resolvePlatformContext(await headers());
  const project = await findTenantProject(id, context.tenant.id);
  if (!project) notFound();
  return (
    <RoundClient
      projectId={id}
      roundNum={parseInt(n)}
      project={project}
    />
  );
}
