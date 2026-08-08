'use client'

import { useParams, useRouter } from 'next/navigation'
import { PriorityBadge, StatusBadge } from '@/components/badges'
import { ArrowLeft, Bot, Loader2, History } from 'lucide-react'
import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { mapPriority, mapStatus } from '@/lib/api'
import { apiFetch, getUser } from '@/lib/authClient'
import { TicketReportPanel } from '@/components/ticket-report-panel'

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
        const user = getUser()
        if (!user) { window.location.href = '/login'; return }

        const woRes = await apiFetch(`/api/workorders/${ticketId}`)
        if (!woRes.ok) throw new Error('not found')
        const wo = await woRes.json()

        const q = `?organizationId=${encodeURIComponent(wo.organizationId)}`
        const [assetsRes, locsRes, allRes] = await Promise.all([
          apiFetch(`/api/assets/${q}`),
          apiFetch(`/api/locations/${q}`),
          apiFetch(`/api/workorders/${q}`),
        ])
        const assets = assetsRes.ok ? await assetsRes.json() : []
        const locations = locsRes.ok ? await locsRes.json() : []
        const allWorkOrders = allRes.ok ? await allRes.json() : []

        const asset = assets.find((a: any) => a.id === wo.assetId)
        const location = locations.find((l: any) => l.id === wo.locationId)

        if (cancelled) return

        setTicket({
          id: wo.id,
         client: location?.client ?? '—',
          facility: location?.name ?? '—',
          asset: asset?.name ?? '—',
          assetId: wo.assetId ?? null,
          priority: mapPriority(wo.priority),
          status: mapStatus(wo.status),
          // The assignee, which this page hardcoded as null even after
          // assignment existed.
          technician: wo.technician?.name ?? null,
          created: wo.createdAt,
          fault: wo.description ?? undefined,
        })

        if (wo.assetId) {
          const history = allWorkOrders
            .filter((w: any) => w.assetId === wo.assetId && w.id !== wo.id)
            .sort((a: any, b: any) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
            .map((w: any) => ({
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

      <TicketReportPanel workOrderId={ticket.id} />

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
          <div className="bg-muted rounded-lg p-4 text-sm leading-relaxed">
            <ReactMarkdown
            remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h3 className="text-base font-semibold mt-4 mb-2 first:mt-0">{children}</h3>
                ),
                h2: ({ children }) => (
                  <h3 className="text-base font-semibold mt-4 mb-2 first:mt-0">{children}</h3>
                ),
                h3: ({ children }) => (
                  <h4 className="text-sm font-semibold mt-3 mb-1">{children}</h4>
                ),
                p: ({ children }) => <p className="mb-2">{children}</p>,
                strong: ({ children }) => (
                  <strong className="font-semibold text-foreground">{children}</strong>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>
                ),
                li: ({ children }) => <li>{children}</li>,
                hr: () => <hr className="my-3 border-border" />,
                table: ({ children }) => (
                  <div className="overflow-x-auto mb-3">
                    <table className="w-full text-left border-collapse">{children}</table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="border-b border-border py-1.5 pr-4 text-xs font-semibold uppercase tracking-wide">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="border-b border-border py-1.5 pr-4 align-top">{children}</td>
                ),
              }}
            >
              {analysis}
            </ReactMarkdown>
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