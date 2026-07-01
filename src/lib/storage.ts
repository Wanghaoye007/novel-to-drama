import fs from "fs/promises";
import path from "path";

const STORAGE_ROOT = path.join(/*turbopackIgnore: true*/ process.cwd(), "storage");

export async function ensureSystemDir(name: string): Promise<string> {
  const safeName = name.replace(/[^a-zA-Z0-9_-]/g, "_");
  const dir = path.join(STORAGE_ROOT, "system", safeName);
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

export async function ensureProjectDir(projectId: string): Promise<string> {
  const dir = path.join(STORAGE_ROOT, "projects", projectId);
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

export async function writeProjectFile(
  projectId: string,
  filename: string,
  content: string | Buffer
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  const filePath = path.join(dir, filename);
  await fs.writeFile(filePath, content);
  return filePath;
}

export async function readProjectFile(
  projectId: string,
  filename: string
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  return fs.readFile(path.join(dir, filename), "utf-8");
}

export function projectDir(projectId: string): string {
  return path.join(STORAGE_ROOT, "projects", projectId);
}
