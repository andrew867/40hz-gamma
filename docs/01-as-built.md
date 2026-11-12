# As-built analysis

This document records what the public projects do. It is descriptive. The
normative rules for the new system are in [03-stimulus-spec.md](03-stimulus-spec.md)
and [02-requirements.md](02-requirements.md). Where the two sources disagree,
the table in the last section says which behavior `web_v1` keeps.

Sources, inspected November 2026:

- Python: [lurnake/40hz_poc](https://github.com/lurnake/40hz_poc) at
  `78f38137e90f1353cc8a4117d0d62b4925fe9689`. One module, `main.py`, 308 lines,
  plus a README that restates it. MIT licensed. See [NOTICE.md](../NOTICE.md).
- Web: `https://40hz-gamma-entrainment.joonaheino.com/`. Next.js app. The
  TypeScript source is not published. Behavior below was read from the
  production bundles `60daa4ef60f3de32.js` (UI and player) and
  `c9a91d3432c01a19.js` (generator worker). A later deploy can change this.
  Re-check the worker before freezing a `web_v1` change.

The author’s own description of the road map is the blog post
[Building a 40 Hz Gamma Entrainment Rig](https://blog.joonaheino.com/posts/40hz-gamma-entrainment/).
Audio exists. The light channel is explicitly future work. This pack is that
channel, plus a written contract for the audio that already exists.

## What the stimulus is

“40 Hz sound” in both codebases is a 40 Hz **rhythm**, not a 40 Hz tone.

| Protocol | Python name | Web value | Sound |
| --- | --- | --- | --- |
| MIT sine | `MIT_SINE_PULSE` | `sine_pulse` | 10 kHz sine, 1 ms on, then silence, repeated at 40 Hz |
| Click train | `HUMAN_CLICK_TRAIN` | `click_train` | One windowed noise burst, 7 ms, repeated at 40 Hz |
| Binaural | `BINAURAL_BEAT` | `binaural` | Left 200 Hz, right 240 Hz, continuous. The 40 Hz difference is perceptual |

The 4% duty cycle of the sine protocol is `1 ms / 25 ms`. BrainWAVE (eNeuro
2022, DOI 10.1523/ENEURO.0257-22.2022) uses that 4% audio duty for audio-only
work and a separate 50% light square wave for visual flicker. The published
visual pattern is 12.5 ms on and 12.5 ms off, with the rising edges aligned
when both are used. The new light mode `audio_envelope` follows the audible
burst. The light mode `visual_50` follows the 50% visual pattern. They are
different signals. See [03-stimulus-spec.md](03-stimulus-spec.md).

Cited parameter sources, which both projects already point at:

- Iaccarino et al., Nature 2016, DOI 10.1038/nature20587
- Martorell et al., Cell 2019, DOI 10.1016/j.cell.2019.02.014
- Chan et al., PLOS ONE 2022, DOI 10.1371/journal.pone.0278412
- Singer et al., Nature Protocols 2018, DOI 10.1038/s41596-018-0021-x
- Adaikkan et al., Neuron 2019, DOI 10.1016/j.neuron.2019.04.011
- Jirakittayakorn and Wongsawat, 2017, DOI 10.1016/j.ijpsycho.2017.07.010
- Clements-Cortes et al., 2016, DOI 10.3233/JAD-160081

Those papers motivate the default numbers. They are not a validation of this
software, and the UI must not say they are.

## Python generator

`GammaStimulator` builds the entire session as a NumPy array, then writes it
to PyAudio in 1024-frame blocks.

Defaults in `main`:

| Field | Value |
| --- | --- |
| Protocol | `MIT_SINE_PULSE` |
| Sample rate | 44100 |
| Duration | 600 s |
| Pink noise | on, target RMS 0.05 |
| Session fade | 10 s linear, both ends |
| Break | 30 s every 5 min, 2 s fade |
| Peak scale | divide by max abs, multiply by 0.95 |

Sine burst: `sin(2π · 10000 · t)` for `floor(0.001 * fs)` samples, no edge
window. Placement period is `floor(fs / 40)`. At 44100 Hz that is 1102
samples, so the rhythm is 40.01815 Hz (+453.7 ppm), not 40 Hz.

A burst is written only when `start + length < total_samples`. The final
burst is dropped if it would touch the last sample.

Click: one `randn` buffer times a Hann window, reused for every burst.
Unseeded.

Binaural: full-length sines at `base ± beat/2`. With the stored base of 220
and beat of 40, the channels are exactly 200 and 240 Hz. No bursts, so there
is no pin edge to lock to an acoustic onset.

Breaks sit at the **start** of each interval. At t = 0 the code is already
inside the break and fading out. The website does the opposite.

Pink noise is an FFT `1/sqrt(f)` filter, then RMS-scaled. For a stereo array,
`len(session_audio)` is the sample count and the code divides by
`channels`. That asks for a noise buffer of `N/2` samples and then adds it to
an `N`-sample buffer. Treat binaural-plus-noise in the Python script as
broken until a test proves a broadcast saves it.

`verify_audio` looks for FFT energy in a ±2 Hz window around 40 Hz. That is
the wrong feature for these signals:

- The sine burst’s spectral peak is at 10 kHz. A 1-second render at 48 kHz
  had peak magnitude about 960 at 10 kHz and about 6.5 near 40 Hz.
- Binaural energy is at 200 Hz and 240 Hz. The 40 Hz beat is not in either
  channel’s spectrum.
- Clicks do have a line near 40 Hz, and also energy across the band. A peak
  near 40 Hz still does not prove the period.

`check_phase_consistency` takes the Hilbert phase of the first sample of
three 100 ms windows and asks whether the variance is under 0.1. That does
not measure burst-to-burst interval jitter. Do not port it as an acceptance
test.

Calibration plays 1 kHz at amplitude `10^(-20/20) = 0.1` for 5 s and tells
the user to set the system volume until a meter reads 60–65 dB SPL. The
session is then peak-scaled to 0.95. The continuous calibration tone is about
19.5 dB below the session peak (`20·log10(0.95/0.1)`). A slow SPL meter on a
1 ms burst also reads far below the peak. The README’s 160 MB figure for one
hour of mono float32 at 44.1 kHz counts samples, not bytes. The array is
`44100 * 3600 * 4 ≈ 606 MiB`, and stereo is twice that.

The script logs start time, end time, protocol, duration, and
`completed` or `interrupted` to `therapy_log.csv`.

## Web application

Stack visible in the bundle, without claimed package versions:

- Next.js with the App Router and Turbopack chunks
- React, Tailwind-style utility classes, Radix-style select, lucide-style icons
- A dedicated Web Worker for generation
- Web Audio `AudioContext`, `AudioBufferSourceNode`, `GainNode`
- Screen Wake Lock and the Media Session API
- A web app manifest (`standalone`, black theme, portrait)

There is no Bluetooth, serial, USB, WebSocket, or light code.

### Defaults the UI actually submits

| Control | Initial state | Sent to the worker |
| --- | --- | --- |
| Protocol | `sine_pulse` | yes |
| Duration | 3600 s | yes |
| Volume | 1 | playback gain only, stripped before generation and before the cache key |
| Pink noise | on | yes |
| Noise level | 0.02 | yes, RMS target |
| Breaks | on | `breakInterval` becomes 0 when the switch is off |
| Break every | 3 min | multiplied by 60 inside the worker |
| Break duration | 20 s | yes |
| Break fade | 2 s | yes, no slider |
| Session fade | none in the UI | hardcoded 10 s inside the worker |

The page copy asks for a 20 s pause every 3 minutes. That matches these
defaults. The Python README’s 30 s / 5 min figures do not.

### Worker algorithm

The worker handles `{type: "generate", id, config, sampleRate}` and posts
`progress`, `done`, or `error`. Buffers are transferred. The page keeps a
`Map` of at most four generated channel sets, keyed by protocol, duration,
noise, breaks, and sample rate.

Shared helpers:

- Break gain is evaluated in seconds. The break occupies the **end** of each
  interval. Fade-out, silence, fade-in, then the next interval starts at full
  gain. Pulses with gain `<= 0.001` are skipped.
- Session fade is linear and applied after mix and peak normalization. Fade
  length is `min(floor(10 * sampleRate), floor(length / 2))`. Sample 0 is
  multiplied by 0. The last sample is multiplied by `1/fade_samples`, not by 0.
- Peak normalization scales `signal + noise` so the peak is 0.95. Noise
  therefore changes the stimulus amplitude.
- Noise is **not** multiplied by the break gain. Breaks remove pulses and
  leave the pink noise running. The session fade does apply to the mix, so
  the noise fades in and out at the ends.

Sine burst, per sample `i` inside the 1 ms window, sample rate `fs`:

```
length = floor(0.001 * fs)
taper  = min(floor(150e-6 * fs), floor(length / 4))
gain   = 1
if taper > 0 and i < taper:       gain = 0.5 * (1 - cos(π * i / taper))
if taper > 0 and i >= length-taper: gain = 0.5 * (1 - cos(π * (length - 1 - i) / taper))
sample = sin(2π * 10000 * i / fs) * gain
```

At 48 kHz, `length = 48`, `taper = 7`, period = `floor(48000/40) = 1200`.
The rhythm is exactly 40 Hz. The deployed player uses the context rate, so a
machine whose `AudioContext` is 44.1 kHz gets the same +453.7 ppm error as
the Python script.

Click burst: `floor(0.007 * fs)` samples of `2*random()-1`, times
`0.5 * (1 - cos(2π * i / (length-1)))`. One template is reused. `Math.random`
is unseeded, so two generations with the same UI settings are not equal.

Binaural: `sin(2π * 200 * t)` and `sin(2π * 240 * t)`. The frequencies are
constants, not read from the config. If noise is on, each channel gets its
own pink buffer. Each channel is peak-normalized separately, then faded.

Pink noise is the Paul Kellet recurrence, not the Python FFT. White input is
`2*Math.random()-1`. Coefficients are locked in the oracle as
`KELLET_B0` through `KELLET_WHITE`. The filter runs in blocks of 480000
samples. Output is RMS-scaled to `noiseLevel`.

### Playback

```
AudioContext
  -> AudioBufferSourceNode
  -> GainNode (gain = volume slider)
  -> destination
```

The context is created on the default output. `outputLatency` and
`baseLatency` are never read. Nothing schedules against
`AudioContext.currentTime` beyond `start()` with no offset. There is no
sample-accurate link to any other device, because there is no other device.

Calibration is a 1 kHz sine at amplitude 0.1 for 5 s, connected straight to
`destination`, bypassing the session gain. Combined with peak 0.95, the same
~19.5 dB gap as the Python script is present. The on-screen instruction still
says to make that tone read 60–65 dB SPL.

Wake lock is requested when a session starts. Media Session metadata is set
so a phone is less likely to suspend the tab. The pause action handler is
empty. A suspended context is resumed by the play handler.

The on-screen “break” flag uses the same end-of-interval rule as the worker,
driven by elapsed wall time from `Date.now()`, not by
`AudioContext.currentTime`. The label can drift from the audio if the tab
stalls. The audio itself does not drift relative to its buffer, because the
buffer was pre-rendered.

## Behaviors the successor must not copy by accident

| ID | As-built behavior | New default |
| --- | --- | --- |
| Q1 | Python breaks at the start of the interval, so playback begins in a fade-out | Breaks at the end, matching the site and the on-page copy |
| Q2 | Site leaves pink noise on during breaks | `research_v1` ducks noise with the envelope. `web_v1` keeps noise up |
| Q3 | Peak-normalizing the mix makes the stimulus level depend on noise | `research_v1` fixes the stimulus peak, then adds noise, then limits only if the sum exceeds 0.95 |
| Q4 | 44.1 kHz grid is 40.018 Hz | `research_v1` allows only rates where `sample_rate / 40` is an integer and `0.001 * sample_rate` is an integer. 48000 and 96000 qualify |
| Q5 | Unseeded clicks and noise | Seeded `xorshift32`, seed stored in the plan |
| Q6 | Calibration tone 19.5 dB below session peak | Calibration tone peak equals the stimulus peak the user is about to hear. The UI states the weighting limit of a phone SPL meter |
| Q7 | “40 Hz SNR” check | Tests compare sample indices and golden vectors |
| Q8 | Full-hour float32 allocation | Streaming `render(frame_count)` API. One hour mono at 48 kHz float32 is 659 MiB before the noise buffer |
| Q9 | No light, no second clock | Light gate is a pure function of the same sample index |

`web_v1` exists so a later test can show the kernel still reproduces the
site: smoothed 1 ms edges, noise through breaks, legacy peak scale, and
`floor(fs/40)` even at 44100 Hz. The user-facing default is `research_v1`.
