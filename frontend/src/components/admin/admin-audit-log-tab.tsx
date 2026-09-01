"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuditLogs } from "@/hooks/use-admin";

const PAGE_SIZE = 50;

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function AdminAuditLogTab() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useAuditLogs(page, PAGE_SIZE);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted-foreground">
              <tr>
                <th className="px-6 py-2 font-medium">Time</th>
                <th className="px-6 py-2 font-medium">Action</th>
                <th className="px-6 py-2 font-medium">Resource</th>
                <th className="px-6 py-2 font-medium">IP address</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading && (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-muted-foreground">
                    No audit events recorded yet.
                  </td>
                </tr>
              )}
              {data?.items.map((log) => (
                <tr key={log.id}>
                  <td className="whitespace-nowrap px-6 py-2 tabular-nums text-muted-foreground">
                    {formatTimestamp(log.created_at)}
                  </td>
                  <td className="px-6 py-2 font-mono text-xs">{log.action}</td>
                  <td className="px-6 py-2 text-muted-foreground">
                    {log.resource_type}
                    {log.resource_id ? ` · ${log.resource_id.slice(0, 8)}` : ""}
                  </td>
                  <td className="px-6 py-2 text-muted-foreground">{log.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && data.total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t px-6 py-3 text-sm text-muted-foreground">
            <span>
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
