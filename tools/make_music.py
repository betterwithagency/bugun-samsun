"""Compose the Reels background music from scratch (no samples, so no licence or Content ID issues).

A calm, warm news bed: 88 BPM, D major, one chord per bar (D add9 · Bm7 · Gmaj7 · A, twice),
soft pad, electric-piano arpeggio, round bass and a light pulse from bar 3. Deterministic (fixed seed).

  .venv/bin/pip install numpy && .venv/bin/python tools/make_music.py
  → assets/audio/haber-fon.m4a (24 s; the Reels trims it to the video and fades it out)

Needs numpy and ffmpeg locally; the bulletin workflow only uses the finished .m4a.
"""
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48000
BPM = 88
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 8
LENGTH = BARS * BAR + 2.5  # tail for the reverb
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio" / "haber-fon.m4a"
rng = np.random.default_rng(20261120)


def hz(note: str) -> float:
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[name] + 12 * (octave + 1) - 69) / 12)


# one chord per bar: (bass, pad voicing, arpeggio notes)
CHORDS = [
    ("D2", ["D3", "A3", "E4", "F#4"], ["D4", "A4", "E5", "F#5", "A5", "F#5", "E5", "A4"]),     # D add9
    ("B1", ["B2", "F#3", "D4", "A4"], ["B3", "F#4", "A4", "D5", "F#5", "D5", "A4", "F#4"]),    # Bm7
    ("G1", ["G2", "D3", "B3", "F#4"], ["G3", "D4", "F#4", "B4", "D5", "B4", "F#4", "D4"]),     # Gmaj7
    ("A1", ["A2", "E3", "C#4", "E4"], ["A3", "E4", "D5", "E5", "A5", "E5", "C#5", "E4"]),    # A (D5 → C#5 in the melody)
]
N = int(LENGTH * SR)
t_all = np.arange(N) / SR


def env_adsr(n, a, r, sustain_len):
    """Linear attack, flat sustain, exponential-ish release (seconds)."""
    t = np.arange(n) / SR
    e = np.clip(t / a, 0, 1)
    rel = np.clip((t - sustain_len) / r, 0, 1)
    return e * (1 - rel) ** 2


def add(buf, start, sig):
    i = int(start * SR)
    j = min(N, i + sig.shape[1])
    if j > i:
        buf[:, i:j] += sig[:, : j - i]


def pad(freqs, dur):
    n = int((dur + 1.6) * SR)
    t = np.arange(n) / SR
    left = np.zeros(n)
    right = np.zeros(n)
    for f in freqs:
        vib = 1 + 0.0015 * np.sin(2 * np.pi * 4.6 * t + rng.uniform(0, 6))
        for cents, side in ((-5, "L"), (5, "R")):
            ff = f * 2 ** (cents / 1200)
            ph = 2 * np.pi * ff * np.cumsum(vib) / SR
            tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
            if side == "L":
                left += tone
            else:
                right += tone
    e = env_adsr(n, 0.9, 1.6, dur)
    return np.vstack([left * e, right * e]) / len(freqs)


def epiano(f, vel, pan):
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.25)
            + 0.32 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.45)
            + 0.10 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.22)
            + 0.04 * np.sin(2 * np.pi * 7.02 * f * t) * np.exp(-t / 0.05))  # soft tine at the strike
    tone *= np.clip(t / 0.004, 0, 1) * (1 + 0.06 * np.sin(2 * np.pi * 5.2 * t))
    tone *= vel
    return np.vstack([tone * (1 - pan), tone * (1 + pan)]) * 0.5


def bass(f, dur):
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t)  # the octave keeps it audible on phones
    tone = np.tanh(1.6 * tone) * np.exp(-t / 1.4) * np.clip(t / 0.01, 0, 1) * env_adsr(n, 0.01, 0.5, dur)
    return np.vstack([tone, tone])


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 46 + 70 * np.exp(-t / 0.035)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)
    return np.vstack([tone, tone])


def shaker():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(6) / 6, mode="same")  # keep the hiss, drop the rumble
    tone = noise * np.exp(-t / 0.025) * np.clip(t / 0.006, 0, 1)
    return np.vstack([tone * 0.8, tone])


def reverb(x, seconds=2.2, mix=0.28):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / (seconds / 6.5))
        ir = np.convolve(ir, np.ones(24) / 24, mode="same")  # darker tail
        ir[: int(0.012 * SR)] = 0  # pre-delay
        ir /= np.sqrt(np.sum(ir ** 2))
        size = 1 << int(np.ceil(np.log2(len(x[ch]) + n)))
        wet = np.fft.irfft(np.fft.rfft(x[ch], size) * np.fft.rfft(ir, size), size)[: x.shape[1]]
        out[ch] = (1 - mix) * x[ch] + mix * wet
    return out


def compose() -> np.ndarray:
    music = np.zeros((2, N))
    bus_pad = np.zeros((2, N))
    bus_keys = np.zeros((2, N))
    bus_low = np.zeros((2, N))
    bus_perc = np.zeros((2, N))
    for b in range(BARS):
        root, voicing, arp = CHORDS[b % 4]
        start = b * BAR
        add(bus_pad, start, pad([hz(n) for n in voicing], BAR))
        add(bus_low, start, bass(hz(root), 2 * BEAT))
        add(bus_low, start + 2 * BEAT, bass(hz(root), 2 * BEAT) * 0.8)
        for k, note in enumerate(arp):
            if b == 0 and k < 2:
                continue  # let the first chord breathe
            vel = (0.95 if k % 2 == 0 else 0.7) * rng.uniform(0.85, 1.0)
            add(bus_keys, start + k * BEAT / 2 + rng.uniform(0, 0.008), epiano(hz(note), vel, 0.35 if k % 2 else -0.35))
        if b >= 2:
            for beat in (0, 2):
                add(bus_perc, start + beat * BEAT, kick() * 0.55)
            for k in range(8):
                add(bus_perc, start + k * BEAT / 2 + BEAT / 4, shaker() * (0.11 if k % 2 else 0.07))
    music += 0.50 * bus_pad + 0.50 * bus_keys + 0.30 * bus_low + 0.50 * bus_perc
    music = reverb(music)
    fade = np.clip(t_all / 0.5, 0, 1) * np.clip((LENGTH - t_all) / 2.0, 0, 1)
    music *= fade
    music = np.tanh(1.2 * music / np.max(np.abs(music))) / np.tanh(1.2)
    return music


TARGET_LUFS = -18.0


def loudness(path) -> float:
    """Integrated loudness (EBU R128) measured by ffmpeg."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    return float(summary.split("I:")[1].split("LUFS")[0])


def main() -> int:
    music = compose()
    pcm = (np.clip(music.T, -1, 1) * 32000).astype("<i2")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "fon.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        gain = TARGET_LUFS - loudness(wav)  # a calm bed: a little under the usual -14/-16 of Reels music
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav),
                        "-af", f"volume={gain:.1f}dB,alimiter=limit=0.8:level=false", "-ar", str(SR),
                        "-c:a", "aac", "-b:a", "192k", str(OUT)], check=True)
    print(f"loudness {loudness(OUT):.1f} LUFS (target {TARGET_LUFS})")
    print(f"{OUT} ({OUT.stat().st_size / 1e3:.0f} kB, {LENGTH:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
