"""
Roadmap for repository maintenance tools.

The :mod:`tools` package contains scripts that support packaging,
maintenance, research, and release workflows around pyfcstm. These modules are
kept outside :mod:`pyfcstm` so they can inspect the repository layout directly
without becoming part of the runtime library API.

.. list-table:: Tool areas
   :header-rows: 1

   * - Area
     - Representative modules
     - Responsibility
   * - Template packaging
     - :mod:`tools.package_templates`
     - Build distributable built-in template archives.
   * - Runtime inventories
     - :mod:`tools.inventory_simulate_semantics`
     - Summarize simulator and generated-runtime fixture coverage.
   * - Numeric render-semantics research
     - :mod:`tools.numeric_render_mapping`, :mod:`tools.numeric_render_probe`
     - Capture renderer/template mappings and provide probe entry points for
       cross-language numeric semantics research.

Example::

    >>> import tools
    >>> tools.__name__
    'tools'
"""
