"use client"

import { useCallback, useEffect, useState } from "react"
import { Boxes, ClipboardList, Wrench, RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch, getUser } from "@/lib/authClient"

// The organisation is never sent from here. /api/analytics/fleet-report takes
// it from the caller's token, so a signed-in user cannot ask for another
// client's fleet by editing a query string.

type Counted = { category: string; count: number }

type FleetReport = {
  period: { start: string; end: string }
  filters: { site: string | null; asset: string | null; site_label: string; asset_label: string }
  fleet: {
    total: number
    by_status: { status: string; count: number }[]
    touched: number
    touched_pct: number
  }
  activity: { reports_filed: number; jobs_completed: number; closed_without_report: number }
  faults: Counted[]
  repeat_offenders: { asset: string; location: string | null; category: string; count: number }[]
  workload: { asset: string; location: string | null; jobs: number }[]
  locations: {
    id: string
    name: string
    client: string | null
    units: number
    jobs: number
    faults: Counted[]
    worst_units: { asset: string; jobs: number }[]
  }[]
}

type Mode = "month" | "year" | "range"

/** FAULT_CATEGORY enum values are stored SCREAMING_SNAKE. Nobody wants to read
 *  that in a client meeting. */
function humanise(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

function formatDay(iso: string) {
  const [y, m, d] = iso.split("-").map(Number)
  return new Date(y, m - 1, d).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
  })
}

function thisMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
}

export function FleetReport() {
  const [mode, setMode] = useState<Mode>("month")
  const [month, setMonth] = useState(thisMonth())
  const [year, setYear] = useState(String(new Date().getFullYear()))
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [site, setSite] = useState("")
  const [asset, setAsset] = useState("")

  const [data, setData] = useState<FleetReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!getUser()) {
      window.location.href = "/login"
      return
    }
    setLoading(true)

    const params = new URLSearchParams()
    if (mode === "month" && month) params.set("month", month)
    if (mode === "year" && year) params.set("year", year)
    if (mode === "range" && start && end) {
      params.set("start", start)
      params.set("end", end)
    }
    if (site.trim()) params.set("site", site.trim())
    if (asset.trim()) params.set("asset", asset.trim())

    try {
      const res = await apiFetch(`/api/analytics/fleet-report?${params.toString()}`)
      if (!res.ok) {
        // The API explains itself on 400 and 404 — an unmatched site name is a
        // typo, not a crash, and the message should say so.
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? "Could not build the report.")
      }
      setData(await res.json())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the server.")
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [mode, month, year, start, end, site, asset])

  // Runs once on mount with the default period. After that the operator
  // decides when to re-query, so a half-typed site name never fires a request.
  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const rangeIncomplete = mode === "range" && (!start || !end)

  const summary = data
    ? [
        {
          label: "Units on register", value: data.fleet.total,
          note: `${data.locations.length} site${data.locations.length !== 1 ? "s" : ""}`,
          icon: Boxes, tone: "text-primary bg-primary/10",
        },
        {
          label: "Units serviced", value: data.fleet.touched,
          note: `${data.fleet.touched_pct.toFixed(1)}% of the fleet`,
          icon: Wrench, tone: "text-emerald-600 bg-emerald-100",
        },
        {
          label: "Reports filed", value: data.activity.reports_filed,
          note: `${data.activity.jobs_completed} job${data.activity.jobs_completed !== 1 ? "s" : ""} completed`,
          icon: ClipboardList, tone: "text-sky-600 bg-sky-100",
        },
        {
          label: "Repeat failures", value: data.repeat_offenders.length,
          note: data.repeat_offenders.length
            ? "Units seen more than once"
            : "No unit seen twice this period",
          icon: RotateCcw,
          tone: data.repeat_offenders.length
            ? "text-amber-600 bg-amber-100"
            : "text-emerald-600 bg-emerald-100",
        },
      ]
    : []

  return (
    <div className="space-y-6 p-6">
      {/* Filters */}
      <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Period</label>
            <div className="inline-flex rounded-lg border border-border p-0.5">
              {(["month", "year", "range"] as Mode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm capitalize transition-colors",
                    mode === m
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted",
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          {mode === "month" && (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Month</label>
              <input
                type="month" value={month} onChange={(e) => setMonth(e.target.value)}
                className="h-9 rounded-lg border border-border bg-background px-3 text-sm"
              />
            </div>
          )}

          {mode === "year" && (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Year</label>
              <input
                type="number" value={year} min="2020" max="2100"
                onChange={(e) => setYear(e.target.value)}
                className="h-9 w-28 rounded-lg border border-border bg-background px-3 text-sm"
              />
            </div>
          )}

          {mode === "range" && (
            <>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">From</label>
                <input
                  type="date" value={start} onChange={(e) => setStart(e.target.value)}
                  className="h-9 rounded-lg border border-border bg-background px-3 text-sm"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">To</label>
                <input
                  type="date" value={end} onChange={(e) => setEnd(e.target.value)}
                  className="h-9 rounded-lg border border-border bg-background px-3 text-sm"
                />
              </div>
            </>
          )}

          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Site</label>
            <input
              type="text" value={site} placeholder="All sites"
              onChange={(e) => setSite(e.target.value)}
              className="h-9 w-40 rounded-lg border border-border bg-background px-3 text-sm"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Asset</label>
            <input
              type="text" value={asset} placeholder="All assets"
              onChange={(e) => setAsset(e.target.value)}
              className="h-9 w-44 rounded-lg border border-border bg-background px-3 text-sm"
            />
          </div>

          <button
            type="button" onClick={load} disabled={loading || rangeIncomplete}
            className="h-9 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Building…" : "Run report"}
          </button>
        </div>

        {rangeIncomplete && (
          <p className="mt-3 text-xs text-muted-foreground">
            Set both a start and an end date to run a custom range.
          </p>
        )}
      </section>

      {error && (
        <div className="rounded-xl bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading && !data && (
        <p className="text-sm text-muted-foreground">Building the report…</p>
      )}

      {data && (
        <>
          <p className="text-sm text-muted-foreground">
            {formatDay(data.period.start)} – {formatDay(data.period.end)}
            <span className="mx-2 text-border">|</span>
            {data.filters.site_label}
            {data.filters.asset && <> <span className="mx-2 text-border">|</span> {data.filters.asset_label}</>}
          </p>

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

          {/* Register first: it is the section that is always populated. */}
          <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="text-sm font-semibold text-foreground">Asset register by site</h2>
              <span className="text-xs text-muted-foreground">
                {data.fleet.total} units across {data.locations.length} sites
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Site</th>
                    <th className="px-5 py-3 font-medium">Client</th>
                    <th className="px-5 py-3 text-right font-medium">Units</th>
                    <th className="px-5 py-3 text-right font-medium">Jobs</th>
                    <th className="px-5 py-3 font-medium">Leading fault</th>
                  </tr>
                </thead>
                <tbody>
                  {data.locations.map((l) => (
                    <tr key={l.id} className="border-b border-border last:border-0 hover:bg-muted/40">
                      <td className="px-5 py-3 font-medium text-foreground">{l.name}</td>
                      <td className="px-5 py-3 text-muted-foreground">{l.client ?? "—"}</td>
                      <td className="px-5 py-3 text-right tabular-nums text-foreground">{l.units}</td>
                      <td className="px-5 py-3 text-right tabular-nums text-muted-foreground">
                        {l.jobs || "—"}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {l.faults.length
                          ? `${humanise(l.faults[0].category)} (${l.faults[0].count})`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-border bg-muted/30 font-semibold text-foreground">
                    <td className="px-5 py-3">Total</td>
                    <td className="px-5 py-3 text-muted-foreground">
                      {data.locations.length} site{data.locations.length !== 1 ? "s" : ""}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums">{data.fleet.total}</td>
                    <td className="px-5 py-3 text-right tabular-nums">
                      {data.locations.reduce((s, l) => s + l.jobs, 0) || "—"}
                    </td>
                    <td className="px-5 py-3" />
                  </tr>
                </tfoot>
              </table>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              <div className="border-b border-border px-5 py-4">
                <h2 className="text-sm font-semibold text-foreground">Faults by category</h2>
              </div>
              {data.faults.length ? (
                <table className="w-full text-left text-sm">
                  <tbody>
                    {data.faults.map((f) => (
                      <tr key={f.category} className="border-b border-border last:border-0">
                        <td className="px-5 py-2.5 text-foreground">{humanise(f.category)}</td>
                        <td className="px-5 py-2.5 text-right tabular-nums text-muted-foreground">
                          {f.count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="px-5 py-6 text-sm text-muted-foreground">
                  No fault categories recorded in this period.
                </p>
              )}
            </section>

            <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              <div className="border-b border-border px-5 py-4">
                <h2 className="text-sm font-semibold text-foreground">Repeat failures</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Units seen more than once for the same fault.
                </p>
              </div>
              {data.repeat_offenders.length ? (
                <table className="w-full text-left text-sm">
                  <tbody>
                    {data.repeat_offenders.map((r, i) => (
                      <tr key={`${r.asset}-${r.category}-${i}`} className="border-b border-border last:border-0">
                        <td className="px-5 py-2.5">
                          <span className="text-foreground">{r.asset}</span>
                          <span className="block text-xs text-muted-foreground">
                            {r.location ?? "—"} · {humanise(r.category)}
                          </span>
                        </td>
                        <td className="px-5 py-2.5 text-right tabular-nums text-amber-600">
                          {r.count}×
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="px-5 py-6 text-sm text-muted-foreground">
                  No unit was attended more than once in this period.
                </p>
              )}
            </section>
          </div>

          {data.workload.length > 0 && (
            <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              <div className="border-b border-border px-5 py-4">
                <h2 className="text-sm font-semibold text-foreground">Busiest units</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="px-5 py-3 font-medium">Asset</th>
                      <th className="px-5 py-3 font-medium">Site</th>
                      <th className="px-5 py-3 text-right font-medium">Jobs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.workload.map((w, i) => (
                      <tr key={`${w.asset}-${i}`} className="border-b border-border last:border-0 hover:bg-muted/40">
                        <td className="px-5 py-3 text-foreground">{w.asset}</td>
                        <td className="px-5 py-3 text-muted-foreground">{w.location ?? "—"}</td>
                        <td className="px-5 py-3 text-right tabular-nums text-muted-foreground">{w.jobs}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {data.activity.closed_without_report > 0 && (
            <p className="text-xs text-muted-foreground">
              {data.activity.closed_without_report} job
              {data.activity.closed_without_report !== 1 ? "s were" : " was"} closed without a
              filed report, so they carry no fault diagnosis.
            </p>
          )}
        </>
      )}
    </div>
  )
}
