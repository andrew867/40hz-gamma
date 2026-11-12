# ADR 0003 — Bounded mode is labeled approximate

## Status

Accepted. Tranche 0.

## Context

A second lamp, or a lamp watching serial while the laptop DAC plays, can be
useful. It cannot honestly use the exact-mode budget. PTP can discipline
two Ethernet clocks and still leave the browser DAC on another clock.

## Decision

Bounded mode slews a follower by at most 50 µs per correction, targets
500 µs at the 95th percentile, and forces the lamp off past 2 ms of error
or 250 ms without a sync frame. The UI may say phase-locked only for
`exact_device` and `exact_usb` with a bench sheet. PTP is optional and only
between panels that share the audio device’s clock domain through hardware
timestamps.

## Consequences

- Tranche 5 is allowed to ship a follower.
- Tranche 5 is not allowed to reuse the exact-mode label.
- A failed sync is darkness, not a best-effort flicker.
