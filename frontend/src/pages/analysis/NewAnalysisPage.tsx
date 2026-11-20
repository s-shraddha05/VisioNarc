import { Activity, AudioLines, CheckCircle2, Loader2, ScanFace, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { ResearchNotice } from "@/components/common/Notices";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox, FieldError, Textarea } from "@/components/ui/form-controls";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, errorMessage } from "@/lib/api";
import { CONSENT_POINTS, CONSENT_VERSION } from "@/lib/consent";
import { cn } from "@/lib/utils";

const MODALITIES = [
  { key: "allow_face", label: "Face", icon: ScanFace, detail: "A still photo for facial-appearance features" },
  { key: "allow_motion", label: "Motion", icon: Activity, detail: "A short video for body-pose movement features" },
  { key: "allow_voice", label: "Voice", icon: AudioLines, detail: "A short speech recording for acoustic features" },
] as const;

type ModalityKey = (typeof MODALITIES)[number]["key"];

export function NewAnalysisPage() {
  useDocumentTitle("New analysis");
  const navigate = useNavigate();
  const settings = useApi(api.settings, []);

  const [subject, setSubject] = useState("");
  const [notes, setNotes] = useState("");
  const [consentBy, setConsentBy] = useState("");
  const [modalities, setModalities] = useState<Record<ModalityKey, boolean>>({
    allow_face: false,
    allow_motion: false,
    allow_voice: false,
  });
  const [rawMedia, setRawMedia] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const anyModality = Object.values(modalities).some(Boolean);
  const errors = {
    subject: !subject.trim() ? "Enter a pseudonymous subject label." : null,
    consentBy: !consentBy.trim() ? "Enter who gave consent (initials or participant code)." : null,
    modality: !anyModality ? "Select at least one modality the subject agreed to." : null,
    agreed: !agreed ? "Consent must be confirmed before a session can be created." : null,
  };
  const valid = !Object.values(errors).some(Boolean);
  const rawAllowedByServer = settings.data?.store_raw_media ?? false;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!valid) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createSession({
        subject_label: subject.trim(),
        notes: notes.trim() || null,
        consent: {
          consent_given: true,
          consented_by_label: consentBy.trim(),
          ...modalities,
          allow_raw_media_storage: rawAllowedByServer && rawMedia,
        },
      });
      navigate(`/history/${created.id}`, { state: { created: true } });
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  const show = (msg: string | null) => (touched ? msg : null);

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      <PageHeader
        eyebrow="Analysis"
        title="New analysis & consent"
        description="Create an analysis session for one participant and record their informed consent. Captures can only be made for the modalities consented to."
      />
      <ResearchNotice />

      {error && <Alert variant="destructive">{error}</Alert>}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Participant</CardTitle>
              <CardDescription>Use a pseudonym or participant code — never a real name.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subject">Subject label *</Label>
                <Input
                  id="subject"
                  placeholder="e.g. Participant 07"
                  maxLength={100}
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  aria-invalid={!!show(errors.subject)}
                  aria-describedby="subject-error"
                />
                <FieldError id="subject-error">{show(errors.subject)}</FieldError>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notes (optional)</Label>
                <Textarea
                  id="notes"
                  maxLength={2000}
                  placeholder="Study context, device used… Avoid identifying or health information."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                <p className="text-right text-xs text-muted-foreground">{notes.length}/2000</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Modalities consented to *</CardTitle>
              <CardDescription>Only selected modalities can be captured for this session.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <fieldset className="grid gap-3 sm:grid-cols-3" aria-describedby="modality-error">
                <legend className="sr-only">Modalities</legend>
                {MODALITIES.map((m) => (
                  <label
                    key={m.key}
                    className={cn(
                      "flex cursor-pointer flex-col gap-2 rounded-xl border p-4 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                      modalities[m.key] ? "border-primary bg-primary/5" : "hover:bg-muted/50",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <m.icon className="size-5 text-primary" />
                      <Checkbox
                        aria-label={`${m.label}: ${m.detail}`}
                        checked={modalities[m.key]}
                        onChange={(e) => setModalities((v) => ({ ...v, [m.key]: e.target.checked }))}
                      />
                    </div>
                    <span className="font-medium">{m.label}</span>
                    <span className="text-xs text-muted-foreground">{m.detail}</span>
                  </label>
                ))}
              </fieldset>
              <FieldError id="modality-error">{show(errors.modality)}</FieldError>
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit xl:sticky xl:top-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-5 text-primary" /> Informed consent
            </CardTitle>
            <CardDescription>Consent text version {CONSENT_VERSION}. Read this to the participant.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <ul className="space-y-2.5 text-sm">
              {CONSENT_POINTS.map((p) => (
                <li key={p} className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>

            <div className="space-y-2">
              <Label htmlFor="consent-by">Consent given by *</Label>
              <Input
                id="consent-by"
                placeholder="Participant initials or code"
                maxLength={100}
                value={consentBy}
                onChange={(e) => setConsentBy(e.target.value)}
                aria-invalid={!!show(errors.consentBy)}
                aria-describedby="consent-by-error"
              />
              <FieldError id="consent-by-error">{show(errors.consentBy)}</FieldError>
            </div>

            <label className={cn("flex items-start gap-3 text-sm", !rawAllowedByServer && "opacity-60")}>
              <Checkbox
                className="mt-0.5"
                checked={rawAllowedByServer && rawMedia}
                disabled={!rawAllowedByServer}
                onChange={(e) => setRawMedia(e.target.checked)}
              />
              <span>
                Participant also agrees to raw media (photo/video/audio) being stored.
                {!rawAllowedByServer && (
                  <span className="block text-xs text-muted-foreground">
                    Disabled: this server is configured not to store raw media (STORE_RAW_MEDIA=false).
                  </span>
                )}
              </span>
            </label>

            <label className="flex items-start gap-3 rounded-lg border bg-muted/40 p-3 text-sm">
              <Checkbox
                className="mt-0.5"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                aria-describedby="agreed-error"
              />
              <span>
                I confirm the participant was given the information above and voluntarily agreed to the selected modalities.
              </span>
            </label>
            <FieldError id="agreed-error">{show(errors.agreed)}</FieldError>

            <Button type="submit" size="lg" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" />}
              {submitting ? "Creating session…" : "Create session"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </form>
  );
}
