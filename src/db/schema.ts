import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull(),
  name: text("name"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const tenants = sqliteTable("tenants", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull(),
  name: text("name").notNull(),
  projectLimit: integer("project_limit").notNull().default(25),
  monthlyJobLimit: integer("monthly_job_limit").notNull().default(200),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const billingPlans = sqliteTable("billing_plans", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull(),
  name: text("name").notNull(),
  monthlyPriceCents: integer("monthly_price_cents").notNull().default(0),
  currency: text("currency").notNull().default("USD"),
  projectLimit: integer("project_limit").notNull().default(25),
  monthlyJobLimit: integer("monthly_job_limit").notNull().default(200),
  includedBillableUnits: integer("included_billable_units")
    .notNull()
    .default(100),
  overageUnitPriceCents: integer("overage_unit_price_cents")
    .notNull()
    .default(0),
  featuresJson: text("features_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const tenantSubscriptions = sqliteTable("tenant_subscriptions", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  planId: text("plan_id")
    .notNull()
    .references(() => billingPlans.id),
  status: text("status", {
    enum: ["active", "trialing", "past_due", "canceled"],
  })
    .notNull()
    .default("active"),
  currentPeriodStart: integer("current_period_start", {
    mode: "timestamp_ms",
  }).notNull(),
  currentPeriodEnd: integer("current_period_end", {
    mode: "timestamp_ms",
  }).notNull(),
  canceledAt: integer("canceled_at", { mode: "timestamp_ms" }),
  externalCustomerId: text("external_customer_id"),
  externalSubscriptionId: text("external_subscription_id"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentCustomers = sqliteTable("payment_customers", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  externalCustomerId: text("external_customer_id"),
  billingEmail: text("billing_email"),
  status: text("status", { enum: ["active", "disabled"] })
    .notNull()
    .default("active"),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const creditPackages = sqliteTable("credit_packages", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull(),
  name: text("name").notNull(),
  credits: integer("credits").notNull(),
  priceCents: integer("price_cents").notNull(),
  currency: text("currency").notNull().default("USD"),
  active: integer("active", { mode: "boolean" }).notNull().default(true),
  sortOrder: integer("sort_order").notNull().default(0),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const tenantMembers = sqliteTable("tenant_members", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  role: text("role", { enum: ["owner", "admin", "member"] })
    .notNull()
    .default("owner"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const apiKeys = sqliteTable("api_keys", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  createdByUserId: text("created_by_user_id").references(() => users.id, {
    onDelete: "set null",
  }),
  name: text("name").notNull(),
  keyPrefix: text("key_prefix").notNull(),
  keyHash: text("key_hash").notNull(),
  lastUsedAt: integer("last_used_at", { mode: "timestamp_ms" }),
  revokedAt: integer("revoked_at", { mode: "timestamp_ms" }),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const projects = sqliteTable("projects", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  ownerUserId: text("owner_user_id").references(() => users.id, {
    onDelete: "set null",
  }),
  name: text("name").notNull(),
  pipelineType: text("pipeline_type", { enum: ["A", "B"] }).notNull().default("A"),
  novelText: text("novel_text").notNull(),
  metaJson: text("meta_json"),
  targetLanguage: text("target_language"),
  targetEpisodeCount: integer("target_episode_count").notNull(),
  status: text("status", {
    enum: ["draft", "bible_ready", "running", "paused", "done", "failed"],
  })
    .notNull()
    .default("draft"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const bibles = sqliteTable("bibles", {
  id: text("id").primaryKey(),
  projectId: text("project_id")
    .notNull()
    .references(() => projects.id, { onDelete: "cascade" }),
  channel: text("channel", { enum: ["male", "female"] }),
  sixAssetsJson: text("six_assets_json"),
  charactersMd: text("characters_md"),
  episodePlanMd: text("episode_plan_md"),
  prevRoundSummaryJson: text("prev_round_summary_json"),
  nameMappingJson: text("name_mapping_json"),
  cultureMappingJson: text("culture_mapping_json"),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const rounds = sqliteTable("rounds", {
  id: text("id").primaryKey(),
  projectId: text("project_id")
    .notNull()
    .references(() => projects.id, { onDelete: "cascade" }),
  roundNum: integer("round_num").notNull(),
  epRange: text("ep_range").notNull(),
  summaryJson: text("summary_json"),
  status: text("status", {
    enum: ["pending", "running", "done", "failed"],
  })
    .notNull()
    .default("pending"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const jobs = sqliteTable("jobs", {
  id: text("id").primaryKey(),
  kind: text("kind", {
    enum: ["round_generation", "quality_samples"],
  }).notNull(),
  status: text("status", {
    enum: ["queued", "running", "succeeded", "failed"],
  })
    .notNull()
    .default("queued"),
  projectId: text("project_id").references(() => projects.id, {
    onDelete: "cascade",
  }),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  roundId: text("round_id").references(() => rounds.id, { onDelete: "set null" }),
  title: text("title").notNull(),
  progress: integer("progress").notNull().default(0),
  message: text("message"),
  errorText: text("error_text"),
  payloadJson: text("payload_json"),
  resultJson: text("result_json"),
  attempts: integer("attempts").notNull().default(0),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
  startedAt: integer("started_at", { mode: "timestamp_ms" }),
  finishedAt: integer("finished_at", { mode: "timestamp_ms" }),
});

export const usageEvents = sqliteTable("usage_events", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  userId: text("user_id").references(() => users.id, { onDelete: "set null" }),
  apiKeyId: text("api_key_id").references(() => apiKeys.id, {
    onDelete: "set null",
  }),
  projectId: text("project_id").references(() => projects.id, {
    onDelete: "set null",
  }),
  jobId: text("job_id").references(() => jobs.id, { onDelete: "set null" }),
  eventType: text("event_type", {
    enum: [
      "project_create",
      "round_start",
      "quality_samples_start",
      "video_brief_export",
      "localization_export",
      "delivery_preflight",
      "delivery_export",
      "episode_txt_export",
      "episode_word_export",
    ],
  }).notNull(),
  quantity: integer("quantity").notNull().default(1),
  billableUnits: integer("billable_units").notNull().default(0),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const methodologySources = sqliteTable("methodology_sources", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  sourceType: text("source_type").notNull(),
  rawText: text("raw_text").notNull(),
  originPath: text("origin_path"),
  status: text("status", {
    enum: ["draft", "active", "archived", "rejected"],
  })
    .notNull()
    .default("draft"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const methodologyCards = sqliteTable("methodology_cards", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  sourceId: text("source_id")
    .notNull()
    .references(() => methodologySources.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  category: text("category").notNull(),
  appliesToChannelJson: text("applies_to_channel_json").notNull(),
  appliesToGenreJson: text("applies_to_genre_json").notNull(),
  appliesToStageJson: text("applies_to_stage_json").notNull(),
  trigger: text("trigger").notNull(),
  generationRule: text("generation_rule").notNull(),
  qualityRule: text("quality_rule").notNull(),
  positiveExamplesJson: text("positive_examples_json"),
  negativeExamplesJson: text("negative_examples_json"),
  status: text("status", {
    enum: ["draft", "active", "archived", "rejected"],
  })
    .notNull()
    .default("draft"),
  version: integer("version").notNull().default(1),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const methodologyRuns = sqliteTable("methodology_runs", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
  projectId: text("project_id").references(() => projects.id, { onDelete: "cascade" }),
  roundId: text("round_id").references(() => rounds.id, { onDelete: "set null" }),
  sourceStrengthJson: text("source_strength_json"),
  methodologyContextJson: text("methodology_context_json"),
  methodologyQualityJson: text("methodology_quality_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentCheckoutSessions = sqliteTable("payment_checkout_sessions", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  packageId: text("package_id").references(() => creditPackages.id, {
    onDelete: "set null",
  }),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  status: text("status", {
    enum: ["open", "paid", "expired", "canceled"],
  })
    .notNull()
    .default("open"),
  credits: integer("credits").notNull(),
  amountCents: integer("amount_cents").notNull(),
  currency: text("currency").notNull().default("USD"),
  checkoutUrl: text("checkout_url"),
  externalSessionId: text("external_session_id"),
  metadataJson: text("metadata_json"),
  expiresAt: integer("expires_at", { mode: "timestamp_ms" }),
  completedAt: integer("completed_at", { mode: "timestamp_ms" }),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentInvoices = sqliteTable("payment_invoices", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  checkoutSessionId: text("checkout_session_id").references(
    () => paymentCheckoutSessions.id,
    { onDelete: "set null" }
  ),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  status: text("status", {
    enum: ["draft", "open", "paid", "void", "refunded"],
  })
    .notNull()
    .default("paid"),
  credits: integer("credits").notNull(),
  amountCents: integer("amount_cents").notNull(),
  currency: text("currency").notNull().default("USD"),
  externalInvoiceId: text("external_invoice_id"),
  hostedInvoiceUrl: text("hosted_invoice_url"),
  metadataJson: text("metadata_json"),
  paidAt: integer("paid_at", { mode: "timestamp_ms" }),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const paymentWebhookEvents = sqliteTable("payment_webhook_events", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id").references(() => tenants.id, {
    onDelete: "set null",
  }),
  checkoutSessionId: text("checkout_session_id").references(
    () => paymentCheckoutSessions.id,
    { onDelete: "set null" }
  ),
  provider: text("provider", {
    enum: ["mock", "stripe", "wechat_pay", "alipay", "manual"],
  })
    .notNull()
    .default("mock"),
  eventType: text("event_type").notNull(),
  status: text("status", {
    enum: ["received", "processed", "failed"],
  })
    .notNull()
    .default("received"),
  externalEventId: text("external_event_id"),
  payloadJson: text("payload_json"),
  errorText: text("error_text"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  processedAt: integer("processed_at", { mode: "timestamp_ms" }),
});

export const creditLedger = sqliteTable("credit_ledger", {
  id: text("id").primaryKey(),
  tenantId: text("tenant_id")
    .notNull()
    .references(() => tenants.id, { onDelete: "cascade" }),
  userId: text("user_id").references(() => users.id, { onDelete: "set null" }),
  sourceType: text("source_type", {
    enum: [
      "monthly_grant",
      "top_up",
      "usage_debit",
      "manual_adjustment",
      "refund",
    ],
  }).notNull(),
  creditsDelta: integer("credits_delta").notNull(),
  balanceAfter: integer("balance_after").notNull(),
  usageEventId: text("usage_event_id").references(() => usageEvents.id, {
    onDelete: "set null",
  }),
  checkoutSessionId: text("checkout_session_id").references(
    () => paymentCheckoutSessions.id,
    { onDelete: "set null" }
  ),
  invoiceId: text("invoice_id").references(() => paymentInvoices.id, {
    onDelete: "set null",
  }),
  referenceKey: text("reference_key"),
  metadataJson: text("metadata_json"),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const episodes = sqliteTable("episodes", {
  id: text("id").primaryKey(),
  projectId: text("project_id")
    .notNull()
    .references(() => projects.id, { onDelete: "cascade" }),
  roundId: text("round_id")
    .notNull()
    .references(() => rounds.id, { onDelete: "cascade" }),
  epNum: integer("ep_num").notNull(),
  draftMd: text("draft_md"),
  scriptTxt: text("script_txt"),
  score: real("score"),
  reviewJson: text("review_json"),
  epSummaryJson: text("ep_summary_json"),
  retryCount: integer("retry_count").notNull().default(0),
  status: text("status", {
    enum: ["pending", "running", "green", "red", "failed"],
  })
    .notNull()
    .default("pending"),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});
