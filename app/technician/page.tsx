import { PageHeader } from "@/components/page-header"
import { FieldReportForm } from "@/components/field-report-form"
import { TechnicianJobCard } from "@/components/technician-job-card"
import {
  fetchPrimaryOrganization,
  fetchWorkOrders,
  fetchAssets,
  fetchLocations,
} from "@/lib/api"

export default async function TechnicianPage() {
  const org = await fetchPrimaryOrganization()
  const [workOrders, assets, locations] = await Promise.all([
    fetchWorkOrders(org.id),
    fetchAssets(org.id),
    fetchLocations(org.id),
  ])

  const assetById = new Map(assets.map((a) => [a.id, a]))
  const locationById = new Map(locations.map((l) => [l.id, l]))

  const activeJobs = workOrders
    .filter((wo) => wo.status !== "COMPLETED" && wo.status !== "CANCELLED")
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())

  return (
    <>
      <PageHeader
        title="Technician App"
        description={`${activeJobs.length} active job${activeJobs.length !== 1 ? "s" : ""} assigned`}
      />

      <div className="mx-auto w-full max-w-md space-y-6 p-4 sm:max-w-2xl sm:p-6">
        <section>
          <h2 className="px-1 text-sm font-semibold text-foreground">Assigned Jobs</h2>
          {activeJobs.length === 0 ? (
            <p className="mt-3 rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
              No active jobs assigned.
            </p>
          ) : (
            <ul className="mt-3 space-y-3">
              {activeJobs.map((wo) => (
                <TechnicianJobCard
                  key={wo.id}
                  wo={wo}
                  asset={wo.assetId ? assetById.get(wo.assetId) : undefined}
                  location={wo.locationId ? locationById.get(wo.locationId) : undefined}
                />
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-foreground">Submit Field Report</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Log your work, parts used, and resolution notes.
          </p>
          <div className="mt-5">
            <FieldReportForm workOrders={activeJobs} />
          </div>
        </section>
      </div>
    </>
  )
}