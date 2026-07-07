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

``--clear`` 会在渲染前删除输出目录旧内容。它适合可重复示例和 CI 临时目录；不要对包含需保留文件的目录使用它。

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
