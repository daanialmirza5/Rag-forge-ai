import { apiFetch } from "@/lib/api/client";
import type { Workspace, WorkspaceMember } from "@/types/api";

export function listWorkspaces(organizationId: string): Promise<Workspace[]> {
  return apiFetch<Workspace[]>(`/organizations/${organizationId}/workspaces`);
}

export function getWorkspace(organizationId: string, workspaceId: string): Promise<Workspace> {
  return apiFetch<Workspace>(`/organizations/${organizationId}/workspaces/${workspaceId}`);
}

export function createWorkspace(
  organizationId: string,
  payload: { name: string; description?: string },
): Promise<Workspace> {
  return apiFetch<Workspace>(`/organizations/${organizationId}/workspaces`, {
    method: "POST",
    body: payload,
  });
}

export function updateWorkspace(
  organizationId: string,
  workspaceId: string,
  payload: { name?: string; description?: string },
): Promise<Workspace> {
  return apiFetch<Workspace>(`/organizations/${organizationId}/workspaces/${workspaceId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function listWorkspaceMembers(
  organizationId: string,
  workspaceId: string,
): Promise<WorkspaceMember[]> {
  return apiFetch<WorkspaceMember[]>(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members`,
  );
}

export function addWorkspaceMember(
  organizationId: string,
  workspaceId: string,
  payload: { user_email: string; role: "owner" | "editor" | "viewer" },
): Promise<WorkspaceMember> {
  return apiFetch<WorkspaceMember>(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members`,
    { method: "POST", body: payload },
  );
}

export function removeWorkspaceMember(
  organizationId: string,
  workspaceId: string,
  memberId: string,
): Promise<void> {
  return apiFetch<void>(
    `/organizations/${organizationId}/workspaces/${workspaceId}/members/${memberId}`,
    { method: "DELETE" },
  );
}
