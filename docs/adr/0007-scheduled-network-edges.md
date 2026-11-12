# ADR 0007 — Network lamps keep appointments

## Status

Accepted.

## Context

Several badges should flash together, and a lighting desk may also be on
the LAN. E1.31 is the usual lighting protocol. It carries DMX levels. It
does not name a future TAI time, and a DMX refresh cannot represent a 1 ms
pulse. The CYD has Wi-Fi and no PTP hardware timestamp. A subset of future
boards may have Ethernet and real PTPv2.

The useful property is weaker than sample lock and stronger than “fire when
the packet arrives”: every device that trusts its clock fires at the same
absolute time, or not at all.

## Decision

- The conductor (the badge playing audio) publishes burst times as TAI
  nanoseconds, 20 ms ahead, unicast, 10 times a second.
- Lamps compute `T(sample)` from the anchor. They skip edges that are no
  longer in the future. They go dark 200 ms after the last good schedule.
- SNTP starts the civil clock in infrastructure mode only. PTPv2 is for
  nodes with hardware timestamps. Wi-Fi CYDs that share one BSS use the
  802.11 TSF instead of the UDP servo. ADR 0008 records that choice. The
  servo remains for CYDs that are not in the same BSS.
- OSC timetags are the external “do this at time T” API. The conductor
  translates them into the native schedule.
- sACN may set intensity and a blackout. It does not generate the 40 Hz
  edges.

## Consequences

- Path B’s PLL remains for a follower with no shared timeline. It is not
  the multi-badge design.
- Wi-Fi multicast is discovery only.
- Two conductors in one group id are a fault.
- Lamps do not play the audio.
