import { listMethodology } from "@/lib/methodology";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { MethodologyClient } from "./MethodologyClient";

export const dynamic = "force-dynamic";

export default async function MethodologyPage() {
  const { context, session } = await resolvePlatformPageContext();
  const data = await listMethodology({ tenantId: context.tenant.id });

  return (
    <MethodologyClient
      initialData={data}
      workspaceName={context.tenant.name}
      sessionSource={session.source}
    />
  );
}
