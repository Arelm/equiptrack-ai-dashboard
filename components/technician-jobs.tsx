"use client"

import { useCallback, useEffect, useState } from "react"
import { Clock, ChevronDown, MapPin } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PriorityBadge, StatusBadge } from "@/components/badges"
import { mapPriority, mapStatus } from "@/lib/api"
import { FieldReportForm, type CatalogPart } from "@/components/field-report-form"
import { apiFetch, getUser } from "@/lib/authClient"

type Job = {
  id: string
  title: string
  description: string | null
  priority: string | null
  status: string | null
  assignedAt: string | null
  acceptedAt: string | null
  accepted: boolean
  ageHours: number | null
  assetName: string | null
  locationName: string | null
  address: string | null
}

function ageLabel(hours: number | null) {
  if (hours === null) return "—"
  if (hours < 1) return "just now"
  if (hours < 24) return `${Math.round(hours)}h`
  return `${Math.round(hours / 24)}d`
}

export function TechnicianJobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [parts, setParts] = useState<CatalogPart[]>([])
  const [openJob, setOpenJob] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const user = getUser()
      const [jobsRes, partsRes] = await Promise.all([
        apiFetch("/api/workorders/mine"),
        user ? apiFetch(`/api/parts/?organizationId=${encodeURIComponent(user.orgId)}`) : null,
      ])
      if (!jobsRes.ok) throw new Error("Could not load your jobs.")
      setJobs(await jobsRes.json())
      if (partsRes?.ok) setParts(await partsRes.json())
      setError(null)
    } catch {
      setError("Could not reach the server. Pull down to retry.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function accept(id: string) {
    const res = await apiFetch(`/api/workorders/${id}/accept`, { method: "POST" })
    if (res.ok) load()
  }

  if (loading) {
    return <p className="px-1 py-8 text-center text-sm text-muted-foreground">Loading your jobs…</p>
  }
  if (error) {
    return <p className="rounded-xl bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</p>
  }
  if (jobs.length === 0) {
    return (
      <p className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
        No jobs assigned to you.
      </p>
    )
  }

  const unaccepted = jobs.filter((j) => !j.accepted).length

  return (
    <div className="space-y-3">
      {unaccepted > 0 && (
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">
          {unaccepted} job{unaccepted !== 1 ? "s" : ""} waiting for you to accept
        </div>
      )}

      {jobs.map((job) => (
        <div key={job.id} className="rounded-xl border border-border bg-card shadow-sm">
          <div className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-mono text-muted-foreground">
                  {job.id.slice(0, 8).toUpperCase()}
                </p>
                <p className="truncate text-sm font-semibold text-foreground">
                  {job.assetName ?? job.title}
                </p>
                {job.locationName && (
                  <p className="text-xs text-muted-foreground">{job.locationName}</p>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <PriorityBadge priority={mapPriority(job.priority ?? "")} />
                <StatusBadge status={mapStatus(job.status ?? "")} />
              </div>
            </div>

            {job.description && (
              <p className="mt-3 text-sm text-foreground">{job.description}</p>
            )}

            <div className="mt-3 flex flex-col gap-1.5 border-t border-border pt-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <MapPin className="size-3.5 shrink-0" />
                {job.address ?? "Address not set"}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="size-3.5 shrink-0" />
                Assigned {ageLabel(job.ageHours)} ago
                {!job.accepted && <span className="font-medium text-amber-700">· not accepted</span>}
              </span>
            </div>

            <div className="mt-4">
              {!job.accepted ? (
                <Button className="w-full" onClick={() => accept(job.id)}>
                  Accept job
                </Button>
              ) : (
                // One path to completion. The report is the completion.
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setOpenJob(openJob === job.id ? null : job.id)}
                >
                  Mark complete & file report
                  <ChevronDown
                    className={`ml-1.5 size-4 transition-transform ${
                      openJob === job.id ? "rotate-180" : ""
                    }`}
                  />
                </Button>
              )}
            </div>
          </div>

          {openJob === job.id && job.accepted && (
            <div className="border-t border-border p-4">
              <FieldReportForm
                workOrderId={job.id}
                workOrderTitle={job.title}
                parts={parts}
                onSubmitted={() => {
                  setOpenJob(null)
                  load()
                }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}