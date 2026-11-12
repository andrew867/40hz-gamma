# Document index

Read [the repository README](../README.md) for the one-page answer. Then use
this index. An implementer who is allowed to write code starts at
[12-agent-guide.md](12-agent-guide.md) and [11-tranches.md](11-tranches.md).

| Doc | Contents |
| --- | --- |
| [01-as-built.md](01-as-built.md) | What the Python script and the live site do, including the bugs worth not copying |
| [02-requirements.md](02-requirements.md) | Numbered requirements. Tests and tranches cite these IDs |
| [03-stimulus-spec.md](03-stimulus-spec.md) | Normative sample math for audio and the light gate |
| [04-architecture.md](04-architecture.md) | Components, trust boundaries, and which process owns the sample clock |
| [05-time-sync.md](05-time-sync.md) | Clock domains, PTP, USB, Bluetooth, WebSocket, and the error budget |
| [06-protocols.md](06-protocols.md) | Session plan, binary frames, BLE layout, sync frames |
| [07-firmware.md](07-firmware.md) | Device state machine, DAC DMA, GPIO, watchdog |
| [13-cyd-badge.md](13-cyd-badge.md) | Freenove CYD badge: pins, internal DAC, what to keep from DashCDG |
| [14-network-time.md](14-network-time.md) | TAI appointments, TSF, PTP, OSC timetags, what sACN is for |
| [15-sync-slate.md](15-sync-slate.md) | On-screen clock, backlight flash, and the slo-mo compare |
| [16-start-gate.md](16-start-gate.md) | What is frozen, what the first slices are, and what can wait |
| [08-web-and-bridge.md](08-web-and-bridge.md) | Browser app and the localhost bridge |
| [09-safety.md](09-safety.md) | Level, flicker, failure, and claim rules |
| [10-test-plan.md](10-test-plan.md) | Vector tests, simulated-device tests, bench tests |
| [11-tranches.md](11-tranches.md) | Phased delivery with entry and exit gates |
| [12-agent-guide.md](12-agent-guide.md) | How a later developer or model implements one tranche |

Architecture decisions:

| ADR | Decision |
| --- | --- |
| [0001](adr/0001-one-clock-for-exact-lock.md) | Exact lock means one sample clock for the DAC and the pin |
| [0002](adr/0002-two-exact-paths.md) | Ship on-device synthesis and a USB audio device, in that priority order |
| [0003](adr/0003-bounded-mode-is-labeled.md) | Split lamps use a PLL and are never labeled phase-locked |
| [0004](adr/0004-research-profile-defaults.md) | `research_v1` is the default; `web_v1` is a compatibility profile |
| [0005](adr/0005-not-a-medical-device.md) | No diagnostic, therapeutic, or dosage claims in UI or logs |
| [0006](adr/0006-cyd-internal-dac.md) | First hardware is the CYD badge, mono internal DAC at 48 kHz |
| [0007](adr/0007-scheduled-network-edges.md) | Multi-badge lamps keep appointments; sACN does not make the edges |
| [0008](adr/0008-tsf-not-mesh.md) | Two CYDs share the Wi-Fi TSF. Mesh and monitor mode stay in the lab |

Schemas live in `../schemas/`. Vectors live in `../vectors/`.

## Glossary

| Term | Meaning |
| --- | --- |
| Burst | One 1 ms (or 7 ms) audible pulse. Forty bursts per second is the 40 Hz rhythm |
| Carrier | The tone inside a burst. 10 kHz for the MIT sine protocol. The ear hears this, not a 40 Hz tone |
| Gate | Logical 1 while the LED should be on, before polarity is applied |
| Exact mode | DAC and gate share a sample clock. Residual error after calibration is at most one sample |
| Bounded mode | A second device slews a local timer toward the host. Target 500 µs p95 |
| Profile `web_v1` | Reproduce the deployed website’s generator, including its quirks |
| Profile `research_v1` | Normative successor. 48 kHz, seeded noise, fixed stimulus peak, noise ducks in breaks |
| Plan | A `gamma.session_plan.v1` JSON document. Volume is not part of the sample identity |
| Oracle | `tools/oracle/stimulus_oracle.py`, the reference math |
