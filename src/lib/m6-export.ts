import fs from "fs/promises";
import { createWriteStream } from "fs";
import path from "path";
import archiver from "archiver";
import { ensureProjectDir, projectDir } from "./storage";

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

export async function writeBibleMd(
  projectId: string,
  charactersMd: string,
  episodePlanMd: string,
  sixAssetsJson: string
): Promise<string> {
  const dir = await ensureProjectDir(projectId);
  const filePath = path.join(dir, "Bible.md");
  const content = `# Bible

## 六大资产

\`\`\`json
${sixAssetsJson}
\`\`\`

## 人物小传

${charactersMd}

## 集数规划

${episodePlanMd}
`;
  await fs.writeFile(filePath, content);
  return filePath;
}

export async function buildProjectZip(
  projectId: string,
  projectName: string
): Promise<string> {
  const dir = projectDir(projectId);
  const zipPath = path.join(dir, `${projectName}.zip`);

  await new Promise<void>((resolve, reject) => {
    const output = createWriteStream(zipPath);
    const archive = archiver("zip", { zlib: { level: 9 } });

    output.on("close", () => resolve());
    archive.on("error", (err) => reject(err));

    archive.pipe(output);

    archive.glob("E*.txt", { cwd: dir });
    archive.glob("Bible.md", { cwd: dir });

    archive.finalize();
  });

  return zipPath;
}
