import archiver from "archiver";
import { PassThrough } from "stream";

export type ExportEpisode = {
  epNum: number;
  scriptTxt: string | null;
};

export function sanitizeExportFilename(name: string): string {
  const cleaned = name
    .replace(/[\\/:*?"<>|]+/g, "_")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || "novel-to-drama";
}

export function attachmentDisposition(filename: string): string {
  const fallback = filename
    .replace(/[^\x20-\x7E]+/g, "_")
    .replace(/["\\;]+/g, "_")
    .trim();
  const safeFallback = fallback || "novel-to-drama";
  return `attachment; filename="${safeFallback}"; filename*=UTF-8''${encodeURIComponent(filename)}`;
}

function stripEpisodeTitleLine(text: string, epNum: number): string {
  const lines = text.trim().split(/\r?\n/);
  const titlePattern = new RegExp(`^第\\s*0*${epNum}\\s*集(?:\\s|：|:|$)`);
  if (lines[0] && titlePattern.test(lines[0].trim())) {
    lines.shift();
  }
  return lines.join("\n").trim();
}

export function formatEpisodesAsEpisodeText(episodes: ExportEpisode[]): string {
  return episodes
    .sort((a, b) => a.epNum - b.epNum)
    .map((episode) => {
      const body = stripEpisodeTitleLine(episode.scriptTxt ?? "", episode.epNum);
      return `# EPISODE ${episode.epNum}\n\n${body}`;
    })
    .join("\n\n");
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function paragraphXml(line: string): string {
  if (!line.trim()) return "<w:p/>";
  const isEpisodeHeading = /^#\s*EPISODE\s+\d+\s*$/i.test(line.trim());
  const runProps = isEpisodeHeading
    ? "<w:rPr><w:b/><w:sz w:val=\"32\"/></w:rPr>"
    : "";
  const paragraphProps = isEpisodeHeading
    ? "<w:pPr><w:spacing w:before=\"240\" w:after=\"120\"/></w:pPr>"
    : "<w:pPr><w:spacing w:after=\"80\"/></w:pPr>";
  return [
    "<w:p>",
    paragraphProps,
    "<w:r>",
    runProps,
    `<w:t xml:space="preserve">${escapeXml(line)}</w:t>`,
    "</w:r>",
    "</w:p>",
  ].join("");
}

function documentXml(title: string, text: string): string {
  const paragraphs = [
    paragraphXml(title),
    "<w:p/>",
    ...text.split(/\r?\n/).map(paragraphXml),
  ].join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:xml="http://www.w3.org/XML/1998/namespace">
  <w:body>
    ${paragraphs}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>`;
}

function contentTypesXml(): string {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>`;
}

function rootRelsXml(): string {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>`;
}

function corePropsXml(title: string): string {
  const now = new Date().toISOString();
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>${escapeXml(title)}</dc:title>
  <dc:creator>Novel-to-Drama</dc:creator>
  <cp:lastModifiedBy>Novel-to-Drama</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">${now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">${now}</dcterms:modified>
</cp:coreProperties>`;
}

function appPropsXml(): string {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Novel-to-Drama</Application>
</Properties>`;
}

export async function buildEpisodeWordDocument(
  title: string,
  text: string
): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const output = new PassThrough();
    const archive = archiver("zip", { zlib: { level: 9 } });
    const chunks: Buffer[] = [];

    output.on("data", (chunk: Buffer) => chunks.push(Buffer.from(chunk)));
    output.on("end", () => resolve(Buffer.concat(chunks)));
    output.on("error", reject);
    archive.on("error", reject);

    archive.pipe(output);
    archive.append(contentTypesXml(), { name: "[Content_Types].xml" });
    archive.append(rootRelsXml(), { name: "_rels/.rels" });
    archive.append(documentXml(title, text), { name: "word/document.xml" });
    archive.append(corePropsXml(title), { name: "docProps/core.xml" });
    archive.append(appPropsXml(), { name: "docProps/app.xml" });
    void archive.finalize();
  });
}
