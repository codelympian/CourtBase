"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { TBody, TD, TH, THead, TR, Table } from "@/components/ui/table";
import { useMe } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import {
  type EventCategory,
  type TournamentEvent,
  type TournamentStatus,
  categoriesApi,
  eventsApi,
  tournamentsApi,
} from "@/lib/resources";

const STATUS_FLOW: TournamentStatus[] = [
  "draft",
  "registration_open",
  "registration_closed",
  "ongoing",
  "completed",
];

const STATUS_VARIANT: Record<TournamentStatus, "muted" | "success" | "warning" | "default"> = {
  draft: "muted",
  registration_open: "success",
  registration_closed: "warning",
  ongoing: "default",
  completed: "muted",
};

const EVENT_STATUS_VARIANT: Record<string, "muted" | "success" | "warning" | "default"> = {
  pending: "muted",
  draw_published: "warning",
  ongoing: "default",
  completed: "success",
};

export default function TournamentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("tournaments:manage");
  const canFinalize = !!me?.permissions.includes("tournaments:finalize");

  const [addEventOpen, setAddEventOpen] = useState(false);
  const [categoryId, setCategoryId] = useState("");
  const [deletingEvent, setDeletingEvent] = useState<TournamentEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: tournament, isLoading } = useQuery({
    queryKey: ["tournament", id],
    queryFn: () => tournamentsApi.get(id),
  });
  const { data: events } = useQuery({
    queryKey: ["tournament-events", id],
    queryFn: () => tournamentsApi.listEvents(id),
  });
  const { data: categories } = useQuery({
    queryKey: ["event-categories"],
    queryFn: () => categoriesApi.list(),
  });

  const setStatus = useMutation({
    mutationFn: (status: TournamentStatus) => tournamentsApi.update(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament", id] }),
  });

  const finalize = useMutation({
    mutationFn: () => tournamentsApi.finalize(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament", id] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not finalize"),
  });

  const addEvent = useMutation({
    mutationFn: () => tournamentsApi.createEvent(id, categoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournament-events", id] });
      qc.invalidateQueries({ queryKey: ["tournament", id] });
      setAddEventOpen(false);
      setCategoryId("");
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not create event"),
  });

  const removeEvent = useMutation({
    mutationFn: (eventId: string) => eventsApi.remove(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournament-events", id] });
      setDeletingEvent(null);
    },
  });

  if (isLoading || !tournament) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/tournaments")}>
        <ArrowLeft className="h-4 w-4" /> Back to tournaments
      </Button>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{tournament.name}</h1>
          <p className="text-muted-foreground">
            {tournament.venue ?? "No venue set"}
            {tournament.start_date ? ` · ${tournament.start_date}` : ""}
            {tournament.end_date ? ` – ${tournament.end_date}` : ""}
          </p>
        </div>
        <Badge variant={STATUS_VARIANT[tournament.status]} className="text-sm">
          {tournament.status.replace(/_/g, " ")}
        </Badge>
      </div>

      {canManage && (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-3 py-4">
            <Label className="mb-0">Status</Label>
            <Select
              className="w-56"
              value={tournament.status}
              onChange={(e) => setStatus.mutate(e.target.value as TournamentStatus)}
              disabled={setStatus.isPending}
            >
              {STATUS_FLOW.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
            {canFinalize && tournament.status !== "completed" && (
              <Button
                variant="outline"
                onClick={() => finalize.mutate()}
                disabled={finalize.isPending}
              >
                <CheckCircle2 className="h-4 w-4" />
                {finalize.isPending ? "Finalizing…" : "Finalize tournament"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Events</h2>
        {canManage && (
          <Button onClick={() => setAddEventOpen(true)}>
            <Plus className="h-4 w-4" /> Add Event
          </Button>
        )}
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Category</TH>
            <TH>Draw size</TH>
            <TH>Status</TH>
            {canManage && <TH className="text-right">Actions</TH>}
          </TR>
        </THead>
        <TBody>
          {events && events.length > 0 ? (
            events.map((e) => (
              <TR key={e.id}>
                <TD className="font-medium">
                  <Link
                    href={`/dashboard/tournaments/${id}/events/${e.id}`}
                    className="hover:underline"
                  >
                    {e.name}
                  </Link>
                </TD>
                <TD>{e.draw_size ?? "—"}</TD>
                <TD>
                  <Badge variant={EVENT_STATUS_VARIANT[e.status] ?? "muted"}>
                    {e.status.replace(/_/g, " ")}
                  </Badge>
                </TD>
                {canManage && (
                  <TD className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => setDeletingEvent(e)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TD>
                )}
              </TR>
            ))
          ) : (
            <TR>
              <TD colSpan={4} className="py-10 text-center text-muted-foreground">
                No events yet. Add one to start registering players.
              </TD>
            </TR>
          )}
        </TBody>
      </Table>

      <Dialog open={addEventOpen} onClose={() => setAddEventOpen(false)}>
        <DialogHeader>
          <DialogTitle>Add event</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="category">Category</Label>
            <Select
              id="category"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">Select a category…</option>
              {categories?.map((c: EventCategory) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code})
                </option>
              ))}
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setAddEventOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!categoryId || addEvent.isPending} onClick={() => addEvent.mutate()}>
            {addEvent.isPending ? "Adding…" : "Add event"}
          </Button>
        </DialogFooter>
      </Dialog>

      <ConfirmDialog
        open={!!deletingEvent}
        title="Delete event"
        description={`Remove “${deletingEvent?.name}”? This is only possible before a draw is generated.`}
        loading={removeEvent.isPending}
        onConfirm={() => deletingEvent && removeEvent.mutate(deletingEvent.id)}
        onClose={() => setDeletingEvent(null)}
      />
    </div>
  );
}
