# Time sync

## The requirement in one sentence

Each audible burst and the matching lamp edge are the same sample index on
the same clock the listener’s headphones use.

A 40 Hz period is 25 ms. One sample at 48 kHz is 20.833 µs. The exact-mode
budget after calibration is one sample of residual, and that residual is a
constant pipeline delay, not a random jitter. Bounded mode is a different
product behavior with a 500 µs p95 budget.

## Why a shared clock is the whole design

Place the burst in a buffer, play the buffer on the laptop, and tell another
board “pulse 1000 should happen at time T”. Three unknowns remain:

1. When the operating system actually clocks that buffer out of the DAC.
2. The offset between T and the board’s timer.
3. The drift between the two oscillators, which is typically tens of ppm.
   Forty ppm is 2.4 µs of slip per second, or 8.6 ms after an hour, if
   nothing corrects it. The correction itself has to be applied without
   moving an edge by a visible jump.

`AudioContext.outputLatency` and `baseLatency` are estimates. The as-built
site does not read them. They are not a calibration.

PTP (IEEE 1588) and its cousins (gPTP, NTP) estimate the offset of two
clocks by timestamping packet departure and arrival. Hardware timestamping
on a NIC can get that offset under a microsecond on a quiet Ethernet. That
solves item 2 for two machines that both have timestamp hardware. It does
not move the laptop DAC onto that clock, and a browser will not give the
page a PTP hardware clock. ESP32 Wi-Fi software PTP is not in the exact
budget. BLE has no timestamp hardware path that meets one sample.

So PTP is specified only as an optional discipline between two wired panels
that are already slaved to the audio device. It is not the browser-to-lamp
mechanism.

## Exact path E1 — synthesize on the device

The host sends a plan and a start command. The MCU’s I2S peripheral and a
hardware timer, or the I2S callback itself, use one master clock.

Normative renderer loop, 48-sample blocks:

1. Pull 48 audio frames and 48 gate bits from the kernel.
2. Write the audio frames into the I2S DMA buffer.
3. Program the gate edges for those samples, delayed by `dac_pipeline_samples`.

`dac_pipeline_samples` is the number of samples already sitting in the DMA
and the DAC after the CPU writes them. Measure it once per board revision
with a scope or a loopback mic plus photodiode, store it in firmware config,
and re-measure when the DMA depth changes. The acceptance test compares the
acoustic onset with the optical onset, not the GPIO instruction with a log
line.

The start command means “begin at the next DMA block boundary”, not “begin
when the USB packet arrived”. Human reaction time does not care about the
sub-millisecond start uncertainty. The lock inside the session does.

E1 has no PLL in the audio path. Do not also slew the sample period to match
the host. The host is not playing the sound.

## Exact path E2 — the device is the sound card

USB full-speed frames are 1 ms. At 48 kHz a frame holds 48 samples. The
device is the USB Audio clock master so the host rate-matches to the MCU
oscillator. Headphones plug into the MCU’s DAC. Laptop speakers are out of
this path; using them makes the session bounded or audio-only.

Each frame on the vendor interface, after the control channel has armed the
plan:

| Field | Type | Meaning |
| --- | --- | --- |
| frame_index | uint32 LE | starts at 0, increases by 1 |
| channel_count | uint8 | 1 or 2 |
| reserved | uint8 | 0 |
| audio | int16 LE, 48 times channel_count | samples |
| gate | 6 bytes | 48 bits, bit 0 of byte 0 is sample 0, bit significance little-endian inside the byte |

The device writes `audio` to the DAC and shifts the gate bits out with the
same `dac_pipeline_samples` delay. A gap in `frame_index` is a fault, not a
concealment that invents flashes.

The LSB-of-the-audio-sample trick is not the v1 mechanism. Operating system
mixers resample and dither, and a resampled LSB is no longer a gate. A
private vendor interface avoids the mixer. OS-facing USB Audio Class can be
added later for listening tests; the gate still travels on the vendor
interface, or the device runs E1.

Chromium `setSinkId` is not an exact-mode implementation. It can point
ordinary audio at a USB speaker. It does not provide a sideband for the
gate unless the samples are bit-transparent, which REQ-SYNC-002 does not
assume.

## Bounded path B — a lamp with its own oscillator

Use this when the lamp cannot sit on the audio clock. The audio player,
whether the MCU in E1 or the bridge, is the time source. The lamp is a
follower.

At 10 Hz the source sends:

| Field | Type | Meaning |
| --- | --- | --- |
| plan_crc32 | uint32 LE | CRC-32 of the canonical plan bytes |
| pulse_index | uint32 LE | the next burst the source will emit |
| source_time_us | uint32 LE | source time of that burst’s rising edge, wrapping at 2^32 |
| source_rate_ppm | int32 LE | source estimate of its own oscillator versus nominal, for diagnostics |

The lamp’s PLL:

- Free-runs at `period_samples` of its own 48 kHz timer when no frame has
  arrived.
- On a frame, computes the error between its predicted edge and
  `source_time_us`, after subtracting a constant `lamp_latency_us` measured
  in calibration.
- Slews the next off-interval by at most 50 µs. It does not jump a rising
  edge.
- Drops frames whose `plan_crc32` does not match the armed plan.
- If no valid frame arrives for 250 ms, forces the pin off.
- If the absolute error after slew limiting would stay above 2 ms, forces
  the pin off and reports `bounded` failure.

The UI shows the live error when the device reports it. A session with no
completed calibration cannot display “synced”. It can display “uncalibrated”.

`lamp_latency_us` is the sum of transport delay and optical delay the user
wants. BrainWAVE notes that auditory and visual neural latencies differ and
that a deliberate phase offset is a research variable. That offset is
`phase_offset_us` in the plan, not a fudge factor hidden in the PLL. Keep
calibration (measure the path) separate from the experimental offset (a
value the plan asked for).

## Control transports and what they are good for

| Transport | Use | Do not use for |
| --- | --- | --- |
| USB vendor, 1 ms frames | E2 media | a laptop-speaker session |
| USB CDC / Web Serial | plans, start, stop, status, and path B sync frames if the bridge is the writer | bit-accurate PCM |
| WebSocket to the bridge on loopback | the browser’s control channel | anything bound to a non-loopback interface |
| WebSocket to the MCU on Wi-Fi | plans and status on a home network for E1 | PCM, and path B sync unless the measured p95 meets REQ-SYNC-004 |
| Web Bluetooth GATT | plans and status from Android Chrome to an E1 device | notifications as a sample clock. Connection-interval jitter is orders of magnitude above one sample |
| IEEE 1588 | two Ethernet lamps slaved to an E1 grandmaster that has hardware timestamps | the browser, and Wi-Fi |

Web Bluetooth UUIDs are frozen so a later stack does not invent new ones:

| Role | UUID |
| --- | --- |
| Service | `ffcc0978-65cc-504b-a70f-630bd8d351c9` |
| Control characteristic, write | `34d6cf8b-a75b-52da-862b-7332d9ba88b0` |
| Status characteristic, notify | `50b2a87c-8e9f-5e9c-81c4-2f48b82e9064` |
| Sync characteristic, write-without-response | `9f346aff-8dd1-5b9a-90bd-ad200c254fbc` |

They were generated as UUID v5 names under the upstream commit
`78f38137-e90f-1353-cc8a-4117d0d62b49`. Do not replace them with randomly
typed values.

iOS Safari cannot open these device APIs. iOS users get path A, or an E1
device that was armed by something else and then runs alone.

## Calibration procedure

Record this procedure in the firmware tranche and run it before any firmware
version is marked capable of `exact_device` or `exact_usb`.

1. Render a 10 s `research_v1` MIT plan with noise off, breaks off, fade 0,
   threshold 0, so every burst is present from sample 0.
2. Put a microphone on the headphone output and a photodiode on the LED.
3. Capture both on one two-channel scope, or one stereo audio interface whose
   channels are known to share a clock. A photodiode into a line input is
   enough if the pulse is visible.
4. Measure the delay from the acoustic envelope onset to the optical onset
   for at least 100 bursts spread over the 10 s.
5. The mean delay is the pipeline compensation target. The peak-to-peak
   variation of that delay must be ≤ one sample (20.8 µs) for exact mode.
6. Store the integer sample compensation that brings the mean inside one
   sample. Repeat at minute 0 and minute 60 of a soak. The mean must not
   walk by more than one sample.

Bounded-mode calibration is the same measurement, with the budget from
REQ-SYNC-004. Record the p95 and the maximum. If the maximum exceeds 2 ms,
the transport is illegal for path B and the firmware must refuse to arm
bounded mode on it.

## Several badges

When more than one board is in the room, the conductor’s DAC and its own
lamp stay on path E1. Every other lamp uses the appointment clock in
[14-network-time.md](14-network-time.md): SNTP to start, PTPv2 only if that
node can timestamp Ethernet, and a software servo on the CYD’s Wi-Fi.
Packets name a future TAI time. They do not carry the waveform, and E1.31
does not create the edges.

The PLL in path B is what remains for a follower that cannot keep that
timeline at all.

## What the UI is allowed to say

| Device report | Label |
| --- | --- |
| `exact_device` or `exact_usb`, and this firmware’s bench sheet is present | Phase-locked on the device clock |
| `bounded`, error reported, under budget | Approximate sync, showing the live error |
| `bounded`, uncalibrated or over budget | Light stopped, sync out of tolerance |
| `scheduled`, error estimate inside budget | Scheduled, showing the live ±µs. This is a lamp, not the word phase-locked |
| `scheduled`, estimate outside budget | Light stopped, clock not tight enough |
| `none`, or no device | Audio only |

The page must not say phase-locked because a WebSocket connected.
