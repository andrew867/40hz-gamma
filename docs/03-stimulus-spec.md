# Stimulus and light specification

This file is normative for both profiles. The executable form is
`tools/oracle/stimulus_oracle.py`. If an example below and the oracle
disagree, the oracle and the vectors win until a reviewed change lands in
both.

All time inside the engine is an integer sample index. Conversion from
seconds uses the rules in this file, not a wall clock.

## Grid

```
period_samples = floor(sample_rate / repetition_hz)
pulse_samples  = floor(pulse_duration_s * sample_rate)
```

`research_v1` additionally requires both divisions to be exact, and requires
`repetition_hz == 40` unless REQ-SAFE-007 is satisfied. Legal rates in the
kernel are 48000 and 96000. The CYD firmware accepts only 48000
(REQ-HW-001).

| Rate | Period | Achieved Hz | Error | 1 ms pulse |
| --- | ---: | ---: | ---: | ---: |
| 48000 | 1200 | 40 | 0 ppm | 48 samples, 1000 µs |
| 96000 | 2400 | 40 | 0 ppm | 96 samples, 1000 µs |
| 44100 | 1102 | 40.01814882 | +453.7 ppm | 44 samples, 997.7 µs |

44100 is legal only in `web_v1`.

At 48 kHz, sample `48000 * k` for integer k is a burst onset. That is a
useful bench mark: the edge at 30.000 s is sample 1,440,000.

## Envelope

Breaks, placement `end`:

```
if interval_s <= 0 or duration_s <= 0:
    break_gain = 1
else:
    fade = min(fade_s, duration_s / 2)
    t = (sample_index / sample_rate) mod interval_s
    stim_until = max(0, interval_s - duration_s)
    if t < stim_until:
        break_gain = 1
    else:
        into = t - stim_until
        if into < fade:
            break_gain = 1 - into / fade
        else if into > duration_s - fade:
            break_gain = (into - (duration_s - fade)) / fade
        else:
            break_gain = 0
```

The comparison `into > duration_s - fade` is strict. At the exact sample
where `into == duration_s - fade`, the gain is still 0. The next sample
begins the fade-in. At the exact start of the break, `into == 0`, so the
gain is still 1. This matches the deployed worker.

Session fade, default `fade_s = 10`:

```
fade_n = min(floor(fade_s * sample_rate), floor(total_samples / 2))
if sample_index < fade_n:
    fade_gain = sample_index / fade_n
else if sample_index >= total_samples - fade_n:
    fade_gain = 1 - (sample_index - (total_samples - fade_n)) / fade_n
else:
    fade_gain = 1
```

```
envelope = break_gain * fade_gain
```

Default probes for a 200 s timeline at 48 kHz with a 180 s interval, 20 s
break, and 2 s fade are in `vectors/envelope_research_v1.json`. Selected
rows:

| Time (s) | Break gain | Fade gain | Envelope | Light at a burst onset |
| ---: | ---: | ---: | ---: | --- |
| 0 | 1 | 0 | 0 | off |
| 0.025 | 1 | 0.0025 | 0.0025 | off, below threshold 0.5 |
| 10 | 1 | 1 | 1 | on |
| 160 | 1 | 1 | 1 | on, this sample is still the last full-gain instant |
| 161 | 0.5 | 1 | 0.5 | on, because the test is `envelope < threshold`, and 0.5 is not less than 0.5 |
| 170 | 0 | 1 | 0 | off |
| 179 | 0.5 | 1 | 0.5 | on |
| 180 | 1 | 1 | 1 | on, next interval |

Placement `start` (Python compatibility only) inverts the cycle: the break
occupies `[0, duration_s)` of each interval, with the same fade shape the
Python script uses. Do not offer it in the main UI.

`research_v1` omits a burst from the audio buffer when `envelope <= 0.001`.
`web_v1` omits a burst only when `break_gain <= 0.001`, then multiplies the
mixed buffer by the session fade, which is what the deployed worker does.
During the opening fade those two choices differ by a burst whose amplitude
is at most 0.001 before peak scaling. The light does not use 0.001. It uses
`threshold` (default 0.5) on the full envelope, so the lamp stays off while
the fade is still below that threshold.

## MIT sine

Carrier 10 kHz. One template is built, then copied to each onset
`n * period_samples` and multiplied by `break_gain` at the onset sample.
`research_v1` also multiplies by `fade_gain`. `web_v1` applies the session
fade later, to the mixed buffer. Those two orders match when noise is off
and no limiter runs.

Edge `hard`: template sample `i` is `sin(2π * 10000 * i / sample_rate)`.

Edge `raised_cosine_150us`:

```
taper = min(floor(150e-6 * sample_rate), floor(pulse_samples / 4))
gain = 1
if taper > 0 and i < taper:
    gain = 0.5 * (1 - cos(π * i / taper))
if taper > 0 and i >= pulse_samples - taper:
    gain = 0.5 * (1 - cos(π * (pulse_samples - 1 - i) / taper))
```

At 48 kHz, `taper` is 7. The committed template is
`vectors/mit_sine_48k_pulse_template.json`. Absolute error per sample for a
port is `1e-9` against that file. The legacy scale recorded there is
`0.95 / template_peak` and applies only to `web_v1` / `legacy_peak_0_95`.

The pin is high for the whole pulse window when the light rule says on. It
is not high only on positive half-cycles of the 10 kHz sine.

## Click train

```
length = floor(0.007 * sample_rate)
white[i] = xorshift32_white(click_seed)
hann[i] = 0.5 * (1 - cos(2π * i / (length - 1)))
template[i] = white[i] * hann[i]
```

At 48 kHz, `length` is 336. The same template is added, scaled by the
envelope, at every onset. A new seed is a new plan. `web_v1` may use an
unseeded generator only inside a test that is marked non-reproducible; such
a test cannot be a release gate.

## Binaural

```
left[i]  = sin(2π * left_hz * i / sample_rate)
right[i] = sin(2π * right_hz * i / sample_rate)
```

Defaults: 200 and 240. First eight samples at 48 kHz are in
`vectors/binaural_48k_first_samples.json`. Sample 0 is 0 on both channels.
There is no burst onset. REQ-LIGHT-004 selects `visual_50` for the gate.

## Noise

White samples come from `XorShift32` in the oracle. The construction is
uint32 throughout:

```
state = seed if seed != 0 else 1
x = state
x ^= (x << 13) with the result masked to 32 bits
x ^= x >> 17
x ^= (x << 5) masked to 32 bits
state = x
unit = state / 4294967296
white = 2 * unit - 1
```

Seed 1’s first 32 white and pink samples are in
`vectors/kellet_pink_seed1.json`. Pink state starts at 0:

```
b0 = 0.99886 * b0 + 0.0555179 * white
b1 = 0.99332 * b1 + 0.0750759 * white
b2 = 0.96900 * b2 + 0.1538520 * white
b3 = 0.86650 * b3 + 0.3104856 * white
b4 = 0.55000 * b4 + 0.5329522 * white
b5 = -0.7616 * b5 - 0.0168980 * white
pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + 0.5362 * white
b6 = 0.115926 * white
```

RMS uses the finished block the caller asked to render, not a running
estimate, when the caller is producing a golden block. Firmware that renders
forever keeps a single filter state for the session and applies a constant
gain computed from a 1-second warmup discarded before sample 0, or from the
known block RMS of a reference second stored beside the plan. Tranche 1
locks the constant-gain method: generate 48000 pink samples with the plan
seed, measure RMS, set `noise_gain = level_rms / rms`, reset the filter and
the RNG, then render the session. Resetting is mandatory so sample 0 matches
a cold filter.

`follows_envelope == true` multiplies pink by `envelope` after the gain.
`false` is the `web_v1` behavior: pink ignores breaks, and the session fade
is applied to the mix afterwards.

## Level

`fixed_stimulus`:

1. Render the dry stimulus for the block with envelope gains already applied.
2. Measure the peak of the dry stimulus over the whole session timeline
   (for a streaming engine, the peak of the MIT template times the maximum
   envelope, which is 1, is enough, because the template is only scaled
   down by the envelope).
3. Multiply the dry stimulus by `stimulus_peak / peak`.
4. Add noise.
5. If the block peak exceeds 0.95, multiply the block by `0.95 / block_peak`
   and set `limited = true` on the render result.

`legacy_peak_0_95`:

1. Render dry stimulus with break gain only.
2. Add noise that ignores breaks.
3. Scale the sum so its peak is 0.95.
4. Apply the session fade to the sum.

Volume is applied by the DAC gain or the Web Audio `GainNode` after this
pipeline. Default volume is 1. Calibration uses a 1 kHz sine at amplitude
`stimulus_peak` for 5 s, through the same volume control, and the UI tells
the user that a phone meter’s A-weighted slow reading is not the peak level
of a 1 ms burst.

## Light function

```
if not light.enabled: return 0
if envelope < threshold: return 0
mode = plan.mode
if protocol == binaural_beat and mode == audio_envelope:
    mode = visual_50
shift = round(phase_offset_us * 1e-6 * sample_rate)
if sample_index - shift < 0: return 0
offset = (sample_index - shift) mod period_samples
if mode == audio_envelope:
    return 1 if offset < pulse_samples else 0
if mode == visual_50:
    width = round(period_samples * duty)
    return 1 if offset < width else 0
```

`vectors/binaural_visual50_override.json` locks the override at 30 s: sample
1,440,000 is on, and sample 1,440,600 is off.

`duty` and `max_duty` cannot exceed 0.5. `audio_envelope` at 1 ms / 25 ms
has duty 0.04. Clicks at 7 ms have duty 0.28. Both fit under the cap.
`visual_50` at duty 0.5 sits on the cap.

Polarity is not part of this function. The pin driver applies it.

Expected duty is the fraction of samples with logical 1 over one period at
envelope 1. The planner rejects plans whose expected duty exceeds `max_duty`.

## Streaming API

Language-neutral shape the Tranche 1 kernel must expose:

```
reset(plan, sample_rate) -> void
render(frame_count) -> {
  channels: float32[channel_count][frame_count],
  gate: uint8[frame_count],   // 0 or 1, logical
  sample_index_start: int,
  limited: bool
}
```

`frame_count` of 0 returns empty arrays. A frame size of 48 samples is 1 ms
at 48 kHz and is the USB frame size used later. The engine must accept any
positive frame size up to 4800.

Channel count is 1 for sine and clicks, 2 for binaural. The gate is not an
audio channel. E2 packing of the gate into a USB frame happens outside the
engine.

## Plan identity

The cache key and the firmware plan hash are the SHA-256 of the canonical
JSON of the plan with `playback` removed. Canonical means object keys sorted
lexicographically, no insignificant whitespace, UTF-8. Volume changes must
not reshuffle a running buffer or re-flash a running device.
