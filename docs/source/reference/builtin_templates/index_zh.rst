.. _sec-reference-builtin-templates-zh:

内置模板参考
============

这些名称用于 ``pyfcstm generate --template <name>``。不要用仓库里的 ``templates/`` 路径来访问内置模板。

模板矩阵
--------

.. list-table:: 内置模板
   :header-rows: 1

   * - 模板
     - 主要文件
     - 用户入口
     - 说明
   * - ``python``
     - ``machine.py``、``README.md``、``README_zh.md``
     - 从 ``machine.py`` import 生成 class。
     - 适合 Python 集成和与 simulator 对齐的实验；runtime 自包含。
   * - ``c``
     - ``machine.h``、``machine.c``、生成 README
     - include ``machine.h``，并把显式 event-id 数组传给 ``cycle``。
     - 适合外围应用已经收集 events 的 C 集成。
   * - ``c_poll``
     - ``machine.h``、``machine.c``、生成 README
     - 调用不接收 event-id 数组的 ``cycle`` API 前，安装完整 ``EventChecks`` 表。
     - 适合按需采样事件真值的 C scan-loop 集成。
   * - ``cpp``
     - C core 文件加 ``machine.hpp`` 和 ``machine.cpp``
     - include ``machine.hpp`` 并使用 ``MachineWrapper``。
     - 模板包含 C core，但 C++ 用户代码不应绕开 wrapper 作为主入口。
   * - ``cpp_poll``
     - C poll core 文件加 ``machine.hpp`` 和 ``machine.cpp``
     - include ``machine.hpp``，安装 wrapper ``EventChecks``，并使用 ``MachineWrapper``。
     - 适合在 wrapper 层安装 event checks 的 C++ scan-loop 集成。

生成 README
-----------

所有内置模板都会把 ``README.md`` 和 ``README_zh.md`` 写入输出目录。这些文件是生成输出契约的一部分，包含针对具体机器的 API、hook、hot-start 和构建指南。

目标 profile 说明
-----------------

C-family 模板在默认 profile 中使用固定宽度生成整数存储。因此 inspect 数值部署 warning 适用于 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 目标。不应把它表述成 Python generated runtime 也具有同一个固定宽度整数承载风险的证据。

更多任务
--------

生成和冒烟检查任务请见 :doc:`/how_to/generation/index_zh`。
