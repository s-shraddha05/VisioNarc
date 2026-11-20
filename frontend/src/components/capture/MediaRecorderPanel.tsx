import { CircleStop, Loader2, Mic, MicOff, Video, VideoOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useMediaStream } from "@/hooks/useMediaStream";
import { formatSeconds } from "@/lib/format";
import { pickRecorderMime, recorderSupported } from "@/lib/media";

/** Record video (camera) or audio (microphone) in the browser, up to maxSeconds. */
export function MediaRecorderPanel({
  kind,
  minSeconds,
  maxSeconds,
  disabled,
  onRecorded,
}: {
  kind: "video" | "audio";
  minSeconds: number;
  maxSeconds: number;
  disabled?: boolean;
  onRecorded: (blob: Blob, seconds: number) => void;
}) {
  const { stream, error, starting, start, stop } = useMediaStream(
    kind === "video"
      ? { video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false }
      : { audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }, video: false },
  );
  const videoRef = useRef<HTMLVideoElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAt = useRef(0);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [level, setLevel] = useState(0);
  const [recError, setRecError] = useState<string | null>(null);

  useEffect(() => {
    if (videoRef.current) videoRef.current.srcObject = stream;
  }, [stream]);

  // Live input level from the actual microphone signal (audio only).
  useEffect(() => {
    if (kind !== "audio" || !stream) return;
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const data = new Float32Array(analyser.fftSize);
    let raf = 0;
    const tick = () => {
      analyser.getFloatTimeDomainData(data);
      let sum = 0;
      for (const v of data) sum += v * v;
      setLevel(Math.min(1, Math.sqrt(sum / data.length) * 4));
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => {
      cancelAnimationFrame(raf);
      void ctx.close();
    };
  }, [kind, stream]);

  useEffect(() => {
    if (!recording) return;
    const id = window.setInterval(() => {
      const secs = (performance.now() - startedAt.current) / 1000;
      setElapsed(secs);
      if (secs >= maxSeconds) recorderRef.current?.stop();
    }, 200);
    return () => window.clearInterval(id);
  }, [recording, maxSeconds]);

  function begin() {
    if (!stream) return;
    setRecError(null);
    const mimeType = pickRecorderMime(kind);
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
    recorder.onstop = () => {
      setRecording(false);
      const seconds = (performance.now() - startedAt.current) / 1000;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || `${kind}/webm` });
      if (seconds < minSeconds) {
        setRecError(`Recording was ${seconds.toFixed(1)} s; at least ${minSeconds} s is needed.`);
        return;
      }
      stop();
      onRecorded(blob, seconds);
    };
    recorder.onerror = () => setRecError("Recording failed. Try again or upload a file instead.");
    recorderRef.current = recorder;
    startedAt.current = performance.now();
    setElapsed(0);
    recorder.start(250);
    setRecording(true);
  }

  if (!recorderSupported()) {
    return <Alert variant="warning">This browser cannot record media. Upload a file instead.</Alert>;
  }

  const OnIcon = kind === "video" ? Video : Mic;
  const OffIcon = kind === "video" ? VideoOff : MicOff;

  return (
    <div className="space-y-3">
      {kind === "video" ? (
        <div className="relative aspect-video overflow-hidden rounded-xl border bg-[oklch(0.2_0.02_250)]">
          <video ref={videoRef} autoPlay playsInline muted className={stream ? "size-full object-cover" : "hidden"} aria-label="Live camera preview" />
          {!stream && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-white/70">
              <OffIcon className="size-6" /> Camera is off
            </div>
          )}
          {recording && <RecordingBadge elapsed={elapsed} max={maxSeconds} />}
        </div>
      ) : (
        <div className="relative flex h-28 items-center gap-4 rounded-xl border bg-muted/40 px-5">
          <span className={`flex size-12 items-center justify-center rounded-full ${stream ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"}`}>
            {stream ? <Mic className="size-5" /> : <MicOff className="size-5" />}
          </span>
          <div className="flex-1 space-y-2">
            <p className="text-sm font-medium">{stream ? (recording ? "Recording…" : "Microphone ready") : "Microphone is off"}</p>
            <div className="h-2 overflow-hidden rounded-full bg-muted" role="meter" aria-label="Input level" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(level * 100)}>
              <div className="h-full rounded-full bg-primary transition-[width] duration-75" style={{ width: `${level * 100}%` }} />
            </div>
          </div>
          {recording && <RecordingBadge elapsed={elapsed} max={maxSeconds} />}
        </div>
      )}

      {(error || recError) && <Alert variant="destructive">{error || recError}</Alert>}

      <div className="flex flex-wrap gap-2">
        {!stream ? (
          <Button onClick={start} disabled={disabled || starting}>
            {starting ? <Loader2 className="animate-spin" /> : <OnIcon />} Start {kind === "video" ? "camera" : "microphone"}
          </Button>
        ) : recording ? (
          <Button variant="destructive" onClick={() => recorderRef.current?.stop()}>
            <CircleStop /> Stop recording
          </Button>
        ) : (
          <>
            <Button onClick={begin} disabled={disabled}>
              <span className="size-2.5 rounded-full bg-current" /> Start recording
            </Button>
            <Button variant="outline" onClick={stop}>
              <OffIcon /> Turn off
            </Button>
          </>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Record {minSeconds}–{maxSeconds} seconds. Recording stops automatically at {maxSeconds} s.
      </p>
    </div>
  );
}

function RecordingBadge({ elapsed, max }: { elapsed: number; max: number }) {
  return (
    <span className="absolute right-3 top-3 inline-flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-xs font-medium tabular-nums text-white">
      <span className="size-2 animate-pulse rounded-full bg-red-500" />
      {formatSeconds(elapsed)} / {formatSeconds(max)}
    </span>
  );
}
