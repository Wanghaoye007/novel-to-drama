CREATE TABLE `bibles` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`channel` text,
	`six_assets_json` text,
	`characters_md` text,
	`episode_plan_md` text,
	`prev_round_summary_json` text,
	`name_mapping_json` text,
	`culture_mapping_json` text,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `episodes` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`round_id` text NOT NULL,
	`ep_num` integer NOT NULL,
	`draft_md` text,
	`script_txt` text,
	`score` real,
	`review_json` text,
	`ep_summary_json` text,
	`retry_count` integer DEFAULT 0 NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`round_id`) REFERENCES `rounds`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `projects` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`pipeline_type` text DEFAULT 'A' NOT NULL,
	`novel_text` text NOT NULL,
	`meta_json` text,
	`target_language` text,
	`target_episode_count` integer NOT NULL,
	`status` text DEFAULT 'draft' NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `rounds` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`round_num` integer NOT NULL,
	`ep_range` text NOT NULL,
	`summary_json` text,
	`status` text DEFAULT 'pending' NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
