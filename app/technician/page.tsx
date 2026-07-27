import { PageHeader } from "@/components/page-header"
import { TechnicianJobs } from "@/components/technician-jobs"

// Jobs are fetched client-side from /api/workorders/mine so the list is scoped
// to the logged-in technician by the backend, not filtered in the browser.
// The page-level "Submit Field Report" card with its own Job dropdown is gone:
// a report now opens from the job card it belongs to and inherits that job id.

export default function TechnicianPage() {
  return (
    <>
      <PageHeader title="My Jobs" description="Accept, complete and report on your assigned work" />
      <div className="mx-auto w-full max-w-md space-y-6 p-4 sm:max-w-2xl sm:p-6">
        <TechnicianJobs />
      </div>
    </>
  )
}