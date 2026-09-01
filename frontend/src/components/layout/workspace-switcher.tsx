"use client";

import { Check, ChevronsUpDown, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateWorkspace, useWorkspaces } from "@/hooks/use-workspaces";
import { cn } from "@/lib/utils";
import { useWorkspaceStore } from "@/store/workspace-store";
import { toast } from "@/store/toast-store";

export function WorkspaceSwitcher({ organizationId }: { organizationId: string }) {
  const router = useRouter();
  const { data: workspaces, isLoading } = useWorkspaces(organizationId);
  const workspaceId = useWorkspaceStore((s) => s.workspaceId);
  const setWorkspace = useWorkspaceStore((s) => s.setWorkspace);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const createWorkspace = useCreateWorkspace(organizationId);

  const current = workspaces?.find((w) => w.id === workspaceId) ?? workspaces?.[0];

  useEffect(() => {
    if (!workspaceId && workspaces && workspaces.length > 0 && workspaces[0]) {
      setWorkspace(workspaces[0].id);
    }
  }, [workspaceId, workspaces, setWorkspace]);

  async function handleCreate() {
    if (!name.trim()) return;
    try {
      const workspace = await createWorkspace.mutateAsync({ name });
      setWorkspace(workspace.id);
      setCreateOpen(false);
      setName("");
      router.push(`/workspaces/${workspace.id}/documents`);
    } catch {
      toast({ title: "Could not create workspace", variant: "destructive" });
    }
  }

  return (
    <Dialog open={createOpen} onOpenChange={setCreateOpen}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            className="w-full justify-between"
            disabled={isLoading}
          >
            <span className="truncate">{current?.name ?? "Select workspace"}</span>
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {workspaces?.map((workspace) => (
            <DropdownMenuItem
              key={workspace.id}
              onSelect={() => {
                setWorkspace(workspace.id);
                router.push(`/workspaces/${workspace.id}/documents`);
              }}
              className="flex items-center justify-between"
            >
              <span className="truncate">{workspace.name}</span>
              {workspace.id === current?.id && <Check className="h-4 w-4" />}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setCreateOpen(true)} className={cn("gap-2")}>
            <Plus className="h-4 w-4" /> New workspace
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a workspace</DialogTitle>
          <DialogDescription>
            A workspace is an isolated knowledge base — documents and chats in one workspace
            never surface in another.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="workspace-name">Name</Label>
          <Input
            id="workspace-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Engineering Docs"
          />
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} disabled={createWorkspace.isPending || !name.trim()}>
            {createWorkspace.isPending ? "Creating…" : "Create workspace"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
