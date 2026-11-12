"""Reference math for the 40 Hz stimulus specification.

This module is the oracle behind the golden vectors. Firmware, TypeScript, and
the local bridge must match it. It is not a player and it does not talk to
hardware.

Two profiles:

- web_v1 reproduces the public site worker recovered from
  https://40hz-gamma-entrainment.joonaheino.com/ (November 2026 bundle).
- research_v1 is the normative profile for the new system.

Run from the repository root:

    python tools/oracle/stimulus_oracle.py check
    python tools/oracle/stimulus_oracle.py write
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "vectors"

# Paul Kellet pink-noise filter, copied from the deployed worker.
KELLET_B0 = 0.99886
KELLET_B1 = 0.99332
KELLET_B2 = 0.96900
KELLET_B3 = 0.86650
KELLET_B4 = 0.55000
KELLET_B5 = -0.7616
KELLET_B6 = 0.115926
KELLET_WHITE = 0.5362


class XorShift32:
    """uint32 xorshift. seed 0 is remapped to 1 so the state never sticks at 0."""

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF or 1

    def next_u32(self) -> int:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state

    def next_unit(self) -> float:
        """Value in [0, 1)."""
        return self.next_u32() / 4294967296.0

    def next_white(self) -> float:
        """Value in [-1, 1], matching 2 * unit - 1."""
        return 2.0 * self.next_unit() - 1.0


def period_samples(sample_rate: int, repetition_hz: float = 40.0) -> int:
    """web_v1 and research_v1 both use floor(sample_rate / repetition_hz)."""
    return int(math.floor(sample_rate / repetition_hz))


def pulse_samples(sample_rate: int, pulse_s: float = 0.001) -> int:
    return int(math.floor(pulse_s * sample_rate))


def edge_samples(sample_rate: int, pulse_len: int, edge_s: float = 150e-6) -> int:
    return min(int(math.floor(edge_s * sample_rate)), pulse_len // 4)


def sine_template(sample_rate: int, edge: str) -> list[float]:
    """One 10 kHz pulse. edge is 'hard' or 'raised_cosine_150us'."""
    count = pulse_samples(sample_rate, 0.001)
    taper = edge_samples(sample_rate, count) if edge == "raised_cosine_150us" else 0
    out: list[float] = []
    for index in range(count):
        gain = 1.0
        if taper > 0:
            if index < taper:
                gain = 0.5 * (1.0 - math.cos(math.pi * index / taper))
            elif index >= count - taper:
                gain = 0.5 * (1.0 - math.cos(math.pi * (count - 1 - index) / taper))
        t = index / sample_rate
        out.append(math.sin(2.0 * math.pi * 10000.0 * t) * gain)
    return out


def break_gain(sample_index: int, sample_rate: int, interval_s: float, duration_s: float, fade_s: float) -> float:
    """Gain applied to pulses. Break sits at the end of each interval (web_v1)."""
    if interval_s <= 0 or duration_s <= 0:
        return 1.0
    fade = min(fade_s, duration_s / 2.0)
    time_s = (sample_index / sample_rate) % interval_s
    stim_until = max(0.0, interval_s - duration_s)
    if time_s < stim_until:
        return 1.0
    into = time_s - stim_until
    if into < fade:
        return 1.0 - into / fade
    if into > duration_s - fade:
        return (into - (duration_s - fade)) / fade
    return 0.0


def session_fade_gain(sample_index: int, total_samples: int, sample_rate: int, fade_s: float = 10.0) -> float:
    """Linear session fade. First faded sample is 0. The final sample is not quite 0."""
    fade = min(int(math.floor(fade_s * sample_rate)), total_samples // 2)
    if fade <= 0:
        return 1.0
    if sample_index < fade:
        return sample_index / fade
    tail = total_samples - fade
    if sample_index >= tail:
        return 1.0 - (sample_index - tail) / fade
    return 1.0


def envelope(sample_index: int, total_samples: int, sample_rate: int, plan: dict) -> float:
    breaks = plan["breaks"]
    interval = 0.0 if not breaks["enabled"] else breaks["interval_s"]
    gain = break_gain(
        sample_index,
        sample_rate,
        interval,
        breaks["duration_s"],
        breaks["fade_s"],
    )
    return gain * session_fade_gain(sample_index, total_samples, sample_rate, plan["session_fade_s"])


def pulse_active(sample_index: int, sample_rate: int, pulse_len: int, repetition_hz: float = 40.0) -> bool:
    period = period_samples(sample_rate, repetition_hz)
    if period <= 0:
        return False
    offset = sample_index % period
    return offset < pulse_len


def light_level(sample_index: int, total_samples: int, sample_rate: int, plan: dict) -> int:
    """1 when the pin should be at its ON level before polarity is applied."""
    env = envelope(sample_index, total_samples, sample_rate, plan)
    if env < plan["light"]["threshold"]:
        return 0
    mode = plan["light"]["mode"]
    # A binaural plan has no acoustic burst. The 50% visual grid is the gate.
    if plan.get("protocol") == "binaural_beat" and mode == "audio_envelope":
        mode = "visual_50"
    period = period_samples(sample_rate, plan["repetition_hz"])
    offset_samples = int(round(plan["light"]["phase_offset_us"] * 1e-6 * sample_rate))
    shifted = sample_index - offset_samples
    if shifted < 0:
        return 0
    offset = shifted % period
    if mode == "audio_envelope":
        width = pulse_samples(sample_rate, plan["pulse_duration_s"])
        return 1 if offset < width else 0
    if mode == "visual_50":
        width = int(round(period * plan["light"]["duty"]))
        return 1 if offset < width else 0
    raise ValueError(mode)


def kellet_block(white: list[float]) -> list[float]:
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    out: list[float] = []
    for sample in white:
        b0 = KELLET_B0 * b0 + 0.0555179 * sample
        b1 = KELLET_B1 * b1 + 0.0750759 * sample
        b2 = KELLET_B2 * b2 + 0.1538520 * sample
        b3 = KELLET_B3 * b3 + 0.3104856 * sample
        b4 = KELLET_B4 * b4 + 0.5329522 * sample
        b5 = KELLET_B5 * b5 - 0.0168980 * sample
        out.append(b0 + b1 + b2 + b3 + b4 + b5 + b6 + KELLET_WHITE * sample)
        b6 = KELLET_B6 * sample
    return out


def research_plan() -> dict:
    return {
        "profile": "research_v1",
        "sample_rate": 48000,
        "protocol": "mit_sine_pulse",
        "repetition_hz": 40.0,
        "pulse_duration_s": 0.001,
        "session_fade_s": 10.0,
        "duration_s": 3600.0,
        "breaks": {
            "enabled": True,
            "interval_s": 180.0,
            "duration_s": 20.0,
            "fade_s": 2.0,
            "placement": "end",
        },
        "light": {
            "mode": "audio_envelope",
            "duty": 0.5,
            "phase_offset_us": 0.0,
            "threshold": 0.5,
            "polarity": "active_high",
        },
    }


def _round(values: list[float], places: int = 10) -> list[float]:
    return [round(value, places) for value in values]


def build_vectors() -> dict[str, dict]:
    template = sine_template(48000, "raised_cosine_150us")
    hard = sine_template(48000, "hard")
    peak = max(abs(value) for value in template)
    scale = 0.95 / peak
    rate_table = []
    for rate in (44100, 48000, 96000):
        period = period_samples(rate)
        width = pulse_samples(rate)
        achieved = rate / period
        rate_table.append(
            {
                "sample_rate": rate,
                "period_samples_floor": period,
                "achieved_hz": achieved,
                "error_ppm": (achieved - 40.0) / 40.0 * 1e6,
                "pulse_samples_floor_1ms": width,
                "pulse_width_us": width / rate * 1e6,
            }
        )
    sine = {
        "id": "MIT_SINE_WEB_COMPAT_48K_NO_NOISE_NO_BREAK",
        "description": (
            "web_v1 pulse template at 48 kHz. Raised-cosine edges, no noise, no breaks, "
            "no session fade. Normalization scale is recorded separately and is not baked "
            "into template_web_smoothed."
        ),
        "sample_rate": 48000,
        "period_samples": 1200,
        "pulse_samples": 48,
        "edge_samples": 7,
        "carrier_hz": 10000,
        "repetition_hz": 40.0,
        "template_web_smoothed": _round(template),
        "template_peak": peak,
        "template_hard_gate": _round(hard),
        "hard_gate_peak": max(abs(value) for value in hard),
        "pulse_gates_first_4": [
            {
                "pulse": index,
                "start": index * 1200,
                "end_exclusive": index * 1200 + 48,
                "high_samples": 48,
            }
            for index in range(4)
        ],
        "normalization": {
            "mode": "legacy_peak_0_95",
            "scale_applied": scale,
            "first_16_after_legacy_normalize": _round([value * scale for value in template[:16]]),
        },
        "rate_table": rate_table,
    }

    plan = research_plan()
    total = 48000 * 200
    probe_times = [0.0, 0.5, 9.999, 10.0, 159.0, 160.0, 161.0, 170.0, 178.0, 179.0, 180.0]
    envelope_rows = []
    for time_s in probe_times:
        index = int(math.floor(time_s * 48000))
        envelope_rows.append(
            {
                "time_s": time_s,
                "sample_index": index,
                "break_gain": break_gain(index, 48000, 180.0, 20.0, 2.0),
                "session_fade_gain": session_fade_gain(index, total, 48000, 10.0),
                "envelope": envelope(index, total, 48000, plan),
                "light_audio_envelope": light_level(index, total, 48000, plan),
            }
        )
    # A sample inside the second pulse, still in the fade-in, must stay dark at threshold 0.5.
    second_pulse = 1200
    envelope_rows.append(
        {
            "time_s": second_pulse / 48000,
            "sample_index": second_pulse,
            "break_gain": break_gain(second_pulse, 48000, 180.0, 20.0, 2.0),
            "session_fade_gain": session_fade_gain(second_pulse, total, 48000, 10.0),
            "envelope": envelope(second_pulse, total, 48000, plan),
            "light_audio_envelope": light_level(second_pulse, total, 48000, plan),
        }
    )
    full_on = 48000 * 30
    envelope_rows.append(
        {
            "time_s": 30.0,
            "sample_index": full_on,
            "break_gain": 1.0,
            "session_fade_gain": 1.0,
            "envelope": envelope(full_on, total, 48000, plan),
            "light_audio_envelope": light_level(full_on, total, 48000, plan),
            "note": "sample 1_440_000 is an exact pulse onset 30 s in",
        }
    )

    rng = XorShift32(1)
    white = [rng.next_white() for _ in range(32)]
    pink = kellet_block(white)
    noise = {
        "id": "KELLET_PINK_SEED_1_FIRST_32",
        "algorithm": "paul_kellet",
        "rng": "xorshift32",
        "seed": 1,
        "white": _round(white),
        "pink_unnormalized": _round(pink),
        "note": (
            "Filter state starts at 0. These samples are before RMS normalization. "
            "research_v1 normalizes a block to the configured RMS only after the block "
            "is complete; do not normalize this 32-sample prefix and expect it to match a long session."
        ),
    }

    left = [math.sin(2.0 * math.pi * 200.0 * (index / 48000)) for index in range(8)]
    right = [math.sin(2.0 * math.pi * 240.0 * (index / 48000)) for index in range(8)]
    binaural = {
        "id": "BINAURAL_48K_FIRST_8",
        "sample_rate": 48000,
        "left_hz": 200.0,
        "right_hz": 240.0,
        "left": _round(left),
        "right": _round(right),
        "note": "Before normalization and before the session fade. Sample 0 is 0 on both channels.",
    }
    binaural_gate = dict(plan)
    binaural_gate["protocol"] = "binaural_beat"
    binaural_gate["light"] = dict(plan["light"], threshold=0.0)
    # Probe 30 s in, after the 10 s fade and before the first break, so the
    # envelope is 1. Offset 0 is on; offset 600 is the visual_50 falling edge.
    gate_total = 48000 * 200
    gate_on = 48000 * 30
    gate_off = gate_on + 600
    binaural_rows = {
        "id": "BINAURAL_VISUAL50_OVERRIDE",
        "note": (
            "protocol binaural_beat with mode audio_envelope still uses the "
            "50 percent grid. threshold 0 so the fade is the only envelope gate. "
            "Samples are 30 s in, where the session fade is finished and no break is active."
        ),
        "sample_on": gate_on,
        "light_on": light_level(gate_on, gate_total, 48000, binaural_gate),
        "sample_off": gate_off,
        "light_off": light_level(gate_off, gate_total, 48000, binaural_gate),
    }
    return {
        "mit_sine_48k_pulse_template.json": sine,
        "binaural_visual50_override.json": binaural_rows,
        "envelope_research_v1.json": {
            "id": "ENVELOPE_RESEARCH_V1_PROBES",
            "total_samples": total,
            "plan": plan,
            "rows": envelope_rows,
        },
        "kellet_pink_seed1.json": noise,
        "binaural_48k_first_samples.json": binaural,
    }


def write_vectors() -> None:
    VECTORS.mkdir(parents=True, exist_ok=True)
    for name, payload in build_vectors().items():
        path = VECTORS / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")


def check_vectors() -> int:
    expected = build_vectors()
    failed = 0
    for name, payload in expected.items():
        path = VECTORS / name
        if not path.exists():
            print(f"MISSING {path}")
            failed += 1
            continue
        actual = json.loads(path.read_text(encoding="utf-8"))
        if actual != payload:
            print(f"MISMATCH {path}")
            failed += 1
        else:
            print(f"ok {name}")
    return failed


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    if command == "write":
        write_vectors()
        return 0
    if command == "check":
        return check_vectors()
    print("usage: stimulus_oracle.py [check|write]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
