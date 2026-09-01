"use client";

import { LogOut, Settings, ShieldCheck, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logoutRequest } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth-store";

function initials(name: string, email: string): string {
  const source = name.trim() || email;
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0]![0]}${parts[1]![0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function UserMenu() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const logout = useAuthStore((s) => s.logout);

  async function handleLogout() {
    if (refreshToken) {
      await logoutRequest(refreshToken).catch(() => undefined);
    }
    logout();
    router.replace("/login");
  }

  if (!user) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex w-full items-center gap-2 rounded-md p-2 text-left text-sm hover:bg-accent">
          <Avatar className="h-8 w-8">
            <AvatarFallback>{initials(user.full_name, user.email)}</AvatarFallback>
          </Avatar>
          <span className="flex-1 truncate">{user.full_name || user.email}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel className="truncate">{user.email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/settings/account" className="flex items-center gap-2">
            <User className="h-4 w-4" /> Account
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/settings/organization" className="flex items-center gap-2">
            <Settings className="h-4 w-4" /> Organization
          </Link>
        </DropdownMenuItem>
        {user.is_superuser && (
          <DropdownMenuItem asChild>
            <Link href="/admin" className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" /> Admin panel
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleLogout} className="flex items-center gap-2 text-destructive">
          <LogOut className="h-4 w-4" /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
