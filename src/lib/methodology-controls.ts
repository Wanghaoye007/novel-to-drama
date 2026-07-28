import type { MethodologyData, MethodologyStatus } from "./methodology";

export type MethodologyCardAction = {
  label: string;
  status: MethodologyStatus;
  variant: "default" | "destructive" | "outline";
};

const statusLabels: Record<MethodologyStatus, string> = {
  draft: "草稿",
  active: "已启用",
  archived: "已归档",
  rejected: "已拒绝",
};

export function methodologyStatusLabel(status: MethodologyStatus): string {
  return statusLabels[status];
}

export function methodologyCardActions(
  status: MethodologyStatus
): MethodologyCardAction[] {
  if (status === "active") {
    return [{ label: "停用", status: "archived", variant: "outline" }];
  }
  if (status === "draft") {
    return [
      { label: "启用", status: "active", variant: "default" },
      { label: "拒绝", status: "rejected", variant: "destructive" },
    ];
  }
  if (status === "archived") {
    return [
      { label: "重新启用", status: "active", variant: "default" },
      { label: "拒绝", status: "rejected", variant: "destructive" },
    ];
  }
  return [
    { label: "重新启用", status: "active", variant: "default" },
    { label: "归档", status: "archived", variant: "outline" },
  ];
}

export function applyMethodologyCardStatus(
  data: MethodologyData,
  id: string,
  status: MethodologyStatus,
  updatedAt = Date.now()
): MethodologyData {
  return {
    ...data,
    cards: data.cards.map((card) =>
      card.id === id ? { ...card, status, updatedAt } : card
    ),
  };
}
