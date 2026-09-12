# Analysis identifier correction

The pre-existing diagnostic evidence identifies the expensive workload as
`codex_vtol_mission_supervision`, not `claude_vtol_mission_supervision`:
[original raw experiment](../../construction_profiles/1aa4315a105e/macro_cache/raw.jsonl).
These are two different corpus models. The new comparison's initial analyzer at
commit `235d29cf` incorrectly selected the Claude model for its 50% gate.

The error was found while inspecting completed Claude samples, before this run
reached the Codex VTOL samples. The analyzer and PR descriptions were corrected
to name the workload from the original diagnostic records explicitly. The other
48 queries include the separate Claude VTOL model. No numerical threshold,
input, revision, sampling order, warmup, repetition or measured record changed.

The immutable manifest and raw samples describe the original sampling program.
The sampling helper itself is unchanged. The original derived analysis is
retained in `initial-analysis/`; the corrected report is rebuilt from exactly the same raw
samples. Analysis provenance records the corrected analyzer hash separately
from the manifest's original program hash. This is an analyzer identifier error,
not an observed production regression or a replacement measurement round.
