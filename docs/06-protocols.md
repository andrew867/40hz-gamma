# Protocols

Two encodings share one vocabulary.

- JSON documents for plans and status, validated by `schemas/`.
- A binary frame for links that need a small parser: USB CDC, BLE, the E2
  media interface’s control endpoint, and path B sync.

The loopback WebSocket carries JSON text messages, one JSON value per
WebSocket message. It does not carry the binary frame. The bridge translates
JSON into binary when it talks to the MCU.

## Session plan

`schemas/session-plan.schema.json` is authoritative. A worked example is
`examples/session-plan.research.json`.

Rules beyond the schema:

- `profile: research_v1` implies the numeric constraints in
  [03-stimulus-spec.md](03-stimulus-spec.md). Schema validation is not a
  substitute for those constraints. Both run.
- `safety.photosensitivity_ack` must be true to arm a plan with
  `light.enabled`. The web app sets it only after a click in the current
  page load.
- Canonical bytes for hashing: JSON object keys sorted at every level,
  separators `(',', ':')`, UTF-8, no BOM. SHA-256 of those bytes is the plan
  hash. CRC-32 of those same bytes is `plan_crc32` on the sync frame
  (IEEE CRC-32, polynomial 0x04C11DB7 reflected, the common ZIP/Ethernet
  variant, init 0xFFFFFFFF, xor-out 0xFFFFFFFF).

Playback volume is a separate message so a volume change is not a new plan.

## Binary frame

```
offset 0  uint16 LE  magic 0x3147, on the wire the bytes 47 31
offset 2  uint8      version 0x01
offset 3  uint8      type
offset 4  uint16 LE  payload length in bytes, 0..1024
offset 6  payload
offset 6+n uint16 LE crc
```

CRC-16-CCITT-FALSE over version, type, length, and payload. Polynomial
0x1021, init 0xFFFF, no reflection, xor-out 0. The check value of the ASCII
bytes `123456789` is `0x29B1`. The magic is outside the CRC so a receiver
can scan for `47 31`.

The empty STOP frame is the parser test vector. Bytes:

```
47 31 01 22 00 00 d2 1a
```

That file is `examples/stop-frame.hex`. A receiver that rejects this frame
is wrong. A receiver that accepts it with the CRC bytes swapped is wrong.

| Type | Name | Payload |
| --- | --- | --- |
| 0x01 | HELLO | none |
| 0x02 | HELLO_ACK | see below |
| 0x10 | SESSION_PLAN | UTF-8 JSON, may be split with 0x11 |
| 0x11 | PLAN_CHUNK | uint16 index, uint16 count, then bytes |
| 0x12 | PLAN_ACK | uint8 status, then a UTF-8 error string if status ≠ 0 |
| 0x20 | ARM | 32-byte SHA-256 of the plan |
| 0x21 | START | none. Start at the next audio block boundary |
| 0x22 | STOP | none |
| 0x23 | CLEAR_FAULT | none |
| 0x24 | SET_VOLUME | uint16 LE, 0..1000 meaning volume 0.000..1.000 |
| 0x30 | STATUS | UTF-8 JSON, `gamma.device_status.v1` |
| 0x40 | SYNC | 16-byte path B record below |
| 0x7F | ERROR | UTF-8 string |

HELLO_ACK payload:

| Offset | Type | Meaning |
| --- | --- | --- |
| 0 | uint8 | protocol version, 1 |
| 1 | uint8 | kind: 1 CDC, 2 UAC vendor, 3 BLE, 4 Wi-Fi socket |
| 2 | uint32 LE | capability bits |
| 6 | uint8 | firmware major |
| 7 | uint8 | firmware minor |
| 8 | uint8 | firmware patch |
| 9 | uint32 LE | native sample rate, 48000 |

Capability bits:

| Bit | Meaning |
| --- | --- |
| 0 | E1 device synthesis |
| 1 | E2 vendor audio frames |
| 2 | path B follower |
| 3 | active-low pin supported |

SYNC payload, 16 bytes, type 0x40:

| Offset | Type | Field |
| --- | --- | --- |
| 0 | uint32 LE | plan_crc32 |
| 4 | uint32 LE | pulse_index |
| 8 | uint32 LE | source_time_us |
| 12 | int32 LE | source_rate_ppm |

PLAN_CHUNK exists because a BLE characteristic write is small. Index is
zero-based. The receiver assembles, then parses, then answers with
PLAN_ACK. USB CDC can send SESSION_PLAN in one frame when the JSON fits in
1024 bytes. Larger plans use chunks. The example plan fits in one CDC frame.

## E2 media frame

This is not wrapped in the magic frame. It is a bulk transfer of a fixed
64-byte mono record or 112-byte stereo record, described in
[05-time-sync.md](05-time-sync.md). The control endpoint still uses the
magic frame. A device that receives media frames while not in `running`
discards them and counts `frames_dropped`.

## WebSocket control

URL: `ws://127.0.0.1:8765/v1`. First message from the client:

```json
{"type":"auth","token":"<token printed by the bridge>"}
```

The bridge closes the socket on any other first message. Later messages:

| type | body |
| --- | --- |
| `hello` | empty. Bridge replies with the HELLO_ACK fields as JSON |
| `plan` | `{ "plan": <GammaSessionPlan> }` |
| `arm` | empty. Uses the last accepted plan |
| `start` | empty |
| `stop` | empty |
| `clear_fault` | empty |
| `volume` | `{ "volume": 0.0 }` |
| `status` | bridge pushes this; clients may also send it to request one |

Status pushes use `schemas/device-status.schema.json`. Errors are
`{"type":"error","message":"..."}`.

The bridge refuses `plan` when the JSON fails the schema or the kernel
rejects the profile constraints. The firmware sees only plans the bridge
already accepted, and it checks them again.

## BLE layout

One service, three characteristics, UUIDs in
[05-time-sync.md](05-time-sync.md).

- Control is write-with-response. Payload is one binary frame. If the frame
  exceeds the ATT MTU, the client uses PLAN_CHUNK frames, each of which must
  fit in a single write.
- Status is notify. Payload is one STATUS frame.
- Sync is write-without-response. Payload is one SYNC frame. E1 devices
  that are not path B followers may omit this characteristic.

The browser page may talk BLE directly only for E1 control, and only when no
bridge is connected. If the bridge is connected, the page uses the bridge.
Two controllers are a defect.

## Versioning

`version` byte 0x01 and `schema` string `gamma.session_plan.v1` move
together. A receiver with a different version answers HELLO_ACK with its
version and rejects plans rather than guessing. There is no silent
downgrade that changes break placement or the sample grid.
