"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAdminOrganizations, useUpdateOrganizationPlan } from "@/hooks/use-admin";
import { toast } from "@/store/toast-store";

const PLAN_TIERS = ["free", "pro", "enterprise"];

export function AdminOrganizationsTab() {
  const { data: organizations, isLoading } = useAdminOrganizations();
  const updatePlan = useUpdateOrganizationPlan();

  async function handlePlanChange(organizationId: string, planTier: string) {
    try {
      await updatePlan.mutateAsync({ organizationId, planTier });
      toast({ title: "Plan updated" });
    } catch {
      toast({ title: "Could not update plan", variant: "destructive" });
    }
  }

  return (
    <Card>
      <CardContent className="divide-y p-0">
        {isLoading && <p className="p-4 text-sm text-muted-foreground">Loading…</p>}
        {organizations?.length === 0 && (
          <p className="p-4 text-sm text-muted-foreground">No organizations yet.</p>
        )}
        {organizations?.map((org) => (
          <div key={org.id} className="flex items-center justify-between gap-4 px-6 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{org.name}</p>
              <p className="text-xs text-muted-foreground">
                {org.member_count} member{org.member_count === 1 ? "" : "s"} ·{" "}
                {org.workspace_count} workspace{org.workspace_count === 1 ? "" : "s"}
              </p>
            </div>
            <Select value={org.plan_tier} onValueChange={(v) => handlePlanChange(org.id, v)}>
              <SelectTrigger className="w-36 shrink-0">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PLAN_TIERS.map((tier) => (
                  <SelectItem key={tier} value={tier} className="capitalize">
                    {tier}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
