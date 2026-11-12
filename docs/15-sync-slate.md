# Sync slate and link statistics

This is the screen and the lamp pattern for checking two CYDs without an
oscilloscope. It is a gross timing check. It does not replace
TST-BENCH-006’s scope row, and a phone cannot see a 200 µs error.

The slate may be built on the badge tree as soon as two boards associate.
It does not need the stimulus kernel, a session, or a home router.

## How accurate TSF is

`esp_wifi_get_tsf_time` returns the 802.11 timing synchronization function,
in microseconds. In a BSS the access point is the master. Each beacon
carries the AP’s timestamp, and a station adopts it. Across a room the
radio delay itself is well under a microsecond.

Espressif does not publish an inter-device error budget for that read.
With Wi-Fi power save left on, the value is documented as unreliable and
in practice can be milliseconds off. With power save forced off, the MAC
timers on two stations of the same AP are commonly in the tens of
microseconds of each other, sometimes a bit tighter, sometimes a few
hundred microseconds. Crystal drift between beacons is only a few
microseconds at a 100 ms beacon interval. Those are lab observations, not
a guarantee. TST-BENCH-006 is what turns them into a number for these
boards.

Two extra errors sit on top of the MAC timer:

| Step | Typical size | What sees it |
| --- | --- | --- |
| MAC TSF agreement, power save off | tens of microseconds, not specified by Espressif | a scope on a pin toggled from a hardware timer |
| Reading TSF and toggling a GPIO from a FreeRTOS task | tens to hundreds of microseconds, worse if the task is late | the same scope, and this slate’s LED if the flash is armed from a task |
| ST7789 pixel update | several milliseconds, often more | the digits on the glass. They must not be used as the fine measurement |

The slate therefore flashes a real LED from a hardware timer, and treats
the on-screen digits as a coarse clock only.

## What a phone camera can resolve

| Camera | Frame time | What a pass means |
| --- | --- | --- |
| 240 fps slo-mo | 4.2 ms | The two flashes start in the same frame or adjacent frames. Offset is within about one frame |
| 960 fps | about 1.0 ms | Same rule, finer. This can support the “no edge later than 1 ms” line if the onset is unambiguous |
| 30 fps normal video | 33 ms | Only catches a mistake of several frames. Enough to see a wrong second, not enough for the slate pass |

A 200 µs TSF target is ten to twenty times smaller than a 240 fps frame.
Slo-mo can fail a bad pair. It cannot certify the tight row. Say that on
the slate itself, in one line at the bottom: “Video checks milliseconds.
It does not check microseconds.”

## The picture

Both boards run the same screen. Film the fronts, side by side, in one
shot. The backlight is the flash the camera scores. The rear RGB LED
flashes on the same edge for a second angle. Conductor and follower use
different RGB colors so the boards stay identifiable when only the backs
are in frame.

```
+----------------------------------+
| COND   standalone   ch6  -41 dBm |
|           [ check ]              |
|           link healthy           |
|                                  |
|              37                  |
|         centiseconds             |
|  [###-------]  100 ms wheel      |
|                                  |
|  BL flashes 2 ms at each 0.1 s   |
|  Video checks milliseconds.      |
+----------------------------------+
```

The giant number is `floor((tsf_us / 10000) % 100)`, so it counts 0..99
and rolls every second. Two boards in the same video frame should show the
same number, or neighbors if the exposure caught the boundary. A difference
of 2 or more (20 ms) is a fail even before counting LED frames.

The ten-cell strip is the same quantity: cell `k` is lit when
`floor((tsf_us % 100000) / 10000) == k`. One cell is 10 ms. The strip and
the digits must agree. If they do not, the screen is stale and that frame
of video is discarded.

## The flash

Armed from `esp_timer` or a GPTimer, not from the LVGL task. Each edge:

1. Read TSF. If it is zero, do not flash, and clear the checkmark.
2. On the conductor, the edge is when `tsf_us % 100000 == 0` (every
   100 ms). The follower uses its own TSF the same way. Neither board waits
   for a packet to decide this edge. The slate is a pure clock compare.
3. Rear RGB on for 2 ms. Conductor green (GPIO22 held in the “on” polarity
   for that LED, which is active-low). Follower blue (GPIO17, active-low).
   The other two channels stay off.
4. Backlight, GPIO27, from the slate idle level of 20% to 100% for the same
   2 ms, then back to 20%. The panel blink is what the front camera scores.
5. If “click” is enabled (default on while idle), a 1 kHz tone for 5 ms at
   the 1 second boundary only, through the existing DAC path. Not on every
   100 ms edge. Two clicks that flam are tens of milliseconds apart. A
   single click means the ears cannot separate them.

The 2 ms width is long enough for a 240 fps shutter to catch the onset and
short enough that the first bright frame is the edge. Do not use a one-frame
LCD rectangle as the measurement. The liquid crystal is slower than the
error we care about.

Slate mode does not run a gamma session. Starting a session leaves the
slate. The stimulus MOSFET stays off for the whole slate so a 10 Hz white
flash is not confused with the 40 Hz lamp.

## Checkmark

The mark is a check only when every line below is true. Otherwise it is a
cross and the first failing reason is the line under it.

| Check | Pass |
| --- | --- |
| Associated | BSS id is non-zero and the station has received a beacon, or this board is the SoftAP |
| Power save | `WIFI_PS_NONE` |
| TSF | last read non-zero |
| Beacons | age of last beacon ≤ twice the beacon interval, or ≤ 300 ms if the interval is unknown. SoftAP skips this row and shows “I am the clock” |
| Schedule, follower only | last `GSCH` age ≤ 200 ms and `plan_crc32` matches, once a session path exists. Before that code exists, this row is hidden, not failed |
| Skipped edges | zero in the last minute while a session is running |
| Read jitter | p95 of the 1 kHz TSF-read test below ≤ 200 µs |

The caption under a check is “link healthy”. It is not “matched to the
other board”. The other board is judged in the video.

Once a second, a 1 kHz `esp_timer` reads TSF 100 times and records
`delta_tsf - delta_timer`. The screen shows p50, p95, and max of those
residuals. A large p95 means the CPU is reading the timer late. Fix that
before believing a bad video.

## Statistics screen

A second page, same navigation style as the badge settings list. Update
the numbers at 5 Hz. Do not let this page’s redraw delay the flash timer.

| Row | Value |
| --- | --- |
| Role | conductor, lamp, speaker, alone |
| Mode | standalone SoftAP, standalone station, infrastructure |
| SSID, BSSID, channel, RSSI | from the Wi-Fi driver |
| Power save | the mode actually set |
| TSF | full 64-bit value |
| Beacon interval and age | milliseconds |
| Missed beacons | counter since associate |
| Clock source | TSF or fallback servo |
| error_est_us | servo only, otherwise “n/a” |
| TSF read p50 / p95 / max | the 1 kHz test |
| Schedule tx, rx, lost | counters |
| Lead time min / last | milliseconds of warning before the next edge |
| Edges fired, edges skipped | session counters |
| DAC underruns, late renders | session counters |
| Reset reason, firmware version, uptime | so a crash photo is useful |

Lost schedule packets are `expected - received` from the conductor’s
100 ms cadence, not a guess from RSSI.

## How to film

1. Slate on both boards, standalone or the same home AP, checkmarks
   showing.
2. Stand them upright, screens toward the phone, almost touching, so both
   backlight flashes and both centisecond numbers are in frame. Turn the
   room lights down until the backlight pulse is obvious.
3. Record slo-mo, 240 fps or faster. About ten seconds. Lock exposure if
   the phone allows it.
4. Step one frame at a time. Let frame N be the first frame where the
   conductor’s backlight has jumped. Frame M is the follower’s.
5. Offset is `(M - N) / fps`. Pass: `|M - N| ≤ 1`, and in that same frame
   the giant digits differ by at most 1. Fail: anything larger. Discard a
   frame whose strip and digits disagree.
6. Write the fps, the frame delta, and a still of the two numbers into the
   bench note. That note is TST-BENCH-007. It does not fill in the 200 µs
   row.

A mirror leaning behind the boards picks up the rear LED in the same shot
if the backlight pulse is hard to see. Score whichever edge is sharper.
Do not average the LCD digits and the LED into one number. Report them
separately. The LED onset is the result. The digits are the coarse check.
