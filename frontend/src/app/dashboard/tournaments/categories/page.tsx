"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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
import { type EventCategory, type EventCategoryInput, categoriesApi } from "@/lib/resources";

const schema = z.object({
  code: z.string().min(1, "Code is required").max(20),
  name: z.string().min(1, "Name is required").max(120),
  discipline: z.enum(["singles", "doubles"]),
  gender_scope: z.enum(["men", "women", "mixed", "any"]),
  age_min: z.string().optional().or(z.literal("")),
  age_max: z.string().optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

export default function EventCategoriesPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("tournaments:manage");

  const [editing, setEditing] = useState<EventCategory | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<EventCategory | null>(null);

  const { data: categories, isLoading } = useQuery({
    queryKey: ["event-categories", "all"],
    queryFn: () => categoriesApi.list(false),
  });

  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const payload: EventCategoryInput = {
        code: values.code,
        name: values.name,
        discipline: values.discipline,
        gender_scope: values.gender_scope,
        age_min: values.age_min ? Number(values.age_min) : null,
        age_max: values.age_max ? Number(values.age_max) : null,
      };
      return editing ? categoriesApi.update(editing.id, payload) : categoriesApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event-categories"] });
      setDialogOpen(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => categoriesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event-categories"] });
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    form.reset({
      code: "",
      name: "",
      discipline: "singles",
      gender_scope: "any",
      age_min: "",
      age_max: "",
    });
    setDialogOpen(true);
  }
  function openEdit(cat: EventCategory) {
    setEditing(cat);
    form.reset({
      code: cat.code,
      name: cat.name,
      discipline: cat.discipline,
      gender_scope: cat.gender_scope,
      age_min: cat.age_min?.toString() ?? "",
      age_max: cat.age_max?.toString() ?? "",
    });
    setDialogOpen(true);
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/tournaments")}>
        <ArrowLeft className="h-4 w-4" /> Back to tournaments
      </Button>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Event Categories</h1>
          <p className="text-muted-foreground">
            Senior and junior disciplines used when creating tournament events.
          </p>
        </div>
        {canManage && (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> Add Category
          </Button>
        )}
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Code</TH>
            <TH>Name</TH>
            <TH>Discipline</TH>
            <TH>Gender</TH>
            <TH>Age range</TH>
            <TH>Scope</TH>
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
          ) : categories && categories.length > 0 ? (
            categories.map((cat) => (
              <TR key={cat.id}>
                <TD className="font-mono text-xs">{cat.code}</TD>
                <TD className="font-medium">{cat.name}</TD>
                <TD className="capitalize">{cat.discipline}</TD>
                <TD className="capitalize">{cat.gender_scope}</TD>
                <TD>
                  {cat.age_min ?? "0"}–{cat.age_max ?? "∞"}
                </TD>
                <TD>
                  <Badge variant={cat.federation_id ? "default" : "muted"}>
                    {cat.federation_id ? "Federation" : "Global"}
                  </Badge>
                </TD>
                {canManage && (
                  <TD className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(cat)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleting(cat)}>
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
                No categories yet.
              </TD>
            </TR>
          )}
        </TBody>
      </Table>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit category" : "Add category"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit((v) => save.mutate(v))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="code">Code</Label>
              <Input id="code" disabled={!!editing} {...form.register("code")} />
              {form.formState.errors.code && (
                <p className="text-sm text-destructive">{form.formState.errors.code.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="discipline">Discipline</Label>
              <Select id="discipline" disabled={!!editing} {...form.register("discipline")}>
                <option value="singles">Singles</option>
                <option value="doubles">Doubles</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="gender_scope">Gender scope</Label>
              <Select id="gender_scope" {...form.register("gender_scope")}>
                <option value="any">Any</option>
                <option value="men">Men</option>
                <option value="women">Women</option>
                <option value="mixed">Mixed</option>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="age_min">Minimum age (optional)</Label>
              <Input id="age_min" type="number" min={0} {...form.register("age_min")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="age_max">Maximum age (optional)</Label>
              <Input id="age_max" type="number" min={0} {...form.register("age_max")} />
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

      <ConfirmDialog
        open={!!deleting}
        title="Delete category"
        description={`Remove “${deleting?.name}”? Existing events using it are unaffected.`}
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
