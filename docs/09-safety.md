# Safety

This tool flashes a light at 40 Hz and plays bursts that some people find
harsh. The rules here are product rules for an experimental device. They are
not a clinical protocol and they are not a certification.

## Claims

REQ-SAFE-001 forbids diagnostic, treatment, and prevention language in the
UI, the manifest, firmware strings, store listings, and log field names.
Citing a paper in a “background” page is allowed when the sentence is
descriptive (“Iaccarino 2016 reported … in mice”) and is paired with the
statement that this software is not that experiment and is not a medical
device.

Do not compute or display a “dose”, a “treatment remaining”, or an efficacy
score.

## Sound level

The upstream tools play a −20 dBFS calibration tone and then a session
peaked at 0.95. That is about 19.5 dB hotter than the tone the user just
measured. `research_v1` removes that gap: the calibration tone peak equals
`stimulus_peak`.

The page still has to be honest about meters. A 1 ms burst at 40 Hz has a
low duty cycle. A slow A-weighted reading sits well below the peak. The copy
tells the user to start low, to use 60–65 dB SPL as a comfort target rather
than as a number this app can guarantee, and to stop on pain, tinnitus, or
distortion.

The engine will not render a stimulus peak above 0.95. Volume then only
turns that down. There is no boost past unity in the bridge or the firmware.

## Light

- Flicker can provoke seizures in people with photosensitive epilepsy, even
  though 15–25 Hz is the range most often cited as provocative. 40 Hz is not
  a reason to skip the warning.
- The acknowledgement is an unchecked control, required once per page load
  before a light plan can arm.
- The default threshold of 0.5 keeps the lamp off during the deep part of
  the fade and the break. The lamp does not come on at full pattern while
  the audio is still near silence at the start.
- Duty is capped at 50%. The firmware enforces the cap even if a modified
  client does not.
- Disconnect, fault, and watchdog drive the electrical off level.
- The user can stop from the page. The page also documents a physical
  expectation: unplugging the USB cable must darken the lamp. That is
  REQ-SYNC-007 plus the boot-time pin state.

`phase_offset_us` is limited to ±5 ms by the schema so a bad value cannot
ask the lamp to lead or lag by a whole period and still look “aligned” in
the UI. Wider offsets are a schema change, not a hidden constant.

## Session shape

Defaults match the public site’s stated practice: 60 minutes, a 20 s break
at the end of every 3 minutes, 10 s fade in and out. The break is part of
the timeline so a client crash during a break still has a defined gate
(off, once the envelope is under the threshold).

The UI may offer shorter sessions. It must not offer longer than 7200 s.

## Failure copy

When the lamp stops because sync was lost, say that the light stopped
because timing was lost. Do not keep flashing “something close”. Darkness is
the safe output.

## Privacy

Plans and logs stay local (REQ-SAFE-006). A future telemetry idea is a new
requirement, off by default, and out of scope for every tranche in
[11-tranches.md](11-tranches.md).

## Electronics handoff

The firmware author and the electronics owner share one sentence: the GPIO
idles at the level that does not conduct the LED, the firmware drives that
level whenever it is not intentionally inside a gate, and the MOSFET’s gate
threshold and the LED current are chosen so a stuck-high fault still fails
safe if a series fuse or a hardware watchdog pulldown is fitted. Fitting
that hardware is outside the software tranches. The software does not assume
the fuse exists; it still drives off.
