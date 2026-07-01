ALTER TABLE `jobs` ADD `payload_json` text;--> statement-breakpoint
ALTER TABLE `jobs` ADD `attempts` integer DEFAULT 0 NOT NULL;