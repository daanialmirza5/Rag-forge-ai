import { apiFetch } from "@/lib/api/client";
import type { Organization, OrganizationMember } from "@/types/api";

export function listOrganizations(): Promise<Organization[]> {
  return apiFetch<Organization[]>("/organizations");
}

export function getOrganization(organizationId: string): Promise<Organization> {
  return apiFetch<Organization>(`/organizations/${organizationId}`);
}

export function listOrganizationMembers(organizationId: string): Promise<OrganizationMember[]> {
  return apiFetch<OrganizationMember[]>(`/organizations/${organizationId}/members`);
}

export function removeOrganizationMember(organizationId: string, memberId: string): Promise<void> {
  return apiFetch<void>(`/organizations/${organizationId}/members/${memberId}`, {
    method: "DELETE",
  });
}
