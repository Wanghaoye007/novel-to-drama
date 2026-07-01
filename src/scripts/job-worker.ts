import { runQueuedJobs } from "@/lib/job-worker";
import type { JobKind } from "@/lib/jobs";

function argValue(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  if (index === -1) return undefined;
  return process.argv[index + 1];
}

function hasArg(name: string): boolean {
  return process.argv.includes(name);
}

function parseKind(value: string | undefined): JobKind | undefined {
  if (value === "round_generation" || value === "quality_samples") return value;
  return undefined;
}

async function main() {
  const watch = hasArg("--watch");
  const kind = parseKind(argValue("--kind"));
  const limit = Number.parseInt(argValue("--limit") ?? "10", 10);
  const pollMs = Number.parseInt(argValue("--poll-ms") ?? "1000", 10);
  const result = await runQueuedJobs({ kind, limit, watch, pollMs });
  if (!watch) {
    console.log(`Processed jobs: ${result.processed}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
