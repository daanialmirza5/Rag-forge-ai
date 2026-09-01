"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import { useAuthHydrated } from "@/hooks/use-auth-hydrated";
import { useOrganizations } from "@/hooks/use-organizations";
import { useAuthStore } from "@/store/auth-store";
import { useWorkspaceStore } from "@/store/workspace-store";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hydrated = useAuthHydrated();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: organizations } = useOrganizations();
  const organizationId = useWorkspaceStore((s) => s.organizationId);
  const setOrganization = useWorkspaceStore((s) => s.setOrganization);

  useEffect(() => {
    if (hydrated && !accessToken) {
      router.replace("/login");
    }
  }, [hydrated, accessToken, router]);

  useEffect(() => {
    if (!organizationId && organizations && organizations.length > 0 && organizations[0]) {
      setOrganization(organizations[0].id);
    }
  }, [organizationId, organizations, setOrganization]);

  if (!hydrated || !accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!organizationId) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Setting up your workspace…
      </div>
    );
  }

  return (
    <div className="flex">
      <Sidebar organizationId={organizationId} />
      <main className="min-h-screen flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
