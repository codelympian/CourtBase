"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Pagination } from "@/components/pagination";
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
  type Tournament,
  type TournamentInput,
  type TournamentStatus,
  tournamentsApi,
} from "@/lib/resources";

const STATUS_VARIANT: Record<TournamentStatus, "muted" | "success" | "warning" | "default"> = {
  draft: "muted",
  registration_open: "success",
  registration_closed: "warning",
  ongoing: "default",
  completed: "muted",
};

const LEVEL_LABEL: Record<string, string> = {
  national_championship: "National Championship",
  open: "Open",
  invitational: "Invitational",
  ranking: "Ranking Tournament",
};

const schema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  venue: z.string().max(255).optional().or(z.literal("")),
  start_date: z.string().optional().or(z.literal("")),
  end_date: z.string().optional().or(z.literal("")),
  level: z.enum(["national_championship", "open", "invitational", "ranking"]),
  organizer: z.string().max(200).optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

export default function TournamentsPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("tournaments:manage");

  const [q, setQ] = useState("");
  const [status, setStatus] = useState<TournamentStatus | "">("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Tournament | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<Tournament | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["tournaments", q, status, page],
    queryFn: () => tournamentsApi.list(q, status, page),
  });

  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const payload: TournamentInput = {
        name: values.name,
        venue: values.venue || null,
        start_date: values.start_date || null,
        end_date: values.end_date || null,
        level: values.level,
        organizer: values.organizer || null,
      };
      return editing ? tournamentsApi.update(editing.id, payload) : tournamentsApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournaments"] });
      setDialogOpen(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => tournamentsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournaments"] });
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    form.reset({
      name: "",
      venue: "",
      start_date: "",
      end_date: "",
      level: "open",
      organizer: "",
    });
    setDialogOpen(true);
  }
  function openEdit(t: Tournament) {
    setEditing(t);
    form.reset({
      name: t.name,
      venue: t.venue ?? "",
      start_date: t.start_date ?? "",
      end_date: t.end_date ?? "",
      level: t.level,
      organizer: t.organizer ?? "",
    });
    setDialogOpen(true);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Tournaments</h1>
          <p className="text-muted-foreground">
            Create tournaments and manage events, registrations, draws, and scoring.
          </p>
        </div>
        <div className="flex gap-2">
          {canManage && (
            <Button variant="outline" asChild>
              <Link href="/dashboard/tournaments/categories">Event Categories</Link>
            </Button>
          )}
          {canManage && (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" /> New Tournament
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name…"
            className="pl-9"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          className="w-52"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as TournamentStatus | "");
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="registration_open">Registration open</option>
          <option value="registration_closed">Registration closed</option>
          <option value="ongoing">Ongoing</option>
          <option value="completed">Completed</option>
        </Select>
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Name</TH>
            <TH>Level</TH>
            <TH>Dates</TH>
            <TH>Status</TH>
            {canManage && <TH className="text-right">Actions</TH>}
          </TR>
        </THead>
        <TBody>
          {isLoading ? (
            <TR>
              <TD colSpan={5} className="py-10 text-center text-muted-foreground">
                Loading…
              </TD>
            </TR>
          ) : data && data.items.length > 0 ? (
            data.items.map((t) => (
              <TR key={t.id}>
                <TD className="font-medium">
                  <Link href={`/dashboard/tournaments/${t.id}`} className="hover:underline">
                    {t.name}
                  </Link>
                </TD>
                <TD>{LEVEL_LABEL[t.level] ?? t.level}</TD>
                <TD>{t.start_date ?? "—"}{t.end_date ? ` – ${t.end_date}` : ""}</TD>
                <TD>
                  <Badge variant={STATUS_VARIANT[t.status]}>{t.status.replace(/_/g, " ")}</Badge>
                </TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(t)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(t)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TD>
                )}
              </TR>
            ))
          ) : (
            <TR>
              <TD colSpan={5} className="py-10 text-center text-muted-foreground">
                No tournaments yet.
              </TD>
            </TR>
          )}
        </TBody>
      </Table>

      {data && (
        <Pagination
          page={data.page}
          pages={data.pages}
          total={data.total}
          size={data.size}
          onPage={setPage}
        />
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit tournament" : "New tournament"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit((v) => save.mutate(v))} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...form.register("name")} />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="level">Level</Label>
              <Select id="level" {...form.register("level")}>
                <option value="national_championship">National Championship</option>
                <option value="open">Open</option>
                <option value="invitational">Invitational</option>
                <option value="ranking">Ranking Tournament</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="venue">Venue</Label>
              <Input id="venue" {...form.register("venue")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start_date">Start date</Label>
              <Input id="start_date" type="date" {...form.register("start_date")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end_date">End date</Label>
              <Input id="end_date" type="date" {...form.register("end_date")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="organizer">Organizer</Label>
            <Input id="organizer" {...form.register("organizer")} />
          </div>
          {save.isError && (
            <p className="text-sm text-destructive">
              {(save.error as ApiError)?.message ?? "Something went wrong"}
            </p>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      <ConfirmDialog
        open={!!deleting}
        title="Delete tournament"
        description={`Remove “${deleting?.name}”? This is a soft delete.`}
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
