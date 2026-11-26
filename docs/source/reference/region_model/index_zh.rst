Region 模型与配置
=================

本页介绍 Python 模型构建和位置值。Python 包里的每个消费者都接受含区域的模型：
仿真器（冷启动与热启动）和 ``pyfcstm simulate``，``pyfcstm inspect`` 与
``pyfcstm.verify`` 的结构分析，有界模型检查与 ``pyfcstm bmc``，PlantUML 导出，
``StateMachine.diagram()`` 与 ``pyfcstm diagram``，以及用内置的 ``python``、
``c``、``c_poll``、``cpp``、``cpp_poll`` 模板生成代码。仅剩的一处拒绝是：
模板的 ``config.yaml`` 没有在 ``features`` 里列出 ``region`` 时，
``pyfcstm generate`` 会在写出任何文件之前以 ``E_UNSUPPORTED_FEATURE`` 停止
（见 :doc:`../template_config/index_zh`）。活动查询从不被拒绝：模型把 ``active()``
降级成普通的隐藏变量。JavaScript 前端（模型、语义分析和图形预览）支持区域与
活动查询；它的 ``inspectModel`` 函数对含区域的模型不生成报告。

命名空间与结构
--------------

``State.regions`` 是按声明顺序排列的 ``Region`` 字典。一个状态的直接子级
要么是状态，要么是区域，不能混用。区域可以包含普通状态、局部转换和事件、
以及持续动作切面；不能直接包含导入或另一个区域，不能拥有状态生命周期动作，
也不能作为转换端点。需要嵌套并行结构时，在区域的子状态内声明区域。
每个区域必须包含状态，并至少有一条合法的初始转换。

区域所属状态可以有自己的生命周期动作和持续动作切面；转换必须放在
区域内。导入必须放在普通子状态内，不能直接写在区域或其所属状态内。
只有一个区域合法，本身不会产生警告。
区域内的普通状态子树仍可使用历史；如果声明历史的状态的子树含区域，
则拒绝构建，因为单一历史叶子不能表示这种配置。

路径包含区域名称，例如 ``Root.Job.Worker.Idle``。``State.parent`` 返回直接
上级命名空间，可能是 ``State`` 或 ``Region``；``Region.parent`` 返回所属状态。
``walk_states()`` 只遍历状态，但包含区域内的状态；``walk_regions()`` 按声明
顺序遍历区域。``StateMachine.has_regions`` 表示模型内是否存在区域。

事件和命名动作引用路径可以穿过两类命名空间。相对路径向上计数时包含区域这一层；
绝对路径保持从根开始的含义。解析不会向祖先搜索碰巧同名的对象。导入会把模块内部的
状态、事件、动作引用和活动查询路径重新定位到导入实例。模型节点保留原始文件及
源位置；区域结构和活动查询目标诊断包含 ``source_path``。部分既有通用构建诊断，
例如缺少初始转换，目前仍只提供源位置，不包含原始文件路径。

位置值
------

``Configuration`` 描述位置，不执行初始化、守卫条件或动作。使用
``Configuration.parse(model, text, mode=...)`` 或
``Configuration.from_dict(model, data)`` 构造。值不可变且可哈希；相等比较取决于
模式和有序路径，不取决于模型对象身份。``leaves`` 返回的状态属于构造时的模型。

.. list-table:: 校验模式
   :header-rows: 1
   :widths: 20 80

   * - 模式
     - 接受的位置
   * - ``stable`` （默认）
     - 每条活动分支到达非伪状态叶子；每个活动的区域所属状态指定全部区域，且至少一个
       区域仍在工作。每一层都检查这个条件。
   * - ``initialization``
     - 一个完整的复合状态或区域所属状态等待初始化。区域项可省略或显式写为
       ``[init]``，不接受活动子状态或已完成项。这不是部分指定的稳定配置。
   * - ``transient``
     - 结构合法的中间位置，包括伪状态、部分区域初始化和全体已完成快照。
       状态机不会停在这样的位置上，所以 ``runtime.configuration`` 在静止时不会
       返回它。热启动按这个模式读取配置文本：省略的区域等待初始化，任一层
       拥有者的区域全体已完成则被拒绝。

文本最外层使用包含根名称的完整状态路径；区域项内的子状态相对于该区域
书写，``[done]`` 表示该区域已完成，``[init]`` 表示尚未初始化。
嵌套并行状态再引入一个区域块。
输入顺序会规范化为模型声明顺序。未知、重复或越界的项目会被拒绝；线性路径不能越过
并行状态，只选择其中一个区域。
``stable`` 在每一层都拒绝 ``[init]``。在 ``initialization`` 和 ``transient``
模式下，省略的区域表示等待初始化，``str()`` 会将其显式输出为 ``[init]``。
配置文本拒绝旧标记 ``[*]``；DSL 的初始和终止转换仍使用 ``[*]``。

.. code-block:: pycon

   >>> from pyfcstm.model import Configuration, load_state_machine_from_text
   >>> source = '''state Root {
   ...     region Left { state Idle; [*] -> Idle; Idle -> [*]; }
   ...     region Right { state Working; [*] -> Working; }
   ... }'''
   >>> model = load_state_machine_from_text(source)
   >>> config = Configuration.parse(model, 'Root{Right: Working, Left: [done]}')
   >>> str(config)
   'Root{Left: [done], Right: Working}'
   >>> [state.path for state in config.leaves]
   [('Root', 'Right', 'Working')]
   >>> config.is_active('Root'), config.is_active('Root.Left.Idle')
   (True, False)
   >>> config.region_status('Root.Left'), config.region_status('Root.Right')
   ('done', 'live')
   >>> Configuration.from_dict(model, config.to_dict()) == config
   True

``str(config)`` 是规范化的位置文本。``repr(config)`` 还显示校验模式，便于调试；
它不是可执行的构造表达式，也不是解析器接受的输入。重新解析非稳定配置时，需要显式传入模式：

.. code-block:: pycon

   >>> pending = Configuration.parse(model, 'Root', mode='initialization')
   >>> str(pending)
   'Root{Left: [init], Right: [init]}'
   >>> repr(pending)
   "Configuration(mode='initialization', position='Root{Left: [init], Right: [init]}')"
   >>> Configuration.parse(model, str(pending), mode=pending.mode) == pending
   True
   >>> mixed = Configuration.parse(model, 'Root{Left: [done]}', mode='transient')
   >>> str(mixed)
   'Root{Left: [done], Right: [init]}'
   >>> mixed.region_status('Root.Left'), mixed.region_status('Root.Right')
   ('done', 'pending')
   >>> Configuration.parse(model, str(mixed), mode=mixed.mode) == mixed
   True

词法单元之间允许空白，包括换行。标识符遵循 ``[A-Za-z_][A-Za-z_0-9]*``；
标记必须精确拼写，因此 ``[Done]`` 和 ``[ init ]`` 都不合法。
语法错误抛出 ``ValueError``，包含从 1 开始的行号和字符列号；制表符算一个字符，
换行字符分隔行。模型校验另行报告无效路径、区域项或校验模式。

.. code-block:: pycon

   >>> Configuration.parse(model, 'Root{\n Left: @\n}', mode='transient')
   Traceback (most recent call last):
       ...
   ValueError: Expected a configuration identifier at line 2, column 8, got '@'.

非字符串输入抛出 ``TypeError``。嵌套过深时抛出说明原因的 ``ValueError``，
不会直接泄漏 Python 的 ``RecursionError``；可支持的深度取决于解释器可用的调用栈。
错误消息缩短过长的记号或路径片段、转义不可打印字符，并用 ``end of input``
明确表示输入已结束。调用方可以捕获 ``ValueError``，直接展示输入问题：

.. code-block:: pycon

   >>> try:
   ...     Configuration.parse(model, 'Root{Left: Working', mode='transient')
   ... except ValueError as error:
   ...     # ValueError: the input is missing its closing region-block brace.
   ...     print(error)
   Expected '}' at line 1, column 19, got end of input.

``is_active`` 接受状态路径，包括活动祖先，但拒绝区域路径。
``region_status`` 接受区域路径，返回 ``live``、``done``、``pending``
（所属状态活动但区域尚未初始化）或 ``inactive``\ （所属状态不在配置中）。
``leaves`` 不包含已完成或等待初始化的分支。未知路径抛出 ``ValueError``。

``to_dict()`` 返回新分配的 JSON 兼容容器。上述例子的结果是：

.. code-block:: json

   {
     "mode": "stable",
     "state": "Root",
     "regions": [
       {"name": "Left", "configuration": null},
       {"name": "Right", "configuration": {
         "state": "Root.Right.Working", "regions": []
       }}
     ]
   }

嵌套节点使用完整状态路径，省略 ``mode``。``null`` 表示已完成；JSON 继续省略
等待初始化的区域项，整个所属状态等待初始化时区域列表为空。``[init]`` 和 ``[done]``
是文本标记，不是 JSON 字符串值。省略外层 ``mode`` 时默认 ``stable``。
文本不编码模式，因此重新解析非稳定值时必须再次传入模式。

.. code-block:: pycon

   >>> pending.to_dict()
   {'mode': 'initialization', 'state': 'Root', 'regions': []}
   >>> mixed.to_dict()
   {'mode': 'transient', 'state': 'Root', 'regions': [{'name': 'Left', 'configuration': None}]}
   >>> Configuration.from_dict(model, mixed.to_dict()) == mixed
   True

活动查询
--------

在根为 ``Root`` 的模型中，``active("Root.Job.Worker.Idle")`` 与
``active("/Job.Worker.Idle")`` 指向同一个状态。目标必须存在，必须是非伪状态，
不能是区域。守卫条件和操作条件可以使用查询，包括生命周期及切面的
条件；持久变量初始化器不能查询活动位置。无效目标产生 ``E_ACTIVE_QUERY_TARGET``。
``parse_expr`` 可以在没有模型时保留 ``ActiveStateQuery``，但求值未绑定的表达式
会抛出 ``TypeError``。

导入模块中，以该模块根名称或 ``/`` 开始的查询会重定位到导入实例。显式指定宿主根
名称的路径则在展开后的完整模型中绑定；这种模块依赖宿主提供该路径。

模型构建会绑定查询，并为每个不同目标生成一个整数活动标志。
``StateMachine.active_queries`` 提供带 ``state_path`` 和 ``variable_name`` 的
``ActiveQuery`` 记录。生成名称会避开持久变量及块内临时变量；消费者应读取记录，
不应猜测名称。
独立的匿名 ``enter``/``exit`` 动作维护标志，不修改命名动作本体。
``model.active_variables(config)`` 为绑定到同一个模型对象的配置计算标志值，
不会执行任何动作。

.. code-block:: pycon

   >>> model = load_state_machine_from_text('state Root { during { if [active("Root")] {} } }')
   >>> config = Configuration.parse(model, 'Root')
   >>> query, = model.active_queries
   >>> query.state_path, model.active_variables(config)[query.variable_name]
   (('Root',), 1)

``to_ast_node()`` 导出当前模型，包括语法糖展开结果，不能当作无损源文本往返接口。
Configuration JSON 是独立的位置值契约，不会给公共 inspect 或 BMC 报告添加字段。

.. _region-limits-and-gaps-zh:

界限与已知差距
------------------------------

下表列出与含区域的模型有关的全部界限和已知差距。数字只在真实运行产生过的地方出现：本页旁边的 ``region_limits.demo.py`` 复现这些界限和核对过的差距，它的输出在表之后。
最后一列写着“已记录”的行，描述的是取自对应 issue、没有为本页重新运行的差距。

.. list-table:: 含区域模型的界限与已知差距
   :header-rows: 1
   :widths: 24 30 26 20

   * - 界限或差距
     - 取值或表现
     - 出处
     - 记载位置
   * - 一个周期内相互嵌套进入的拥有者
     - 至多 64 层。第 65 层抛出 ``SimulationRuntimeDfsError``\ （``Group initialization nested deeper than the structural safety limit (64) within one cycle``）；64 层嵌套的拥有者可以运行。
       一个周期里把同一个整组重复进入约 64 次以上的循环也适用同一上限。模型本身在任何深度都能构建。
     - ``pyfcstm/simulate/runtime.py`` 的 ``_DFS_STRUCTURAL_DEPTH_LIMIT``；生成的 Python 运行时和 C 内核带有相同常量；
       共享用例 ``region_unbounded_group_reentry_is_reported_as_a_safety_limit_error``。
     - :ref:`region-limits-run-zh`、:doc:`../simulation/index_zh`
   * - 一个周期内的步数
     - 至多 1000 个推测步。一个伪状态在一个周期里转 500 圈会抛出 ``Speculative DFS exceeded the step safety limit (1000)``。
       校验一条长链的代价增长得比链长更快（\ `issue #579 <https://github.com/HansBug/pyfcstm/issues/579>`_\ ，不含区域的模型同样如此）；这里没有测量转圈数。
     - ``pyfcstm/simulate/runtime.py`` 的 ``_DFS_STEP_LIMIT``；共享用例 ``pseudo_self_loop_step_limit_raises_dfs_error``。
     - :ref:`region-limits-run-zh`
   * - BMC：同一拥有者在自己的进入里重入的次数
     - ``BmcOptions.max_group_reentries``，默认 ``16``。需要更多时抛出 ``BmcBuildError``，而不是近似。没有命令行选项：``pyfcstm bmc`` 总是用默认值。
     - ``pyfcstm/bmc/engine.py``、``pyfcstm/bmc/region_relation.py``；``test/bmc/test_region_relation.py``。
     - :ref:`region-limits-run-zh`、:doc:`/reference/bmc_query/index_zh`
   * - BMC：单个表达式的嵌套深度
     - 100 层。表达式嵌套更深的查询被 ``expression_too_deep`` 拒绝；一个比较前面加 98 个前缀取反可以接受，99 个被拒绝。
     - ``pyfcstm/bmc/binding.py``；``test/bmc/test_query_binding.py``。
     - :ref:`region-limits-run-zh`
   * - 子树里含区域的历史拥有者
     - 被 ``E_REGION_STRUCTURE``\ （\ ``history_boundary``\ ）拒绝。区域内部、覆盖不含区域的状态的历史是合法的。
     - ``pyfcstm/model/region.py`` 的 ``validate_region_structure``；``test/model/test_region_consumers.py``。
     - :ref:`dsl-history-regions-zh`
   * - jsfcstm 的 ``inspectModel``
     - 对含区域或 ``active()`` 查询的模型不出报告：``isInspectable(machine)`` 为 ``false``，``inspectModel`` 抛出
       ``inspectModel does not support machines with regions or active() queries``。编辑器对这样的模型跳过 inspect 诊断；模型、语义诊断和图形预览支持区域。
     - ``editors/jsfcstm/src/diagnostics/inspect.ts``；``editors/jsfcstm/test/region-diagnostics.test.ts``。
     - 本表
   * - jsfcstm 的顺序诊断
     - jsfcstm 里没有 ``I_REGION_BACKWARD_READ`` 与 ``W_REGION_BLIND_OVERWRITE``；只有 Python 的 ``pyfcstm inspect`` 会报告它们。
     - ``editors/jsfcstm/src`` 里不存在；定义在 ``pyfcstm/diagnostics/codes.yaml``。
     - :doc:`/reference/diagnostics_codes/index_zh`
   * - inspect 的过近似：历史默认目标
     - 只经历史默认目标进入的复合状态，它的普通初始子状态仍被算作可达，所以 ``inspect`` 不会报告这个子状态（下面输出里的 ``unreachable: 0``）。
       这条规则的偏差方向是漏报，不会误报。
     - ``pyfcstm/diagnostics/inspect.py``；发布说明。
     - :ref:`region-limits-run-zh`
   * - inspect 的过近似：按实际运行的机器判断的验证
     - ``pyfcstm.verify`` 判断的是降级之后的机器。对强制声明它仍是不看条件的过近似，所以只有强制声明才能离开的复合状态后面的状态，仍可能被列为可达。
     - 发布说明（“Inspect and verify”一节）。
     - 已记录
   * - inspect 的过近似：每条强制声明一个标记
     - 只要一条强制声明的某个展开从不可达状态出发，整条声明就被标记。
     - 发布说明（“Inspect and verify”一节）。
     - 已记录
   * - 触达区域的强制声明
     - 同一拥有者的两条声明竞争整组：先抬起变量的占住它，第二条不会被尝试；不含区域的模型则改试下一条声明。区域里叶子的其他转换在变量抬起时照常工作
       （\ `issue #591 <https://github.com/HansBug/pyfcstm/issues/591>`_\ ）。
     - 共享用例 ``region_forced_declaration_whose_target_cannot_be_entered_holds_the_group_against_a_later_declaration``。
     - :ref:`dsl-region-forced-zh`
   * - 复合状态里只会绕回的候选
     - 在不含区域的模型里，经伪状态绕回自己起点的候选使整个周期成为 Delta，而不是让后面的候选触发（下面的输出；
       `issue #578 <https://github.com/HansBug/pyfcstm/issues/578>`_\ ）。同一个 issue 还记录了第二个缺陷，即 Delta 周期里 handler 已被调用；那一个没有重新运行。
     - ``limits_composite_loop.fcstm`` 与演示输出。
     - :ref:`region-limits-run-zh`
   * - 触达区域的强制声明的导出文本
     - ``to_ast_node()`` 文本加载得到的机器，在 `issue #580 <https://github.com/HansBug/pyfcstm/issues/580>`_ 的复现上行为相同（退出顺序与结果一致，见下面的输出）；该 issue 记录的是更早的行为。
     - ``region_limits.demo.py``。
     - :ref:`region-limits-run-zh`
   * - 行为类 inspect 诊断与语法糖
     - 哪些诊断码属于书写的模型、哪些属于实际运行的机器，仍在归类；实际运行的机器上的发现可能提到隐藏变量或生成的状态
       （\ `issue #588 <https://github.com/HansBug/pyfcstm/issues/588>`_\ ）。
     - issue 正文与发布说明。
     - 已记录
   * - jsfcstm 对历史的预览
     - 编辑器预览画的是降级之后的历史；Python 的图形快照和 PlantUML 按书写画
       （\ `issue #590 <https://github.com/HansBug/pyfcstm/issues/590>`_\ ）。
     - issue 正文。
     - 已记录
   * - 生成的 C 系运行时：容量
     - ``..._ARENA_CAPACITY`` 对没有区域、伪状态和复合状态的模型默认是 ``8``，否则是 ``max(24, 12 * scopes)``；``..._TRAIL_CAPACITY`` 是 ``4`` 或 ``16 + 4 * scopes``，
       其中 scopes 是状态数加区域数。这些值是经验公式，不是证明过的上界；一个周期需要更多时失败，报 ``Speculative search exceeded the capacity safety limit`` 并点名对应的宏。
       要在所有编译单元里调大该宏（\ `issue #598 <https://github.com/HansBug/pyfcstm/issues/598>`_\ ）。
     - ``pyfcstm/render/c_kernel.py`` 的 ``_plan_capacity``；``test/render/test_c_kernel.py``。
     - :ref:`region-limits-run-zh`、:doc:`/reference/builtin_templates/index_zh`
   * - 生成的 Python 运行时
     - 每个生成的 ``machine.py`` 都带着通用的搜索内核（位置解析、记忆化、整组初始化），不管模型有没有区域，并且做与仿真器相同的推测工作；进一步的专用化记录在
       `issue #596 <https://github.com/HansBug/pyfcstm/issues/596>`_\ 。64 与 1000 这两个界限同样适用。
     - ``templates/python/machine.py.j2``。
     - :doc:`/reference/builtin_templates/index_zh`
   * - 没有在 ``features`` 里列出 ``region`` 的模板
     - ``pyfcstm generate`` 在写出任何文件之前以 ``E_UNSUPPORTED_FEATURE`` 拒绝含区域的模型。
     - ``pyfcstm/entry/generate.py``。
     - :doc:`/reference/cli/index_zh`

.. _region-limits-run-zh:

复现这些界限
~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: limits_composite_loop.fcstm
   :language: fcstm

.. literalinclude:: limits_history_default.fcstm
   :language: fcstm

.. literalinclude:: region_limits.demo.py.txt
   :language: text

按顺序读各块。深度一块显示 64 层与 65 层嵌套拥有者之间的边界；步数一块显示 500 圈的链被拒绝；BMC 几块显示默认的 16 次重入上限（``n < 3`` 能构建，``n < 20`` 不能）、
该选项可以调低或调高，以及表达式深度的 98/99 边界；历史一块显示拒绝。复合状态一块显示整个周期变成 Delta（两个 ``Root.Go`` 周期的 ``delta=True``），尽管 ``S -> T`` 本可以触发；
导出一块显示两台机器一致；inspect 一块对一个 ``Root.P.A`` 进不去的模型显示 ``unreachable: 0``，因为 ``P`` 只经历史默认目标 ``B`` 进入且没有出路，所以没有任何东西会记录 ``A``。
容量一块打印 C 模板对教程控制器和一台平铺机器使用的默认值。这些数字都不是性能数据。

相关参考：:doc:`../dsl/index_zh`、:doc:`../diagnostics_codes/index_zh`、
:doc:`/api_doc_zh`。
