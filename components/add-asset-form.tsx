"use client"

import { useState } from "react"
import { CheckCircle2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { createAsset, type BackendLocation } from "@/lib/api"

const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

const CATEGORIES = [
  "HVAC",
  "Electrical",
  "Plumbing",
  "Mechanical",
  "Fire Safety",
  "Lifting Equipment",
  "Other",
]

type Props = {
  organizationId: string
  locations: BackendLocation[]
  onSuccess?: () => void
}

export function AddAssetForm({ organizationId, locations, onSuccess }: Props) {
  const [name, setName] = useState("")
  const [category, setCategory] = useState("")
  const [locationId, setLocationId] = useState("")
  const [serialNumber, setSerialNumber] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await createAsset({
        name,
        category,
        organizationId,
        locationId: locationId || undefined,
        serialNumber: serialNumber || undefined,
      })
      setSubmitted(true)
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add asset.")
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-8 text-center">
        <CheckCircle2 className="size-10 text-emerald-600" />
        <div>
          <p className="text-sm font-semibold text-emerald-800">Asset added</p>
          <p className="mt-1 text-xs text-emerald-700">
            The new asset has been registered and is ready for service requests.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setSubmitted(false)
            setName("")
            setCategory("")
            setLocationId("")
            setSerialNumber("")
          }}
        >
          Add another asset
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="asset-name" className="text-xs font-medium text-foreground">
          Asset Name
        </label>
        <input
          id="asset-name"
          required
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Chiller Unit CH-03"
          className={fieldClass}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="category" className="text-xs font-medium text-foreground">
          Category
        </label>
        <select
          id="category"
          required
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className={fieldClass}
        >
          <option value="" disabled>Select a category</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="asset-location" className="text-xs font-medium text-foreground">
          Facility
        </label>
        <select
          id="asset-location"
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
          className={fieldClass}
        >
          <option value="">No facility assigned</option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="serial" className="text-xs font-medium text-foreground">
          Serial Number <span className="text-muted-foreground">(optional)</span>
        </label>
        <input
          id="serial"
          type="text"
          value={serialNumber}
          onChange={(e) => setSerialNumber(e.target.value)}
          placeholder="e.g. SN-2024-00123"
          className={fieldClass}
        />
      </div>

      {error && (
        <p className="text-xs font-medium text-red-600">{error}</p>
      )}

      <Button type="submit" size="lg" className="w-full" disabled={submitting}>
        {submitting ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="size-4 animate-spin" />
            Adding asset...
          </span>
        ) : (
          "Add Asset"
        )}
      </Button>
    </form>
  )
}