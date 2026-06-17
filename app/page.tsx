import Link from "next/link";
import { Shield, Zap, ArrowRight } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-5 max-w-6xl mx-auto w-full">
        <div className="flex items-center gap-2 font-bold text-xl">
          <div className="w-9 h-9 rounded-xl bg-teal flex items-center justify-center text-[#001a18]">V</div>
          Payfin
        </div>
        <div className="flex gap-3">
          <Link href="/login" className="btn-ghost">Sign in</Link>
          <Link href="/register" className="btn-primary">Open account</Link>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 rounded-full border border-teal/20 bg-teal-faint px-4 py-1.5 text-xs font-semibold text-teal mb-8">
          <Shield className="w-3.5 h-3.5" /> Bank-grade security · UPI · Real-time
        </div>
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6">
          Bank <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal to-gold">Smarter</span>.
          <br />Move <span className="text-teal">Faster</span>.
        </h1>
        <p className="text-second text-lg max-w-2xl mb-10">
          Payfin is a production-grade digital banking platform with glassmorphic dashboards,
          MFA security, idempotent payments, and real-time balance updates.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link href="/register" className="btn-primary text-base px-8 py-3">
            Get started <ArrowRight className="w-4 h-4" />
          </Link>
          <Link href="/login" className="btn-ghost text-base px-8 py-3">
            <Zap className="w-4 h-4 text-teal" /> Demo login
          </Link>
        </div>
        <p className="mt-8 text-sm text-muted">Demo: username <code className="text-teal">demo</code> · password <code className="text-teal">Demo@12345</code></p>
      </main>
    </div>
  );
}
