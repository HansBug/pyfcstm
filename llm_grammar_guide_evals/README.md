# FCSTM LLM Grammar Guide Evaluation Fixtures

This directory contains standalone prompt-evaluation material for the official
FCSTM LLM grammar guide. It is intentionally outside `test/` and outside
`pyfcstm/`, so normal unit tests and package data do not include these natural
language fixtures.

The fixtures are used to check whether an LLM can read the packaged guide and
produce `.fcstm` source that passes pyfcstm parsing and model semantic
validation on the first attempt. The acceptance gate here is legal FCSTM
structure only; it does not claim business correctness, simulation scenario
coverage, or formal verification coverage.

## Source Snapshot

All source references are pinned to the `research_ideas` repository at commit
`02171240d7690c275232bb0dfabc363aeb691083`.

## Directory Layout

```text
llm_grammar_guide_evals/
  fixtures/              # Natural-language prompt inputs.
  outputs/<provider>/    # Raw provider output, extracted FCSTM files, and per-case reports.
  reports/               # Replay/live JSON summaries.
```

## Fixture Coverage Matrix

| Fixture id | Domain | Type | Time class | Smoke | Why it is included |
|---|---|---|---|---|---|
| `traffic_emergency_priority` | traffic-light preemption | EFSM | T0 | yes | Covers camera counts, ambulance priority, neighbor-light coordination, guard plus event modeling. |
| `parking_lift_rotate_push` | underground parking machinery | EFSM | T0 | no | Covers lift, rotate, push/retract, slot sensors, manual override, and deterministic mechanical sequencing. |
| `distributed_elevator_can` | distributed elevator control | EFSM with simple FSM core | T0 | yes | Covers `UP` / `DOWN` / `STOP`, request clearing, rank arbitration, and CAN state synchronization. |
| `platooning_join_protocol` | autonomous-vehicle platooning | protocol | T0 | yes | Covers request/agreement/ack flow and safety guards for lane change and steering enablement. |
| `bottle_filling_capping_sorting` | bottle filling and capping | EFSM | T1 boundary | no | Covers batch ordering, timed fill intervals, capping, conveyor output routing, and T1-to-legal-FCSTM approximation. |
| `drawbridge_plc_sequence` | drawbridge PLC control | EFSM | T0 | no | Covers ship detection, road barriers, bridge actuator sequence, and traffic signal restoration. |
| `vtol_mission_supervision` | VTOL UAV mission manager | HSM | T0 | yes | Covers hierarchical `Mission Mode` / `Command Mode`, supervisory commands, and global exits. |
| `landing_gear_sequence_boundary` | aircraft landing gear | EFSM | T1 boundary | no | Covers interruptible extend/retract sequences, pilot indicators, timing guards, and failure-light thresholds. |

The fixed minimum live smoke set is:

- `traffic_emergency_priority`
- `distributed_elevator_can`
- `platooning_join_protocol`
- `vtol_mission_supervision`

This set preserves one EFSM+T0 engineering system, one simple FSM core inside an
EFSM controller, one protocol state machine, and one HSM sample.

## Provider CLI Contract

The evaluation script uses the same guide text returned by
`pyfcstm.llm.get_grammar_guide_prompt_for_llm()` and passes one natural-language
fixture to a provider. The provider must return only FCSTM source, but the
script can still extract a fenced `fcstm` code block if the provider adds a
Markdown fence.

Supported provider names:

- `codex`
- `claude`
- `codex-deepseek`

Run replay without contacting providers:

```bash
python tools/evaluate_llm_grammar_guide.py --mode replay --smoke-only
```

Run one live smoke:

```bash
python tools/evaluate_llm_grammar_guide.py --mode live --provider codex --fixture traffic_emergency_priority
```

Reports record provider, fixture id, guide SHA-256, raw output path, extracted
`.fcstm` path, parse/semantic result, and failure category. Per-case live
reports are written as `live_report.json`; per-case replay reports are written
as `replay_report.json`, so offline replay does not overwrite the original live
evidence.
