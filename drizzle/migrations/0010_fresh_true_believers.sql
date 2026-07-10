CREATE UNIQUE INDEX `credit_ledger_tenant_reference_unique` ON `credit_ledger` (`tenant_id`,`reference_key`) WHERE "credit_ledger"."reference_key" is not null;--> statement-breakpoint
CREATE UNIQUE INDEX `payment_checkout_provider_session_unique` ON `payment_checkout_sessions` (`provider`,`external_session_id`) WHERE "payment_checkout_sessions"."external_session_id" is not null;--> statement-breakpoint
CREATE UNIQUE INDEX `payment_webhook_provider_event_unique` ON `payment_webhook_events` (`provider`,`external_event_id`) WHERE "payment_webhook_events"."external_event_id" is not null;--> statement-breakpoint
CREATE UNIQUE INDEX `tenant_members_tenant_user_unique` ON `tenant_members` (`tenant_id`,`user_id`);--> statement-breakpoint
CREATE UNIQUE INDEX `tenants_slug_unique` ON `tenants` (`slug`);--> statement-breakpoint
CREATE UNIQUE INDEX `users_email_unique` ON `users` (`email`);