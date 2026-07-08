"use client";

import { ImageIcon, Loader2, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPT = "image/png,image/jpeg,image/webp";

interface ImageUploadProps {
  url: string | null;
  alt: string;
  shape?: "circle" | "square";
  disabled?: boolean;
  /** Uploads the file and resolves to the new public URL. */
  uploader: (file: File) => Promise<string | null>;
  /** Removes the stored image. */
  remover: () => Promise<void>;
  onChange: (url: string | null) => void;
}

export function ImageUpload({
  url,
  alt,
  shape = "circle",
  disabled = false,
  uploader,
  remover,
  onChange,
}: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      onChange(await uploader(file));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleRemove() {
    setError(null);
    setBusy(true);
    try {
      await remover();
      onChange(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Remove failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-4">
      <div
        className={cn(
          "relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden border bg-muted",
          shape === "circle" ? "rounded-full" : "rounded-md",
        )}
      >
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element -- remote Supabase URL
          <img src={url} alt={alt} className="h-full w-full object-cover" />
        ) : (
          <ImageIcon className="h-8 w-8 text-muted-foreground" />
        )}
        {busy && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/60">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        )}
      </div>

      <div className="space-y-2">
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled || busy}
            onClick={() => inputRef.current?.click()}
          >
            <Upload className="h-4 w-4" /> {url ? "Replace" : "Upload"}
          </Button>
          {url && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={disabled || busy}
              onClick={handleRemove}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">PNG, JPEG or WebP · max 5 MB</p>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    </div>
  );
}
