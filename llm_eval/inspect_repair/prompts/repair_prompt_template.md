# FCSTM Inspect Repair Prompt Template

You are repairing one FCSTM model. Return only the repaired `.fcstm` source.
Do not include Markdown fences or prose.

## Repair rules

- Make the smallest source edit that preserves the apparent model intent.
- Use the official grammar guide as the syntax authority.
- Use the inspect report location, provenance, recommended actions, and do-not text before changing the model.
- Do not add dummy assignments, self-loops, unconditional exits, or guard constants only to silence diagnostics.
- Do not delete states or transitions unless the report and the model intent clearly justify deletion.
- If a diagnostic is `inspect-static`, do not treat it as an SMT proof.
- If a diagnostic is `verify-backed`, treat it as solver-backed evidence for the specific reported property.
- A repair is acceptable only when parse/model loading succeeds and all `error` and `warning` diagnostics are gone.
- `info` diagnostics may remain when the report says they can describe intentional modeling style, such as an unconditional fall-through.
- When you need to explain your choice, put the explanation outside any FCSTM fenced block; the evaluator will extract the fenced FCSTM source.
- If replacing a guarded transition with an event transition makes a variable unused, also remove that variable or keep a real guard-affecting data-flow path.
- Do not invent event declarations or standalone state event handlers; FCSTM events are introduced by transition syntax.

## Official grammar guide

{{ grammar_guide }}

## Input FCSTM

```fcstm
{{ fcstm_source }}
```

## Inspect report

{{ inspect_report }}

Return the repaired FCSTM source now.
