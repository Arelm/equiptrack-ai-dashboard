"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { CheckCircle2, Loader2, Package, Pencil, Search, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { apiFetch } from "@/lib/authClient"

const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

// The three states the backend accepts, with labels a technician would use.
const STATUSES = [
  { value: "OPERATIONAL", label: "Operational" },
  { value: "UNDER_MAINTENANCE", label: "Under maintenance" },
  { value: "DECOMMISSIONED", label: "Decommissioned" },
]

const STATUS_LABEL: Record<string, string> = {
  OPERATIONAL: "Operational",
  UNDER_MAINTENANCE: "Under maintenance",
  DECOMMISSIONED: "Decommissioned",
}

type BackendAsset = {
  id: string
  name: string
  serialNumber: string | null
  category: string | null
  status: string
  organizationId: string
  locationId: string | null
}

type SiteOption = {
  id: string
  name: string
  isActive: boolean
}

type Props = {
  locationId: string
  locationName: string
  organizationId: string
  /** Every site, so an asset can be moved to the right one. */
  sites: SiteOption[]
  onClose: () => void
}

export function AssetManager({
  locationId,
  locationName,
  organizationId,
  sites,
  onClose,
}: Props) {
  const [assets, setAssets] = useState<BackendAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [query, setQuery] = useState("")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: "", status: "", locationId: "" })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  // The assets endpoint filters by organisation, not by site, so the site
  // filter happens here.
  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await apiFetch(
        `/api/assets/?organizationId=${encodeURIComponent(organizationId)}`,
      )
      if (!res.ok) {
        throw new Error(`Could not load assets (${res.status})`)
      }
      const all: BackendAsset[] = await res.json()
      setAssets(all.filter((a) => a.locationId === locationId))
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Could not load assets.",
      )
    } finally {
      setLoading(false)
    }
  }, [organizationId, locationId])

  useEffect(() => {
    load()
  }, [load])

  // Some plots hold ninety-odd units, so scrolling is not enough. Room names
  // live inside the asset name, so searching the name finds them.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const sorted = [...assets].sort((a, b) => a.name.localeCompare(b.name))
    if (!q) return sorted
    return sorted.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        (a.serialNumber ?? "").toLowerCase().includes(q),
    )
  }, [assets, query])

  function startEdit(asset: BackendAsset) {
    setEditingId(asset.id)
    setForm({
      name: asset.name,
      status: asset.status,
      locationId: asset.locationId ?? locationId,
    })
    setError(null)
    setSaved(null)
  }

  function cancelEdit() {
    setEditingId(null)
    setForm({ name: "", status: "", locationId: "" })
    setError(null)
  }

  async function readError(res: Response, fallback: string) {
    const body = await res.json().catch(() => null)
    const detail = body && typeof body.detail === "string" ? body.detail : null
    return detail ?? `${fallback} (${res.status})`
  }

  async function handleSave(asset: BackendAsset) {
    if (!form.name.trim()) {
      setError("An asset needs a name.")
      return
    }

    setSubmitting(true)
    setError(null)
    setSaved(null)

    const movedAway = form.locationId !== locationId

    try {
      const res = await apiFetch(`/api/assets/${asset.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name.trim(),
          status: form.status,
          locationId: form.locationId,
        }),
      })

      if (!res.ok) {
        throw new Error(await readError(res, "Could not save changes"))
      }

      const result: BackendAsset = await res.json()
      setSaved(
        movedAway
          ? `${result.name} moved to ${
              sites.find((s) => s.id === form.locationId)?.name ?? "another site"
            }.`
          : `Saved changes to ${result.name}.`,
      )
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Assets at {locationName}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Correct a name, change the status, or move a unit to the site it
            actually sits on.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          <X className="mr-1 size-3" />
          Close
        </Button>
      </div>

      {saved && (
        <div className="mx-6 mt-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />
          {saved}
        </div>
      )}

      {error && (
        <p className="mx-6 mt-4 text-xs font-medium text-red-600">{error}</p>
      )}

      {loading ? (
        <p className="px-6 py-8 text-sm text-muted-foreground">
          Loading assets...
        </p>
      ) : loadError ? (
        <div className="px-6 py-8">
          <p className="text-sm text-red-600">{loadError}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={load}
          >
            Try again
          </Button>
        </div>
      ) : assets.length === 0 ? (
        <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
          <Package className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No assets registered at this site yet.
          </p>
        </div>
      ) : (
        <>
          <div className="border-b border-border px-6 py-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name, room, or serial"
                className={`${fieldClass} pl-9`}
              />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {visible.length} of {assets.length} shown
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-6 py-3 font-medium">Asset</th>
                  <th className="px-6 py-3 font-medium">Serial</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((asset) =>
                  editingId === asset.id ? (
                    <tr
                      key={asset.id}
                      className="border-b border-border bg-muted/40 last:border-0"
                    >
                      <td className="px-6 py-3" colSpan={4}>
                        <div className="grid gap-3 sm:grid-cols-3">
                          <div className="sm:col-span-3">
                            <label
                              htmlFor={`name-${asset.id}`}
                              className="mb-1.5 block text-xs font-medium text-foreground"
                            >
                              Asset name
                            </label>
                            <input
                              id={`name-${asset.id}`}
                              type="text"
                              value={form.name}
                              onChange={(e) =>
                                setForm((p) => ({ ...p, name: e.target.value }))
                              }
                              className={fieldClass}
                            />
                          </div>

                          <div>
                            <label
                              htmlFor={`status-${asset.id}`}
                              className="mb-1.5 block text-xs font-medium text-foreground"
                            >
                              Status
                            </label>
                            <select
                              id={`status-${asset.id}`}
                              value={form.status}
                              onChange={(e) =>
                                setForm((p) => ({
                                  ...p,
                                  status: e.target.value,
                                }))
                              }
                              className={fieldClass}
                            >
                              {STATUSES.map((s) => (
                                <option key={s.value} value={s.value}>
                                  {s.label}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div className="sm:col-span-2">
                            <label
                              htmlFor={`site-${asset.id}`}
                              className="mb-1.5 block text-xs font-medium text-foreground"
                            >
                              Site
                            </label>
                            <select
                              id={`site-${asset.id}`}
                              value={form.locationId}
                              onChange={(e) =>
                                setForm((p) => ({
                                  ...p,
                                  locationId: e.target.value,
                                }))
                              }
                              className={fieldClass}
                            >
                              {sites
                                .filter((s) => s.isActive || s.id === form.locationId)
                                .map((s) => (
                                  <option key={s.id} value={s.id}>
                                    {s.name}
                                    {s.isActive ? "" : " (inactive)"}
                                  </option>
                                ))}
                            </select>
                          </div>
                        </div>

                        <div className="mt-4 flex gap-2">
                          <Button
                            type="button"
                            size="sm"
                            disabled={submitting}
                            onClick={() => handleSave(asset)}
                          >
                            {submitting ? (
                              <span className="flex items-center gap-2">
                                <Loader2 className="size-3 animate-spin" />
                                Saving...
                              </span>
                            ) : (
                              "Save changes"
                            )}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            disabled={submitting}
                            onClick={cancelEdit}
                          >
                            Cancel
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr
                      key={asset.id}
                      className="border-b border-border last:border-0"
                    >
                      <td className="px-6 py-3 font-medium text-foreground">
                        {asset.name}
                      </td>
                      <td className="px-6 py-3 text-muted-foreground">
                        {asset.serialNumber ?? "--"}
                      </td>
                      <td className="px-6 py-3">
                        <span
                          className={
                            asset.status === "OPERATIONAL"
                              ? "rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
                              : asset.status === "UNDER_MAINTENANCE"
                                ? "rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700"
                                : "rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
                          }
                        >
                          {STATUS_LABEL[asset.status] ?? asset.status}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex justify-end">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => startEdit(asset)}
                          >
                            <Pencil className="mr-1 size-3" />
                            Edit
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ),
                )}

                {visible.length === 0 && (
                  <tr>
                    <td
                      className="px-6 py-8 text-center text-sm text-muted-foreground"
                      colSpan={4}
                    >
                      Nothing matches &ldquo;{query}&rdquo;.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
