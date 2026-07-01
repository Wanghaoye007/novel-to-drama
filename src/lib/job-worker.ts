import { executePlatformJob } from "./engine-runner";
import {
  claimNextQueuedJob,
  failJob,
  requeueStaleRunningJobs,
  type JobKind,
} from "./jobs";

let kickActive = false;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function shouldAutoRunWorker(): boolean {
  if (process.env.NOVEL_DRAMA_AUTO_WORKER === "0") return false;
  if (process.env.NOVEL_DRAMA_AUTO_WORKER === "1") return true;
  return process.env.NODE_ENV !== "production";
}

export async function runQueuedJobs({
  kind,
  limit = 10,
  watch = false,
  pollMs = 1000,
  recoverStale = true,
}: {
  kind?: JobKind;
  limit?: number;
  watch?: boolean;
  pollMs?: number;
  recoverStale?: boolean;
} = {}): Promise<{ processed: number }> {
  if (recoverStale) await requeueStaleRunningJobs();

  let processed = 0;
  const max = Math.max(1, Math.floor(limit));

  while (watch || processed < max) {
    const job = await claimNextQueuedJob({ kind });
    if (!job) {
      if (!watch) break;
      await sleep(Math.max(250, pollMs));
      continue;
    }

    try {
      await executePlatformJob(job);
    } catch (error) {
      await failJob(job.id, error);
      console.error("[job-worker] failed:", error);
    }
    processed += 1;
  }

  return { processed };
}

export function kickJobWorker(): void {
  if (!shouldAutoRunWorker() || kickActive) return;
  kickActive = true;
  void runQueuedJobs({ limit: 1, recoverStale: false }).finally(() => {
    kickActive = false;
  });
}
