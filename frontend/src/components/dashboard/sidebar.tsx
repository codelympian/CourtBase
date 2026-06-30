"use client";

import {
  BarChart3,
  Building2,
  LayoutDashboard,
  MapPin,
  Trophy,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/players", label: "Players", icon: Users },
  { href: "/dashboard/clubs", label: "Clubs", icon: Building2 },
  { href: "/dashboard/states", label: "State Associations", icon: MapPin },
  { href: "/dashboard/tournaments", label: "Tournaments", icon: Trophy },
  { href: "/dashboard/rankings", label: "Rankings", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-64 shrink-0 border-r bg-card md:block">
      <div className="flex h-16 items-center gap-2 border-b px-6 font-bold">
        <Trophy className="h-6 w-6 text-primary" />
        CourtBase
      </div>
      <nav className="space-y-1 p-3">
        {nav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
