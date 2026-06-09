SysDeSim FinalState maintenance
===============================

This page documents the SysDeSim ``uml:FinalState`` compatibility contract used
by the ``dev/damnx`` branch. It is a branch-specific maintenance note for the
SysDeSim XML/XMI import path, not a new FCSTM language feature.

Scope
-----

SysDeSim state-machine diagrams render UML final states as a bullseye marker.
In XML/XMI these vertices appear as ``uml:FinalState``. The converter does not
emit them as ordinary FCSTM states. Instead, supported transitions that target a
FinalState are lowered onto FCSTM exit semantics.

The supported shapes are deliberately narrow:

* A leaf state targeting a FinalState in the same region lowers to
  ``State -> [*]``.
* A nested leaf state targeting a FinalState owned by an ancestor region lowers
  to a route-flag exit chain.
* FinalState sources, outgoing FinalState transitions, unrelated-region jumps,
  ``exitPoint`` and ``terminate`` variants remain explicit non-goals until real
  samples define their intended semantics.

Lowering contracts
------------------

Same-level FinalState transitions are rendered directly as FCSTM exits::

    SS -> [*];

Cross-level FinalState transitions use one reserved route flag. The first hop
exits the source composite and sets the flag. Ancestor hops keep exiting while
the flag is active, and the last hop clears it::

    def int __sysdesim_flag_route_control_e__tx_dqgyfg = 0;

    state StateMachine {
        state Control {
            state EState;
            EState -> [*] effect {
                __sysdesim_flag_route_control_e__tx_dqgyfg = 1;
            }
        }

        Control -> [*] : if [__sysdesim_flag_route_control_e__tx_dqgyfg > 0] effect {
            __sysdesim_flag_route_control_e__tx_dqgyfg = 0;
        };
    }

Route flags are variables, not states. They must not appear as rendered state
nodes or state-lane cells.

Timeline and report contract
----------------------------

After the runtime exits through ``[*]``, timeline validation records the ended
sentinel as the string ``"[*]"``. This sentinel is not a normal model state path
and must not be passed through ordinary state lookup.

The timeline import report exposes XML provenance through the fixed field
``report["phase10"]["termination"]``. Each row has exactly these keys::

    {
        "machine_alias": "...",
        "source_path": ["..."],
        "target_id": "...",
        "target_path": [],
        "target_vertex_type": "final",
        "transition_ids": ["..."],
        "reached": true,
        "ended_step_ids": ["s27"],
    }

Downstream code should preserve those keys. Any future schema extension must be
reviewed together with this maintenance page and the FS-5 regression tests.

Visualization contract
----------------------

User-facing views must describe ended machines as ``已终止`` or equivalent human
text. They must not display ``__sysdesim_final_*`` as a state, pseudo state,
lifeline state-cell value, SVG label or PNG label.

SVG/PNG overlays and CLI summaries should derive their termination text from the
same termination summary used by the JSON report. This keeps report, CLI and
visual output aligned.

Regression evidence
-------------------

The checked-in regression fixtures are:

* ``test/testfile/sysdesim/final_state_same_level_model2.xml`` for same-level
  FinalState lowering.
* ``test/testfile/sysdesim/final_state_cross_level_model0608.xml`` for
  cross-level route-flag lowering, ended timeline rows and visible termination
  provenance.

The focused FS-5 regression entry point is
``test/convert/sysdesim/test_final_state_regression.py``. Unit tests must use
checked-in fixtures only. External files under ``/data/sync/work`` are allowed
for local smoke evidence, but not as pytest dependencies.
