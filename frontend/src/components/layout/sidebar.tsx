"use client";

import { BarChart3, FileText, MessageSquare, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { UserMenu } from "@/components/layout/user-menu";
import { WorkspaceSwitcher } from "@/components/layout/workspace-switcher";
import { cn } from "@/lib/utils";
import { useWorkspaceStore } from "@/store/workspace-store";

interface NavItem {
  href: (workspaceId: string) => string;
  label: string;
  icon: typeof FileText;
}

const navItems: NavItem[] = [
  { href: (id) => `/workspaces/${id}/chat`, label: "Chat", icon: MessageSquare },
  { href: (id) => `/workspaces/${id}/documents`, label: "Documents", icon: FileText },
  { href: (id) => `/workspaces/${id}/analytics`, label: "Analytics", icon: BarChart3 },
  { href: (id) => `/workspaces/${id}/settings`, label: "Workspace settings", icon: Settings },
];

export function Sidebar({ organizationId }: { organizationId: string }) {
  const pathname = usePathname();
  const workspaceId = useWorkspaceStore((s) => s.workspaceId);

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r bg-card">
      <div className="p-3">
        <Link href="/dashboard" className="mb-3 block px-1 text-lg font-semibold">
          RAGForge
        </Link>
        <WorkspaceSwitcher organizationId={organizationId} />
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {workspaceId &&
          navItems.map((item) => {
            const href = item.href(workspaceId);
            const active = pathname?.startsWith(href);
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
      </nav>

      <div className="border-t p-3">
        <UserMenu />
      </div>
    </aside>
  );
}
