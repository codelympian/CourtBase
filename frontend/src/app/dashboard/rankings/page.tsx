"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Minus, RefreshCw, Send, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { TBody, TD, TH, THead, TR, Table } from "@/components/ui/table";
import { useMe } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import {
  type RankingRow,
  categoriesApi,
  rankingsApi,
} from "@/lib/resources";

function Movement({ value, previous }: { value: number; previous: number | null }) {
  if (previous === null)
    return <span className="text-xs text-muted-foreground">new</span>;
  if (value === 0)
    return (
      <span className="flex items-center gap-1 text-muted-foreground">
        <Minus className="h-3.5 w-3.5" />
      </span>
    );
  const up = value > 0;
  return (
    <span className={up ? "flex items-center gap-1 text-primary" : "flex items-center gap-1 text-destructive"}>
      {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
      {Math.abs(value)}
    </span>
  );
}

export default function RankingsPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canApprove = !!me?.permissions.includes("rankings:approve");
  const canManageRules = !!me?.permissions.includes("ranking_rules:manage");

  const [categoryId, setCategoryId] = useState("");
  const [publishedOnly, setPublishedOnly] = useState(false);
  const [historyFor, setHistoryFor] = useState<RankingRow | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: categories } = useQuery({
    queryKey: ["event-categories"],
    queryFn: () => categoriesApi.list(),
  });

  // Default to the first category once loaded.
  useEffect(() => {
    if (!categoryId && categories && categories.length > 0) {
      setCategoryId(categories[0].id);
    }
  }, [categories, categoryId]);

  const { data: rows, isLoading } = useQuery({
    queryKey: ["rankings", categoryId, publishedOnly],
    queryFn: () => rankingsApi.list(categoryId, publishedOnly),
    enabled: !!categoryId,
  });

  const anyPublished = !!rows?.some((r) => r.is_published);

  const recalculate = useMutation({
    mutationFn: () => rankingsApi.recalculate(categoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rankings"] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Recalculation failed"),
  });

  const publish = useMutation({
    mutationFn: () => rankingsApi.publish(categoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rankings"] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Publish failed"),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Rankings</h1>
          <p className="text-muted-foreground">
            Automatically computed from tournament results. Recalculate and publish per category.
          </p>
        </div>
        {canManageRules && (
          <Button variant="outline" asChild>
            <Link href="/dashboard/rankings/rules">Ranking Rules</Link>
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-[220px]">
          <Label htmlFor="category" className="sr-only">
            Category
          </Label>
          <Select id="category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">Select a category…</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name} ({cat.code})
              </option>
            ))}
          </Select>
        </div>
        <Select
          className="w-44"
          value={publishedOnly ? "published" : "all"}
          onChange={(e) => setPublishedOnly(e.target.value === "published")}
        >
          <option value="all">Draft + published</option>
          <option value="published">Published only</option>
        </Select>
        <div className="ml-auto flex gap-2">
          {canApprove && (
            <Button
              variant="outline"
              disabled={!categoryId || recalculate.isPending}
              onClick={() => {
                setError(null);
                recalculate.mutate();
              }}
            >
              <RefreshCw className="h-4 w-4" />
              {recalculate.isPending ? "Recalculating…" : "Recalculate"}
            </Button>
          )}
          {canApprove && (
            <Button
              disabled={!categoryId || !rows?.length || publish.isPending}
              onClick={() => {
                setError(null);
                publish.mutate();
              }}
            >
              <Send className="h-4 w-4" />
              {publish.isPending ? "Publishing…" : "Publish"}
            </Button>
          )}
        </div>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {rows && rows.length > 0 && (
          <>
            <span>As of {rows[0].as_of}</span>
            <Badge variant={anyPublished ? "success" : "warning"}>
              {anyPublished ? "Published" : "Draft"}
            </Badge>
          </>
        )}
      </div>

      <Table>
        <THead>
          <TR>
            <TH className="w-16">Rank</TH>
            <TH className="w-20">Move</TH>
            <TH>Player</TH>
            <TH>Club</TH>
            <TH className="text-right">Points</TH>
          </TR>
        </THead>
        <TBody>
          {!categoryId ? (
            <TR>
              <TD colSpan={5} className="py-10 text-center text-muted-foreground">
                Select a category to view its rankings.
              </TD>
            </TR>
          ) : isLoading ? (
            <TR>
              <TD colSpan={5} className="py-10 text-center text-muted-foreground">
                Loading…
              </TD>
            </TR>
          ) : rows && rows.length > 0 ? (
            rows.map((r) => (
              <TR
                key={r.id}
                className="cursor-pointer"
                onClick={() => setHistoryFor(r)}
              >
                <TD className="font-semibold tabular-nums">{r.rank}</TD>
                <TD>
                  <Movement value={r.movement} previous={r.previous_rank} />
                </TD>
                <TD className="font-medium">{r.player_name ?? r.player_id}</TD>
                <TD className="text-muted-foreground">{r.club_name ?? "—"}</TD>
                <TD className="text-right font-semibold tabular-nums">
                  {r.points.toLocaleString()}
                </TD>
              </TR>
            ))
          ) : (
            <TR>
              <TD colSpan={5} className="py-10 text-center text-muted-foreground">
                No rankings yet. Finalize a tournament with a matching ranking rule, then
                recalculate.
              </TD>
            </TR>
          )}
        </TBody>
      </Table>

      {historyFor && (
        <HistoryDialog row={historyFor} onClose={() => setHistoryFor(null)} />
      )}
    </div>
  );
}

function HistoryDialog({ row, onClose }: { row: RankingRow; onClose: () => void }) {
  const { data: history } = useQuery({
    queryKey: ["ranking-history", row.player_id, row.category_id],
    queryFn: () => rankingsApi.history(row.player_id, row.category_id),
  });

  const chartData =
    history?.map((h) => ({
      date: h.snapshot_date,
      rank: h.rank,
      points: h.points,
    })) ?? [];

  return (
    <Dialog open onClose={onClose} className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{row.player_name ?? "Player"} — ranking timeline</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-muted-foreground">Current rank</span>
            <p className="text-2xl font-bold">{row.rank}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Points</span>
            <p className="text-2xl font-bold">{row.points.toLocaleString()}</p>
          </div>
        </div>
        {chartData.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ left: -20, right: 8, top: 8 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis
                  reversed
                  allowDecimals={false}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="rank"
                  stroke="hsl(142 72% 29%)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No history recorded yet.
          </p>
        )}
      </div>
    </Dialog>
  );
}
