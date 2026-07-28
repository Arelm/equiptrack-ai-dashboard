import { fetchPrimaryOrganization } from "@/lib/api"
import { LocationsManager } from "@/components/locations-manager"

// Sites change while the app is running, so this page is never cached.
export const dynamic = "force-dynamic"

export default async function LocationsPage() {
  const organization = await fetchPrimaryOrganization()

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Sites</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Client plots your technicians are dispatched to, and who to call on
          arrival.
        </p>
      </header>

      <LocationsManager organizationId={organization.id} />
    </div>
  )
}
