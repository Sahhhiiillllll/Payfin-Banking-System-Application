"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { api, getToken } from "@/lib/api";
import { formatINR } from "@/lib/utils";

function idemKey() {
  return crypto.randomUUID();
}

export default function UpiPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Array<Record<string, unknown>>>([]);
  const [form, setForm] = useState({ from_account_id: "", to_upi_id: "", amount: "", note: "" });
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.accounts().then((r) => {
      setAccounts(r.accounts);
      const p = r.accounts.find((a) => a.is_primary) || r.accounts[0];
      if (p) setForm((f) => ({ ...f, from_account_id: String(p.id) }));
    });
  }, [router]);

  async function send() {
    setLoading(true);
    setStatus("");
    try {
      const res = await api.upiSend({
        from_account_id: Number(form.from_account_id),
        to_upi_id: form.to_upi_id,
        amount: form.amount,
        note: form.note,
      }, idemKey());
      setStatus(`Success! Ref: ${(res as { reference_id?: string }).reference_id}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Payment failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold mb-6">UPI Payments</h1>
      <div className="glass-card p-6 max-w-lg space-y-4">
        <select className="input-field" value={form.from_account_id} onChange={(e) => setForm({ ...form, from_account_id: e.target.value })}>
          {accounts.map((a) => (
            <option key={String(a.id)} value={String(a.id)}>****{String(a.account_no).slice(-4)} — ₹{Number(a.balance).toFixed(2)}</option>
          ))}
        </select>
        <input className="input-field" placeholder="Payee UPI ID (e.g. demo@payfin)" value={form.to_upi_id} onChange={(e) => setForm({ ...form, to_upi_id: e.target.value })} />
        <input className="input-field" placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        <input className="input-field" placeholder="Note (optional)" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
        <button className="btn-primary w-full" onClick={send} disabled={loading}>{loading ? "Processing…" : "Send UPI Payment"}</button>
        {status && <p className="text-sm text-teal">{status}</p>}
      </div>
    </AppShell>
  );
}
