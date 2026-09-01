"use client";

import { useAuthStore } from "@/store/auth-store";
import type { ApiErrorBody } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** Decodes a JWT payload without verifying the signature — fine for a
 * client-side "is this token about to expire" check; the server is the
 * actual authority on validity. */
function decodeJwtExpiry(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

const EXPIRY_BUFFER_MS = 30_000;

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setTokens, logout } = useAuthStore.getState();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          logout();
          return null;
        }
        const tokens = await res.json();
        setTokens(tokens.access_token, tokens.refresh_token);
        return tokens.access_token as string;
      } catch {
        logout();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

/** Returns a currently-valid access token, refreshing first if it's expired
 * or about to expire. Used before both regular requests and SSE streams
 * (which can't transparently retry mid-stream on a 401). */
export async function getValidAccessToken(): Promise<string | null> {
  const { accessToken } = useAuthStore.getState();
  if (!accessToken) return null;

  const expiresAt = decodeJwtExpiry(accessToken);
  if (expiresAt !== null && expiresAt - Date.now() < EXPIRY_BUFFER_MS) {
    return refreshAccessToken();
  }
  return accessToken;
}

async function parseErrorBody(res: Response): Promise<ApiErrorBody["error"]> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    return body.error;
  } catch {
    return { code: "unknown_error", message: res.statusText || "Request failed" };
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  isFormData?: boolean;
  skipAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, isFormData, skipAuth, headers, ...rest } = options;

  const doFetch = async (token: string | null): Promise<Response> => {
    const finalHeaders = new Headers(headers);
    if (!isFormData && body !== undefined) {
      finalHeaders.set("Content-Type", "application/json");
    }
    if (token) {
      finalHeaders.set("Authorization", `Bearer ${token}`);
    }
    return fetch(`${API_BASE_URL}/api/v1${path}`, {
      ...rest,
      headers: finalHeaders,
      body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
    });
  };

  const token = skipAuth ? null : await getValidAccessToken();
  let res = await doFetch(token);

  if (res.status === 401 && !skipAuth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      res = await doFetch(refreshed);
    }
  }

  if (!res.ok) {
    const error = await parseErrorBody(res);
    throw new ApiError(res.status, error.code, error.message, error.details);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export { API_BASE_URL };
