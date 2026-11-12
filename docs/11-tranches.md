# Delivery tranches

Work proceeds in order. A tranche can be split into several pull requests,
and each pull request still has one of the purposes below. Do not open the
firmware USB task in the same change as the kernel’s first sine function.

Tranche 0 is this documentation pack. Its exit criterion is met when
`python tools/oracle/stimulus_oracle.py check` passes and a reader can
implement Tranche 1 without asking what the sample grid is.

## What to build on the two CYDs

The kernel tranche and this list can run in parallel. On the boards the
order is:

1. Sync slate, [15-sync-slate.md](15-sync-slate.md), REQ-DBG-001 through
   REQ-DBG-003. This is the next firmware slice. It needs Wi-Fi and the
   backlight, not the audio kernel.
2. IO0 stop, REQ-HW-005, in that same slice. The platform task already
   times the 1.4 s hold.
3. Pin header, REQ-HW-006, before any new GPIO is claimed. Lamp on
   GPIO21, I2S left unused on 18, 19, and 23.
4. Quiet-channel scan, REQ-NET-011, in the same slice that opens the
   standalone SoftAP for the slate.
5. Filter sentence, REQ-HW-007, on the first session screen.
6. SPL note, REQ-HW-008, on that settings screen and on the web app.

## Tranche 1 — Pure kernel

**Purpose.** A dependency-free library whose outputs match the vectors.

**In scope.** TypeScript package `packages/stimulus-kernel`. Profiles
`research_v1` and `web_v1`. Streaming `reset` / `render`. Plan hash helper.
Schema validation wrapper. Tests TST-KERNEL-001 through 016.

**Out of scope.** Web UI, audio devices, GPIO, USB, BLE, the C port.

**Exit.** All Tranche 1 tests pass on a clean install. A 60 s render at
48 kHz does not allocate a second full-session copy of the signal
(REQ-KERNEL-006). The package’s dependency list has no React, Web Audio,
or serial library.

## Tranche 2 — Browser player

**Purpose.** Audio-only parity with the public site, on top of the kernel,
with the calibration and clock fixes this pack requires.

**In scope.** `apps/web`. Worker or AudioWorklet. Controls listed in
[08-web-and-bridge.md](08-web-and-bridge.md). Wake lock, Media Session,
acknowledgement control present but not yet able to arm hardware. Tests
TST-WEB-001 through 006.

**Out of scope.** Claiming a light is connected. Web Bluetooth. Packaging a
native installer.

**Exit.** A person can run a short MIT session in Chromium and in Firefox.
The captured first pulse matches the vector. The 44.1 kHz context refuses
`research_v1`. The string scan passes.

**Browser check.** This tranche changes a web UI, so the implementer
exercises start, stop, volume, protocol switch, break toggle, and the
44.1 kHz refusal in a real browser, not only in unit tests.

## Tranche 3 — Bridge and exact USB playback

**Purpose.** Path E2. The host renders, the device plays, the pin matches
the samples on that DAC.

**In scope.** `tools/bridge` with `--simulate` and a real USB backend.
Firmware playout of E2 frames, control frames, watchdog, pin off on fault.
VID/PID chosen and written down. Tests TST-PROTO-* and TST-FW-002, plus
TST-BENCH-001 before the capability bit is turned on.

**Out of scope.** On-device synthesis. BLE. Wi-Fi. Bounded mode.

**Exit.** Simulate mode runs the WebSocket script end to end. On hardware,
TST-BENCH-001 and TST-BENCH-003 have a written sheet, and only then does
HELLO_ACK set capability bit 1. The UI shows “Phase-locked on the device
clock” for that firmware and “simulate” when the badge is set.

## Tranche 4 — CYD on-device synthesis

**Purpose.** Path E1 on the badge in [13-cyd-badge.md](13-cyd-badge.md).

**In scope.** Fork `dashcdg_badge`. Keep the display, touch, amp, backlight,
and `dac_continuous` writer. Strip the karaoke and codec tree listed in
that document. C kernel passing TST-FW-001. Mono 48 kHz on GPIO26. Lamp
GPIO scheduled from the same sample counter. On-device LVGL session screen,
including the filter sentence (REQ-HW-007), the SPL note (REQ-HW-008), and
the IO0 stop path if the slate slice has not already landed it.
USB CDC control if the badge already has a free USB path; Wi-Fi control is
enough when USB gadget mode is not on this module.

**Out of scope.** A second badge. PTP. sACN. An external I2S DAC, unless
the MIT filter bench cannot be done any other way and the PR says so.
Changing the sample math.

**Exit.** TST-BENCH-001 sheet for this DAC and this lamp GPIO. Capability
bit 0 set only with that sheet. The speaker is the badge amp, not the
laptop. The MIT sheet records whether the 10 nF shunt was fitted. Click
protocol passes on the unmodified filter. Unplug or power-cut leaves the
lamp dark on the next boot.

## Tranche 5 — Scheduled lamps

**Purpose.** Path N from [14-network-time.md](14-network-time.md). Extra
badges flash at the conductor’s TAI times. sACN can black them out. OSC can
hand the conductor a timetag.

**In scope.** The sync slate in [15-sync-slate.md](15-sync-slate.md) may
land first, before the audio kernel, so two boards can be filmed with no
scope. Then TST-BENCH-006 when a scope exists. Then the same TSF
appointments with the kernel running. Infrastructure mode reuses the
badge Wi-Fi screen. The four-timestamp servo only when the boards are not
in one BSS. Status RGB, OSC ingest, sACN slots 1 and 2. Path B’s PLL only
for a node that cannot run TSF or the servo.

**Out of scope.** Calling a Wi-Fi lamp phase-locked. Streaming the waveform
over sACN or BLE. Playing audio on the lamps. Hardware PTP on the CYD.

**Exit.** TST-BENCH-005 sheet for two badges on one access point. A late
packet does not produce a late flash. A second conductor in the same group
id faults both publishers. The UI does not say phase-locked for a lamp. A
forced error estimate of 3 ms holds the lamp dark.

## Tranche 6 — Session hygiene

**Purpose.** Local logs, soak, and the rough edges that show up after the
timing is real.

**In scope.** JSONL logs, a local history view, a 60-minute soak note,
installer notes for the bridge, any wake-lock gaps found in Tranche 2.

**Out of scope.** Accounts, cloud sync, medical questionnaires, new
waveforms.

**Exit.** REQ-SAFE-006 is visible in the design (no network client in the
log path). A one-hour E1 soak has a bench note that the residual did not
walk by more than one sample.

## Pull request rules

- One tranche’s purpose per pull request. A PR that “also quickly adds BLE”
  during Tranche 1 is sent back.
- The oracle and the vectors change only in a PR whose body explains the
  math change and updates [03-stimulus-spec.md](03-stimulus-spec.md).
- Requirement IDs that the PR claims are listed in the PR body.
- Firmware that turns on an exact capability bit links the bench sheet in
  the PR body.

## Suggested PR slices

These are small enough for one review.

1. Oracle already present. Kernel sine and gate, TST-KERNEL-001..004 and 009.
2. Clicks, binaural, noise, envelope flags, the rest of TST-KERNEL.
3. Web audio-only shell and TST-WEB.
4. Bridge simulate mode and protocol tests.
5. Firmware control state machine on the host test model.
6. Firmware E2 or E1 on device, bench sheet in a follow-up PR that only
   flips the capability bit.

Step 6 is the first PR that needs hardware on the desk. Everything before
it is software.
