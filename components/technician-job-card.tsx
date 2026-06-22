"use client"

import { useState } from "react"
import { MapPin, Clock, CheckCircle2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PriorityBadge, StatusBadge } from "@/components/badges"
import { updateWorkOrderStatus, mapPriority, mapStatus } from "@/lib/api"
import type { BackendWorkOrder, BackendAsset, BackendLocation } from "@/lib/api"

type Props = {
  wo: BackendWorkOrder
  asset: BackendAsset | undefined
  location: BackendLocation | undefined
}

const STATUS_FLOW: Record<string, { label: string; next: string } | null> = {
  OPEN: { label: "Accept Job", next: "IN_PROGRESS" },
  IN_PROGRESS: { label: "Mark Complete", next: "COMPLETED" },
  COMPLETED: null,
  ON_HOLD: null,
  CANCELLED: null,
}

export function TechnicianJobCard({ wo, asset, location }: Props) {
  const [status, setStatus] = useState(wo.status)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const action = STATUS_FLOW[status] ?? null

  async function handleStatusUpdate() {
    if (!action) return
    setUpdating(true)
    setError(null)
    try {
      const updated = await updateWorkOrderStatus(wo.id, action.next)
      setStatus(updated.status)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status")
    } finally {
      setUpdating(false)
    }
  }

  return (
    <li className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs font-medium text-primary">
            {wo.id.slice(0, 8).toUpperCase()}
          </p>
          <p className="mt-1 text-sm font-semibold text-foreground">
            {asset?.name ?? "—"}
          </p>
          <p className="text-xs text-muted-foreground">{location?.name ?? "—"}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <PriorityBadge priority={mapPriority(wo.priority)} />
          <StatusBadge status={mapStatus(status)} />
        </div>
      </div>

      {wo.description && (
        <p className="mt-3 text-sm text-foreground">{wo.description}</p>
      )}

      <div className="mt-3 flex flex-col gap-1.5 border-t border-border pt-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <MapPin className="size-3.5 shrink-0" />
          {location?.address ?? "Address not set"}
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="size-3.5 shrink-0" />
          {new Date(wo.createdAt).toLocaleDateString("en-US", {
            month: "short", day: "numeric", year: "numeric",
          })}
        </span>
      </div>

      {error && (
        <p className="mt-2 text-xs font-medium text-red-600">{error}</p>
      )}

      {status === "COMPLETED" ? (
        <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald-600">
          <CheckCircle2 className="size-4" />
          Job completed
        </div>
      ) : action ? (
        <Button
          size="sm"
          className="mt-3 w-full"
          onClick={handleStatusUpdate}
          disabled={updating}
        >
          {updating ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="size-3.5 animate-spin" />
              Updating...
            </span>
          ) : (
            action.label
          )}
        </Button>
      ) : null}
    </li>
  )
}