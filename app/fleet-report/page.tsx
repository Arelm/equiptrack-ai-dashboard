import { PageHeader } from "@/components/page-header"
import { FleetReport } from "@/components/fleet-report"

// Thin server component, same shape as the operations dashboard: the report is
// scoped to the caller's organisation from their token, and the token only
// exists in the browser, so all fetching happens client-side.

export default function Page() {
  return (
    <>
      <PageHeader
        title="Fleet Report"
        description="Asset register, service activity and repeat failures across the fleet."
      />
      <FleetReport />
    </>
  )
}
