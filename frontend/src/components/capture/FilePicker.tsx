import { Upload } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";
import { formatBytes } from "@/lib/format";
import type { MediaRules } from "@/lib/media";
import { cn } from "@/lib/utils";

export function FilePicker({
  rules,
  label,
  disabled,
  onFile,
}: {
  rules: MediaRules;
  label: string;
  disabled?: boolean;
  onFile: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const hintId = useId();

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
        dragging ? "border-primary bg-primary/5" : "border-border",
        disabled && "opacity-60",
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Upload className="size-5" />
      </span>
      <div className="space-y-1">
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:no-underline"
          aria-describedby={hintId}
        >
          {label}
        </button>
        <p className="text-sm text-muted-foreground">or drag and drop</p>
      </div>
      <p id={hintId} className="text-xs text-muted-foreground">
        {rules.extensions.join(", ")} · up to {formatBytes(rules.maxBytes)}
        {rules.minSeconds ? ` · ${rules.minSeconds}–${rules.maxSeconds} s` : ""}
        {rules.minWidth ? ` · at least ${rules.minWidth}×${rules.minHeight}` : ""}
      </p>
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        tabIndex={-1}
        accept={[...rules.accept, ...rules.extensions].join(",")}
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
