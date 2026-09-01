"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { changePassword, updateProfile } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "@/store/toast-store";

export default function AccountSettingsPage() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  async function handleSaveProfile() {
    setSavingProfile(true);
    try {
      const updated = await updateProfile({ full_name: fullName });
      setUser(updated);
      toast({ title: "Profile updated" });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Could not update profile";
      toast({ title: "Update failed", description: message, variant: "destructive" });
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleChangePassword() {
    if (!currentPassword || !newPassword) return;
    setSavingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      toast({ title: "Password changed" });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Could not change password";
      toast({ title: "Password change failed", description: message, variant: "destructive" });
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) return null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Account settings</h1>
        <p className="text-sm text-muted-foreground">Manage your profile and password.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
          <CardDescription>{user.email}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <Button
            onClick={handleSaveProfile}
            disabled={savingProfile || fullName === user.full_name}
            className="self-start"
          >
            {savingProfile ? "Saving…" : "Save"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change password</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="current_password">Current password</Label>
            <Input
              id="current_password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new_password">New password</Label>
            <Input
              id="new_password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <Button
            onClick={handleChangePassword}
            disabled={savingPassword || !currentPassword || !newPassword}
            className="self-start"
          >
            {savingPassword ? "Updating…" : "Update password"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
