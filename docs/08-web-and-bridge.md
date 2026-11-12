# Web application and local bridge

## Web application

Tranche 2 builds a browser player that can stand in for the public site.
Tranche 3 and 4 add a device panel. The visual design can be new. The
behavior below is the contract.

### Audio-only session

- Edit the plan fields that the public site exposes: protocol, duration,
  volume, noise on/off and level, breaks on/off, break interval, break
  duration.
- Hidden but set: break fade 2 s, session fade 10 s, edge
  `raised_cosine_150us`, profile `research_v1`, sample rate 48000 when the
  context allows it.
- Generate in a Worker by calling the kernel in blocks, and assemble an
  `AudioBuffer`, or play from a `AudioWorklet` that calls the kernel live.
  Live playback is preferred once the kernel is fast enough for the
  callback. Either way the samples match the vectors.
- Route `BufferSource` or the worklet through a `GainNode` whose value is
  the volume slider. Moving the slider does not rebuild the timeline.
- Calibration plays 1 kHz at `stimulus_peak` through that same gain for 5 s.
  After the user has measured it, “Save SPL note” stores the slider
  percent, arm’s length or headphones, the dB they typed, and the date
  (REQ-HW-008). The session screen shows that sentence. It does not move
  the slider by itself.
  Copy on the page: this tone is the peak level of the stimulus, a phone
  SPL meter on a slow weighting will read a 1 ms burst lower, target a
  comfortable level around 60–65 dB SPL, stop if it is unpleasant.
- Show remaining time from the audio clock (`AudioContext.currentTime`
  minus the start context time), not from `Date.now`.
- Request a screen wake lock and set Media Session metadata for the
  duration of playback.
- If `sampleRate` is not legal for `research_v1`, stop and offer an explicit
  switch to `web_v1` or instructions to use the bridge. Do not resample.

### Light session

The device panel is visible only after the user opens “Light”. It shows:

- connection state
- firmware version and capability bits
- `sync_mode` using the words in [05-time-sync.md](05-time-sync.md)
- last error

The start button with the light enabled is disabled until the
photosensitivity acknowledgement has been clicked in this page load. The
acknowledgement states that flicker can provoke seizures in some people,
that this is not a medical device, and that the user should stop on
discomfort. It is a gate, not a consent form for a clinical trial.

Start order:

1. Validate the plan locally with the schema and the kernel.
2. Send `plan`, wait for acceptance.
3. Send `arm`, wait until status is `armed`.
4. Send `start`.
5. For path A plus nothing, start local audio.
6. For E1, do not also start local audio. The device is playing.
7. For E2, the bridge plays. The page does not open a second `AudioContext`
   onto the laptop speakers.

Stop sends `stop` and stops local audio. Closing the laptop lid is not a
control path we can trust; the firmware watchdog is.

Volume sends `volume` and updates the local gain if local audio is running.

### Platform notes the UI should reflect

| Browser | Audio-only | Bridge on localhost | Direct BLE |
| --- | --- | --- | --- |
| Desktop Chromium | yes | yes | yes, E1 control only |
| Firefox | yes | yes | no |
| Safari on iOS | yes | no, unless a separate computer runs the bridge | no |

Do not advertise direct USB from the page in v1. The bridge holds the
device.

## Bridge

A single-user process. Python is acceptable if it can meet the 1 ms E2
schedule on the developer’s machine; if it cannot, the tranche switches the
bridge to a language that can, without changing the WebSocket schema.

### Process

- Bind `127.0.0.1:8765` only.
- Print a random token at startup. Require it on the first socket message.
- Open the USB device by a documented VID/PID once the firmware has one.
  Until then, a `--simulate` mode runs the kernel and prints gate edges to
  the log so the web app can be developed without hardware.
- Serialize control messages. One plan is armed at a time. A new `plan`
  while `running` is an error; the client must `stop` first.

### E2 pacing

The bridge renders with the kernel at 48 kHz, quantizes to int16 by
rounding, clips to the int16 range, and packs the records from
[05-time-sync.md](05-time-sync.md). It writes one record per millisecond,
aligned to the device’s feedback or SOF count, not to a `sleep(0.001)` loop
alone. A `sleep` loop will miss the exact-mode budget. The implementation
note in the bridge README must say which USB mechanism provides the pace.

If the write falls behind by one frame, the bridge tells the device to fault
rather than bursting a backlog of gate bits.

### Simulate mode

`--simulate` accepts the WebSocket API and emits STATUS as if a device were
in `exact_device`. It sets `last_error` to `simulate` so the UI can show a
badge. The UI must not hide that badge. Simulate mode is how Tranche 2 and
3 tests run in CI.

## Logging

Append a JSON line per session on the machine running the bridge or, for
audio-only, in the browser’s local storage:

```json
{
  "plan_hash": "...",
  "started_unix_ms": 0,
  "stopped_unix_ms": 0,
  "stop_reason": "completed",
  "sync_mode": "none",
  "firmware": "0.0.0"
}
```

`stop_reason` is `completed`, `stopped`, or `fault`. No symptom scores and
no medical fields are required or implied. An optional free-text `note` is
allowed if the user typed one.

## Accessibility and ordinary UI practice

- The start, stop, and acknowledgement controls are real buttons and work
  from the keyboard.
- Do not autoplay a session on load.
- Show the protocol in words a user can match to the public site: MIT sine
  pulse, click train, binaural beat.
- Binaural copy says headphones are required, and that the lamp follows a
  50% square wave because there is no acoustic burst to follow.
