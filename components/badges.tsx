import { cn } from "@/lib/utils"
import type { Priority, Status } from "@/lib/data"

export function PriorityBadge({ priority }: { priority: Priority }) {
  const styles: Record<Priority, string> = {
    High: "bg-red-100 text-red-700 ring-red-600/20",
    Medium: "bg-amber-100 text-amber-700 ring-amber-600/20",
    Low: "bg-emerald-100 text-emerald-700 ring-emerald-600/20",
  }
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        styles[priority],
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          priority === "High" && "bg-red-500",
          priority === "Medium" && "bg-amber-500",
          priority === "Low" && "bg-emerald-500",
        )}
      />
      {priority}
    </span>
  )
}

export function StatusBadge({ status }: { status: Status }) {
  const styles: Record<Status, string> = {
    Open: "bg-slate-100 text-slate-600 ring-slate-500/20",
    Assigned: "bg-blue-100 text-blue-700 ring-blue-600/20",
    "In Progress": "bg-indigo-100 text-indigo-700 ring-indigo-600/20",
    Resolved: "bg-emerald-100 text-emerald-700 ring-emerald-600/20",
  }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        styles[status],
      )}
    >
      {status}
    </span>
  )
}
