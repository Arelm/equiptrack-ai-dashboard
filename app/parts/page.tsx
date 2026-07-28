import { PageHeader } from "@/components/page-header"
import { PartsInventory } from "@/components/parts-inventory"

export default function PartsPage() {
  return (
    <>
      <PageHeader
        title="Parts & Inventory"
        description="Stock levels, receipts, and the movement history behind every balance."
      />
      <PartsInventory />
    </>
  )
}