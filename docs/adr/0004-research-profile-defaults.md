# ADR 0004 — research_v1 is the default profile

## Status

Accepted. Tranche 0.

## Context

The Python script and the website disagree on break placement, noise during
breaks, sample rate, noise synthesis, and calibration level. The website is
the product people actually use. Some of its choices fight the level and
reproducibility goals of the new system.

## Decision

`research_v1` is the default: 48 kHz, breaks at the end of the interval,
seeded Kellet noise that follows the envelope, fixed stimulus peak, raised-
cosine 150 µs edges, calibration tone at the stimulus peak.

`web_v1` reproduces the deployed worker, including noise through breaks and
legacy peak normalization, for comparison tests. The UI does not select it
unless the audio device rate is illegal or the user asks for compatibility.

## Consequences

- Golden vectors for the default path are at 48 kHz.
- A port that “matches the Python README” by putting the break at t = 0 is
  wrong for the default profile.
- The 19.5 dB calibration gap is treated as a defect, not as heritage.
