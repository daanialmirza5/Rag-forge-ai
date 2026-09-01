"use client";

import { Trash2 } from "lucide-react";
import { use, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAddWorkspaceMember,
  useRemoveWorkspaceMember,
  useWorkspaceMembers,
} from "@/hooks/use-workspace-members";
import { ApiError } from "@/lib/api/client";
import { useWorkspaceStore } from "@/store/workspace-store";
import { toast } from "@/store/toast-store";

export default function WorkspaceSettingsPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = use(params);
  const organizationId = useWorkspaceStore((s) => s.organizationId)!;
  const { data: members, isLoading } = useWorkspaceMembers(organizationId, workspaceId);
  const addMember = useAddWorkspaceMember(organizationId, workspaceId);
  const removeMember = useRemoveWorkspaceMember(organizationId, workspaceId);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"editor" | "viewer">("viewer");

  async function handleAdd() {
    if (!email.trim()) return;
    try {
      await addMember.mutateAsync({ user_email: email.trim(), role });
      setEmail("");
      toast({ title: "Member added" });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Could not add member";
      toast({ title: "Could not add member", description: message, variant: "destructive" });
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Workspace settings</h1>
        <p className="text-sm text-muted-foreground">Manage who has access to this workspace.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Add a member</CardTitle>
          <CardDescription>They must already have a RAGForge account.</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Input
            placeholder="teammate@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1"
          />
          <Select value={role} onValueChange={(v) => setRole(v as "editor" | "viewer")}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="viewer">Viewer</SelectItem>
              <SelectItem value="editor">Editor</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleAdd} disabled={addMember.isPending || !email.trim()}>
            Add
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Members</CardTitle>
        </CardHeader>
        <CardContent className="divide-y p-0">
          {isLoading && <p className="p-4 text-sm text-muted-foreground">Loading…</p>}
          {members?.map((member) => (
            <div key={member.id} className="flex items-center justify-between px-6 py-3">
              <div>
                <p className="text-sm font-medium">{member.user_full_name || member.user_email}</p>
                <p className="text-xs capitalize text-muted-foreground">{member.role}</p>
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
    </div>
  );
}
