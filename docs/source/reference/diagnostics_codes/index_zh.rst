.. _sec-reference-diagnostics-codes-zh:

诊断码参考
==========

诊断码（diagnostic code）是 ``pyfcstm inspect``、CI 过滤、IDE 集成和 LLM 修复提示使用的稳定标识。权威注册表是加载后的
``pyfcstm.diagnostics.codes.CODE_REGISTRY`` 对象。原始 ``codes.yaml`` 条目可能省略 ``emit_tier`` 或 ``capability``；加载器会把这些缺省值补成
``static_pipeline`` 和 ``pure_static``。

本页是参考资料，不是教程。当你已经从检查输出中拿到 ``code`` 值，并需要确认它的含义、稳定字段、发射路径、修复方向或边界时，应该查本页。

如何阅读一个诊断
----------------

一个诊断对象会把稳定标识、源码位置和修复上下文放在一起：

.. list-table:: 诊断对象字段
   :header-rows: 1
   :widths: 22 78

   * - 字段
     - 含义
   * - ``code``
     - 稳定标识，例如 ``W_COMBO_DUPLICATE_EVENT``。
   * - ``severity``
     - ``error`` 会阻塞模型构建；``warning`` 指出有风险或可疑的设计；``info`` 是非阻塞观察。
   * - ``message``
     - 面向人的简短说明。
   * - ``span``
     - 分析器能够定位具体对象时给出的源码范围。
   * - ``refs``
     - 工具和 LLM 修复提示使用的结构化载荷。下面每个诊断码都会列出预期字段。
   * - ``suggested_fix``
     - 当注册表能描述安全局部编辑形状时提供的可选编辑元数据。

发射层级
--------

.. list-table:: 发射层级
   :header-rows: 1
   :widths: 24 76

   * - 层级
     - 含义
   * - ``static_pipeline``
     - 默认静态检查或模型诊断路径会产生。
   * - ``verify_pipeline``
     - 只有运行封闭且在策略预算内的结构或局部 SMT 验证算法时才会产生，通常需要 ``--enable-verify``。
   * - ``lookup_api``
     - 由显式解析 API 产生，不属于默认静态检查输出。
   * - ``partial_static_pipeline``
     - 注册表契约已经存在，但当前不是每个前端或后端都会发射。
   * - ``catalog_only``
     - 只保留兼容契约；当前正常 pyfcstm 路径不应发射。

已弃用的兼容别名
----------------

历史名称 ``W_DEADLOCK_LEAF`` 仍保留在 ``CODE_REGISTRY`` 中，作为
``W_LEAF_NO_OUTGOING_TRANSITION`` 的弃用别名。新的分析器只发射规范名称；
读取历史 JSON 或 LLM 报告的消费者可以通过 ``resolve_diagnostic_code`` 和
``canonicalize_diagnostic_code`` 继续识别旧名称。该别名计划在 ``1.0.0``
移除，计划由 ``make deprecation_check`` 自动检查。

示例类型
--------

下面每个诊断码至少有三个可见示例或边界示例。源码中还带有隐藏的 ``diagnostics-example`` 标记，供
``python tools/check_diagnostics_reference_docs.py --check`` 检查覆盖率。

.. list-table:: 示例类型
   :header-rows: 1
   :widths: 24 76

   * - 类型
     - 含义
   * - ``repro_cli``
     - 期望可作为成功检查报告复现；使用
       ``pyfcstm inspect -i <file> --format json`` 并读取 ``diagnostics[]``。
   * - ``cli_error``
     - 期望可作为受控命令行或模型校验错误复现。当前检查格式会在成功
       JSON 报告产生前以非零状态退出，因此应断言错误输出和退出状态，而不是
       ``diagnostics[]``。
   * - ``repro_api``
     - 期望可通过显式 Python API 调用复现。
   * - ``verify_opt_in``
     - 需要可选验证集成，并可能受求解器策略或超时影响。
   * - ``boundary_only``
     - 说明修复方向或反例边界，不代表单独的命令行触发路径。
   * - ``compatibility_only``
     - 说明历史或跨版本行为；当前正常路径不应发射。

机器覆盖检查
------------

编辑本页或诊断注册表后，运行这个仓库本地维护检查：

.. code-block:: bash

   python tools/check_diagnostics_reference_docs.py --check

该检查会验证诊断码集合、严重级别、发射层级、能力层级、源码对象、``refs`` 字段、双语覆盖、每个诊断码的复现边界标记和示例标记数量。它不证明示例在语义上真的不趋同；PR review 仍需要人工抽样。

.. _diag-region-examples-zh:

在终端里看区域诊断
------------------

下面的目录逐个说明诊断码。本节在本页旁边的模型上运行与区域有关的诊断码，因此每条信息和每个退出状态都是真实的。故意写成不合法的模型使用扩展名 ``.fcstm.txt``\ ，它们出现在各自诊断码的目录条目里，或紧挨在运行它们的命令之前；它们是负例，请勿当作起点复制。

``pyfcstm inspect`` 把 ``E_REGION_STRUCTURE`` 报成一行，其中带有出错构造所在的行号。修复后的模型，以及历史放在区域子树之外的模型都会被接受；完整报告很长，这里只保留摘要里的 ``regions:`` 一行。

.. literalinclude:: region_diag_history_boundary.fcstm.txt
   :language: fcstm
   :caption: region_diag_history_boundary.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_empty_region_fixed.fcstm
   :language: fcstm
   :caption: region_diag_empty_region_fixed.fcstm

.. code-block:: console

   $ pyfcstm inspect -i region_diag_empty_region.fcstm.txt
   Invalid state machine model in region_diag_empty_region.fcstm.txt: Invalid region structure at Root.Empty (empty_region). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_history_boundary.fcstm.txt
   Invalid state machine model in region_diag_history_boundary.fcstm.txt: Invalid region structure at Root.P (history_boundary). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_empty_region_fixed.fcstm
   ...
     regions: 1
   ...
   $ pyfcstm inspect -i region_diag_history_outside.fcstm
   ...
     regions: 2
   ...

原因 ``mixed_children`` 与 ``owner_statements`` 无法用文本写出：解析器在构建模型之前就拒绝了文本，用户看到的是语法错误。只有用公开的节点类构造语法树才能触发它们。

.. literalinclude:: region_diag_mixed_children.fcstm.txt
   :language: fcstm
   :caption: region_diag_mixed_children.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_owner_transition.fcstm.txt
   :language: fcstm
   :caption: region_diag_owner_transition.fcstm.txt (negative example, do not copy)

.. code-block:: console

   $ pyfcstm inspect -i region_diag_mixed_children.fcstm.txt
   Failed to parse input DSL file region_diag_mixed_children.fcstm.txt: Found 3 errors during parsing:
   Error 1: Syntax error at line 3, column 4, near 'region': Unexpected token 'region'
   ...
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_owner_transition.fcstm.txt
   Failed to parse input DSL file region_diag_owner_transition.fcstm.txt: Found 1 errors during parsing:
   Error 1: Syntax error at line 3, column 4, near '[*]': Unexpected token '[*]'
   $ echo $?
   1

``E_DUPLICATE_REGION`` 按拥有者计算。第一个模型在 ``Root`` 下两次声明 ``A``\ ，被拒绝；第二个模型在 ``Root.P`` 和 ``Root.Q`` 下各声明一个 ``A``\ ，被接受，含三个区域。

.. code-block:: console

   $ pyfcstm inspect -i region_diag_duplicate.fcstm.txt
   Invalid state machine model in region_diag_duplicate.fcstm.txt: Duplicate region 'A' in Root. (line 3)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_same_name_two_owners.fcstm
   ...
     regions: 3
   ...

``E_ACTIVE_QUERY_TARGET`` 为每一种被拒绝的查询写法给出一个原因。\ ``region_diag_active_ok.fcstm`` 展示被接受的相对根写法 ``active("/B")``\ 。

.. literalinclude:: region_diag_active_invalid_path.fcstm.txt
   :language: fcstm
   :caption: region_diag_active_invalid_path.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_active_region.fcstm.txt
   :language: fcstm
   :caption: region_diag_active_region.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_active_pseudo.fcstm.txt
   :language: fcstm
   :caption: region_diag_active_pseudo.fcstm.txt (negative example, do not copy)

.. literalinclude:: region_diag_active_ok.fcstm
   :language: fcstm
   :caption: region_diag_active_ok.fcstm

.. code-block:: console

   $ pyfcstm inspect -i region_diag_active_not_found.fcstm.txt
   Invalid state machine model in region_diag_active_not_found.fcstm.txt: Invalid active query 'Root.Unknown' (not_found). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_invalid_path.fcstm.txt
   Invalid state machine model in region_diag_active_invalid_path.fcstm.txt: Invalid active query 'Other.A' (invalid_path). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_region.fcstm.txt
   Invalid state machine model in region_diag_active_region.fcstm.txt: Invalid active query 'Root.P.R' (region). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_pseudo.fcstm.txt
   Invalid state machine model in region_diag_active_pseudo.fcstm.txt: Invalid active query 'Root.G' (pseudo). (line 2)
   $ echo $?
   1
   $ pyfcstm inspect -i region_diag_active_ok.fcstm
   [WARN] FCSTM Inspect Report: region_diag_active_ok.fcstm
   ...

原因 ``initializer`` 同样无法从文本触发：持久变量初始值里调用 ``active(...)`` 是语法错误。

.. code-block:: console

   $ pyfcstm inspect -i region_diag_active_initializer.fcstm.txt
   Failed to parse input DSL file region_diag_active_initializer.fcstm.txt: Found 3 errors during parsing:
   Error 1: Syntax error at line 1, column 16, near 'active': Unexpected token 'active'
   ...
   $ echo $?
   1

结构化诊断带有出错构造的 span 和该诊断码的 ``refs`` 载荷。要求模型构建“收集”而不是抛出异常时，就能拿到它们。重复区域的 ``refs`` 里还有 ``previous_span``\ ，即第一次声明的位置。

.. testcode::

   from pathlib import Path

   from pyfcstm.dsl import parse_with_grammar_entry
   from pyfcstm.model import parse_dsl_node_to_state_machine

   names = (
       "region_diag_empty_region.fcstm.txt",
       "region_diag_duplicate.fcstm.txt",
       "region_diag_active_not_found.fcstm.txt",
   )
   for name in names:
       ast = parse_with_grammar_entry(Path(name).read_text(), "state_machine_dsl")
       model, diagnostics = parse_dsl_node_to_state_machine(ast, collect=True)
       for item in diagnostics:
           print(item.code, item.span)
           print(sorted(item.refs.items()))

.. testoutput::

   E_REGION_STRUCTURE Span(line=2, column=5, end_line=2, end_column=20)
   [('namespace_path', 'Root.Empty'), ('reason', 'empty_region'), ('source_path', None)]
   E_DUPLICATE_REGION Span(line=3, column=5, end_line=3, end_column=42)
   [('owner_path', 'Root'), ('previous_span', Span(line=2, column=5, end_line=2, end_column=42)), ('region_name', 'A'), ('source_path', None)]
   E_ACTIVE_QUERY_TARGET Span(line=2, column=28, end_line=2, end_column=50)
   [('reason', 'not_found'), ('source_path', None), ('state_path', 'Root.Unknown')]

自定义模板没有声明 ``features: [region]`` 而模型含区域时，会报 ``E_UNSUPPORTED_FEATURE``\ 。拒绝发生在写出任何输出之前，后面两条命令通过检查输出目录不存在来说明这一点。同一个模型可以用内置 ``python`` 模板生成。

.. literalinclude:: region_two_regions.fcstm
   :language: fcstm
   :caption: region_two_regions.fcstm

.. code-block:: console

   $ cat region_plain_template/config.yaml
   expr_styles: {}
   stmt_styles: {}
   globals: {}
   filters: {}
   tests: {}
   ignores: []
   $ pyfcstm generate -i region_two_regions.fcstm -t region_plain_template -o out_plain
   generate with template directory '...region_plain_template' does not support region models yet. (line 2)
   The model declares 2 regions, the first is 'Root.Left'.
   If you write this template: its config.yaml does not list `region` under `features`. ...
   If you write the model: use a template that supports regions. Built-in templates that support regions: c, c_poll, cpp, cpp_poll, python.
     pyfcstm generate -i region_two_regions.fcstm --template c -o out_plain
   Or take the regions out of the model.
   $ echo $?
   1
   $ test -e out_plain || echo "output directory was not created"
   output directory was not created
   $ pyfcstm generate -i region_two_regions.fcstm --template python -o out_python
   $ test -f out_python/machine.py && echo "machine.py generated"
   machine.py generated

拒绝信息按这个顺序读：第一行点名模板目录；第二行说明模型声明了几个区域、第一个在哪里；\ ``If you write this template`` 一段说明模板作者该声明什么；\ ``If you write the model`` 一段列出声明了 ``region`` 的内置模板，并给出一条可以复制的命令。

.. include:: _code_catalog_zh.rst.inc
