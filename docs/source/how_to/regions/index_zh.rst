.. _sec-how-to-regions-zh:

区域建模任务
============

已经知道区域（region）是什么、需要完成一个具体的建模任务时使用本页：拆分状态、嵌套区域、共用事件、
安排顺序、联合完成、整组打断、读取其他区域、添加切面，或修复被拒绝的模型。第一个带引导的模型见
:doc:`/tutorials/regions/index_zh`；每条规则的来由见
:doc:`/explanations/region_semantics/index_zh`；确切的写法与位置值见
:doc:`/reference/region_model/index_zh`。

每张任务卡都给出同样的六项：\ **起点**\ 、\ **命令或代码**\ 、\ **预期信号**\ 、\ **文件副作用**\ 、\ **失败时先查什么**\ 、\ **参考链接**\ 。
所有示例模型都在本页同一目录里，请在存放 ``index_zh.rst`` 的目录运行命令。下面的输出来自该目录里的
``*.demo.py`` 与 ``*.demox.sh``，重新构建文档会重新生成它们。

1. 把一个状态拆成两个区域
-------------------------

**起点。** 一台平铺的机器，它的叶子状态是两个互相独立的关注点的乘积。``panel_flat.fcstm`` 有四个状态
（``CoolClosed``、``CoolOpen``、``HotClosed``、``HotOpen``）和八条转换；``panel_regions.fcstm`` 用两个各含两个状态的
区域、四条转换表达同一件事。

.. literalinclude:: panel_regions.fcstm
   :language: fcstm
   :caption: panel_regions.fcstm

**命令或代码。** 用同一组输入运行两个模型，每个周期后打印配置：

.. literalinclude:: split_state.demo.py
   :language: python
   :caption: split_state.demo.py

.. literalinclude:: split_state.demo.py.txt
   :language: text

**预期信号。** 只有一个输入变化的周期里，两个模型一致。第二个周期两个输入同时变化：平铺的机器只能走一条转换
（``HotClosed``），漏掉了门；区域版两条都走（``Panel{Temperature: Hot, Door: Open}``）。每个区域每个周期推进一次，
所以两个关注点在同一周期里变化时，拆分会改变行为。要拆分一台依赖单步行为的机器时，先检查这个差别。

**文件副作用。** 无。脚本读取两个 ``.fcstm`` 文件并输出到标准输出。

**失败时先查什么。** 加载失败时运行 ``pyfcstm inspect -i panel_regions.fcstm`` 读第一条错误；常见原因是有状态留在区域之外
（拥有者要么含区域，要么含子状态，不能混排，见任务 9）。

**参考链接。** :doc:`/reference/region_model/index_zh`。

2. 通过一个状态嵌套区域
-----------------------

**起点。** ``nested_cell.fcstm``。区域不能直接包含另一个区域，所以 ``Line`` 里放一个状态 ``Cell``，由 ``Cell`` 拥有
区域 ``Feed`` 与 ``Cut``。

.. literalinclude:: nested_cell.fcstm
   :language: fcstm
   :caption: nested_cell.fcstm

**命令或代码。**

.. literalinclude:: nest_regions.demo.py
   :language: python
   :caption: nest_regions.demo.py

.. literalinclude:: nest_regions.demo.py.txt
   :language: text

**预期信号。** 配置文本每个拥有者嵌套一层花括号：``Plant{Line: Cell{Feed: Waiting, Cut: Ready}, Monitor: Watching}``。
内层拥有者是一个状态，所以每条路径都经过区域名（``Plant.Line.Cell.Feed.Waiting``）。``leaves`` 列出三个活动叶子，
内层区域的 ``region_status`` 是 ``live``。

**文件副作用。** 无。

**失败时先查什么。** 若把 ``region`` 直接写进 ``region``，解析器会在内层关键字处停下（任务 9 给出确切报错）。在两者之间放一个状态。

**参考链接。** :doc:`/reference/region_model/index_zh`。

3. 让两个区域响应同一个事件
---------------------------

**起点。** ``shared_event.fcstm`` 在拥有者上声明 ``event Start;``，两个区域都使用 ``/Start``。``scoped_event.fcstm`` 是反例：
每个区域各自声明 ``Ping``，并使用 ``: Ping``。

.. literalinclude:: shared_event.fcstm
   :language: fcstm
   :caption: shared_event.fcstm

**命令或代码。**

.. literalinclude:: shared_events.demo.py
   :language: python
   :caption: shared_events.demo.py

.. literalinclude:: shared_events.demo.py.txt
   :language: text

**预期信号。** ``/Start`` 在一个周期里让两个区域都动。反例中 ``Rig.Left.Ping`` 与 ``Rig.Right.Ping`` 是两个不同的事件：
只写一个只让一个区域动，两个都写才让两个都动。裸名字（``Start``、``Ping``）被拒绝，因为它要对每个活动叶子各解析一次，
结果什么也没找到。区域里的 ``: 名字`` 归该区域，不会到拥有者里去找。

**文件副作用。** 无。

**失败时先查什么。** 事件被拒绝时读报错：它列出了尝试过的活动叶子。在模型和调用里都写完整路径或从根开始的路径（``/Start``）。

**参考链接。** :doc:`/reference/simulation/index_zh`。

4. 决定区域的书写顺序
---------------------

**起点。** ``controller.fcstm``\ （``Safety`` 在 ``Motion`` 之前）与 ``controller_swapped.fcstm``\ （两个区域对调）。书写顺序就是
执行顺序。经验法则：读取另一个区域所写内容的区域放在它后面（前向依赖）；读取靠后区域的值，看到的是上一个周期的值
（反向依赖）。

**命令或代码。** ``order_regions.demo.py`` 在第二个周期发送 ``/Start``，并在第 4、5 个周期把 ``fault`` 置为 1：

.. literalinclude:: order_regions.demo.py.txt
   :language: text

然后用 ``inspect`` 看哪种顺序可疑：

.. literalinclude:: order_check.demo.sh
   :language: bash

.. literalinclude:: order_check.demo.sh.txt
   :language: text

**预期信号。** ``controller.fcstm`` 在故障周期（第 4 周期）就已经是 ``permit=0 motor=0``。对调后的文件里第 4 周期电机仍是
``1``，晚一个周期才变 ``0``，故障解除后也晚一个周期恢复。``inspect`` 对 ``controller.fcstm`` 什么也不输出（过滤只保留区域顺序
诊断），对调换后的文件报告 ``I_REGION_BACKWARD_READ``；它是提示，不是缺陷。

**文件副作用。** 无。

**失败时先查什么。** 值晚一个周期到达时，先检查文件里区域的顺序，再改条件。

**参考链接。** :doc:`/reference/inspect_report/index_zh`。

5. 让各区域做完后一起往下走
---------------------------

**起点。** ``join_done.fcstm``：每个区域以 ``Run -> [*]`` 结束，拥有者有一条普通出边 ``Work -> Next``。``join_gate.fcstm``
给这条转换加了条件 ``gate``。

**命令或代码。**

.. literalinclude:: join_regions.demo.py
   :language: python
   :caption: join_regions.demo.py

.. literalinclude:: join_regions.demo.py.txt
   :language: text

**预期信号。** 完成的区域显示 ``[done]`` 并一直保持。最后一个区域完成时，拥有者在同一周期里续接（``Job.Next``）。
``join_gate.fcstm`` 里，``B`` 本该完成的周期中条件为假，于是最后一次完成被拒绝：``B`` 留在 ``Run``，它的 ``during`` 照常执行
（``ticks`` 增长），``A`` 保持 ``[done]``，机器不会停在全体已完成的位置。触发 ``B`` 完成的事件或条件不会保留到下一个周期；
``gate=1`` 的那个周期机器就离开了。

**文件副作用。** 无。

**失败时先查什么。** 拥有者不动时，检查每个区域是否都有能触发的 ``-> [*]``，以及拥有者出边的条件能否变真。某个区域永远
不能完成时 ``inspect`` 会报告 ``owner_never_completes``\ （见 inspect 页）。

**参考链接。** :doc:`/reference/region_model/index_zh`。

6. 从拥有者外面一次性打断整组
-----------------------------

**起点。** ``preempt_group.fcstm``：拥有者上的强制转换 ``!Job -> Idle : /Cancel``，以及把一位数字追加到 ``order`` 的 ``exit`` 动作。
``preempt_blocked.fcstm`` 把强制转换指向一个进不去的状态。

**命令或代码。** ``preempt_owner.demo.py`` 运行这两个模型，发送 ``/Cancel``\ （第二次运行还发送 ``/ADone``）：

.. literalinclude:: preempt_owner.demo.py.txt
   :language: text

强制转换是简写。``preempt_expansion.demo.py`` 用 ``to_ast_node()`` 打印展开后的模型，可以看到每个区域里实际有什么：

.. literalinclude:: preempt_expansion.demo.py.txt
   :language: text

**预期信号。** ``/Cancel`` 在一个周期里离开 ``Job``，退出按书写顺序执行：``1``\ （``A``）、``2``\ （``B``）、再是拥有者（``3``），
所以 ``order=123``。已经 ``[done]`` 的区域不会再次退出（第二次运行在 ``/ADone`` 时是 ``1``，最后仍是 ``123``）。目标进不去时，
区域依次结束直到最后一个：``A`` 变成 ``[done]``，``B`` 继续工作，机器不会停在退了一半的拥有者上。展开结果里有一个隐藏变量
``__forced_0`` 和每个区域里普通的 ``-> [*]``；这个变量和其他变量一样出现在 ``runtime.vars`` 里。

**文件副作用。** 无。

**失败时先查什么。** 没有离开时，检查事件名是否写成拥有者的事件 ``/Cancel``，以及目标状态能否经它的初始转换进入。

**参考链接。** :doc:`/reference/dsl/index_zh`。

7. 在一个区域里读另一个区域的状态
---------------------------------

**起点。** ``watch_regions.fcstm``：``Trigger`` 声明在两个读取者之间。``Later`` 把路径写成 ``active("/Trigger.Fired")``，
``Earlier`` 写成 ``active("Plant.Trigger.Fired")``；两者指向同一个状态。

**命令或代码。**

.. literalinclude:: watch_regions.demo.py
   :language: python
   :caption: watch_regions.demo.py

.. literalinclude:: watch_regions.demo.py.txt
   :language: text

**预期信号。** ``Trigger`` 到达 ``Fired`` 的那个周期，``Later`` 已经显示 ``Saw``；``Earlier`` 晚一个周期才显示 ``Saw``。
``active()`` 接受状态路径（不接受区域路径），从状态的 ``enter`` 开始到 ``exit`` 执行完毕为止都能看到该状态。

**文件副作用。** 无。

**失败时先查什么。** 构建时报 ``Invalid active query`` 说明写了区域，请改写区域里的某个状态。值晚一个周期，说明读取者
声明在写入者之前。

**参考链接。** :doc:`/reference/region_model/index_zh`。

8. 给区域添加切面
-----------------

**起点。** ``aspect_regions.fcstm``：``Plant`` 有祖先切面 ``>> during before``；``Left`` 与 ``Right`` 各有自己的区域切面。
``Left`` 可以用 ``/End`` 结束；``Right`` 的叶子没有 ``during`` 动作。

**命令或代码。** 脚本每个周期后打印计数器，``/End`` 在第三个周期发送：

.. literalinclude:: aspect_regions.demo.py
   :language: python
   :caption: aspect_regions.demo.py

.. literalinclude:: aspect_regions.demo.py.txt
   :language: text

**预期信号。** 三个叶子都在工作，祖先切面每个周期仍只执行一次（``ancestor`` 每次加一）。区域切面对每个有叶子在做
``during`` 步骤的区域每周期执行一次，即使该叶子没有声明 ``during`` 动作（``right`` 每个周期都增长）。``left`` 在 ``Left`` 结束的
那个周期停止增长，``Left`` 为 ``[done]`` 期间保持不变。

**文件副作用。** 无。

**失败时先查什么。** 区域切面始终不执行时，检查该区域是否已经 ``[done]``，以及它是否有叶子在本周期停留（叶子发生转换的周期
不执行该区域的切面）。

**参考链接。** :doc:`/reference/dsl/index_zh`。

9. 排查区域模型的常见错误
-------------------------

**起点。** 每种错误一个很小的模型，文件名为 ``err_*.fcstm``。

**命令或代码。** 每个 ``err_*.demox.sh`` 运行 ``pyfcstm inspect -i err_<名字>.fcstm --color never``。这些都是负例，不要复制这些模型。

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - 错误
     - 报告
     - 修法
   * - 转换离开了自己的区域（``err_cross_region``）
     - ``Invalid state machine model ...: Unknown to state 'Y' of transition:``
     - 把转换移进同一个区域，或让区域结束、由拥有者决定
   * - 普通子状态与区域并排（``err_mixed_children``）
     - ``Failed to parse input DSL file ...: Found 2 errors during parsing:``
     - 把普通状态包进区域，或去掉区域
   * - 没有状态的区域（``err_empty_region``）
     - ``Invalid region structure at Root.R (empty_region).``
     - 加一个状态和 ``[*] -> State;``，或删掉区域
   * - 两个区域同名（``err_duplicate_region``）
     - ``Duplicate region 'R' in Root.``
     - 给其中一个改名
   * - ``active()`` 指向区域（``err_active_region``）
     - ``Invalid active query 'Root.S' (region).``
     - 写区域里的某个状态
   * - 含区域的拥有者上有历史（``err_history_owner``）
     - ``Invalid region structure at Root.Owner (history_boundary).``
     - 去掉 ``[H]``，或把历史放在普通子树里
   * - 区域直接包含区域（``err_region_in_region``）
     - ``Failed to parse input DSL file ...: Found 3 errors during parsing:``
     - 在两个区域之间放一个状态

每份报告的全文和退出码都在生成的文件里。以 ``err_cross_region.demox.sh`` 为例：

.. literalinclude:: err_cross_region.demox.sh.err
   :language: text

退出码：

.. literalinclude:: err_cross_region.demox.sh.exitcode
   :language: text

其余六个脚本的报告在 ``err_mixed_children.demox.sh.err``、``err_empty_region.demox.sh.err``、``err_duplicate_region.demox.sh.err``、
``err_active_region.demox.sh.err``、``err_history_owner.demox.sh.err`` 与 ``err_region_in_region.demox.sh.err`` 里；
``pyfcstm inspect`` 把这些失败写到标准错误，标准输出为空。

**预期信号。** 每条命令都以退出码 1 结束，并输出上表中的某份报告。

**文件副作用。** 无。

**失败时先查什么。** 只修第一行报告，然后重新运行；后面的解析错误常常是第一个错误的后果。

**参考链接。** :doc:`/reference/diagnostics_codes/index_zh`。

其他工具的任务在哪里
--------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 任务
     - 页面
   * - 热启动、事件名、“什么都没发生”与 REPL
     - :doc:`/how_to/simulation/index_zh`
   * - 顺序诊断与 ``owner_never_completes``
     - :doc:`/how_to/inspect/index_zh`
   * - 查询、局部情形与代价
     - :doc:`/how_to/bmc/index_zh`
   * - 生成的运行时与容量宏
     - :doc:`/how_to/generation/index_zh`
   * - 支持区域的自定义模板
     - :doc:`/how_to/templates/index_zh`
   * - PlantUML、查看器与布局
     - :doc:`/how_to/visualization/index_zh`
   * - 一个模型的端到端验收
     - :doc:`/how_to/cli_workflows/index_zh`
