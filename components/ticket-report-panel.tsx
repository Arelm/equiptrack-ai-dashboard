"use client"

import { useEffect, useState } from "react"
import { ClipboardCheck, Package, Clock, User } from "lucide-react"
import { apiFetch } from "@/lib/authClient"

type PartLine = {
  id: string
  partId: string | null
  name: string | null
  fromCatalogue: boolean
  quantity: number
  unit?: string | null
  source: string | null
}

type Report = {
  id: string
  technician: { id: string; name: string | null }
  notes: string | null
  hoursSpent: number | null
  partsUsedDeclared: boolean | null
  createdAt: string | null
  parts: PartLine[]
}

const SOURCE_LABEL: Record<string, string> = {
  van_stock: "Van stock",
  company_store: "Company store",
  purchased_on_site: "Purchased on site",
  client_supplied: "Client supplied",
}

/** The field report, rendered where the operations manager actually looks.
 *
 *  The report endpoint existed and nothing called it, so parts were captured
 *  and then invisible — which is the same as not capturing them, from the
 *  manager's side of the desk.
 */
export function TicketReportPanel({ workOrderId }: { workOrderId: string }) {
  const [report, setReport] = useState<Report | null>(null)
  const [state, setState] = useState<"loading" | "ready" | "none">("loading")

  useEffect(() => {
    apiFetch(`/api/workorders/${workOrderId}/report`)
      .then(async (r) => {
        if (!r.ok) { setState("none"); return }
        setReport(await r.json())
        setState("ready")
      })
      .catch(() => setState("none"))
  }, [workOrderId])

  if (state === "loading") return null

  if (state === "none" || !report) {
    return (
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-2">
          <ClipboardCheck size={20} className="text-muted-foreground" />
          <h2 className="font-semibold">Field Report</h2>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          No report filed for this job yet.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClipboardCheck size={20} className="text-primary" />
          <h2 className="font-semibold">Field Report</h2>
        </div>
        {report.createdAt && (
          <span className="text-xs text-muted-foreground">
            Filed {new Date(report.createdAt).toLocaleDateString("en-US", {
              month: "short", day: "numeric", year: "numeric",
            })}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-4 text-sm">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          <User size={14} />
          {report.technician?.name ?? "—"}
        </span>
        {report.hoursSpent != null && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Clock size={14} />
            {report.hoursSpent} hours on site
          </span>
        )}
      </div>

      {report.notes && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Work done
          </p>
          <p className="mt-1 text-sm text-foreground">{report.notes}</p>
        </div>
      )}

      <div>
        <div className="flex items-center gap-2">
          <Package size={14} className="text-muted-foreground" />
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Parts used
          </p>
        </div>

        {/* Three distinct facts, never collapsed: declared none, logged some,
            or never asked (legacy rows filed before the declaration existed). */}
        {report.partsUsedDeclared === false ? (
          <p className="mt-2 text-sm text-muted-foreground">
            No parts needed — declared by the technician.
          </p>
        ) : report.parts.length === 0 ? (
          <p className="mt-2 text-sm italic text-muted-foreground">
            Not recorded. This report predates the parts declaration.
          </p>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Part</th>
                  <th className="pb-2 pr-4 font-medium">Qty</th>
                  <th className="pb-2 font-medium">Source</th>
                </tr>
              </thead>
              <tbody>
                {report.parts.map((p) => (
                  <tr key={p.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4 text-foreground">
                      {p.name ?? "—"}
                      {!p.fromCatalogue && (
                        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
                          not in catalogue
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4 whitespace-nowrap text-foreground">
                      {p.quantity}{p.unit ? ` ${p.unit}` : ""}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {SOURCE_LABEL[p.source ?? ""] ?? p.source ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}