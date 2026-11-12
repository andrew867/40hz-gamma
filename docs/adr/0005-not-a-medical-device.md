# ADR 0005 — Not a medical device

## Status

Accepted. Tranche 0.

## Context

The stimulus parameters come from neuroscience papers about 40 Hz sensory
stimulation. The upstream author already labels the public tool as
experimental and not a medical device. This pack adds a flashing lamp,
which has a real photosensitivity hazard, and it is easy for UI copy to
slide from “based on a paper” into “this treats”.

## Decision

The software is an experimental research tool. Requirements REQ-SAFE-001
through REQ-SAFE-007 are in force for every tranche. No tranche adds
accounts, cloud logs, diagnostic scores, or treatment language. A future
regulated-device effort is a different project; it does not get to inherit
these shortcuts by renaming them.

## Consequences

- The photosensitivity acknowledgement is a product gate, not a claim that
  the device is safe.
- Paper citations stay on a background page and stay descriptive.
- Test TST-WEB-004 scans the built strings.
