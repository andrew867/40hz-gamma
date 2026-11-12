# ADR 0008 — Two CYDs share the 802.11 TSF, not a mesh

## Status

Accepted.

## Context

Both boards are CYD badges with one 2.4 GHz radio and no Ethernet. The
session can run entirely on the device. A home access point is useful for
firmware update, logs, and the browser, and useless for producing the
waveform.

ESP-WIFI-MESH, monitor mode, and raw 802.11 injection were considered as a
way to invent hardware PTP. The ESP32 promiscuous path does give a local
RX timestamp in microseconds, and only while modem sleep is off. The
transmit call returns when the frame is queued, before CSMA backoff, so
there is no IEEE 1588-style TX timestamp. A mesh hop adds delay on top of
that. Two boards on a desk can already share a clock: in a BSS the station
adopts the AP’s TSF, and `esp_wifi_get_tsf_time` reads it.

The waveform does not need to be streamed. Both chips run the same plan.
They only need to agree when sample 0 happens.

## Decision

- Two modes. Standalone: the conductor is a SoftAP and the other board
  joins it. Infrastructure: both are stations on a home AP. Power save is
  off during a session.
- The clock for either mode, when both are in the same BSS, is the TSF.
  Appointments are in TSF microseconds.
- The UDP servo and TAI anchor remain the fallback when the boards are not
  in the same BSS.
- ESP-WIFI-MESH is out of the session path until a board cannot hear the
  conductor.
- Monitor mode and `esp_wifi_80211_tx` are a lab measurement, built only if
  the TSF bench misses 200 µs p95. They are not a second sync stack in v1.
- A follower is silent unless its role is set to speaker. A speaker
  renders locally. It does not receive PCM.

## Consequences

- The first two-board test is a GPIO pulse at a TSF boundary, with no audio
  and no router. That is TST-BENCH-006.
- OTA and the browser live in infrastructure mode.
- A later claim of “hardware PTP over Wi-Fi” requires a bench sheet that
  beats TSF using RX timestamps. The sheet does not exist yet.
