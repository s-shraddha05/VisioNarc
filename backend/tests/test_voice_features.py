"""Voice extractor tests with synthetic signals (test fixtures, not training data)."""

import io
import wave

import numpy as np
import pytest

from app.analysis.common import FeatureError
from app.analysis.voice import SAMPLE_RATE, decode_wav, extract_voice_features

SR = SAMPLE_RATE
rng = np.random.default_rng(0)


def tone(freq, seconds, amp=0.3):
    t = np.arange(int(SR * seconds)) / SR
    # A few harmonics so it resembles a voiced sound rather than a pure sine.
    return amp * (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(4 * np.pi * freq * t) + 0.2 * np.sin(6 * np.pi * freq * t))


def noise(seconds, amp=0.002):
    return amp * rng.standard_normal(int(SR * seconds))


def speechlike(freq=220.0):
    """Tone bursts separated by quiet gaps: 0.5 s quiet, 1.5 s tone, 0.6 s quiet, 1.5 s tone, 0.5 s quiet."""
    parts = [noise(0.5), tone(freq, 1.5) + noise(1.5), noise(0.6), tone(freq, 1.5) + noise(1.5), noise(0.5)]
    return np.concatenate(parts)


def to_wav(x, rate=SR, channels=1, width=2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
        if channels == 2:
            pcm = np.repeat(pcm, 2)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


@pytest.mark.parametrize("freq", [110.0, 220.0, 330.0])
def test_pitch_matches_tone_frequency(freq):
    result = extract_voice_features(decode_wav(to_wav(speechlike(freq))))
    assert result.features["f0_median_hz"] == pytest.approx(freq, rel=0.02)
    assert result.features["f0_std_semitones"] < 0.2


def test_pauses_activity_and_quality():
    result = extract_voice_features(decode_wav(to_wav(speechlike())))
    f = result.features
    assert f["pause_count"] == 1  # only the 0.6 s gap is *between* active sound
    assert f["mean_pause_s"] == pytest.approx(0.6, abs=0.06)
    assert 0.6 < f["active_fraction"] < 0.8
    assert f["snr_db_estimate"] > 20
    assert f["clipping_fraction"] == 0
    assert len(f["mfcc_mean"]) == 13
    assert 0 < f["spectral_flatness"] < 0.5
    assert result.is_reliable
    assert 0.8 <= result.quality_score <= 1


def test_clipping_and_noise_are_flagged():
    clipped = np.clip(speechlike() * 6, -1, 1)
    result = extract_voice_features(decode_wav(to_wav(clipped)))
    assert result.features["clipping_fraction"] > 0.01
    assert not result.is_reliable
    assert any("clipped" in w for w in result.warnings)


def test_continuous_noise_has_no_pitch_or_snr():
    result = extract_voice_features(decode_wav(to_wav(noise(4, amp=0.2))))
    assert result.features["f0_median_hz"] is None
    assert result.features["snr_db_estimate"] is None
    assert not result.is_reliable
    assert result.warnings


def test_silence_too_short_and_too_long_rejected():
    with pytest.raises(FeatureError, match="silent"):
        extract_voice_features(decode_wav(to_wav(np.zeros(SR * 4))))
    with pytest.raises(FeatureError, match="too short"):
        extract_voice_features(decode_wav(to_wav(tone(200, 1))))
    with pytest.raises(FeatureError, match="too long"):
        extract_voice_features(np.full(SR * 62, 0.1))


@pytest.mark.parametrize(
    "data, message",
    [
        (b"not a wav file at all, definitely not" * 3, "WAV"),
        (to_wav(tone(200, 4), rate=44100), "44100 Hz"),
        (to_wav(tone(200, 4), channels=2), "mono"),
        (b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 40, "could not be read"),
    ],
    ids=["not-wav", "44khz", "stereo", "corrupt-header"],
)
def test_bad_wav_rejected(data, message):
    with pytest.raises(FeatureError, match=message):
        decode_wav(data)


def test_oversized_rejected():
    with pytest.raises(FeatureError, match="larger"):
        decode_wav(b"RIFF" + b"\x00" * (5 * 1024 * 1024))
