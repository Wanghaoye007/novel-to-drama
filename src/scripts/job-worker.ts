import { runQueuedJobs } from "@/lib/job-worker";
import type { JobKind } from "@/lib/jobs";
import {
  heartbeatWorkerInstance,
  registerWorkerInstance,
  stopWorkerInstance,
} from "@/lib/ops-observability";
import { hostname } from "node:os";
import { randomUUID } from "node:crypto";

let activeWorkerId: string | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let shuttingDown = false;

async function markWorkerStopped(): Promise<void> {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (activeWorkerId) {
    await stopWorkerInstance(activeWorkerId);
    activeWorkerId = null;
  }
}

async function shutdown(signal: "SIGTERM" | "SIGINT"): Promise<void> {
  if (shuttingDown) return;
  shuttingDown = true;
  try {
    await markWorkerStopped();
  } catch (error) {
    console.error(`[worker] ${signal} shutdown record failed`, error);
  } finally {
    process.exit(0);
  }
}

process.once("SIGTERM", () => void shutdown("SIGTERM"));
process.once("SIGINT", () => void shutdown("SIGINT"));

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
    value === "localization_export" ||
    value === "episode_optimize" ||
    value === "edit_impact"
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
  const workerId =
    process.env.NOVEL_DRAMA_WORKER_ID ??
    `${hostname()}:${process.pid}:${randomUUID().slice(0, 8)}`;
  const heartbeatMs = Math.max(
    1_000,
    Number.parseInt(process.env.NOVEL_DRAMA_WORKER_HEARTBEAT_MS ?? "5000", 10) ||
      5_000
  );
  await registerWorkerInstance({
    id: workerId,
    hostname: hostname(),
    pid: process.pid,
    version: process.env.NOVEL_DRAMA_WORKER_VERSION ?? "development",
  });
  activeWorkerId = workerId;
  let heartbeatBusy = false;
  heartbeatTimer = setInterval(() => {
    if (heartbeatBusy) return;
    heartbeatBusy = true;
    void heartbeatWorkerInstance(workerId)
      .catch((error) => console.error(`[worker:${workerId}] heartbeat failed`, error))
      .finally(() => {
        heartbeatBusy = false;
      });
  }, heartbeatMs);

  try {
    const result = await runQueuedJobs({
      kind,
      limit,
      watch,
      pollMs,
      recoverInterrupted,
      interruptedOlderThanMs,
      workerId,
    });
    if (!watch) {
      console.log(`Processed jobs: ${result.processed}`);
    }
  } finally {
    await markWorkerStopped();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
