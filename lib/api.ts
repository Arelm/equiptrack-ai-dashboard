import type { Priority, Status } from "@/lib/data"

const API_BASE = process.env.NEXT_PUBLIC_API_URL

// JDAEM Enterprise Limited's org id is looked up dynamically via fetchOrganizations()
// rather than hardcoded, so seeding/reseeding never breaks the dashboard.

function requireApiBase() {
  if (!API_BASE) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Add it in Vercel project settings (Environment Variables) " +
        "pointing at the Railway backend URL, e.g. https://your-service.up.railway.app",
    )
  }
  return API_BASE
}

// ---- Backend <-> frontend enum mapping ----
// Backend (Prisma) uses SCREAMING_SNAKE_CASE enums.
// Frontend components (badges.tsx) expect the original mock's display strings.
// Mapping here means we never have to touch badges.tsx or other display components.

const PRIORITY_MAP: Record<string, Priority> = {
  CRITICAL: "High", // no separate "Critical" badge style exists yet, fold into High
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
}

const STATUS_MAP: Record<string, Status> = {
  OPEN: "Open",
  IN_PROGRESS: "In Progress",
  ON_HOLD: "Assigned", // closest existing visual equivalent
  COMPLETED: "Resolved",
  CANCELLED: "Resolved",
}

export function mapPriority(backendPriority: string): Priority {
  return PRIORITY_MAP[backendPriority] ?? "Medium"
}

const PRIORITY_REVERSE_MAP: Record<Priority, string> = {
  High: "HIGH",
  Medium: "MEDIUM",
  Low: "LOW",
}

// Frontend display string ("High"/"Medium"/"Low") -> backend enum ("HIGH"/"MEDIUM"/"LOW")
export function toBackendPriority(priority: Priority): string {
  return PRIORITY_REVERSE_MAP[priority] ?? "MEDIUM"
}

export function mapStatus(backendStatus: string): Status {
  return STATUS_MAP[backendStatus] ?? "Open"
}

// ---- Raw backend shapes (subset of fields we actually use) ----

export type BackendOrganization = {
  id: string
  name: string
  industry: string | null
}

export type BackendLocation = {
  id: string
  name: string
  address: string | null
  organizationId: string
}

export type BackendAsset = {
  id: string
  name: string
  category: string
  status: string
  organizationId: string
  locationId: string | null
}

export type BackendWorkOrder = {
  id: string
  title: string
  description: string | null
  priority: string
  status: string
  organizationId: string
  assetId: string | null
  locationId: string | null
  createdAt: string
}

// ---- Fetch helpers ----
// NOTE: these run on the server (no "use client" in the pages that call them),
// so plain fetch with no-store is fine — this is server-side data fetching,
// not a client-side network call.

export async function fetchOrganizations(): Promise<BackendOrganization[]> {
  const base = requireApiBase()
  const res = await fetch(`${base}/api/organizations/`, { cache: "no-store" })
  if (!res.ok) {
    throw new Error(`Failed to fetch organizations: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// The dashboard and client portal are currently scoped to a single organization
// (JDAEM Enterprise Limited). This finds it by name rather than a hardcoded id,
// so reseeding the database never breaks the app.
export async function fetchPrimaryOrganization(): Promise<BackendOrganization> {
  const orgs = await fetchOrganizations()
  const jdaem = orgs.find((o) => o.name === "JDAEM Enterprise Limited")
  if (!jdaem) {
    throw new Error(
      "Could not find 'JDAEM Enterprise Limited' organization. Has the database been seeded?",
    )
  }
  return jdaem
}

export async function fetchWorkOrders(organizationId?: string): Promise<BackendWorkOrder[]> {
  const base = requireApiBase()
  const url = organizationId
    ? `${base}/api/workorders/?organizationId=${encodeURIComponent(organizationId)}`
    : `${base}/api/workorders/`
  const res = await fetch(url, { cache: "no-store" })
  if (!res.ok) {
    throw new Error(`Failed to fetch work orders: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function fetchAssets(organizationId?: string): Promise<BackendAsset[]> {
  const base = requireApiBase()
  const url = organizationId
    ? `${base}/api/assets/?organizationId=${encodeURIComponent(organizationId)}`
    : `${base}/api/assets/`
  const res = await fetch(url, { cache: "no-store" })
  if (!res.ok) {
    throw new Error(`Failed to fetch assets: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function fetchLocations(organizationId?: string): Promise<BackendLocation[]> {
  const base = requireApiBase()
  const url = organizationId
    ? `${base}/api/locations/?organizationId=${encodeURIComponent(organizationId)}`
    : `${base}/api/locations/`
  const res = await fetch(url, { cache: "no-store" })
  if (!res.ok) {
    throw new Error(`Failed to fetch locations: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function fetchWorkOrderById(id: string): Promise<BackendWorkOrder> {
  const base = requireApiBase()
  const res = await fetch(`${base}/api/workorders/${encodeURIComponent(id)}`, { cache: "no-store" })
  if (!res.ok) {
    throw new Error(`Failed to fetch work order ${id}: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function createWorkOrder(payload: {
  title: string
  description?: string
  priority: string
  organizationId: string
  assetId?: string
  locationId?: string
}): Promise<BackendWorkOrder> {
  const base = requireApiBase()
  const res = await fetch(`${base}/api/workorders/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`Failed to create work order: ${res.status} ${res.statusText} ${text}`)
  }
  return res.json()
}