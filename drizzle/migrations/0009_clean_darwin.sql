ALTER TABLE `jobs` ADD `idempotency_key` text;--> statement-breakpoint
WITH ranked_bibles AS (
  SELECT
    `id`,
    row_number() OVER (
      PARTITION BY `project_id`
      ORDER BY `updated_at` DESC, `id` DESC
    ) AS `artifact_rank`
  FROM `bibles`
)
DELETE FROM `bibles`
WHERE `id` IN (
  SELECT `id` FROM ranked_bibles WHERE `artifact_rank` > 1
);--> statement-breakpoint
WITH ranked_rounds AS (
  SELECT
    `id`,
    row_number() OVER (
      PARTITION BY `project_id`, `round_num`
      ORDER BY `created_at` DESC, `id` DESC
    ) AS `artifact_rank`
  FROM `rounds`
)
DELETE FROM `rounds`
WHERE `id` IN (
  SELECT `id` FROM ranked_rounds WHERE `artifact_rank` > 1
);--> statement-breakpoint
DELETE FROM `episodes`
WHERE `round_id` NOT IN (
  SELECT `id` FROM `rounds`
);--> statement-breakpoint
WITH ranked_project_episodes AS (
  SELECT
    `id`,
    row_number() OVER (
      PARTITION BY `project_id`, `ep_num`
      ORDER BY `updated_at` DESC, `id` DESC
    ) AS `artifact_rank`
  FROM `episodes`
)
DELETE FROM `episodes`
WHERE `id` IN (
  SELECT `id` FROM ranked_project_episodes WHERE `artifact_rank` > 1
);--> statement-breakpoint
WITH ranked_round_episodes AS (
  SELECT
    `id`,
    row_number() OVER (
      PARTITION BY `round_id`, `ep_num`
      ORDER BY `updated_at` DESC, `id` DESC
    ) AS `artifact_rank`
  FROM `episodes`
)
DELETE FROM `episodes`
WHERE `id` IN (
  SELECT `id` FROM ranked_round_episodes WHERE `artifact_rank` > 1
);--> statement-breakpoint
CREATE UNIQUE INDEX `jobs_tenant_kind_idempotency_unique` ON `jobs` (`tenant_id`,`kind`,`idempotency_key`) WHERE "jobs"."idempotency_key" is not null;--> statement-breakpoint
CREATE UNIQUE INDEX `bibles_project_unique` ON `bibles` (`project_id`);--> statement-breakpoint
CREATE UNIQUE INDEX `episodes_project_episode_unique` ON `episodes` (`project_id`,`ep_num`);--> statement-breakpoint
CREATE UNIQUE INDEX `episodes_round_episode_unique` ON `episodes` (`round_id`,`ep_num`);--> statement-breakpoint
CREATE UNIQUE INDEX `rounds_project_round_unique` ON `rounds` (`project_id`,`round_num`);
