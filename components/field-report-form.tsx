"use client"

import { useEffect, useState } from "react"
import { AlertCircle, CheckCircle2, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { apiFetch } from "@/lib/authClient"

const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

const SOURCES = [
  { value: "van_stock", label: "Van stock" },
  { value: "company_store", label: "Company store" },
  { value: "purchased_on_site", label: "Purchased on site" },
  { value: "client_supplied", label: "Client supplied" },
] as const

const NOT_LISTED = "__not_listed__"

export type CatalogPart = {
  id: string
  name: string
  partNumber: string | null
  quantity: number
  lowStock: boolean
}

type PartLine = {
  key: string
  partId: string
  partNameRaw: string
  quantity: number
  source: string
}

type Props = {
  /** The job this report belongs to. Taken from the card it opens from — never
   *  chosen from a dropdown. The Daikin/Gree mis-attribution was a dropdown
   *  selection error, so the dropdown is gone. */
  workOrderId: string
  workOrderTitle: string
  parts: CatalogPart[]
  onSubmitted?: () => void
}

const draftKey = (id: string) => `equiptrack_report_draft_${id}`

export function FieldReportForm({ workOrderId, workOrderTitle, parts, onSubmitted }: Props) {
  const [notes, setNotes] = useState("")
  const [hoursSpent, setHoursSpent] = useState("")
  const [declaration, setDeclaration] = useState<"" | "none" | "some">("")
  const [lines, setLines] = useState<PartLine[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [restored, setRestored] = useState(false)

  // --- Draft restore -------------------------------------------------------
  // Plant rooms and basements have no usable signal at the moment a job
  // finishes. A form that loses the technician's work teaches him to stop
  // using the app, and that lesson is permanent.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(draftKey(workOrderId))
      if (!raw) return
      const d = JSON.parse(raw)
      setNotes(d.notes ?? "")
      setHoursSpent(d.hoursSpent ?? "")
      setDeclaration(d.declaration ?? "")
      setLines(d.lines ?? [])
      setRestored(true)
    } catch {
      /* a corrupt draft is not worth an error */
    }
  }, [workOrderId])

  // --- Draft save ----------------------------------------------------------
  useEffect(() => {
    if (submitted) return
    if (!notes && !declaration && lines.length === 0) return
    try {
      localStorage.setItem(
        draftKey(workOrderId),
        JSON.stringify({ notes, hoursSpent, declaration, lines }),
      )
    } catch {
      /* storage full or blocked — never block the form on it */
    }
  }, [workOrderId, notes, hoursSpent, declaration, lines, submitted])

  function addLine() {
    setLines((prev) => [
      ...prev,
      {
        key: `${Date.now()}-${prev.length}`,
        partId: "",
        partNameRaw: "",
        quantity: 1,
        source: "van_stock",
      },
    ])
  }

  function updateLine(key: string, patch: Partial<PartLine>) {
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)))
  }

  function removeLine(key: string) {
    setLines((prev) => {
      const next = prev.filter((l) => l.key !== key)
      // Removing the last line means he has not decided yet, not that he
      // declared zero parts. Fall back to undecided rather than leaving him
      // in a state the form will reject on submit.
      if (next.length === 0) setDeclaration("")
      return next
    })
    setError(null)
  }

  function chooseDeclaration(choice: "none" | "some") {
    // Pressing the selected button again deselects it. Without this, a
    // technician who taps "Add parts" by accident is stuck: the form demands a
    // line he does not have, and the way out is to press a different button he
    // has no reason to think is the answer.
    if (declaration === choice) {
      setDeclaration("")
      setLines([])
      setError(null)
      return
    }
    setDeclaration(choice)
    setError(null)
    if (choice === "some" && lines.length === 0) addLine()
    if (choice === "none") setLines([])
  }

  async function handleSubmit() {
    setError(null)

    if (!notes.trim()) return setError("Work notes are required.")
    if (!declaration) {
      return setError('Say whether parts were used. "No parts needed" is a valid answer.')
    }
    if (declaration === "some") {
     if (lines.length === 0) {
        return setError(
          'No parts added. Press "No parts needed" if none were used, or add a part below.',
        )
      } 
      for (const l of lines) {
        if (!l.partId) return setError("Every line needs a part selected.")
        if (l.partId === NOT_LISTED && !l.partNameRaw.trim()) {
          return setError("Type the name of the part that is not listed.")
        }
        if (!l.quantity || l.quantity < 1) return setError("Quantity must be at least 1.")
      }
    }

    setSubmitting(true)
    try {
      const res = await apiFetch(`/api/workorders/${workOrderId}/report`, {
        method: "POST",
        body: JSON.stringify({
          notes: notes.trim(),
          hoursSpent: hoursSpent ? Number(hoursSpent) : null,
          partsUsed: declaration === "some",
          parts: lines.map((l) => ({
            partId: l.partId === NOT_LISTED ? null : l.partId,
            partNameRaw: l.partId === NOT_LISTED ? l.partNameRaw.trim() : null,
            quantity: Number(l.quantity),
            source: l.source,
          })),
        }),
      })

      if (!res.ok) {
        const detail = (await res.json().catch(() => ({}))).detail
        setError(typeof detail === "string" ? detail : `Submission failed (${res.status}).`)
        return
      }

      localStorage.removeItem(draftKey(workOrderId))
      setSubmitted(true)
      onSubmitted?.()
    } catch {
      // Never say "error, try again" — that reads as your work is gone.
      setError("No connection. Your report is saved on this device and will submit when you retry.")
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-8 text-center">
        <CheckCircle2 className="size-10 text-emerald-600" />
        <div>
          <p className="text-sm font-semibold text-emerald-800">Report filed</p>
          <p className="mt-1 text-xs text-emerald-700">
            Job marked complete and stock updated.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg bg-muted px-3 py-2">
        <p className="text-xs text-muted-foreground">Filing report for</p>
        <p className="text-sm font-medium text-foreground">
          {workOrderId.slice(0, 8).toUpperCase()} — {workOrderTitle}
        </p>
      </div>

      {restored && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Unsent draft restored from this device.
        </p>
      )}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="notes" className="text-xs font-medium text-foreground">
          Work notes
        </label>
        <textarea
          id="notes"
          rows={4}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Describe the work performed, findings, and resolution..."
          className={`${fieldClass} resize-none`}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="hours" className="text-xs font-medium text-foreground">
          Hours on site <span className="text-muted-foreground">(optional)</span>
        </label>
        <input
          id="hours"
          type="number"
          min="0"
          step="0.25"
          value={hoursSpent}
          onChange={(e) => setHoursSpent(e.target.value)}
          className={fieldClass}
        />
      </div>

      {/* Explicit declaration. An empty parts list is ambiguous: no parts needed,
          or nobody logged them. Those are different facts. */}
      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium text-foreground">Parts used</span>
        <div className="grid grid-cols-2 gap-2">
          <Button
            type="button"
            variant={declaration === "none" ? "default" : "outline"}
            onClick={() => chooseDeclaration("none")}
          >
            No parts needed
          </Button>
          <Button
            type="button"
            variant={declaration === "some" ? "default" : "outline"}
            onClick={() => chooseDeclaration("some")}
          >
            Add parts
          </Button>
        </div>
      </div>

      {declaration === "some" && (
        <div className="flex flex-col gap-3">
          {lines.map((line) => (
            <div key={line.key} className="rounded-lg border border-border p-3">
              <div className="flex items-start gap-2">
                <div className="flex-1 space-y-2">
                  <select
                    value={line.partId}
                    onChange={(e) => updateLine(line.key, { partId: e.target.value })}
                    className={fieldClass}
                    aria-label="Part"
                  >
                    <option value="">Select a part</option>
                    {parts.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                        {p.partNumber ? ` (${p.partNumber})` : ""} — {p.quantity} in stock
                      </option>
                    ))}
                    <option value={NOT_LISTED}>Part not listed…</option>
                  </select>

                  {line.partId === NOT_LISTED && (
                    <input
                      value={line.partNameRaw}
                      onChange={(e) => updateLine(line.key, { partNameRaw: e.target.value })}
                      placeholder="Type the part name — it will be queued for review"
                      className={fieldClass}
                    />
                  )}

                  <div className="flex gap-2">
                    <div className="w-24">
                      <input
                        type="number"
                        min="1"
                        value={line.quantity}
                        onChange={(e) =>
                          updateLine(line.key, { quantity: Number(e.target.value) })
                        }
                        className={fieldClass}
                        aria-label="Quantity"
                      />
                    </div>
                    <select
                      value={line.source}
                      onChange={(e) => updateLine(line.key, { source: e.target.value })}
                      className={fieldClass}
                      aria-label="Source"
                    >
                      {SOURCES.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => removeLine(line.key)}
                  aria-label="Remove part line"
                  className="rounded p-1 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              </div>
            </div>
          ))}

          <Button type="button" variant="outline" onClick={addLine} className="w-full">
            <Plus className="mr-1.5 size-4" />
            Add another part
          </Button>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2">
          <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
          <p className="text-xs text-destructive">{error}</p>
        </div>
      )}

      <Button type="button" size="lg" className="w-full" disabled={submitting} onClick={handleSubmit}>
        {submitting ? "Submitting…" : "Submit report & complete job"}
      </Button>
    </div>
  )
}