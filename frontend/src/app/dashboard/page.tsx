"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  MapPin,
  TrendingDown,
  TrendingUp,
  Trophy,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMe } from "@/hooks/use-auth";
import { statsApi } from "@/lib/resources";

const rankingTrend = [
  { month: "Jan", points: 3200 },
  { month: "Feb", points: 3500 },
  { month: "Mar", points: 4100 },
  { month: "Apr", points: 3900 },
  { month: "May", points: 4600 },
  { month: "Jun", points: 5000 },
];

const recentChanges = [
  { name: "—", movement: 0 },
];

export default function DashboardPage() {
  const { data: me } = useMe();
  const { data: overview } = useQuery({
    queryKey: ["stats", "overview"],
    queryFn: () => statsApi.overview(),
  });

  const fmt = (n: number | undefined) => (n === undefined ? "—" : n.toLocaleString());
  const stats = [
    {
      label: "Total Players",
      value: fmt(overview?.total_players),
      icon: Users,
      hint: `${fmt(overview?.active_players)} active`,
    },
    {
      label: "Total Clubs",
      value: fmt(overview?.total_clubs),
      icon: Building2,
      hint: "Across all states",
    },
    {
      label: "State Associations",
      value: fmt(overview?.total_states),
      icon: MapPin,
      hint: "Registered bodies",
    },
    {
      label: "Active Tournaments",
      value: fmt(overview?.active_tournaments),
      icon: Trophy,
      hint: `${fmt(overview?.total_tournaments)} total`,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back{me ? `, ${me.full_name.split(" ")[0]}` : ""}. Here is your federation at a glance.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{s.label}</CardTitle>
              <s.icon className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{s.value}</div>
              <p className="text-xs text-muted-foreground">{s.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Ranking points trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={rankingTrend} margin={{ left: -20, right: 8, top: 8 }}>
                  <defs>
                    <linearGradient id="pts" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(142 72% 29%)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="hsl(142 72% 29%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="month" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="points"
                    stroke="hsl(142 72% 29%)"
                    fill="url(#pts)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent ranking changes</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-3">
            {recentChanges.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{c.name}</span>
                <span
                  className={
                    c.movement >= 0
                      ? "flex items-center gap-1 text-primary"
                      : "flex items-center gap-1 text-destructive"
                  }
                >
                  {c.movement >= 0 ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  {c.movement === 0 ? "No data yet" : Math.abs(c.movement)}
                </span>
              </div>
            ))}
            <p className="pt-2 text-xs text-muted-foreground">
              Live data connects in Phase 2 (Player & Ranking modules).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
