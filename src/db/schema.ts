import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

export const projects = sqliteTable("projects", {
  id: text("id").primaryKey(),
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
