# ADR 0002 — Two exact paths, device synthesis first

## Status

Accepted. Tranche 0.

## Context

Some sessions should be generated on the microcontroller so the host is only
a remote control. Some sessions should be generated on the host so the same
kernel the browser uses is what the DAC plays. Both can be exact if the DAC
is on the microcontroller.

Sending PCM over Wi-Fi or telling the lamp the wall-clock time of the next
burst does not put the laptop speaker and the lamp on one clock.

## Decision

- E1, preferred: the MCU runs the kernel into I2S and the GPIO.
- E2, also exact: a localhost bridge sends 1 ms frames of int16 audio plus
  gate bits to a vendor USB interface, and the headphones are plugged into
  the device.
- The browser does not hold the USB device in v1. The bridge does.
- Laptop speakers are audio-only or, with a separate lamp, bounded mode.

## Consequences

- Tranche 4 (E1) is the path to recommend to a user who wants the lamp.
- Tranche 3 (E2) exists so host-side rendering can still be bit-faithful.
- Web Bluetooth is a control plane for E1, not a third exact path.
