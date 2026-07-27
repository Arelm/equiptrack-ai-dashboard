import { PageHeader } from "@/components/page-header"
import { ServiceRequestForm } from "@/components/service-request-form"
import { ClientTicketHistory } from "@/components/client-ticket-history"

// No server-side data fetching. This page rendered on the server and called the
// work-order API with no token, which returned 500 once that API required one.
//
// The request form stays public: a client reporting a broken chiller is the
// entry point of the whole system and must not need an account. Ticket history
// loads in the browser, where a token exists if the person is signed in.

export default function ClientPortalPage() {
  return (
    <>
      <PageHeader
        title="Client Portal"
        description="Submit and track service requests."
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
          <ClientTicketHistory />
        </section>
      </div>
    </>
  )
}