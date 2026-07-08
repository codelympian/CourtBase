"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, RotateCcw, Shuffle, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { TBody, TD, TH, THead, TR, Table } from "@/components/ui/table";
import { useMe } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import {
  type BracketMatch,
  type Registration,
  categoriesApi,
  eventsApi,
  matchesApi,
  playersApi,
  registrationsApi,
} from "@/lib/resources";

const REG_STATUS_VARIANT: Record<string, "muted" | "success" | "warning" | "danger"> = {
  pending: "warning",
  confirmed: "success",
  withdrawn: "muted",
  rejected: "danger",
};

export default function EventDetailPage() {
  const { id, eventId } = useParams<{ id: string; eventId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("tournaments:manage");
  const canManageDraws = !!me?.permissions.includes("draws:manage");
  const canEnterScores = !!me?.permissions.includes("scores:enter");

  const [addOpen, setAddOpen] = useState(false);
  const [playerId, setPlayerId] = useState("");
  const [partnerId, setPartnerId] = useState("");
  const [seed, setSeed] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState<Registration | null>(null);
  const [scoringMatch, setScoringMatch] = useState<BracketMatch | null>(null);

  const { data: event } = useQuery({
    queryKey: ["event", eventId],
    queryFn: () => eventsApi.get(eventId),
  });
  const { data: registrations } = useQuery({
    queryKey: ["event-registrations", eventId],
    queryFn: () => eventsApi.listRegistrations(eventId),
  });
  const { data: bracket } = useQuery({
    queryKey: ["event-bracket", eventId],
    queryFn: () => eventsApi.getDraw(eventId),
    enabled: !!event?.draw_size,
  });
  const { data: categories } = useQuery({
    queryKey: ["event-categories"],
    queryFn: () => categoriesApi.list(),
  });
  const { data: players } = useQuery({
    queryKey: ["players", "active-all"],
    queryFn: () => playersApi.list({ status: "active", size: 100 }),
  });

  const category = categories?.find((c) => c.id === event?.category_id);
  const isDoubles = category?.discipline === "doubles";

  const confirmedCount =
    registrations?.items.filter((r) => r.status === "confirmed").length ?? 0;

  const addRegistration = useMutation({
    mutationFn: () =>
      eventsApi.createRegistration(eventId, {
        player_id: playerId,
        partner_player_id: isDoubles ? partnerId || null : null,
        seed: seed ? Number(seed) : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event-registrations", eventId] });
      qc.invalidateQueries({ queryKey: ["event", eventId] });
      setAddOpen(false);
      setPlayerId("");
      setPartnerId("");
      setSeed("");
      setError(null);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not register player"),
  });

  const confirmRegistration = useMutation({
    mutationFn: (regId: string) => registrationsApi.update(regId, { status: "confirmed" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["event-registrations", eventId] }),
  });

  const withdrawRegistration = useMutation({
    mutationFn: (regId: string) => registrationsApi.remove(regId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event-registrations", eventId] });
      setWithdrawing(null);
    },
  });

  const generateDraw = useMutation({
    mutationFn: () => eventsApi.generateDraw(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event", eventId] });
      qc.invalidateQueries({ queryKey: ["event-bracket", eventId] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not generate draw"),
  });

  const resetDraw = useMutation({
    mutationFn: () => eventsApi.resetDraw(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event", eventId] });
      qc.invalidateQueries({ queryKey: ["event-bracket", eventId] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not reset draw"),
  });

  if (!event) return <p className="text-muted-foreground">Loading…</p>;

  const rounds = Array.from(new Set((bracket ?? []).map((m) => m.round))).sort((a, b) => a - b);

  return (
    <div className="space-y-6">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.push(`/dashboard/tournaments/${id}`)}
      >
        <ArrowLeft className="h-4 w-4" /> Back to tournament
      </Button>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{event.name}</h1>
          <p className="text-muted-foreground">
            {event.category_name} · {event.registration_count} registered
            {event.draw_size ? ` · draw of ${event.draw_size}` : ""}
          </p>
        </div>
        <Badge variant="default">{event.status.replace(/_/g, " ")}</Badge>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Registrations</h2>
        {canManage && !event.draw_size && (
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Register player
          </Button>
        )}
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Player</TH>
            {isDoubles && <TH>Partner</TH>}
            <TH>Seed</TH>
            <TH>Status</TH>
            {canManage && <TH className="text-right">Actions</TH>}
          </TR>
        </THead>
        <TBody>
          {registrations && registrations.items.length > 0 ? (
            registrations.items.map((r) => (
              <TR key={r.id}>
                <TD className="font-medium">{r.player_name ?? r.player_id}</TD>
                {isDoubles && <TD>{r.partner_name ?? "—"}</TD>}
                <TD>{r.seed ?? "—"}</TD>
                <TD>
                  <Badge variant={REG_STATUS_VARIANT[r.status] ?? "muted"}>{r.status}</Badge>
                </TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      {r.status === "pending" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => confirmRegistration.mutate(r.id)}
                          disabled={confirmRegistration.isPending}
                        >
                          Confirm
                        </Button>
                      )}
                      {!event.draw_size && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setWithdrawing(r)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TD>
                )}
              </TR>
            ))
          ) : (
            <TR>
              <TD colSpan={isDoubles ? 5 : 4} className="py-10 text-center text-muted-foreground">
                No registrations yet.
              </TD>
            </TR>
          )}
        </TBody>
      </Table>

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Draw</h2>
        {canManageDraws && (
          <div className="flex gap-2">
            {!event.draw_size ? (
              <Button
                onClick={() => generateDraw.mutate()}
                disabled={confirmedCount < 2 || generateDraw.isPending}
              >
                <Shuffle className="h-4 w-4" />
                {generateDraw.isPending ? "Generating…" : "Generate Draw"}
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => resetDraw.mutate()}
                disabled={resetDraw.isPending}
              >
                <RotateCcw className="h-4 w-4" />
                {resetDraw.isPending ? "Resetting…" : "Reset Draw"}
              </Button>
            )}
          </div>
        )}
      </div>

      {!event.draw_size ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            {confirmedCount < 2
              ? `Confirm at least 2 registrations to generate a draw (${confirmedCount} confirmed).`
              : "Ready — generate the draw to create the bracket."}
          </CardContent>
        </Card>
      ) : (
        <div className="flex gap-6 overflow-x-auto pb-4">
          {rounds.map((round) => {
            const matches = (bracket ?? [])
              .filter((m) => m.round === round)
              .sort((a, b) => a.position - b.position);
            return (
              <div key={round} className="flex w-64 shrink-0 flex-col gap-4">
                <p className="text-center text-sm font-semibold text-muted-foreground">
                  {matches[0]?.round_name ?? `Round ${round}`}
                </p>
                {matches.map((m) => (
                  <MatchCard
                    key={m.id}
                    match={m}
                    canScore={canEnterScores}
                    onScore={() => setScoringMatch(m)}
                  />
                ))}
              </div>
            );
          })}
        </div>
      )}

      {/* Register player dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)}>
        <DialogHeader>
          <DialogTitle>Register player</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="player">Player</Label>
            <Select id="player" value={playerId} onChange={(e) => setPlayerId(e.target.value)}>
              <option value="">Select a player…</option>
              {players?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name} ({p.federation_player_code})
                </option>
              ))}
            </Select>
          </div>
          {isDoubles && (
            <div className="space-y-2">
              <Label htmlFor="partner">Partner</Label>
              <Select id="partner" value={partnerId} onChange={(e) => setPartnerId(e.target.value)}>
                <option value="">Select a partner…</option>
                {players?.items
                  .filter((p) => p.id !== playerId)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_name} ({p.federation_player_code})
                    </option>
                  ))}
              </Select>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="seed">Seed (optional)</Label>
            <Input
              id="seed"
              type="number"
              min={1}
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setAddOpen(false)}>
            Cancel
          </Button>
          <Button
            disabled={!playerId || (isDoubles && !partnerId) || addRegistration.isPending}
            onClick={() => addRegistration.mutate()}
          >
            {addRegistration.isPending ? "Registering…" : "Register"}
          </Button>
        </DialogFooter>
      </Dialog>

      <ConfirmDialog
        open={!!withdrawing}
        title="Withdraw registration"
        description={`Withdraw ${withdrawing?.player_name ?? "this player"} from the event?`}
        confirmLabel="Withdraw"
        loading={withdrawRegistration.isPending}
        onConfirm={() => withdrawing && withdrawRegistration.mutate(withdrawing.id)}
        onClose={() => setWithdrawing(null)}
      />

      {scoringMatch && (
        <ScoreDialog
          match={scoringMatch}
          eventId={eventId}
          onClose={() => setScoringMatch(null)}
        />
      )}
    </div>
  );
}

function MatchCard({
  match,
  canScore,
  onScore,
}: {
  match: BracketMatch;
  canScore: boolean;
  onScore: () => void;
}) {
  const canEnter =
    canScore &&
    match.status === "scheduled" &&
    match.player1_id !== null &&
    match.player2_id !== null;
  return (
    <Card>
      <CardContent className="space-y-2 py-3 text-sm">
        <PlayerLine
          name={match.player1_name}
          won={match.winner_id !== null && match.winner_id === match.player1_id}
        />
        <PlayerLine
          name={match.player2_name}
          won={match.winner_id !== null && match.winner_id === match.player2_id}
        />
        {match.score && (
          <p className="text-xs text-muted-foreground">
            {match.score.map((g) => g.join("-")).join(", ")}
          </p>
        )}
        {match.status === "bye" && <p className="text-xs text-muted-foreground">Bye</p>}
        {match.status === "walkover" && <p className="text-xs text-muted-foreground">Walkover</p>}
        {canEnter && (
          <Button size="sm" variant="outline" className="w-full" onClick={onScore}>
            Enter score
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function PlayerLine({ name, won }: { name: string | null | undefined; won: boolean }) {
  return (
    <p className={won ? "font-semibold" : "text-muted-foreground"}>{name ?? "TBD"}</p>
  );
}

function ScoreDialog({
  match,
  eventId,
  onClose,
}: {
  match: BracketMatch;
  eventId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"score" | "walkover">("score");
  const [games, setGames] = useState<[string, string][]>([
    ["", ""],
    ["", ""],
  ]);
  const [walkoverWinner, setWalkoverWinner] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () => {
      if (mode === "walkover") {
        return matchesApi.score(match.id, { walkover_winner_id: walkoverWinner });
      }
      const parsed = games
        .filter(([a, b]) => a !== "" || b !== "")
        .map(([a, b]) => [Number(a), Number(b)]);
      return matchesApi.score(match.id, { score: parsed });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event-bracket", eventId] });
      qc.invalidateQueries({ queryKey: ["event", eventId] });
      onClose();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not record score"),
  });

  return (
    <Dialog open onClose={onClose}>
      <DialogHeader>
        <DialogTitle>
          {match.player1_name ?? "TBD"} vs {match.player2_name ?? "TBD"}
        </DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="flex gap-2">
          <Button
            type="button"
            variant={mode === "score" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("score")}
          >
            Score
          </Button>
          <Button
            type="button"
            variant={mode === "walkover" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("walkover")}
          >
            Walkover
          </Button>
        </div>

        {mode === "score" ? (
          <div className="space-y-2">
            {games.map(([a, b], i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-16 text-sm text-muted-foreground">Game {i + 1}</span>
                <Input
                  type="number"
                  min={0}
                  value={a}
                  onChange={(e) => {
                    const next = [...games] as [string, string][];
                    next[i] = [e.target.value, next[i][1]];
                    setGames(next);
                  }}
                />
                <span>–</span>
                <Input
                  type="number"
                  min={0}
                  value={b}
                  onChange={(e) => {
                    const next = [...games] as [string, string][];
                    next[i] = [next[i][0], e.target.value];
                    setGames(next);
                  }}
                />
              </div>
            ))}
            {games.length < 3 && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setGames([...games, ["", ""]])}
              >
                <Plus className="h-4 w-4" /> Add deciding game
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="walkover">Winner</Label>
            <Select
              id="walkover"
              value={walkoverWinner}
              onChange={(e) => setWalkoverWinner(e.target.value)}
            >
              <option value="">Select winner…</option>
              {match.player1_id && (
                <option value={match.player1_id}>{match.player1_name}</option>
              )}
              {match.player2_id && (
                <option value={match.player2_id}>{match.player2_name}</option>
              )}
            </Select>
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button
          disabled={
            submit.isPending || (mode === "walkover" ? !walkoverWinner : games.length < 2)
          }
          onClick={() => submit.mutate()}
        >
          {submit.isPending ? "Saving…" : "Save score"}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
