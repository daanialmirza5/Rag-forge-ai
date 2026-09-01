"use client";

import { useState } from "react";

import { AdminAuditLogTab } from "@/components/admin/admin-audit-log-tab";
import { AdminOrganizationsTab } from "@/components/admin/admin-organizations-tab";
import { AdminUsersTab } from "@/components/admin/admin-users-tab";
import { UsageDashboard } from "@/components/charts/usage-dashboard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePlatformUsage } from "@/hooks/use-admin";
import { useAuthStore } from "@/store/auth-store";

export default function AdminPage() {
  const user = useAuthStore((s) => s.user);
  const [lookbackDays, setLookbackDays] = useState(30);
  const { data: usage, isLoading } = usePlatformUsage(lookbackDays);

  if (!user?.is_superuser) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8 text-sm text-muted-foreground">
        You don&apos;t have access to this page.
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Admin</h1>
        <p className="text-sm text-muted-foreground">
          Platform-wide visibility across every organization. Superuser only.
        </p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="organizations">Organizations</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="audit-log">Audit log</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <UsageDashboard
            summary={usage}
            isLoading={isLoading}
            lookbackDays={lookbackDays}
            onLookbackDaysChange={setLookbackDays}
          />
        </TabsContent>

        <TabsContent value="organizations">
          <AdminOrganizationsTab />
        </TabsContent>

        <TabsContent value="users">
          <AdminUsersTab />
        </TabsContent>

        <TabsContent value="audit-log">
          <AdminAuditLogTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
