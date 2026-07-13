import { schema } from "@/db/client";

type ProjectRow = typeof schema.projects.$inferSelect;

export function projectWorkspaceView(project: ProjectRow) {
  return {
    id: project.id,
    name: project.name,
    targetEpisodeCount: project.targetEpisodeCount,
    status: project.status,
    metaJson: project.metaJson,
  };
}
