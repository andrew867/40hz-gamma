# CYD badge hardware

The first exact-mode device is the Freenove ESP32 CYD 3.2 inch badge
already running DashCDG, not a new ESP32-S3 board. The application tree to
fork is `C:\src\dashcdg\platform\espidf\projects\dashcdg_badge`. The pin
header in that tree is the authority for this board. If a silk revision
disagrees with `board_cyd_freenove_32.h` or `board_badge_hw.h`, the header
that matches the board on the bench wins, and this document is updated in
the same change.

## What the board actually is

| Item | Fact |
| --- | --- |
| SoC | Original ESP32 (Xtensa), the chip the badge project builds. Not ESP32-S3. The S3 has no internal DAC |
| Display | ST7789, physical 240×320, LVGL landscape 320×240 |
| Touch | XPT2046 on the same SPI bus, with the calibration store already in the badge |
| Speaker | GPIO26 into the badge analog network, then an SC8002B class-D amp. Shutdown is GPIO4, high = muted |
| IDF | 5.5-era `dac_continuous` API, as included by `platform_hw.c` |
| Radio | Wi-Fi. This module has no Ethernet jack and no PTP hardware timestamp path |
| Sample rate | 48 kHz only for gamma sessions |

Mono is the v1 audio path. GPIO25 is the second internal DAC pin and it is
already I2C SCL (`DASHCDG_HW_GPIO_I2C_SCL`). Moving I2C to free a second DAC
channel is not worth it. Binaural playback waits for an external stereo I2S
DAC.

## Internal DAC, and why it is not the I2S peripheral

The badge already plays PCM by DMA into the 8-bit DAC on GPIO26:

- API: `dac_continuous_new_channels` / `dac_continuous_write`
- Channel mask: `DAC_CHANNEL_MASK_CH1` (GPIO26)
- Rate planner: `dashcdg_dac_rate_plan_resolve`. A push rate of 48000 is at
  or above `DAC_CYD_MIN_SAFE_HZ` (24000), so the DMA clock is 48000 with
  ratio 1:1
- Bytes are 8-bit. The karaoke path converts s16 to that width before the
  write

That is the supported ESP-IDF 5.5 path. The older mode that wired the I2S
peripheral into the internal DAC is a legacy driver. Gamma firmware uses
`dac_continuous` at 48000 Hz, one channel, and does not open the I2S
peripheral for the onboard speaker.

An external I2S DAC (PCM5102-class or similar, with a maintained ESP-IDF
`i2s` example) is the upgrade when a session needs a clean 10 kHz sine or
two headphone channels. The kernel does not change. Only the sink behind
`render()` changes. Do not block Tranche 4 on buying that part. MIT and
click sessions are mono and can be brought up on GPIO26.

8-bit audio has a coarse staircase. A 10 kHz sine at 48 kHz has 4.8 samples
per cycle, so the carrier will not look like a lab generator. The 40 Hz
rhythm is still in the sample grid. The bench for exact mode compares the
burst envelope at the speaker with the lamp edge. It does not require a
low-distortion sine.

## The reconstruction filter will quiet a 10 kHz carrier

`board_badge_hw.h` documents the speaker feed as GPIO26, then 4.7 kΩ, then
a 10 nF shunt to ground (plus 100 pF), then a coupling cap into the
SC8002B. A 4.7 kΩ / 10 nF pole sits near 3.4 kHz. A 10 kHz burst is well
down that slope. The existing network was built for voice and karaoke, not
for this carrier.

Bring-up rule:

| Protocol on this filter | Expectation |
| --- | --- |
| Click train | Usable. Enough energy remains below a few kHz to hear the 40 Hz rhythm |
| MIT 10 kHz sine | Quiet or dull until the 10 nF shunt is lifted, reduced, or the DAC is tapped ahead of it |
| Binaural | Not on this mono, filtered path |

Tranche 4 may ship the click protocol on the unmodified badge. The MIT
protocol’s bench sheet includes a note of the filter state. A failed MIT
bench because the shunt is still fitted is a hardware note, not a kernel
bug. The lamp edge is still tested against the samples written to the DAC,
and against the acoustic envelope once the filter passes the carrier.

## Lamp pin

The RGB LED on GPIO16 / GPIO22 / GPIO17 is a status indicator. The cathodes
are active-low through 1 kΩ. It is the sync-quality lamp in the UI sense
(color), not the 40 Hz stimulus. Breathing that LED at 40 Hz would also
fight the existing PWM personality.

Proposed stimulus GPIO: **GPIO21**, active high, into the MOSFET the
hardware owner adds. Nothing in the badge tree references GPIO21, GPIO18,
GPIO19, or GPIO23. GPIO21 is not an ESP32 strapping pin. Confirm with a
meter that the assembled badge does not use it, then set
`GAMMA_GPIO_LAMP` to that number. If 21 is taken, pick another free GPIO
on the bench. Do not take GPIO26, GPIO25, GPIO4, GPIO0, GPIO12, GPIO15,
or the three I2S pins below.

These three stay reserved for a later external DAC. The firmware does not
drive them. They are inputs, not the lamp, not SPI, and not the status LED.

| Signal | GPIO | Later use |
| --- | --- | --- |
| I2S BCLK | 18 | bit clock |
| I2S DOUT | 19 | data to the DAC |
| I2S WS | 23 | word select / LRCK |

A PCM5102-class board uses that map. Changing the map is a one-line header
edit before the board is built, not a change to the kernel.

The pin contract in [07-firmware.md](07-firmware.md) still applies: off at
boot, off on every fault, one edge pair per burst.

## What to keep from the badge tree

| Keep | Why |
| --- | --- |
| `board_cyd_freenove_32.h`, `board_badge_hw.h` | Pin map, LCD timings, touch raw bounds, amp polarity, backlight |
| `display_lvgl.c`, `touch_cal_store.c`, `touch_cal_ui.c` | ST7789, XPT2046, LVGL port, calibration. Partial buffers stay at 16 lines, full refresh stays off |
| `nav.c`, `home_ui.c`, `topbar_ui.c`, `settings_ui.c`, `display_ui.c`, `wifi_touch_ui.c` | Shell, tiles, Wi-Fi, backlight and idle behavior |
| `platform_hw.c` pieces for backlight PWM, amp shutdown, IO0, idle dim, battery cache, I2C bus | Already debugged. Amp mute-before-DAC-teardown stays; skipping it pops the speaker |
| `dac_continuous` open/write/stop and the route-owner enum | Becomes `NONE` / `GAMMA_SESSION`. One owner of GPIO26 |
| `vbat_sense.c`, `battery_label.c` | Pack voltage on the status dock |
| `badge_exec` health bits | Boot and fault reporting, with karaoke subsystem names removed |
| FreeRTOS task split already in the tree | LVGL on the port task, hardware on the platform task, a new gamma render task at higher priority than Wi-Fi and LVGL |

LVGL calls stay on the LVGL task, under `lvgl_port_lock`, the same rule
`display_lvgl.h` already states.

## What to strip

Remove these from the gamma firmware target. Leave them in the DashCDG tree.

| Strip | Why |
| --- | --- |
| `karaoke_ui.*`, `karaoke_settings_ui.*`, `badge_rx*.c`, `badge_rx*.h` | CDG/karaoke session, multicast media, overlay blit |
| `badge_cdg_rgb565.*`, `badge_sp_blit_worker.*` | CDG frame blit |
| `components/dashcdg_adf_amr`, `components/dashcdg_rx_audio`, QCELP/AMR | Speech codecs |
| `audio_lab_ui.*`, `badge_lab_ym.*` | YM synth toy |
| A2DP route in `audio_output.*` | Not a gamma sink. Bluetooth audio jitter is the opposite of this spec |
| CDG-specific idle hooks (`note_karaoke_mcast_rx`, stream-ok LED personality) | Replace with “session running” so the screen does not sleep during a 60 minute run, and does sleep when the session stops |

`audio_mgr.c` is replaced by the gamma kernel’s `render()` into the existing
DAC writer. Do not feed the kernel through the karaoke rate-change path.
Gamma opens the DAC once at 48000 and holds it for the session.

## Tasks

| Task | Priority | Job |
| --- | --- | --- |
| LVGL / `esp_lvgl_port` | as today | UI only |
| Platform | as today | backlight, amp, button, idle, battery |
| Gamma render | above Wi-Fi and LVGL | `kernel.render(48)` then `dac_continuous_write`, and schedule the lamp from the same sample counter |
| Wi-Fi | below render | control, SNTP, the clock servo, schedule packets |
| Idle | low | must not dim the stimulus or stop the DAC while `state == running`. Dimming the backlight is allowed. Stopping the render task is not |

The render task uses a static buffer. It does not allocate. A DMA underrun
faults the session and forces the lamp off, same as [07-firmware.md](07-firmware.md).

## On-device UI

The badge can run a session with no laptop after the plan is on the device.

Screens, reusing the tile shell:

1. Home: Start, protocol (MIT sine / click), duration, noise, breaks, lamp on/off.
2. Running: remaining time from the sample counter, lamp state, clock-sync state, stop.
3. Settings: volume (amp gain / digital gain), backlight, Wi-Fi, touch cal, lamp GPIO confirmation, role (conductor or lamp).
4. Sync slate and statistics, specified in [15-sync-slate.md](15-sync-slate.md). This screen is the no-scope check and may be built before the stimulus kernel.

The photosensitivity acknowledgement is a full-screen button before the
first light-enabled start after boot. It is not remembered as a permanent
“do not ask again” in v1. Stopping the session does not require the
acknowledgement again until the next boot.

The browser remains the editor for long plans and the audio-only fallback.
The badge does not need the browser to be open during the hour.

## Roles

| Role | Audio | Lamp | Clock |
| --- | --- | --- | --- |
| Conductor | yes, local DAC | yes, same sample counter | publishes the timeline |
| Lamp | no | yes, at scheduled times | follows the conductor |
| Alone | yes | yes | no network |

A lamp does not play the stimulus through its speaker. Several delayed
copies of the same bursts would comb-filter in the room and none of them
would match the conductor’s edges. Lamp speakers stay on the amp-shutdown
pin.

## Stop button

IO0 already sleeps the badge on a hold of about 1.4 s (`USER_BTN_SLEEP_FRAMES`
in the DashCDG platform task, 35 ticks at 40 ms). Gamma keeps that gesture
and that task. While a session or the sync slate is active, the same hold
does this before the existing sleep fade, and it does it without taking
the LVGL lock:

1. Drive the lamp GPIO to the electrical off level.
2. Stop the DAC writer and mute the amp (shutdown pin high).
3. Mark the session stopped, reason `button`.
4. Then run the existing sleep path.

A stuck screen is not a reason the lamp stays on. Releasing the button
after sleep still uses the existing wake behavior.

## Quiet channel for the standalone access point

Before the conductor opens the SoftAP, it spends one scan as a station.
It considers only channels 1, 6, and 11. The score for a channel is the
sum of the RSSI values of the access points heard on it, treating a missing
RSSI as −100 dBm. The lowest score wins. Ties prefer 1, then 6, then 11.
The SoftAP stays on that channel until the conductor is stopped. It does
not rescan during a session. The statistics page shows the chosen channel
and the other two scores.

Infrastructure mode joins the saved home AP and does not override that
AP’s channel.

## What the session screen says about the tone

The badge speaker network rolls off near 3.4 kHz while the 10 nF shunt is
fitted. NVS flag `gamma_shunt_removed` defaults to false.

| Protocol | Flag | Line on the session screen |
| --- | --- | --- |
| Click | false | Clicks are the right first sound on an unmodified badge. |
| MIT sine | false | This speaker network cuts above about 3 kHz. The 10 kHz tone will sound dull until the 10 nF shunt is removed. |
| MIT sine | true | Filter bypass recorded. The 10 kHz tone should be audible. |
| Click | true | Clicks. Filter bypass is recorded and is not required for this protocol. |

The flag is a setting the user turns on after they change the board. The
firmware does not detect the capacitor.

## Volume note

Settings offers “Save SPL note”. It stores, in NVS, the current slider
percent, a place (`arm_length` or `headphones`), an integer dB SPL from
50 to 90, the date, and an optional note of at most 40 characters. The
session screen shows one read-only line, for example “Saved: 70% ≈ 65 dB
at arm’s length, 2026-11-12”. Saving does not move the slider. The line
is the user’s note from a meter, not a measurement the device made. The
web app stores the same fields in local storage and shows the same
sentence. The note is not part of the plan hash.
