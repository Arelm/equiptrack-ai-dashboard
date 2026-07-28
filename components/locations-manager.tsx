"use client"

import { useCallback, useEffect, useState } from "react"
import { CheckCircle2, Loader2, MapPin, Pencil, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { apiFetch } from "@/lib/authClient"

// Sterling Oil sites sit in these parts of Lagos. "Other" is here so a
// new area never blocks someone from adding a site.
const AREAS = [
  "V.I.",
  "Banana Island",
  "Ikeja",
  "Elegushi",
  "Lekki",
  "Other",
]

const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

const labelClass = "mb-1.5 block text-sm font-medium text-foreground"

type BackendLocation = {
  id: string
  name: string
  address: string | null
  organizationId: string
  client: string | null
  supervisorName: string | null
  supervisorPhone: string | null
  area: string | null
  isActive: boolean
}

type Props = {
  organizationId: string
}

const EMPTY = {
  name: "",
  client: "Sterling Oil",
  area: "",
  supervisorName: "",
  supervisorPhone: "",
}

export function LocationsManager({ organizationId }: Props) {
  const [locations, setLocations] = useState<BackendLocation[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [form, setForm] = useState({ ...EMPTY })
  const [editingId, setEditingId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await apiFetch(
        `/api/locations/?organizationId=${encodeURIComponent(
          organizationId,
        )}&includeInactive=true`,
      )
      if (!res.ok) {
        throw new Error(`Could not load sites (${res.status})`)
      }
      setLocations(await res.json())
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Could not load sites.",
      )
    } finally {
      setLoading(false)
    }
  }, [organizationId])

  useEffect(() => {
    load()
  }, [load])

  function set(field: keyof typeof EMPTY, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function startEdit(location: BackendLocation) {
    setEditingId(location.id)
    setForm({
      name: location.name,
      client: location.client ?? "",
      area: location.area ?? "",
      supervisorName: location.supervisorName ?? "",
      supervisorPhone: location.supervisorPhone ?? "",
    })
    setError(null)
    setSaved(null)
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" })
    }
  }

  function cancelEdit() {
    setEditingId(null)
    setForm({ ...EMPTY })
    setError(null)
  }

  async function readError(res: Response, fallback: string) {
    const body = await res.json().catch(() => null)
    const detail = body && typeof body.detail === "string" ? body.detail : null
    return detail ?? `${fallback} (${res.status})`
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSaved(null)

    const payload = {
      name: form.name,
      client: form.client || null,
      area: form.area || null,
      supervisorName: form.supervisorName || null,
      supervisorPhone: form.supervisorPhone || null,
    }

    try {
      const res = editingId
        ? await apiFetch(`/api/locations/${editingId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          })
        : await apiFetch(`/api/locations/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, organizationId }),
          })

      if (!res.ok) {
        throw new Error(
          await readError(
            res,
            editingId ? "Could not save changes" : "Could not add site",
          ),
        )
      }

      const result: BackendLocation = await res.json()
      setSaved(
        editingId ? `Saved changes to ${result.name}.` : `Added ${result.name}.`,
      )
      setEditingId(null)
      setForm({ ...EMPTY })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setSubmitting(false)
    }
  }

  async function toggleActive(location: BackendLocation) {
    setBusyId(location.id)
    setError(null)
    setSaved(null)
    try {
      const res = await apiFetch(`/api/locations/${location.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isActive: !location.isActive }),
      })
      if (!res.ok) {
        throw new Error(await readError(res, "Could not update site"))
      }
      setSaved(
        location.isActive
          ? `${location.name} is now inactive and hidden from new work.`
          : `${location.name} is active again.`,
      )
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setBusyId(null)
    }
  }

  const active = locations.filter((l) => l.isActive)
  const inactive = locations.filter((l) => !l.isActive)

  return (
    <div className="space-y-6">
      {/* ---- Form ---- */}
      <section className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground">
          {editingId ? "Edit site" : "Add a site"}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {editingId
            ? "Update the plot details or the supervisor on site."
            : "Register a client site. Use the plot number as the name, the way it is called on the ground."}
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="client" className={labelClass}>
                Client
              </label>
              <input
                id="client"
                type="text"
                value={form.client}
                onChange={(e) => set("client", e.target.value)}
                placeholder="e.g. Sterling Oil"
                className={fieldClass}
              />
            </div>

            <div>
              <label htmlFor="name" className={labelClass}>
                Location name
              </label>
              <input
                id="name"
                type="text"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. 217B or OML13A"
                required
                className={fieldClass}
              />
            </div>

            <div>
              <label htmlFor="area" className={labelClass}>
                Area
              </label>
              <select
                id="area"
                value={form.area}
                onChange={(e) => set("area", e.target.value)}
                className={fieldClass}
              >
                <option value="">Select an area</option>
                {AREAS.map((area) => (
                  <option key={area} value={area}>
                    {area}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="supervisorName" className={labelClass}>
                Supervisor
              </label>
              <input
                id="supervisorName"
                type="text"
                value={form.supervisorName}
                onChange={(e) => set("supervisorName", e.target.value)}
                placeholder="Who the technician meets on site"
                className={fieldClass}
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="supervisorPhone" className={labelClass}>
                Supervisor phone
              </label>
              <input
                id="supervisorPhone"
                type="tel"
                value={form.supervisorPhone}
                onChange={(e) => set("supervisorPhone", e.target.value)}
                placeholder="e.g. 08012345678"
                className={fieldClass}
              />
            </div>
          </div>

          {error && (
            <p className="text-xs font-medium text-red-600">{error}</p>
          )}

          <div className="flex gap-3">
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin" />
                  {editingId ? "Saving..." : "Adding site..."}
                </span>
              ) : editingId ? (
                "Save changes"
              ) : (
                "Add site"
              )}
            </Button>

            {editingId && (
              <Button
                type="button"
                size="lg"
                variant="outline"
                onClick={cancelEdit}
                disabled={submitting}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>
      </section>

      {saved && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />
          {saved}
        </div>
      )}

      {/* ---- List ---- */}
      <section className="rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">Sites</h2>
          <span className="text-sm text-muted-foreground">
            {active.length} active
            {inactive.length > 0 && `, ${inactive.length} inactive`}
          </span>
        </div>

        {loading ? (
          <p className="px-6 py-8 text-sm text-muted-foreground">
            Loading sites...
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
        ) : locations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
            <MapPin className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No sites yet. Add the first plot using the form above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-6 py-3 font-medium">Location</th>
                  <th className="px-6 py-3 font-medium">Area</th>
                  <th className="px-6 py-3 font-medium">Client</th>
                  <th className="px-6 py-3 font-medium">Supervisor</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {[...active, ...inactive].map((location) => (
                  <tr
                    key={location.id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-6 py-3 font-medium text-foreground">
                      {location.name}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {location.area ?? "--"}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {location.client ?? "--"}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {location.supervisorName ? (
                        <span>
                          {location.supervisorName}
                          {location.supervisorPhone && (
                            <span className="block text-xs">
                              {location.supervisorPhone}
                            </span>
                          )}
                        </span>
                      ) : (
                        "--"
                      )}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={
                          location.isActive
                            ? "rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
                            : "rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
                        }
                      >
                        {location.isActive ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => startEdit(location)}
                        >
                          <Pencil className="mr-1 size-3" />
                          Edit
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={busyId === location.id}
                          onClick={() => toggleActive(location)}
                        >
                          {busyId === location.id ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : location.isActive ? (
                            <>
                              <X className="mr-1 size-3" />
                              Deactivate
                            </>
                          ) : (
                            "Reactivate"
                          )}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
