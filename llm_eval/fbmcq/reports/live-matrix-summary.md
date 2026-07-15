# FBMCQ LLM Guide Evidence Summary

## Retention Policy

Only the accepted core and generality-smoke runs belong in this directory.
Each artifact-returning case stores raw output, extracted query, live report,
and replay report. Each prose smoke stores raw output, live report, and replay
report. The live report embeds every immutable digest needed for replay, so the
repository deliberately omits full prompt transcripts, standalone snapshots,
provider success logs, and superseded runs.

## Accepted Live Evidence

- Source commit: `64207b9d3b7092012a9db6ded1d04f52939dd572`
- Guide SHA-256: `45328169d44ace8c972496f54ac8d3aba33c1442dd8eb4a442e6e5d22f39271a`
- Evaluator SHA-256: `37abf1915b28d0626d15e4ef42d1011caa1e18df6a890cf7ed561723e8807707`
- Semantic source SHA-256: `f6cd22d3743ac7619b4ce8eadb65a03e0000d8342e478552bac254cc78335d04`
- Core run: `20260712-final-v15-core`, `42/42` live passed
- Core aggregate: `20260712-final-v15-core-core-live.json`
- Core aggregate SHA-256: `71a5a50b4b41de7f4f58b5ac4d674dd099ab531403b113edf6930600d18fe515`
- Smoke run: `20260712-final-v16-smoke`, `12/12` live passed
- Smoke aggregate: `20260712-final-v16-smoke-smoke-live.json`
- Smoke aggregate SHA-256: `f97fff73936cab3dcb2ba58fb69b5adaefbb7970366056c23b5dcb740e7f260d`
- Core replay aggregate: `20260712-final-v15-core-core-replay.json`
- Core replay aggregate SHA-256: `9cbeea95faaaaefe4a6fe249162eba964d01090874133aa2e8454dc5c1dd17e3`
- Core replay result: `42/42` passed
- Smoke replay aggregate: `20260712-final-v16-smoke-smoke-replay.json`
- Smoke replay aggregate SHA-256: `49cfd97036d97b19ea68201d317c3f3377d60ee81177462c5d3f6281644c0336`
- Smoke replay result: `12/12` passed
