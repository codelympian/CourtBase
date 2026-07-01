"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
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
  type ImportResult,
  type Player,
  type PlayerInput,
  type PlayerStatus,
  clubsApi,
  playersApi,
  statesApi,
} from "@/lib/resources";

const STATUS_VARIANT: Record<PlayerStatus, "success" | "muted" | "warning" | "danger"> = {
  active: "success",
  inactive: "muted",
  suspended: "danger",
  retired: "warning",
};

const schema = z.object({
  federation_player_code: z.string().min(1, "Code is required").max(40),
  full_name: z.string().min(1, "Name is required").max(200),
  gender: z.enum(["M", "F", "O"]),
  date_of_birth: z.string().optional().or(z.literal("")),
  nationality: z.string().max(80).optional().or(z.literal("")),
  phone: z.string().max(40).optional().or(z.literal("")),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  status: z.enum(["active", "inactive", "suspended", "retired"]),
  club_id: z.string().optional().or(z.literal("")),
  state_id: z.string().optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

export default function PlayersPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("players:manage");
  const canImport = !!me?.permissions.includes("players:import");
  const canExport = !!me?.permissions.includes("reports:export");

  const [q, setQ] = useState("");
  const [status, setStatus] = useState<PlayerStatus | "">("");
  const [gender, setGender] = useState<"M" | "F" | "O" | "">("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Player | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<Player | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["players", q, status, gender, page],
    queryFn: () => playersApi.list({ q, status, gender, page }),
  });
  const { data: clubs } = useQuery({
    queryKey: ["clubs", "all"],
    queryFn: () => clubsApi.list("", "", 1, 100),
  });
  const { data: states } = useQuery({
    queryKey: ["states", "all"],
    queryFn: () => statesApi.list("", 1, 100),
  });
  const clubName = (id: string | null) =>
    id ? (clubs?.items.find((c) => c.id === id)?.name ?? "—") : "—";

  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const payload: PlayerInput = {
        federation_player_code: values.federation_player_code,
        full_name: values.full_name,
        gender: values.gender,
        date_of_birth: values.date_of_birth || null,
        nationality: values.nationality || null,
        phone: values.phone || null,
        email: values.email || null,
        status: values.status,
        club_id: values.club_id || null,
        state_id: values.state_id || null,
      };
      return editing ? playersApi.update(editing.id, payload) : playersApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["players"] });
      setDialogOpen(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => playersApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["players"] });
      setDeleting(null);
    },
  });

  const importMut = useMutation({
    mutationFn: (file: File) => playersApi.importFile(file),
    onSuccess: (res) => {
      setImportResult(res);
      qc.invalidateQueries({ queryKey: ["players"] });
    },
  });

  async function handleExport(format: "csv" | "xlsx") {
    const blob = await playersApi.exportFile(format);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `players.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function openCreate() {
    setEditing(null);
    form.reset({
      federation_player_code: "",
      full_name: "",
      gender: "M",
      date_of_birth: "",
      nationality: "",
      phone: "",
      email: "",
      status: "active",
      club_id: "",
      state_id: "",
    });
    setDialogOpen(true);
  }
  function openEdit(p: Player) {
    setEditing(p);
    form.reset({
      federation_player_code: p.federation_player_code,
      full_name: p.full_name,
      gender: p.gender,
      date_of_birth: p.date_of_birth ?? "",
      nationality: p.nationality ?? "",
      phone: p.phone ?? "",
      email: p.email ?? "",
      status: p.status,
      club_id: p.club_id ?? "",
      state_id: p.state_id ?? "",
    });
    setDialogOpen(true);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Players</h1>
          <p className="text-muted-foreground">
            Registry of federation players with search, filtering, and import/export.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canExport && (
            <>
              <Button variant="outline" onClick={() => handleExport("csv")}>
                <Download className="h-4 w-4" /> CSV
              </Button>
              <Button variant="outline" onClick={() => handleExport("xlsx")}>
                <Download className="h-4 w-4" /> Excel
              </Button>
            </>
          )}
          {canImport && (
            <>
              <input
                ref={fileInput}
                type="file"
                accept=".csv,.xlsx,.xlsm"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importMut.mutate(f);
                  e.target.value = "";
                }}
              />
              <Button
                variant="outline"
                onClick={() => fileInput.current?.click()}
                disabled={importMut.isPending}
              >
                <Upload className="h-4 w-4" /> {importMut.isPending ? "Importing…" : "Import"}
              </Button>
            </>
          )}
          {canManage && (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" /> Add Player
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search name, code, or email…"
            className="pl-9"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          className="w-40"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as PlayerStatus | "");
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
          <option value="retired">Retired</option>
        </Select>
        <Select
          className="w-36"
          value={gender}
          onChange={(e) => {
            setGender(e.target.value as "M" | "F" | "O" | "");
            setPage(1);
          }}
        >
          <option value="">All genders</option>
          <option value="M">Male</option>
          <option value="F">Female</option>
          <option value="O">Other</option>
        </Select>
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Code</TH>
            <TH>Name</TH>
            <TH>Gender</TH>
            <TH>Category</TH>
            <TH>Club</TH>
            <TH>Status</TH>
            {canManage && <TH className="text-right">Actions</TH>}
          </TR>
        </THead>
        <TBody>
          {isLoading ? (
            <TR>
              <TD colSpan={7} className="py-10 text-center text-muted-foreground">
                Loading…
              </TD>
            </TR>
          ) : data && data.items.length > 0 ? (
            data.items.map((p) => (
              <TR key={p.id}>
                <TD className="font-mono text-xs">{p.federation_player_code}</TD>
                <TD className="font-medium">{p.full_name}</TD>
                <TD>{p.gender}</TD>
                <TD>{p.age_category ?? "—"}</TD>
                <TD>{clubName(p.club_id)}</TD>
                <TD>
                  <Badge variant={STATUS_VARIANT[p.status]}>{p.status}</Badge>
                </TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(p)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(p)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TD>
                )}
              </TR>
            ))
          ) : (
            <TR>
              <TD colSpan={7} className="py-10 text-center text-muted-foreground">
                No players match your filters.
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

      {/* Create / edit dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit player" : "Add player"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit((v) => save.mutate(v))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="federation_player_code">Federation code</Label>
              <Input id="federation_player_code" {...form.register("federation_player_code")} />
              {form.formState.errors.federation_player_code && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.federation_player_code.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" {...form.register("full_name")} />
              {form.formState.errors.full_name && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.full_name.message}
                </p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="gender">Gender</Label>
              <Select id="gender" {...form.register("gender")}>
                <option value="M">Male</option>
                <option value="F">Female</option>
                <option value="O">Other</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="date_of_birth">Date of birth</Label>
              <Input id="date_of_birth" type="date" {...form.register("date_of_birth")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select id="status" {...form.register("status")}>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
                <option value="retired">Retired</option>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="club_id">Club</Label>
              <Select id="club_id" {...form.register("club_id")}>
                <option value="">— None —</option>
                {clubs?.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="state_id">State</Label>
              <Select id="state_id" {...form.register("state_id")}>
                <option value="">— None —</option>
                {states?.items.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="nationality">Nationality</Label>
              <Input id="nationality" {...form.register("nationality")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" {...form.register("phone")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...form.register("email")} />
              {form.formState.errors.email && (
                <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
              )}
            </div>
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

      {/* Import result dialog */}
      <Dialog open={!!importResult} onClose={() => setImportResult(null)}>
        <DialogHeader>
          <DialogTitle>Import complete</DialogTitle>
        </DialogHeader>
        {importResult && (
          <div className="space-y-3 text-sm">
            <div className="flex gap-4">
              <Badge variant="success">Created {importResult.created}</Badge>
              <Badge variant="default">Updated {importResult.updated}</Badge>
              <Badge variant="muted">Skipped {importResult.skipped}</Badge>
            </div>
            {importResult.errors.length > 0 && (
              <div className="max-h-48 space-y-1 overflow-y-auto rounded-md border p-3">
                {importResult.errors.map((e, i) => (
                  <p key={i} className="text-destructive">
                    Row {e.row}: {e.message}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
        <DialogFooter>
          <Button onClick={() => setImportResult(null)}>Done</Button>
        </DialogFooter>
      </Dialog>

      <ConfirmDialog
        open={!!deleting}
        title="Delete player"
        description={`Remove “${deleting?.full_name}”? This is a soft delete.`}
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
