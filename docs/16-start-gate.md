# Start gate

Planning is far enough along to write code. This page is the freeze. A new
idea lands in a later tranche. It does not reopen this list.

## Ready

- Stimulus math, vectors, and the oracle check.
- Requirements with IDs, tests, and tranches.
- CYD pin plan, TSF schedule, sync slate, stop button, quiet channel,
  filter sentence, and SPL note.
- Safety copy rules and the ban on treatment language.

`python tools/oracle/stimulus_oracle.py check` passes. That is the gate
for the kernel. The slate does not wait on it.

## Where the code goes

| Work | Tree |
| --- | --- |
| Spec, oracle, vectors | this folder, `C:\src\misc\40hz-gamma` |
| Kernel and web app | `packages/stimulus-kernel` and `apps/web` here, when those tranches start |
| Badge firmware | a new `firmware/cyd` here, copied from `dashcdg_badge` at the moment the slate starts |

Do not develop gamma inside `C:\src\dashcdg`. That tree stays the karaoke
badge. The copy keeps FreeRTOS, LVGL, the display, the touch stack, the
amp, and the DAC writer, and deletes the karaoke pieces named in
[13-cyd-badge.md](13-cyd-badge.md).

## First slices

Two slices, and they can run at the same time.

1. **Slate on the two CYDs.** [15-sync-slate.md](15-sync-slate.md), the IO0
   stop, the pin header, and the quiet-channel scan. No audio kernel.
2. **Kernel.** Tranche 1 only. Vectors pass. No GPIO and no Wi-Fi.

The session screen, the filter sentence, and the SPL note wait until a
session exists. USB audio, sACN, OSC, mesh, and monitor-mode timestamps
wait until the slate has been filmed and the kernel matches the vectors.

## Defaults that keep work moving

| Open point | Default | Change it when |
| --- | --- | --- |
| GPIO21 free | Treat it as the lamp. Do not drive it until a meter shows it is unused | The meter says otherwise. Pick another free pin that is not 18, 19, or 23 |
| 10 nF shunt | Still fitted. `gamma_shunt_removed` is false. Clicks are the first sound | The board is actually modified |
| TSF error | Unknown. The slate may show a multi-millisecond miss. It cannot pass the 200 µs row | A scope run of TST-BENCH-006 |
| First radio | Standalone SoftAP, no home router | You want OTA or the browser on the same LAN |
| License | MIT, copyright 2026 Andrew Green, in `LICENSE`. Separate from the upstream POC | You choose a different license |
| Public repo | https://github.com/andrew867/40hz-gamma is public. Safety copy is in `docs/09-safety.md` and `NOTICE.md` | You make the repository private |

## Risks already accepted

| Risk | What we do about it |
| --- | --- |
| The speaker filter dulls 10 kHz | Say so on the MIT screen. Bring clicks up first |
| No oscilloscope yet | Film the slate. Do not record that film as a microsecond pass |
| DAC clock and Wi-Fi clock differ | Restamp the schedule anchor every packet |
| ESP32 RAM is tight with LVGL and Wi-Fi | Keep the badge’s 16-line display buffers. The slate is the memory test |
| A second conductor splits the room | Same group id is a fault. Lamps go dark |
| Copy drifts into treatment claims | TST-WEB-004 word scan, including on-device strings |

## Not worth more planning

A RACI chart, a regulated-device process, more protocols, and another
clock design. Those wait until a tranche exit says the current one is done.

## Before the first commit of code

- Oracle check is green.
- `vendor/` stays gitignored. Do not commit the minified website bundle.
- Firmware, when it appears, is `firmware/cyd`, not a dirty karaoke tree.
- The PR names its tranche and requirement IDs, as in
  [12-agent-guide.md](12-agent-guide.md).
