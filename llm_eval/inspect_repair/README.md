# Inspect Repair Evaluation

This directory stores standalone evidence for the LLM-oriented `pyfcstm inspect`
reports. It is separate from the root grammar-guide evaluation: the root
`llm_eval/fixtures/` tasks ask providers to generate legal FCSTM from natural
language, while this directory asks providers to repair an existing FCSTM file
using the official grammar guide plus an `llm-json` or `llm-md` inspect report.

The directory is intentionally outside both `test/` and `pyfcstm/`.

- It is not collected by normal `make unittest`.
- It is not packaged into sdist or wheel artifacts.
- It may contain provider transcripts and repair attempts because they are
  evaluation evidence, not runtime package data.

## Directory Layout

```text
llm_eval/inspect_repair/
  fixtures/manifest.json       # Fixture catalog and expected diagnostics.
  fixtures/*.fcstm             # Broken FCSTM inputs for repair.
  prompts/                     # Prompt template used by the runner.
  reports/                     # Aggregate summaries.
  artifacts/                   # Per fixture/provider/format evidence.
  run_inspect_repair_eval.py   # Maintenance runner, not a pytest test.
```

## Repair Contract Under Test

Each repair prompt contains only:

1. the official grammar guide from `pyfcstm.llm.get_grammar_guide_prompt_for_llm()`;
2. one FCSTM source fixture;
3. one inspect report rendered as `llm-json` or `llm-md`;
4. the fixed minimal-repair rules from `prompts/repair_prompt_template.md`.

The provider should return repaired FCSTM source only. The runner then validates
that source with pyfcstm parse/model construction and `inspect` recheck.

## Isolation Requirement

The repair generation stage must run in an isolated temporary working directory.
That directory contains only a prompt packet, the input FCSTM fixture, and the
rendered inspect report. The provider process must not use the repository root
as its current directory and must not rely on tests, source code, previous
artifacts, or PR comments to infer the answer.

The artifact for each provider × format × fixture cell records:

- isolated working directory path;
- visible file list;
- provider command and client version when known;
- guide metadata and SHA-256;
- inspect command and report path;
- prompt packet path;
- raw provider output;
- repaired source;
- verification command and result;
- failure category and bad-repair flags.

Verification may run back in the repository because it intentionally uses the
current pyfcstm implementation. Isolation applies to the generation stage.

## Failure Categories

| Category | Meaning |
|---|---|
| `passed` | Repaired source parsed, loaded, and passed the selected inspect gate. |
| `prepared` | Prompt packet and inspect report were generated without contacting a provider. |
| `model-error` | Provider returned source, but parse/model/inspect verification failed. |
| `infra-blocked` | Provider CLI, authentication, timeout, or network failed before a usable repair. |
| `guide-gap` | The official grammar guide was insufficient or misleading for the repair. |
| `contract-gap` | The `llm-json` / `llm-md` report lacked information needed for a safe repair. |

Infrastructure failures must be recorded and retried. They must not be counted
as a successful repair cell.

## Fixture Coverage

The manifest keeps the fixture matrix as the single source of truth. It includes
separate cases for static dataflow warnings, static-only contradictory guards,
verify-backed dead guards, multi-diagnostic stacking, redundant transitions,
unreachable states, single diagnostic combo-trigger warnings, and adversarial
suggested-action cases. In particular, `combo_trigger_single` is intentionally
separate from `multi_diag_stacking` so a single diagnostic with a compound
trigger condition is not confused with multiple diagnostics interacting.

## Typical Commands

Generate inspect reports and prompt packets without contacting providers:

```bash
python llm_eval/inspect_repair/run_inspect_repair_eval.py --mode prepare --smoke-only
```

Run a single live repair cell:

```bash
python llm_eval/inspect_repair/run_inspect_repair_eval.py \
  --mode live --provider codex --format llm-md --fixture combo_trigger_single
```

Replay existing repaired sources:

```bash
python llm_eval/inspect_repair/run_inspect_repair_eval.py --mode replay --smoke-only
```
