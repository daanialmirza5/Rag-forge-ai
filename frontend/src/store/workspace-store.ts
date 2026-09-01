"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface WorkspaceSelectionState {
  organizationId: string | null;
  workspaceId: string | null;
  setOrganization: (organizationId: string | null) => void;
  setWorkspace: (workspaceId: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceSelectionState>()(
  persist(
    (set) => ({
      organizationId: null,
      workspaceId: null,
      setOrganization: (organizationId) => set({ organizationId, workspaceId: null }),
      setWorkspace: (workspaceId) => set({ workspaceId }),
    }),
    { name: "ragforge-workspace-selection" },
  ),
);
