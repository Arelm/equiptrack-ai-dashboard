"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"
import { getUser, clearAuth, type AuthUser } from "@/lib/authClient"
import {
  LayoutDashboard,
  ClipboardList,
  Wrench,
  Radar,
  ArrowLeftRight,
  Archive,
  LogOut,
  Package,
  MapPin,
} from "lucide-react"

const navItems = [
  { href: "/", label: "Operations Dashboard", icon: LayoutDashboard, desc: "Live ticket queue" },
  { href: "/client-portal", label: "Client Portal", icon: ClipboardList, desc: "Submit & track requests" },
  { href: "/technician", label: "Technician App", icon: Wrench, desc: "Assigned field jobs" },
  { href: "/parts", label: "Parts & Inventory", icon: Package, desc: "Stock levels & receipts" },
  { href: "/locations", label: "Sites", icon: MapPin, desc: "Client plots & supervisors" },
  { href: "/transfers", label: "Asset Transfers", icon: ArrowLeftRight, desc: "Site-to-site custody" },
  { href: "/disposals", label: "Disposal Center", icon: Archive, desc: "Retired & scrapped assets" },
]

export function Sidebar() {
  const pathname = usePathname()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    setUser(getUser())
    setChecked(true)
  }, [])

  function signOut() {
    clearAuth()
    window.location.href = "/login"
  }

  const initials = !checked
    ? ""
    : user
    ? user.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()
    : "—"
  const displayName = !checked ? "\u00A0" : user?.name ?? "Not signed in"
  const displayEmail = !checked ? "\u00A0" : user?.email ?? "\u2014"


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
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
            {initials}
          </div>

          <div className="min-w-0 flex-1 text-xs">
            <p className="truncate font-medium text-sidebar-foreground">
              {displayName}
            </p>
            <p className="truncate text-sidebar-foreground/55">{displayEmail}</p>
          </div>

          <button
            type="button"
            disabled={!checked}
            onClick={user ? signOut : () => { window.location.href = "/login" }}
            aria-label={user ? "Sign out" : "Sign in"}
            title={user ? "Sign out" : "Sign in"}
            className="shrink-0 rounded p-1.5 text-sidebar-foreground/55 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}