"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { api, getToken } from "@/lib/api";

export default function SecurityPage() {
  const router = useRouter();
  const [qr, setQr] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!getToken()) router.push("/login");
  }, [router]);

  async function setupMfa() {
    const res = await api.mfaSetup();
    setSecret(res.secret);
    setQr(res.qr_base64);
  }

  async function enableMfa() {
    const res = await api.mfaEnable(secret, code);
    setMsg((res as { message?: string }).message || "MFA enabled");
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold mb-6">Security Center</h1>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h2 className="font-semibold mb-4">Two-Factor Authentication (TOTP)</h2>
          <button className="btn-primary mb-4" onClick={setupMfa}>Setup MFA</button>
          {qr && <img src={`data:image/png;base64,${qr}`} alt="MFA QR" className="w-48 h-48 mx-auto mb-4 rounded-xl" />}
          {secret && (
            <>
              <input className="input-field mb-3" placeholder="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} />
              <button className="btn-ghost w-full" onClick={enableMfa}>Enable MFA</button>
            </>
          )}
          {msg && <p className="text-teal text-sm mt-4">{msg}</p>}
        </div>
        <div className="glass-card p-6">
          <h2 className="font-semibold mb-4">Security Checklist</h2>
          <ul className="space-y-2 text-sm text-second">
            <li className="text-green-400">✓ bcrypt password hashing (cost 12)</li>
            <li className="text-green-400">✓ JWT HS256 sessions</li>
            <li className="text-green-400">✓ Idempotency keys on payments</li>
            <li className="text-green-400">✓ Immutable audit logs</li>
            <li className="text-green-400">✓ HMAC webhook verification</li>
            <li className="text-green-400">✓ Live IFSC validation</li>
          </ul>
        </div>
      </div>
    </AppShell>
  );
}
