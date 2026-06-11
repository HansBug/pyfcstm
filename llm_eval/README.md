# FCSTM LLM Guide Evaluation

This directory stores the standalone evaluation material for the official
FCSTM prompt guide at `pyfcstm/llm/fcstm_grammar_guide.md`.

The guide is meant to be copied into downstream LLM prompts. That makes it
different from ordinary user documentation: the practical question is not only
"is the syntax described correctly?", but also "can real coding agents read the
guide and produce legal `.fcstm` source on the first attempt from realistic
natural-language control-system descriptions?". The files under this directory
answer that question with replayable evidence.

This directory is intentionally outside both `test/` and `pyfcstm/`.

- It is not collected by normal `make unittest`.
- It is not packaged into sdist or wheel artifacts.
- It can contain natural-language fixtures, provider transcripts, extracted
  generated models, and JSON reports without turning those materials into
  runtime package resources.

The short root name `llm_eval/` is intentional. These files are evaluation
evidence for the LLM-facing guide, not part of the importable `pyfcstm.llm`
module and not part of the ordinary Python unit-test tree. Keeping the name
short makes report paths readable while preserving that separation.

## What This Evaluation Checks

The acceptance gate is deliberately narrow:

1. Build a prompt from the packaged grammar guide plus one NL fixture.
2. Ask a provider to return one complete `.fcstm` model.
3. Extract FCSTM source from the raw provider output.
4. Validate that source with pyfcstm parsing and model semantic validation.

Passing this gate means the generated model is legal FCSTM according to the
current parser and semantic loader. It does not mean the model is business
complete, simulation-covered, formally verified, or equivalent to a source
paper's full design.

That boundary is important. The guide is a syntax and modeling prompt aid, not
a domain expert or a formal correctness proof.

## Why These Fixtures Exist

The fixtures were selected because the prompt guide is supposed to help LLMs
generate FCSTM models for realistic discrete control systems, not toy examples.
The samples therefore come from the `research_ideas` project-1 source corpus
and intentionally cover several shapes that have caused modeling mistakes in
past discussions:

- EFSM-style plant/controller logic with numeric variables and guards.
- Simple FSM cores embedded in larger EFSM models.
- Protocol-like request/agreement/ack flows.
- HSM-style supervisory structure.
- T1/timing-heavy source material that must be approximated as legal FCSTM
  because current FCSTM syntax is not a timed-automata language.

All source references are pinned to the `research_ideas` repository at commit
`02171240d7690c275232bb0dfabc363aeb691083`. Fixtures summarize only the
natural-language modeling task and source traceability; they do not copy source
papers or long external documents.

## Directory Layout

```text
llm_eval/
  fixtures/              # Natural-language prompt inputs.
  outputs/<provider>/    # Raw provider output, extracted FCSTM, per-case reports.
  reports/               # Aggregated replay/live JSON summaries.
```

Each live output directory contains:

- `raw_output.md`: provider response as captured by the eval script.
- `model.fcstm`: extracted FCSTM source that was validated.
- `live_report.json`: result from the original live provider call.
- `replay_report.json`: result from replaying the saved output offline.

Aggregated reports under `reports/` are useful for PR evidence and review
comments. Per-case reports are useful when debugging one fixture or one
provider.

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
EFSM controller, one protocol state machine, and one HSM sample. Do not replace
one of these smoke fixtures without documenting why the replacement preserves
the same coverage dimension.

## Provider Evidence

The checked-in live smoke evidence currently covers three provider CLIs:

| Provider | Command shape | Live smoke | Replay | Observed output style |
|---|---:|---:|---:|---|
| `codex` | `codex exec --skip-git-repo-check -` | 4 / 4 passed | 4 / 4 passed | Larger models, generally more explicit state decomposition and guard detail. |
| `claude` | `claude -p` | 4 / 4 passed | 4 / 4 passed | Shorter models, usually compact but still legal FCSTM. |
| `codex-deepseek` | `codex-deepseek exec --skip-git-repo-check -` | 4 / 4 passed | 4 / 4 passed | Most compact outputs; good syntax adherence on the smoke set. |

The aggregate replay report is
`llm_eval/reports/replay-all-providers-all-fixtures-20260610T164058Z.json`.
Despite the filename, the committed replay evidence currently covers all saved
provider outputs for the fixed smoke set: 3 providers multiplied by 4 smoke
fixtures, for 12 total cases.

The guide metadata recorded with those reports was:

- resource name: `fcstm_grammar_guide.md`
- guide SHA-256:
  `1508e493b210348b06ec0d4b033c643a1a50e465530b568c701555174e0cb859`
- guide line count: 338
- guide chapter count: 15

If the guide changes, the SHA-256 in new reports should change too. Old reports
remain useful as historical evidence, but new PR claims should be backed by
fresh replay or live reports generated from the current guide.

## Provider CLI Contract

The evaluation script uses the same guide text returned by
`pyfcstm.llm.get_grammar_guide_prompt_for_llm()` and passes one natural-language
fixture to a provider. The provider should return only FCSTM source. If it adds
a Markdown fence, the script attempts to extract a fenced `fcstm` block before
falling back to the first FCSTM-looking line.

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

Run one provider across the fixed smoke set:

```bash
python tools/evaluate_llm_grammar_guide.py --mode live --provider claude --smoke-only
```

Reports record provider, fixture id, guide SHA-256, raw output path, extracted
`.fcstm` path, parse/semantic result, and failure category. Per-case live
reports are written as `live_report.json`; per-case replay reports are written
as `replay_report.json`, so offline replay does not overwrite the original live
evidence.

## Failure Categories

The eval script reports failures in categories so reviewers can distinguish
prompt-guide problems from infrastructure problems:

| Category | Meaning | Typical response |
|---|---|---|
| `passed` | Extracted FCSTM parsed and loaded semantically. | Keep as evidence. |
| `missing_output` | Replay expected a saved provider output that is not present. | Add output or restrict replay to saved cases. |
| `parse_error` | Provider output was not valid FCSTM syntax. | Improve the guide/prompt or classify the provider behavior. |
| `semantic_error` | Syntax parsed but model construction rejected it. | Improve examples and semantic constraints in the guide. |
| provider return-code failure | Live provider command failed before useful output. | Treat as CLI/auth/network infrastructure unless raw output shows model text. |

Only infrastructure failures should be excused without changing the guide.
Provider-generated invalid FCSTM should normally lead to guide or prompt
improvements before the PR claims the prompt is ready.

## Maintenance Rules

- Keep fixtures short, traceable, and task-oriented.
- Do not add these fixtures to `test/`; use `tools/evaluate_llm_grammar_guide.py`
  for replay/live evaluation.
- Do not include `llm_eval/` in package data.
- Keep committed live evidence bounded to representative smoke cases unless a
  PR specifically expands the eval corpus.
- When changing FCSTM syntax or semantics, update the grammar guide first, then
  rerun replay. If the change affects LLM generation behavior, refresh live
  evidence for at least the fixed smoke set.
- When adding a new fixture, document its source commit, domain, type, time
  class, and the coverage gap it fills.
