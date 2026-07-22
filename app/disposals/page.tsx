"use client";

/**
 * EquipTrack — Disposal Center (includes the Scrap view as a filter).
 * File: app/disposals/page.tsx
 * Sidebar: add a link to /disposals (see integration notes).
 */

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "";

type Org = { id: string; name: string };
type Asset = { id: string; name: string; category: string; status: string };
type Disposal = {
  id: string; assetId: string;
  assetName?: string | null; assetCategory?: string | null;
  lastLocationName?: string | null;
  method: string; reason?: string | null; disposedAt: string;
};

const METHODS: [string, string][] = [
  ["SCRAPPED", "Scrapped"],
  ["SOLD", "Sold"],
  ["DONATED", "Donated"],
  ["RETURNED", "Returned to supplier"],
  ["LOST_STOLEN", "Lost / stolen"],
];

const METHOD_STYLES: Record<string, string> = {
  SCRAPPED: "bg-gray-200 text-gray-700",
  SOLD: "bg-green-100 text-green-700",
  DONATED: "bg-blue-100 text-blue-700",
  RETURNED: "bg-amber-100 text-amber-800",
  LOST_STOLEN: "bg-red-100 text-red-700",
};

export default function DisposalsPage() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState("");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [disposals, setDisposals] = useState<Disposal[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // form
  const [assetId, setAssetId] = useState("");
  const [method, setMethod] = useState("SCRAPPED");
  const [reason, setReason] = useState("");

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/disposals`);
    if (r.ok) setDisposals(await r.json());
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const orgRes = await fetch(`${API}/api/organizations/`);
        const orgList: Org[] = await orgRes.json();
        setOrgs(orgList);
        if (orgList.length) setOrgId(orgList[0].id);
        await load();
      } catch {
        setError("Could not reach the API. Check your connection.");
      }
    })();
  }, [load]);

  useEffect(() => {
    if (!orgId) return;
    (async () => {
      const r = await fetch(`${API}/api/assets/?organizationId=${orgId}`);
      if (r.ok) setAssets(await r.json());
    })();
  }, [orgId]);

  const eligible = assets.filter((a) => a.status !== "DECOMMISSIONED");
  const shown =
    filter === "ALL" ? disposals : disposals.filter((d) => d.method === filter);

  async function dispose() {
    if (!assetId) {
      setError("Select an asset to dispose.");
      return;
    }
    const asset = assets.find((a) => a.id === assetId);
    const label = METHODS.find(([v]) => v === method)?.[1] ?? method;
    const sure = window.confirm(
      `Confirm disposal of "${asset?.name}" as ${label}?\n\n` +
        "The asset will be retired permanently and removed from operational views. " +
        "Its history is kept, and this can be reversed from this page if needed."
    );
    if (!sure) return;

    setBusy(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/disposals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assetId, method, reason: reason || null }),
      });
      if (!r.ok) {
        const detail = (await r.json().catch(() => ({}))).detail;
        throw new Error(typeof detail === "string" ? detail : `HTTP ${r.status}`);
      }
      setAssetId("");
      setReason("");
      await load();
      // refresh assets so the disposed one leaves the dropdown
      const ar = await fetch(`${API}/api/assets/?organizationId=${orgId}`);
      if (ar.ok) setAssets(await ar.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function restore(d: Disposal) {
    if (!window.confirm(`Restore "${d.assetName}" to operational status?`)) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/disposals/${d.id}/restore`, {
        method: "POST",
      });
      if (r.ok) {
        await load();
        const ar = await fetch(`${API}/api/assets/?organizationId=${orgId}`);
        if (ar.ok) setAssets(await ar.json());
      }
    } finally {
      setBusy(false);
    }
  }

  function fmt(ts: string) {
    return new Date(ts).toLocaleString("en-NG", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Disposal Center</h1>
        <p className="text-gray-500">
          Retired assets with their disposal records. Scrapped equipment lives here.
        </p>
      </div>

      {error && (
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {/* -------- dispose form -------- */}
      <div className="rounded-lg border bg-white p-4 space-y-3">
        <h2 className="font-semibold text-gray-900">Dispose an asset</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <select
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
            className="rounded border px-2 py-2 text-sm"
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
          <select
            value={assetId}
            onChange={(e) => setAssetId(e.target.value)}
            className="rounded border px-2 py-2 text-sm"
          >
            <option value="">Select asset…</option>
            {eligible.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.category})
              </option>
            ))}
          </select>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="rounded border px-2 py-2 text-sm"
          >
            {METHODS.map(([v, label]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
        </div>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason / notes (e.g. compressor beyond economic repair)"
          rows={2}
          className="w-full rounded border px-2 py-2 text-sm"
        />
        <button
          disabled={busy}
          onClick={dispose}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          Confirm disposal…
        </button>
      </div>

      {/* -------- filter tabs -------- */}
      <div className="flex flex-wrap gap-2">
        {[["ALL", "All"], ...METHODS].map(([v, label]) => (
          <button
            key={v}
            onClick={() => setFilter(v)}
            className={`rounded-full px-3 py-1 text-sm ${
              filter === v
                ? "bg-gray-900 text-white"
                : "bg-white border text-gray-700 hover:bg-gray-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* -------- list -------- */}
      <div className="rounded-lg border bg-white">
        {shown.length === 0 ? (
          <p className="px-4 py-6 text-sm text-gray-500">
            No disposed assets{filter !== "ALL" ? " under this method" : ""} yet.
          </p>
        ) : (
          <ul className="divide-y">
            {shown.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900">
                    {d.assetName}{" "}
                    <span className="text-sm font-normal text-gray-500">
                      ({d.assetCategory})
                    </span>
                  </p>
                  <p className="text-sm text-gray-500">
                    {fmt(d.disposedAt)}
                    {d.lastLocationName && ` · last at ${d.lastLocationName}`}
                    {d.reason && ` · ${d.reason}`}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${METHOD_STYLES[d.method] || ""}`}
                >
                  {d.method.replace("_", " ")}
                </span>
                <button
                  disabled={busy}
                  onClick={() => restore(d)}
                  className="rounded border px-2.5 py-1 text-xs text-gray-700 hover:bg-gray-50"
                >
                  Restore
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
