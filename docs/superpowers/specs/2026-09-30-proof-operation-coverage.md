# Solver proof operation coverage

This is an acceptance map of the current compiler and solver surface. It is not
an assertion of completeness for arbitrary nonlinear integer arithmetic. All
paths below enter through public query/model construction or public proof loading.
Private certificate probes are instruments for checking those public contracts.

## Compiler construction and real-input regressions

All named BMC tests live in `test/bmc/test_solver_proof_coverage.py` unless stated
otherwise. Their formulas are produced by `BmcEngine.prepare`,
`build_bmc_core_formula` and `compile_bmc_property`, then passed to `explain_unsat`.
They do not establish that the production BMC explanation CLI has been migrated.

| Construction | Production location | Evidence and regression |
|---|---|---|
| Boolean connectives, implication, ITE | `relation.py::_lower_bmc_cond_expr`, `_lower_bmc_num_expr`, `_build_case_relation` | Native logical rules retain scopes; `test_control_flow_encodings_have_complete_proofs`, encoder coverage and scoped reading tests |
| State domain, initial/havoc values, frame equality | `relation.py::_build_domain_formula`, `_build_initial_formula`, `_build_step_relation` | Actual initial/transition/objective groups; control-flow and multi-frame tests |
| Priority and false guards | `macro.py` case construction; `relation.py::_lower_guard_requirement` | `test_control_flow_encodings_have_complete_proofs`, `test_guard_after_prefix_effect_is_proved_at_its_actual_anchor` |
| Conditional true/false guards and definedness | `relation.py::_guarded_domain_constraints`, solver expression/domain encoding | `test/solver/proof/test_guards.py`; consistent-context prerequisite and undefinedness are separate |
| Exit, transition and entry actions; unchanged variables | `relation.py::_execute_action_block`, `_prepare_case_lowering` | `test_exit_transition_and_entry_effects_compose_in_the_proof`, with SAT perturbation |
| Action call history, absolute/relative windows and snapshot filters | `properties.py::_effective_call_steps`, `_call_match_expr`, `_lower_call_count` | `test_call_history_filters_use_the_recorded_action_snapshot`; two-frame before/after actions, SAT and UNSAT cases |
| Event capacity | `relation.py::_build_environment_formula` | `test_three_event_cardinality_has_a_complete_native_proof`; weighted/signed counting and portable mutation controls in `test_theories.py` |
| Numeric comparison, addition, subtraction, multiplication, casts | `relation.py::_z3_arith_binary`, `_z3_comparison`; `solver/expr.py` | Arithmetic/interval/polynomial replay; real BMC arithmetic and assignment composition tests |
| Division and remainder | `relation.py::_z3_arith_binary` and expression definedness | Positive/negative integer division, nonzero-divisor guard and modular BMC tests; integer remainder/product SAT and UNSAT pair |
| abs/sign, floor/ceil/trunc/round | `relation.py::_z3_ufunc`, `solver/expr.py::python_round_to_z3` | `test_lowered_numeric_functions_and_short_circuit_domains`, `test_rounding_bounds_remain_complete_inside_bmc`; signed tie-to-even cases and SAT controls |
| Short-circuit domain guards | `relation.py::_lower_bmc_cond_expr`, `_guarded_domain_constraints` | Actual `x<0 || sqrt(x)>0` under `x=-1`, with both SAT and UNSAT objectives |
| Square roots and powers | `relation.py::_z3_ufunc`, `_z3_arith_binary` | Root/power domain tests, quartic and composite-square tests, query-only root contradiction, multi-frame root products and shifted powers |
| Shared algebraic constants across contexts | `solver/proof/_z3_proof.py::capture_proof` | Batched translation preserves assertion/source identity; `test_algebraic_equality_contradiction_has_an_original_input_proof`, `test_algebraic_source_binding_shares_the_assertions_translated_value` |
| Operator spelling versus builtin identity | Typed proof capture and normalization | Authored-function negative controls in encoder/theory/semantic tests prevent name-based inference |

Call-history coverage uses the supported call windows and action snapshots.
Frame-local predicates accept omitted/current selectors; `binding.py` rejects
explicit numeric frame selectors outside event assumptions, and `var` has no
historical-frame argument. The tests do not invent unsupported selector syntax.
Reserved bitwise branches
in `_z3_arith_binary` are marked for a future BitVec profile; they are not evidence
that the current BMC numeric language supports bit vectors.

## Composition and evidence boundary

The remainder/product regression varies sign of divisor/product, assertion
order, variable names, multiplication operand order and Int-to-Real casts. All
variants must retain UNSAT, complete reading, no gaps, and canonical text
roundtrips. A satisfiable product and unconstrained Real-product controls prevent
integrality from being guessed.

`integer_round` replays a polynomial's monomial lattices, including rational
steps and offsets; it does not ask Z3 whether a proposed inference is true.
Mutation controls alter parent counts, weights, factors, coefficients, strictness
and numeric sorts. Sparse equalities are substituted first, with authored variables
ordered before interpreted integer atoms; every substitution still emits an
existing equality-product and sum certificate. Search order is not trusted by replay.

Source attachment, logical input ownership, local hypotheses and folded evidence
coverage are checked during public canonical loading. Source description content
is caller-provided metadata, not authenticated provenance. Native mechanical
rules and explicit extensions retain their documented trust boundary.

## Text and resource acceptance

`proof_readings/integer_product.json` is an actual captured native proof. Its
English/Chinese brief, standard and detailed texts are full `text_aligner`
fixtures. Live native tests compare offline roundtrips; fixed graphs pin exact
wording without assuming native proof layouts remain identical across versions.

Timeout tests preserve known UNSAT/core and completed analysis; pending checks do
not become passed. Minimization establishes group-level subset minimality only
after all required checks finish. Pruning removes unused dependencies from the
selected derivation; it does not claim a globally shortest proof.

## Native limitation experiment

A direct native query `x % 2 == 0, (x*y) % 2 != 0` over integers, with a 2000 ms
budget, returned `unknown` with timeout in both ordinary and proof-enabled Z3
contexts on the development environment. This records a finite-budget outcome,
not mathematical unprovability or a universal Z3 limitation. It differs from
`x % 2 == 0, x*y == 3`, for which Z3 supplies a proof and the repaired reconstruction
produces complete readings. Native solving, capture and readable reconstruction
must remain separate status fields.
