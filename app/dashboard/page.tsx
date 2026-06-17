"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { AppShell } from "@/components/app-shell";
import { DashboardSkeleton } from "@/components/skeleton";
import { api, getToken } from "@/lib/api";
import { useRealtime } from "@/lib/realtime";
import { formatINR } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<Record<string, unknown> | null>(null);
  const [stats, setStats] = useState<Record<string, number | string | null>>({});
  const [accounts, setAccounts] = useState<Array<Record<string, unknown>>>([]);
  const [primaryBalance, setPrimaryBalance] = useState(0);

  const refresh = useCallback(async () => {
    const [me, dash, accs] = await Promise.all([api.me(), api.dashboardStats(), api.accounts()]);
    setUser(me.user);
    setStats(dash.stats);
    setAccounts(accs.accounts);
    const primary = accs.accounts.find((a) => a.is_primary) || accs.accounts[0];
    if (primary) setPrimaryBalance(Number(primary.balance));
  }, []);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    refresh()
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, [router, refresh]);

  useRealtime(user?.id as number | null, {
    onBalanceUpdate: (data) => {
      setPrimaryBalance(data.balance);
      setStats((s) => ({ ...s, total_balance: data.balance }));
    },
    onTransaction: () => refresh(),
  });

  if (loading) {
    return (
      <AppShell>
        <DashboardSkeleton />
      </AppShell>
    );
  }

  const primary = accounts.find((a) => a.is_primary) || accounts[0];

  return (
    <AppShell userName={String(user?.full_name || "")}>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">
          Good day, <span className="text-teal">{String(user?.full_name)}</span>!
        </h1>
        <p className="text-second text-sm">Here&apos;s your financial overview</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        <motion.div
          className="glass-card p-6 lg:col-span-2 relative overflow-hidden"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-teal/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <p className="text-xs uppercase tracking-wider text-muted mb-1">{String(primary?.account_type)}</p>
          <p className="text-sm text-second mb-2">Available Balance</p>
          <p className="text-4xl sm:text-5xl font-extrabold tracking-tight">
            {formatINR(primaryBalance)}
          </p>
          <p className="text-xs font-mono text-muted mt-2">A/C {String(primary?.account_no)}</p>
          {!!user?.upi_id && (
            <p className="text-sm text-teal mt-3 font-mono">UPI: {String(user.upi_id)}</p>
          )}
        </motion.div>

        <motion.div className="glass-card p-6" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <h3 className="font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-2 text-sm">
            {["/transactions", "/upi", "/payment-gateway"].map((href) => (
              <a key={href} href={href} className="block rounded-xl border border-white/10 px-4 py-3 hover:bg-white/5 transition">
                {href.replace("/", "").replace("-", " ")}
              </a>
            ))}
          </div>
        </motion.div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Balance", value: formatINR(Number(stats.total_balance || 0)), color: "text-teal" },
          { label: "Credits (30d)", value: formatINR(Number(stats.monthly_credits || 0)), color: "text-green-400" },
          { label: "Debits (30d)", value: formatINR(Number(stats.monthly_debits || 0)), color: "text-red-400" },
          { label: "Transactions", value: String(stats.txn_count_30d || 0), color: "text-gold" },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            className="glass-card p-5"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15 + i * 0.05 }}
          >
            <p className="text-xs text-muted uppercase tracking-wide">{stat.label}</p>
            <p className={`stat-value mt-2 ${stat.color}`}>{stat.value}</p>
          </motion.div>
        ))}
      </div>
    </AppShell>
  );
}
