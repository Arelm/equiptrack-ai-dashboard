"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { Ticket as TicketIcon, Users, PackageX, AlarmClock } from "lucide-react"
import { PriorityBadge, StatusBadge } from "@/components/badges"
import { AddAssetForm } from "@/components/add-asset-form"
import { AssignControl } from "@/components/assign-control"
import { cn } from "@/lib/utils"
import { mapPriority, mapStatus, type BackendLocation } from "@/lib/api"
import { apiFetch, getUser, type AuthUser } from "@/lib/authClient"

type Technician = { id: string; name: string; role: string; isActive?: boolean }
type Asset = { id: string; name: string }

type WorkOrder = {
  id: string
  title: string
  priority: string | null
  status: string | null
  assetId: string | null
  locationId: string | null
  createdAt: string | null
  ageDays: number | null
  isLegacy: boolean
  technician: { id: string; name: string | null; accepted: boolean } | null
}

function formatDate(iso: string | null) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  })
}

/** Job age is what turns a queue into a warning. A pump open since Jul 21 and a
 *  job opened this morning looked identical before this. */
function AgeCell({ days, resolved }: { days: number | null; resolved: boolean }) {
  if (days === null) return <span className="text-muted-foreground">—</span>
  if (resolved) return <span className="text-muted-foreground">{Math.round(days)}d</span>
  const tone =
    days >= 7 ? "text-red-600 font-semibold"
    : days >= 3 ? "text-amber-600 font-medium"
    : "text-muted-foreground"
  return <span className={tone}>{days < 1 ? "today" : `${Math.round(days)}d`}</span>
}

export function OperationsDashboard() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([])
  const [technicians, setTechnicians] = useState<Technician[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [locations, setLocations] = useState<BackendLocation[]>([])
  const [lowStock, setLowStock] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const u = getUser()
    if (!u) {
      window.location.href = "/login"
      return
    }
    setUser(u)
    const q = `?organizationId=${encodeURIComponent(u.orgId)}`
    try {
      const [wo, tech, ast, loc, stock] = await Promise.all([
        apiFetch(`/api/workorders/${q}`),
        apiFetch(`/api/technicians/${q}`),
        apiFetch(`/api/assets/${q}`),
        apiFetch(`/api/locations/${q}`),
        apiFetch(`/api/parts/low-stock${q}`),
      ])
      if (!wo.ok) throw new Error("Could not load the ticket queue.")
      setWorkOrders(await wo.json())
      if (tech.ok) setTechnicians(await tech.json())
      if (ast.ok) setAssets(await ast.json())
      if (loc.ok) setLocations(await loc.json())
      if (stock.ok) setLowStock((await stock.json()).count)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the server.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) {
    return <p className="p-6 text-sm text-muted-foreground">Loading operations data…</p>
  }
  if (error) {
    return (
      <div className="m-6 rounded-xl bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    )
  }

  const assetById = new Map(assets.map((a) => [a.id, a]))
  const locationById = new Map(locations.map((l) => [l.id, l]))
  const fieldTechs = technicians.filter((t) => t.role === "TECHNICIAN")

  const open = workOrders.filter((w) => mapStatus(w.status ?? "") !== "Resolved")
  // Unassigned is now a real count off real assignment rows, not a hardcoded null.
  const unassigned = open.filter((w) => !w.technician).length
  const assignedNotAccepted = open.filter((w) => w.technician && !w.technician.accepted).length
  const busy = new Set(open.filter((w) => w.technician).map((w) => w.technician!.id)).size
  const slaBreaches = open.filter(
    (w) => mapPriority(w.priority ?? "") === "High" && !w.technician,
  ).length

  const summary = [
    { label: "Open Tickets", value: open.length, note: "Across all facilities",
      icon: TicketIcon, tone: "text-primary bg-primary/10" },
    { label: "Technicians Free", value: `${Math.max(fieldTechs.length - busy, 0)} / ${fieldTechs.length}`,
      note: busy > 0 ? `${busy} on active jobs` : "Ready for dispatch",
      icon: Users, tone: "text-emerald-600 bg-emerald-100" },
    { label: "Parts Low Stock", value: lowStock ?? "—", note: "Below reorder threshold",
      icon: PackageX, tone: "text-amber-600 bg-amber-100" },
    { label: "Unassigned", value: unassigned,
      note: slaBreaches > 0 ? `${slaBreaches} high priority` : "All high priority covered",
      icon: AlarmClock, tone: unassigned > 0 ? "text-red-600 bg-red-100" : "text-emerald-600 bg-emerald-100" },
  ]

  const canAssign = user?.role === "MANAGER" || user?.role === "ADMIN"

  return (
    <div className="space-y-6 p-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summary.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="rounded-xl border border-border bg-card p-5 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{card.label}</p>
                  <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
                    {card.value}
                  </p>
                </div>
                <span className={cn("flex size-10 items-center justify-center rounded-lg", card.tone)}>
                  <Icon className="size-5" />
                </span>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">{card.note}</p>
            </div>
          )
        })}
      </section>

      {assignedNotAccepted > 0 && (
        <div className="rounded-lg bg-amber-50 px-4 py-2.5 text-sm text-amber-900">
          {assignedNotAccepted} assigned job{assignedNotAccepted !== 1 ? "s have" : " has"} not
          been accepted yet.
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">Live Ticket Queue</h2>
          <span className="text-xs text-muted-foreground">{workOrders.length} tickets</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1000px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-5 py-3 font-medium">Ticket ID</th>
                <th className="px-5 py-3 font-medium">Facility</th>
                <th className="px-5 py-3 font-medium">Asset</th>
                <th className="px-5 py-3 font-medium">Priority</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Age</th>
                <th className="px-5 py-3 font-medium">Technician</th>
                <th className="px-5 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {workOrders.map((w) => {
                const resolved = mapStatus(w.status ?? "") === "Resolved"
                return (
                  <tr key={w.id} className="border-b border-border last:border-0 hover:bg-muted/40">
                    <td className="px-5 py-3 font-mono text-xs font-medium text-primary">
                      <Link href={`/tickets/${w.id}`} className="hover:underline">
                        {w.id.slice(0, 8).toUpperCase()}
                      </Link>
                      {w.isLegacy && (
                        <span className="ml-1.5 rounded bg-muted px-1 py-0.5 text-[10px] font-normal text-muted-foreground">
                          legacy
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">
                      {(w.locationId && locationById.get(w.locationId)?.name) ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">
                      {(w.assetId && assetById.get(w.assetId)?.name) ?? "—"}
                    </td>
                    <td className="px-5 py-3"><PriorityBadge priority={mapPriority(w.priority ?? "")} /></td>
                    <td className="px-5 py-3"><StatusBadge status={mapStatus(w.status ?? "")} /></td>
                    <td className="px-5 py-3"><AgeCell days={w.ageDays} resolved={resolved} /></td>
                    <td className="px-5 py-3">
                      <AssignControl
                        workOrderId={w.id}
                        current={w.technician}
                        technicians={fieldTechs}
                        disabled={!canAssign || resolved}
                        onAssigned={load}
                      />
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-muted-foreground">
                      {formatDate(w.createdAt)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {canAssign && user && (
        <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold text-foreground">Add New Asset</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Register a new piece of equipment to a facility.
            </p>
          </div>
          <div className="p-5">
            <AddAssetForm organizationId={user.orgId} locations={locations} />
          </div>
        </section>
      )}
    </div>
  )
}