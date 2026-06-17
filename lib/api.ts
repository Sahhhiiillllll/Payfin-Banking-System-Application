const API_BASE = typeof window !== "undefined" ? "" : process.env.NEXT_PUBLIC_API_URL || "";

export type ApiResponse<T> = T & { success?: boolean; error?: string };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("ve_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.message || `HTTP ${res.status}`);
  return data as T;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  login: (body: { username: string; password: string; mfa_code?: string }) =>
    request<{ success: boolean; token?: string; mfa_required?: boolean; user?: Record<string, unknown> }>(
      "/api/auth/login", { method: "POST", body: JSON.stringify(body) },
    ),
  register: (body: Record<string, string>) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<{ user: Record<string, unknown> }>("/api/auth/me"),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  dashboardStats: () => request<{ stats: Record<string, number | string | null> }>("/api/dashboard/stats"),
  accounts: () => request<{ accounts: Array<Record<string, unknown>> }>("/api/accounts"),
  transactions: (limit = 50) => request<{ transactions: Array<Record<string, unknown>> }>(`/api/transactions?limit=${limit}`),
  deposit: (body: Record<string, unknown>) =>
    request("/api/transactions/deposit", { method: "POST", body: JSON.stringify(body) }),
  withdraw: (body: Record<string, unknown>) =>
    request("/api/transactions/withdraw", { method: "POST", body: JSON.stringify(body) }),
  upiSend: (body: Record<string, unknown>, idempotencyKey: string) =>
    request("/api/upi/send", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  gatewayPay: (body: Record<string, unknown>, idempotencyKey: string) =>
    request("/api/gateway/pay", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  mfaSetup: () => request<{ secret: string; qr_base64: string }>("/api/security/mfa/setup", { method: "POST" }),
  mfaEnable: (secret: string, code: string) =>
    request("/api/security/mfa/enable", { method: "POST", body: JSON.stringify({ secret, code }) }),
  mfaVerify: (code: string) =>
    request<{ token: string }>("/api/security/mfa/verify", { method: "POST", body: JSON.stringify({ code }) }),
};

export function setToken(token: string) {
  localStorage.setItem("ve_token", token);
}

export function clearToken() {
  localStorage.removeItem("ve_token");
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ve_token");
}
