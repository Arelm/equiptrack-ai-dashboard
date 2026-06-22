'use client'

import { useParams, useRouter } from 'next/navigation'
import { PriorityBadge, StatusBadge } from '@/components/badges'
import { ArrowLeft, Bot, Loader2, History } from 'lucide-react'
import { useState, useEffect } from 'react'
import {
  fetchWorkOrderById,
  fetchWorkOrders,
  fetchAssets,
  fetchLocations,
  fetchOrganizations,
  mapPriority,
  mapStatus,
  type BackendWorkOrder,
} from '@/lib/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL

type DisplayTicket = {
  id: string
  client: string
  facility: string
  asset: string
  assetId: string | null
  priority: ReturnType<typeof mapPriority>
  status: ReturnType<typeof mapStatus>
  technician: string | null
  created: string
  fault?: string
}

type HistoryEntry = {
  id: string
  priority: ReturnType<typeof mapPriority>
  status: ReturnType<typeof mapStatus>
  created: string
  fault: string | null
}

export default function TicketDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const ticketId = Array.isArray(id) ? id[0] : id

  const [ticket, setTicket] = useState<DisplayTicket | null>(null)
  const [loadingTicket, setLoadingTicket] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [serviceHistory, setServiceHistory] = useState<HistoryEntry[]>([])

  const [analysis, setAnalysis] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!ticketId) return
    let cancelled = false

    async function load() {
      try {
        const wo: BackendWorkOrder = await fetchWorkOrderById(ticketId!)

        const [orgs, assets, locations, allWorkOrders] = await Promise.all([
          fetchOrganizations(),
          fetchAssets(wo.organizationId),
          fetchLocations(wo.organizationId),
          fetchWorkOrders(wo.organizationId),
        ])

        const org = orgs.find((o) => o.id === wo.organizationId)
        const asset = assets.find((a) => a.id === wo.assetId)
        const location = locations.find((l) => l.id === wo.locationId)

        if (cancelled) return

        setTicket({
          id: wo.id,
          client: org?.name ?? '—',
          facility: location?.name ?? '—',
          asset: asset?.name ?? '—',
          assetId: wo.assetId ?? null,
          priority: mapPriority(wo.priority),
          status: mapStatus(wo.status),
          technician: null,
          created: wo.createdAt,
          fault: wo.description ?? undefined,
        })

        // Service history: all other work orders for the same asset
        if (wo.assetId) {
          const history = allWorkOrders
            .filter((w) => w.assetId === wo.assetId && w.id !== wo.id)
            .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
            .map((w) => ({
              id: w.id,
              priority: mapPriority(w.priority),
              status: mapStatus(w.status),
              created: w.createdAt,
              fault: w.description ?? null,
            }))
          setServiceHistory(history)
        }
      } catch (err) {
        if (!cancelled) setNotFound(true)
      } finally {
        if (!cancelled) setLoadingTicket(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [ticketId])

  async function runAIAnalysis() {
    if (!ticket || !API_BASE) return
    setLoading(true)
    setAnalysis(null)
    try {
      const res = await fetch(`${API_BASE}/api/ai/analyze-ticket`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticket_id: ticket.id,
          asset: ticket.asset,
          client: ticket.client,
          facility: ticket.facility,
          priority: ticket.priority,
          status: ticket.status,
          technician: ticket.technician,
          fault: ticket.fault ?? 'No fault description provided',
        }),
      })
      const data = await res.json()
      setAnalysis(data.analysis ?? data.message ?? JSON.stringify(data))
    } catch (err) {
      setAnalysis('Error contacting AI service. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loadingTicket) {
    return (
      <div className="p-8 text-center text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 size={16} className="animate-spin" />
        Loading ticket...
      </div>
    )
  }

  if (notFound || !ticket) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Ticket not found.
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      {/* Ticket Details */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold font-mono">{ticket.id}</h1>
          <div className="flex gap-2">
            <PriorityBadge priority={ticket.priority} />
            <StatusBadge status={ticket.status} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Client</p>
            <p className="font-medium">{ticket.client}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Facility</p>
            <p className="font-medium">{ticket.facility}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Asset</p>
            <p className="font-medium">{ticket.asset}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Technician</p>
            <p className="font-medium">{ticket.technician ?? 'Unassigned'}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Created</p>
            <p className="font-medium">
              {new Date(ticket.created).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric',
              })}
            </p>
          </div>
          {ticket.fault && (
            <div className="col-span-2">
              <p className="text-muted-foreground">Fault Description</p>
              <p className="font-medium">{ticket.fault}</p>
            </div>
          )}
        </div>
      </div>

      {/* Service History */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History size={20} className="text-primary" />
            <h2 className="font-semibold">Asset Service History</h2>
          </div>
          <span className="text-xs text-muted-foreground">
            {serviceHistory.length} previous job{serviceHistory.length !== 1 ? 's' : ''} on this asset
          </span>
        </div>

        {serviceHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No previous service records for this asset.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Ticket ID</th>
                  <th className="pb-2 pr-4 font-medium">Priority</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 pr-4 font-medium">Date</th>
                  <th className="pb-2 font-medium">Fault</th>
                </tr>
              </thead>
              <tbody>
                {serviceHistory.map((h) => (
                  <tr key={h.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4 font-mono text-xs font-medium text-primary">
                      {h.id.slice(0, 8).toUpperCase()}
                    </td>
                    <td className="py-2 pr-4">
                      <PriorityBadge priority={h.priority} />
                    </td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={h.status} />
                    </td>
                    <td className="py-2 pr-4 whitespace-nowrap text-muted-foreground">
                      {new Date(h.created).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric',
                      })}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {h.fault ?? <span className="italic">No description</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* AI Analysis */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Bot size={20} className="text-primary" />
          <h2 className="font-semibold">AI Maintenance Analysis</h2>
        </div>

        {!analysis && !loading && (
          <p className="text-sm text-muted-foreground">
            Run AI analysis to get predictive maintenance recommendations for this asset.
          </p>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 size={16} className="animate-spin" />
            Analysing asset data...
          </div>
        )}

        {analysis && (
          <div className="bg-muted rounded-lg p-4 text-sm whitespace-pre-wrap leading-relaxed">
            {analysis}
          </div>
        )}

        <button
          onClick={runAIAnalysis}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Bot size={14} />}
          {loading ? 'Analysing...' : 'Run AI Analysis'}
        </button>
      </div>
    </div>
  )
}