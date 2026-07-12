# FBMCQ LLM Guide Evaluation

This directory stores standalone evidence for the packaged FBMCQ language guide
at `pyfcstm/llm/fbmcq_language_guide.md`. It is private evaluation material,
not a public prompt API, model-fact schema, or recommended application input
format.

The Guide teaches FBMCQ authoring quality: known facts, property selection,
bounds, initialization, assumptions, vacuity, definedness, and response
windows. It does not teach checking-engine internals.

## Layout

```text
llm_eval/fbmcq/
  fixtures/<property>_<complete|facts>.task.md
  fixtures/models/<property>.fcstm
  fixtures/models/<property>.mutated.fcstm
  fixtures/models/<property>.discriminator.fcstm
  fixtures/models/<property>.expected.fbmcq
  fixtures/smoke/<repair|audit|explanation>.task.md
  outputs/runs/<accepted-run>/<provider>/<case>/{raw_output.md,query.fbmcq?,live_report.json,replay_report.json}
  reports/<run-id>-<core|smoke>-<live|replay>.json
```

Each property has two private task forms. `complete` embeds FCSTM source;
`facts` names only the facts required by the property. This contrast tests the
Guide without defining a public context format. A complete-source task may use
other supplied model facts, while a facts task may only use the facts stated in
its task packet. Both forms must still agree with the task-specific semantic
oracle and any discriminator model.

## Core Matrix

The acceptance matrix has seven property kinds, two task forms, and three
providers: 42 single-generation cases.

| Property | Nominal intent | Mutation check |
|---|---|---|
| `reach` | target is reachable | target transition removed |
| `forbid` | dangerous state is forbidden | dangerous transition removed |
| `invariant` | variable condition holds everywhere | update preserves condition |
| `must_reach` | initial state occurs on every trace | initial child changed |
| `exists_always` | one path keeps a condition true | event changes the value |
| `response` | later response follows trigger | response transition removed |
| `cover` | public transition case is coverable | guard becomes impossible |

Every core case must pass raw-output validation, parse, canonical round-trip,
structural and model binding, compile, executable query precondition, solver
result interpretation, witness replay, nominal oracle, anti-vacuity checks,
task-specific semantic discrimination when present, and mutation
discrimination. Reference queries define the oracle only; they do not require
one output spelling.

## Generality Smokes

Four private smoke tasks exercise the same Guide outside the core generation
matrix: repair one parser error, repair one model-binding error, audit a
vacuous assumption, and explain a response-incomplete result. Repair replies
must pass the same raw-artifact and semantic gates as the matching core task.
Audit and explanation replies use an explicit three-line prose contract that
checks their verdict, causal reasoning, repair or bound limitation, and absence
of extra response panels. These 12 calls (four tasks across three providers)
do not dilute or replace the core 42-case acceptance threshold.

## Commands

Replay one immutable evidence run without contacting a provider:

```bash
python tools/evaluate_llm_fbmcq_guide.py --mode replay --run-id 20260712-final-v15-core
python tools/evaluate_llm_fbmcq_guide.py --mode replay --smoke-only --run-id 20260712-final-v16-smoke
```

Check the evaluator's deterministic anti-regression cases without contacting a
provider:

```bash
python tools/evaluate_llm_fbmcq_guide.py --check
```

Create a new run for all three providers across all 14 tasks:

```bash
python tools/evaluate_llm_fbmcq_guide.py --mode live --run-id 20260712-final-v15-core
python tools/evaluate_llm_fbmcq_guide.py --mode live --smoke-only --run-id 20260712-final-v16-smoke
```

Live mode refuses to overwrite a run and requires a clean tracked working tree.
The repository retains only accepted raw output, extracted query when the outer
task returns an artifact, and per-case live/replay reports, matching the FCSTM
evaluator's minimal evidence layout. Each live report embeds immutable prompt,
task, raw-output, query, Guide, evaluator, semantic-source, and model-asset
SHA-256 digests plus the source commit; full prompt transcripts, standalone
snapshots, and successful provider stderr logs are deliberately not retained.
Replay reconstructs the prompt from the current Guide and task, then rejects
missing metadata, altered raw/query artifacts, changed evaluator or semantic
source code, changed task/model assets, incompatible source ancestry, or a
tracked dirty tree. Infrastructure failures are never successful cases.

The accepted core run is `20260712-final-v15-core` and the accepted generality
smoke run is `20260712-final-v16-smoke`. Superseded runs are deleted rather
than retained as duplicate evidence. The aggregate summary is in
`reports/live-matrix-summary.md`.

## Maintenance

- Do not add this directory to `test/` or package data.
- Do not import the evaluator from pytest.
- Do not add fixture answers, task ids, provider instructions, or a public
  context format to the packaged Guide.
- After changing FBMCQ grammar, binding, visible atom rules, property behavior,
  polarity, or response-incomplete behavior, update the Guide as needed, run
  `make sha256`, run deterministic Guide tests, and refresh affected evidence.
- Do not claim readiness from fixture-oracle checks alone. All 42 single-run
  core provider cases and all 12 generality smoke cases must pass and replay
  before the Guide is ready.
- A raw LLM artifact must not contain FBMCQ comments. Comments remain legal in
  ordinary handwritten `.fbmcq` files, but the evaluator rejects them so that
  response prose or commands cannot be hidden from the output contract.
