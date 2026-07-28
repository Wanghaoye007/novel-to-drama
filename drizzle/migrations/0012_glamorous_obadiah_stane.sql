CREATE TABLE `job_events` (
	`id` text PRIMARY KEY NOT NULL,
	`job_id` text NOT NULL,
	`event_type` text NOT NULL,
	`message` text,
	`metadata_json` text,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`job_id`) REFERENCES `jobs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `job_events_job_created_idx` ON `job_events` (`job_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `worker_instances` (
	`id` text PRIMARY KEY NOT NULL,
	`status` text DEFAULT 'online' NOT NULL,
	`current_job_id` text,
	`hostname` text NOT NULL,
	`pid` integer NOT NULL,
	`version` text NOT NULL,
	`started_at` integer NOT NULL,
	`heartbeat_at` integer NOT NULL,
	`stopped_at` integer
);
--> statement-breakpoint
ALTER TABLE `jobs` ADD `worker_id` text REFERENCES worker_instances(id);