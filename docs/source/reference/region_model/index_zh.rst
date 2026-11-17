Region 模型与配置
=================

本页介绍 Python 模型构建和位置值。目前执行、代码生成、图形以及 inspect/verify
分析遇到含区域或活动查询的模型，会以 ``E_UNSUPPORTED_FEATURE`` 拒绝操作。
能够解析和构建模型，不代表这些消费者已经可以执行它。
JavaScript 模型前端目前仍在构建阶段拒绝这些功能。

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
       接受快照不代表它是合法的运行时驻停位置或热启动输入。

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

``is_active`` 接受状态路径，包括活动祖先，但拒绝区域路径。
``region_status`` 接受区域路径，返回 ``live``、``done``、``pending``
（所属状态活动但区域尚未初始化）或 ``inactive``（所属状态不在配置中）。
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

相关参考：:doc:`../dsl/index_zh`、:doc:`../diagnostics_codes/index_zh`、
:doc:`/api_doc_zh`。
