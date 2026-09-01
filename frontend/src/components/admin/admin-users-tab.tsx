"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAdminUsers, useUpdateUserActive, useUpdateUserSuperuser } from "@/hooks/use-admin";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "@/store/toast-store";

export function AdminUsersTab() {
  const currentUser = useAuthStore((s) => s.user);
  const { data: users, isLoading } = useAdminUsers();
  const updateActive = useUpdateUserActive();
  const updateSuperuser = useUpdateUserSuperuser();

  async function handleToggleActive(userId: string, isActive: boolean) {
    try {
      await updateActive.mutateAsync({ userId, isActive: !isActive });
      toast({ title: !isActive ? "User activated" : "User deactivated" });
    } catch {
      toast({ title: "Could not update user", variant: "destructive" });
    }
  }

  async function handleToggleSuperuser(userId: string, isSuperuser: boolean) {
    try {
      await updateSuperuser.mutateAsync({ userId, isSuperuser: !isSuperuser });
      toast({ title: !isSuperuser ? "Superuser access granted" : "Superuser access revoked" });
    } catch {
      toast({ title: "Could not update user", variant: "destructive" });
    }
  }

  return (
    <Card>
      <CardContent className="divide-y p-0">
        {isLoading && <p className="p-4 text-sm text-muted-foreground">Loading…</p>}
        {users?.map((user) => {
          const isSelf = user.id === currentUser?.id;
          return (
            <div key={user.id} className="flex items-center justify-between gap-4 px-6 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user.full_name || user.email}</p>
                <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                <div className="mt-1 flex gap-1.5">
                  {!user.is_active && <Badge variant="destructive">Deactivated</Badge>}
                  {user.is_superuser && <Badge variant="secondary">Superuser</Badge>}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isSelf && user.is_superuser}
                  title={isSelf && user.is_superuser ? "You cannot revoke your own superuser access" : undefined}
                  onClick={() => handleToggleSuperuser(user.id, user.is_superuser)}
                >
                  {user.is_superuser ? "Revoke admin" : "Make admin"}
                </Button>
                <Button
                  size="sm"
                  variant={user.is_active ? "outline" : "default"}
                  disabled={isSelf && user.is_active}
                  title={isSelf && user.is_active ? "You cannot deactivate your own account" : undefined}
                  onClick={() => handleToggleActive(user.id, user.is_active)}
                >
                  {user.is_active ? "Deactivate" : "Activate"}
                </Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
