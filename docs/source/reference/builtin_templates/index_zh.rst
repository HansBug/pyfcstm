.. _sec-reference-builtin-templates-zh:

内置模板参考
============

这些名称用于 ``pyfcstm generate --template <name>``。不要把仓库 ``templates/`` 路径当成普通内置模板入口；那是维护者源码。

当前所有内置模板（built-in template）都在打包元数据中标记为 ``experimental: true``。

在本参考里，**实验状态** 表示生成输出具有当前仓库测试和冒烟证据，但它不是生产认证或所有平台保证。下方元数据表的 ``description`` 列保留 ``template.json`` 原文，因为它是被文档漂移检查同步的源数据，不是中文叙述段落。

.. template-ref-meta: name=python title=Python language=python archive=python.zip root_dir=python experimental=true description="Native Python built-in template with embedded runtime logic."
.. template-ref-meta: name=c title=C99 language=c archive=c.zip root_dir=c experimental=true description="Native C99 built-in template with embedded runtime logic and abstract hook callbacks."
.. template-ref-meta: name=c_poll title="C Poll" language=c archive=c_poll.zip root_dir=c_poll experimental=true description="Native C99 / C++98 built-in template with hook-polled events and embedded runtime logic."
.. template-ref-meta: name=cpp title="C++ Wrapper" language=cpp archive=cpp.zip root_dir=cpp experimental=true description="Early-stage first-class C++ template that reuses the C99 runtime core and emits C++ wrapper files."
.. template-ref-meta: name=cpp_poll title="C++ Poll Wrapper" language=cpp archive=cpp_poll.zip root_dir=cpp_poll experimental=true description="Early-stage first-class C++ poll template that reuses the C poll runtime core and emits C++ wrapper files."

.. template-ref-contract: name=python generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=c generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=c_poll generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=cpp generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=cpp_poll generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status

.. template-ref-profile: name=python event_input=cycle_events wrapper=false core=python native_evidence=false semantic_alignment=true formatter=ruff poll=false
.. template-ref-profile: name=c event_input=explicit_event_ids wrapper=false core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=false
.. template-ref-profile: name=c_poll event_input=event_checks wrapper=false core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=true
.. template-ref-profile: name=cpp event_input=explicit_event_ids wrapper=true core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=false
.. template-ref-profile: name=cpp_poll event_input=event_checks wrapper=true core=c_poll native_evidence=true semantic_alignment=true formatter=clang-format poll=true

上面的隐藏 ``template-ref-profile`` 标记包含 ``core`` 值，它只供文档漂移检查使用。这个值是从生成文件和模板测试推导出的文档内部字段，不是 ``template.json`` 或 ``index.json`` 的公开元数据键。

元数据矩阵
----------

下表结合 ``pyfcstm/template/index.json`` 与 ``templates/<name>/template.json``。``archive`` 和 ``root_dir`` 来自打包索引；其余可见元数据由源码 ``template.json`` 镜像。

.. list-table:: 内置模板元数据
   :header-rows: 1

   * - 名称
     - 标题
     - 语言
     - 归档 / 根目录
     - 实验状态
     - 描述
   * - ``python``
     - Python
     - ``python``
     - ``python.zip`` / ``python``
     - ``true``
     - ``Native Python built-in template with embedded runtime logic.``
   * - ``c``
     - C99
     - ``c``
     - ``c.zip`` / ``c``
     - ``true``
     - ``Native C99 built-in template with embedded runtime logic and abstract hook callbacks.``
   * - ``c_poll``
     - C Poll
     - ``c``
     - ``c_poll.zip`` / ``c_poll``
     - ``true``
     - ``Native C99 / C++98 built-in template with hook-polled events and embedded runtime logic.``
   * - ``cpp``
     - C++ Wrapper
     - ``cpp``
     - ``cpp.zip`` / ``cpp``
     - ``true``
     - ``Early-stage first-class C++ template that reuses the C99 runtime core and emits C++ wrapper files.``
   * - ``cpp_poll``
     - C++ Poll Wrapper
     - ``cpp``
     - ``cpp_poll.zip`` / ``cpp_poll``
     - ``true``
     - ``Early-stage first-class C++ poll template that reuses the C poll runtime core and emits C++ wrapper files.``

发现公开接口（API）
------------------------

``pyfcstm.template`` 中的公开包接口很小：

.. list-table:: 内置模板接口
   :header-rows: 1

   * - 函数
     - 用途
     - 边界
   * - ``list_templates()``
     - 按打包索引顺序返回已安装内置模板名。
     - 只用于发现；不渲染也不验证模型。
   * - ``has_template(name)``
     - 检查某个名称是否存在。
     - 如果包元数据缺失或无效，会抛出索引加载错误。
   * - ``get_template_info(name)``
     - 返回某个元数据条目的浅拷贝。
     - 未知名称抛出 ``LookupError``。
   * - ``extract_template(name, output_dir)``
     - 把打包归档解包成普通目录，供渲染器消费。
     - 开发检出中若归档不存在，可能复制仓库源码目录。

生成 README 契约
----------------

每个内置模板都会生成 ``README.md`` 和 ``README_zh.md``。这些文件由模型生成，应视为该生成机器的具体集成契约。它们提供本通用参考无法完全预知的名称和编号：类名、C 前缀、钩子名、事件编号、状态编号、热启动例子和目标构建片段。

.. _sec-reference-builtin-templates-regions-zh:

含区域的模型
------------

五套内置模板的 ``config.yaml`` 都声明了 ``features: [region]``\ （见 :ref:`sec-reference-template-config-features-zh`），所以 ``pyfcstm generate --template <name>`` 能渲染声明了 ``region`` 块的模型，嵌套的区域（region）也不例外。自定义模板目录遇到这样的模型会被拒绝，除非它自己声明了这个特性。拒绝的文字见 :doc:`/reference/template_config/index_zh`。生成的运行时遵循模拟器对区域的规则：区域的拥有者（owner）按书写顺序推进各个区域，靠后的区域能读到靠前区域在同一周期写入的值，机器的位置是一棵树而不是一条路径，由配置（configuration）值表示。这些规则见 :doc:`/explanations/region_semantics/index_zh`。

下面的事实取自 ``pyfcstm generate --template X`` 为 ``controller.fcstm``\ （``Running`` 里有两个区域）和 ``region_plain.fcstm``\ （没有区域）写出的文件，以及各自生成的 ``README.md``。仓库的模板测试把 118 个共享区域用例（``test/fixtures/simulate_semantics/cases`` 下的 ``region_*.yaml``）对每个内置模板运行一遍：Python 模板与 ``SimulationRuntime`` 对比，四套 C 家族模板则编译后运行并与它对比。本页没有重跑这些测试套件。

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: controller.fcstm

.. literalinclude:: region_plain.fcstm
   :language: fcstm
   :caption: region_plain.fcstm

位置与查询
~~~~~~~~~~

.. list-table:: 按模板和模型种类读取位置
   :header-rows: 1

   * - 模板
     - 含区域的模型
     - 不含区域的模型
   * - ``python``
     - ``configuration``\ （位置文本）、``leaves``\ （路径元组的元组）、``is_active(path)``、``region_status(path)``。没有 ``current_state_path``，也没有 ``current_state_name``：读取其中任何一个都是 ``AttributeError``。
     - 同样四个成员，另有 ``current_state_path``\ （元组，终止后为 ``None``）和 ``current_state_name``。``region_status`` 不存在。
   * - ``c``、``c_poll``
     - ``<Prefix>_get_configuration`` 填充一个 ``<Prefix>Configuration`` 值（``at`` 加每个区域一个槽位）；该值有查询、校验、格式化与解析函数。``machine.h`` 里没有声明 ``<Prefix>_current_state_id``、``_path`` 和 ``_name``，调用它们无法通过编译。
     - 配置函数同样存在；``<Prefix>_current_state_id``、``_path`` 和 ``_name`` 也存在。
   * - ``cpp``、``cpp_poll``
     - ``MachineWrapper::get_configuration`` 加静态的 ``region_status``、``is_active``、``leaves``、``validate_configuration``、``format_configuration`` 和 ``parse_configuration``。没有声明 ``current_state_id()`` 和 ``current_state_path()``。
     - 同样的成员，另有 ``current_state_id()`` 和 ``current_state_path()``。

位置文本与 ``SimulationRuntime`` 打印的一致。``Controller.Idle`` 是不含区域的位置；``Controller.Running{Safety: Watching, Motion: On}`` 写出每个区域最深的状态；``[done]`` 代替已完成区域的状态，``[init]`` 代替等待初始转换的区域（等待初始化）。Python 的 ``region_status(path)`` 返回四个字符串之一，C 里对应的四个值是 ``<PREFIX>_REGION_STATUS_*`` 宏：

.. list-table:: 区域状态值
   :header-rows: 1

   * - Python 字符串
     - C 宏（取值）
     - 含义
   * - ``'live'``
     - ``..._REGION_STATUS_LIVE``\ （2）
     - 拥有者活动，区域里有一个活动状态。
   * - ``'done'``
     - ``..._REGION_STATUS_DONE``\ （3）
     - 区域已完成，直到拥有者再次进入之前一直保持已完成。
   * - ``'pending'``
     - ``..._REGION_STATUS_PENDING``\ （1）
     - 拥有者活动，区域还没有执行初始转换（文本 ``[init]``）。
   * - ``'inactive'``
     - ``..._REGION_STATUS_INACTIVE``\ （0）
     - 拥有者不在位置里。

``region_status`` 对状态路径抛出 ``ValueError``\ （``region_status requires a Region path.``），对不存在的路径也抛出 ``ValueError``\ （``Unknown configuration path: 'Controller.Nowhere'.``）。

Python 运行时
~~~~~~~~~~~~~

.. list-table:: Python 生成运行时的公开接口
   :header-rows: 1

   * - 成员
     - 约定
   * - ``Machine(initial_state=None, initial_vars=None, *, parameters=None)``
     - 冷启动构造；给出 ``initial_state`` 时是完整的热启动恢复。
   * - ``initial_state``
     - 位置文本、点路径或名字元组。含区域的模型：写出的叶子直接就位，不执行 enter 动作；没写出的部分等待初始化（``[init]``），在第一个周期执行它们的初始转换。写成 ``[done]`` 的区域保持已完成；拥有者的区域全部是 ``[done]`` 时抛出 ``ValueError``。
   * - ``initial_vars``
     - 热启动时给出全部变量，``__forced_0`` 这样的隐藏变量也不例外。冷启动接受只含控制变量和输出变量的部分映射。
   * - ``cycle(events=None, *, inputs=None)``
     - 返回 ``None``。通过 ``configuration``、``vars``、``is_ended``、``last_cycle_was_delta`` 观察结果。
   * - ``vars``
     - 已提交变量的只读映射视图；没有 ``variables`` 别名。
   * - ``ABSTRACT_HOOKS``、``get_abstract_hook_map()``
     - DSL 抽象动作到覆写方法名的只读映射；``get_abstract_hook_map()`` 返回副本。
   * - 钩子上下文 ``ctx``
     - ``vars``、``inputs``、``parameters``、``state_path``、``active_leaf``、``action_name``、``abstract_target``、``action_stage``、``call_stage``、``named_ref`` 和 ``configuration``。对包住多个区域的动作，``state_path`` 与 ``active_leaf`` 是所有分支共有的最深状态，例如拥有者。
   * - 事件名
     - 绝对路径、以 ``/`` 开头的路径、以 ``.`` 开头的相对路径，或短名。含区域的模型里，短名对每个活动叶子各解析一次；一个都找不到抛出 ``SimulationRuntimeEventError``，找到的相同则使用，找到的不同则报歧义并列出全部候选。处于 ``[init]`` 的区域没有活动叶子，不参与解析。

下面的命令为三个模型生成 Python 运行时，其后的脚本驱动生成出的 ``machine.py``\ 。

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o controller_py
   $ pyfcstm generate -i region_probe.fcstm --template python -o probe_py
   $ pyfcstm generate -i region_plain.fcstm --template python -o plain_py

第一个脚本冷启动控制器，读取 ``/Start`` 事件前后的位置文本、四种区域状态，以及 ``/Stop`` 之后的隐藏变量：

.. testcode::

   import sys

   sys.path.insert(0, "controller_py")
   from machine import ControllerMachine

   machine = ControllerMachine()
   sensors = {"fault": 0, "requested": 1}
   machine.cycle(inputs=sensors)
   print("first cycle:", machine.configuration)
   machine.cycle("/Start", inputs=sensors)
   print("after /Start:", machine.configuration)
   machine.cycle(inputs=sensors)
   print("next cycle:", machine.configuration)
   print("motor:", machine.vars["motor"])
   print("leaves:", machine.leaves)
   print("is_active(Controller.Running):", machine.is_active("Controller.Running"))
   print("is_active(Controller.Idle):", machine.is_active("Controller.Idle"))
   for path in ("Controller.Running.Safety", "Controller.Running.Motion"):
       print("region_status(%s): %s" % (path, machine.region_status(path)))
   machine.cycle("/Stop", inputs=sensors)
   print("after /Stop:", machine.configuration)
   print("region_status(Controller.Running.Safety):", machine.region_status("Controller.Running.Safety"))
   print("hidden variable __forced_0:", machine.vars["__forced_0"])

.. testoutput::

   first cycle: Controller.Idle
   after /Start: Controller.Running{Safety: Watching, Motion: Off}
   next cycle: Controller.Running{Safety: Watching, Motion: On}
   motor: 1
   leaves: (('Controller', 'Running', 'Safety', 'Watching'), ('Controller', 'Running', 'Motion', 'On'))
   is_active(Controller.Running): True
   is_active(Controller.Idle): False
   region_status(Controller.Running.Safety): live
   region_status(Controller.Running.Motion): live
   after /Stop: Controller.Idle
   region_status(Controller.Running.Safety): inactive
   hidden variable __forced_0: 0

第二个脚本展示区域模型上不存在的 ``current_state_path`` 和被拒绝的路径：

.. testcode::

   import sys

   sys.path.insert(0, "controller_py")
   from machine import ControllerMachine

   machine = ControllerMachine()
   try:
       machine.current_state_path
   except AttributeError as err:
       print("AttributeError:", err)
   for path in ("Controller.Idle", "Controller.Nowhere"):
       try:
           machine.region_status(path)
       except ValueError as err:
           print("ValueError:", err)

.. testoutput::

   AttributeError: 'ControllerMachine' object has no attribute 'current_state_path'
   ValueError: region_status requires a Region path.
   ValueError: Unknown configuration path: 'Controller.Nowhere'.

第三个脚本给出 ``initial_state`` 的六种写法及其位置，以及所有区域都是 ``[done]`` 时的拒绝：

.. testcode::

   import sys

   sys.path.insert(0, "controller_py")
   from machine import ControllerMachine

   base_vars = {"permit": 0, "motor": 0, "__forced_0": 0}
   spellings = [
       ("configuration text", "Controller.Running{Safety: Watching, Motion: On}"),
       ("text, region left out", "Controller.Running{Motion: On}"),
       ("text, region [init]", "Controller.Running{Safety: Watching, Motion: [init]}"),
       ("dotted path through a region", "Controller.Running.Motion.On"),
       ("owner path only", "Controller.Running"),
       ("tuple", ("Controller", "Running", "Motion", "On")),
   ]
   for label, state in spellings:
       m = ControllerMachine(initial_state=state, initial_vars=dict(base_vars))
       print("%s: %s | Safety=%s Motion=%s" % (
           label, m.configuration,
           m.region_status("Controller.Running.Safety"),
           m.region_status("Controller.Running.Motion")))
   try:
       ControllerMachine(
           initial_state="Controller.Running{Safety: [done], Motion: [done]}",
           initial_vars=dict(base_vars))
   except ValueError as err:
       print("ValueError:", err)

.. testoutput::

   configuration text: Controller.Running{Safety: Watching, Motion: On} | Safety=live Motion=live
   text, region left out: Controller.Running{Safety: [init], Motion: On} | Safety=pending Motion=live
   text, region [init]: Controller.Running{Safety: Watching, Motion: [init]} | Safety=live Motion=pending
   dotted path through a region: Controller.Running{Safety: [init], Motion: On} | Safety=pending Motion=live
   owner path only: Controller.Running{Safety: [init], Motion: [init]} | Safety=pending Motion=pending
   tuple: Controller.Running{Safety: [init], Motion: On} | Safety=pending Motion=live
   ValueError: All regions are Done at 'Controller.Running'; a finished owner cannot be hot-started.

第四个脚本是一个包住两个区域的动作的钩子上下文，模型如下：

.. literalinclude:: region_probe.fcstm
   :language: fcstm
   :caption: region_probe.fcstm

.. testcode::

   import sys

   sys.path.insert(0, "probe_py")
   from machine import LineMachine


   class Probe(LineMachine):
       def read_fault(self):
           return 0

       def _log(self, name, ctx):
           print("%s: state_path=%s active_leaf=%s configuration=%s" % (
               name, ".".join(ctx.state_path), ".".join(ctx.active_leaf), ctx.configuration))

       def _abstract_hook_Line_Boot(self, ctx):
           self._log("Boot", ctx)

       def _abstract_hook_Line_Work_Left_L_Tick(self, ctx):
           self._log("Tick", ctx)

       def _abstract_hook_Line_Work_Settle(self, ctx):
           self._log("Settle", ctx)


   probe = Probe()
   probe.cycle()
   print("cycle 1 configuration:", probe.configuration)
   probe.cycle()

.. testoutput::

   Boot: state_path=Line active_leaf=Line configuration=Line
   Tick: state_path=Line.Work.Left.L active_leaf=Line.Work.Left.L configuration=Line.Work{Left: L, Right: [init]}
   Settle: state_path=Line.Work active_leaf=Line.Work configuration=Line.Work{Left: L, Right: R}
   cycle 1 configuration: Line.Work{Left: L, Right: R}
   Tick: state_path=Line.Work.Left.L active_leaf=Line.Work.Left.L configuration=Line.Work{Left: L, Right: R}
   Settle: state_path=Line.Work active_leaf=Line.Work configuration=Line.Work{Left: L, Right: R}

最后一个脚本展示不含区域的模型上的同样成员：

.. testcode::

   import sys

   sys.path.insert(0, "plain_py")
   from machine import PlainMachine

   plain = PlainMachine()
   plain.cycle()
   print("current_state_path:", plain.current_state_path)
   print("current_state_name:", plain.current_state_name)
   print("configuration:", plain.configuration)
   print("leaves:", plain.leaves)
   print("has region_status:", hasattr(plain, "region_status"))

.. testoutput::

   current_state_path: ('Plain', 'Idle')
   current_state_name: Idle
   configuration: Plain.Idle
   leaves: (('Plain', 'Idle'),)
   has region_status: False

读输出时注意：

* 第一个周期只是进入 ``Controller.Idle``；第二个周期收到的 ``/Start`` 事件让机器进入 ``Controller.Running{Safety: Watching, Motion: Off}``，第三个周期才打开电机，所以位置文本里每个区域各占一项；
* ``/Stop`` 之后拥有者被离开，两个区域都报告 ``inactive``，隐藏变量 ``__forced_0`` 回到 ``0``；
* ``initial_state`` 的六种写法只产生四种不同的位置：被省略的区域、通过点路径穿过另一个区域的写法，以及只写拥有者的路径，都会让没写出的区域处于 ``[init]``；显式写成 ``[init]`` 的区域同样是 ``pending``；
* 热启动不是一个周期：位置被设定，不执行任何 enter 动作，之后的第一个周期才初始化等待中的区域；
* 在探针模型里，``Tick`` 位于 ``Left`` 内部，报告那个叶子；``Settle`` 包住两个区域，报告拥有者 ``Line.Work``。第一个周期里 ``Tick`` 看到 ``Right`` 是 ``[init]``，因为 ``Left`` 先进入，而 ``ctx.configuration`` 是调用那一刻的位置。

这次运行没有展示已完成的区域。``region_status`` 对它返回 ``'done'`` 由共享区域用例覆盖，不由本页覆盖。

C 家族运行时
~~~~~~~~~~~~

四套 C 家族模板共用一套内核发射器：``c`` 和 ``cpp`` 以编号传入事件，``c_poll`` 和 ``cpp_poll`` 查询事件检查表，C++ 模板包装 C 核心。对含区域的模型：

.. list-table:: C 家族生成运行时的公开接口（``<Prefix>`` 是生成的前缀，例如 ``ControllerMachine``）
   :header-rows: 1

   * - 成员
     - 约定
   * - ``<Prefix>Configuration``
     - 普通值：``at`` 是所有区域之外最深的活动状态，``regions[r]`` 是区域 ``r`` 最深的活动状态、``<PREFIX>_REGION_SLOT_PENDING``\ （0）或 ``<PREFIX>_REGION_SLOT_DONE``\ （-1）。合法值只有一种表示，所以可以用 ``memcmp`` 比较两个值；C++ 包装层另外提供 ``operator==`` 和 ``operator!=``。
   * - ``<Prefix>_get_configuration(machine, &cfg)``
     - 写出当前位置；机器结束之后返回 0。
   * - ``<Prefix>_hot_start_at(machine, &cfg, &vars)``、``..._hot_start_at_with_parameters(...)``
     - 恢复位置和完整的变量快照，不执行 enter 动作。按状态编号的 ``hot_start`` 仍然存在，用于所有区域之外的状态。
   * - ``configuration_region_status``、``configuration_is_active``、``configuration_leaves``
     - 接受配置值、不需要机器的查询。``configuration_leaves(cfg, NULL, 0u)`` 用来数叶子。
   * - ``configuration_validate(cfg, &err)``
     - 值合法返回 1，否则返回 0 并填写 ``<Prefix>ConfigurationError``：``kind``\ （``<PREFIX>_CONFIGURATION_ERROR_*``，1 到 11）、字节 ``position`` 和 ``message``。
   * - ``configuration_format(cfg, buf, size)``、``configuration_parse(text, &cfg, &err)``
     - 文本形式，与模拟器逐字节相同。``format`` 按 ``size`` 截断并返回完整长度。``parse`` 失败时不改动 ``cfg``；文本里省略的区域是等待初始化。为 ``machine.c`` 和每个使用者定义 ``PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT`` 时，两者都被省略。
   * - ``<PREFIX>_REGION_COUNT``、``<PREFIX>_REGION_<path>``
     - 区域个数，以及每个区域一个区域编号，按拥有者顺序、同一拥有者内按书写顺序。
   * - ``<Prefix>ExecutionContext``
     - ``state_id`` 与 ``active_leaf_state_id`` 取同一个值：区域内的动作是它自己的状态，切面或拥有者的动作是它包住的全部内容共有的最深状态。含区域的模型没有唯一的叶子，所以用 ``get_configuration`` 读位置。
   * - ``<PREFIX>_ARENA_CAPACITY``、``<PREFIX>_TRAIL_CAPACITY``、``<PREFIX>_STORAGE_BYTES``
     - 机器的静态容量；见下面的容量表。

``c`` / ``cpp`` 与 ``c_poll`` / ``cpp_poll`` 有两处不同：

* ``c``：``<Prefix>_cycle(machine, event_ids, count)`` 与 ``<Prefix>_cycle_with_inputs(machine, event_ids, count, &inputs)``；``cpp``：``cycle()``、``cycle(event_id)``、``cycle(ids, count)`` 与 ``cycle_with_inputs(inputs, ids, count)``；
* ``c_poll``：``<Prefix>_set_event_checks(machine, &checks, user_data)`` 配一张 ``<Prefix>EventChecks`` 表（每个事件一个 ``check_<event>`` 函数，对本模型用 ``CONTROLLERMACHINE_EVENT_CHECKS_INIT`` 初始化，即大写的类型名，不带分隔符），再用 ``<Prefix>_cycle(machine)`` 与 ``<Prefix>_cycle_with_inputs(machine, &inputs)``；``cpp_poll``：``set_event_checks`` 与 ``cycle_with_inputs(inputs)``。检查函数拿到的 ``<Prefix>EventContext`` 有 ``event_id`` 和 ``vars``；不含区域的模型还有 ``current_state_id``，含区域的模型没有它。

.. list-table:: C 家族生成运行时的容量宏
   :header-rows: 1

   * - 宏
     - ``controller.fcstm``
     - ``region_plain.fcstm``
     - 含义
   * - ``<PREFIX>_ARENA_CAPACITY``
     - 108
     - 8
     - 一个周期的一次判定最多能检查多少个配置和待办项。默认值取决于模型：``controller.fcstm`` 是 ``max(24, 12 * scopes)``，降级后有 7 个状态和 2 个区域，共 9。
   * - ``<PREFIX>_TRAIL_CAPACITY``
     - 52
     - 4
     - 最多能嵌套多少层检查。默认值取决于模型。
   * - ``<PREFIX>_STORAGE_BYTES``
     - 14272（``c`` 与 ``cpp`` 是 ``944 + 108 * 108 + 52 * 32``；``c_poll`` 与 ``cpp_poll`` 的常数项是 976）
     - ``c`` 与 ``cpp`` 是 ``848 + 8 * 68 + 4 * 32``；``c_poll`` 与 ``cpp_poll`` 的常数项是 880
     - 由前两个宏推出；机器类型就是这么多字节的静态、不透明存储。

这些宏取代了运行时不再定义的 ``MAX_STACK_DEPTH`` 与 ``MAX_DFS_STEPS``。机器的大小取决于它们，所以改动后的值要对 ``machine.c`` 和每个包含 ``machine.h`` 的文件一致地定义，例如 ``-DCONTROLLER_MACHINE_ARENA_CAPACITY=480``。某个周期需要更多空间时会失败，``last_error()`` 以 ``Speculative search exceeded the capacity safety limit`` 开头并点出要调大的宏。由模型决定的深度和步数上限（``Speculative DFS exceeded the structural stack-depth safety limit``、``Group initialization nested deeper than the structural safety limit``、``Speculative DFS exceeded the step safety limit``）是固定的。永远停不下来的闭环报告 ``Cannot reach a stoppable state in the same cycle; suspected loop.``

.. literalinclude:: region_c_runtime.c
   :language: c
   :caption: region_c_runtime.c（``c`` 模板的驱动程序）

.. literalinclude:: region_c_hooks.c
   :language: c
   :caption: region_c_hooks.c（含两个区域的模型里的钩子上下文）

.. literalinclude:: region_cpp_runtime.cpp
   :language: cpp
   :caption: region_cpp_runtime.cpp（``cpp`` 模板的驱动程序）

.. literalinclude:: region_c_poll_runtime.c
   :language: c
   :caption: region_c_poll_runtime.c（``c_poll`` 模板的驱动程序）

.. literalinclude:: region_cpp_poll_runtime.cpp
   :language: cpp
   :caption: region_cpp_poll_runtime.cpp（``cpp_poll`` 模板的驱动程序）

头文件里的事实不需要编译器。下面的命令为两个模型生成 ``c`` 运行时，并从 ``machine.h`` 读出容量宏、区域个数和 ``current_state_`` 函数：

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template c -o out_c
   $ pyfcstm generate -i region_plain.fcstm --template c -o out_plain_c
   $ grep -E "^#define .*_(ARENA_CAPACITY|TRAIL_CAPACITY|STORAGE_BYTES|REGION_COUNT) " out_c/machine.h out_plain_c/machine.h
   out_c/machine.h:#define CONTROLLER_MACHINE_ARENA_CAPACITY 108
   out_c/machine.h:#define CONTROLLER_MACHINE_TRAIL_CAPACITY 52
   out_c/machine.h:#define CONTROLLER_MACHINE_STORAGE_BYTES (944 + (CONTROLLER_MACHINE_ARENA_CAPACITY) * 108 + (CONTROLLER_MACHINE_TRAIL_CAPACITY) * 32)
   out_c/machine.h:#define CONTROLLER_MACHINE_REGION_COUNT 2
   out_plain_c/machine.h:#define PLAIN_MACHINE_ARENA_CAPACITY 8
   out_plain_c/machine.h:#define PLAIN_MACHINE_TRAIL_CAPACITY 4
   out_plain_c/machine.h:#define PLAIN_MACHINE_STORAGE_BYTES (848 + (PLAIN_MACHINE_ARENA_CAPACITY) * 68 + (PLAIN_MACHINE_TRAIL_CAPACITY) * 32)
   out_plain_c/machine.h:#define PLAIN_MACHINE_REGION_COUNT 0
   $ grep -l current_state_ out_c/machine.h out_plain_c/machine.h
   out_plain_c/machine.h

编译并运行驱动程序需要 C 和 C++ 编译器，所以下面的命令不在文档检查里运行。它们生成每个模板、编译上面为它列出的驱动程序并运行；命令之后的输出是这个版本的一次真实运行记录，而 C 家族运行时与仿真器是否一致，由模板测试检查。

.. code-block:: bash

   # c: generate, compile as C99 and run the driver
   pyfcstm generate -i controller.fcstm --template c -o out_c
   cc -std=c99 -Wall -Wextra -pedantic -O1 -I out_c out_c/machine.c region_c_runtime.c -lm -o c_driver
   ./c_driver

   # c: the hook context driver, on the model of region_probe.fcstm
   pyfcstm generate -i region_probe.fcstm --template c -o out_hooks
   cc -std=c99 -Wall -Wextra -pedantic -O1 -I out_hooks out_hooks/machine.c region_c_hooks.c -lm -o hooks_driver
   ./hooks_driver

   # cpp: the C++98 wrapper over the same C core
   pyfcstm generate -i controller.fcstm --template cpp -o out_cpp
   cc -std=c99 -O1 -c out_cpp/machine.c -o out_cpp/machine_c.o
   c++ -std=c++98 -Wall -Wextra -pedantic -O1 -I out_cpp out_cpp/machine.cpp region_cpp_runtime.cpp out_cpp/machine_c.o -lm -o cpp_driver
   ./cpp_driver

   # c_poll: event checks are queried during the cycle
   pyfcstm generate -i controller.fcstm --template c_poll -o out_c_poll
   cc -std=c99 -Wall -Wextra -pedantic -O1 -I out_c_poll out_c_poll/machine.c region_c_poll_runtime.c -lm -o c_poll_driver
   ./c_poll_driver

   # cpp_poll: the C++98 wrapper over the polling core
   pyfcstm generate -i controller.fcstm --template cpp_poll -o out_cpp_poll
   cc -std=c99 -O1 -c out_cpp_poll/machine.c -o out_cpp_poll/machine_c.o
   c++ -std=c++98 -Wall -Wextra -pedantic -O1 -I out_cpp_poll out_cpp_poll/machine.cpp region_cpp_poll_runtime.cpp out_cpp_poll/machine_c.o -lm -o cpp_poll_driver
   ./cpp_poll_driver

下面是同一顺序的输出记录（以 ``==`` 开头的行标明各次运行）：

.. code-block:: text

   == c: model with regions (controller.fcstm)
   cycle 1: Controller.Idle | at=1 regions=[0, 0] | motor=0
   cycle 2 (/Start): Controller.Running{Safety: Watching, Motion: Off} | at=2 regions=[3, 4] | motor=0
   cycle 3: Controller.Running{Safety: Watching, Motion: On} | at=2 regions=[3, 5] | motor=1
   REGION_COUNT = 2
   Safety status = 2 (LIVE is 2)
   Running active = 1, Idle active = 0
   leaf count = 2
   leaf ids = 3, 5
   parsed: Controller.Running{Safety: [init], Motion: On}
   refused: kind=5 position=0 message=Path passes through the regions of 'Controller.Running' at byte 0.
   refused: kind=6 position=19 message=Unknown region 'Speed' at byte 19.
   refused: kind=7 position=31 message=Duplicate region 'Motion' at byte 31.
   after hot start: Controller.Running{Safety: Watching, Motion: On} | at=2 regions=[3, 5] | motor=1
   cycle after hot start: Controller.Running{Safety: Watching, Motion: On} | at=2 regions=[3, 5] | motor=1
   ARENA_CAPACITY = 108, TRAIL_CAPACITY = 52, STORAGE_BYTES = 14272
   sizeof(machine) >= STORAGE_BYTES: 1
   == c: hook context (region_probe.fcstm)
   Boot: state_id=0 active_leaf_state_id=0 configuration=Line
   Tick: state_id=2 active_leaf_state_id=2 configuration=Line.Work{Left: L, Right: [init]}
   state ids: Line=0 Work=1 Left.L=2 Right.R=3
   == cpp: wrapper over the same core
   after three cycles: Controller.Running{Safety: Watching, Motion: On} | motor=1
   Safety status = 2
   valid = 1
   saved == parsed: 0
   saved != parsed: 1
   refused: kind=3 message=Unknown name 'Idle' at byte 27.
   after hot start: Controller.Running{Safety: Watching, Motion: On} | motor=1
   == c_poll: event checks are queried during the cycle
   cycle 1: Controller.Idle | start checks so far=0 stop checks so far=0
   cycle 2: Controller.Idle | start checks so far=1 stop checks so far=0
   cycle 3: Controller.Running{Safety: Watching, Motion: Off} | start checks so far=2 stop checks so far=0
   == cpp_poll: wrapper over the polling core
   cycle 1: Controller.Idle | start checks so far=0
   cycle 2: Controller.Idle | start checks so far=1
   cycle 3: Controller.Running{Safety: Watching, Motion: Off} | start checks so far=2

读输出时注意：

* ``at=2 regions=[3, 5]`` 是文本 ``Controller.Running{Safety: Watching, Motion: On}`` 背后的配置值：``2`` 是 ``Running``，``3`` 和 ``5`` 是 ``Safety`` 与 ``Motion`` 的活动叶子，区域槽位为 ``0`` 表示等待初始化；``cycle 1`` 里拥有者不活动，所以两个槽位都是 ``0``；
* ``parse`` 接受省略了某个区域的文本并给它 ``[init]``，拒绝穿过区域的点路径（kind 5，路径穿过了拥有者的区域）、未知区域（kind 6）和重复的区域（kind 7）；每个错误都带有出错位置的字节偏移；
* ``hot_start_at`` 让机器回到保存的位置，下一个周期从那里继续；热启动之后显示的位置没有执行任何 enter 动作；
* 钩子驱动程序对 ``Line`` 的 enter 动作报告拥有者层的状态（``state_id=0``），对区域内的动作报告叶子 ``Left.L``，两种情况下 ``active_leaf_state_id`` 都等于 ``state_id``；
* ``c_poll`` 与 ``cpp_poll`` 在机器停在 ``Idle`` 时每个周期调用一次 ``Start`` 检查，并且从不在那里调用 ``Stop`` 检查（运行只展示了计数，没有展示原因，所以本页不为此写规则）；``cpp`` 驱动程序用 ``-std=c++98`` 编译，C 核心用 ``-std=c99``；
* 不含区域的模型在 ``machine.h`` 里保留 ``current_state_name`` 与 ``current_state_path``；含区域的模型一个也没有声明。

这次运行没有检查 ``PYFCSTM_GENERATED_NO_HEAP``、消毒器（sanitizer）构建或 ``native-toolchain`` 矩阵；它们属于模板测试套件。

旧集成的名称变化
~~~~~~~~~~~~~~~~

.. list-table:: 已不存在的接口
   :header-rows: 1

   * - 旧的集成代码
     - 当前生成的运行时
   * - Python ``machine.variables``
     - 已删除；用 ``machine.vars``\ （只读视图）。
   * - Python ``machine.vars['x'] = 1``
     - 不受支持；``vars`` 是只读视图。要写入就在 DSL 里表达。
   * - 把 Python ``ABSTRACT_HOOKS`` 当字典来改
     - 是只读映射；``get_abstract_hook_map()`` 返回副本。
   * - 含区域的模型上的 Python ``current_state_path``
     - ``AttributeError``；读 ``configuration`` 或 ``leaves``。
   * - C ``MAX_STACK_DEPTH``、``MAX_DFS_STEPS``
     - 已删除；用 ``ARENA_CAPACITY`` 与 ``TRAIL_CAPACITY`` 宏。
   * - 含区域的模型上的 C ``<Prefix>_current_state_id``
     - 没有声明，调用无法通过编译；用 ``get_configuration``。
   * - 把 C 机器当作透明结构体
     - 机器是 ``<PREFIX>_STORAGE_BYTES`` 字节的不透明存储；用 ``machine.h`` 里的函数。

模板契约
--------

``python``
~~~~~~~~~~

* 生成文件：``machine.py``、``README.md`` 和 ``README_zh.md``。
* 入口：从 ``machine.py`` 导入生成机器类。教程模型的类名是 ``SimpleMachineMachine``。
* 事件模型：``cycle(events=None, *, inputs=None)`` 接受无事件、一个事件字符串，或事件字符串的列表、元组、集合；``inputs`` 为该周期提供数值输入。
* 扩展点：继承生成类，覆写生成 README 中列出的受保护抽象钩子方法。
* 生命周期概念：构造、初始 ``cycle()``、后续 ``cycle(...)``、通过构造参数（``initial_state``、``initial_vars``、``parameters``）热启动、读取位置和变量。含区域的模型通过 ``configuration`` 读取位置；见 :ref:`sec-reference-builtin-templates-regions-zh`。
* 目标边界：Python 3.7+ 标准库运行时；生成代码不应导入 ``pyfcstm``。
* 证据边界：Python 模板测试和语义对齐测试覆盖受支持生成行为；教程冒烟检查只是第一次成功信号。

``c``
~~~~~

* 生成文件：``machine.h``、``machine.c``、``README.md`` 和 ``README_zh.md``。
* 入口：包含 ``machine.h``，调用 ``..._init(...)``、``..._cycle(machine, event_ids, event_count)``、``..._vars(...)`` 和启用堆辅助时的 ``..._destroy(...)`` 等生成 C 函数。
* 事件模型：应用在每个周期把生成的整数事件编号传入运行时。
* 扩展点：安装抽象钩子表，回调签名由生成头文件和 README 描述。
* 生命周期概念：调用者持有或堆分配机器对象、初始化、热启动、周期、变量读取、状态读取和销毁。
* 目标边界：C99 核心、C++98 兼容头文件用法、默认只依赖标准库、整数变量使用固定宽度生成整数配置。
* 证据边界：本机冒烟和模板对齐检查是工具链证据，不是所有编译器或部署配置认证。

``c_poll``
~~~~~~~~~~

* 生成文件：``machine.h``、``machine.c``、``README.md`` 和 ``README_zh.md``。
* 入口：包含 ``machine.h``，初始化机器，安装钩子和完整 ``EventChecks`` 表，然后调用轮询周期接口。
* 事件模型：运行时在周期中调用已安装事件检查函数；不接收逐周期外部事件编号数组。
* 扩展点：抽象钩子使用 ``Hooks``；事件真值来自 ``EventChecks`` 回调。
* 生命周期概念：初始化、事件检查安装、热启动、周期、变量读取、状态读取和销毁。
* 目标边界：与 ``c`` 相同的 C 家族配置，并在公开接口中增加事件轮询。
* 证据边界：本机和对齐证据必须包含事件检查行为；回调结果应在单个周期中表现为只读探针。

``cpp``
~~~~~~~

* 生成文件：``machine.h``、``machine.c``、``machine.hpp``、``machine.cpp``、``README.md`` 和 ``README_zh.md``。
* 入口：包含 ``machine.hpp``，使用 ``pyfcstm_generated::<Machine>_cpp::MachineWrapper``。模板包含 C 核心，但 C++ 用户代码不应绕过包装层作为主集成面。
* 事件模型：包装层周期方法把生成事件编号提交给复用的 C 核心。
* 扩展点：包装层通过 C++ 别名暴露 C 钩子注册；运行时行为仍在生成 C 核心中。
* 生命周期概念：包装层构造、钩子注册、周期重载、变量/状态读取、按文档通过公开 C 核心热启动，以及包装层持有的初始化。
* 目标边界：C99 执行核心加 C++98 兼容、无异常、无 RTTI、无 STL 容器要求的包装层。
* 证据边界：C++ 冒烟测试必须走 ``machine.hpp`` / ``machine.cpp`` 包装层入口，即使最终可执行文件会链接生成 C 核心。

``cpp_poll``
~~~~~~~~~~~~

* 生成文件：``machine.h``、``machine.c``、``machine.hpp``、``machine.cpp``、``README.md`` 和 ``README_zh.md``。
* 入口：包含 ``machine.hpp``，构造 ``pyfcstm_generated::<Machine>_cpp_poll::MachineWrapper``\ （注意命名空间是 ``_cpp_poll``），安装包装层钩子和事件检查，然后调用 ``cycle()``。
* 事件模型：复用的 C 轮询核心调用已安装事件检查函数；C++ 包装层提供别名和设置方法。
* 扩展点：抽象钩子和事件检查都通过包装层接口安装。
* 生命周期概念：包装层构造、钩子/事件检查安装、周期、变量/状态读取、按文档通过底层公开接口热启动，以及包装层持有的初始化。
* 目标边界：C 轮询核心加 C++98 兼容包装层；不是完全独立的 C++ 运行时。
* 证据边界：冒烟和对齐测试必须覆盖包装层和轮询事件模型，而不只是复用的 C 核心。

目标配置说明
------------

C 家族模板在默认配置中使用固定宽度生成整数存储。因此数值部署警告适用于 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 目标。不要把它表述成 Python 生成运行时也有同样的固定宽度整数承载风险。

C++ 模板按设计复用 C 核心。``cpp`` 复用 C99 核心；``cpp_poll`` 复用 C 轮询核心。它们的 C++ 价值是包装层集成面，不是另一套执行语义实现。

选择与误用矩阵
--------------

.. list-table:: 选择矩阵
   :header-rows: 1

   * - 模板
     - 适合的第一用途
     - 应避免的误用
     - 第一验证
   * - ``python``
     - 应用或测试代码可以导入 Python 模块并调用 ``cycle``。
     - 把 Python 冒烟成功当成 C 家族整数存储或编译器行为证据。
     - 导入 ``machine.py``，按生成 README 运行短事件序列。
   * - ``c``
     - C 主机收集事件，并在每个周期提交生成事件编号。
     - 期待显式事件接口查询轮询回调。
     - 用包含 ``machine.h`` 的驱动编译 ``machine.c`` 并提交编号。
   * - ``c_poll``
     - C 主机希望在周期中通过回调查询事件真值。
     - 留空某个 ``EventChecks`` 项，并假设所有集成形状都把缺失回调当作 false。
     - 编译并运行安装完整事件检查表的驱动。
   * - ``cpp``
     - C++ 主机希望使用包装层方法，同时接受生成 C 核心。
     - 把它称为完全独立的 C++ 运行时，或只测试 C 核心。
     - 编译包含 ``machine.hpp`` 并使用包装层的消费者。
   * - ``cpp_poll``
     - C++ 主机希望使用包装层事件检查回调。
     - 把显式事件编号和轮询包装层混用，并期待二者接口等价。
     - 编译安装事件检查并调用 ``cycle()`` 的包装层消费者。

逐模板证据卡
------------

.. list-table:: 证据卡
   :header-rows: 1

   * - 模板
     - 事实源
     - 运行时证据
     - 边界证据
   * - ``python``
     - 包元数据、Python 模板配置、生成 README 模板、Python 模板测试。
     - 导入/周期冒烟，以及受支持 Python 生成运行时的模拟器对齐测试。
     - 没有本机编译器证明；生成代码应是自包含的 Python 标准库代码。
   * - ``c``
     - C 模板配置、``pyfcstm/render/c_runtime.py`` 中的 C 运行时辅助、生成 C README、本机测试。
     - C 编译器冒烟和显式事件编号的语义对齐覆盖。
     - 固定宽度整数配置和具体工具链证据必须可见。
   * - ``c_poll``
     - C 轮询模板配置、事件检查生成文件、C 运行时辅助事实。
     - 覆盖轮询回调的本机冒烟，以及轮询事件模型的对齐覆盖。
     - 轮询改变事件输入，不改变 FCSTM 生命周期语义。
   * - ``cpp``
     - C 核心模板事实，加包装层 ``machine.hpp`` / ``machine.cpp`` 模板。
     - C++ 包装层冒烟，而不仅是 C 核心编译成功。
     - 包装层集成面兼容 C++98，并复用生成 C 核心。
   * - ``cpp_poll``
     - C 轮询核心事实，加轮询包装层模板。
     - 通过包装层表面安装事件检查的包装层冒烟。
     - 不是独立 C++ 轮询运行时，而是 C 轮询核心加包装层。

通用例子形状
------------

具体名称来自模型。下面只是形状例子，实际符号必须读生成 README。

.. list-table:: 集成形状
   :header-rows: 1

   * - 模板
     - 形状例子
     - 生成 README 提供什么
   * - ``python``
     - ``from machine import <GeneratedMachine>; machine = <GeneratedMachine>(); machine.cycle()``
     - 类名、事件字符串、钩子方法名、状态和变量读取方式。
   * - ``c``
     - ``#include "machine.h"``，然后初始化机器对象，把事件编号数组传给生成周期函数。
     - C 前缀、类型名、事件编号、钩子表字段、初始化/周期/销毁名称。
   * - ``c_poll``
     - 初始化机器，安装钩子，安装 ``EventChecks``，调用轮询周期函数。
     - 事件检查表字段、回调签名、生命周期函数名。
   * - ``cpp``
     - ``#include "machine.hpp"``，然后构造生成包装层并调用包装层周期方法。
     - 命名空间、包装类名、钩子别名、周期重载。
   * - ``cpp_poll``
     - 构造包装层，安装包装层钩子和事件检查，然后调用 ``cycle()``。
     - 包装层事件检查别名、设置器名称和轮询生命周期片段。

不支持或高风险假设
------------------

.. list-table:: 反例
   :header-rows: 1

   * - 假设
     - 为什么错
     - 更安全表述
   * - “所有内置模板都已经生产认证。”
     - 元数据当前把五个模板都标成实验状态。
     - 它们有当前仓库测试和冒烟证据，不是全平台认证。
   * - “仓库 ``templates/`` 目录就是用户接口。”
     - 普通用户应通过 ``--template`` 使用打包资产。
     - 仓库模板源码是维护者输入和打包来源。
   * - “C++ 模板不需要 C 生成核心。”
     - ``cpp`` 和 ``cpp_poll`` 会复用生成 C 核心。
     - C++ 模板提供生成 C 核心之上的包装层集成面。
   * - “轮询模板改变状态机语义。”
     - 轮询改变事件真值的提供方式。
     - 生命周期和转换语义应在已记录排除项内与模拟器对齐。
   * - “生成文件树证明运行时正确。”
     - 渲染成功只证明文件创建。
     - 运行时、本机和语义声明需要对应冒烟或对齐证据。

使用本表审查集成方案时，应先问“这个声明需要哪一层证据”。例如，文件存在只需要生成命令；能否导入 Python 类需要消费者冒烟；能否编译 C 家族输出需要本机工具链；语义一致性则需要和模拟器对齐的测试语料。

这也是本页不把“内置模板存在”写成“目标平台已认证”的原因。模板契约描述当前仓库能证明什么；发布、嵌入式平台移植或安全关键部署仍需要项目自己的目标环境证据。

事实源审计地图
--------------

审阅者可以按下面的来源审计本页，而不需要猜测：

* 包列表和归档名：``pyfcstm/template/index.json``；
* 每个模板的标题、语言、描述和实验状态：``templates/<name>/template.json``；
* 生成文件和集成片段：每个模板生成的 ``README.md`` 和 ``README_zh.md``；
* 事件输入模型：生成 README、运行时模板和模板测试；
* C 家族辅助和固定宽度代码体事实：``pyfcstm/render/c_runtime.py``；
* 包装层事实：``templates/cpp``、``templates/cpp_poll`` 源模板和包装层冒烟测试；
* 区域支持：每个 ``templates/<name>/config.yaml`` 里的 ``features``、C 内核发射器 ``pyfcstm/render/c_kernel.py``、``pyfcstm/render/c_kernel_engine.py`` 与 ``pyfcstm/render/c_configuration.py``，以及 ``pyfcstm generate --template <name>`` 为 ``controller.fcstm`` 和 ``region_plain.fcstm`` 写出的文件；
* 当前证据边界：模板单元测试、语义对齐测试、格式化检查，以及主机工具链可用时的本机冒烟检查。
