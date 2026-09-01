import type { Metadata } from "next";

import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/toaster";

import "./globals.css";

export const metadata: Metadata = {
  title: "RAGForge AI",
  description: "Ask questions over your team's documents, with cited answers.",
};

// This app is a client-side auth-gated dashboard: every page's content
// depends on Zustand state hydrated from localStorage at runtime, so there's
// nothing meaningful to statically prerender — and `persist.hasHydrated()`
// (used by `useAuthHydrated`) isn't safe to call during Next.js's build-time
// static generation pass, since `localStorage` doesn't exist there. Forcing
// dynamic rendering site-wide from the root layout sidesteps both issues.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
