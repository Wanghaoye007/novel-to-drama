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
  if (
    value === "round_generation" ||
    value === "quality_samples" ||
    value === "delivery_export" ||
    value === "video_brief_export" ||
    value === "localization_export"
  ) {
    return value;
  }
  return undefined;
}

function parseBool(value: string | undefined): boolean {
  return value === "1" || value === "true" || value === "yes";
}

async function main() {
  const watch = hasArg("--watch");
  const kind = parseKind(argValue("--kind"));
  const limit = Number.parseInt(argValue("--limit") ?? "10", 10);
  const pollMs = Number.parseInt(argValue("--poll-ms") ?? "1000", 10);
  const recoverInterrupted =
    hasArg("--recover-interrupted") ||
    parseBool(process.env.NOVEL_DRAMA_RECOVER_INTERRUPTED_RUNNING);
  const interruptedOlderThanMs = Number.parseInt(
    process.env.NOVEL_DRAMA_RECOVER_INTERRUPTED_OLDER_THAN_MS ?? "0",
    10
  );
  const result = await runQueuedJobs({
    kind,
    limit,
    watch,
    pollMs,
    recoverInterrupted,
    interruptedOlderThanMs,
  });
  if (!watch) {
    console.log(`Processed jobs: ${result.processed}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
