WITH ranked_active_round_generation_jobs AS (
  SELECT
    "id",
    row_number() OVER (
      PARTITION BY "round_id"
      ORDER BY "updated_at" DESC, "created_at" DESC, "id" DESC
    ) AS "active_rank"
  FROM "jobs"
  WHERE "kind" = 'round_generation'
    AND "round_id" IS NOT NULL
    AND "status" IN ('queued', 'running')
)
UPDATE "jobs"
SET
  "status" = 'failed',
  "progress" = 100,
  "error_text" = COALESCE(
    "error_text",
    'round_generation dedup migration: superseded by a newer active job for the same round'
  ),
  "finished_at" = COALESCE(
    "finished_at",
    CAST(strftime('%s', 'now') AS INTEGER) * 1000
  ),
  "updated_at" = CAST(strftime('%s', 'now') AS INTEGER) * 1000
WHERE "id" IN (
  SELECT "id"
  FROM ranked_active_round_generation_jobs
  WHERE "active_rank" > 1
);
--> statement-breakpoint
CREATE UNIQUE INDEX `jobs_active_round_generation_unique` ON `jobs` (`round_id`) WHERE "jobs"."kind" = 'round_generation' and "jobs"."round_id" is not null and "jobs"."status" in ('queued', 'running');
