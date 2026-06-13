"use client"

import { useState } from "react"
import { CheckCircle2, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { technicianJobs, parts } from "@/lib/data"

const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

export function FieldReportForm() {
  const [jobId, setJobId] = useState(technicianJobs[0]?.id ?? "")
  const [notes, setNotes] = useState("")
  const [selectedPart, setSelectedPart] = useState("")
  const [partsUsed, setPartsUsed] = useState<string[]>([])
  const [submitted, setSubmitted] = useState(false)

  function addPart() {
    if (selectedPart && !partsUsed.includes(selectedPart)) {
      setPartsUsed((prev) => [...prev, selectedPart])
      setSelectedPart("")
    }
  }

  function removePart(sku: string) {
    setPartsUsed((prev) => prev.filter((p) => p !== sku))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-8 text-center">
        <CheckCircle2 className="size-10 text-emerald-600" />
        <div>
          <p className="text-sm font-semibold text-emerald-800">Report submitted</p>
          <p className="mt-1 text-xs text-emerald-700">
            Your field report has been logged and the ticket updated.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setSubmitted(false)
            setNotes("")
            setPartsUsed([])
            setSelectedPart("")
          }}
        >
          Submit another report
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="job" className="text-xs font-medium text-foreground">
          Job
        </label>
        <select
          id="job"
          value={jobId}
          onChange={(e) => setJobId(e.target.value)}
          className={fieldClass}
        >
          {technicianJobs.map((job) => (
            <option key={job.id} value={job.id}>
              {job.id} — {job.asset}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="notes" className="text-xs font-medium text-foreground">
          Work notes
        </label>
        <textarea
          id="notes"
          required
          rows={4}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Describe the work performed, findings, and resolution..."
          className={`${fieldClass} resize-none`}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="part" className="text-xs font-medium text-foreground">
          Parts used
        </label>
        <div className="flex gap-2">
          <select
            id="part"
            value={selectedPart}
            onChange={(e) => setSelectedPart(e.target.value)}
            className={fieldClass}
          >
            <option value="">Select a part to add</option>
            {parts.map((p) => (
              <option key={p.sku} value={p.sku}>
                {p.name} ({p.sku})
              </option>
            ))}
          </select>
          <Button type="button" variant="outline" size="icon-lg" onClick={addPart} aria-label="Add part">
            <Plus className="size-4" />
          </Button>
        </div>
        {partsUsed.length > 0 && (
          <ul className="mt-1 flex flex-wrap gap-2">
            {partsUsed.map((sku) => {
              const part = parts.find((p) => p.sku === sku)
              return (
                <li
                  key={sku}
                  className="flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground"
                >
                  {part?.name ?? sku}
                  <button
                    type="button"
                    onClick={() => removePart(sku)}
                    aria-label={`Remove ${part?.name ?? sku}`}
                    className="text-accent-foreground/60 hover:text-accent-foreground"
                  >
                    <X className="size-3" />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <Button type="submit" size="lg" className="w-full">
        Submit Report
      </Button>
    </form>
  )
}
