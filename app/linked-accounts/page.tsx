"use client";

import { AppShell } from "@/components/app-shell";

export default function LinkedAccountsPage() {
  return (
    <AppShell>
      <h1 className="text-2xl font-bold mb-6">Linked Bank Accounts</h1>
      <div className="glass-card p-6">
        <p className="text-second text-sm">Link external bank accounts with live IFSC verification via Razorpay IFSC API.</p>
        <p className="text-muted text-xs mt-4">Use POST /api/linked-accounts/add from the API or extend this UI.</p>
      </div>
    </AppShell>
  );
}
