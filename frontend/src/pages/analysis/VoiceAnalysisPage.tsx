import { Mic, Upload } from "lucide-react";
import { MediaRecorderPanel } from "@/components/capture/MediaRecorderPanel";
import { ModalityWorkspace, type AnalyzeFn, type CapturedMedia } from "@/components/capture/ModalityWorkspace";
import { UploadTab, useMediaValidation } from "@/components/capture/ValidatedInput";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toWav16kMono } from "@/lib/audio";
import { AUDIO_RULES } from "@/lib/media";
import type { VoiceMeasurement } from "@/lib/types";

const analyzeVoice: AnalyzeFn = async (media, sessionId, progress) => {
  progress("Converting to 16 kHz WAV…");
  const wav = await toWav16kMono(media.blob);
  progress("Uploading and measuring…");
  return api.analyzeVoice(sessionId, wav, media.origin === "upload" ? "upload" : "microphone");
};

function RecordTab({ onMedia }: { onMedia: (m: CapturedMedia) => void }) {
  const { accept, status, checking } = useMediaValidation("audio", AUDIO_RULES, onMedia);
  return (
    <div className="space-y-3">
      <MediaRecorderPanel
        kind="audio"
        minSeconds={AUDIO_RULES.minSeconds!}
        maxSeconds={AUDIO_RULES.maxSeconds!}
        disabled={checking}
        onRecorded={(blob) => accept(blob, "microphone", "voice.webm")}
      />
      <p className="text-xs text-muted-foreground">
        Suggested prompt: read a short neutral passage aloud at a normal pace in a quiet room.
      </p>
      {status}
    </div>
  );
}

export function VoiceAnalysisPage() {
  return (
    <ModalityWorkspace
      modality="voice"
      title="Voice analysis"
      description="Record or upload a short speech sample. The server measures pitch, loudness, spectral and timing features after checking silence, noise and clipping."
      tabs={[
        { id: "record", label: "Microphone", icon: <Mic />, render: (onMedia) => <RecordTab onMedia={onMedia} /> },
        {
          id: "upload",
          label: "Upload audio",
          icon: <Upload />,
          render: (onMedia) => <UploadTab kind="audio" rules={AUDIO_RULES} label="Choose an audio file" onMedia={onMedia} />,
        },
      ]}
      dataFlow={
        <>
          <strong>This recording IS sent to the server</strong> when you press Analyse, after you confirm it. It is
          converted to 16 kHz mono WAV in the browser, measured in server memory and discarded. The audio is never
          written to disk, stored in the database or logged; only the numeric measurements are saved.
        </>
      }
      uploadConfirmation="I confirm the participant agreed to this recording being sent to the VisoNarc server for measurement. It will be processed in memory and not stored."
      renderPreview={(m) => <audio src={m.url} controls className="w-full" aria-label="Recorded voice sample" />}
      measurementsOf={(s) => s.voice_measurements}
      renderMeasurement={(m) => {
        const v = m as VoiceMeasurement;
        return v.snr_db !== null ? <Badge variant="neutral">SNR ≈ {v.snr_db.toFixed(0)} dB</Badge> : null;
      }}
      onAnalyze={analyzeVoice}
    />
  );
}
