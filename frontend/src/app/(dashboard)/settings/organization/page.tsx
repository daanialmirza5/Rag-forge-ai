"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UsageDashboard } from "@/components/charts/usage-dashboard";
import { useOrganizationUsage } from "@/hooks/use-analytics";
import { useOrganizations } from "@/hooks/use-organizations";
import { useOrganizationMembers, useRemoveOrganizationMember } from "@/hooks/use-organization-members";
import { useAuthStore } from "@/store/auth-store";
import { useWorkspaceStore } from "@/store/workspace-store";

export default function OrganizationSettingsPage() {
  const organizationId = useWorkspaceStore((s) => s.organizationId)!;
  const currentUser = useAuthStore((s) => s.user);
  const { data: organizations } = useOrganizations();
  const { data: members, isLoading } = useOrganizationMembers(organizationId);
  const removeMember = useRemoveOrganizationMember(organizationId);
  const organization = organizations?.find((o) => o.id === organizationId);

  const myMembership = members?.find((m) => m.user_id === currentUser?.id);
  const canViewUsage = myMembership?.role === "owner" || myMembership?.role === "admin";

  const [lookbackDays, setLookbackDays] = useState(30);
  const { data: usage, isLoading: usageLoading } = useOrganizationUsage(
    organizationId,
    lookbackDays,
    canViewUsage,
  );

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Organization</h1>
        <p className="text-sm text-muted-foreground">
          Billing and membership for your organization.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{organization?.name ?? "…"}</CardTitle>
          <CardDescription>Plan: {organization?.plan_tier ?? "…"}</CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Members</CardTitle>
          <CardDescription>
            New members join by being added to a workspace within this organization.
          </CardDescription>
        </CardHeader>
        <CardContent className="divide-y p-0">
          {isLoading && <p className="p-4 text-sm text-muted-foreground">Loading…</p>}
          {members?.map((member) => (
            <div key={member.id} className="flex items-center justify-between px-6 py-3">
              <div>
                <p className="text-sm font-medium">{member.user_full_name || member.user_email}</p>
                <Badge variant="secondary" className="mt-1 capitalize">
                  {member.role}
                </Badge>
              </div>
              {member.role !== "owner" && (
                <button
                  onClick={() => removeMember.mutate(member.id)}
                  className="text-muted-foreground hover:text-destructive"
                  aria-label="Remove member"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {canViewUsage && (
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-base font-semibold">Usage across all workspaces</h2>
            <p className="text-sm text-muted-foreground">
              Visible to organization owners and admins only.
            </p>
          </div>
          <UsageDashboard
            summary={usage}
            isLoading={usageLoading}
            lookbackDays={lookbackDays}
            onLookbackDaysChange={setLookbackDays}
          />
        </div>
      )}
    </div>
  );
}
