CREATE TABLE `methodology_cards` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text,
	`source_id` text NOT NULL,
	`name` text NOT NULL,
	`category` text NOT NULL,
	`applies_to_channel_json` text NOT NULL,
	`applies_to_genre_json` text NOT NULL,
	`applies_to_stage_json` text NOT NULL,
	`trigger` text NOT NULL,
	`generation_rule` text NOT NULL,
	`quality_rule` text NOT NULL,
	`positive_examples_json` text,
	`negative_examples_json` text,
	`status` text DEFAULT 'draft' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`source_id`) REFERENCES `methodology_sources`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `methodology_runs` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text,
	`project_id` text,
	`round_id` text,
	`source_strength_json` text,
	`methodology_context_json` text,
	`methodology_quality_json` text,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`round_id`) REFERENCES `rounds`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE TABLE `methodology_sources` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text,
	`title` text NOT NULL,
	`source_type` text NOT NULL,
	`raw_text` text NOT NULL,
	`origin_path` text,
	`status` text DEFAULT 'draft' NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade
);
