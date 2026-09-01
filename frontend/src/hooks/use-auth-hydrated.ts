"use client";

import { useEffect, useState } from "react";

import { useAuthStore } from "@/store/auth-store";

/** Auth tokens are persisted to localStorage (not cookies), so Next.js
 * middleware — which only sees cookies — can't gate routes server-side.
 * Route guards instead run client-side after the Zustand `persist`
 * middleware finishes reading localStorage; this hook exposes that
 * "have we checked yet" boundary so guards don't redirect to /login on a
 * false negative during the brief pre-hydration window.
 *
 * The initial state must always be `false` here, and `persist.hasHydrated()`
 * must only ever be read inside `useEffect` — Next.js still runs an initial
 * server-side render pass for "use client" components even under
 * `force-dynamic`, and `persist`'s internal state isn't safely readable in
 * that server context (no `localStorage`). `useEffect` never runs during
 * SSR, so gating the read behind it keeps the server/client initial render
 * identical (no hydration mismatch) and avoids touching `persist` off the
 * client entirely. */
export function useAuthHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (useAuthStore.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsubscribe = useAuthStore.persist.onFinishHydration(() => setHydrated(true));
    return unsubscribe;
  }, []);

  return hydrated;
}
