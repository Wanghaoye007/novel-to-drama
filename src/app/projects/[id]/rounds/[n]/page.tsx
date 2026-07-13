import { notFound } from "next/navigation";
import { findTenantProject } from "@/lib/platform-context";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { projectWorkspaceView } from "@/lib/project-view";
import { RoundClient } from "./RoundClient";

export const dynamic = "force-dynamic";

export default async function RoundPage({
  params,
}: {
  params: Promise<{ id: string; n: string }>;
}) {
  const { id, n } = await params;
  const { context, session } = await resolvePlatformPageContext();
  const project = await findTenantProject(id, context.tenant.id, context.user.id);
  if (!project) notFound();
  return (
    <RoundClient
      projectId={id}
      roundNum={parseInt(n)}
      project={projectWorkspaceView(project)}
      platformSession={session}
    />
  );
}
