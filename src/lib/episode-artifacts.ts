import fs from "fs/promises";
import path from "path";
import { ensureProjectDir } from "./storage";

export async function writeEpisodeTxt(
  projectId: string,
  epNum: number,
  scriptTxt: string
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  const filename = `E${String(epNum).padStart(2, "0")}.txt`;
  const filePath = path.join(dir, filename);
  await fs.writeFile(filePath, scriptTxt);
  return filePath;
}
