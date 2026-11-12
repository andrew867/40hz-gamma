# ADR 0001 — Exact lock uses one sample clock

## Status

Accepted. Tranche 0.

## Context

The audible event is a 1 ms burst on a 25 ms grid. The lamp must rise on
that same burst. The public web app plays a pre-rendered buffer on
`AudioContext` and has no second device. Host timers, BLE notifications,
and Wi-Fi sockets jitter by milliseconds. A 40 ppm oscillator slip walks
several milliseconds per hour if it is not corrected, and a correction that
jumps an edge is itself a failed lock.

## Decision

Exact mode is defined as one physical sample clock driving both the DAC the
listener hears and the gate. The allowed residual, after a measured
pipeline delay, is one sample at 48 kHz, stable across an hour.

## Consequences

- Tranche 1 can be exact about samples and still contain no sync code.
- Firmware and the USB device path are where “exact” becomes a hardware
  claim, and only after a bench sheet.
- Any design that starts by synchronizing two free-running clocks is
  bounded mode, specified separately.
