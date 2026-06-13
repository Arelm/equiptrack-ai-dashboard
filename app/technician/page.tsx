import { MapPin, Clock } from "lucide-react"
import { PageHeader } from "@/components/page-header"
import { PriorityBadge } from "@/components/badges"
import { FieldReportForm } from "@/components/field-report-form"
import { technicianJobs } from "@/lib/data"

export default function TechnicianPage() {
  return (
    <>
      <PageHeader
        title="Technician App"
        description="Marcus Hill · 3 jobs assigned today"
      />

      <div className="mx-auto w-full max-w-md space-y-6 p-4 sm:max-w-2xl sm:p-6">
        <section>
          <h2 className="px-1 text-sm font-semibold text-foreground">Assigned Jobs</h2>
          <ul className="mt-3 space-y-3">
            {technicianJobs.map((job) => (
              <li
                key={job.id}
                className="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-xs font-medium text-primary">{job.id}</p>
                    <p className="mt-1 text-sm font-semibold text-foreground">{job.asset}</p>
                    <p className="text-xs text-muted-foreground">{job.client}</p>
                  </div>
                  <PriorityBadge priority={job.priority} />
                </div>
                <p className="mt-3 text-sm text-foreground">{job.fault}</p>
                <div className="mt-3 flex flex-col gap-1.5 border-t border-border pt-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="size-3.5 shrink-0" />
                    {job.address}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Clock className="size-3.5 shrink-0" />
                    {job.window}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-foreground">Submit Field Report</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Log your work, parts used, and resolution notes.
          </p>
          <div className="mt-5">
            <FieldReportForm />
          </div>
        </section>
      </div>
    </>
  )
}
