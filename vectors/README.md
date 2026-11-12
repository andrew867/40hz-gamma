# Golden vectors

These JSON files are the acceptance contract for the stimulus math. A
TypeScript, C, or Python port matches when its outputs equal these files
within the tolerances in `docs/10-test-plan.md`.

Regenerate and check them with:

```bash
python tools/oracle/stimulus_oracle.py write
python tools/oracle/stimulus_oracle.py check
```

`check` exits non-zero on any mismatch. Do not hand-edit the JSON. Change
`tools/oracle/stimulus_oracle.py`, run `write`, and review the diff.

| File | What it locks |
| --- | --- |
| `mit_sine_48k_pulse_template.json` | 10 kHz / 1 ms pulse shape, 40 Hz grid, legacy 0.95 scale |
| `envelope_research_v1.json` | Break placement, session fade, light gate at probe times |
| `kellet_pink_seed1.json` | Seeded noise source and pink-filter recurrence |
| `binaural_48k_first_samples.json` | 200 Hz / 240 Hz pair before fade or normalization |
| `binaural_visual50_override.json` | Binaural plans use the 50% light grid even when the mode says `audio_envelope` |

The oracle is the reference implementation of the math in
`docs/03-stimulus-spec.md`. If the oracle and that document disagree, fix
both in the same change and say which one was wrong.
