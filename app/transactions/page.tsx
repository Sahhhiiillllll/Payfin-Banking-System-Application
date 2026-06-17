"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { api, getToken } from "@/lib/api";
import { formatINR } from "@/lib/utils";

export default function TransactionsPage() {
  const router = useRouter();
  const [txns, setTxns] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.transactions(100).then((r) => setTxns(r.transactions)).catch(() => router.push("/login"));
  }, [router]);

  return (
    <AppShell>
      <h1 className="text-2xl font-bold mb-6">Transaction History</h1>
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-bg-elevated text-muted text-xs uppercase">
              <tr>
                <th className="text-left p-4">Date</th>
                <th className="text-left p-4">Type</th>
                <th className="text-left p-4">Description</th>
                <th className="text-right p-4">Amount</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t) => (
                <tr key={String(t.id)} className="border-t border-white/5 hover:bg-white/[0.02]">
                  <td className="p-4 font-mono text-xs">{String(t.created_at).slice(0, 10)}</td>
                  <td className={`p-4 font-semibold ${t.txn_type === "CREDIT" ? "text-green-400" : "text-red-400"}`}>{String(t.txn_type)}</td>
                  <td className="p-4 text-second">{String(t.description)}</td>
                  <td className="p-4 text-right font-mono">{formatINR(Number(t.amount))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
