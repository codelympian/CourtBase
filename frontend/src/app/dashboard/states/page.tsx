"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TBody, TD, TH, THead, TR, Table } from "@/components/ui/table";
import { useMe } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import { type State, type StateInput, statesApi } from "@/lib/resources";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(150),
  code: z.string().max(20).optional().or(z.literal("")),
  contact_email: z.string().email("Invalid email").optional().or(z.literal("")),
  contact_phone: z.string().max(40).optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

export default function StatesPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("states:manage");

  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<State | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<State | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["states", q, page],
    queryFn: () => statesApi.list(q, page),
  });

  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const payload: StateInput = {
        name: values.name,
        code: values.code || null,
        contact_email: values.contact_email || null,
        contact_phone: values.contact_phone || null,
      };
      return editing ? statesApi.update(editing.id, payload) : statesApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["states"] });
      setDialogOpen(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => statesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["states"] });
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    form.reset({ name: "", code: "", contact_email: "", contact_phone: "" });
    setDialogOpen(true);
  }
  function openEdit(s: State) {
    setEditing(s);
    form.reset({
      name: s.name,
      code: s.code ?? "",
      contact_email: s.contact_email ?? "",
      contact_phone: s.contact_phone ?? "",
    });
    setDialogOpen(true);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">State Associations</h1>
          <p className="text-muted-foreground">Manage state badminton associations.</p>
        </div>
        {canManage && (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> Add State
          </Button>
        )}
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by name or code…"
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
            <TH>Code</TH>
            <TH>Contact email</TH>
            <TH>Phone</TH>
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
            data.items.map((s) => (
              <TR key={s.id}>
                <TD className="font-medium">{s.name}</TD>
                <TD>{s.code ?? "—"}</TD>
                <TD>{s.contact_email ?? "—"}</TD>
                <TD>{s.contact_phone ?? "—"}</TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(s)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(s)}>
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
                No state associations yet.
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
          <DialogTitle>{editing ? "Edit state" : "Add state"}</DialogTitle>
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
              <Label htmlFor="code">Code</Label>
              <Input id="code" {...form.register("code")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_phone">Phone</Label>
              <Input id="contact_phone" {...form.register("contact_phone")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_email">Contact email</Label>
            <Input id="contact_email" type="email" {...form.register("contact_email")} />
            {form.formState.errors.contact_email && (
              <p className="text-sm text-destructive">
                {form.formState.errors.contact_email.message}
              </p>
            )}
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
        title="Delete state association"
        description={`Remove “${deleting?.name}”? This is a soft delete and can be restored by an admin.`}
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
