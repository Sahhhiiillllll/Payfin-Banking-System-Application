"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, ArrowLeftRight, Zap, Link2, CreditCard, Shield, LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api, clearToken } from "@/lib/api";
import { useRouter } from "next/navigation";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/upi", label: "UPI Pay", icon: Zap },
  { href: "/linked-accounts", label: "Linked Banks", icon: Link2 },
  { href: "/payment-gateway", label: "Payments", icon: CreditCard },
  { href: "/security", label: "Security", icon: Shield },
];

export function AppShell({ children, userName }: { children: React.ReactNode; userName?: string }) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    try { await api.logout(); } catch { /* ignore */ }
    clearToken();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="glass-sidebar hidden lg:flex w-[260px] flex-col fixed inset-y-0 left-0 z-40">
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center gap-2 font-bold text-lg">
            <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center text-[#001a18] text-sm">V</div>
            Payfin
          </div>
          {userName && <p className="text-xs text-muted mt-2 truncate">Hi, {userName}</p>}
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                pathname === href
                  ? "bg-teal-faint text-teal border border-teal/20"
                  : "text-second hover:bg-white/5 hover:text-white",
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>
        <button onClick={logout} className="m-4 flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-red-400 hover:bg-red-500/10">
          <LogOut className="w-4 h-4" /> Sign out
        </button>
      </aside>

      <div className="flex-1 lg:pl-[260px]">
        <header className="sticky top-0 z-30 border-b border-white/10 bg-bg-root/80 backdrop-blur-xl px-4 py-4 lg:px-8 flex items-center justify-between">
          <div className="lg:hidden font-bold">Payfin</div>
          <div className="flex items-center gap-2 text-xs font-semibold text-green-400 bg-green-500/10 border border-green-500/20 rounded-full px-3 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse-glow" />
            Secured
          </div>
        </header>
        <main className="p-4 lg:p-8 max-w-6xl">{children}</main>
      </div>
    </div>
  );
}
