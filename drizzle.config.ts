import type { Config } from "drizzle-kit";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

const databaseUrl = process.env.NOVEL_DRAMA_DB_PATH ?? "./db.sqlite";
mkdirSync(dirname(resolve(databaseUrl)), { recursive: true });

export default {
  schema: "./src/db/schema.ts",
  out: "./drizzle/migrations",
  dialect: "sqlite",
  dbCredentials: {
    url: databaseUrl,
  },
} satisfies Config;
