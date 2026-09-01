"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useWorkspaces } from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/store/workspace-store";

export default function DashboardIndexPage() {
  const router = useRouter();
  const organizationId = useWorkspaceStore((s) => s.organizationId);
  const workspaceId = useWorkspaceStore((s) => s.workspaceId);
  const { data: workspaces, isLoading } = useWorkspaces(organizationId);

  useEffect(() => {
    if (workspaceId) {
      router.replace(`/workspaces/${workspaceId}/chat`);
      return;
    }
    if (!isLoading && workspaces && workspaces.length > 0 && workspaces[0]) {
      router.replace(`/workspaces/${workspaces[0].id}/chat`);
    }
  }, [workspaceId, workspaces, isLoading, router]);

  if (!isLoading && workspaces && workspaces.length === 0) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 text-center">
        <h1 className="text-lg font-semibold">Create your first workspace</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Use the workspace switcher in the sidebar to create one — it&apos;s where your documents
          and chats live.
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
      Loading…
    </div>
  );
}
