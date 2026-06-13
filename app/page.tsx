import { Ticket as TicketIcon, Users, PackageX, AlarmClock } from "lucide-react"
import { PageHeader } from "@/components/page-header"
import { PriorityBadge, StatusBadge } from "@/components/badges"
import { tickets, technicians, parts } from "@/lib/data"
import { cn } from "@/lib/utils"

const openTickets = tickets.filter((t) => t.status !== "Resolved").length
const availableTechs = technicians.filter((t) => t.available).length
const lowStock = parts.filter((p) => p.stock < p.threshold).length
const slaBreaches = tickets.filter((t) => t.priority === "High" && t.status === "Open").length

const summary = [
  {
    label: "Open Tickets",
    value: openTickets,
    note: "Across all facilities",
    icon: TicketIcon,
    tone: "text-primary bg-primary/10",
  },
  {
    label: "Technicians Available",
    value: `${availableTechs} / ${technicians.length}`,
    note: "Ready for dispatch",
    icon: Users,
    tone: "text-emerald-600 bg-emerald-100",
  },
  {
    label: "Parts Low Stock",
    value: lowStock,
    note: "Below reorder threshold",
    icon: PackageX,
    tone: "text-amber-600 bg-amber-100",
  },
  {
    label: "SLA Breaches",
    value: slaBreaches,
    note: "High priority, unassigned",
    icon: AlarmClock,
    tone: "text-red-600 bg-red-100",
  },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export default function OperationsDashboard() {
  return (
    <>
      <PageHeader
        title="Operations Dashboard"
        description="Live service ticket queue and field operations overview."
      />

      <div className="space-y-6 p-6">
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {summary.map((card) => {
            const Icon = card.icon
            return (
              <div
                key={card.label}
                className="rounded-xl border border-border bg-card p-5 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{card.label}</p>
                    <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
                      {card.value}
                    </p>
                  </div>
                  <span className={cn("flex size-10 items-center justify-center rounded-lg", card.tone)}>
                    <Icon className="size-5" />
                  </span>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">{card.note}</p>
              </div>
            )
          })}
        </section>

        <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold text-foreground">Live Ticket Queue</h2>
            <span className="text-xs text-muted-foreground">{tickets.length} tickets</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-5 py-3 font-medium">Ticket ID</th>
                  <th className="px-5 py-3 font-medium">Client</th>
                  <th className="px-5 py-3 font-medium">Facility</th>
                  <th className="px-5 py-3 font-medium">Asset</th>
                  <th className="px-5 py-3 font-medium">Priority</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Technician</th>
                  <th className="px-5 py-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.id} className="border-b border-border last:border-0 hover:bg-muted/40">
                    <td className="px-5 py-3 font-mono text-xs font-medium text-primary">{t.id}</td>
                    <td className="px-5 py-3 font-medium text-foreground">{t.client}</td>
                    <td className="px-5 py-3 text-muted-foreground">{t.facility}</td>
                    <td className="px-5 py-3 text-muted-foreground">{t.asset}</td>
                    <td className="px-5 py-3">
                      <PriorityBadge priority={t.priority} />
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">
                      {t.technician ?? <span className="italic text-muted-foreground/60">Unassigned</span>}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-muted-foreground">{formatDate(t.created)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  )
}
