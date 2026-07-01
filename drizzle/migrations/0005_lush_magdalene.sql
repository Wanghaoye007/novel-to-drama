CREATE TABLE `billing_plans` (
	`id` text PRIMARY KEY NOT NULL,
	`slug` text NOT NULL,
	`name` text NOT NULL,
	`monthly_price_cents` integer DEFAULT 0 NOT NULL,
	`currency` text DEFAULT 'USD' NOT NULL,
	`project_limit` integer DEFAULT 25 NOT NULL,
	`monthly_job_limit` integer DEFAULT 200 NOT NULL,
	`included_billable_units` integer DEFAULT 100 NOT NULL,
	`overage_unit_price_cents` integer DEFAULT 0 NOT NULL,
	`features_json` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `tenant_subscriptions` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text NOT NULL,
	`plan_id` text NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`current_period_start` integer NOT NULL,
	`current_period_end` integer NOT NULL,
	`canceled_at` integer,
	`external_customer_id` text,
	`external_subscription_id` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`plan_id`) REFERENCES `billing_plans`(`id`) ON UPDATE no action ON DELETE no action
);
