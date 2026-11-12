# 40 Hz gamma stimulator — specification pack

This folder is the build contract for a successor to
[Joona Heino's 40 Hz stimulator](https://40hz-gamma-entrainment.joonaheino.com/).
The public site plays research-style auditory stimuli in the browser. The
Python project it came from is [lurnake/40hz_poc](https://github.com/lurnake/40hz_poc).
Neither one drives a light. This pack specifies the audio, the light pin, and
the only clock arrangements that can keep those two locked.

The product is an experimental research tool. It is not a medical device and
the documents must not grow therapeutic claims.

## What “locked to the 10 kHz pulse” means

The MIT-style sound is a 10 kHz tone turned on for 1 ms, then off for 24 ms.
That pattern repeats 40 times a second. The pin does **one** pulse per burst.
It does not toggle at 10 kHz. At 48 kHz the burst occupies samples
`[n*1200, n*1200+48)` and the pin’s rising edge is that first sample, after a
calibrated constant delay of at most one sample at the headphone jack and the
LED.

A browser timer, a Bluetooth notification, or a Wi-Fi WebSocket cannot hold
that tolerance. IEEE 1588 (PTP) synchronizes clocks. It does not tell a
browser which audio sample is leaving the headphone jack. Exact lock is
defined only for two arrangements:

1. The microcontroller generates the audio and the pin from one sample clock.
   The board we have is the Freenove CYD badge: original ESP32, mono 8-bit
   DAC on GPIO26 at 48 kHz, LVGL touchscreen. See
   [docs/13-cyd-badge.md](docs/13-cyd-badge.md).
2. The microcontroller is the USB sound device. Headphones plug into it. Each
   USB frame carries the audio samples and the gate bits, and the pin is
   delayed by the same FIFO as the DAC.

Extra badges do not receive an audio stream. Both chips render the plan.
The conductor publishes when sample 0 happens. With two CYDs and no home
router, one board is the SoftAP and the other joins it. They share the
802.11 TSF clock. A home AP is the other mode, used for updates and the
browser. Mesh and raw monitor-mode packets are a lab measurement if that
TSF bench misses its target, not the session path. See
[docs/14-network-time.md](docs/14-network-time.md).

## Read this in order

| Order | Document | You need it when you are… |
| --- | --- | --- |
| 1 | [docs/16-start-gate.md](docs/16-start-gate.md) | deciding whether planning is done |
| 2 | [docs/12-agent-guide.md](docs/12-agent-guide.md) | about to write code |
| 3 | [docs/11-tranches.md](docs/11-tranches.md) | choosing the next slice of work |
| 4 | [docs/01-as-built.md](docs/01-as-built.md) | checking what the current site and script actually do |
| 5 | [docs/03-stimulus-spec.md](docs/03-stimulus-spec.md) | implementing the sample math |
| 6 | [docs/05-time-sync.md](docs/05-time-sync.md) | touching clocks, USB, Bluetooth, or the pin |
| 7 | [docs/10-test-plan.md](docs/10-test-plan.md) | deciding whether a slice is done |

The index of every document is [docs/README.md](docs/README.md).

## Check the math before trusting a port

```bash
python tools/oracle/stimulus_oracle.py check
```

That command compares `tools/oracle/stimulus_oracle.py` with `vectors/`.
Ports in later tranches import the same JSON. They do not re-derive the
numbers from the prose.

## Layout

```
docs/           requirements, architecture, protocols, tranches, ADRs
schemas/        JSON Schema for session plans and device status
examples/       one valid plan and one CRC test frame
vectors/        golden outputs
tools/oracle/   reference math
vendor/         local analysis cache, gitignored, not a product dependency
```

Tranche 0 is this pack. The next implementation slice is Tranche 1, a pure
stimulus kernel with no audio device and no GPIO. Do not start the firmware
or the website until that kernel matches the vectors.
