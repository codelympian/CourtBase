"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Sidebar } from "@/components/dashboard/sidebar";
import { Button } from "@/components/ui/button";
import { useLogout, useMe } from "@/hooks/use-auth";
import { tokenStore } from "@/lib/api";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: me, isLoading, isError } = useMe();
  const logout = useLogout();

  useEffect(() => {
    if (typeof window !== "undefined" && !tokenStore.access) {
      router.replace("/login");
    }
  }, [router]);

  useEffect(() => {
    if (isError) router.replace("/login");
  }, [isError, router]);

  if (isLoading || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-secondary/30">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b bg-card px-6">
          <div className="text-sm text-muted-foreground">
            {me.federation_id ? "Federation workspace" : "Platform administration"}
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm font-medium">{me.full_name}</div>
              <div className="text-xs text-muted-foreground">{me.roles.join(", ") || "user"}</div>
            </div>
            <Button variant="outline" size="icon" onClick={() => logout.mutate()}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
