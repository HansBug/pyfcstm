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

PR-F placeholder
----------------

No records yet.

PR-G placeholder
----------------

No records yet.

PR-H placeholder
----------------

No records yet.

PR-I placeholder
----------------

No records yet.
