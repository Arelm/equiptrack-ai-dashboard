import { PageHeader } from "@/components/page-header"
import { OperationsDashboard } from "@/components/operations-dashboard"

// Data fetching moved into a client component. As a server component this page
// fetched at request time on the server, where the user's token does not exist,
// so it could never send one — and every counter came from lib/data.ts mocks
// while the Technician column was a hardcoded null.

export default function Page() {
  return (
    <>
      <PageHeader
        title="Operations Dashboard"
        description="Live service ticket queue and field operations overview."
      />
      <OperationsDashboard />
    </>
  )
}