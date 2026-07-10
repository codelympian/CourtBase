"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { TBody, TD, TH, THead, TR, Table } from "@/components/ui/table";
import { useMe } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import {
  type RankingRule,
  type TournamentLevel,
  categoriesApi,
  rankingRulesApi,
} from "@/lib/resources";

const LEVELS: { value: TournamentLevel; label: string }[] = [
  { value: "national_championship", label: "National Championship" },
  { value: "open", label: "Open" },
  { value: "invitational", label: "Invitational" },
  { value: "ranking", label: "Ranking Tournament" },
];

// Result keys the engine understands, best finish first.
const RESULT_KEYS: { key: string; label: string }[] = [
  { key: "winner", label: "Winner" },
  { key: "runner_up", label: "Runner-up" },
  { key: "semi_final", label: "Semi-final" },
  { key: "quarter_final", label: "Quarter-final" },
  { key: "round_16", label: "Round of 16" },
  { key: "round_32", label: "Round of 32" },
  { key: "round_64", label: "Round of 64" },
];

type PointsState = Record<string, string>;

export default function RankingRulesPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("ranking_rules:manage");

  const [editing, setEditing] = useState<RankingRule | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<RankingRule | null>(null);
  const [name, setName] = useState("");
  const [level, setLevel] = useState<TournamentLevel>("national_championship");
  const [categoryId, setCategoryId] = useState("");
  const [points, setPoints] = useState<PointsState>({});
  const [error, setError] = useState<string | null>(null);

  const { data: rules, isLoading } = useQuery({
    queryKey: ["ranking-rules"],
    queryFn: () => rankingRulesApi.list(),
  });
  const { data: categories } = useQuery({
    queryKey: ["event-categories"],
    queryFn: () => categoriesApi.list(),
  });
  const categoryName = (id: string | null) =>
    id ? (categories?.find((c) => c.id === id)?.name ?? id) : "All categories";

  function openCreate() {
    setEditing(null);
    setName("");
    setLevel("national_championship");
    setCategoryId("");
    setPoints({});
    setError(null);
    setDialogOpen(true);
  }
  function openEdit(rule: RankingRule) {
    setEditing(rule);
    setName(rule.name);
    setLevel(rule.level);
    setCategoryId(rule.category_id ?? "");
    const p: PointsState = {};
    for (const row of rule.points) p[row.result_key] = String(row.points);
    setPoints(p);
    setError(null);
    setDialogOpen(true);
  }

  const save = useMutation({
    mutationFn: () => {
      const pointsList = RESULT_KEYS.map((r) => ({
        result_key: r.key,
        points: Number(points[r.key] ?? 0),
      })).filter((p) => p.points > 0);
      const payload = {
        name,
        level,
        category_id: categoryId || null,
        points: pointsList,
      };
      return editing
        ? rankingRulesApi.update(editing.id, payload)
        : rankingRulesApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ranking-rules"] });
      setDialogOpen(false);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not save rule"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => rankingRulesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ranking-rules"] });
      setDeleting(null);
    },
  });

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/rankings")}>
        <ArrowLeft className="h-4 w-4" /> Back to rankings
      </Button>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Ranking Rules</h1>
          <p className="text-muted-foreground">
            Points awarded per finishing result, by tournament level and (optionally) category.
          </p>
        </div>
        {canManage && (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> New Rule
          </Button>
        )}
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Name</TH>
            <TH>Level</TH>
            <TH>Category</TH>
            <TH>Winner pts</TH>
            <TH>Active</TH>
            {canManage && <TH className="text-right">Actions</TH>}
          </TR>
        </THead>
        <TBody>
          {isLoading ? (
            <TR>
              <TD colSpan={6} className="py-10 text-center text-muted-foreground">
                Loading…
              </TD>
            </TR>
          ) : rules && rules.length > 0 ? (
            rules.map((rule) => (
              <TR key={rule.id}>
                <TD className="font-medium">{rule.name}</TD>
                <TD>{LEVELS.find((l) => l.value === rule.level)?.label ?? rule.level}</TD>
                <TD>{categoryName(rule.category_id)}</TD>
                <TD className="tabular-nums">
                  {rule.points.find((p) => p.result_key === "winner")?.points.toLocaleString() ??
                    "—"}
                </TD>
                <TD>
                  <Badge variant={rule.is_active ? "success" : "muted"}>
                    {rule.is_active ? "Active" : "Inactive"}
                  </Badge>
                </TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(rule)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(rule)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TD>
                )}
              </TR>
            ))
          ) : (
            <TR>
              <TD colSpan={6} className="py-10 text-center text-muted-foreground">
                No ranking rules yet.
              </TD>
            </TR>
          )}
        </TBody>
      </Table>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit rule" : "New ranking rule"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="level">Tournament level</Label>
              <Select
                id="level"
                value={level}
                onChange={(e) => setLevel(e.target.value as TournamentLevel)}
              >
                {LEVELS.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select
                id="category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">All categories</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Points table</Label>
            <div className="grid grid-cols-2 gap-3">
              {RESULT_KEYS.map((r) => (
                <div key={r.key} className="flex items-center gap-2">
                  <span className="w-28 text-sm text-muted-foreground">{r.label}</span>
                  <Input
                    type="number"
                    min={0}
                    value={points[r.key] ?? ""}
                    onChange={(e) => setPoints({ ...points, [r.key]: e.target.value })}
                    placeholder="0"
                  />
                </div>
              ))}
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setDialogOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!name || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </Dialog>

      <ConfirmDialog
        open={!!deleting}
        title="Delete ranking rule"
        description={`Remove “${deleting?.name}”? Past awards are unaffected, but future finalizations won't use it.`}
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
