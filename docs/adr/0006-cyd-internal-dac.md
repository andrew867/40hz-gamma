# ADR 0006 — CYD badge, internal mono DAC, 48 kHz

## Status

Accepted.

## Context

The hardware on hand is the Freenove ESP32 CYD 3.2 inch with the DashCDG
daughterboard: ST7789, XPT2046, SC8002B amp, GPIO26 analog feed. The
firmware already runs ESP-IDF 5.5 `dac_continuous` into the 8-bit DAC.
GPIO25, the other DAC pin, is I2C SCL. The speaker network has a lowpass
near 3.4 kHz. The ESP32-S3 has no internal DAC, so the earlier “S3 plus
I2S” sketch does not match this board.

## Decision

- Fork `dashcdg_badge`. Keep FreeRTOS, LVGL, the display and touch stack,
  the amp and backlight, and the DAC DMA writer. Strip karaoke, CDG, and
  the speech codecs.
- Gamma audio is mono 48 kHz through `dac_continuous` on GPIO26.
- The I2S peripheral is reserved for a future external DAC. It is not how
  the internal DAC is driven on IDF 5.5.
- The stimulus MOSFET is a free GPIO, proposed GPIO21, confirmed on the
  bench. The RGB LED is status only. GPIO18, GPIO19, and GPIO23 stay free
  for a later I2S DAC and are not lamp alternates.
- Binaural and a clean 10 kHz sine wait on an external stereo I2S DAC, or
  on a filter change for the sine. Click trains are the unmodified-hardware
  audio bring-up.

## Consequences

- Tranche 4 builds on the badge tree rather than a blank IDF project.
- Exact mode on this board means the lamp edge matches the samples written
  to the DAC, and matches the acoustic envelope to the extent the analog
  filter passes it.
- 96 kHz stays legal in the pure kernel and illegal on this firmware.
