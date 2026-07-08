"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { ImageUpload } from "@/components/image-upload";
import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { TBody, TD, TH, THead, TR, Table } from "@/components/ui/table";
import { useMe } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import { type Club, type ClubInput, clubsApi, statesApi } from "@/lib/resources";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  state_id: z.string().optional().or(z.literal("")),
  coach_name: z.string().max(200).optional().or(z.literal("")),
  contact_email: z.string().email("Invalid email").optional().or(z.literal("")),
  contact_phone: z.string().max(40).optional().or(z.literal("")),
  address: z.string().max(400).optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

export default function ClubsPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("clubs:manage");

  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Club | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<Club | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["clubs", q, page],
    queryFn: () => clubsApi.list(q, "", page),
  });
  const { data: states } = useQuery({
    queryKey: ["states", "all"],
    queryFn: () => statesApi.list("", 1, 100),
  });
  const stateName = (id: string | null) =>
    id ? (states?.items.find((s) => s.id === id)?.name ?? "—") : "—";

  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const payload: ClubInput = {
        name: values.name,
        state_id: values.state_id || null,
        coach_name: values.coach_name || null,
        contact_email: values.contact_email || null,
        contact_phone: values.contact_phone || null,
        address: values.address || null,
      };
      return editing ? clubsApi.update(editing.id, payload) : clubsApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clubs"] });
      setDialogOpen(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => clubsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clubs"] });
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    form.reset({
      name: "",
      state_id: "",
      coach_name: "",
      contact_email: "",
      contact_phone: "",
      address: "",
    });
    setDialogOpen(true);
  }
  function openEdit(c: Club) {
    setEditing(c);
    form.reset({
      name: c.name,
      state_id: c.state_id ?? "",
      coach_name: c.coach_name ?? "",
      contact_email: c.contact_email ?? "",
      contact_phone: c.contact_phone ?? "",
      address: c.address ?? "",
    });
    setDialogOpen(true);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Clubs</h1>
          <p className="text-muted-foreground">Clubs, coaches, and contact details.</p>
        </div>
        {canManage && (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> Add Club
          </Button>
        )}
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by name or coach…"
          className="pl-9"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Name</TH>
            <TH>State</TH>
            <TH>Coach</TH>
            <TH>Contact</TH>
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
            data.items.map((c) => (
              <TR key={c.id}>
                <TD className="font-medium">
                  <div className="flex items-center gap-2">
                    {c.logo_url ? (
                      // eslint-disable-next-line @next/next/no-img-element -- remote Supabase URL
                      <img
                        src={c.logo_url}
                        alt=""
                        className="h-7 w-7 rounded object-cover"
                      />
                    ) : null}
                    {c.name}
                  </div>
                </TD>
                <TD>{stateName(c.state_id)}</TD>
                <TD>{c.coach_name ?? "—"}</TD>
                <TD>{c.contact_email ?? c.contact_phone ?? "—"}</TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(c)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(c)}>
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
                No clubs yet.
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

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogHeader>
          <DialogTitle>{editing ? "Edit club" : "Add club"}</DialogTitle>
        </DialogHeader>
        {editing && (
          <div className="mb-4 border-b pb-4">
            <Label className="mb-2 block">Logo</Label>
            <ImageUpload
              url={editing.logo_url}
              alt={editing.name}
              shape="square"
              disabled={!canManage}
              uploader={async (file) => (await clubsApi.uploadLogo(editing.id, file)).logo_url}
              remover={async () => {
                await clubsApi.deleteLogo(editing.id);
              }}
              onChange={(url) => {
                setEditing({ ...editing, logo_url: url });
                qc.invalidateQueries({ queryKey: ["clubs"] });
              }}
            />
          </div>
        )}
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
            <div className="space-y-2">
              <Label htmlFor="coach_name">Coach</Label>
              <Input id="coach_name" {...form.register("coach_name")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contact_email">Contact email</Label>
              <Input id="contact_email" type="email" {...form.register("contact_email")} />
              {form.formState.errors.contact_email && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.contact_email.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_phone">Phone</Label>
              <Input id="contact_phone" {...form.register("contact_phone")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="address">Address</Label>
            <Input id="address" {...form.register("address")} />
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
        title="Delete club"
        description={`Remove “${deleting?.name}”? Players will be unlinked from this club.`}
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
