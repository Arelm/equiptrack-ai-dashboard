"use client"

import { useState } from "react"
import { Check, ChevronDown, Loader2 } from "lucide-react"
import { apiFetch } from "@/lib/authClient"

type Technician = { id: string; name: string }

type Props = {
  workOrderId: string
  current: { id: string; name: string | null; accepted: boolean } | null
  technicians: Technician[]
  disabled?: boolean
  onAssigned: () => void
}

/** The single highest-value control in the product.
 *
 *  Before this, the Technician column rendered a hardcoded null and every ticket
 *  in the queue read "Unassigned" — not because nobody was assigned, but because
 *  nothing could be. Parts, response time, SLA and accountability all hang off it.
 *
 *  Reassignment demands a reason. It is not an overwrite: the backend closes the
 *  previous row and opens a new one, or the history credits the second technician
 *  for work the first started.
 */
export function AssignControl({ workOrderId, current, technicians, disabled, onAssigned }: Props) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Technician | null>(null)
  const [reason, setReason] = useState("")

  async function assign(tech: Technician, why?: string) {
    setBusy(true)
    setError(null)
    try {
      const res = await apiFetch(`/api/workorders/${workOrderId}/assign`, {
        method: "POST",
        body: JSON.stringify({ userId: tech.id, reason: why ?? null }),
      })
      if (!res.ok) {
        const detail = (await res.json().catch(() => ({}))).detail
        setError(typeof detail === "string" ? detail : "Assignment failed.")
        return
      }
      setOpen(false)
      setPending(null)
      setReason("")
      onAssigned()
    } catch {
      setError("No connection.")
    } finally {
      setBusy(false)
    }
  }

  function choose(tech: Technician) {
    if (current) {
      setPending(tech)   // reassignment needs a reason first
    } else {
      assign(tech)
    }
  }

  if (disabled) {
    return current ? (
      <span className="text-foreground">{current.name}</span>
    ) : (
      <span className="italic text-muted-foreground/60">Unassigned</span>
    )
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 rounded px-2 py-1 -mx-2 text-left hover:bg-muted"
      >
        {current ? (
          <span className="flex items-center gap-1.5">
            <span className="text-foreground">{current.name}</span>
            {current.accepted ? (
              <Check className="size-3.5 text-emerald-600" aria-label="accepted" />
            ) : (
              <span className="text-[10px] font-medium text-amber-600">pending</span>
            )}
          </span>
        ) : (
          <span className="italic text-muted-foreground/60">Assign…</span>
        )}
        <ChevronDown className="size-3.5 text-muted-foreground" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-64 rounded-lg border border-border bg-card p-1 shadow-lg">
          {pending ? (
            <div className="space-y-2 p-2">
              <p className="text-xs text-muted-foreground">
                Reassigning to <span className="font-medium text-foreground">{pending.name}</span>.
                Reason is written to the audit log.
              </p>
              <input
                autoFocus
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. moved to Sterling Oil site"
                className="w-full rounded border border-input bg-background px-2 py-1.5 text-xs outline-none focus:border-ring"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy || !reason.trim()}
                  onClick={() => assign(pending, reason.trim())}
                  className="flex-1 rounded bg-primary px-2 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50"
                >
                  {busy ? <Loader2 className="mx-auto size-3.5 animate-spin" /> : "Confirm"}
                </button>
                <button
                  type="button"
                  onClick={() => { setPending(null); setReason("") }}
                  className="rounded border border-border px-2 py-1.5 text-xs"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              {technicians.length === 0 && (
                <p className="px-2 py-3 text-xs text-muted-foreground">
                  No technicians on the roster.
                </p>
              )}
              {technicians.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  disabled={busy}
                  onClick={() => choose(t)}
                  className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-xs hover:bg-muted disabled:opacity-50"
                >
                  <span>{t.name}</span>
                  {current?.id === t.id && <Check className="size-3.5 text-emerald-600" />}
                </button>
              ))}
            </>
          )}

          {error && <p className="px-2 py-1.5 text-xs text-destructive">{error}</p>}
        </div>
      )}
    </div>
  )
}