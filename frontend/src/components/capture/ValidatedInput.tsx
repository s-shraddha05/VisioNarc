import { Loader2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { FilePicker } from "@/components/capture/FilePicker";
import type { CapturedMedia } from "@/components/capture/ModalityWorkspace";
import { Alert } from "@/components/ui/alert";
import { validateMedia, type MediaRules } from "@/lib/media";

type Kind = "image" | "video" | "audio";

/** Validates a file or recording and hands a CapturedMedia to the workspace, or shows why not. */
export function useMediaValidation(kind: Kind, rules: MediaRules, onMedia: (m: CapturedMedia) => void) {
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function accept(blob: Blob, origin: CapturedMedia["origin"], name: string) {
    setError(null);
    setChecking(true);
    try {
      const info = await validateMedia(blob, name, kind, rules);
      onMedia({ blob, url: URL.createObjectURL(blob), origin, name, info });
    } catch (err) {
      setError(err instanceof Error ? err.message : "The file could not be read.");
    } finally {
      setChecking(false);
    }
  }

  const status: ReactNode = (
    <>
      {checking && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Checking file…
        </p>
      )}
      {error && <Alert variant="destructive">{error}</Alert>}
    </>
  );
  return { accept, status, checking };
}

export function UploadTab({
  kind,
  rules,
  label,
  onMedia,
}: {
  kind: Kind;
  rules: MediaRules;
  label: string;
  onMedia: (m: CapturedMedia) => void;
}) {
  const { accept, status, checking } = useMediaValidation(kind, rules, onMedia);
  return (
    <div className="space-y-3">
      <FilePicker rules={rules} label={label} disabled={checking} onFile={(f) => accept(f, "upload", f.name)} />
      {status}
    </div>
  );
}
