:orphan:

Tutorials information-architecture migration log
================================================

Purpose
-------

This orphan page is the persistent migration log for the tutorials information-architecture split. It is intentionally outside the public toctree. PR-F through PR-I append their detailed migration records here; PR-J audits this file during final cleanup.

Owner boundaries
----------------

* PR-F owns user-facing pages: installation, CLI, generation, inspect, visualization.
* PR-G owns DSL pages.
* PR-H owns simulation pages.
* PR-I owns maintainer pages: render, grammar, structure.
* PR-J owns final navigation cleanup, duplicate-link cleanup, landing-page checks, and global verification.

Shared-file rule
----------------

PR-E creates the shared top-level and category toctrees. Later PRs should fill their own leaf pages and should not add or remove shared toctree entries unless the change is recorded in that PR body and deferred to PR-J when possible.

Old URL rule
------------

Do not rename existing ``docs/source/tutorials/<slug>/`` directories during the migration. When a later PR moves the main content away from an old tutorial path, the old path should become a short landing page that points to the new location.

Chapter migration record template
---------------------------------

.. list-table::
   :header-rows: 1

   * - Old location
     - Old section
     - New location
     - Action
     - Notes
   * - ``tutorials/<page>/index*.rst``
     - ``<heading>``
     - ``tutorials/`` / ``how_to/`` / ``explanations/`` / ``reference/``
     - move / merge / keep landing / delete
     - Deletions need an explicit reason.

Resource migration record template
----------------------------------

.. list-table::
   :header-rows: 1

   * - Old resource
     - New resource
     - Action
     - Notes
   * - ``.fcstm`` / ``.puml`` / ``.demo.*`` / ``.png`` / ``.svg`` / ``.txt``
     - New path or retained path
     - move / copy / keep / delete / regenerate
     - Record source-output pairs and regeneration commands when applicable.

PR-F user-facing page migration
-------------------------------

Scope
~~~~~

PR-F covers the user-facing installation, CLI, generation, inspect, and visualization pages. It keeps old ``tutorials/<slug>/`` URLs reachable while moving task and reference material into the four-way information architecture.

Chapter migration records
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-F chapter migration
   :header-rows: 1

   * - Old location
     - Old section
     - New location
     - Action
     - Notes
   * - ``tutorials/installation/index*.rst``
     - ``Installation`` / ``安装``
     - ``how_to/installation/index*.rst``
     - move
     - Installation steps, package checks, CLI checks, and troubleshooting moved to the task guide.
   * - ``tutorials/installation/index*.rst``
     - whole old page path
     - ``tutorials/installation/index*.rst``
     - keep landing
     - Old URL now points to the installation how-to and quick start.
   * - ``tutorials/cli/index*.rst``
     - ``Installation`` and verification sections
     - ``how_to/installation/index*.rst``
     - merge
     - Installation tasks no longer live in the CLI page; PyPI, module execution, source install, pre-built executable release, and published-doc links are preserved.
   * - ``tutorials/cli/index*.rst``
     - ``Getting Help`` and common command workflows
     - ``how_to/cli_workflows/index*.rst``
     - move
     - Task-oriented CLI flows moved to how-to.
   * - ``tutorials/cli/index*.rst``
     - command syntax and parameter facts
     - ``reference/cli/index*.rst``
     - move
     - CLI facts are now independently searchable in reference.
   * - ``tutorials/cli/index*.rst``
     - ``Best Practices`` / ``最佳实践``
     - ``how_to/cli_workflows/index*.rst``
     - merge
     - DSL file organization, version-control hygiene, clean generation, output mapping, and custom-template smoke-test advice were compressed into the reproducibility checklist.
   * - ``tutorials/cli/index*.rst``
     - whole old page path
     - ``tutorials/cli/index*.rst``
     - keep landing
     - Old URL now routes readers to how-to, reference, installation, and quick start.
   * - ``tutorials/generation/index*.rst``
     - first Python generation path
     - ``tutorials/generation/index*.rst``
     - keep tutorial
     - Tutorial remains as the shortest first generated-runtime path.
   * - ``tutorials/generation/index*.rst``
     - native generation, polling generation, README, and integration tasks
     - ``how_to/generation/index*.rst``
     - move
     - How-to covers Python, C/C++, polling templates, README entry points, validation summary, and ``--template`` discipline.
   * - ``tutorials/generation/index*.rst``
     - built-in template table and selection hints
     - ``reference/builtin_templates/index*.rst``
     - move
     - Template names, main files, user entry points, and target notes moved to reference.
   * - ``tutorials/inspect/index*.rst``
     - first human and JSON inspect path
     - ``tutorials/inspect/index*.rst``
     - keep tutorial
     - Tutorial now focuses on one first diagnostic-heavy report.
   * - ``tutorials/inspect/index*.rst``
     - CI, LLM, and verify task usage
     - ``how_to/inspect/index*.rst``
     - move / add short task guide
     - CI and LLM usage is task-oriented and bounded to user-facing use.
   * - ``tutorials/inspect/index*.rst``
     - report keys and output format facts
     - ``reference/inspect_report/index*.rst``
     - move
     - JSON and LLM report facts moved to reference.
   * - ``tutorials/inspect/index*.rst``
     - diagnostic code examples and target-profile code scope
     - ``reference/diagnostics_codes/index*.rst``
     - move
     - Common codes and C/C++ target-profile wording moved to reference.
   * - ``tutorials/inspect/index*.rst``
     - diagnostics boundaries and LLM guidance rationale
     - ``explanations/diagnostics/index*.rst``
     - move
     - Explanation stays user-facing and does not cover maintainer architecture.
   * - ``tutorials/visualization/index*.rst``
     - first PlantUML source generation path
     - ``tutorials/visualization/index*.rst``
     - keep tutorial
     - Tutorial remains a short first-diagram path with observable output.
   * - ``tutorials/visualization/index*.rst``
     - diagram export and renderer tasks
     - ``how_to/visualization/index*.rst``
     - move
     - Task guide covers PlantUML source export, detail-level comparison, rendered-file export, renderer mode, and headless ``--no-open`` usage.
   * - ``tutorials/visualization/index*.rst``
     - best practices, readability, and performance guidance
     - ``how_to/visualization/index*.rst``
     - merge
     - Audience-specific detail levels, ``max_depth``, hiding irrelevant details, event coloring, ``collapse_empty_states``, and large-model guidance were compressed into ``Keep diagrams readable``.
   * - ``tutorials/visualization/index*.rst``
     - ``PlantUMLOptions`` and ``-c`` option facts
     - ``reference/visualization_options/index*.rst``
     - move
     - Full option facts, defaults, CLI typing rules, and Python-only ``custom_colors`` scope are now in reference.

Resource migration records
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-F resource migration
   :header-rows: 1

   * - Old resource
     - New resource
     - Action
     - Notes
   * - ``tutorials/installation/install_check.demo.py`` and ``*.txt``
     - same path
     - keep
     - Reused by ``how_to/installation`` through ``literalinclude`` while the old landing URL remains in place.
   * - ``tutorials/installation/cli_check.demo.sh`` and ``*.txt``
     - same path
     - keep
     - Reused by ``how_to/installation``; no regeneration needed in this PR.
   * - ``tutorials/cli/simple_machine.fcstm`` and generated PlantUML image/source outputs
     - same path
     - keep
     - Old CLI page became a landing page; resources remain for compatibility and PR-J cleanup review.
   * - ``tutorials/cli/file_download.fcstm`` and generated PlantUML image/source outputs
     - same path
     - keep
     - Not copied into new pages; retained to avoid deleting historical resources before final cleanup.
   * - ``tutorials/cli/*.demo.sh.txt``
     - same path
     - keep
     - No new page depends on these outputs; retained for old-resource audit and PR-J cleanup.
   * - ``tutorials/generation/simple_machine.fcstm`` and generated PlantUML outputs
     - same path
     - keep
     - Reused by the shortened tutorial and generation how-to.
   * - ``tutorials/generation/python_runtime.demo.py`` and ``*.txt``
     - same path
     - keep
     - Reused by tutorial and how-to.
   * - ``tutorials/generation/native_runtime.demo.sh`` and ``*.txt``
     - same path
     - keep
     - Reused by generation how-to; output was not regenerated in this PR.
   * - ``tutorials/generation/*_driver.c`` and ``*_driver.cpp``
     - same path
     - keep
     - Detailed driver excerpts no longer dominate the tutorial; sources remain for native smoke generation, the how-to validation matrix, and future cleanup.
   * - ``tutorials/inspect/inspect_diagnostics.fcstm`` and generated PlantUML outputs
     - same path
     - keep
     - Reused by inspect tutorial and references.
   * - ``tutorials/inspect/inspect_*.demo.sh`` and ``*.txt``
     - same path
     - keep
     - Reused by inspect tutorial and reference pages; no regeneration needed in this PR.
   * - ``tutorials/visualization/example.fcstm`` and generated PlantUML outputs
     - same path
     - keep
     - Reused by visualization tutorial.
   * - ``tutorials/visualization/cli_*.demo.sh`` and ``*.txt``
     - same path
     - keep
     - Reused by visualization tutorial or kept for option examples; no regeneration needed in this PR.
   * - ``tutorials/visualization/output_*.puml`` and rendered image outputs
     - same path
     - keep
     - Existing rendered artifacts remain valid; detail-level comparison SVGs are referenced from ``how_to/visualization`` and the rest remain for PR-J cleanup review.
   * - ``tutorials/visualization/python_*.demo.py`` and ``*.txt``
     - same path
     - keep
     - Python API examples are linked from ``how_to/visualization`` and retained for future reference/cleanup decisions.

Resource cleanup note
~~~~~~~~~~~~~~~~~~~~~

All PR-F resources remain in their original tutorial directories to keep legacy
landing pages and existing generated artifacts stable. PR-J should reassess each
``keep`` row before removing old landing pages or relocating resources.

PR-G DSL migration
--------------------

Scope
~~~~~

PR-G covers DSL pages only: ``tutorials/dsl/``, ``how_to/dsl/``,
``reference/dsl/``, ``explanations/dsl_semantics/``, and this PR-G section of
this migration log. It does not change shared category toctrees or non-DSL owner
pages.

Inbound reference check
~~~~~~~~~~~~~~~~~~~~~~~

The implementation scanned inbound DSL references with::

    rg -n ':doc:.*dsl|:ref:.*dsl|tutorials/dsl' docs/source -g '*.rst'

Findings:

* Category stubs under ``how_to/dsl``, ``reference/dsl``, and
  ``explanations/dsl_semantics`` were replaced by real content, so their old
  "current authority" links were removed.
* Existing top-level and tutorial links continue to point at
  ``tutorials/dsl/index*.rst``, which remains a short learning path.
* Simulation and grammar pages still link to the DSL tutorial or DSL example
  resources; those cross-owner pages are left unchanged for PR-H / PR-I / PR-J.

Chapter migration records
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-G chapter migration
   :header-rows: 1

   * - Old location
     - Old section
     - New location
     - Action
     - Notes
   * - ``tutorials/dsl/index*.rst``
     - ``Overview`` / ``概述``
     - ``tutorials/dsl/index*.rst``
     - keep tutorial
     - Compressed to a short orientation and explicit links to how-to, reference, and explanation pages.
   * - ``tutorials/dsl/index*.rst``
     - ``Language Structure`` / ``语言结构``
     - ``tutorials/dsl/index*.rst`` and ``reference/dsl/index*.rst``
     - merge
     - First-model structure remains in tutorial; exact top-level facts moved to reference.
   * - ``tutorials/dsl/index*.rst``
     - ``Variable Definitions`` / ``变量定义``
     - ``tutorials/dsl/index*.rst`` and ``reference/dsl/index*.rst``
     - merge
     - Introductory declaration examples remain in tutorial; literal and expression facts moved to reference.
   * - ``tutorials/dsl/index*.rst``
     - ``State Definitions`` / ``状态定义``
     - ``tutorials/dsl/index*.rst``, ``reference/dsl/index*.rst``, ``explanations/dsl_semantics/index*.rst``
     - merge
     - Leaf/composite first path remains in tutorial; exact state forms and pseudo semantics moved out.
   * - ``tutorials/dsl/index*.rst``
     - ``Transition Definitions`` / ``转换定义``
     - ``tutorials/dsl/index*.rst``, ``how_to/dsl/index*.rst``, ``reference/dsl/index*.rst``, ``explanations/dsl_semantics/index*.rst``
     - merge
     - First ordinary transition path remains in tutorial; combo/forced forms and semantics moved out.
   * - ``tutorials/dsl/index*.rst``
     - ``Event Definitions`` / ``事件定义``
     - ``tutorials/dsl/index*.rst``, ``how_to/dsl/index*.rst``, ``reference/dsl/index*.rst``, ``explanations/dsl_semantics/index*.rst``
     - merge
     - A short event-transition introduction remains in tutorial; local-event recipes, scope facts, and ownership semantics moved out.
   * - ``tutorials/dsl/index*.rst``
     - ``Guard Conditions and Effects`` / ``守卫条件和效果``
     - ``tutorials/dsl/index*.rst``, ``how_to/dsl/index*.rst``, ``reference/dsl/index*.rst``, ``explanations/dsl_semantics/index*.rst``
     - merge
     - Basic guard/effect path remains in tutorial; operation facts and expression-separation rationale moved out.
   * - ``tutorials/dsl/index*.rst``
     - ``Expression System`` / ``表达式系统``
     - ``reference/dsl/index*.rst``
     - move
     - Operator, literal, boolean, comparison, and function facts are now reference material.
   * - ``tutorials/dsl/index*.rst``
     - ``Lifecycle Actions`` / ``生命周期动作``
     - ``tutorials/dsl/index*.rst``, ``how_to/dsl/index*.rst``, ``reference/dsl/index*.rst``, ``explanations/dsl_semantics/index*.rst``
     - merge
     - Minimal enter/during/exit remains in tutorial; action forms, recipes, and aspect boundaries moved out.
   * - ``tutorials/dsl/index*.rst``
     - ``Real-World Example: Smart Thermostat`` / ``实际示例：智能恒温器``
     - ``tutorials/dsl/index*.rst``
     - keep tutorial
     - Retained as an advanced complete example; first runnable path now uses compact warning-free ``first_thermostat.fcstm``.
   * - ``tutorials/dsl/index*.rst``
     - ``Comment Styles`` / ``注释样式``
     - ``reference/dsl/index*.rst``
     - move
     - Comment forms are now top-level facts in the reference page.
   * - ``tutorials/dsl/index*.rst``
     - ``Documentation Best Practices`` / ``文档最佳实践``
     - ``how_to/dsl/index*.rst`` and ``PR-J``
     - merge / defer
     - Practical writing advice was compressed into task guidance; any duplicated prose should be audited in PR-J.
   * - ``tutorials/dsl/index*.rst``
     - ``Semantic Validation Rules`` / ``语义验证规则``
     - ``tutorials/dsl/index*.rst`` and ``reference/dsl/index*.rst``
     - merge
     - First-model validity checklist remains in tutorial; detailed boundary facts moved to reference.
   * - ``tutorials/dsl/index*.rst``
     - ``Import Assembly`` / ``Import 装配``
     - ``how_to/dsl/index*.rst``, ``reference/dsl/index*.rst``, ``explanations/dsl_semantics/index*.rst``
     - move
     - Import tasks, syntax facts, and assembly boundaries are now split by document mode.
   * - ``tutorials/dsl/index*.rst``
     - repeated ``Common Errors`` / ``常见错误`` subsections
     - ``how_to/dsl/index*.rst`` and ``reference/dsl/index*.rst``
     - merge / delete duplicate detail
     - Repeated old error lists were compressed into task warnings and boundary facts instead of being copied verbatim.
   * - ``tutorials/dsl/index*.rst``
     - stale grammar-file reference
     - ``reference/dsl/index*.rst``
     - corrected
     - Old text referred to a single ``Grammar.g4``; reference now names ``GrammarParser.g4`` and ``GrammarLexer.g4``.
   * - ``tutorials/dsl/index*.rst``
     - pseudo composite state wording
     - ``reference/dsl/index*.rst``
     - corrected
     - Reference now distinguishes the parser shape ``pseudo state Name { ... }`` from model-valid DSL. Model construction reports ``E_PSEUDO_NOT_LEAF`` for pseudo composites, so user-facing docs only present ``pseudo state Name;`` as valid.
   * - ``tutorials/dsl/index*.rst``
     - event declaration and ``::`` examples
     - ``tutorials/dsl/index*.rst``, ``how_to/dsl/index*.rst``, ``reference/dsl/index*.rst``
     - corrected
     - Explicit reusable events now use chain-scoped forms such as ``: Start``. Source-local ``:: Event`` examples no longer claim to consume parent-level declarations, and runnable simulate snippets perform the cold-start cycle before sending the event.
   * - ``tutorials/dsl/index*.rst``
     - runtime cycle ordering details
     - ``explanations/execution_semantics/index*.rst``
     - defer
     - PR-G keeps only DSL-level summaries; complete simulator ordering belongs to PR-H.
   * - ``tutorials/dsl/index*.rst``
     - ``Summary`` / ``总结``
     - ``tutorials/dsl/index*.rst``
     - keep tutorial
     - Rewritten as navigation to the three split DSL pages.

Resource migration records
~~~~~~~~~~~~~~~~~~~~~~~~~~

PR-G keeps DSL resources in ``docs/source/tutorials/dsl/`` to preserve old URL
compatibility and existing source-output pairs. New split pages reference those
stable paths when needed. No generated resource was regenerated by this PR.

.. list-table:: PR-G resource migration
   :header-rows: 1

   * - Old resource
     - New resource
     - Action
     - Notes
   * - ``tutorials/dsl/abstract_reference_demo.fcstm``
     - same path
     - keep
     - FCSTM source; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/abstract_reference_demo.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/abstract_reference_demo.fcstm.puml.png``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/abstract_reference_demo.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/composite_state_lifecycle.puml``
     - same path
     - keep
     - hand-authored PlantUML source; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/composite_state_lifecycle.puml.png``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/composite_state_lifecycle.puml.svg``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm``
     - same path
     - keep
     - FCSTM source; archive-only legacy guard/effect example replaced by ``operation_blocks_complete.fcstm`` for current docs; path kept stable for migration audit.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; archive-only legacy guard/effect diagram follows ``guards_and_effects.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm.puml.png``
     - same path
     - keep
     - generated image output; archive-only legacy guard/effect diagram follows ``guards_and_effects.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; archive-only legacy guard/effect diagram follows ``guards_and_effects.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/event_scoping_complete.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/event_scoping_complete.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/event_scoping_complete.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/event_scoping_complete.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/example.fcstm``
     - same path
     - keep
     - FCSTM source; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/example.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/example.fcstm.puml.png``
     - same path
     - keep
     - generated image output; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/example.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/expression_demo.fcstm``
     - same path
     - keep
     - FCSTM source; archive-only legacy expression example replaced by ``expression_condition_ternary.fcstm`` for current docs; path kept stable for migration audit.
   * - ``tutorials/dsl/expression_demo.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; archive-only legacy expression diagram follows ``expression_demo.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/expression_demo.fcstm.puml.png``
     - same path
     - keep
     - generated image output; archive-only legacy expression diagram follows ``expression_demo.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/expression_demo.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; archive-only legacy expression diagram follows ``expression_demo.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/forced_transitions.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/forced_transitions.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/forced_transitions.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/forced_transitions.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/guards_and_effects.fcstm``
     - same path
     - keep
     - FCSTM source; archive-only legacy guard/effect example replaced by ``operation_blocks_complete.fcstm`` for current docs; path kept stable for migration audit.
   * - ``tutorials/dsl/guards_and_effects.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; archive-only legacy guard/effect diagram follows ``guards_and_effects.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/guards_and_effects.fcstm.puml.png``
     - same path
     - keep
     - generated image output; archive-only legacy guard/effect diagram follows ``guards_and_effects.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/guards_and_effects.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; archive-only legacy guard/effect diagram follows ``guards_and_effects.fcstm``; path kept stable for migration audit.
   * - ``tutorials/dsl/hierarchy_execution.fcstm``
     - same path
     - keep
     - FCSTM source; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/hierarchy_execution.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/hierarchy_execution.fcstm.puml.png``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/hierarchy_execution.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/import_host_basic.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_basic.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_basic.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_basic.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_directory.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_directory.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_directory.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_directory.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_mapped.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_mapped.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_mapped.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_host_mapped.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/main.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/main.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/main.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/main.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/subsystems/robot.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/subsystems/robot.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/subsystems/robot.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_line/subsystems/robot.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_worker.fcstm``
     - same path
     - keep
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_worker.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_worker.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/import_worker.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/leaf_state_lifecycle.puml``
     - same path
     - keep
     - hand-authored PlantUML source; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/leaf_state_lifecycle.puml.png``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/leaf_state_lifecycle.puml.svg``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/pseudo_state_demo.fcstm``
     - same path
     - keep
     - FCSTM source; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/pseudo_state_demo.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/pseudo_state_demo.fcstm.puml.png``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/pseudo_state_demo.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; explanations/dsl_semantics + how_to/dsl; reused by semantic explanations or lifecycle recipes; path kept stable.
   * - ``tutorials/dsl/thermostat_example.fcstm``
     - same path
     - keep
     - FCSTM source; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/thermostat_example.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/thermostat_example.fcstm.puml.png``
     - same path
     - keep
     - generated image output; tutorials/dsl; kept for the short learning path and legacy tutorial URL.
   * - ``tutorials/dsl/thermostat_example.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; tutorials/dsl; kept for the short learning path and legacy tutorial URL.

Resource cleanup note
~~~~~~~~~~~~~~~~~~~~~

All PR-G resources are recorded as ``keep``. PR-J should reassess whether any
legacy-only diagram or generated image can be removed after all split pages and
old landing pages are stable.

PR-H simulation page migration
------------------------------

Scope
~~~~~

PR-H covers the simulation tutorial, simulation task guide, and execution
semantics explanation. It keeps the old ``tutorials/simulation/`` URL reachable
as a short first-run tutorial while moving task recipes and runtime semantics to
``how_to/simulation/`` and ``explanations/execution_semantics/``.

Chapter migration records
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-H chapter migration
   :header-rows: 1

   * - Old location
     - Old section
     - New location
     - Action
     - Notes
   * - ``tutorials/simulation/index*.rst``
     - ``Core Concepts``
     - ``tutorials/simulation/index*.rst`` and ``explanations/execution_semantics/index*.rst``
     - split / keep tutorial summary
     - Short state/lifecycle vocabulary remains in the first-run tutorial; execution details moved to explanation.
   * - ``tutorials/simulation/index*.rst``
     - ``Python Usage`` / ``Creating and Running Simulations``
     - ``tutorials/simulation/index*.rst`` and ``how_to/simulation/index*.rst``
     - split
     - Minimal runtime loop remains in tutorial; embedding and API-oriented tasks moved to how-to.
   * - ``tutorials/simulation/index*.rst``
     - ``Triggering Events``
     - ``how_to/simulation/index*.rst``
     - move
     - Event injection is now a task recipe; DSL event syntax is linked to DSL reference instead of repeated.
   * - ``tutorials/simulation/index*.rst``
     - ``Hot Start from Specific State`` and ``Hot Start Feature`` examples
     - ``how_to/simulation/index*.rst`` and ``explanations/execution_semantics/index*.rst``
     - split
     - Command/API usage moved to how-to; hot-start boundary semantics moved to explanation.
   * - ``tutorials/simulation/index*.rst``
     - ``Implementing Abstract Handlers``
     - ``how_to/simulation/index*.rst``
     - move
     - Handler registration and context usage are task-oriented runtime embedding material.
   * - ``tutorials/simulation/index*.rst``
     - ``CLI Usage`` / ``Starting the Simulator`` / ``Available Commands`` / ``Interactive Features`` / ``Reproducible CLI Transcript`` / ``Batch Mode``
     - ``how_to/simulation/index*.rst``
     - move
     - CLI and REPL tasks now live in the simulation how-to.
   * - ``tutorials/simulation/index*.rst``
     - ``Configuration Settings``
     - ``how_to/simulation/index*.rst``
     - move
     - ``setting`` command facts moved to display-setting task guidance.
   * - ``tutorials/simulation/index*.rst``
     - ``Export Formats``
     - ``how_to/simulation/index*.rst``
     - move
     - ``export <path>`` and output-format guidance are simulation task facts.
   * - ``tutorials/simulation/index*.rst``
     - ``Command Line Options``
     - ``how_to/simulation/index*.rst``
     - move
     - ``pyfcstm simulate --help`` facts are summarized in the task guide rather than a separate reference page.
   * - ``tutorials/simulation/index*.rst``
     - ``Execution Semantics`` / ``Cycle Execution`` / examples 1-10
     - ``explanations/execution_semantics/index*.rst``
     - move / summarize
     - Runtime ordering, validation, pseudo state, aspect, priority and transition-effect semantics moved to explanation; detailed legacy examples retained as resources for PR-J audit.
   * - ``tutorials/simulation/index*.rst``
     - ``Real-World Business Examples`` / examples 11-13
     - ``explanations/execution_semantics/index*.rst`` and PR-J audit
     - summarize / keep resource
     - Business models remain as old resources; current PR-H does not keep long business walkthroughs in tutorial.
   * - ``tutorials/simulation/index*.rst``
     - ``Best Practices`` / ``Testing and Debugging`` / ``Handler Implementation`` / ``Performance`` / ``Common Pitfalls``
     - ``how_to/simulation/index*.rst`` and ``explanations/execution_semantics/index*.rst``
     - merge
     - Task debugging advice moved to how-to; runtime boundary notes moved to explanation.
   * - ``tutorials/simulation/index*.rst``
     - whole old page path
     - ``tutorials/simulation/index*.rst``
     - keep tutorial / landing
     - Old URL now hosts a short first-run tutorial plus a topic destination table.

Resource migration records
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-H resource migration
   :header-rows: 1

   * - Old resource
     - New resource
     - Action
     - Notes
   * - ``tutorials/simulation/abstract_handlers.demo.py``
     - same path
     - keep
     - how_to/simulation; Kept in old directory and literal-included by abstract-handler task; source-output pair remains stable.
   * - ``tutorials/simulation/abstract_handlers.demo.py.txt``
     - same path
     - keep
     - how_to/simulation; Kept in old directory and literal-included by abstract-handler task; source-output pair remains stable.
   * - ``tutorials/simulation/basic_usage.demo.py``
     - same path
     - keep
     - tutorials/simulation + how_to/simulation; Kept for first Python runtime loop and how-to reference; source-output pair remains stable.
   * - ``tutorials/simulation/basic_usage.demo.py.txt``
     - same path
     - keep
     - tutorials/simulation + how_to/simulation; Kept for first Python runtime loop and how-to reference; source-output pair remains stable.
   * - ``tutorials/simulation/cli_batch.demo.sh``
     - same path
     - keep
     - tutorials/simulation + how_to/simulation; Kept for first CLI transcript and batch-mode task guide; output was not regenerated because source is unchanged.
   * - ``tutorials/simulation/cli_batch.demo.sh.txt``
     - same path
     - keep
     - tutorials/simulation + how_to/simulation; Kept for first CLI transcript and batch-mode task guide; output was not regenerated because source is unchanged.
   * - ``tutorials/simulation/event_triggering.demo.py``
     - same path
     - keep
     - how_to/simulation; Kept in old directory and literal-included by event injection task; source-output pair remains stable.
   * - ``tutorials/simulation/event_triggering.demo.py.txt``
     - same path
     - keep
     - how_to/simulation; Kept in old directory and literal-included by event injection task; source-output pair remains stable.
   * - ``tutorials/simulation/example10_validation_failure.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example10_validation_failure.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example10_validation_failure.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example10_validation_failure.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example11_elevator_door.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example11_elevator_door.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example11_elevator_door.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example11_elevator_door.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example12_water_heater.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example12_water_heater.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example12_water_heater.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example12_water_heater.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example13_traffic_light.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example13_traffic_light.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example13_traffic_light.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example13_traffic_light.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example1_basic.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example1_basic.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example1_basic.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example1_basic.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example2_composite.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example2_composite.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example2_composite.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example2_composite.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example3_aspect.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example3_aspect.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example3_aspect.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example3_aspect.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example4_pseudo.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example4_pseudo.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example4_pseudo.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example4_pseudo.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example5_multilevel.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example5_multilevel.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example5_multilevel.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example5_multilevel.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example6_transition_priority.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example6_transition_priority.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example6_transition_priority.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example6_transition_priority.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example7_self_transition.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example7_self_transition.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example7_self_transition.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example7_self_transition.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example8_guard_effect.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example8_guard_effect.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example8_guard_effect.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example8_guard_effect.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example9_pseudo_chain.full.fcstm``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example9_pseudo_chain.full.fcstm.puml``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example9_pseudo_chain.full.fcstm.puml.png``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/example9_pseudo_chain.full.fcstm.puml.svg``
     - same path
     - keep
     - explanations/execution_semantics / PR-J audit; Legacy simulation model or generated diagram kept at original path for compatibility; no page-specific copy created in PR-H.
   * - ``tutorials/simulation/hierarchy_execution.demo.py``
     - same path
     - keep
     - explanations/execution_semantics; Kept in old directory and literal-included by execution-order explanation; source-output pair remains stable.
   * - ``tutorials/simulation/hierarchy_execution.demo.py.txt``
     - same path
     - keep
     - explanations/execution_semantics; Kept in old directory and literal-included by execution-order explanation; source-output pair remains stable.

Resource cleanup note
~~~~~~~~~~~~~~~~~~~~~

All PR-H simulation resources are recorded as ``keep``. No resource source file
was moved, so generated ``*.txt``, ``*.puml``, ``*.png`` and ``*.svg`` outputs
were not regenerated in this PR. PR-J should reassess whether legacy-only
business examples or generated diagrams can be removed after the new pages and
old landing page are stable.

PR-I maintainer pages
---------------------

PR-I splits maintainer-facing content from the old ``tutorials/render``,
``tutorials/grammar``, and ``tutorials/structure`` pages into task guides,
explanations, and references. Old tutorial paths are retained as compatibility
landing pages.

Chapter migration records
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-I chapter migration
   :header-rows: 1

   * - Old location
     - Old section
     - New location
     - Action
     - Notes
   * - ``tutorials/render/index*.rst``
     - ``Template System Tutorial``
     - ``tutorials/render/index*.rst``
     - keep landing
     - Old URL now points to the new task, explanation, and reference pages.
   * - ``tutorials/render/index*.rst``
     - ``Understand The Template System`` / ``What The Template System Does`` / ``Current Rendering Boundaries`` / ``Template Directory Anatomy``
     - ``explanations/template_rendering/index*.rst``
     - merge
     - Conceptual renderer boundaries and directory anatomy became renderer explanation material.
   * - ``tutorials/render/index*.rst``
     - ``Build The Template Foundation`` / ``Jinja2 Essentials For Template Authors``
     - ``how_to/templates/index*.rst``
     - merge
     - Minimal Jinja2 and custom-template authoring guidance is now a task-oriented guide.
   * - ``tutorials/render/index*.rst``
     - ``The Role Of config.yaml``
     - ``reference/template_config/index*.rst``
     - move / merge
     - Config keys and accepted sections are reference facts.
   * - ``tutorials/render/index*.rst``
     - ``Use The Rendering Interfaces`` / ``Understanding expr_render`` / ``How expr_render Resolves Template Keys`` / ``How To Override Those Keys`` / ``Understanding stmt_render And stmts_render`` / ``Template Context: What You Can Access``
     - ``reference/template_config/index*.rst`` and ``explanations/template_rendering/index*.rst``
     - split
     - Exact filter/style facts moved to reference; rationale and boundaries moved to explanation.
   * - ``tutorials/render/index*.rst``
     - ``Design Real Templates`` / ``Generation Scale And Template Shape`` / ``Minimal Template From Scratch``
     - ``how_to/templates/index*.rst``
     - merge
     - The actionable part is now a custom-template authoring workflow.
   * - ``tutorials/render/index*.rst``
     - ``Built-In Templates`` and per-template subsections
     - ``tutorials/generation/index*.rst`` / ``reference/builtin_templates/index*.rst``
     - keep by reference
     - User-side built-in-template usage was already handled by PR-F; PR-I does not modify ``reference/builtin_templates``.
   * - ``tutorials/render/index*.rst``
     - ``Test And Consolidate`` / ``Testing Templates`` / renderer, generated-artifact, behavior-alignment, and CLI tests
     - ``how_to/templates/index*.rst`` and ``explanations/template_rendering/index*.rst``
     - merge
     - Testing workflow guidance moved to how-to; logic-placement rationale moved to explanation.
   * - ``tutorials/render/index*.rst``
     - ``When To Put Logic Where`` / ``Summary``
     - ``explanations/template_rendering/index*.rst`` and ``how_to/templates/index*.rst``
     - merge
     - Logic-placement decision rules are now explicit in the explanation and task pages.
   * - ``tutorials/grammar/index*.rst``
     - ``FCSTM Syntax Highlighting Guide``
     - ``tutorials/grammar/index*.rst``
     - keep landing
     - Old URL now points to grammar task, explanation, and reference pages.
   * - ``tutorials/grammar/index*.rst``
     - ``Overview`` / ``Using Pygments in Python`` / ``Using in Sphinx Documentation`` / ``Using TextMate Grammar`` / ``VS Code Extension``
     - ``reference/grammar_tooling/index*.rst`` and ``explanations/grammar_tooling/index*.rst``
     - split
     - Pygments aliases, Sphinx registration, TextMate/Sublime facts, VSCode feature facts, and VSIX install command are reference facts; layer responsibilities and synchronization rationale moved to explanation.
   * - ``tutorials/grammar/index*.rst``
     - ``Development Workflow`` / ``Testing and Verification`` / ``Validation and Testing`` / ``Development and Customization``
     - ``how_to/grammar_editor/index*.rst`` and ``reference/grammar_tooling/index*.rst``
     - merge / split
     - Maintainer task flow, VSCode local installation checks, focused ``verify-p0.*`` suites, and troubleshooting steps moved to the how-to; stable command names and feature maps moved to reference.
   * - ``tutorials/grammar/index*.rst``
     - ``Supported Syntax Elements`` and subsections such as keywords, operators, literals, built-ins, and import highlighting
     - ``reference/dsl/index*.rst`` / ``reference/grammar_tooling/index*.rst``
     - keep by reference
     - User-facing DSL facts are covered by PR-G; highlighter-specific path facts are in grammar tooling reference.
   * - ``tutorials/grammar/index*.rst``
     - ``Complete Example`` / troubleshooting sections / ``Related Resources`` / ``File Locations``
     - ``how_to/grammar_editor/index*.rst`` and ``reference/grammar_tooling/index*.rst``
     - merge / keep by reference
     - Troubleshooting became workflow guidance; file paths, related external documentation pointers, feature provider files, and validation command names became reference facts.
       The large all-syntax FCSTM example is intentionally not duplicated because user-facing syntax examples are already owned by PR-G's DSL reference split.
   * - ``tutorials/structure/index*.rst``
     - ``Project Structure Guide``
     - ``tutorials/structure/index*.rst``
     - keep landing
     - Old URL now points to architecture explanation and related pages.
   * - ``tutorials/structure/index*.rst``
     - ``Overview`` / ``Architecture Layers`` / ``Module Reference`` / layer subsections
     - ``explanations/architecture/index*.rst``
     - merge
     - Layer responsibilities are architecture explanation, not a tutorial.
   * - ``tutorials/structure/index*.rst``
     - ``Architecture Diagram`` / ``Processing Pipeline`` / ``User Interaction Flow`` / ``Dependency Relationships`` / ``Key Design Patterns``
     - ``explanations/architecture/index*.rst``
     - merge
     - Pipeline and dependency rationale moved to architecture explanation.

Resource migration records
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-I resource migration
   :header-rows: 1

   * - Old resource
     - New resource
     - Action
     - Notes
   * - ``tutorials/render/architecture.puml``
     - ``explanations/template_rendering/architecture.puml``
     - copy
     - Source copied so the template-rendering explanation owns its diagram source; old file kept for legacy compatibility.
   * - ``tutorials/render/architecture.puml.png``
     - ``explanations/template_rendering/architecture.puml.png``
     - copy
     - Generated PNG copied with its source-output pair.
   * - ``tutorials/render/architecture.puml.svg``
     - ``explanations/template_rendering/architecture.puml.svg``
     - copy
     - Generated SVG copied and referenced by the new explanation page.
   * - ``tutorials/render/core_component.puml``
     - ``explanations/template_rendering/core_component.puml``
     - copy
     - Source copied for renderer component diagram ownership.
   * - ``tutorials/render/core_component.puml.png``
     - ``explanations/template_rendering/core_component.puml.png``
     - copy
     - Generated PNG copied with its source-output pair.
   * - ``tutorials/render/core_component.puml.svg``
     - ``explanations/template_rendering/core_component.puml.svg``
     - copy
     - Generated SVG copied and referenced by the new explanation page.
   * - ``tutorials/render/model.puml``
     - ``explanations/template_rendering/model.puml``
     - copy
     - Source copied for model/rendering boundary diagram ownership.
   * - ``tutorials/render/model.puml.png``
     - ``explanations/template_rendering/model.puml.png``
     - copy
     - Generated PNG copied with its source-output pair.
   * - ``tutorials/render/model.puml.svg``
     - ``explanations/template_rendering/model.puml.svg``
     - copy
     - Generated SVG copied and referenced by the new explanation page.
   * - ``tutorials/render/render_flow.puml``
     - ``explanations/template_rendering/render_flow.puml``
     - copy
     - Source copied for renderer flow diagram ownership.
   * - ``tutorials/render/render_flow.puml.png``
     - ``explanations/template_rendering/render_flow.puml.png``
     - copy
     - Generated PNG copied with its source-output pair.
   * - ``tutorials/render/render_flow.puml.svg``
     - ``explanations/template_rendering/render_flow.puml.svg``
     - copy
     - Generated SVG copied and referenced by the new explanation page.
   * - ``tutorials/structure/structure.puml``
     - ``explanations/architecture/structure.puml``
     - copy
     - Source copied so architecture explanation owns the diagram source; old file kept for legacy compatibility.
   * - ``tutorials/structure/structure.puml.png``
     - ``explanations/architecture/structure.puml.png``
     - copy
     - Generated PNG copied with its source-output pair.
   * - ``tutorials/structure/structure.puml.svg``
     - ``explanations/architecture/structure.puml.svg``
     - copy
     - Generated SVG copied and referenced by the new explanation page.

Resource cleanup note
~~~~~~~~~~~~~~~~~~~~~

PR-I copies diagram source-output pairs into the explanation pages that now own
the diagrams. The old resources remain in ``tutorials/render`` and
``tutorials/structure`` so old links and historical generated files do not break.
PR-J may decide whether legacy copies should remain permanently.

PR-J final audit
----------------

Scope
~~~~~

PR-J performs the final information-architecture cleanup after PR-E through
PR-I. It does not re-own the migrated leaf-page bodies. Its job is to stabilize
the public navigation, keep old tutorial URLs useful, and verify that the
four-way Tutorials / How-to / Explanations / Reference split is discoverable in
both English and Chinese.

Navigation audit
~~~~~~~~~~~~~~~~

.. list-table:: PR-J navigation audit
   :header-rows: 1

   * - Area
     - Result
     - Notes
   * - Top-level index
     - cleaned
     - The Tutorials entry now points to the category index instead of listing
       every old tutorial and compatibility landing page.
   * - Tutorials category
     - added
     - ``tutorials/index*.rst`` now owns the guided learning path and keeps old
       landing pages in a hidden compatibility toctree.
   * - How-to category
     - cleaned
     - The migration-skeleton wording was replaced by stable task-guide
       wording.
   * - Explanations category
     - cleaned
     - The migration-skeleton wording was replaced by stable explanation
       wording.
   * - Reference category
     - cleaned
     - The migration-skeleton wording was replaced by a reference map, with
       generated API documentation retained as the last toctree item.

Compatibility landing audit
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This table only covers old tutorial URLs that are now compatibility landing
pages. The guided tutorial pages that still own tutorial bodies remain in the
visible ``tutorials/index*.rst`` path: ``quick_start``, ``dsl``,
``simulation``, ``inspect``, ``generation`` and ``visualization``.

.. list-table:: Compatibility landing URL status after PR-J
   :header-rows: 1

   * - Old URL
     - Status
     - Current role
   * - ``tutorials/installation/``
     - keep landing
     - Points to the installation how-to and quick start.
   * - ``tutorials/cli/``
     - keep landing
     - Points to CLI workflows, CLI reference, installation, and quick start.
   * - ``tutorials/render/``
     - keep landing
     - Points to template-author tasks, renderer explanation, template config
       reference, and built-in template usage.
   * - ``tutorials/grammar/``
     - keep landing
     - Points to grammar/editor tasks, grammar tooling explanation, grammar
       tooling reference, and DSL reference.
   * - ``tutorials/structure/``
     - keep landing
     - Points to architecture, execution semantics, template rendering, and API
       documentation.

Resource cleanup decision
~~~~~~~~~~~~~~~~~~~~~~~~~

PR-J keeps legacy resources under their original ``tutorials/*`` directories.
Some resources are still literal-included by new pages, and the rest remain as
stable old-link/source-output pairs after the information-architecture split.
Deleting or moving them would create churn without improving the public
documentation structure, so any deeper resource pruning should be handled by a
future focused cleanup PR with generated-resource regeneration evidence.
PR-K DSL full-coverage audit
----------------------------

This section records the PR-K DSL coverage closure. It is intentionally an audit log for reviewers, not a public navigation page.

DSL feature checklist
~~~~~~~~~~~~~~~~~~~~~

.. csv-table:: DSL feature checklist
   :header: "feature_id", "family", "fact source", "new owner pages", "verification"

   dsl-top-level-root,top-level,GrammarParser.g4 state_machine_dsl / def_assignment,"tutorials/dsl, reference/dsl",first_thermostat.fcstm inspect
   dsl-import-preamble,import,preamble_program / constant_definition / initial_assignment,"how_to/dsl, reference/dsl, explanations/dsl_semantics","parse_preamble helper only; not normal .fcstm entry point"
   dsl-state-leaf-composite-pseudo,state,state_definition / E_PSEUDO_NOT_LEAF,"tutorials/dsl, how_to/dsl, reference/dsl, explanations/dsl_semantics",pseudo_state_demo inspect
   dsl-transition-normal,transition,transition_definition,"tutorials/dsl, how_to/dsl, reference/dsl",operation_blocks_complete.fcstm inspect
   dsl-transition-forced,transition,transition_force_definition,"how_to/dsl, reference/dsl, explanations/dsl_semantics",forced_transitions inspect
   dsl-transition-combo,transition,combo_transition_trigger / entry_combo_transition_trigger / W_COMBO_*,"how_to/dsl, reference/dsl, explanations/dsl_semantics","combo_transitions.fcstm inspect, combo_duplicate_event.fcstm inspect, event_guard_mixed_invalid.fcstm.txt parse-error fixture"
   dsl-event-scopes,event,event_definition / chain_id,"tutorials/dsl, how_to/dsl, reference/dsl, explanations/dsl_semantics",event_scoping examples inspect
   dsl-expression-reference,expression,num_expression / cond_expression,"how_to/dsl, reference/dsl, explanations/dsl_semantics",expression_condition_ternary.fcstm inspect
   dsl-operation-blocks,operation,operational_statement / if_statement,"how_to/dsl, reference/dsl",operation_blocks_complete.fcstm inspect
   dsl-lifecycle-forms,lifecycle,enter_definition / during_definition / exit_definition,"tutorials/dsl, how_to/dsl, reference/dsl, explanations/dsl_semantics",abstract_reference_demo inspect
   dsl-aspect-forms,aspect,during_aspect_definition,"how_to/dsl, reference/dsl, explanations/dsl_semantics",hierarchy_execution.fcstm inspect
   dsl-diagnostics-risk,diagnostics,diagnostics/codes.yaml / analyzers,"how_to/dsl, reference/dsl, diagnostics_codes",risk wording line audit


New DSL example resources added by the repair pass
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Added DSL examples
   :header-rows: 1
   :widths: 30 35 35

   * - Resource
     - Purpose
     - Expected diagnostics
   * - ``tutorials/dsl/combo_transitions.fcstm``
     - Normal combo, entry combo, guard alias, root event term, effects, and pseudo relay provenance.
     - none
   * - ``tutorials/dsl/operation_blocks_complete.fcstm``
     - Block-local temporaries, ``if`` / ``else if`` / ``else``, empty statement, and ternary assignment.
     - none
   * - ``tutorials/dsl/expression_condition_ternary.fcstm``
     - Condition operators including implication, ``xor``, ``iff``, and ternary expressions.
     - none
   * - ``tutorials/dsl/combo_duplicate_event.fcstm``
     - Intentional duplicate combo event diagnostic.
     - ``W_COMBO_DUPLICATE_EVENT`` and ``I_TRANSITION_NEVER_EVENT_TRIGGERED``
   * - ``tutorials/dsl/event_guard_mixed_invalid.fcstm.txt``
     - Intentional parser-error fixture for ordinary event syntax plus ordinary guard syntax.
     - parse error excerpt: ``Unexpected token 'if'``
   * - ``tutorials/dsl/guard_vars_never_change.fcstm``
     - Intentional initial-value-only guard diagnostic.
     - ``W_UNWRITTEN_READ_VAR``, ``W_GUARD_VARS_NEVER_CHANGE``, and ``I_TRANSITION_NEVER_EVENT_TRIGGERED``
   * - ``tutorials/dsl/during_const_assign.fcstm``
     - Intentional constant ``during`` assignment diagnostic.
     - ``W_DURING_CONST_ASSIGN``
   * - ``tutorials/dsl/numeric_target_range.fcstm``
     - C/C++ target-profile numeric range warning.
     - ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE``

Old DSL heading migration table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. csv-table:: Old DSL heading migration
   :header: "old position", "old heading", "new position", "handling", "verification"

   L1,PyFCSTM DSL Syntax Tutorial,"split overview: tutorials/dsl, how_to/dsl, reference/dsl, explanations/dsl_semantics",split,manual fact check against current grammar/model
   L8,Overview,tutorial overview or migration audit; stale prose removed when not DSL-specific,merged/stale,manual fact check against current grammar/model
   L13,What You'll Learn,tutorial overview or migration audit; stale prose removed when not DSL-specific,merged/stale,manual fact check against current grammar/model
   L23,Language Structure,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L26,Program Organization,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L45,Variable Definitions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L48,Syntax,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L70,Correct Usage,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L113,Semantic Rules,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L131,Common Errors,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L170,State Definitions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L176,Syntax Types,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L193,Leaf States,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L235,Composite States,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L323,Pseudo States,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L367,Named States,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L380,Semantic Rules,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L400,Common Errors,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L467,Transition Definitions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L479,Transition Types,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L495,Entry Transitions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L521,Normal Transitions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L553,Exit Transitions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L578,Combo Trigger Syntax,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L674,Forced Transitions,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L848,Event Definitions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L858,Explicit Event Definitions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L921,Event Scoping,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L943,Scoping Mechanisms,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L954,Local Events (`::` operator),covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L994,Chain Events (`:` operator),covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1035,Absolute Events (`/` prefix),covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1085,Complete Comparison Example,checked-in .fcstm literalinclude or migration audit replacement,kept/replaced,manual fact check against current grammar/model
   L1167,Guard Conditions and Effects,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L1170,Guard Conditions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L1218,Transition Effects,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1248,Operation Blocks and Temporary Variables,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L1296,If Blocks Inside Operation Blocks,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L1369,Practical Example: Heating Controller,checked-in .fcstm literalinclude or migration audit replacement,kept/replaced,manual fact check against current grammar/model
   L1402,Combined Guards and Effects,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1421,Complete Example,checked-in .fcstm literalinclude or migration audit replacement,kept/replaced,manual fact check against current grammar/model
   L1437,Semantic Rules,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L1457,Common Errors,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L1528,Expression System,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L1540,Expression Hierarchy,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1579,Literal Values,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1612,Operators,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1659,Arithmetic vs Logical Expression Separation,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1710,Mathematical Functions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1753,Conditional Expressions,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L1793,Complete Expression Example,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1809,Semantic Rules,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L1828,Common Errors,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L1872,Lifecycle Actions,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L1890,Action Types,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1912,Enter Actions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L1988,During Actions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2062,Exit Actions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2114,Aspect Actions,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2153,Hierarchical Execution Order,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L2221,Abstract and Reference Actions Example,how_to/dsl task section plus explanations/dsl_semantics semantic section,split,manual fact check against current grammar/model
   L2237,Semantic Rules,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L2257,Common Errors,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L2335,Real-World Example: Smart Thermostat,checked-in .fcstm literalinclude or migration audit replacement,kept/replaced,manual fact check against current grammar/model
   L2379,Comment Styles,tutorial overview or migration audit; stale prose removed when not DSL-specific,merged/stale,manual fact check against current grammar/model
   L2420,Documentation Best Practices,tutorial overview or migration audit; stale prose removed when not DSL-specific,merged/stale,manual fact check against current grammar/model
   L2490,Semantic Validation Rules,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L2493,Comprehensive Validation,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2526,Error Handling,how_to/dsl diagnostics task and reference/diagnostics_codes links,merged,manual fact check against current grammar/model
   L2554,Import Assembly,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L2557,Overview,tutorial overview or migration audit; stale prose removed when not DSL-specific,merged/stale,manual fact check against current grammar/model
   L2570,Minimal Import,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2602,Using ``named`` on imports,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2618,Variable Mapping with ``def``,reference/dsl exact facts plus how_to/dsl recipes,split,manual fact check against current grammar/model
   L2634,Event Mapping with ``event``,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2649,Directory-organized subsystem entry via ``main.fcstm``,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2689,Common Mistakes,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2701,Public Entry Points Stay the Same,covered by DSL coverage matrix,covered,manual fact check against current grammar/model
   L2716,Summary,tutorial overview or migration audit; stale prose removed when not DSL-specific,merged/stale,manual fact check against current grammar/model

Old DSL resource migration table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The old DSL page contains 108 resource directives when counted with ``grep -cE "^\s*\.\.\s+(literalinclude|image|code-block)::"``. Every directive is recorded below with an old line number so reviewers can recount it.

.. csv-table:: Old DSL resource directives
   :header: "old line", "type", "target/language", "old section", "new position", "handling", "verification"

   L31,code-block,fcstm,Program Organization,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L53,code-block,fcstm,Syntax,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L75,code-block,fcstm,Correct Usage,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L85,code-block,fcstm,Correct Usage,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L95,code-block,fcstm,Correct Usage,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L136,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L151,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L181,code-block,fcstm,Syntax Types,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L200,code-block,fcstm,Leaf States,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L221,code-block,fcstm,Leaf States,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L242,code-block,fcstm,Composite States,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L271,code-block,fcstm,Composite States,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L330,code-block,fcstm,Pseudo States,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L340,literalinclude,pseudo_state_demo.fcstm,Pseudo States,explanations/dsl_semantics pseudo/combo relay and reference/dsl state forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L372,code-block,fcstm,Named States,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L405,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L436,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L484,code-block,fcstm,Transition Types,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L504,code-block,fcstm,Entry Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L530,code-block,fcstm,Normal Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L562,code-block,fcstm,Exit Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L590,code-block,fcstm,Combo Trigger Syntax,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L607,code-block,fcstm,Combo Trigger Syntax,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L624,code-block,fcstm,Combo Trigger Syntax,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L640,code-block,fcstm,Combo Trigger Syntax,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L681,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L698,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L709,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L734,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L768,literalinclude,forced_transitions.fcstm,Forced Transitions,how_to/dsl forced transitions and reference/dsl transition forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L783,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L800,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L825,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L837,code-block,fcstm,Forced Transitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L865,code-block,fcstm,Explicit Event Definitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L871,code-block,fcstm,Explicit Event Definitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L892,code-block,fcstm,Explicit Event Definitions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L929,code-block,fcstm,Event Scoping,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L966,code-block,fcstm,Local Events (`::` operator),reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L979,code-block,fcstm,Local Events (`::` operator),reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1006,code-block,fcstm,Chain Events (`:` operator),reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1020,code-block,fcstm,Chain Events (`:` operator),reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1047,code-block,fcstm,Absolute Events (`/` prefix),reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1071,code-block,fcstm,Absolute Events (`/` prefix),reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1090,literalinclude,event_scoping_complete.fcstm,Complete Comparison Example,how_to/dsl event scope and reference/dsl event scopes,kept as literalinclude,pyfcstm inspect where file is a full model
   L1143,code-block,fcstm,Complete Comparison Example,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1187,code-block,fcstm,Guard Conditions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1227,code-block,fcstm,Transition Effects,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1262,code-block,fcstm,Operation Blocks and Temporary Variables,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1280,code-block,fcstm,Operation Blocks and Temporary Variables,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1289,code-block,fcstm,Operation Blocks and Temporary Variables,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1308,code-block,fcstm,If Blocks Inside Operation Blocks,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1331,code-block,fcstm,If Blocks Inside Operation Blocks,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1343,code-block,fcstm,If Blocks Inside Operation Blocks,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1379,code-block,fcstm,Practical Example: Heating Controller,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1407,code-block,fcstm,Combined Guards and Effects,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1426,literalinclude,guards_and_effects.fcstm,Complete Example,archive-only legacy example; current coverage uses operation_blocks_complete.fcstm,replaced in current docs,legacy file remains inspectable for migration audit
   L1462,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1487,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1545,code-block,fcstm,Expression Hierarchy,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1584,code-block,fcstm,Literal Values,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1593,code-block,fcstm,Literal Values,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1604,code-block,fcstm,Literal Values,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1647,code-block,fcstm,Operators,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1673,code-block,fcstm,Arithmetic vs Logical Expression Separation,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1687,code-block,fcstm,Arithmetic vs Logical Expression Separation,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1717,code-block,fcstm,Mathematical Functions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1736,code-block,fcstm,Mathematical Functions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1745,code-block,fcstm,Mathematical Functions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1765,code-block,fcstm,Conditional Expressions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1785,code-block,fcstm,Conditional Expressions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1798,literalinclude,expression_demo.fcstm,Complete Expression Example,archive-only legacy example; current coverage uses expression_condition_ternary.fcstm,replaced in current docs,legacy file remains inspectable for migration audit
   L1833,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1849,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1895,code-block,fcstm,Action Types,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1919,code-block,fcstm,Enter Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1940,code-block,fcstm,Enter Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1959,code-block,fcstm,Enter Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L1997,code-block,fcstm,During Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2011,code-block,fcstm,During Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2036,code-block,fcstm,During Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2069,code-block,fcstm,Exit Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2087,code-block,fcstm,Exit Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2101,code-block,fcstm,Exit Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2121,code-block,fcstm,Aspect Actions,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2158,literalinclude,hierarchy_execution.fcstm,Hierarchical Execution Order,explanations/dsl_semantics or execution_semantics cross-reference,kept as literalinclude,pyfcstm inspect where file is a full model
   L2226,literalinclude,abstract_reference_demo.fcstm,Abstract and Reference Actions Example,how_to/dsl lifecycle and reference/dsl lifecycle forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2263,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2296,code-block,fcstm,Common Errors,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2340,literalinclude,thermostat_example.fcstm,Real-World Example: Smart Thermostat,tutorials/dsl advanced complete resource and migration audit; first runnable replaced by first_thermostat.fcstm,kept as checked resource but no longer first runnable,pyfcstm inspect where file is a full model; first runnable inspect is warning-free
   L2386,code-block,fcstm,Comment Styles,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2396,code-block,fcstm,Comment Styles,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2405,code-block,fcstm,Comment Styles,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2425,code-block,fcstm,Documentation Best Practices,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2441,code-block,fcstm,Documentation Best Practices,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2475,code-block,fcstm,Documentation Best Practices,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2547,code-block,fcstm,Error Handling,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2575,literalinclude,import_worker.fcstm,Minimal Import,how_to/dsl imports and reference/dsl import forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2581,literalinclude,import_host_basic.fcstm,Minimal Import,how_to/dsl imports and reference/dsl import forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2593,image,import_host_basic.fcstm.puml.svg,Minimal Import,follows same-named .fcstm owner or lifecycle explanation resource,kept as image resource,docs build and image link check
   L2608,code-block,fcstm,Using ``named`` on imports,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2624,literalinclude,import_host_mapped.fcstm,Variable Mapping with ``def``,how_to/dsl imports and reference/dsl import forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2657,literalinclude,import_host_directory.fcstm,Directory-organized subsystem entry via ``main.fcstm``,how_to/dsl imports and reference/dsl import forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2663,literalinclude,import_line/main.fcstm,Directory-organized subsystem entry via ``main.fcstm``,how_to/dsl imports and reference/dsl import forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2669,literalinclude,import_line/subsystems/robot.fcstm,Directory-organized subsystem entry via ``main.fcstm``,how_to/dsl imports and reference/dsl import forms,kept as literalinclude,pyfcstm inspect where file is a full model
   L2675,code-block,fcstm,Directory-organized subsystem entry via ``main.fcstm``,reference/how-to prose or checked-in literalinclude replacement,audited as legacy inline block; fragment unless reintroduced as validated full block,full reintroduced blocks parse/inspect; fragments marked partial
   L2684,image,import_host_directory.fcstm.puml.svg,Directory-organized subsystem entry via ``main.fcstm``,follows same-named .fcstm owner or lifecycle explanation resource,kept as image resource,docs build and image link check
   L2707,code-block,bash,Public Entry Points Stay the Same,tutorial/how-to command snippet if still useful,audited command snippet,manual command relevance check

Inline code block audit policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Legacy inline ``code-block:: fcstm`` directives are not blindly copied as runnable models. PR-K treats them as fragments unless the implementation reintroduces a block as a complete FCSTM model. Any complete reintroduced inline model must be parse/model/inspect checked; fragments must be explicitly described as fragments or partial syntax examples.

Image and generated resource policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``*.fcstm.puml``, ``*.fcstm.puml.svg`` and ``*.fcstm.puml.png`` resources follow the same-named ``.fcstm`` owner. Lifecycle-only PUML resources stay with lifecycle explanations or task guides. No orphan diagram should remain in the tutorial page after the split.

Risk wording audit
~~~~~~~~~~~~~~~~~~~

All new or modified lines mentioning ``C/C++``, ``Python``, ``risk`` or ``风险`` must be traceable to ``pyfcstm/diagnostics/codes.yaml`` or a diagnostics analyzer, or be marked as non-target-risk prose. This keeps C/C++ deployment-profile warnings from being presented as Python generated-runtime failures.

Verification log
~~~~~~~~~~~~~~~~

* ``make rst_auto`` must be run before commit.
* All ``docs/source/**/*.fcstm`` files must pass ``pyfcstm inspect`` batch validation.
* English and Chinese Sphinx HTML builds must pass with no ``class="problematic"`` markup leaks.
* Inline full FCSTM blocks must be enumerated and verified; fragments must be marked partial.
* Third-round PR body reviews are recorded on PR #338 and found no C/I blockers before implementation.

PR-N simulation hardening record
================================

PR-N is an additive hardening pass on the simulation pages created by PR-H. It
keeps existing tutorial, how-to and execution-semantics URLs stable, creates the
new reference owner for exact simulator facts, and records that no legacy
simulation resource is moved by this pass.

.. list-table:: PR-N affected-page record
   :header-rows: 1

   * - Page or resource
     - PR-H state
     - PR-N action
     - URL/resource movement
   * - ``tutorials/simulation/index*.rst``
     - First-run tutorial already exists with checked batch and Python output.
     - Add minimal ``CycleResult`` pointer and link exact facts to
       ``reference/simulation/``.
     - No URL move.
   * - ``how_to/simulation/index*.rst``
     - Batch, REPL, events, hot start, handlers, export, settings and debugging
       recipes already exist.
     - Keep task recipes and point full command/setting/export facts to
       ``reference/simulation/``.
     - No URL move.
   * - ``explanations/execution_semantics/index*.rst``
     - Core cycle, lifecycle, aspect, validation and hot-start explanations
       already exist.
     - Add ordering and fixture-family evidence matrices, plus pseudo/combo and
       terminal-boundary strengthening.
     - No URL move.
   * - ``reference/simulation/index*.rst``
     - Missing before PR-N; ``reference/index*`` explicitly said no dedicated
       simulation reference existed.
     - New exact-fact owner for CLI, REPL, settings, event input, history/export,
       Python API, ``CycleResult`` and public failures.
     - New URL added.
   * - ``docs/source/tutorials/simulation/*.demo.*``
     - Existing checked source-output pairs.
     - Reused as evidence without changing output in this pass.
     - No resource move and no generated-output refresh.

Verification note: this pass is prose and index hardening only. Existing demo
outputs are referenced unchanged; if a later PR modifies any ``*.demo.*`` source
or output, that PR must record the exact source-output regeneration command.

PR-Q command, visualization, architecture, and grammar-tooling strengthening
----------------------------------------------------------------------------

Scope
~~~~~

PR-Q strengthens the command-line, installation, visualization, architecture,
and grammar/editor-tooling documentation after the earlier information
architecture split. It does not move public pages or tutorial resources; it adds
in-place depth, exact reference coverage, and tools-only drift checks for CLI and
visualization facts.

Chapter records
~~~~~~~~~~~~~~~

.. list-table:: PR-Q chapter updates
   :header-rows: 1

   * - Location
     - Action
     - Notes
   * - ``how_to/installation/index*.rst``
     - strengthen in place
     - Clarifies all-in-one package install, external renderer boundaries, virtualenv/CI patterns, smoke checks, and troubleshooting.
   * - ``how_to/cli_workflows/index*.rst``
     - strengthen in place
     - Expands command selection, simulation, inspect, generation, PlantUML source, rendered diagram, reproducibility, and layer-by-layer troubleshooting workflows.
   * - ``reference/cli/index*.rst``
     - strengthen in place
     - Adds complete command/option markers, output/failure contracts, examples, and command boundary taxonomy.
   * - ``how_to/visualization/index*.rst``
     - strengthen in place
     - Expands source-vs-rendered selection, preset comparison, focus patterns, renderer selection, CI stability, Python API use, and troubleshooting.
   * - ``reference/visualization_options/index*.rst``
     - strengthen in place
     - Adds complete ``PlantUMLOptions`` field map, typed ``-c`` value syntax, renderer/file facts, environment variables, and behavior boundaries.
   * - ``explanations/architecture/index*.rst``
     - strengthen in place
     - Explains the model-centered pipeline, command flow, template asset split, diagnostics boundary, simulation/template relationship, visualization split, and generated-asset rules.
   * - ``how_to/grammar_editor/index*.rst``
     - strengthen in place
     - Expands grammar, highlighter, VSCode, LLM guide, and validation workflow guidance.
   * - ``reference/grammar_tooling/index*.rst``
     - strengthen in place
     - Adds canonical file map, command map, Pygments/TextMate/VSCode facts, verification suites, operator ordering, and keyword update checklist.
   * - ``explanations/grammar_tooling/index*.rst``
     - strengthen in place
     - Explains parser/model/highlighter/editor/docs coupling and drift risks.

Tooling records
~~~~~~~~~~~~~~~

.. list-table:: PR-Q tools-only checks
   :header-rows: 1

   * - Tool
     - Action
     - Purpose
   * - ``tools/check_cli_reference_docs.py``
     - add
     - Verifies CLI reference synchronization markers against the Click command tree and human-documented command boundary tokens.
   * - ``tools/check_visualization_reference_docs.py``
     - add
     - Verifies visualization reference markers against ``PlantUMLOptions`` fields, renderer/type constants, environment facts, parser forms, and behavior boundary tokens.

Resource migration records
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-Q resource migration
   :header-rows: 1

   * - Resource
     - Action
     - Notes
   * - ``docs/source/tutorials/visualization/output_*.puml`` and rendered images
     - keep
     - Existing generated figures are reused by the strengthened visualization how-to; no regeneration was required.
   * - ``docs/source/tutorials/installation/*.demo.*`` and outputs
     - keep
     - Existing installation examples remain in their tutorial directory and are reused by the installation how-to.
   * - All other tutorial/demo/diagram resources
     - keep
     - PR-Q is an in-place prose and tooling update with no public URL or resource movement.

Validation note
~~~~~~~~~~~~~~~

Because PR-Q does not edit ``.fcstm``, ``.puml``, ``.demo.*``, ``.plot.*``, or
notebook source resources, no documentation resource regeneration is expected.
The required verification is the documentation build plus the two new tools-only
reference drift checks.

PR-Q depth-gate hardening update
--------------------------------

Scope
~~~~~

After PR-Q initially reached a CI-green state, review tightened the documentation
quality bar. This follow-up records the additional hardening: CLI and
visualization references were expanded with example-heavy evidence cards,
per-option decision cards, and per-field scenario matrices; how-to pages gained
concrete command signals and task acceptance cards; explanations gained
trace-based boundary reasoning; and the documentation authoring guide now treats
substantial docs PR depth as a merge-blocking gate.

Resource update records
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PR-Q depth-gate resource update
   :header-rows: 1

   * - Resource
     - Action
     - Regeneration command
     - Notes
   * - ``docs/source/explanations/architecture/structure.puml``
     - update
     - hand-edited source, then regenerated SVG/PNG with ``python -m plantumlcli -R -t svg -o structure.puml.svg -O docs/source/explanations/architecture docs/source/explanations/architecture/structure.puml`` and ``python -m plantumlcli -R -t png -o structure.puml.png -O docs/source/explanations/architecture docs/source/explanations/architecture/structure.puml``
     - The figure now shows the model-centered pipeline, inspect/simulate/render/visualize consumers, packaged template split, external renderer/toolchain boundaries, and generated artifacts.
   * - ``docs/source/explanations/architecture/structure.puml.svg`` and ``structure.puml.png``
     - regenerate
     - same commands as above
     - Visual inspection confirmed the regenerated diagram is readable at full resolution; Sphinx HTML visual placement is verified by the PR-Q docs build.
   * - Other ``.fcstm``, ``.demo.*``, ``.puml`` and generated documentation resources
     - keep
     - not applicable
     - No other source-output resource pair was moved or regenerated in this hardening update.

PR-Q strict authoring-gate follow-up
------------------------------------

Scope
~~~~~

The second PR-Q follow-up records the explicit reviewer requirement that command,
visualization, how-to, and explanation pages must be reviewed for human depth,
not merely for Sphinx or marker-check success. It strengthens the long-term
authoring policy and adds more concrete examples, output signals, side effects,
failure boundaries, and mechanism traces to the pages most likely to be copied
into user projects.

Page updates
~~~~~~~~~~~~

.. list-table:: PR-Q strict-gate page updates
   :header-rows: 1

   * - Location
     - Action
     - Notes
   * - ``docs/documentation_authoring.md``
     - strengthen policy
     - Adds a zero-exception ready/merge rule requiring human depth evidence for substantial documentation PRs.
   * - ``CLAUDE.md``
     - strengthen policy pointer
     - States directly that missing any applicable authoring-guide requirement blocks ready and merge, even when CI is green.
   * - ``how_to/cli_workflows/index*.rst``
     - add concrete task evidence
     - Adds the quick-start traffic-light source as a real sample, with acceptance cards covering command, output, side effect, and first troubleshooting step.
   * - ``reference/cli/index*.rst``
     - add reference-grade examples
     - Adds valid/invalid examples for each command family and names the layer that owns each failure.
   * - ``how_to/visualization/index*.rst``
     - add visual task evidence
     - Adds the visualization tutorial source as a real sample, visual task acceptance cards, and HTML/visual-review expectations.
   * - ``reference/visualization_options/index*.rst``
     - add scenario coverage
     - Adds option-combination scenarios so field rows are backed by concrete effects and counterexamples.
   * - ``explanations/grammar_tooling/index*.rst``
     - add mechanism traces
     - Adds syntax-support trace and boundary examples from tokenization through docs/LLM guidance.

Resource update records
~~~~~~~~~~~~~~~~~~~~~~~

No generated documentation resources are moved or regenerated by this follow-up.
The new examples reuse existing checked-in sources under
``docs/source/tutorials/quick_start/`` and ``docs/source/tutorials/visualization/``.
Validation therefore focuses on reST/Sphinx correctness, reference drift checks,
and visual inspection of existing generated figures in the rebuilt HTML.
