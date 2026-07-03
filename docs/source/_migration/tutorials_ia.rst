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
     - Retained as the first complete example through ``thermostat_example.fcstm``.
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
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/event_scoping_comparison.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
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
     - FCSTM source; reference/dsl; reused by expression and operator facts; path kept stable.
   * - ``tutorials/dsl/expression_demo.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; reference/dsl; reused by expression and operator facts; path kept stable.
   * - ``tutorials/dsl/expression_demo.fcstm.puml.png``
     - same path
     - keep
     - generated image output; reference/dsl; reused by expression and operator facts; path kept stable.
   * - ``tutorials/dsl/expression_demo.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; reference/dsl; reused by expression and operator facts; path kept stable.
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
     - FCSTM source; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/guards_and_effects.fcstm.puml``
     - same path
     - keep
     - PlantUML source output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/guards_and_effects.fcstm.puml.png``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
   * - ``tutorials/dsl/guards_and_effects.fcstm.puml.svg``
     - same path
     - keep
     - generated image output; how_to/dsl + reference/dsl; reused by DSL task recipes and syntax facts; path kept stable.
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
