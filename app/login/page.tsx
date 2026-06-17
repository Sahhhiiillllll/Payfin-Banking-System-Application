"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("Demo@12345");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.login({ username, password, mfa_code: mfaCode || undefined });
      if (res.token) setToken(res.token);
      if (res.mfa_required) {
        setMfaRequired(true);
        return;
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="glass-card w-full max-w-md p-8">
        <h1 className="text-2xl font-bold mb-1">Welcome back</h1>
        <p className="text-second text-sm mb-8">Sign in to Payfin</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!mfaRequired ? (
            <>
              <input className="input-field" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
              <input className="input-field" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </>
          ) : (
            <input className="input-field" placeholder="6-digit MFA code" value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} maxLength={6} required />
          )}
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Signing in…" : mfaRequired ? "Verify MFA" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-6">
          No account? <Link href="/register" className="text-teal hover:underline">Register</Link>
        </p>
      </div>
    </div>
  );
}
