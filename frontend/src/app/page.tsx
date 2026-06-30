import Link from "next/link";
import { Trophy, Users, BarChart3, Shield } from "lucide-react";

import { Button } from "@/components/ui/button";

const features = [
  { icon: Users, title: "Players & Clubs", desc: "Central registry for players, clubs, and state associations." },
  { icon: Trophy, title: "Tournaments", desc: "Draws, registrations, and live match scoring." },
  { icon: BarChart3, title: "Ranking Engine", desc: "Automatic points, rankings, and historical timelines." },
  { icon: Shield, title: "Multi-tenant", desc: "Isolated data per federation, secure RBAC." },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-lg">
            <Trophy className="h-6 w-6 text-primary" />
            CourtBase
          </div>
          <Button asChild>
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </header>

      <section className="container py-20 text-center">
        <span className="inline-block rounded-full bg-accent px-4 py-1 text-sm font-medium text-accent-foreground">
          Badminton Federation Management System
        </span>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          Run your federation from one professional platform
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Replace spreadsheets with a centralized system for players, clubs, tournaments,
          and automatic rankings — built for national federations.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Button asChild size="lg">
            <Link href="/login">Get started</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/dashboard">View dashboard</Link>
          </Button>
        </div>
      </section>

      <section className="container grid gap-6 pb-24 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <div key={f.title} className="rounded-xl border p-6">
            <f.icon className="h-8 w-8 text-primary" />
            <h3 className="mt-4 font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
