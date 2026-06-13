"use client"

import { useState } from "react"
import { CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { facilities, assetsByFacility, type Priority } from "@/lib/data"

const priorities: Priority[] = ["High", "Medium", "Low"]
const fieldClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

export function ServiceRequestForm() {
  const [facility, setFacility] = useState("")
  const [asset, setAsset] = useState("")
  const [priority, setPriority] = useState<Priority>("Medium")
  const [fault, setFault] = useState("")
  const [submitted, setSubmitted] = useState(false)

  const assetOptions = facility ? assetsByFacility[facility] ?? [] : []

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitted(true)
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
            setFacility("")
            setAsset("")
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
          value={facility}
          onChange={(e) => {
            setFacility(e.target.value)
            setAsset("")
          }}
          className={fieldClass}
        >
          <option value="" disabled>
            Select a facility
          </option>
          {facilities.map((f) => (
            <option key={f} value={f}>
              {f}
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
          disabled={!facility}
          value={asset}
          onChange={(e) => setAsset(e.target.value)}
          className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-50`}
        >
          <option value="" disabled>
            {facility ? "Select an asset" : "Select a facility first"}
          </option>
          {assetOptions.map((a) => (
            <option key={a} value={a}>
              {a}
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

      <Button type="submit" size="lg" className="w-full">
        Submit Service Request
      </Button>
    </form>
  )
}
