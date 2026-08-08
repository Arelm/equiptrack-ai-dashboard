import { PageHeader } from "@/components/page-header"
import { TicketEntryForm } from "@/components/ticket-entry-form"

// Technician entry of the printed helpdesk sheets collected each morning.
// One form per sheet. Distinct from the Client Portal request form: this one
// records who raised it and when, which the report needs and a request form
// has no business asserting.

export default function TicketEntryPage() {
  return (
    <>
      <PageHeader
        title="Enter a ticket"
        description="One sheet at a time, from the morning printout."
      />
      <div className="p-6">
        <div className="mx-auto max-w-md rounded-xl border border-border bg-card p-6 shadow-sm">
          <TicketEntryForm />
        </div>
      </div>
    </>
  )
}
