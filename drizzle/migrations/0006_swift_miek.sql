CREATE TABLE `credit_ledger` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text NOT NULL,
	`user_id` text,
	`source_type` text NOT NULL,
	`credits_delta` integer NOT NULL,
	`balance_after` integer NOT NULL,
	`usage_event_id` text,
	`checkout_session_id` text,
	`invoice_id` text,
	`reference_key` text,
	`metadata_json` text,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`usage_event_id`) REFERENCES `usage_events`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`checkout_session_id`) REFERENCES `payment_checkout_sessions`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`invoice_id`) REFERENCES `payment_invoices`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE TABLE `credit_packages` (
	`id` text PRIMARY KEY NOT NULL,
	`slug` text NOT NULL,
	`name` text NOT NULL,
	`credits` integer NOT NULL,
	`price_cents` integer NOT NULL,
	`currency` text DEFAULT 'USD' NOT NULL,
	`active` integer DEFAULT true NOT NULL,
	`sort_order` integer DEFAULT 0 NOT NULL,
	`metadata_json` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `payment_checkout_sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text NOT NULL,
	`package_id` text,
	`provider` text DEFAULT 'mock' NOT NULL,
	`status` text DEFAULT 'open' NOT NULL,
	`credits` integer NOT NULL,
	`amount_cents` integer NOT NULL,
	`currency` text DEFAULT 'USD' NOT NULL,
	`checkout_url` text,
	`external_session_id` text,
	`metadata_json` text,
	`expires_at` integer,
	`completed_at` integer,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`package_id`) REFERENCES `credit_packages`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE TABLE `payment_customers` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text NOT NULL,
	`provider` text DEFAULT 'mock' NOT NULL,
	`external_customer_id` text,
	`billing_email` text,
	`status` text DEFAULT 'active' NOT NULL,
	`metadata_json` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `payment_invoices` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text NOT NULL,
	`checkout_session_id` text,
	`provider` text DEFAULT 'mock' NOT NULL,
	`status` text DEFAULT 'paid' NOT NULL,
	`credits` integer NOT NULL,
	`amount_cents` integer NOT NULL,
	`currency` text DEFAULT 'USD' NOT NULL,
	`external_invoice_id` text,
	`hosted_invoice_url` text,
	`metadata_json` text,
	`paid_at` integer,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`checkout_session_id`) REFERENCES `payment_checkout_sessions`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE TABLE `payment_webhook_events` (
	`id` text PRIMARY KEY NOT NULL,
	`tenant_id` text,
	`checkout_session_id` text,
	`provider` text DEFAULT 'mock' NOT NULL,
	`event_type` text NOT NULL,
	`status` text DEFAULT 'received' NOT NULL,
	`external_event_id` text,
	`payload_json` text,
	`error_text` text,
	`created_at` integer NOT NULL,
	`processed_at` integer,
	FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`checkout_session_id`) REFERENCES `payment_checkout_sessions`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
ALTER TABLE `usage_events` ADD `billable_units` integer DEFAULT 0 NOT NULL;