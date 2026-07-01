import { headers } from "next/headers";
import {
  listTenantApiKeys,
  resolvePlatformContext,
} from "@/lib/platform-context";
import { getUsageSummary } from "@/lib/platform-usage";
import { PlatformClient } from "./PlatformClient";

export const dynamic = "force-dynamic";

export default async function PlatformPage() {
  const context = await resolvePlatformContext(await headers());
  const [apiKeys, usage] = await Promise.all([
    listTenantApiKeys(context),
    getUsageSummary(context),
  ]);

  return (
    <PlatformClient
      tenant={{
        id: context.tenant.id,
        name: context.tenant.name,
        slug: context.tenant.slug,
        projectLimit: context.tenant.projectLimit,
        monthlyJobLimit: context.tenant.monthlyJobLimit,
      }}
      user={{
        id: context.user.id,
        email: context.user.email,
      }}
      apiKeys={apiKeys}
      usage={usage}
    />
  );
}
