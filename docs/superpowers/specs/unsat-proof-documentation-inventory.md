# UNSAT proof documentation inventory

| Field | Concrete ownership and evidence |
|---|---|
| Scope | Standalone `pyfcstm.solver` native proof API. Existing BMC CLI and explanation migration are outside this change. |
| Source facts | `solver/proof.py`, `_z3_proof.py`, `proof_rules.py`, `proof_text.py`, `proof_io.py`, `unsat.py`, `symbols.py`, `budget.py`; public tests in `test/solver/test_proof*.py` and `test_unsat.py`. |
| Capability list | Exact named conjunction/background; native evidence capture; arithmetic/scope analysis; readable EN/ZH output; source bindings; rule and reading extensions; subset minimization and reproof; cooperative deadlines; canonical offline loading. |
| Tutorial path | `tutorials/unsat_proofs/index{,_zh}.rst`: construct three contradictory conditions and one irrelevant condition, obtain the full actual proof, read the weighted contradiction. |
| How-to tasks | `how_to/unsat_proofs/index{,_zh}.rst`: minimize groups, retain background, map caller sources, fold a checked proof slice, add a native-rule interpreter, export/load, handle unavailable evidence. |
| Explanation topics | `explanations/unsat_proofs/index{,_zh}.rst`: full-input proof versus core, native trust versus local checking, hypothesis scope, evidence-preserving folds, exact source provenance and future BMC boundary. |
| Reference facts | `reference/unsat_proofs/index{,_zh}.rst`: input/options contracts, all report fields and statuses, graph/reading field groups, extension signatures and errors, minimization and budget boundaries. Generated API pages cover the dataclass fields and callable docstrings. |
| Boundaries and counterexamples | No shortest-proof or minimum-cardinality promise; unsupported rules remain partial; no full independent proof kernel; plugins are trusted Python code; loaded snapshots are structurally validated, not authenticated; source candidates do not imply necessary statements. |
| Diagnostics and errors | TypeError/ValueError/KeyError boundaries; SAT/UNKNOWN/timeout; missing core or proof, interrupted assembly; invalid evidence and explicit proof gaps. |
| Examples and resources | `tutorials/unsat_proofs/proof.demo.py` and its generated `.py.txt`: linear, branch and non-BMC source examples in both languages. Optional `--minimize` and `--fold` use the same public APIs. No hand-authored proof inference is keyed to an example. |
| Migration and landing pages | Add sibling links under each role and root language toctree; no existing page or CLI contract removed. BMC adapter/old explanation replacement belongs to subsequent consumer work. |
| Verification | Run the demo with PYTHONPATH set to this checkout; regenerate through `make -C docs contents`; run `make rst_auto`, doctests, terminology/toctree checks, fresh EN/ZH HTML builds, applicable PDF gates and visual inspection. Compare paired pages and execute all claimed examples before readiness. |

No mathematical equation ledger is introduced: these pages explain exact
printed arithmetic and API semantics without adding labelled LaTeX equations.
No rendered diagram is needed for the small linear pipeline; trace tables and
complete real text outputs carry the explanation in each language.
