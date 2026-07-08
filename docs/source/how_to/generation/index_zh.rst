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

.. literalinclude:: ../../tutorials/generation/simple_machine.fcstm
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
     - include ``machine.h``，把事件编号数组传给 ``..._cycle``。
   * - ``c_poll``
     - ``machine.h``、``machine.c``、生成 README
     - 安装 ``EventChecks``，调用事件轮询形式的周期函数。
   * - ``cpp``
     - C 核心文件加 ``machine.hpp`` / ``machine.cpp`` 和 README
     - include ``machine.hpp``，使用 ``MachineWrapper``。
   * - ``cpp_poll``
     - C 轮询核心文件加 ``machine.hpp`` / ``machine.cpp`` 和 README
     - include ``machine.hpp``，安装包装层事件检查，再使用 ``MachineWrapper``。

冒烟检查 Python 输出
--------------------

最小 Python 消费者导入 ``machine.py`` 并推进几个事件：

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py
   :language: python
   :lines: 47-60

已纳入文档构建的演示会打印：

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py.txt
   :language: text

这份证据表示生成的 Python 运行时可导入，并能执行展示的事件序列。更广的模拟器语义对齐由模板单元测试覆盖，不由这一条教程冒烟检查证明。

冒烟检查 C 和 C++ 输出
----------------------

文档树中的本机演示会生成 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 输出，并在 ``cc``、``c++`` 和 ``cmake`` 可用时构建小驱动。输出先给本地工具链快照，再按模板分段：

.. literalinclude:: ../../tutorials/generation/native_runtime.demo.sh.txt
   :language: text
   :lines: 1-28

这是本地冒烟检查。它证明生成文件在显示的工具链上完成编译并运行；它不是对所有嵌入式编译器、工业配置、清理器配置或认证环境的声明。

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
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template python -o /tmp/pyfcstm-python --clear``
     - 出现 ``machine.py`` 和生成 README；README 写出具体类名。
     - ``--clear`` 会替换临时输出目录。若失败，先确认输入模型能解析，再看模板。
   * - 生成显式事件 C 输出。
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template c -o /tmp/pyfcstm-c --clear``
     - 出现 ``machine.h`` 和 ``machine.c``，README 写出事件编号。
     - 后续编译冒烟检查必须使用生成头文件。事件名不清楚时，读生成 README，不要猜编号。
   * - 生成轮询 C 输出。
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template c_poll -o /tmp/pyfcstm-c-poll --clear``
     - ``machine.h`` 记录事件检查表形状。
     - 轮询需要事件真值回调。若事件一直不触发，先检查 ``EventChecks``，再改状态机逻辑。
   * - 生成 C++ 包装层。
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template cpp -o /tmp/pyfcstm-cpp --clear``
     - 除 C 核心外，还出现 ``machine.hpp`` 和 ``machine.cpp``。
     - 用户代码应 include ``machine.hpp``。如果构建绕过包装层，冒烟检查就不能证明文档里的 C++ 集成面。
   * - 生成 C++ 轮询包装层。
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template cpp_poll -o /tmp/pyfcstm-cpp-poll --clear``
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
     - include 路径缺失、编译模式不对或钩子表不完整。
     - 用生成 README 的构建片段和最小驱动复现。
     - 应用构建失败可能混入了与生成输出无关的构建系统假设。

文档里的本机冒烟策略
--------------------

``native_runtime.demo.sh`` 是本教程家族的规范小型本机冒烟检查。修改生成、C 家族模板文档或本机构建声明时，应运行它，或写明当前环境不能运行的具体理由。

如果运行了，记录工具链行和每个模板的成功段落。如果不能运行，不要把本机声明悄悄改成正文里的成功；写清缺少哪个二进制，例如 ``cmake``、``cc`` 或 ``c++``，并把结论限定在生成层，而不是本机运行层。

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
* 是否运行了 ``native_runtime.demo.sh``；若没有运行，写明缺少的工具或策略理由；
* 每个模板家族检查过哪些生成文件；
* 哪个生成 README 章节作为接口名称来源；
* 哪个参考页负责每个选项、模板名和配置键；
* 未知模板名、互斥模板选项、自定义配置无效、渲染失败和本机构建失败的第一失败边界；
* 普通用户正文是否用 ``--template`` 表示内置模板，并把 ``-t`` / ``--template-dir`` 保留给受信任自定义模板；
* C 家族语句是否绑定到 C 运行时辅助事实，而不是描述成 Python 或全平台行为。

验收时还要单独确认：

* 英文页和中文页使用同一组模板、同一组失败边界和同一组证据层级；
* 中文页首次交接“渲染器（renderer）”等术语后，后续普通正文不重复夹英文；
* 长脚本只通过 ``literalinclude`` 展示聚焦输出，不把整段脚本塞回正文；
* 若本机工具链不可用，验收记录写明这是环境限制，不把本机声明降级成未经验证的成功。

* 若引用生成 README，必须说明它是机器专属契约，不替代通用参考页。
* 若新增输出片段，必须来自当前文档资源或重新生成后的记录。
