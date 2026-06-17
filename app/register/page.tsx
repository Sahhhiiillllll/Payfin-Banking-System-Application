"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    username: "", full_name: "", email: "", phone: "", password: "", confirm_password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.register(form);
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="glass-card w-full max-w-lg p-8">
        <h1 className="text-2xl font-bold mb-1">Create account</h1>
        <p className="text-second text-sm mb-8">Join Payfin in minutes</p>
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <input className="input-field sm:col-span-1" placeholder="Username" value={form.username} onChange={(e) => update("username", e.target.value)} required />
          <input className="input-field sm:col-span-1" placeholder="Full name" value={form.full_name} onChange={(e) => update("full_name", e.target.value)} required />
          <input className="input-field sm:col-span-2" type="email" placeholder="Email" value={form.email} onChange={(e) => update("email", e.target.value)} required />
          <input className="input-field sm:col-span-2" placeholder="Phone (optional)" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
          <input className="input-field sm:col-span-1" type="password" placeholder="Password" value={form.password} onChange={(e) => update("password", e.target.value)} required />
          <input className="input-field sm:col-span-1" type="password" placeholder="Confirm password" value={form.confirm_password} onChange={(e) => update("confirm_password", e.target.value)} required />
          {error && <p className="text-red-400 text-sm sm:col-span-2">{error}</p>}
          <button type="submit" className="btn-primary sm:col-span-2 w-full" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>
        <p className="text-center text-sm text-muted mt-6">
          Have an account? <Link href="/login" className="text-teal hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
