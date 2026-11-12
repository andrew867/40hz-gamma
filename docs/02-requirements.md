# Requirements

IDs in this file are stable. A tranche may satisfy an ID or leave it for a
later tranche. It must not silently redefine one. Changes are a documentation
edit in the same pull request as the code, with the old sentence kept under a
“Changed” note for one revision.

Priority is P0 (cannot ship the tranche that owns it without this) or P1
(required before calling the product complete).

## Kernel

| ID | P | Statement |
| --- | --- | --- |
| REQ-KERNEL-001 | P0 | The stimulus engine is a pure function of `(plan, sample_rate, sample_index)`. It performs no I/O, reads no clock, and allocates no audio device |
| REQ-KERNEL-002 | P0 | `render(start_sample, frame_count)` returns audio frames and a logical gate bit per sample. Calling it twice with the same arguments returns the same samples |
| REQ-KERNEL-003 | P0 | Sample index 0 is the start of the session timeline. Negative indexes are out of range. Indexes at or past `floor(duration_s * sample_rate)` are silence and gate 0 |
| REQ-KERNEL-004 | P0 | Ports match `vectors/` within the tolerances in [10-test-plan.md](10-test-plan.md) |
| REQ-KERNEL-005 | P0 | `research_v1` rejects a plan whose `sample_rate / repetition_hz` is not an integer, or whose MIT pulse length `0.001 * sample_rate` is not an integer |
| REQ-KERNEL-006 | P1 | The engine streams. Generating 60 s at 48 kHz mono does not require a second full-session buffer for the signal |

## Stimulus

| ID | P | Statement |
| --- | --- | --- |
| REQ-STIM-001 | P0 | MIT sine in `research_v1` at 48 kHz has period 1200 samples and pulse length 48 samples. Achieved repetition is 40 Hz exactly |
| REQ-STIM-002 | P0 | The audible carrier inside that pulse is 10 kHz. The pin does not toggle at 10 kHz |
| REQ-STIM-003 | P0 | Default edge for `research_v1` MIT sine is `raised_cosine_150us`, matching the site. `hard` is available and matches `template_hard_gate` |
| REQ-STIM-004 | P0 | Click trains use one seeded template per plan, Hann-shaped, length `floor(0.007 * sample_rate)`, reused at every period |
| REQ-STIM-005 | P0 | Binaural `research_v1` is left 200 Hz and right 240 Hz for the whole session, multiplied by the envelope |
| REQ-STIM-006 | P0 | Breaks in both profiles sit at the end of each interval. Placement `start` exists only to reproduce the Python script and is not a UI default |
| REQ-STIM-007 | P0 | Session fade is linear, default 10 s, applied as a gain on stimulus and, when `follows_envelope` is true, on noise |
| REQ-STIM-008 | P0 | `research_v1` noise uses the Kellet filter and `xorshift32`, then RMS-scales to `level_rms`. It is multiplied by the envelope when `follows_envelope` is true |
| REQ-STIM-009 | P0 | `fixed_stimulus` scales the dry stimulus so its peak is `stimulus_peak` (default 0.95) before noise is added. If the mix would exceed 0.95, the mix is scaled down and the engine records that it limited |
| REQ-STIM-010 | P1 | `web_v1` reproduces Q2, Q3, and the smoothed sine template from [01-as-built.md](01-as-built.md), including noise that ignores the break gain and a final peak scale of 0.95 |
| REQ-STIM-011 | P0 | Playback volume is a device gain. It is not baked into rendered samples and it is not part of the plan hash used for caches |

## Light

| ID | P | Statement |
| --- | --- | --- |
| REQ-LIGHT-001 | P0 | `audio_envelope` is logical 1 only when the envelope is greater than or equal to `threshold` and the sample offset inside the period is `< pulse_samples` |
| REQ-LIGHT-002 | P0 | `visual_50` is logical 1 on the first `round(period * duty)` samples of each period, under the same envelope threshold. Default duty is 0.5. At 48 kHz that is 600 on, 600 off |
| REQ-LIGHT-003 | P0 | `phase_offset_us` shifts the gate later when positive. The shift in samples is `round(phase_offset_us * 1e-6 * sample_rate)`. Samples before 0 are off |
| REQ-LIGHT-004 | P0 | Binaural has no acoustic burst. Its gate uses `visual_50` even if the plan says `audio_envelope`, and the status text says so |
| REQ-LIGHT-005 | P0 | Logical 1 means “LED on” before polarity. `active_high` drives the GPIO high for on. `active_low` drives it low for on. Idle, stop, fault, and disconnect use the electrical off level |
| REQ-LIGHT-006 | P0 | `max_duty` above 0.5 is rejected in v1. A plan whose expected on-time exceeds `max_duty` is rejected |
| REQ-LIGHT-007 | P0 | While the envelope is below threshold, including the deep part of a break and the first half of the default 10 s fade, the gate stays 0 |
| REQ-LIGHT-008 | P1 | The gate bit is available to the DAC path in the same frame as the audio sample it belongs to |

## Sync

| ID | P | Statement |
| --- | --- | --- |
| REQ-SYNC-001 | P0 | Exact mode shares one sample clock between the samples the listener hears and the gate. After the calibrated pipeline delay, the rising logical edge and the first sample of that burst differ by at most one sample at 48 kHz, measured at the analog outputs, and that residual does not grow across 60 minutes |
| REQ-SYNC-002 | P0 | Two implementations qualify as exact. E1: the MCU synthesizes audio and gate. E2: the MCU is the USB playback device, headphones are plugged into it, and each frame contains audio plus gate bits |
| REQ-SYNC-003 | P0 | Browser timers, BLE notifications, WebSocket messages, and USB serial command streams are control planes or bounded-mode inputs. They are not exact mode |
| REQ-SYNC-004 | P0 | Bounded mode targets absolute edge error ≤ 500 µs for 95% of edges over 10 minutes after calibration, and never lets an edge through with absolute error > 2 ms. Beyond 2 ms the gate is forced off and the UI shows approximate-sync failure |
| REQ-SYNC-005 | P0 | The UI word “phase-locked” is reserved for a session whose device reports `sync_mode` of `exact_device` or `exact_usb` and whose bench record exists for that firmware version. Otherwise the UI says “approximate” or “audio only” |
| REQ-SYNC-006 | P1 | PTP is allowed only between networked panels that already share the audio device’s clock domain through a hardware timestamp path. The browser is not a PTP node |
| REQ-SYNC-007 | P0 | Loss of frames, loss of the link, or a stalled render task forces the electrical off level within 5 ms |

## Safety and product

| ID | P | Statement |
| --- | --- | --- |
| REQ-SAFE-001 | P0 | The product is described as an experimental research tool. Screens, logs, manifests, and firmware strings do not claim diagnosis, treatment, or prevention |
| REQ-SAFE-002 | P0 | Starting a session with `light.enabled` requires `photosensitivity_ack == true` in the current page load. The acknowledgement is not pre-checked |
| REQ-SAFE-003 | P0 | Default audible instructions tell the user to measure SPL and to stop on discomfort. The calibration tone uses the same peak as the stimulus |
| REQ-SAFE-004 | P0 | Session length in the UI cannot exceed 7200 s. The schema rejects larger plans |
| REQ-SAFE-005 | P0 | A failed device, a missing acknowledgement, or an invalid plan starts audio-only only when the user explicitly chooses audio-only. It does not start the light |
| REQ-SAFE-006 | P1 | Logs stay on the machine that ran the session. The client does not post plans or audio to a project server |
| REQ-SAFE-007 | P0 | Repetition other than 40 Hz is rejected unless the plan is marked experimental and the UI has shown the photosensitivity warning again for that value |

## Web, bridge, device

| ID | P | Statement |
| --- | --- | --- |
| REQ-WEB-001 | P0 | The web app can run a full audio session with no device attached, using the kernel in a worker, at the context sample rate when that rate is legal for the profile |
| REQ-WEB-002 | P0 | If the context rate is illegal for `research_v1`, the app tells the user and offers `web_v1` or the bridge. It does not quietly resample a 40 Hz grid |
| REQ-WEB-003 | P1 | Wake lock and Media Session metadata are requested for the duration of playback |
| REQ-WEB-004 | P0 | The page that offers a light shows the sync mode returned by the device. It does not infer exactness from “the socket is open” |
| REQ-BRIDGE-001 | P0 | The bridge listens on `127.0.0.1` only, on a fixed default port 8765, with a token printed at startup and required on the socket |
| REQ-BRIDGE-002 | P0 | The bridge is the owner of the USB device handle. The browser does not also open that handle |
| REQ-DEV-001 | P0 | Firmware powers up with the pin at the electrical off level and stays there through enumeration |
| REQ-DEV-002 | P0 | Firmware accepts a plan, arms, runs, stops, and faults as specified in [07-firmware.md](07-firmware.md) |
| REQ-DEV-003 | P0 | E1 firmware renders with the same kernel results as the vectors, at 48 kHz, in the audio callback or in a task fed by that callback |
| REQ-DEV-004 | P1 | E2 firmware plays USB frames to the DAC and applies gate bits delayed by the measured FIFO depth |
| REQ-HW-001 | P0 | The first firmware target is the CYD badge in [13-cyd-badge.md](13-cyd-badge.md): ESP32, `dac_continuous` mono, 48000 Hz, GPIO26. 96000 and 44100 are rejected on device |
| REQ-HW-002 | P0 | The stimulus lamp is a dedicated GPIO, proposed GPIO21 after a continuity check. The RGB LED is status only and is not driven at 40 Hz |
| REQ-HW-003 | P0 | The gamma render task is the only owner of the DAC route during a session. Karaoke, the audio lab, and A2DP are not linked into this firmware |
| REQ-HW-004 | P0 | A MIT session’s on-device UI states whether the ~3.4 kHz reconstruction filter is still in circuit. Click sessions may run with the filter fitted |
| REQ-HW-005 | P0 | An IO0 hold of about 1.4 s, handled in the platform task, forces the lamp off, stops the DAC, mutes the amp, and then follows the existing sleep path. It does not depend on LVGL |
| REQ-HW-006 | P0 | GPIO18, GPIO19, and GPIO23 are reserved for a future I2S DAC (BCLK, DOUT, WS). Firmware does not drive them. They are not lamp alternates |
| REQ-HW-007 | P0 | The session screen shows the four protocol/filter sentences in [13-cyd-badge.md](13-cyd-badge.md). `gamma_shunt_removed` defaults to false |
| REQ-HW-008 | P0 | The user can save one SPL note (slider percent, arm’s length or headphones, dB, date). The session screen shows it. Saving does not change gain, and the note is not in the plan hash |
| REQ-NET-001 | P0 | A lamp fires a network edge only at the conductor’s TAI time for that burst, and only when its clock-error estimate is inside the budget in [14-network-time.md](14-network-time.md) |
| REQ-NET-002 | P0 | An edge whose packet arrived with under 5 ms of lead, or whose time is already past, is skipped. The lamp does not fire late |
| REQ-NET-003 | P0 | 200 ms without a matching schedule packet forces the lamp off |
| REQ-NET-004 | P0 | sACN may force the lamp off or set a master enable. It does not generate 40 Hz edges |
| REQ-NET-005 | P1 | OSC bundles with future timetags are accepted by the conductor and republished as native schedule packets |
| REQ-NET-006 | P0 | Two conductors with the same group id refuse to publish and signal a fault. A follower plays audio only when its role is speaker, and then from the local kernel, not from a PCM stream |
| REQ-NET-007 | P0 | Standalone mode runs with the conductor as SoftAP and the follower as a station. No external access point is required for a session |
| REQ-NET-008 | P0 | While a session runs, Wi-Fi power save is off. Boards in the same BSS schedule edges from `esp_wifi_get_tsf_time` |
| REQ-NET-010 | P0 | Each schedule packet restamps `anchor_sample` from the live DAC sample counter and the TSF read taken with it. Followers discard older anchors. The conductor’s own lamp stays on the sample counter |
| REQ-NET-011 | P0 | A standalone conductor scans once and opens its SoftAP on channel 1, 6, or 11, whichever has the lowest summed RSSI. It does not rescan during a session |
| REQ-NET-009 | P0 | ESP-WIFI-MESH and promiscuous injection are not the session clock. A lab build of the sniffer path is allowed only after TST-BENCH-006 misses its target |
| REQ-DBG-001 | P0 | The badge has a sync slate per [15-sync-slate.md](15-sync-slate.md): centisecond digits, a 10 ms wheel, a checkmark with the failing reason, and a 2 ms backlight and rear-LED flash on the 100 ms TSF boundary, armed from a hardware timer |
| REQ-DBG-002 | P0 | The checkmark means the local link checks passed. The slate copy says the video checks milliseconds and does not check microseconds |
| REQ-DBG-003 | P1 | A statistics page lists the rows in [15-sync-slate.md](15-sync-slate.md), including beacon age, TSF-read p95, schedule loss, and skipped edges |

## Explicit non-requirements

- EEG, cameras, heart rate, or closed-loop adaptation
- An iOS native app. Safari has no WebUSB or Web Bluetooth here
- Streaming PCM over Wi-Fi or BLE and calling it exact
- Using E1.31 or Art-Net as the 40 Hz phase clock
- Hardware PTPv2 on the CYD module. That module has no Ethernet timestamp unit. PTPv2 is for a later wired node
- A 10 kHz square wave on the lamp pin
- Medical-device design control, IEC 62304, or an FDA filing. If that goal appears later, it is a new project with its own requirements
- Choosing the LED, the MOSFET, or the optical diffuser. The pin contract is in [07-firmware.md](07-firmware.md). The electrical load is the hardware owner’s problem
