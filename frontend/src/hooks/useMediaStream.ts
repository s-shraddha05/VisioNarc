import { useCallback, useEffect, useRef, useState } from "react";
import { mediaErrorMessage, mediaSupported } from "@/lib/media";

/** Start/stop a camera or microphone stream; always releases the device on unmount. */
export function useMediaStream(constraints: MediaStreamConstraints) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const constraintsRef = useRef(constraints);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setStream(null);
  }, []);

  const start = useCallback(async () => {
    if (!mediaSupported()) {
      setError("This browser does not support camera/microphone capture.");
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const s = await navigator.mediaDevices.getUserMedia(constraintsRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = s;
      setStream(s);
      // If the user unplugs the device or revokes permission mid-stream.
      s.getTracks().forEach((t) =>
        t.addEventListener("ended", () => {
          if (streamRef.current === s) {
            setError("The device stopped sending data (disconnected or permission revoked).");
            stop();
          }
        }),
      );
    } catch (err) {
      setError(mediaErrorMessage(err));
    } finally {
      setStarting(false);
    }
  }, [stop]);

  useEffect(() => stop, [stop]);

  return { stream, error, starting, start, stop };
}
