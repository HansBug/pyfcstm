Region 模型与配置
=================

本页介绍 Python 模型构建和位置值。目前执行、代码生成、图形以及 inspect/verify
分析遇到含 region 或活动查询的模型，会以 ``E_UNSUPPORTED_FEATURE`` 拒绝操作。
能够解析和构建模型，不代表这些消费者已经可以执行它。
JavaScript 模型前端目前仍在构建阶段拒绝这些功能。

命名空间与结构
--------------

``State.regions`` 是按声明顺序排列的 ``Region`` 字典。一个 state 的直接子级
要么是 state，要么是 region，不能混用。region 可以包含普通 state、局部转换和事件、
导入以及 during aspect；不能直接包含另一个 region，不能拥有 state 生命周期动作，
也不能作为转换端点。需要嵌套并行结构时，在 region 的子 state 内声明 region。
每个 region 必须包含 state，并至少有一条合法的初始转换。

包含 region 的 owner 可以有自己的生命周期动作和 during aspect；转换和导入必须
放在 region 内，不能直接写在 owner 内。只有一个 region 合法，本身不会产生警告。
region 内的普通 state 子树仍可使用 history；如果 history owner 的子树含 region，
则拒绝构建，因为单一历史叶子不能表示这种配置。

路径包含 region 名称，例如 ``Root.Job.Worker.Idle``。``State.parent`` 返回直接
上级命名空间，可能是 ``State`` 或 ``Region``；``Region.parent`` 返回 owner state。
``walk_states()`` 只遍历 state，但包含 region 内的 state；``walk_regions()`` 按声明
顺序遍历 region。``StateMachine.has_regions`` 表示模型内是否存在 region。

事件和命名动作引用路径可以穿过两类命名空间。相对路径向上计数时包含 region 这一层；
绝对路径保持从根开始的含义。解析不会向祖先搜索碰巧同名的对象。导入会把状态、事件、
动作引用和活动查询路径重新定位到导入实例；源诊断保留原始文件路径。

位置值
------

``Configuration`` 描述位置，不执行初始化、guard 或动作。使用
``Configuration.parse(model, text, mode=...)`` 或
``Configuration.from_dict(model, data)`` 构造。值不可变且可哈希；相等比较取决于
模式和有序路径，不取决于模型对象身份。``leaves`` 返回的 State 属于构造时的模型。

.. list-table:: 校验模式
   :header-rows: 1
   :widths: 20 80

   * - 模式
     - 接受的位置
   * - ``stable``（默认）
     - 每条活动分支到达非 pseudo 叶子；每个活动 owner 指定全部 region，且至少一个
       region 仍在工作。每一层都检查这个条件。
   * - ``initialization``
     - 一个完整的 composite 或 region owner 路径，不带 region 块。表示整组等待
       初始化，不是部分指定的稳定配置。
   * - ``transient``
     - 结构合法的中间位置，包括 pseudo、部分 region 初始化和全体 Done 快照。
       接受快照不代表它是合法的运行时驻停位置或热启动输入。

文本最外层使用包含根名称的完整 state 路径；region 项内的子状态相对于该 region
书写，``[*]`` 表示该 region 已 Done。嵌套并行 owner 再引入一个 region 块。
输入顺序会规范化为模型声明顺序。未知、重复或越界的项目会被拒绝；线性路径不能越过
并行 owner，只选择其中一个 region。

.. code-block:: pycon

   >>> from pyfcstm.model import Configuration, load_state_machine_from_text
   >>> source = '''state Root {
   ...     region Left { state Idle; [*] -> Idle; Idle -> [*]; }
   ...     region Right { state Working; [*] -> Working; }
   ... }'''
   >>> model = load_state_machine_from_text(source)
   >>> config = Configuration.parse(model, 'Root{Right: Working, Left: [*]}')
   >>> str(config)
   'Root{Left: [*], Right: Working}'
   >>> [state.path for state in config.leaves]
   [('Root', 'Right', 'Working')]
   >>> config.is_active('Root'), config.is_active('Root.Left.Idle')
   (True, False)
   >>> config.region_status('Root.Left'), config.region_status('Root.Right')
   ('done', 'live')
   >>> Configuration.from_dict(model, config.to_dict()) == config
   True

``is_active`` 接受 State 路径，包括活动祖先，但拒绝 Region 路径。
``region_status`` 接受 Region 路径，返回 ``live``、``done``、``pending``
（owner 活动但 region 尚未初始化）或 ``inactive``（owner 不在配置中）。
``leaves`` 不包含 Done 或等待初始化的分支。未知路径抛出 ``ValueError``。

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

嵌套节点使用完整 state 路径，省略 ``mode``。``null`` 表示 Done；在对应模式下，
composite 的空 region 列表表示等待初始化。省略外层 ``mode`` 时默认 ``stable``。
文本不编码模式，因此重新解析非稳定值时必须再次传入模式。

活动查询
--------

在根为 ``Root`` 的模型中，``active("Root.Job.Worker.Idle")`` 与
``active("/Job.Worker.Idle")`` 指向同一个 state。目标必须存在，必须是非 pseudo
State，不能是 Region。guard 和操作条件可以使用查询，包括生命周期及 aspect 的
条件；持久变量初始化器不能查询活动位置。无效目标产生 ``E_ACTIVE_QUERY_TARGET``。
``parse_expr`` 可以在没有模型时保留 ``ActiveStateQuery``，但求值未绑定的表达式
会抛出 ``TypeError``。

模型构建会绑定查询，并为每个不同目标生成一个整数活动标志。
``StateMachine.active_queries`` 提供带 ``state_path`` 和 ``variable_name`` 的
``ActiveQuery`` 记录。生成名称会避开用户变量；消费者应读取记录，不应猜测名称。
独立的匿名 enter/exit 动作维护标志，不修改命名动作本体。
``model.active_variables(config)`` 为绑定到同一个模型对象的配置计算标志值，
不会执行任何动作。

.. code-block:: pycon

   >>> model = load_state_machine_from_text('state Root { during { if [active("Root")] {} } }')
   >>> config = Configuration.parse(model, 'Root')
   >>> query, = model.active_queries
   >>> query.state_path, model.active_variables(config)[query.variable_name]
   (('Root',), 1)

``to_ast_node()`` 导出当前模型，包括 lowering 结果，不能当作无损源文本往返接口。
Configuration JSON 是独立的位置值契约，不会给公共 inspect 或 BMC 报告添加字段。

相关参考：:doc:`../dsl/index_zh`、:doc:`../diagnostics_codes/index_zh`、
:doc:`/api_doc_zh`。
