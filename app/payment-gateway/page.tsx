"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { api, getToken } from "@/lib/api";

export default function PaymentGatewayPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Array<Record<string, unknown>>>([]);
  const [form, setForm] = useState({ account_id: "", amount: "", merchant: "Amazon India", payment_method: "UPI" });
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.accounts().then((r) => {
      setAccounts(r.accounts);
      const p = r.accounts[0];
      if (p) setForm((f) => ({ ...f, account_id: String(p.id) }));
    });
  }, [router]);

  async function pay() {
    try {
      const res = await api.gatewayPay({
        account_id: Number(form.account_id),
        amount: form.amount,
        merchant: form.merchant,
        payment_method: form.payment_method,
        description: "Online purchase",
      }, crypto.randomUUID());
      setMsg(`Paid! Ref: ${(res as { reference_id?: string }).reference_id}`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold mb-6">Payment Gateway</h1>
      <div className="glass-card p-6 max-w-lg space-y-4">
        <select className="input-field" value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })}>
          {accounts.map((a) => <option key={String(a.id)} value={String(a.id)}>A/C ****{String(a.account_no).slice(-4)}</option>)}
        </select>
        <input className="input-field" placeholder="Merchant" value={form.merchant} onChange={(e) => setForm({ ...form, merchant: e.target.value })} />
        <input className="input-field" placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        <select className="input-field" value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
          {["UPI", "CARD", "NETBANKING", "WALLET"].map((m) => <option key={m}>{m}</option>)}
        </select>
        <button className="btn-primary w-full" onClick={pay}>Pay Now</button>
        {msg && <p className="text-sm text-teal">{msg}</p>}
      </div>
    </AppShell>
  );
}
