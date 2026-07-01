import {
  listTenantApiKeys,
} from "@/lib/platform-context";
import { getBillingOverview } from "@/lib/platform-billing";
import { getCreditOverview } from "@/lib/platform-credits";
import { resolvePlatformPageContext } from "@/lib/platform-page-context";
import { getUsageSummary } from "@/lib/platform-usage";
import { PlatformClient } from "./PlatformClient";

export const dynamic = "force-dynamic";

export default async function PlatformPage() {
  const { context, session } = await resolvePlatformPageContext();
  const billing = await getBillingOverview(context);
  const [apiKeys, usage, credits] = await Promise.all([
    listTenantApiKeys(context),
    getUsageSummary(context),
    getCreditOverview(context),
  ]);

  return (
    <PlatformClient
      tenant={{
        id: context.tenant.id,
        name: context.tenant.name,
        slug: context.tenant.slug,
        projectLimit: billing.plan.projectLimit,
        monthlyJobLimit: billing.plan.monthlyJobLimit,
      }}
      user={{
        id: context.user.id,
        email: context.user.email,
      }}
      apiKeys={apiKeys}
      usage={usage}
      billing={billing}
      credits={credits}
      session={session}
    />
  );
}
