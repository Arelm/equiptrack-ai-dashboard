"use client"

import { useState, useEffect } from "react"
import { CheckCircle2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Priority } from "@/lib/data"
import {
  fetchPrimaryOrganization,
  fetchLocations,
  fetchAssets,
  createWorkOrder,
  toBackendPriority,
  type BackendOrganization,
  type BackendLocation,
  type BackendAsset,
} from "@/lib/api"

const priorities: Priority[] = ["High", "Medium", "Low"]
const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

export function ServiceRequestForm() {
  // Reference data, loaded once on mount
  const [org, setOrg] = useState<BackendOrganization | null>(null)
  const [locations, setLocations] = useState<BackendLocation[]>([])
  const [assets, setAssets] = useState<BackendAsset[]>([])
  const [loadingRefData, setLoadingRefData] = useState(true)
  const [refDataError, setRefDataError] = useState<string | null>(null)

  // Form fields
  const [locationId, setLocationId] = useState("")
  const [assetId, setAssetId] = useState("")
  const [priority, setPriority] = useState<Priority>("Medium")
  const [fault, setFault] = useState("")

  // Submission state
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const organization = await fetchPrimaryOrganization()
        const [locs, asts] = await Promise.all([
          fetchLocations(organization.id),
          fetchAssets(organization.id),
        ])
        if (cancelled) return
        setOrg(organization)
        setLocations(locs)
        setAssets(asts)
      } catch (err) {
        if (!cancelled) {
          setRefDataError(
            err instanceof Error ? err.message : "Failed to load facilities and assets.",
          )
        }
      } finally {
        if (!cancelled) setLoadingRefData(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const assetOptions = locationId ? assets.filter((a) => a.locationId === locationId) : []

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!org) return
    setSubmitting(true)
    setSubmitError(null)

    const selectedAsset = assets.find((a) => a.id === assetId)
    const title = selectedAsset
      ? `${selectedAsset.name} - Service Request`
      : "Service Request"

    try {
      await createWorkOrder({
        title,
        description: fault,
        priority: toBackendPriority(priority),
        organizationId: org.id,
        assetId: assetId || undefined,
        locationId: locationId || undefined,
      })
      setSubmitted(true)
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to submit request. Please try again.",
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (loadingRefData) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-8 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Loading facilities and assets...
      </div>
    )
  }

  if (refDataError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-center text-sm text-red-700">
        {refDataError}
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-8 text-center">
        <CheckCircle2 className="size-10 text-emerald-600" />
        <div>
          <p className="text-sm font-semibold text-emerald-800">Request submitted</p>
          <p className="mt-1 text-xs text-emerald-700">
            Your ticket has been created and queued for dispatch.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setSubmitted(false)
            setLocationId("")
            setAssetId("")
            setPriority("Medium")
            setFault("")
          }}
        >
          Submit another request
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="facility" className="text-xs font-medium text-foreground">
          Facility
        </label>
        <select
          id="facility"
          required
          value={locationId}
          onChange={(e) => {
            setLocationId(e.target.value)
            setAssetId("")
          }}
          className={fieldClass}
        >
          <option value="" disabled>
            Select a facility
          </option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="asset" className="text-xs font-medium text-foreground">
          Asset
        </label>
        <select
          id="asset"
          required
          disabled={!locationId}
          value={assetId}
          onChange={(e) => setAssetId(e.target.value)}
          className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-50`}
        >
          <option value="" disabled>
            {locationId ? "Select an asset" : "Select a facility first"}
          </option>
          {assetOptions.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-foreground">Priority</span>
        <div className="grid grid-cols-3 gap-2">
          {priorities.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriority(p)}
              className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                priority === p
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input bg-background text-muted-foreground hover:border-ring hover:text-foreground"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="fault" className="text-xs font-medium text-foreground">
          Describe the fault
        </label>
        <textarea
          id="fault"
          required
          rows={4}
          value={fault}
          onChange={(e) => setFault(e.target.value)}
          placeholder="Describe the issue, symptoms, and any error codes..."
          className={`${fieldClass} resize-none`}
        />
      </div>

      {submitError && (
        <p className="text-xs font-medium text-red-600">{submitError}</p>
      )}

      <Button type="submit" size="lg" className="w-full" disabled={submitting}>
        {submitting ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="size-4 animate-spin" />
            Submitting...
          </span>
        ) : (
          "Submit Service Request"
        )}
      </Button>
    </form>
  )
}
