"use client";

/**
 * EquipTrack — Asset Transfers page.
 * File: app/transfers/page.tsx
 * Sidebar: add a link to /transfers (see integration notes).
 */

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "";

type Org = { id: string; name: string };
type Location = { id: string; name: string; address?: string | null };
type Asset = {
  id: string; name: string; category: string; status: string;
  locationId: string; custodyStatus?: string;
};
type Transfer = {
  id: string; assetId: string;
  fromLocationName?: string | null; toLocationName?: string | null;
  reason: string; status: string; notes?: string | null;
  conditionOnDispatch?: string | null; conditionOnArrival?: string | null;
  initiatedAt: string; resolvedAt?: string | null;
};

const REASONS: [string, string][] = [
  ["PROJECT_NEED", "Needed on another project"],
  ["SITE_DEMOB", "Site demobilization"],
  ["REPAIR", "Repair / workshop"],
  ["STORAGE", "Return to storage"],
  ["OTHER", "Other"],
];

const STATUS_STYLES: Record<string, string> = {
  IN_TRANSIT: "bg-amber-100 text-amber-800",
  RECEIVED: "bg-green-100 text-green-700",
  DISPUTED: "bg-red-100 text-red-700",
  CANCELLED: "bg-gray-100 text-gray-600",
};

export default function TransfersPage() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState("");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [assetNames, setAssetNames] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // form state
  const [assetId, setAssetId] = useState("");
  const [toLocationId, setToLocationId] = useState("");
  const [reason, setReason] = useState("PROJECT_NEED");
  const [condition, setCondition] = useState("");

  const loadTransfers = useCallback(async () => {
    const r = await fetch(`${API}/api/transfers`);
    if (r.ok) setTransfers(await r.json());
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [orgRes, locRes] = await Promise.all([
          fetch(`${API}/api/organizations/`),
          fetch(`${API}/api/transfers/locations`),
        ]);
        const orgList: Org[] = await orgRes.json();
        setOrgs(orgList);
        if (orgList.length) setOrgId(orgList[0].id);
        setLocations(await locRes.json());
        await loadTransfers();
      } catch {
        setError("Could not reach the API. Check your connection.");
      }
    })();
  }, [loadTransfers]);

  useEffect(() => {
    if (!orgId) return;
    (async () => {
      const r = await fetch(`${API}/api/assets/?organizationId=${orgId}`);
      if (!r.ok) return;
      const list: Asset[] = await r.json();
      setAssets(list);
      setAssetNames((prev) => ({
        ...prev,
        ...Object.fromEntries(list.map((a) => [a.id, a.name])),
      }));
    })();
  }, [orgId]);

  const selectedAsset = assets.find((a) => a.id === assetId);
  const eligibleAssets = assets.filter(
    (a) => a.status !== "DECOMMISSIONED" && a.custodyStatus !== "IN_TRANSIT"
  );
  const destinations = locations.filter(
    (l) => l.id !== selectedAsset?.locationId
  );

  async function post(path: string, body: unknown): Promise<boolean> {
    setBusy(true);
    setError("");
    try {
      const r = await fetch(`${API}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const detail = (await r.json().catch(() => ({}))).detail;
        throw new Error(typeof detail === "string" ? detail : `HTTP ${r.status}`);
      }
      await loadTransfers();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function initiate() {
    if (!assetId || !toLocationId) {
      setError("Select an asset and a destination.");
      return;
    }
    const ok = await post("/api/transfers", {
      assetId,
      toLocationId,
      reason,
      conditionOnDispatch: condition || null,
    });
    if (ok) {
      setAssetId("");
      setToLocationId("");
      setCondition("");
    }
  }

  function fmt(ts?: string | null) {
    return ts
      ? new Date(ts).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" })
      : "—";
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Asset Transfers</h1>
        <p className="text-gray-500">
          Move equipment between sites with a confirmed custody trail.
        </p>
      </div>

      {error && (
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {/* -------- initiate -------- */}
      <div className="rounded-lg border bg-white p-4 space-y-3">
        <h2 className="font-semibold text-gray-900">New transfer</h2>
        <div className="grid gap-3 md:grid-cols-2">
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
            {eligibleAssets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.category})
              </option>
            ))}
          </select>
          <select
            value={toLocationId}
            onChange={(e) => setToLocationId(e.target.value)}
            className="rounded border px-2 py-2 text-sm"
            disabled={!assetId}
          >
            <option value="">Destination site…</option>
            {destinations.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
          <select
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="rounded border px-2 py-2 text-sm"
          >
            {REASONS.map(([v, label]) => (
              <option key={v} value={v}>{label}</option>
            ))}
          </select>
        </div>
        <input
          value={condition}
          onChange={(e) => setCondition(e.target.value)}
          placeholder="Condition on dispatch (optional)"
          className="w-full rounded border px-2 py-2 text-sm"
        />
        <button
          disabled={busy}
          onClick={initiate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Send transfer
        </button>
      </div>

      {/* -------- list -------- */}
      <div className="rounded-lg border bg-white">
        <div className="border-b px-4 py-3 font-semibold text-gray-900">
          Movement history
        </div>
        {transfers.length === 0 ? (
          <p className="px-4 py-6 text-sm text-gray-500">No transfers yet.</p>
        ) : (
          <ul className="divide-y">
            {transfers.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900">
                    {assetNames[t.assetId] || t.assetId.slice(0, 8)}
                  </p>
                  <p className="text-sm text-gray-500">
                    {t.fromLocationName} → {t.toLocationName} · {fmt(t.initiatedAt)}
                    {t.conditionOnArrival && ` · arrival: ${t.conditionOnArrival}`}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[t.status] || ""}`}
                >
                  {t.status.replace("_", " ")}
                </span>
                {t.status === "IN_TRANSIT" && (
                  <span className="flex gap-2">
                    <button
                      disabled={busy}
                      onClick={() => {
                        const c = window.prompt("Condition on arrival (optional):") ?? "";
                        post(`/api/transfers/${t.id}/receive`, {
                          conditionOnArrival: c || null,
                        });
                      }}
                      className="rounded bg-green-600 px-2.5 py-1 text-xs text-white hover:bg-green-700"
                    >
                      Receive
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => {
                        const why = window.prompt(
                          "Describe the problem (missing, damaged, wrong item):"
                        );
                        if (why) post(`/api/transfers/${t.id}/dispute`, { notes: why });
                      }}
                      className="rounded bg-red-600 px-2.5 py-1 text-xs text-white hover:bg-red-700"
                    >
                      Dispute
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => {
                        if (window.confirm("Cancel this transfer?"))
                          post(`/api/transfers/${t.id}/cancel`, {});
                      }}
                      className="rounded border px-2.5 py-1 text-xs text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
