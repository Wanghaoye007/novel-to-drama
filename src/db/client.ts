import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as schema from "./schema";
import {
  ensureDatabaseDirectory,
  resolveDatabasePath,
} from "@/lib/deployment-readiness";

const databasePath = resolveDatabasePath();
ensureDatabaseDirectory(databasePath);

const sqlite = new Database(databasePath);
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });
export { schema };
