"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  createWorkOrder,
  toBackendPriority,
  fetchPrimaryOrganization,
  fetchLocations,
  fetchAssets,
  type BackendOrganization,
  type BackendLocation,
  type BackendAsset,
} from "@/lib/api"

const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

const priorities = ["Critical", "High", "Medium", "Low"] as const
type Priority = (typeof priorities)[number]

const clientCategories = ["AC Works", "Electrical", "Plumbing", "Civil", "Other"]

function today(): string {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10)
}

function readableError(message: string): string {
  if (/failed to fetch/i.test(message)) {
    return "Could not reach the server. Check your connection and try again."
  }
  if (/\b401\b|\b403\b/.test(message)) {
    return "Your session has expired. Sign in again to save this ticket."
  }
  if (/\b422\b/.test(message)) {
    return "The server rejected this ticket. Check the site and asset are still valid."
  }
  if (/\b5\d{2}\b/.test(message)) {
    return "The server had a problem saving this ticket. Try again in a moment."
  }
  return "Could not save the ticket. Try again."
}

export function TicketEntryForm() {
  const [org, setOrg] = useState<BackendOrganization | null>(null)
  const [locations, setLocations] = useState<BackendLocation[]>([])
  const [assets, setAssets] = useState<BackendAsset[]>([])
  const [loadingRefs, setLoadingRefs] = useState(true)
  const [refError, setRefError] = useState<string | null>(null)

  const [dateReported, setDateReported] = useState(today())
  const [raisedBy, setRaisedBy] = useState("")
  const [locationId, setLocationId] = useState("")
  const [assetId, setAssetId] = useState("")
  const [clientCategory, setClientCategory] = useState(clientCategories[0])
  const [priority, setPriority] = useState<Priority>("Medium")
  const [title, setTitle] = useState("")
  const [complaint, setComplaint] = useState("")

  const [submitting, setSubmitting] = useState(false)
  const [saved, setSaved] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const organization = await fetchPrimaryOrganization()
        if (cancelled) return
        setOrg(organization)

        const [locs, asts] = await Promise.all([
          fetchLocations(organization.id),
          fetchAssets(organization.id),
        ])
        if (cancelled) return

        setLocations(locs)
        setAssets(asts)
      } catch {
        if (cancelled) return
        setRefError("Could not load sites and assets.")
      } finally {
        if (!cancelled) setLoadingRefs(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const assetsForLocation = useMemo(() => {
    if (!locationId) return assets
    return assets.filter((a) => a.locationId === locationId)
  }, [assets, locationId])

  function handleLocationChange(value: string) {
    setLocationId(value)
    setAssetId("")
  }

  function resetForNextSheet() {
    setRaisedBy("")
    setAssetId("")
    setTitle("")
    setComplaint("")
    setPriority("Medium")
    setClientCategory(clientCategories[0])
  }

  async function handleSubmit() {
    if (!org) return
    if (!title.trim()) {
      setError("Enter a fault title before saving.")
      return
    }

    setSubmitting(true)
    setError(null)
    setSaved(null)

    const descriptionLines = [
      `Date reported: ${dateReported}`,
      `Raised by: ${raisedBy.trim() || "Not recorded"}`,
      `Client category: ${clientCategory}`,
      "",
      complaint.trim() || "No further detail on the sheet.",
    ]

    try {
      const created = await createWorkOrder({
        title: title.trim(),
        description: descriptionLines.join("\n"),
        priority: toBackendPriority(priority),
        organizationId: org.id,
        assetId: assetId || undefined,
        locationId: locationId || undefined,
      })
      setSaved(created.title)
      resetForNextSheet()
    } catch (err) {
      setError(readableError(err instanceof Error ? err.message : ""))
    } finally {
      setSubmitting(false)
    }
  }

  if (loadingRefs) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading sites and assets
      </div>
    )
  }

  if (refError) {
    return (
      <p className="py-8 text-sm text-destructive">
        {refError} Reload the page to try again.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Date reported
          </span>
          <input
            type="date"
            value={dateReported}
            onChange={(e) => setDateReported(e.target.value)}
            className={fieldClass}
          />
        </label>

        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Raised by
          </span>
          <input
            type="text"
            value={raisedBy}
            onChange={(e) => setRaisedBy(e.target.value)}
            placeholder="Name on the sheet"
            className={fieldClass}
          />
        </label>
      </div>

      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">Site</span>
        <select
          value={locationId}
          onChange={(e) => handleLocationChange(e.target.value)}
          className={fieldClass}
        >
          <option value="">No site recorded</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name}
            </option>
          ))}
        </select>
      </label>

      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">Asset</span>
        <select
          value={assetId}
          onChange={(e) => setAssetId(e.target.value)}
          className={fieldClass}
        >
          <option value="">No asset recorded</option>
          {assetsForLocation.map((asset) => (
            <option key={asset.id} value={asset.id}>
              {asset.name} — {asset.category}
            </option>
          ))}
        </select>
        {locationId && assetsForLocation.length === 0 && (
          <span className="text-xs text-muted-foreground">
            No assets registered at this site yet.
          </span>
        )}
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Client category
          </span>
          <select
            value={clientCategory}
            onChange={(e) => setClientCategory(e.target.value)}
            className={fieldClass}
          >
            {clientCategories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Priority
          </span>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
            className={fieldClass}
          >
            {priorities.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">
          Fault title
        </span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="AC not cooling — Admin block"
          className={fieldClass}
        />
      </label>

      <label className="block space-y-1">
        <span className="text-xs font-medium text-muted-foreground">
          Complaint as written
        </span>
        <textarea
          value={complaint}
          onChange={(e) => setComplaint(e.target.value)}
          rows={4}
          placeholder="Copy the wording from the sheet"
          className={fieldClass}
        />
      </label>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {saved && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Check className="h-4 w-4" />
          Saved {saved}. Ready for the next sheet.
        </p>
      )}

      <Button onClick={handleSubmit} disabled={submitting} className="w-full">
        {submitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Saving ticket
          </>
        ) : (
          "Save ticket"
        )}
      </Button>
    </div>
  )
}
