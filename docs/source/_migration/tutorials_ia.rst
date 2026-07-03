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

PR-G placeholder
----------------

No records yet.

PR-H placeholder
----------------

No records yet.

PR-I placeholder
----------------

No records yet.
