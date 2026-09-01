import { apiFetch } from "@/lib/api/client";
import type { TokenPair, User } from "@/types/api";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

export function register(payload: RegisterPayload): Promise<User> {
  return apiFetch<User>("/auth/register", { method: "POST", body: payload, skipAuth: true });
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? "Login failed");
  }
  return res.json();
}

export function logoutRequest(refreshToken: string): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST", body: { refresh_token: refreshToken } });
}

export function getCurrentUser(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

export function updateProfile(payload: { full_name?: string }): Promise<User> {
  return apiFetch<User>("/users/me", { method: "PATCH", body: payload });
}

export function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  return apiFetch<void>("/users/me/change-password", { method: "POST", body: payload });
}
