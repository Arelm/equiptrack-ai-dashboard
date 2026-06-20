'use client'

import { useParams, useRouter } from 'next/navigation'
import { tickets } from '@/lib/data'
import { PriorityBadge, StatusBadge } from '@/components/badges'
import { ArrowLeft, Bot, Loader2 } from 'lucide-react'
import { useState } from 'react'

export default function TicketDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const ticket = tickets.find((t) => t.id === id)
  const [analysis, setAnalysis] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!ticket) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Ticket not found.
      </div>
    )
  }

  async function runAIAnalysis() {
    setLoading(true)
    setAnalysis(null)
    try {
      const res = await fetch(
        'https://equiptrack-ai-dashboard-production.up.railway.app/api/ai/analyze-ticket',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ticket_id: ticket!.id,
            asset: ticket!.asset,
            client: ticket!.client,
            facility: ticket!.facility,
            priority: ticket!.priority,
            status: ticket!.status,
            technician: ticket!.technician,
            fault: ticket!.fault ?? 'No fault description provided',
          }),
        }
      )
      const data = await res.json()
      setAnalysis(data.analysis ?? data.message ?? JSON.stringify(data))
    } catch (err) {
      setAnalysis('Error contacting AI service. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

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
            <p className="font-medium">{ticket.created}</p>
          </div>
          {ticket.fault && (
            <div className="col-span-2">
              <p className="text-muted-foreground">Fault Description</p>
              <p className="font-medium">{ticket.fault}</p>
            </div>
          )}
        </div>
      </div>

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