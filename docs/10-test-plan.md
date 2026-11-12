# Test plan

Tests cite requirement IDs. A tranche exits only when its rows are green.
Bench rows are not CI rows. They are written procedures with a stored
result.

Tolerances:

| Comparison | Tolerance |
| --- | --- |
| Sine and binaural samples against vectors | absolute error ≤ 1e-9 per sample |
| Envelope probe values | absolute error ≤ 1e-9 |
| Kellet prefix against `kellet_pink_seed1.json` | absolute error ≤ 1e-9 |
| Gate bits | exact |
| int16 quantization in the bridge | exact match to round-to-nearest, ties away from zero, then clip to int16. Document the tie rule in the bridge test so C and Python agree |
| Exact-mode bench | peak-to-peak residual ≤ 1 sample at 48 kHz after compensation, at both t≈0 and t≈60 min |
| Bounded-mode bench | p95 ≤ 500 µs, max ≤ 2 ms, over 10 min |

## Kernel — Tranche 1

| Test | Covers | Procedure |
| --- | --- | --- |
| TST-KERNEL-001 | REQ-KERNEL-004, REQ-STIM-001, REQ-STIM-003 | Render the MIT template at 48 kHz, edge `raised_cosine_150us`, and compare to `template_web_smoothed` |
| TST-KERNEL-002 | REQ-STIM-003 | Compare the hard-gate template to `template_hard_gate` |
| TST-KERNEL-003 | REQ-STIM-001 | Assert period 1200, pulse 48, and onsets at 0, 1200, 2400, 3600 |
| TST-KERNEL-004 | REQ-STIM-006, REQ-STIM-007, REQ-LIGHT-001, REQ-LIGHT-007 | Assert every row of `envelope_research_v1.json` |
| TST-KERNEL-005 | REQ-STIM-008 | Assert the 32 white and pink samples for seed 1 |
| TST-KERNEL-006 | REQ-STIM-005 | Assert the eight binaural samples |
| TST-KERNEL-007 | REQ-KERNEL-002 | `render` the same 480-sample block twice from a fresh `reset` and compare |
| TST-KERNEL-008 | REQ-KERNEL-005 | A `research_v1` plan at 44100 Hz is rejected. The same plan at 48000 is accepted |
| TST-KERNEL-009 | REQ-LIGHT-002 | `visual_50` at 48 kHz is high for samples 0..599 of each period and low for 600..1199, with envelope 1 and threshold 0 |
| TST-KERNEL-010 | REQ-LIGHT-003 | `phase_offset_us` of 1000 delays the gate by 48 samples at 48 kHz |
| TST-KERNEL-011 | REQ-LIGHT-004 | `vectors/binaural_visual50_override.json`: logical light is 1 at sample 1,440,000 and 0 at sample 1,440,600. The render result also carries a flag the UI can show |
| TST-KERNEL-012 | REQ-LIGHT-006 | Duty 0.75 is rejected |
| TST-KERNEL-013 | REQ-STIM-009 | With noise off, the session peak equals 0.95. With a very large `level_rms` in a unit test that bypasses the schema cap, `limited` becomes true and the peak is 0.95 |
| TST-KERNEL-014 | REQ-STIM-010 | A `web_v1` fixture with noise off matches legacy normalization of the template (`first_16_after_legacy_normalize`) and keeps a non-zero noise sample during a break when noise is on and the break gain is 0 |
| TST-KERNEL-015 | REQ-KERNEL-001 | Static check or review: the kernel package imports no audio, USB, or network module |
| TST-KERNEL-016 | REQ-STIM-011 | Two plans that differ only in `playback.volume` have the same plan hash |

Property checks, not just fixtures:

- For a no-break, no-fade MIT plan, every sample where `index % 1200 < 48`
  is inside a copy of the template, and every other sample is 0.
- The gate is never 1 where that statement is false, for `audio_envelope`
  with threshold 0 and offset 0.
- `render` across a block boundary equals one `render` of the concatenated
  length. Split at frame 48 and at frame 47.

## Protocol — Tranche 3

| Test | Covers | Procedure |
| --- | --- | --- |
| TST-PROTO-001 | frame parser | The bytes in `examples/stop-frame.hex` decode as STOP version 1 with a valid CRC. Flipping one payload bit fails the CRC |
| TST-PROTO-002 | schema | `examples/session-plan.research.json` validates. Removing `photosensitivity_ack` or setting duration to 8000 fails |
| TST-PROTO-003 | REQ-BRIDGE-001 | The bridge bound address is 127.0.0.1. A connection that does not authenticate first is closed |
| TST-PROTO-004 | REQ-SAFE-005 | Arming a light plan with `photosensitivity_ack: false` returns an error and status stays `idle` |
| TST-PROTO-005 | hash | The bridge and a Python test compute the same SHA-256 for the example plan |

## Web — Tranche 2

| Test | Covers | Procedure |
| --- | --- | --- |
| TST-WEB-001 | REQ-WEB-001 | Start a 2 s audio-only session in a headless browser or a worklet harness. Capture the buffer. Compare the first pulse to the vector |
| TST-WEB-002 | REQ-WEB-002 | Stub `AudioContext.sampleRate` to 44100 and expect a blocking notice, not playback, in `research_v1` |
| TST-WEB-003 | REQ-SAFE-002 | The light start control is disabled before the acknowledgement click and enabled after it |
| TST-WEB-004 | REQ-SAFE-001 | A text scan of the built UI strings finds none of: cure, treat, therapy, patient, dosage, clinically proven. “Experimental research tool” is present |
| TST-WEB-005 | REQ-STIM-011 | Moving volume during playback does not call the generator a second time |
| TST-WEB-006 | clock | The on-screen elapsed time advances from the audio clock. A test doubles `Date.now` and expects the displayed audio position to stay put |

TST-WEB-004’s word list is blunt on purpose. The background page may name
papers. It may not use those product words.

## Firmware and bench — Tranches 3 and 4

CI, no hardware:

| Test | Covers | Procedure |
| --- | --- | --- |
| TST-FW-001 | REQ-DEV-003 | The C kernel, compiled on the host, passes TST-KERNEL-001 through 014 |
| TST-FW-002 | REQ-DEV-001 | A host-side state-machine model starts in `idle` with pin off. Every fault injection ends with pin off |
| TST-FW-003 | REQ-SYNC-007 | The model, given a 5 ms frame gap, enters `fault` and clears the pin |

Bench, recorded in `docs/bench/` as a short markdown sheet per firmware
version (that directory is created by the tranche that first runs the
test):

| Test | Covers | Procedure |
| --- | --- | --- |
| TST-BENCH-001 | REQ-SYNC-001 | The calibration procedure in [05-time-sync.md](05-time-sync.md), exact mode |
| TST-BENCH-002 | REQ-SYNC-004 | The same procedure for bounded mode, if that firmware enables it |
| TST-BENCH-003 | REQ-SYNC-007 | Unplug USB during a run. The lamp is dark as soon as the cable leaves, and stays dark on the next boot |
| TST-BENCH-004 | REQ-DEV-001 | Power-cycle and watch the pin with a scope through enumeration. It stays at the off level |
| TST-BENCH-007 | REQ-DBG-001, REQ-DBG-002 | Film the slate as [15-sync-slate.md](15-sync-slate.md) describes. Pass is backlight or rear-LED onset within one slo-mo frame, and centisecond digits differing by at most one. Record fps. This does not pass the 200 µs TSF row |
| TST-HW-STOP | REQ-HW-005 | A platform-task hold of the button duration forces lamp off, DAC stop, and amp mute with the LVGL lock held by someone else |
| TST-HW-CHAN | REQ-NET-011 | A fake scan with busy channels 1 and 11 and an empty channel 6 selects 6. A second call during a session does not change channel |
| TST-HW-COPY | REQ-HW-007 | MIT with `gamma_shunt_removed` false shows the dull-tone sentence. Clicks show the unmodified-badge sentence. True hides the dull-tone sentence |
| TST-HW-VOL | REQ-HW-008 | Saving 70%, arm’s length, 65 dB reloads the same note and does not change the plan hash or the live gain |

A firmware build whose HELLO_ACK sets an exact capability bit without a
TST-BENCH-001 sheet for that git revision is a failed review.

## Traceability

| Requirement group | Proving tests | Tranche |
| --- | --- | --- |
| REQ-KERNEL-* REQ-STIM-* REQ-LIGHT-001..007 | TST-KERNEL-* | 1 |
| REQ-WEB-* REQ-SAFE-001..003 | TST-WEB-* | 2 |
| REQ-BRIDGE-* REQ-DEV-004 exact USB | TST-PROTO-* TST-BENCH-001 | 3 |
| REQ-DEV-001..003 REQ-SYNC-001 E1 | TST-FW-* TST-BENCH-001 TST-BENCH-003 | 4 |
| REQ-SYNC-003..006, REQ-NET-* | TST-BENCH-002, TST-BENCH-005, TST-BENCH-006, TST-BENCH-007 | 5 |
| REQ-DBG-* | slate matches [15-sync-slate.md](15-sync-slate.md); TST-BENCH-007 if no scope | 5, and the slate may land before audio |
| REQ-HW-001..004, REQ-HW-007, REQ-HW-008 | review against [13-cyd-badge.md](13-cyd-badge.md), TST-HW-COPY, TST-HW-VOL, TST-BENCH-001 | 4 |
| REQ-HW-005, REQ-HW-006, REQ-NET-011, REQ-DBG-* | slate slice: TST-HW-STOP, pin header review, TST-HW-CHAN, TST-BENCH-007 | before audio, on the two CYDs |
| REQ-SAFE-006 REQ-WEB-003 | log inspection and a wake-lock call check | 6 |

REQ-LIGHT-008 is proved by TST-BENCH-001, because that is the measurement
that sees the gate and the acoustic sample together.
