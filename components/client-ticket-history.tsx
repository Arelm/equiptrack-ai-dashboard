"use client"

import { useEffect, useState } from "react"
import { PriorityBadge, StatusBadge } from "@/components/badges"
import { mapPriority, mapStatus } from "@/lib/api"
import { apiFetch, getUser } from "@/lib/authClient"

type Ticket = {
  id: string
  priority: string | null
  status: string | null
  assetId: string | null
  locationId: string | null
  createdAt: string | null
}

type Named = { id: string; name: string }

function formatDate(iso: string | null) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  })
}

/** Ticket history for the client portal.
 *
 *  Fetched in the browser, not on the server. As a server component this page
 *  called the work-order API at render time with no token and returned a 500
 *  once the API required one.
 *
 *  The request form above stays public and unauthenticated: raising a ticket is
 *  the front door of the whole system and must never need a login. Reading other
 *  people's ticket history is a different act, so it does.
 */
export function ClientTicketHistory() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [assets, setAssets] = useState<Named[]>([])
  const [locations, setLocations] = useState<Named[]>([])
  const [state, setState] = useState<"loading" | "ready" | "anon" | "error">("loading")

  useEffect(() => {
    const user = getUser()
    if (!user) {
      setState("anon")
      return
    }
    const q = `?organizationId=${encodeURIComponent(user.orgId)}`
    Promise.all([
      apiFetch(`/api/workorders/${q}`),
      apiFetch(`/api/assets/${q}`),
      apiFetch(`/api/locations/${q}`),
    ])
      .then(async ([w, a, l]) => {
        if (!w.ok) throw new Error()
        setTickets(await w.json())
        if (a.ok) setAssets(await a.json())
        if (l.ok) setLocations(await l.json())
        setState("ready")
      })
      .catch(() => setState("error"))
  }, [])

  if (state === "anon") {
    return (
      <div className="rounded-xl border border-border bg-card px-5 py-10 text-center">
        <p className="text-sm text-muted-foreground">
          Sign in to see the history of your requests.
        </p>
        <a href="/login" className="mt-2 inline-block text-sm font-medium text-primary hover:underline">
          Sign in
        </a>
      </div>
    )
  }

  if (state === "loading") {
    return (
      <div className="rounded-xl border border-border bg-card px-5 py-10 text-center">
        <p className="text-sm text-muted-foreground">Loading your requests…</p>
      </div>
    )
  }

  if (state === "error") {
    return (
      <div className="rounded-xl bg-destructive/10 px-5 py-4">
        <p className="text-sm text-destructive">Could not load ticket history.</p>
      </div>
    )
  }

  const assetById = new Map(assets.map((a) => [a.id, a]))
  const locationById = new Map(locations.map((l) => [l.id, l]))

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <h2 className="text-sm font-semibold text-foreground">Ticket History</h2>
        <span className="text-xs text-muted-foreground">{tickets.length} requests</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
              <th className="px-5 py-3 font-medium">Ticket ID</th>
              <th className="px-5 py-3 font-medium">Asset</th>
              <th className="px-5 py-3 font-medium">Priority</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id} className="border-b border-border last:border-0 hover:bg-muted/40">
                <td className="px-5 py-3 font-mono text-xs font-medium text-primary">
                  {t.id.slice(0, 8).toUpperCase()}
                </td>
                <td className="px-5 py-3 text-foreground">
                  <span className="font-medium">
                    {(t.assetId && assetById.get(t.assetId)?.name) ?? "—"}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {(t.locationId && locationById.get(t.locationId)?.name) ?? ""}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <PriorityBadge priority={mapPriority(t.priority ?? "")} />
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={mapStatus(t.status ?? "")} />
                </td>
                <td className="px-5 py-3 whitespace-nowrap text-muted-foreground">
                  {formatDate(t.createdAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}