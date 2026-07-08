.. _sec-how-to-visualization-zh:

可视化任务
==========

当你需要图表源码或渲染后的图表文件时使用本指南。完整选项表见 :doc:`/reference/visualization_options/index_zh`。
首次图表流程见 :doc:`/tutorials/visualization/index_zh`。

具体输入和视觉证据
------------------

下面的具体示例使用 ``docs/source/tutorials/visualization/example.fcstm``。可视化教程已经从该源码生成
``output_minimal.puml.svg``、``output_normal.puml.svg`` 和 ``output_full.puml.svg``，所以本任务指南可以引用真实渲染产物，而不是只让读者相信选项名。

比较渲染图片前，先导出 PlantUML 源码：

.. code-block:: bash

   pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -o /tmp/example.puml

成功信号是 ``/tmp/example.puml`` 存在、以 ``@startuml`` 开头，并包含预期状态名。若源码导出失败，先修复 DSL/模型错误，再改渲染器设置。渲染选项无法修复无效的 PlantUML 源码。

先选择源码还是渲染产物
----------------------

.. list-table:: 输出选择
   :header-rows: 1

   * - 需求
     - 使用
     - 原因
   * - 可审阅的图表源码
     - ``pyfcstm plantuml``
     - 生成确定性的 ``.puml`` 文本，不需要渲染器。
   * - 图片或 PDF 产物
     - ``pyfcstm visualize``
     - 构造同一份 PlantUML 源码，并渲染成 ``png``、``svg`` 或 ``pdf``。
   * - 没有图形界面的持续集成（CI）
     - ``visualize --no-open``
     - 避免依赖桌面查看器。
   * - 私有图表
     - ``visualize --renderer local``
     - 避免把 PlantUML 源码发送给远程服务。

可视化任务验收卡片
------------------

决定某个图表步骤是否适合放进教程、审查记录或持续集成（CI）任务时，使用下表。

.. list-table:: 可视化任务证据
   :header-rows: 1

   * - 任务
     - 命令
     - 成功信号
     - 副作用
     - 第一排查步骤
   * - 审阅图表源码。
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -o /tmp/example.puml``
     - ``/tmp/example.puml`` 以 ``@startuml`` 开头，且是可比较差异的文本。
     - 只写指定源码文件。
     - PlantUML 导出失败时，先对同一输入运行 ``inspect``。
   * - 比较细节预设。
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -l full -o /tmp/example.full.puml``
     - full 源码包含 minimal 预设隐藏的生命周期/动作细节。
     - 写出第二个源码文件供审阅。
     - 混用预设和 ``-c`` 覆盖前，先查 :doc:`/reference/visualization_options/index_zh`。
   * - 检查渲染器可用性。
     - ``pyfcstm visualize --check --renderer auto``
     - 报告可用的本地/远程后端，或给出具体后端错误。
     - 不写图表文件。
     - 接受远程回退前，先判断隐私要求是否必须使用 ``--renderer local``。
   * - 无图形界面依赖地渲染。
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm -t svg -o /tmp/example.svg --no-open``
     - ``/tmp/example.svg`` 存在，并且在文档/审查上下文中可读。
     - 写出渲染文件，并可能填充渲染器缓存。
     - 若后端报告成功但文件缺失，把它当作渲染器失败，而不是 DSL 失败。
   * - 验证文档图。
     - 重新生成图源码后构建 HTML。
     - 图在文档宽度下清晰可读，图注说明它证明什么。
     - 图源码变化时更新生成图片。
     - 检查渲染后的 HTML；只看 reST 源码不能证明视觉质量。

导出 PlantUML 源码
------------------

PlantUML 源码是最安全的第一产物，因为它是文本、确定性强、容易比较差异：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

先使用细节预设，再添加单项覆盖：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

只有存在明确阅读目标时，才重复添加 ``-c key=value``：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=2 \
     -o machine.events-depth2.puml

比较细节预设输出
----------------

同一个模型可以按不同细节级别呈现给不同读者。下面示例复用可视化教程里的生成产物。

.. list-table:: 细节预设比较
   :header-rows: 1

   * - 预设
     - 目标读者
     - 优先隐藏内容
     - 现有源码
   * - ``minimal``
     - 架构讨论和非实现读者。
     - 生命周期动作和伪状态样式。
     - :download:`output_minimal.puml <../../tutorials/visualization/output_minimal.puml>`
   * - ``normal``
     - 通用文档和代码审查。
     - 生命周期动作体。
     - :download:`output_normal.puml <../../tutorials/visualization/output_normal.puml>`
   * - ``full``
     - 调试、语义审查和实现讨论。
     - 预设级开关不隐藏内容。
     - :download:`output_full.puml <../../tutorials/visualization/output_full.puml>`

.. figure:: ../../tutorials/visualization/output_minimal.puml.svg
   :alt: minimal 细节预设输出
   :align: center
   :width: 70%

   ``minimal`` 在读者只需要结构时保持图形清晰。

.. figure:: ../../tutorials/visualization/output_normal.puml.svg
   :alt: normal 细节预设输出
   :align: center
   :width: 70%

   ``normal`` 是文档和审查的默认折中。

.. figure:: ../../tutorials/visualization/output_full.puml.svg
   :alt: full 细节预设输出
   :align: center
   :width: 70%

   ``full`` 适合动作和转换细节也是审查内容的场景。

聚焦大型模型
------------

大型状态机应先收窄问题，再增加视觉细节。好的聚焦图通常回答以下问题之一：

* 状态层级是什么？
* 哪些事件驱动模型移动？
* 哪些保护条件和效果控制某组转换？
* 哪些生命周期钩子是集成点？
* 本次审查要讨论哪棵子树？

实用命令模式：

.. code-block:: bash

   # 限制层级深度。
   pyfcstm plantuml -i machine.fcstm -c max_depth=2 -o machine.depth2.puml

   # 结构是主题时隐藏事件名。
   pyfcstm plantuml -i machine.fcstm -c show_events=false -o machine.structure.puml

   # 事件流是主题时显示事件分组。
   pyfcstm plantuml -i machine.fcstm \
     -c event_visualization_mode=both \
     -o machine.events.puml

   # 输出紧凑实现视图。
   pyfcstm plantuml -i machine.fcstm \
     -l full \
     -c max_action_lines=3 \
     -c transition_effect_mode=inline \
     -o machine.compact-full.puml

直接渲染最终文件
----------------

当环境应负责渲染时，使用 ``visualize``：

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

不读取领域特定语言（DSL）文件，只检查渲染器可用性：

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

明确选择渲染器模式：

.. list-table:: 渲染器选择
   :header-rows: 1

   * - 模式
     - 命令形态
     - 适用场景
   * - ``auto``
     - ``pyfcstm visualize --check --renderer auto``
     - 本地开发中，本地或远程渲染任一可用都可以。
   * - ``local``
     - ``pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open``
     - 图表私有，或构建不应依赖网络。
   * - ``remote``
     - ``pyfcstm visualize -i machine.fcstm --renderer remote --no-open``
     - 允许使用配置的 PlantUML 服务，并且比本地 Java 设置更方便。

保持 CI 图表任务稳定
--------------------

CI 图表任务不应依赖桌面查看器：

.. code-block:: bash

   pyfcstm plantuml -i machines/main.fcstm -o build/main.puml
   pyfcstm visualize -i machines/main.fcstm -t svg -o build/main.svg --no-open

如果渲染在持续集成中是可选项，把源码导出和渲染导出拆开。源码导出证明 pyfcstm 能解析并输出 PlantUML；渲染导出额外证明渲染后端可用。

命令行取值不够时使用 Python API（应用程序接口）
------------------------------------------------

命令行支持标量和元组值。需要事件颜色字典这类对象配置时，使用 Python API（应用程序接口）：

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   options = PlantUMLOptions(
       event_visualization_mode='color',
       custom_colors={'System.Start': '#00AA00'},
   )
   plantuml_text = model.to_plantuml(options)

完整可运行示例可下载
:download:`python_basic.demo.py <../../tutorials/visualization/python_basic.demo.py>` 和
:download:`python_options.demo.py <../../tutorials/visualization/python_options.demo.py>`。

具体可视化配方
----------------

每个配方先写读者目标。需要可审查性时先导出源码；只有需要图片产物时才渲染。

.. list-table:: 聚焦可视化配方
   :header-rows: 1

   * - 读者目标
     - 命令
     - 预期产物
     - 边界
   * - 只审查层级。
     - ``pyfcstm plantuml -i machine.fcstm -l minimal -o machine.structure.puml``
     - 紧凑 ``.puml`` 源码，隐藏实现细节。
     - 不检查任何渲染器。
   * - 审查状态/事件流。
     - ``pyfcstm plantuml -i machine.fcstm -c event_visualization_mode=both -o machine.events.puml``
     - 源码包含面向事件的标签、图例或颜色事实。
     - 事件着色可能让大图变密。
   * - 审查生命周期钩子。
     - ``pyfcstm plantuml -i machine.fcstm -l full -c show_concrete_actions=false -o machine.hooks.puml``
     - 抽象钩子可见，具体动作体隐藏。
     - 适合集成讨论，不适合动作体审计。
   * - 审查大型子树。
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=2 -o machine.depth2.puml``
     - 深层后代在第 2 层后折叠。
     - 被隐藏的后代仍然存在于模型中。
   * - 在 CI 中产出图片。
     - ``pyfcstm visualize -i machine.fcstm -t svg -o build/machine.svg --no-open``
     - SVG 文件出现在请求路径。
     - 需要已配置的本地或远程渲染器。
   * - 渲染前检查后端。
     - ``pyfcstm visualize --check --renderer auto``
     - 后端可用性报告。
     - 不解析 DSL，也不证明图表内容。

视觉审查清单
~~~~~~~~~~~~

文档接受新增或修改图之前，检查渲染后的 HTML，并回答：

* 标签在配置宽度下是否可读？
* 图注是否说明该图证明什么？
* 图源是否能追踪到 ``.fcstm`` 或 ``.puml`` 输入？
* 是否真的需要密集 ``full`` 视图，还是 ``normal`` 加一个覆盖项更清晰？
* 如果使用远程渲染，PlantUML 源码离开本机是否可接受？



任务卡片
--------

上面的配方是简短命令选择；下面的卡片把常见任务展开成完整 how-to 合同：起始输入、命令、预期信号、副作用和第一步修复。新增可视化任务时，应保持这种具体度，而不是只追加命令列表。

.. list-table:: 任务卡片
   :header-rows: 1

   * - 任务
     - 起点
     - 命令
     - 预期信号和副作用
     - 失败时的第一步修复
   * - 只审查层次
     - ``docs/source/tutorials/quick_start/traffic_light.fcstm`` 或另一个小型源文件。
     - ``pyfcstm plantuml -i traffic_light.fcstm -l minimal -o traffic_light.minimal.puml``。
     - 文本文件以 ``@startuml`` 开头，并包含紧凑状态层次；不需要渲染器。
     - 如果写文件前失败，先运行 ``pyfcstm inspect -i traffic_light.fcstm`` 定位解析/模型错误。
   * - 解释事件和 guard
     - 转换使用事件或 guard 的模型。
     - ``pyfcstm plantuml -i machine.fcstm -l normal -c show_events=true -c show_transition_guards=true -o machine.events.puml``。
     - 源标签应显示该转换族使用的事件名和 guard 条件。
     - 如果标签缺失，确认转换语法确实包含事件/guard，且没有覆盖项隐藏它们。
   * - 展示集成钩子
     - 带抽象生命周期动作的模型。
     - ``pyfcstm plantuml -i machine.fcstm -l full -c show_concrete_actions=false -o machine.hooks.puml``。
     - 源会突出抽象钩子，同时抑制实现体。
     - 如果图仍过密，添加 ``-c max_action_lines=2``，或用 ``max_depth`` 拆分。
   * - 生成 CI SVG 产物
     - 安装了 pyfcstm 且有被批准 PlantUML 后端的 CI 任务。
     - ``pyfcstm visualize -i machine.fcstm -t svg -o artifacts/machine.svg --no-open``。
     - SVG 文件存在；标准输出报告渲染器和输出路径；不需要桌面查看器。
     - 如果渲染器发现失败，运行 ``pyfcstm visualize --check --renderer auto``，再决定本地或远程渲染是否允许。
   * - 保持私有图本地渲染
     - 机密模型和本地 PlantUML jar。
     - ``pyfcstm visualize -i private.fcstm --renderer local -p ./plantuml.jar -t png -o private.png --no-open``。
     - PNG 被写出，PlantUML 源不会发给远程服务。
     - 如果本地渲染失败，修复 Java/JAR 路径；除非允许远程回退，否则不要切到 ``auto``。
   * - 诊断选项解析错误
     - 使用 ``-c`` 覆盖项的命令。
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=abc`` 可作为有意失败探针。
     - 命令应点名非法键/值，而不是写出误导性源码。
     - 把值改成整数，或移除该覆盖项。

视觉验收例子
~~~~~~~~~~~~

生成图以后，应检查实际渲染 HTML 或图片，而不只是检查源命令。使用这组简短验收规则：

1. 图注说明这张图回答的问题。
2. 所选预设匹配问题：``minimal`` 用于层次，``normal`` 用于转换，只有生命周期/动作细节本身是重点时才用 ``full``。
3. 文本在文档宽度下可读。若不可读，优先减少细节，而不是单纯放大图片。
4. 渲染路径符合数据边界：私有模型用本地渲染，只有源文本允许离开本机时才用远程。
5. 页面应链接到 :doc:`/reference/visualization_options/index_zh`，解释所有非显而易见的选项。

排查可视化问题
--------------

.. list-table:: 可视化排查
   :header-rows: 1

   * - 现象
     - 检查
     - 可能修复
   * - ``plantuml`` 失败
     - ``pyfcstm inspect -i machine.fcstm``
     - 先修复 DSL 语法或模型诊断，再导出图表。
   * - ``visualize`` 渲染前失败
     - 输出后缀和 ``--type``
     - 对齐后缀和类型，或省略后缀让 pyfcstm 自动补。
   * - 本地渲染失败
     - ``pyfcstm visualize --check --renderer local``
     - 配置 Java 和 ``PLANTUML_JAR``，或传 ``-p``。
   * - 远程渲染失败
     - ``pyfcstm visualize --check --renderer remote``
     - 检查网络、代理或 ``PLANTUML_HOST``。
   * - 查看器启动被跳过
     - ``PYFCSTM_NO_GUI``、``CI``、显示环境变量
     - 脚本中使用 ``--no-open``；``--strict-open`` 只留给桌面任务。
   * - 图表太密
     - 细节级别和可见性选项
     - 从 ``minimal`` 或 ``normal`` 开始，只添加当前读者需要的事实。
