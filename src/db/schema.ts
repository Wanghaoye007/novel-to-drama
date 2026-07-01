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
    enum: ["draft", "bible_ready", "running", "done", "failed"],
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
