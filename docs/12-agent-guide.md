# Implementation guide

You are implementing one tranche of the system specified in `docs/`. You do
not need the conversation that produced the spec. You need this file, the
tranche file, and the documents that tranche names.

## First 15 minutes

1. Run `python tools/oracle/stimulus_oracle.py check` from the repository
   root. If it fails, stop and fix the oracle before writing product code.
2. Read [11-tranches.md](11-tranches.md) and identify the first tranche
   whose exit tests are not in the tree.
3. Read only the docs that tranche points at. Tranche 1 needs
   [03-stimulus-spec.md](03-stimulus-spec.md),
   [02-requirements.md](02-requirements.md), and
   [10-test-plan.md](10-test-plan.md). It does not need the USB frame layout.
4. Do not re-reverse-engineer the live website unless a `web_v1` test
   disagrees with [01-as-built.md](01-as-built.md). The bundle was not
   published as source and may have moved.

## Rules that are easy to violate

- The lamp pulses once per burst, at 40 Hz. It does not emit a 10 kHz
  square wave. The 10 kHz signal is the sine inside the 1 ms audio window.
- Exact sync means one sample clock for the headphones and the pin. A
  WebSocket, a BLE notification, or a PTP library in the browser does not
  qualify. If you are in Tranche 1–4, do not add a PTP dependency. The
  first board is the CYD badge, internal 8-bit DAC via `dac_continuous`,
  not an ESP32-S3 and not the legacy I2S-to-DAC mode.
- Two CYDs sync by sharing an 802.11 BSS and reading the TSF. Do not start
  with ESP-WIFI-MESH or monitor mode. Do not stream PCM. Read
  [14-network-time.md](14-network-time.md) and ADR 0008 before writing a
  radio path. The first test is TST-BENCH-006.
- `research_v1` at 48 kHz is the default. 44.1 kHz is a compatibility
  profile that must be asked for.
- Breaks sit at the end of the interval. The Python script’s start-of-interval
  break is not the default.
- Noise in `research_v1` follows the envelope. The website’s “noise stays on
  during the break” behavior is `web_v1` only.
- Volume is a gain after the renderer. It is not part of the plan hash.
- The pin’s idle level is off. Every fault path drives off. Do not leave a
  pull-up as the only thing holding the lamp dark.
- Do not write medical claims, including in test fixture names and log keys.
- Do not copy the minified site bundle into the repo. `vendor/` is a local
  cache and is gitignored.

## How to port the math

Prefer translating `tools/oracle/stimulus_oracle.py` over translating the
prose. The prose is the explanation; the oracle is the tie-breaker.

For TypeScript, keep numbers in IEEE-754 doubles for the oscillator and the
filter, and store audio as float32 only at the render boundary. Compare
against the vectors in float64 before the float32 store, so a float32
rounding does not fail a 1e-9 test. The test may cast the vector and the
output to a common comparison.

For C, use `double` for the same recurrence, then store `float`. The host
unit test compiles the C with the ordinary toolchain. The ESP-IDF build
comes in Tranche 4 and must link the same files.

RNG and Kellet state are part of the session, reset exactly as the stimulus
spec says. A firmware shortcut that uses the hardware RNG will fail
TST-KERNEL-005’s noise vector and is a functional bug, not an optimization.

## Definition of done for a pull request

- The PR body names the tranche and the requirement IDs.
- New behavior has a test from [10-test-plan.md](10-test-plan.md), or the
  PR adds the test in the same change.
- `python tools/oracle/stimulus_oracle.py check` still passes.
- No new runtime dependency in the kernel.
- UI changes that affect playback were exercised in a browser, and the PR
  says what was clicked.
- Firmware capability bits for exact mode stay off unless a bench sheet is
  in the PR.

## Extending the system later

**New auditory protocol.** Add an enum value to the schema, a branch in the
kernel, a vector, and a UI label. Keep the gate function’s contract: it
still consumes envelope, period, and a width. If the protocol has no burst,
follow the binaural rule and use `visual_50`.

**New transport.** Implement the message list in
[06-protocols.md](06-protocols.md). Do not invent a parallel plan JSON.
Register the transport in the platform table in
[08-web-and-bridge.md](08-web-and-bridge.md) with an honest sync class.

**New board.** Re-measure `dac_pipeline_samples`. A new integer is a new
bench sheet. The kernel does not change.

**Experimental frequency.** Only with REQ-SAFE-007’s extra acknowledgement.
The default UI keeps offering 40 Hz. The kernel may already receive
`repetition_hz` as a parameter; the UI tranche does not expose it until the
warning exists.

**Phase between light and sound as a research variable.** Use
`phase_offset_us`. Do not hide it inside the PLL latency. Calibration
measures the path. The plan offset is the experiment.

## What “good” looks like

A later reader can run the kernel tests with no hardware and know the
samples are right. They can run the bridge in `--simulate` and watch a
session arm. They can flash firmware and, if the bench sheet exists, trust
the word phase-locked. If the sheet does not exist, the device refuses to
claim the word.

That split, between math that is tested on a laptop and timing that is
tested with a microphone and a photodiode, is the design. Do not collapse
it by asserting exactness in a unit test that never saw the DAC.
