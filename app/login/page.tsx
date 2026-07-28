"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Radar } from "lucide-react";
import { login } from "@/lib/authClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLogin() {
    if (!email || !password) {
      setError("Enter your phone number or email, and your password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Radar className="size-5" />
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-900">EquipTrack AI</p>
            <p className="text-sm text-gray-500">Field Service Platform</p>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6 space-y-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Sign in</h1>
            <p className="text-sm text-gray-500">Access your operations dashboard.</p>
          </div>

          {error && (
            <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}

          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">
                Phone number or email
              </label>
            <input
              type="text"
                inputMode="text"
                placeholder="08012345678"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              className="w-full rounded border px-3 py-2 text-sm"
              autoComplete="username"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="••••••••"
              className="w-full rounded border px-3 py-2 text-sm"
              autoComplete="current-password"
            />
          </div>

          <button
            disabled={busy}
            onClick={handleLogin}
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}