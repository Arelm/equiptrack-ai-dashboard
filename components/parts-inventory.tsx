"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus, PackagePlus, History, X, AlertTriangle } from "lucide-react"
import { apiFetch, getUser, type AuthUser } from "@/lib/authClient"

type Part = {
  id: string
  name: string
  partNumber: string | null
  quantity: number
  reorderLevel: number
  unit: string
  category: string | null
  lowStock: boolean
}

type Movement = {
  id: string
  delta: number
  reason: string
  refType: string | null
  by: string | null
  note: string | null
  createdAt: string | null
}

const UNITS = ["pcs", "m", "kg", "length", "set", "litre"]

const REASON_LABEL: Record<string, string> = {
  job_consumption: "Used on a job",
  receipt: "Received",
  adjustment: "Adjustment",
  return: "Returned",
  correction: "Correction",
}

const field =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"

export function PartsInventory() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAdd, setShowAdd] = useState(false)
  const [receiveFor, setReceiveFor] = useState<Part | null>(null)
  const [historyFor, setHistoryFor] = useState<Part | null>(null)
  const [movements, setMovements] = useState<Movement[]>([])

  const load = useCallback(async () => {
    const u = getUser()
    if (!u) { window.location.href = "/login"; return }
    setUser(u)
    try {
      const res = await apiFetch(`/api/parts/?organizationId=${encodeURIComponent(u.orgId)}`)
      if (!res.ok) throw new Error("Could not load the parts catalogue.")
      setParts(await res.json())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the server.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function openHistory(p: Part) {
    setHistoryFor(p)
    setMovements([])
    const res = await apiFetch(`/api/parts/${p.id}/movements`)
    if (res.ok) setMovements((await res.json()).movements)
  }

  if (loading) return <p className="p-6 text-sm text-muted-foreground">Loading catalogue…</p>
  if (error) {
    return <div className="m-6 rounded-xl bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
  }

  const canManage = user?.role === "MANAGER" || user?.role === "ADMIN"
  const lowCount = parts.filter((p) => p.lowStock).length
  const negative = parts.filter((p) => p.quantity < 0)

  const byCategory = parts.reduce<Record<string, Part[]>>((acc, p) => {
    const key = p.category ?? "Uncategorised"
    ;(acc[key] ||= []).push(p)
    return acc
  }, {})

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-4 text-sm">
          <span className="text-muted-foreground">{parts.length} parts</span>
          {lowCount > 0 && (
            <span className="font-medium text-amber-600">{lowCount} at or below reorder level</span>
          )}
        </div>
        {canManage && (
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="size-4" /> Add part
          </button>
        )}
      </div>

      {/* A negative balance is not a bug to hide. It means the store issued
          something the system did not know it had — which is exactly the gap
          a stock take exists to find. */}
      {negative.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg bg-amber-50 px-4 py-3">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" />
          <p className="text-sm text-amber-900">
            {negative.length} part{negative.length !== 1 ? "s have" : " has"} a negative balance —
            issued on a job before the opening stock was counted. Receive the real quantity to correct it.
          </p>
        </div>
      )}

      {Object.entries(byCategory).map(([category, items]) => (
        <section key={category} className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <div className="border-b border-border px-5 py-3">
            <h2 className="text-sm font-semibold text-foreground">{category}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-5 py-2.5 font-medium">Part</th>
                  <th className="px-5 py-2.5 font-medium">Part no.</th>
                  <th className="px-5 py-2.5 font-medium">In stock</th>
                  <th className="px-5 py-2.5 font-medium">Reorder at</th>
                  <th className="px-5 py-2.5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.id} className="border-b border-border last:border-0 hover:bg-muted/40">
                    <td className="px-5 py-2.5 font-medium text-foreground">{p.name}</td>
                    <td className="px-5 py-2.5 font-mono text-xs text-muted-foreground">
                      {p.partNumber ?? "—"}
                    </td>
                    <td className="px-5 py-2.5">
                      <span className={
                        p.quantity < 0 ? "font-semibold text-red-600"
                        : p.lowStock ? "font-medium text-amber-600"
                        : "text-foreground"
                      }>
                        {p.quantity} {p.unit}
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-muted-foreground">
                      {p.reorderLevel} {p.unit}
                    </td>
                    <td className="px-5 py-2.5">
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openHistory(p)}
                          title="Movement history"
                          className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                        >
                          <History className="size-4" />
                        </button>
                        {canManage && (
                          <button
                            type="button"
                            onClick={() => setReceiveFor(p)}
                            title="Receive stock"
                            className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                          >
                            <PackagePlus className="size-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      {showAdd && user && (
        <AddPartDialog
          orgId={user.orgId}
          onClose={() => setShowAdd(false)}
          onSaved={() => { setShowAdd(false); load() }}
        />
      )}

      {receiveFor && (
        <ReceiveDialog
          part={receiveFor}
          onClose={() => setReceiveFor(null)}
          onSaved={() => { setReceiveFor(null); load() }}
        />
      )}

      {historyFor && (
        <Dialog title={`${historyFor.name} — movement history`} onClose={() => setHistoryFor(null)}>
          {movements.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No movements recorded. The opening balance predates the ledger.
            </p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Change</th>
                  <th className="pb-2 pr-4 font-medium">Reason</th>
                  <th className="pb-2 pr-4 font-medium">By</th>
                  <th className="pb-2 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {movements.map((m) => (
                  <tr key={m.id} className="border-b border-border last:border-0">
                    <td className={`py-2 pr-4 font-medium ${m.delta < 0 ? "text-red-600" : "text-emerald-600"}`}>
                      {m.delta > 0 ? "+" : ""}{m.delta} {historyFor.unit}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {REASON_LABEL[m.reason] ?? m.reason}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">{m.by ?? "—"}</td>
                    <td className="py-2 whitespace-nowrap text-muted-foreground">
                      {m.createdAt
                        ? new Date(m.createdAt).toLocaleDateString("en-US", {
                            month: "short", day: "numeric", year: "numeric",
                          })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Dialog>
      )}
    </div>
  )
}

function Dialog({ title, children, onClose }: {
  title: string; children: React.ReactNode; onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-card p-5 shadow-lg">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <button type="button" onClick={onClose} className="rounded p-1 text-muted-foreground hover:text-foreground">
            <X className="size-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function AddPartDialog({ orgId, onClose, onSaved }: {
  orgId: string; onClose: () => void; onSaved: () => void
}) {
  const [name, setName] = useState("")
  const [partNumber, setPartNumber] = useState("")
  const [unit, setUnit] = useState("pcs")
  const [category, setCategory] = useState("")
  const [reorderLevel, setReorderLevel] = useState("0")
  const [openingQuantity, setOpeningQuantity] = useState("0")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function save() {
    if (!name.trim()) return setErr("A part needs a name.")
    setBusy(true); setErr(null)
    try {
      const res = await apiFetch("/api/parts/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          partNumber: partNumber.trim() || null,
          unit,
          category: category.trim() || null,
          reorderLevel: Number(reorderLevel) || 0,
          openingQuantity: Number(openingQuantity) || 0,
          organizationId: orgId,
        }),
      })
      if (!res.ok) {
        const d = (await res.json().catch(() => ({}))).detail
        setErr(typeof d === "string" ? d : "Could not save the part.")
        return
      }
      onSaved()
    } catch { setErr("No connection.") } finally { setBusy(false) }
  }

  return (
    <Dialog title="Add a part to the catalogue" onClose={onClose}>
      <div className="space-y-3">
        <input className={field} placeholder="Name, e.g. Copper pipe 1/2&quot;"
               value={name} onChange={(e) => setName(e.target.value)} />
        <input className={field} placeholder="Part number (optional)"
               value={partNumber} onChange={(e) => setPartNumber(e.target.value)} />
        <div className="flex gap-2">
          <select className={field} value={unit} onChange={(e) => setUnit(e.target.value)} aria-label="Unit">
            {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
          <input className={field} placeholder="Category, e.g. Pipe"
                 value={category} onChange={(e) => setCategory(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground">Reorder level</label>
            <input className={field} type="number" min="0" step="0.01"
                   value={reorderLevel} onChange={(e) => setReorderLevel(e.target.value)} />
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted-foreground">Opening stock counted</label>
            <input className={field} type="number" min="0" step="0.01"
                   value={openingQuantity} onChange={(e) => setOpeningQuantity(e.target.value)} />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Opening stock is written as a ledger receipt, so the balance has provenance from day one.
        </p>
        {err && <p className="text-xs text-destructive">{err}</p>}
        <button type="button" disabled={busy} onClick={save}
                className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
          {busy ? "Saving…" : "Add part"}
        </button>
      </div>
    </Dialog>
  )
}

function ReceiveDialog({ part, onClose, onSaved }: {
  part: Part; onClose: () => void; onSaved: () => void
}) {
  const [quantity, setQuantity] = useState("")
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function save() {
    const q = Number(quantity)
    if (!q || q <= 0) return setErr("Enter a quantity greater than zero.")
    setBusy(true); setErr(null)
    try {
      const res = await apiFetch(`/api/parts/${part.id}/receive`, {
        method: "POST",
        body: JSON.stringify({ quantity: q, note: note.trim() || null }),
      })
      if (!res.ok) {
        const d = (await res.json().catch(() => ({}))).detail
        setErr(typeof d === "string" ? d : "Could not record the receipt.")
        return
      }
      onSaved()
    } catch { setErr("No connection.") } finally { setBusy(false) }
  }

  return (
    <Dialog title={`Receive stock — ${part.name}`} onClose={onClose}>
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Currently {part.quantity} {part.unit} on record.
        </p>
        <div>
          <label className="text-xs text-muted-foreground">Quantity received ({part.unit})</label>
          <input className={field} type="number" min="0" step="0.01" autoFocus
                 value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </div>
        <input className={field} placeholder="Note, e.g. supplier or invoice number"
               value={note} onChange={(e) => setNote(e.target.value)} />
        {err && <p className="text-xs text-destructive">{err}</p>}
        <button type="button" disabled={busy} onClick={save}
                className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
          {busy ? "Recording…" : "Record receipt"}
        </button>
      </div>
    </Dialog>
  )
}