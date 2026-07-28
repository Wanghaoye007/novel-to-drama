import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

const databasePath = resolve(process.env.NOVEL_DRAMA_DB_PATH ?? "./db.sqlite");
const migrationsFolder = resolve("./drizzle/migrations");

mkdirSync(dirname(databasePath), { recursive: true });

const sqlite = new Database(databasePath);
try {
  sqlite.pragma("journal_mode = WAL");
  sqlite.pragma("foreign_keys = ON");
  migrate(drizzle(sqlite), { migrationsFolder });
  console.log(`Database migrations applied: ${databasePath}`);
} finally {
  sqlite.close();
}
