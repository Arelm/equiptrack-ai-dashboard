// lib/authClient.ts — client-side auth for "use client" pages only.
// Server components use lib/api.ts instead (no token there yet — see auth notes).

const API = process.env.NEXT_PUBLIC_API_URL || "";

const TOKEN_KEY = "equiptrack_token";
const USER_KEY = "equiptrack_user";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  role: string;
  orgId: string;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// Drop-in replacement for fetch on client pages: attaches the bearer token
// and bounces to /login on a 401. Call it with a path like "/api/transfers"
// (no base) — it prepends NEXT_PUBLIC_API_URL just like the pages do today.
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401 && typeof window !== "undefined") {
    clearAuth();
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }
  return res;
}

// Calls the backend login endpoint. Returns the user on success, throws on failure.
export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail;
    throw new Error(typeof detail === "string" ? detail : "Login failed");
  }
  const data = await res.json();
  setAuth(data.token, data.user);
  return data.user;
}