"use client";

import { use, useState } from "react";

import { UsageDashboard } from "@/components/charts/usage-dashboard";
import { useWorkspaceUsage } from "@/hooks/use-analytics";

export default function WorkspaceAnalyticsPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = use(params);
  const [lookbackDays, setLookbackDays] = useState(30);
  const { data, isLoading } = useWorkspaceUsage(workspaceId, lookbackDays);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Token usage, estimated cost, and activity for this workspace.
        </p>
      </div>

      <UsageDashboard
        summary={data}
        isLoading={isLoading}
        lookbackDays={lookbackDays}
        onLookbackDaysChange={setLookbackDays}
      />
    </div>
  );
}
