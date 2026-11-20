"""Acoustic measurements from a 16 kHz mono 16-bit PCM WAV, using NumPy only.

The audio is decoded from bytes in memory and never written to disk.
"""

import io
import wave

import numpy as np

from app.analysis.common import ExtractionResult, FeatureError, clamp01, clean

EXTRACTOR_VERSION = "voice/1.0.0+numpy-yin-mfcc@16kHz-mono-pcm16"

SAMPLE_RATE = 16_000
MIN_SECONDS = 3.0
MAX_SECONDS = 60.0
MAX_BYTES = 4 * 1024 * 1024  # 60 s of 16-bit 16 kHz mono is ~1.9 MB

FRAME = 400  # 25 ms
HOP = 160  # 10 ms
F0_MIN, F0_MAX = 60.0, 400.0
YIN_THRESHOLD = 0.15
N_MELS, N_MFCC = 26, 13

# Engineering quality gates for this prototype (not validated reference values).
MIN_SNR_DB = 10.0
MAX_CLIPPING = 0.01
MIN_VOICED_SECONDS = 1.0


def decode_wav(data: bytes) -> np.ndarray:
    if len(data) > MAX_BYTES:
        raise FeatureError(f"Audio is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise FeatureError("Audio must be a WAV (RIFF/WAVE) file.")
    try:
        with wave.open(io.BytesIO(data)) as w:
            channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as exc:
        raise FeatureError(f"The WAV file could not be read ({exc}).") from None
    if channels != 1 or width != 2 or rate != SAMPLE_RATE:
        raise FeatureError(
            f"Audio must be 16-bit mono PCM at {SAMPLE_RATE} Hz "
            f"(got {channels} channel(s), {width * 8}-bit, {rate} Hz)."
        )
    if len(frames) % 2:
        frames = frames[:-1]
    return np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0


def frame_signal(x: np.ndarray, frame: int, hop: int) -> np.ndarray:
    n = 1 + max(0, (len(x) - frame) // hop)
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, length) of consecutive True runs."""
    padded = np.concatenate([[False], mask, [False]]).astype(np.int8)
    diff = np.diff(padded)
    starts, ends = np.flatnonzero(diff == 1), np.flatnonzero(diff == -1)
    return [(int(s), int(e - s)) for s, e in zip(starts, ends)]


def yin_f0(x: np.ndarray, sr: int = SAMPLE_RATE, hop: int = HOP) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame F0 in Hz (NaN when unvoiced) and frame RMS, following de Cheveigné & Kawahara (2002)."""
    tau_min, tau_max = int(sr / F0_MAX), int(sr / F0_MIN)
    window = 512
    length = window + tau_max + 1
    if len(x) < length:
        return np.full(0, np.nan), np.zeros(0)
    frames = frame_signal(x, length, hop)
    n_fft = 1 << int(np.ceil(np.log2(length + window)))
    # r[tau] = sum_{j<W} x[j] * x[j + tau]
    r = np.fft.irfft(np.fft.rfft(frames, n_fft) * np.conj(np.fft.rfft(frames[:, :window], n_fft)), n_fft)
    r = r[:, : tau_max + 1]
    cs = np.concatenate([np.zeros((len(frames), 1)), np.cumsum(frames**2, axis=1)], axis=1)
    taus = np.arange(tau_max + 1)
    energy_0 = cs[:, window]
    energy_tau = cs[:, taus + window] - cs[:, taus]
    diff = energy_0[:, None] + energy_tau - 2 * r
    diff[:, 0] = 0
    cmnd = np.ones_like(diff)
    running = np.cumsum(diff[:, 1:], axis=1)
    cmnd[:, 1:] = diff[:, 1:] * taus[1:] / np.maximum(running, 1e-12)

    f0 = np.full(len(frames), np.nan)
    below = cmnd[:, tau_min:tau_max] < YIN_THRESHOLD
    for i in np.flatnonzero(below.any(axis=1)):
        t = int(np.argmax(below[i])) + tau_min
        while t + 1 < tau_max and cmnd[i, t + 1] < cmnd[i, t]:
            t += 1
        a, b, c = cmnd[i, t - 1], cmnd[i, t], cmnd[i, t + 1]
        denom = a - 2 * b + c
        shift = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
        f0[i] = sr / (t + float(np.clip(shift, -1, 1)))
    rms = np.sqrt(np.mean(frames[:, :window] ** 2, axis=1))
    return f0, rms


def _mel_filterbank(sr: int, n_fft: int, n_mels: int) -> np.ndarray:
    def hz_to_mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def mel_to_hz(m):
        return 700.0 * (10 ** (m / 2595.0) - 1.0)

    mel_points = np.linspace(hz_to_mel(0.0), hz_to_mel(sr / 2), n_mels + 2)
    bins = np.floor((n_fft + 1) * mel_to_hz(mel_points) / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        left, centre, right = bins[m - 1], bins[m], bins[m + 1]
        if centre > left:
            fb[m - 1, left:centre] = (np.arange(left, centre) - left) / (centre - left)
        if right > centre:
            fb[m - 1, centre:right] = (right - np.arange(centre, right)) / (right - centre)
    return fb


def _dct_matrix(n_out: int, n_in: int) -> np.ndarray:
    k = np.arange(n_out)[:, None]
    n = np.arange(n_in)[None, :]
    m = np.cos(np.pi * k * (2 * n + 1) / (2 * n_in)) * np.sqrt(2.0 / n_in)
    m[0] /= np.sqrt(2.0)
    return m


def extract_voice_features(x: np.ndarray, sr: int = SAMPLE_RATE) -> ExtractionResult:
    duration = len(x) / sr
    if duration < MIN_SECONDS:
        raise FeatureError(f"Recording is too short ({duration:.1f} s; at least {MIN_SECONDS:.0f} s needed).")
    if duration > MAX_SECONDS + 0.5:
        raise FeatureError(f"Recording is too long ({duration:.0f} s; at most {MAX_SECONDS:.0f} s).")
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak < 1e-3:
        raise FeatureError("The recording is silent. Check that the microphone is not muted.")

    warnings: list[str] = []
    clipping = float(np.mean(np.abs(x) >= 0.999))
    frames = frame_signal(x, FRAME, HOP)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    db = 20 * np.log10(rms + 1e-10)
    noise_db, loud_db = np.percentile(db, 10), np.percentile(db, 90)
    level_dbfs = 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-10)

    dynamic = loud_db - noise_db
    if dynamic >= 6.0:
        threshold = noise_db + 0.35 * dynamic
        snr = float(dynamic)
    else:
        # No distinguishable quiet frames: treat everything above -50 dBFS as active.
        threshold = -50.0
        snr = None
        warnings.append("No quiet background frames were found, so signal-to-noise and pauses cannot be estimated.")
    active = db > threshold
    if not active.any():
        raise FeatureError("No sound above the background level was detected.")

    pauses = [length for start, length in _runs(~active)
              if start > 0 and start + length < len(active) and length >= 25]
    segments = [r for r in _runs(active) if r[1] >= 10]

    f0, f0_rms = yin_f0(x, sr)
    f0_active = 20 * np.log10(f0_rms + 1e-10) > threshold
    voiced = f0[f0_active & ~np.isnan(f0)]
    voiced_seconds = len(voiced) * HOP / sr
    features: dict = {
        "duration_s": clean(duration, 2),
        "level_dbfs": clean(level_dbfs, 1),
        "snr_db_estimate": clean(snr, 1),
        "clipping_fraction": clean(clipping, 5),
        "active_fraction": clean(active.mean(), 3),
        "pause_count": len(pauses),
        "mean_pause_s": clean(np.mean(pauses) * HOP / sr, 2) if pauses else None,
        "active_segments_per_min": clean(len(segments) / duration * 60, 1),
        "voiced_fraction": clean(len(voiced) / max(1, int(f0_active.sum())), 3),
    }
    if len(voiced) >= 50:
        median = float(np.median(voiced))
        semis = 12 * np.log2(voiced / median)
        p5, p95 = np.percentile(voiced, [5, 95])
        features.update(
            f0_median_hz=clean(median, 1),
            f0_mean_hz=clean(np.mean(voiced), 1),
            f0_std_hz=clean(np.std(voiced), 2),
            f0_std_semitones=clean(np.std(semis), 3),
            f0_range_semitones=clean(12 * np.log2(p95 / p5), 2),
        )
    else:
        features.update(f0_median_hz=None, f0_mean_hz=None, f0_std_hz=None, f0_std_semitones=None, f0_range_semitones=None)
        warnings.append("Too little voiced speech (under 0.5 s) to measure pitch.")

    # Spectral features and MFCC on active frames.
    n_fft = 512
    active_frames = frames[active] * np.hanning(FRAME)
    power = np.abs(np.fft.rfft(active_frames, n_fft)) ** 2 + 1e-12
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    total = power.sum(axis=1)
    centroid = (power * freqs).sum(axis=1) / total
    bandwidth = np.sqrt((power * (freqs[None, :] - centroid[:, None]) ** 2).sum(axis=1) / total)
    rolloff = freqs[np.argmax(np.cumsum(power, axis=1) >= 0.85 * total[:, None], axis=1)]
    flatness = np.exp(np.mean(np.log(power), axis=1)) / np.mean(power, axis=1)
    signs = np.signbit(frames[active])
    zcr = np.mean(signs[:, 1:] != signs[:, :-1], axis=1)
    mel = np.log(power @ _mel_filterbank(sr, n_fft, N_MELS).T + 1e-10)
    mfcc = mel @ _dct_matrix(N_MFCC, N_MELS).T
    features.update(
        spectral_centroid_hz=clean(centroid.mean(), 1),
        spectral_bandwidth_hz=clean(bandwidth.mean(), 1),
        spectral_rolloff_hz=clean(rolloff.mean(), 1),
        spectral_flatness=clean(flatness.mean(), 4),
        zero_crossing_rate=clean(zcr.mean(), 4),
        mfcc_mean=[clean(v, 3) for v in mfcc.mean(axis=0)],
    )

    if clipping > MAX_CLIPPING:
        warnings.append(f"{clipping:.1%} of samples are clipped; move further from the microphone or lower the gain.")
    if snr is not None and snr < MIN_SNR_DB:
        warnings.append(f"Background noise is high (SNR estimate {snr:.0f} dB); record in a quieter room.")
    if voiced_seconds < MIN_VOICED_SECONDS:
        warnings.append("Less than 1 s of voiced speech was found.")

    snr_part = clamp01((snr - 5) / 20) if snr is not None else 0.5
    quality = (snr_part + (1 - clamp01(clipping * 20)) + clamp01(voiced_seconds / 3)) / 3
    reliable = snr is not None and snr >= MIN_SNR_DB and clipping <= MAX_CLIPPING and voiced_seconds >= MIN_VOICED_SECONDS
    return ExtractionResult(features=features, warnings=warnings, quality_score=round(quality, 3), is_reliable=reliable)
