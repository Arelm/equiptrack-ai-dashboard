import { PageHeader } from "@/components/page-header"
import { ServiceRequestForm } from "@/components/service-request-form"
import { PriorityBadge, StatusBadge } from "@/components/badges"
import {
  fetchPrimaryOrganization,
  fetchWorkOrders,
  fetchAssets,
  fetchLocations,
  mapPriority,
  mapStatus,
} from "@/lib/api"

const clientName = "Northwind Logistics"

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export default async function ClientPortalPage() {
  const org = await fetchPrimaryOrganization()
  const [workOrders, assets, locations] = await Promise.all([
    fetchWorkOrders(org.id),
    fetchAssets(org.id),
    fetchLocations(org.id),
  ])

  const assetById = new Map(assets.map((a) => [a.id, a]))
  const locationById = new Map(locations.map((l) => [l.id, l]))

  const clientTickets = [...workOrders].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )

  return (
    <>
      <PageHeader
        title="Client Portal"
        description={`Signed in as ${clientName} · Submit and track service requests.`}
      />

      <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-5">
        <section className="lg:col-span-2">
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-foreground">New Service Request</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Tell us what needs attention and we&apos;ll dispatch a technician.
            </p>
            <div className="mt-5">
              <ServiceRequestForm />
            </div>
          </div>
        </section>

        <section className="lg:col-span-3">
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="text-sm font-semibold text-foreground">Ticket History</h2>
              <span className="text-xs text-muted-foreground">{clientTickets.length} requests</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Ticket ID</th>
                    <th className="px-5 py-3 font-medium">Asset</th>
                    <th className="px-5 py-3 font-medium">Priority</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {clientTickets.map((t) => {
                    const asset = t.assetId ? assetById.get(t.assetId) : undefined
                    const location = t.locationId ? locationById.get(t.locationId) : undefined
                    return (
                      <tr key={t.id} className="border-b border-border last:border-0 hover:bg-muted/40">
                        <td className="px-5 py-3 font-mono text-xs font-medium text-primary">
                          {t.id.slice(0, 8).toUpperCase()}
                        </td>
                        <td className="px-5 py-3 text-foreground">
                          <span className="font-medium">{asset?.name ?? "—"}</span>
                          <span className="block text-xs text-muted-foreground">
                            {location?.name ?? ""}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <PriorityBadge priority={mapPriority(t.priority)} />
                        </td>
                        <td className="px-5 py-3">
                          <StatusBadge status={mapStatus(t.status)} />
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap text-muted-foreground">
                          {formatDate(t.createdAt)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </>
  )
}