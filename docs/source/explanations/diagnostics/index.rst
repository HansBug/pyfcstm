.. _sec-explanations-diagnostics:

Diagnostics explanation
=======================

Inspect diagnostics are model-review evidence. They are designed to tell a
human, CI job, editor, or LLM what the current FCSTM model looks like and which
places deserve attention.

What inspect can do
-------------------

Inspect can report:

* structural metrics and derived graph facts;
* source-level diagnostics with spans and structured refs;
* combo-trigger provenance that links generated pseudo-state chains back to the
  authored trigger terms;
* LLM-oriented repair guidance that keeps source context near suggested actions;
* optional verify-backed diagnostics when explicitly enabled.

What inspect cannot prove
-------------------------

Inspect is not a replacement for simulation, target hardware tests, or a full
formal-verification workflow. Static warnings can be conservative. LLM-oriented
reports are good prompts and evidence, but edits still need to be checked by
rerunning tools.

Invalid DSL remains a CLI failure
---------------------------------

If parsing or model construction fails, inspect exits with a non-zero status.
That is different from a successful report containing warning diagnostics for a
valid model.

Target-specific warnings need target-specific wording
----------------------------------------------------------

Numeric deployment-profile warnings that mention the C-family fixed-width
integer profile should be explained as C/C++ deployment risks. If the generated
target is Python, the same fixed-width integer carrying risk usually does not
apply, even though other model design warnings may still matter.

Why diagnostics help LLMs
-------------------------

Good LLM repair prompts need exact source spans, provenance, and do-not notes.
Inspect's LLM formats package those details so the assistant can propose a
small edit instead of guessing from a vague error message.
