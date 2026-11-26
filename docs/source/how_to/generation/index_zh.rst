.. _sec-how-to-generation-zh:

生成任务指南
============

当任务是运行 ``pyfcstm generate`` 并冒烟检查结果时，使用本指南。本页面面向生成代码用户；模板作者请看 :doc:`../templates/index_zh`，精确模板契约请看 :doc:`../../reference/builtin_templates/index_zh`。

当前内置状态
------------

pyfcstm 当前打包五个内置模板：``python``、``c``、``c_poll``、``cpp`` 和 ``cpp_poll``。它们在打包元数据中都标记为 ``experimental: true``。这个标记不表示模板只是占位；它表示当前输出是有测试证据的工程基线，不是生产认证或所有平台本机编译器保证。

选择生成入口
------------

``pyfcstm generate`` 必须且只能选择一种模板来源：

.. list-table:: 模板来源选择
   :header-rows: 1

   * - 使用选项
     - 何时使用
     - 边界
   * - ``--template <name>``
     - 需要已安装内置模板。
     - 这是内置模板的稳定用户路径。
   * - ``-t <dir>`` / ``--template-dir <dir>``
     - 正在编写或测试自定义模板目录。
     - 不要把仓库 ``templates/`` 源码目录写成普通用户入口。

同时传入两个选项会报用法错误；两个都不传也会报错。未知内置模板名会在渲染前被 Click 拒绝。

准备输入模型
------------

示例使用第一次教程里的小模型：

.. literalinclude:: /_models/simple_machine.fcstm
   :language: fcstm

生成每个内置模板
----------------

每个目标使用一条短命令：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear
   pyfcstm generate -i simple_machine.fcstm --template c -o generated/c --clear
   pyfcstm generate -i simple_machine.fcstm --template c_poll -o generated/c_poll --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp -o generated/cpp --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp_poll -o generated/cpp_poll --clear

``--clear`` 会在渲染前删除输出目录旧内容。它适合可重复示例和持续集成临时目录；不要对包含需保留文件的目录使用它。

先读生成 README
---------------

每个内置模板都会在输出目录写入 ``README.md`` 和 ``README_zh.md``。这些文件由你的模型生成，是具体机器的集成指南。参考页给通用契约；生成 README 给出该模型实际的类名、事件编号、钩子（hook）名称、状态编号、热启动（hot start）例子和构建片段。

把生成 README 当作从文档进入集成的交接点。如果通用参考和生成 README 看起来不一致，先以生成 README 中随机器变化的名称为准，再回到参考页核对模板家族、事件输入模型或证据边界是否被误读。

顶层生成文件如下：

.. list-table:: 生成文件摘要
   :header-rows: 1

   * - 模板
     - 文件
     - 主要用户入口
   * - ``python``
     - ``machine.py``、``README.md``、``README_zh.md``
     - 从 ``machine.py`` 导入生成的机器类。
   * - ``c``
     - ``machine.h``、``machine.c``、生成 README
     - 包含 ``machine.h``，把事件编号数组传给 ``..._cycle``。
   * - ``c_poll``
     - ``machine.h``、``machine.c``、生成 README
     - 安装 ``EventChecks``，调用事件轮询形式的周期函数。
   * - ``cpp``
     - C 核心文件加 ``machine.hpp`` / ``machine.cpp`` 和 README
     - 包含 ``machine.hpp``，使用 ``MachineWrapper``。
   * - ``cpp_poll``
     - C 轮询核心文件加 ``machine.hpp`` / ``machine.cpp`` 和 README
     - 包含 ``machine.hpp``，安装包装层事件检查，再使用 ``MachineWrapper``。

冒烟检查 Python 输出
--------------------

最小 Python 消费者导入 ``machine.py``。

下面的冒烟检查使用区域教程里的联锁控制器；请把 :download:`controller.fcstm </_models/controller.fcstm>` 下载到一个空目录。生成的 ``machine.py`` 不依赖 ``pyfcstm``，所以普通的 ``python`` 就能导入它：

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o generated/python --clear
   $ PYTHONPATH=generated/python python -c "import machine; print(machine.ControllerMachine.__name__)"
   ControllerMachine

这份证据表示生成的 Python 运行时可导入。真正发送事件、读取位置的消费者是 `含区域模型的任务`_ 里第一张任务卡的程序。更广的模拟器语义对齐由模板单元测试覆盖，不由这一条冒烟检查证明。

冒烟检查 C 和 C++ 输出
----------------------

本机检查需要 C 编译器，C++ 模板还需要 C++ 编译器和 ``cmake``，所以文档检查不运行它。任务卡 `设定 C 运行时的容量宏`_ 用一个小驱动构建生成的 ``c`` 运行时，给出命令和一次真实构建记录下的输出。

那张任务卡是本地冒烟检查。它证明生成文件在构建它的工具链上完成编译并运行；它不是对所有嵌入式编译器、工业配置、清理器配置或认证环境的声明。

如果本机冒烟检查失败，先记录编译器和 ``cmake`` 的版本，再判断失败属于生成器问题、构建工具缺失，还是自定义驱动和生成 README 不一致。不要只贴最后一行编译错误；模板维护者需要看到使用的模板名、输出目录、编译器版本和最小驱动。

选择显式事件或轮询
------------------

非轮询模板要求应用在每个周期提交事件：

.. list-table:: 事件输入模型
   :header-rows: 1

   * - 模板家族
     - 事件模型
     - 适用场景
   * - ``python``
     - ``cycle(events=None)`` 接受无事件、单个事件字符串或集合。
     - Python 应用代码已经知道哪些事件路径处于激活状态。
   * - ``c`` / ``cpp``
     - 周期调用接收生成的整数事件编号。
     - 集成层在调用运行时之前已经收集事件。
   * - ``c_poll`` / ``cpp_poll``
     - 运行时在周期中调用已安装的事件检查回调。
     - 主机通过回调、设备探针或应用状态读取事件真值。

只有当轮询形状正是你想要的集成面时，才使用 ``c_poll`` 或 ``cpp_poll``。它改变的是事件输入机制，不是 FCSTM 执行语义分叉。

同一个模型应先选择宿主应用最容易提供事件真值的模板。后续切换模板当然可以，但消费者代码、钩子安装方式和本机冒烟命令需要一起更新，这样生成 README 才仍然是唯一的集成检查清单。

建议在变更记录里写清楚三件事：选择了哪个模板、宿主侧如何提供事件、用哪条命令证明生成输出可用。这样后续读者不需要从输出目录反推集成方式，也更容易判断失败是输入事件、钩子安装还是构建环境造成的。

排查常见生成失败
----------------

.. list-table:: 失败排查表
   :header-rows: 1

   * - 现象
     - 常见原因
     - 修复
   * - ``Invalid value for '--template'``
     - 内置模板名不在已安装包中。
     - 运行 ``pyfcstm generate --help``，或使用 ``pyfcstm.template.list_templates()``。
   * - ``Exactly one of --template-dir/-t or --template must be provided.``
     - 同时传了两个模板选项，或两个都没传。
     - 在内置路径和自定义模板路径中选一个。
   * - YAML 或配置校验错误
     - 自定义模板 ``config.yaml`` 的根、分节、样式或忽略规则形状不合法。
     - 到 :doc:`../../reference/template_config/index_zh` 查失败形状。
   * - 模板渲染错误
     - Jinja 表达式、辅助导入、模型属性或自定义过滤器失败。
     - 缩减到小模型和单个模板文件，再检查辅助声明。
   * - 生成的本机代码无法编译
     - 输出契约、编译器、编译选项或集成驱动不匹配。
     - 先从生成 README 和最小驱动开始，再加入应用代码。

验证文档或模板改动
------------------

按声明选择最小证据：

.. list-table:: 证据层级
   :header-rows: 1

   * - 声明
     - 可用检查
     - 边界
   * - 生成命令可用
     - 对一个小 ``.fcstm`` 文件运行 ``pyfcstm generate``。
     - 不证明运行时语义。
   * - Python 输出可用
     - 导入 ``machine.py`` 并运行几个周期。
     - 不证明每个语义样例。
   * - 本机输出可在本地编译
     - 配置、构建并运行一个小 CMake 或驱动冒烟检查。
     - 仅是具体工具链证据。
   * - 模板声称模拟器语义一致
     - 运行该模板家族的语义对齐测试。
     - 必须说明事件模型、排除项和样例覆盖。

任务验收卡
----------

评审生成配方是否完整时，按下面的卡片检查。每张卡都写明起始输入、命令、成功信号、文件副作用和第一排查步骤。

.. list-table:: 内置生成任务卡
   :header-rows: 1

   * - 任务
     - 命令
     - 成功信号
     - 副作用和第一排查
   * - 生成 Python 运行时。
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template python -o /tmp/pyfcstm-python --clear``
     - 出现 ``machine.py`` 和生成 README；README 写出具体类名。
     - ``--clear`` 会替换临时输出目录。若失败，先确认输入模型能解析，再看模板。
   * - 生成显式事件 C 输出。
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template c -o /tmp/pyfcstm-c --clear``
     - 出现 ``machine.h`` 和 ``machine.c``，README 写出事件编号。
     - 后续编译冒烟检查必须使用生成头文件。事件名不清楚时，读生成 README，不要猜编号。
   * - 生成轮询 C 输出。
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template c_poll -o /tmp/pyfcstm-c-poll --clear``
     - ``machine.h`` 记录事件检查表形状。
     - 轮询需要事件真值回调。若事件一直不触发，先检查 ``EventChecks``，再改状态机逻辑。
   * - 生成 C++ 包装层。
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template cpp -o /tmp/pyfcstm-cpp --clear``
     - 除 C 核心外，还出现 ``machine.hpp`` 和 ``machine.cpp``。
     - 用户代码应包含 ``machine.hpp``。如果构建绕过包装层，冒烟检查就不能证明文档里的 C++ 集成面。
   * - 生成 C++ 轮询包装层。
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template cpp_poll -o /tmp/pyfcstm-cpp-poll --clear``
     - 生成包装层文件和轮询 README 指引。
     - 安装包装层事件检查。若转换不激活，检查该周期的回调返回值。
   * - 重新渲染到干净临时目录。
     - 只有输出目录可丢弃时才加 ``--clear``。
     - 旧生成文件消失，新树只包含当前输出。
     - 若手写文件被删，从版本控制恢复，并停止把该目录当临时输出。
   * - 使用自定义模板目录。
     - ``pyfcstm generate -i model.fcstm -t ./my_template -o ./out --clear``
     - 渲染器消费 ``./my_template/config.yaml`` 和目录里的 ``*.j2`` 文件。
     - 这是模板作者路径。若要使用打包内置模板，请用 ``--template``。
   * - 保留机器专属集成说明。
     - 每次生成后打开生成的 ``README.md``。
     - README 列出该模型的具体接口名、钩子名、编号和构建片段。
     - 若通用参考和生成 README 在名称上看似冲突，对该机器优先相信生成 README，并报告不一致。

模板选择检查表
--------------

.. list-table:: 选择内置目标
   :header-rows: 1

   * - 需求
     - 优先选择
     - 不要假设
   * - 纯 Python 集成和快速语义冒烟检查。
     - ``python``。
     - 不要把它当成 C 家族整数或编译器行为的证据。
   * - C 主机已经知道每个周期有哪些事件为真。
     - ``c``。
     - 不要安装轮询回调并期待显式事件接口调用它们。
   * - C 主机需要通过回调查询事件。
     - ``c_poll``。
     - 不要把回调轮询说成另一套状态机语义。
   * - C++ 应用想要包装层，但接受生成 C 核心。
     - ``cpp``。
     - 不要描述成完全独立的 C++ 运行时。
   * - C++ 应用需要包装层事件检查回调。
     - ``cpp_poll``。
     - 不要只测试 C 核心就声称包装层契约已验证。

失败演练和第一检查
------------------

.. list-table:: 生成失败演练
   :header-rows: 1

   * - 演练
     - 触发例子
     - 第一检查
     - 为什么先查这里
   * - 未知内置模板。
     - ``--template py``。
     - 用 ``pyfcstm.template.list_templates()`` 做小 Python 查询，或查看 ``pyfcstm generate --help``。
     - 错误发生在模板解包之前，修改输出文件没有帮助。
   * - 同时选择两种模板来源。
     - ``--template python -t ./template``。
     - 删除一个选项，用同一输入重跑。
     - 命令行入口故意要求模板来源唯一，避免信任边界和打包边界含混。
   * - 自定义 ``config.yaml`` 无效。
     - 顶层键写成 ``helperz``。
     - 改 Jinja 文件前，先对照 :doc:`../../reference/template_config/index_zh`。
     - 配置校验先于文件渲染，Jinja 语法不是第一嫌疑。
   * - Jinja 渲染失败。
     - 模板中写了 ``{{ state.unknown_attr }}``。
     - 缩减到一个模板文件和一个小模型，再参考现有模板使用的模型对象。
     - 此时模型已经解析完成，失败层是受信任模板表达式或辅助对象。
   * - 本机构建失败。
     - 头文件包含路径缺失、编译模式不对或钩子表不完整。
     - 用生成 README 的构建片段和最小驱动复现。
     - 应用构建失败可能混入了与生成输出无关的构建系统假设。

文档里的本机冒烟策略
--------------------

本页的小型本机冒烟检查是容量任务卡里的编译并运行驱动；更大的是仓库里的本机工具链模板测试（``PYFCSTM_RUN_NATIVE_TOOLCHAIN=1 make template_unittest TEMPLATE_UNITTEST_ARGS="--include-suites c --run-native-toolchain"``）。修改生成、C 家族模板文档或本机构建声明时，应运行其中之一，或写明当前环境不能运行的具体理由。

如果运行了，记录编译器版本和每个模板的结果。如果不能运行，不要把本机声明悄悄改成正文里的成功；写清缺少哪个二进制，例如 ``cmake``、``cc`` 或 ``c++``，并把结论限定在生成层，而不是本机运行层。

生成后的读者分流
----------------

第一次命令成功后，把读者引到真正负责后续问题的页面：

* 比较内置目标契约和实验状态时，读 :doc:`../../reference/builtin_templates/index_zh`；
* 下一步是写自定义模板目录时，读 :doc:`../templates/index_zh`；
* 需要查 ``config.yaml`` 键、样式、辅助对象或忽略规则时，读 :doc:`../../reference/template_config/index_zh`；
* 需要理解内置模板和自定义模板为什么共享同一个渲染器时，读 :doc:`../../explanations/template_rendering/index_zh`；
* 要把某个生成机器接入应用时，读那次生成输出里的 README。

可复用验收检查表
----------------

为项目撰写生成流程文档时，应在变更摘要或团队验收记录中写清这些事实：

* 修改了哪些页面，以及每个页面负责哪类读者角色；
* 用于 Python 消费者冒烟检查的 ``simple_machine.fcstm`` 生成命令；
* 是否运行了本机编译并运行的冒烟检查；若没有运行，写明缺少的工具或策略理由；
* 每个模板家族检查过哪些生成文件；
* 哪个生成 README 章节作为接口名称来源；
* 哪个参考页负责每个选项、模板名和配置键；
* 未知模板名、互斥模板选项、自定义配置无效、渲染失败和本机构建失败的第一失败边界；
* 普通用户正文是否用 ``--template`` 表示内置模板，并把 ``-t`` / ``--template-dir`` 保留给受信任自定义模板；
* C 家族语句是否绑定到 C 运行时辅助事实，而不是描述成 Python 或全平台行为。

验收时还要单独确认：

* 英文页和中文页使用同一组模板、同一组失败边界和同一组证据层级；
* 中文页首次交接“渲染器（renderer）”等术语后，后续普通正文不重复夹英文；
* 示例保持简短，输出来自真实运行，不手写；
* 若本机工具链不可用，验收记录写明这是环境限制，不把本机声明降级成未经验证的成功。

* 若引用生成 README，必须说明它是机器专属契约，不替代通用参考页。
* 若新增输出片段，必须来自真实运行，需要编译器的命令则写明未在文档检查里运行。

含区域模型的任务
----------------

每个内置模板（``python``、``c``、``c_poll``、``cpp`` 与 ``cpp_poll``）都能为含区域（region）的模型生成运行时。下面的任务卡使用
联锁控制器（:doc:`/tutorials/regions/index_zh`，:download:`controller.fcstm </_models/controller.fcstm>`），并给出同样的六项：\ **起点**\ 、\ **命令或代码**\ 、
\ **预期信号**\ 、\ **文件副作用**\ 、\ **失败时先查什么**\ 、\ **参考链接**\ 。生成的运行时与 :class:`pyfcstm.simulate.SimulationRuntime`
逐周期一致；建模任务见 :doc:`/how_to/regions/index_zh`。

生成五套运行时并运行 Python 的那一套
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** ``controller.fcstm`` 和 Python 3.7 及以上的解释器。生成的 ``machine.py`` 不依赖 ``pyfcstm``。请把 :download:`region_app.py` 下载到旁边。程序 ``region_app.py``
继承生成的类，实现两个输入读取方法，通过 ``configuration``、``leaves``、``is_active`` 与 ``region_status`` 读取位置；它还恢复一个热启动并发送事件。

.. literalinclude:: region_app.py
   :language: python
   :caption: region_app.py

**命令或代码。**

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o out/python --clear
   $ pyfcstm generate -i controller.fcstm --template c -o out/c --clear
   $ pyfcstm generate -i controller.fcstm --template c_poll -o out/c_poll --clear
   $ pyfcstm generate -i controller.fcstm --template cpp -o out/cpp --clear
   $ pyfcstm generate -i controller.fcstm --template cpp_poll -o out/cpp_poll --clear
   $ LC_ALL=C ls out/*
   out/c:
   README.md
   README_zh.md
   machine.c
   machine.h

   out/c_poll:
   README.md
   README_zh.md
   machine.c
   machine.h

   out/cpp:
   README.md
   README_zh.md
   machine.c
   machine.cpp
   machine.h
   machine.hpp

   out/cpp_poll:
   README.md
   README_zh.md
   machine.c
   machine.cpp
   machine.h
   machine.hpp

   out/python:
   README.md
   README_zh.md
   machine.py
   $ PYTHONPATH=out/python python region_app.py
   after start: Controller.Running{Safety: Watching, Motion: On}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.On']
     motor=1 permit=1
   is_active Running: True
   region_status Safety: live
   fault raised: Controller.Running{Safety: Watching, Motion: Off}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.Off']
     motor=0 permit=0
   hot start: Controller.Running{Safety: Watching, Motion: On}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.On']
     motor=1 permit=1
   hot start, one cycle later: Controller.Running{Safety: Watching, Motion: Off}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.Off']
     motor=0 permit=0
   after /Stop: Controller.Idle
     leaves ['Controller.Idle']
     motor=0 permit=0
**预期信号。** 列表给出各个模板生成的文件。程序把位置打印成文本（``Controller.Running{Safety: Watching, Motion: On}``）、活动叶子和变量。
``fault`` 升高后，电机在同一个周期关断。热启动不执行任何 ``enter`` 动作就把两个区域就位，``initial_vars`` 像其他变量一样携带隐藏变量 ``__forced_0``。
``/Stop`` 事件在一个周期里离开 ``Running``。

**文件副作用。** ``pyfcstm generate`` 把上面的文件写入输出目录，使用 ``--clear`` 时先清空该目录。这些命令把文件写在你运行命令的目录下的 ``out/``。

**失败时先查什么。** 程序抛出 ``SimulationRuntimeEventError`` 时读它的消息：依赖位置的名字会对每个活动叶子各解析一次，所以请写完整路径或 ``/名字``。
类名或方法与预期不同时，读生成的 ``README.md``：它是按这个模型写的。

**参考链接。** :doc:`/reference/builtin_templates/index_zh`。

设定 C 运行时的容量宏
~~~~~~~~~~~~~~~~~~~~~

**起点。** 同一个模型的 ``c`` 运行时、一个 C 编译器，以及 :download:`region_capacity_app.c`。机器的存储是静态预留的，``machine.h`` 里的两个宏决定其大小：
``CONTROLLER_MACHINE_ARENA_CAPACITY``\ （一次决策所检查的配置与待办项数）和 ``CONTROLLER_MACHINE_TRAIL_CAPACITY``\ （嵌套检查的层数）。
默认值按模型算出。只有周期以容量报错失败时才需要覆盖。覆盖后的值要对 ``machine.c`` 与每个包含 ``machine.h`` 的文件一致地定义。

.. literalinclude:: region_capacity_app.c
   :language: c
   :caption: region_capacity_app.c

**命令或代码。** 这些命令把程序构建三次：用默认值、用太小的值（演示失败）、用更大的值。它们需要 C 编译器，所以文档检查不运行；下面的输出来自对这些命令的一次真实运行：

.. code-block:: bash

   pyfcstm generate -i controller.fcstm --template c -o c_out --clear
   cp region_capacity_app.c c_out/app.c
   grep -E '^#define CONTROLLER_MACHINE_(ARENA|TRAIL)_CAPACITY' c_out/machine.h
   cd c_out
   cc -std=c99 -Wall -Wextra -pedantic -O2 machine.c app.c -lm -o app && ./app
   cc -std=c99 -Wall -Wextra -pedantic -O2 -DCONTROLLER_MACHINE_ARENA_CAPACITY=4 machine.c app.c -lm -o app && ./app
   cc -std=c99 -Wall -Wextra -pedantic -O2 -DCONTROLLER_MACHINE_ARENA_CAPACITY=480 -DCONTROLLER_MACHINE_TRAIL_CAPACITY=96 machine.c app.c -lm -o app && ./app

.. code-block:: text

   #define CONTROLLER_MACHINE_ARENA_CAPACITY 108
   #define CONTROLLER_MACHINE_TRAIL_CAPACITY 52
   storage bytes: 14272
   cycle 1: Controller.Idle motor=0
   cycle 2: Controller.Running{Safety: Watching, Motion: Off} motor=0
   cycle 3: Controller.Running{Safety: Watching, Motion: On} motor=1
   storage bytes: 3040
   cycle 1: Controller.Idle motor=0
   cycle 2 failed: Speculative search exceeded the capacity safety limit (4 configurations); define CONTROLLER_MACHINE_ARENA_CAPACITY to a larger value to allow a longer search.
   storage bytes: 55856
   cycle 1: Controller.Idle motor=0
   cycle 2: Controller.Running{Safety: Watching, Motion: Off} motor=0
   cycle 3: Controller.Running{Safety: Watching, Motion: On} motor=1

**预期信号。** 默认值够用：三个周期，退出状态 0。``ARENA_CAPACITY=4`` 时第 2 个周期（进入区域的那个）以 ``Speculative search exceeded the capacity safety limit`` 失败，
消息指出该宏；机器报告失败，而不是行为异常。更大的值同样成功，并让存储变大（``storage bytes``）。要确认选定的值够用，就用它运行你关心的场景：
值太小会明确失败，所以干净的运行就是证据。存储大小依赖平台（上面的数字来自一次 64 位构建）。

**文件副作用。** 这些命令把生成的源文件和可执行文件写入 ``c_out/``。

**失败时先查什么。** 读失败消息：它指出要调大的宏。程序只在某些构建里失败时，检查每个编译单元是否看到同一个 ``-D`` 值。

**参考链接。** :doc:`/reference/builtin_templates/index_zh`。

处理“模板没有声明 region”的拒绝
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**起点。** 目录 ``plain_template/`` 里的 :download:`plain_template/config.yaml` 和 :download:`plain_template/summary.txt.j2`：一个自定义模板，它的 ``config.yaml`` 没有在 ``features`` 里列出 ``region``；以及一个含区域的模型。为单一活动路径写的模板
会给区域生成错误的代码，所以 ``pyfcstm generate`` 在写任何文件之前就拒绝。这是负例。

**命令或代码。**

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm -t plain_template -o refused_out --clear
   generate with template directory '.../plain_template' does not support region models yet. (line 12)
   The model declares 2 regions, the first is 'Controller.Running.Safety'.
   If you write this template: its config.yaml does not list `region` under `features`. List it (`features: [region]`) only once the template really renders regions, because a template written for a single active path would generate wrong code for them, which is why it is refused. See "Declaring model features" in templates/README.md.
   If you write the model: use a template that supports regions. Built-in templates that support regions: c, c_poll, cpp, cpp_poll, python.
     pyfcstm generate -i controller.fcstm --template c -o refused_out
   Or take the regions out of the model.
   $ echo $?
   1
   $ test ! -e refused_out && echo "no output directory was written"
   no output directory was written
   $ pyfcstm generate -i controller.fcstm --template python -o refused_out --clear
   $ LC_ALL=C ls refused_out
   README.md
   README_zh.md
   machine.py

退出状态是 1。工具打印的是模板目录的绝对路径，这里用 ``...`` 省略。

**预期信号。** 消息指出第一个区域，并给出两条出路：写模板的人，在模板确实能渲染区域之后才声明 ``features: [region]``\ （见 :doc:`/how_to/templates/index_zh`）；
写模型的人，改用支持区域的模板。改用内置模板则成功（上面的最后两条命令）。

**文件副作用。** 失败时没有：不会创建输出目录。

**失败时先查什么。** 读以 ``If you write this template`` 或 ``If you write the model`` 开头的那一行，选适用的分支。

**参考链接。** :doc:`/reference/template_config/index_zh`。
