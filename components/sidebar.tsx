"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, ClipboardList, Wrench, Radar } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { href: "/", label: "Operations Dashboard", icon: LayoutDashboard, desc: "Live ticket queue" },
  { href: "/client-portal", label: "Client Portal", icon: ClipboardList, desc: "Submit & track requests" },
  { href: "/technician", label: "Technician App", icon: Wrench, desc: "Assigned field jobs" },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-full shrink-0 flex-col bg-sidebar text-sidebar-foreground md:h-dvh md:w-72 md:sticky md:top-0">
      <div className="flex items-center gap-3 border-b border-sidebar-border px-6 py-5">
        <div className="flex size-9 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
          <Radar className="size-5" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">EquipTrack AI</p>
          <p className="text-xs text-sidebar-foreground/60">Field Service Platform</p>
        </div>
      </div>

      <nav className="flex flex-row gap-1 overflow-x-auto p-3 md:flex-col md:overflow-visible">
        {navItems.map((item) => {
          const active = pathname === item.href
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" />
              <span className="flex flex-col">
                <span>{item.label}</span>
                <span
                  className={cn(
                    "hidden text-xs font-normal md:block",
                    active ? "text-sidebar-primary-foreground/75" : "text-sidebar-foreground/45",
                  )}
                >
                  {item.desc}
                </span>
              </span>
            </Link>
          )
        })}
      </nav>

      <div className="mt-auto hidden border-t border-sidebar-border px-6 py-4 md:block">
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-full bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
            OM
          </div>
          <div className="text-xs">
            <p className="font-medium text-sidebar-foreground">Operations Manager</p>
            <p className="text-sidebar-foreground/55">ops@equiptrack.ai</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
