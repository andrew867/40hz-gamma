# Network time and multi-device lamps

This document is the multi-badge clock. One conductor plays audio and
publishes the time of each future burst. Every lamp fires at that time or
stays dark. The protocol does not stream the 40 Hz waveform.

Read [05-time-sync.md](05-time-sync.md) for the single-device case, where
the DAC and the GPIO share a sample clock. This page starts where the lamp
is a different chip.

## What “the same time” means

Inter-device agreement is the requirement. If two lamps are asked for the
burst at conductor time T, their optical edges differ by at most the budget
below. Agreement with a wristwatch is a separate, looser goal: SNTP keeps
the displayed civil time sensible. Phase lock does not depend on the
national time servers once the conductor and the lamps share a timeline.

Wire time is **TAI nanoseconds since 1970-01-01 TAI**. Civil UTC differs
from TAI by the leap-second offset. The firmware holds that offset in
`GAMMA_TAI_MINUS_UTC_SECONDS`. As of this spec’s date (2026-11-12) the last
IERS leap insertion was 2016-12-31 and the offset is 37 seconds. Check the
IERS bulletin before a release and bump the constant when it changes. Do
not mix NTP timestamps and PTP timestamps in one comparison without
converting.

A human time such as 09:46:10.100 is converted to TAI once, at the
conductor, in the conductor’s timezone settings. Lamps never parse a
timezone. They compare nanoseconds.

## Budgets

| Path | Clock | Edge agreement target | If the estimate is worse |
| --- | --- | --- | --- |
| Two CYDs in one 802.11 BSS, Wi-Fi power save off | 802.11 TSF, read with `esp_wifi_get_tsf_time` | ≤ 200 µs p95 over 10 minutes, after TST-BENCH-006 | lamp stays off above 1 ms |
| Ethernet node with hardware PTP timestamps | PTPv2 slave | ≤ 100 µs p95 over 10 minutes | lamp stays off |
| CYDs that do not share a BSS | software two-way servo below | ≤ 1 ms p95 over 10 minutes | lamp stays off |
| Packet arrived after the burst time | none | that edge is skipped | never fire late |

The 200 µs TSF row is the target a scope bench has to confirm. It is not a
datasheet number, and a phone camera cannot see it. [15-sync-slate.md](15-sync-slate.md)
is the check that works with slo-mo: it can catch a multi-millisecond miss
and cannot pass the 200 µs row. Until a scope sheet exists, the UI shows
the measured read jitter and does not claim a tighter class. Wired PTP
remains the way to a hard sub-100 µs number on a future Ethernet board.
The CYD has no Ethernet timestamp unit.

## Two radio modes

A home router is not part of the stimulus. The session needs a shared
802.11 clock and a few dozen bytes of schedule. Internet, a browser, and
firmware update are the reasons to join a normal access point.

| Mode | Who associates to whom | Clock | What the extra network is for |
| --- | --- | --- | --- |
| Standalone | Conductor is the SoftAP. The other CYD is a station on that SSID. SSID `gamma-` plus four hex digits of the conductor id. No router | Conductor TSF. The station adopts it from beacons, which is ordinary 802.11 | Nothing. A laptop may join the same SSID to watch logs |
| Infrastructure | Both CYDs are stations on a saved home AP | That AP’s TSF, if both `esp_wifi_get_tsf_time` values are non-zero and the bench still meets the table | OTA, the browser, SNTP for the civil clock, a laptop on the same LAN |

Wi-Fi power save stays off in both modes (`WIFI_PS_NONE`). Modem sleep
makes the TSF read and the promiscuous RX timestamp coarse. The screen may
dim. The radio does not sleep during a session.

Standalone is the default when no home AP is configured, and the mode the
two-board bring-up uses. Infrastructure is selected from the Wi-Fi screen
the badge already has. Both modes run the same schedule packets. Only the
clock source changes.

A follower’s default role is lamp: it does not play audio. The user can
set the role to speaker. A speaker renders the same plan locally and starts
sample 0 at the same TSF time as the conductor. No PCM crosses the air.
Two speakers in one room will comb-filter, so the screen says so before
that role is armed.

## What mesh and monitor mode are for

ESP-WIFI-MESH is not the session clock. With two boards that can hear each
other, a mesh root election and a routing hop add machinery and jitter and
do not give a better clock than SoftAP plus TSF. Mesh comes back only when
a third board cannot hear the conductor and a bench shows that forwarding
schedule packets is worth the extra delay. Even then the forwarded packet
carries an appointment. It does not synthesize a new clock per hop.

Monitor mode and hand-built 802.11 frames are a measurement tool, not the
v1 link.

- `esp_wifi_80211_tx` returns when the frame is queued. CSMA backoff and
  retries happen after that, so an application timestamp of the send call
  is not a transmit timestamp. That gap is often hundreds of microseconds
  and sometimes milliseconds. It is the reason a raw “PTP” on this radio
  is not IEEE 1588 hardware PTP.
- The promiscuous RX callback does provide a local microsecond timestamp
  (`wifi_pkt_rx_ctrl_t.timestamp`). Espressif documents it as precise only
  while modem sleep and light sleep are off. It is a local timer, not a
  shared TAI clock, until both devices have been shown to be reading the
  same counter.
- One radio cannot be a comfortable IP station and a full-time sniffer.
  The session stays associated. Promiscuous capture is a lab screen.

Build that lab only if TST-BENCH-006 misses 200 µs. The experiment is a
four-timestamp exchange that uses the RX timestamp as t2 and t4, sends a
follow-up with the sender’s TSF, and logs the residual against GPIO edges.
If it beats TSF on the same two boards, it can replace TSF in a later ADR.
Until that sheet exists, TSF is the clock.

## Clock startup

When the node is in a BSS (standalone station, or infrastructure station
that has associated):

1. Turn power save off.
2. Wait until `esp_wifi_get_tsf_time` is non-zero.
3. Publish and consume appointments in TSF microseconds. The schedule
   field `T_anchor_tai_ns` is unused on this path. Each schedule packet
   carries a fresh anchor, not the TSF from sample 0.
4. SNTP runs only in infrastructure mode, and only to label civil time.
   It does not steer the DAC.

`T(sample)` on a TSF link:

```
T_tsf_us(sample) = T_anchor_tsf_us + (sample * 1000000) / 48000
```

`1000000 / 48000` is not an integer. Use the 64-bit multiply-then-divide
above. The remainder is under 48, so each value is within 1 µs of the real
product. Do not add a rounded 21 µs per sample.

The DAC clock and the Wi-Fi TSF are different oscillators. Fifty parts per
million of disagreement is 180 ms over an hour if the follower extrapolates
from sample 0. Every schedule packet therefore restamps the anchor: read
the sample counter and `esp_wifi_get_tsf_time` in the same place in the
render path, and store that pair as `anchor_sample` and `T_anchor_tsf_us`.
The follower throws away any older anchor. Between 100 ms packets the
leftover drift at 50 ppm is 5 µs, which is inside the TSF budget. Do not
slew the DAC to chase TSF. The conductor’s own lamp stays on the sample
counter. Only followers use the restamped TSF anchor.

When the two CYDs do not share a BSS, fall back to the servo and the TAI
anchor below. That path is the earlier design and stays for a lamp that
joined a different access point than the conductor.

## Fallback servo, when the boards do not share a TSF

Use this only when the lamp is not in the conductor’s BSS. Two CYDs in
standalone mode, or both joined to the same home AP, do not use it.

1. SNTP until the civil clock has stepped and one successful sync has
   landed. This only has to be good to a few tens of milliseconds.
2. If the node has an Ethernet MAC with hardware timestamps, start PTPv2
   against the grandmaster and servo the local timeline from the hardware
   timestamps. linuxptp on a Pi or on the bridge PC is an acceptable
   grandmaster. The ESP32 CYD skips this step.
3. A Wi-Fi lamp that is outside the conductor’s BSS runs the software
   servo against the conductor at 4 Hz.

The servo is the four-timestamp exchange from IEEE 1588, taken at the UDP
socket rather than on the wire:

```
t1  conductor sends Sync, stamped on send
t2  lamp stamps on receive
t3  lamp sends Delay_Req, stamped on send
t4  conductor stamps Delay_Req on receive and returns it
offset ≈ ((t2 - t1) - (t4 - t3)) / 2
delay  ≈ ((t2 - t1) + (t4 - t3)) / 2
```

Socket stamps include Wi-Fi jitter, so the offset wanders. The lamp keeps
the last 8 offsets, uses the median, and sets `error_est_us` to the spread
of those 8 samples. The lamp may fire only when `error_est_us` is inside
the budget for its path. A single lucky packet does not clear the gate.

The conductor’s audio sample clock is not slewed to UTC. SNTP and PTP
correct the **label** on the timeline. They do not stretch the 48 kHz DMA
clock to chase a time server. Sample index 0 of a session is an anchor:

```
T_anchor_tai_ns  = conductor TAI when sample 0 is at the DAC write
T(sample)        = T_anchor_tai_ns + sample * 1000000000 / 48000
```

`1000000000 / 48000` is not an integer, so the implementation uses one
64-bit multiply and then divides:

```
T(sample) = T_anchor_tai_ns + (sample * 1000000000) / 48000
```

The remainder of that division is less than 48000, so each timestamp is
within 1 ns of the real product. Do not add `20833` ns per sample. That
shortens the hour by 16 µs per second.

Burst `n` rises at sample `n * 1200`.

## Schedule transport

UDP, IPv4.

| Name | Value |
| --- | --- |
| Discovery multicast | `239.192.40.1:4040` (organization-local range) |
| Schedule | unicast from the conductor to each subscribed lamp |
| Servo | unicast, the four timestamps above, port 4041 |

Home access points are unreliable multicast forwarders. Discovery may be
multicast. The 40 Hz schedule is unicast so a lamp either gets the packet
or it does not. A group larger than 8 lamps is out of v1; revisit multicast
only on a wired switch that is known to forward it.

### Discovery

Lamp → `239.192.40.1:4040`, about once per second while it wants a
conductor:

| Offset | Type | Field |
| --- | --- | --- |
| 0 | char[4] | `GDIS` |
| 4 | uint8 | version 1 |
| 5 | uint8 | role: 2 = lamp (silent), 3 = speaker (renders locally) |
| 6 | uint16 | reserved 0 |
| 8 | uint32 LE | group_id |
| 12 | uint32 LE | lamp_id, random at first boot, then stored in NVS |

Conductor replies by unicast with `GACK` and its own id. A lamp locks onto
the first conductor in its `group_id`. A second conductor with the same
group id is an error: both devices light the status LED red and refuse to
publish, because two timelines would split the room.

### Schedule packet

Conductor → each subscribed lamp, every 100 ms while a session runs, and
once more on stop.

| Offset | Type | Field |
| --- | --- | --- |
| 0 | char[4] | `GSCH` |
| 4 | uint8 | version 1 |
| 5 | uint8 | flags, bit 0 = session running |
| 6 | uint16 LE | count of edges in this packet, 1..16 |
| 8 | uint32 LE | group_id |
| 12 | uint32 LE | plan_crc32 |
| 16 | uint64 LE | T_anchor_tai_ns, valid when clock is TAI |
| 24 | uint32 LE | anchor_sample, the sample the anchor refers to (0 at start) |
| 28 | uint32 LE | conductor_id |
| 32 | uint8 | clock: 1 = TSF, 2 = TAI |
| 33 | uint8 | 0 |
| 34 | uint16 LE | 0 |
| 36 | uint64 LE | T_anchor_tsf_us, valid when clock is TSF |

The burst-index list starts at offset 44. On a shared BSS the conductor
sets clock to TSF and fills `T_anchor_tsf_us`. It still fills
`T_anchor_tai_ns` with 0. A TAI follower ignores the TSF field.

The lamp computes the next edges from the anchor. It does not need one
packet per burst. `count` is the number of upcoming burst indices included
as an explicit list only when the conductor wants to mark a subset (a break
has no edges). For a normal run the conductor sends `count = 8` and then
8 × uint32 burst indices whose rise times are all at least 15 ms in the
future.

Default lead time is **20 ms**. The allowed range is 10 ms to 50 ms.
A packet that arrives with less than 5 ms of lead for a given edge does
not fire that edge. The following edges in the same packet still may.

After 200 ms with no valid `GSCH` whose `plan_crc32` matches the armed
plan, the lamp forces the pin off. A `flags` bit 0 clear is an immediate
off.

### Why this beats a PLL for these devices

The path B PLL in [05-time-sync.md](05-time-sync.md) slews a free-running
timer. That is the right tool when the follower has no shared timeline.
Once both devices can read TAI, the edge is an appointment: fire at
`T(n * 1200)`, or skip it. There is no slew and no accumulated drift
between appointments, other than the clock offset itself. Path B remains
for a follower that cannot run the servo.

## OSC

OSC 1.0 timetags are the interoperable form of the same appointment. A
bundle whose timetag is in the future is held and executed at that tag.
Immediate timetag (value 1) is rejected for lamp edges. A timetag more than
50 ms in the past is dropped. A timetag more than 2 s in the future is
dropped.

The OSC bridge, which may be the conductor, converts the NTP-epoch timetag
to TAI before it hits the scheduler. Lamps do not parse OSC on the render
task in v1. The conductor accepts OSC from a laptop and republishes `GSCH`.

Address pattern:

```
/gamma/v1/edge  ii   burst_index, unused
```

The time is the bundle timetag, not an argument. Intensity and enable for
a console live under `/gamma/v1/master` as a float 0..1 and do not move
the edge.

## E1.31 / sACN

sACN (ANSI E1.31) stays in the product as a lighting-desk hook. It is not
the phase reference.

A DMX universe updates far too slowly, and with too much jitter, to encode
a 1 ms pulse. Streaming “channel 1 high, channel 1 low” at 40 Hz will not
land on the audio grid, on Wi-Fi or on a typical console.

sACN usage that is in scope:

| Slot | Meaning |
| --- | --- |
| 1 | Master intensity 0..255. Scales nothing in v1 except a future PWM brightness. 0 forces the lamp off |
| 2 | Enable. 0 forces off. 255 allows the scheduler to fire |
| 3..512 | reserved, ignored |

The desk can black out the room. It cannot create the 40 Hz edges. Those
remain `GSCH` appointments. Priority and universe number are settings,
default universe 1, priority 100. A higher-priority stream that sets slot
2 to 0 is an immediate off, the same as a stop button.

Art-Net is not required. One lighting ingress is enough.

## Status LED

On the badge RGB LED, not on the stimulus MOSFET:

| Color | Meaning |
| --- | --- |
| Off | idle |
| Blue | servo running, error estimate inside budget, session not started |
| Green | conductor, or lamp currently accepting edges |
| Amber | packets flowing, error estimate outside budget, lamp held dark |
| Red | two conductors, fault, or plan hash mismatch |

Green on the status LED is not the word “phase-locked” in the sense of
REQ-SYNC-005. The on-device screen says “scheduled, ±N µs” with the live
`error_est_us`. The exact-mode words stay reserved for the conductor’s own
DAC and GPIO.

## Bench

TST-BENCH-006 is the first thing to run with the two CYDs, before a mesh
stack or a sniffer exists:

1. Conductor SoftAP, follower station, `WIFI_PS_NONE`, same channel, no
   home router.
2. Once a second, at conductor TSF modulo 1_000_000 equal to 0, both boards
   pulse a GPIO for 100 µs. The follower uses its own `esp_wifi_get_tsf_time`
   to decide the edge. No audio yet.
3. One scope, 10 minutes. Record p95 and the maximum follower-minus-conductor
   delay, and note any step at beacon time.
4. Pass for the TSF row in the budget table is p95 ≤ 200 µs and no edge
   later than 1 ms. A miss does not get patched by firing late. It means
   the monitor-mode experiment above is the next measurement, not the next
   product mode.

TST-BENCH-005, for a running session:

1. Two badges, one conductor running a click session, one lamp, same group
   id, same access point, no other heavy Wi-Fi traffic.
2. Photodiodes on both stimulus LEDs, one scope.
3. Record 10 minutes. p95 of the lamp-minus-conductor edge is ≤ 1 ms.
   Any edge later than 2 ms is a failure even if the p95 passes, because
   the firmware should have skipped it.
4. Turn the access point’s airtime up (a video stream on the same AP).
   Record whether the lamp goes amber and dark instead of firing late.
   That behavior is a pass.
5. Repeat with an Ethernet PTP slave in place of the Wi-Fi lamp when that
   hardware exists. Budget for that row is 100 µs p95.

## Ideas that stay in scope because they fall out of this design

- The conductor keeps running if the laptop is closed. The badge already
  has the screen, the amp, and the buttons.
- A lamp in another room follows the same timeline without playing a second
  delayed copy of the audio.
- A lighting console can black out via sACN without becoming the clock.
- A show-control laptop can drop an OSC bundle on a cue mark and the
  conductor turns that timetag into `GSCH`.

ESP-NOW, Dante, and AES67 are not v1. AES67 would be the standard if the
goal were networked audio. The goal here is one audio source and many
lamps, which is a clock plus a calendar of edges.
