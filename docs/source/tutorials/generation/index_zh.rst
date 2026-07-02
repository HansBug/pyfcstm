内置模板生成
============

本教程是打包内置模板的用户侧入口。它说明如何用 ``--template`` 渲染模型，如何运行生成的
Python runtime，如何对 native runtime 做冒烟编译/运行，以及什么时候继续阅读生成目录里的
README。

如果你要编写或维护模板，请阅读 :doc:`/tutorials/render/index_zh`\ 。本页面面向想直接使用内置输出的用户。

示例模型
--------

所有示例共用一个很小的事件驱动模型，这样便于对比不同模板生成物的行为：

.. literalinclude:: simple_machine.fcstm
   :language: fcstm

第一次空 cycle 会进入 ``SimpleMachine.Idle``\ 。随后 ``Start`` 转到 ``Running``\ ，``Stop`` 转到
``Stopped`` 并让 ``counter`` 加一，``Reset`` 再回到 ``Idle``\ 。

内置模板使用 ``--template``
----------------------------

对内置模板，使用打包模板名：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

当前内置模板名包括：

.. list-table:: 内置模板
   :header-rows: 1

   * - 模板
     - 主要输出形态
     - 用户入口
   * - ``python``
     - ``machine.py`` 和生成 README
     - import 生成的 Python class
   * - ``c``
     - ``machine.h`` / ``machine.c`` 和生成 README
     - C 集成代码 include ``machine.h``
   * - ``c_poll``
     - ``machine.h`` / ``machine.c`` 和生成 README
     - 安装 ``EventChecks`` 并调用不接收 event-id 数组的 ``cycle`` API
   * - ``cpp``
     - C core 文件加 ``machine.hpp`` / ``machine.cpp``
     - include ``machine.hpp`` 并使用 ``MachineWrapper``
   * - ``cpp_poll``
     - C poll core 文件加 ``machine.hpp`` / ``machine.cpp``
     - include ``machine.hpp``\ ，安装 ``EventChecks``\ ，并使用 ``MachineWrapper``

只有在你明确提供自定义模板目录时，才使用 ``-t`` / ``--template-dir``\ 。这不是内置模板的默认路径。

生成 README 是输出契约的一部分
------------------------------

每个内置模板都会在输出目录中写入生成的 ``README.md`` 和 ``README_zh.md``\ 。本教程只保留短小的端到端路径；生成 README 才是具体生成机器的详细 API 和集成说明。

不要把下面的例子原样当成生产控制循环。它们只是证明生成的公开入口可用的冒烟测试。真正集成 hooks、hot start、no-heap profile、构建系统细节或目标平台部署规则前，请阅读生成 README。

本教程的验证摘要
----------------

下面的例子由 ``docs/source/tutorials/generation/`` 下面 checked-in 的 demo 脚本和 driver 源文件支撑。文档资源构建会通过 ``make -C docs contents`` 重新生成输出。

.. list-table:: 教程验证矩阵
   :header-rows: 1

   * - 模板
     - demo 是否真实生成
     - demo 是否做 runtime 冒烟检查
     - 本页展示的入口纪律
   * - ``python``
     - 是，通过 ``python_runtime.demo.py``
     - 是，import 后执行四个 cycle
     - 从 ``machine.py`` 里的生成 class 进入
   * - ``c``
     - 是，通过 ``native_runtime.demo.sh``
     - 是，在 ``cc`` 可用时编译运行
     - C driver include ``machine.h``
   * - ``c_poll``
     - 是，通过 ``native_runtime.demo.sh``
     - 是，在 ``cc`` 可用时编译运行
     - C driver 安装完整 ``EventChecks`` 表
   * - ``cpp``
     - 是，通过 ``native_runtime.demo.sh``
     - 是，在 ``cc`` 和 ``c++`` 可用时编译运行
     - C++ driver include ``machine.hpp`` 并使用 ``MachineWrapper``
   * - ``cpp_poll``
     - 是，通过 ``native_runtime.demo.sh``
     - 是，在 ``cc`` 和 ``c++`` 可用时编译运行
     - C++ driver include ``machine.hpp`` 并安装 wrapper ``EventChecks``

native 输出会记录本地 OS、C 编译器、C++ 编译器和 CMake 版本。这是本教程运行环境的证据，不承诺所有工业或嵌入式编译器都接受完全相同的 flags。

Python 模板
-----------

生成 Python 代码：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

生成的 ``machine.py`` 是自包含文件，runtime 不依赖 ``pyfcstm``\ 。最小消费者 import 生成 class，创建机器，然后调用 ``cycle(...)``\ ：

.. literalinclude:: python_runtime.demo.py
   :language: python
   :lines: 47-60

demo 输出刻意保持短小：

.. literalinclude:: python_runtime.demo.py.txt
   :language: text

C 模板
------

生成 C 代码：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template c -o generated/c --clear

用户侧集成面是 ``machine.h``\ 。生成的 ``machine.c`` 拥有 runtime 实现。一个很小的 driver 会把显式 event-id 数组传给 ``cycle``\ ：

.. literalinclude:: c_driver.c
   :language: c
   :lines: 26-53

native demo 使用的直接编译命令是：

.. code-block:: bash

   cc -std=c99 -Wall -Wextra -pedantic -O2 machine.c app.c -lm -o demo

工程化集成时，更推荐把生成 runtime 放进普通构建系统 target。生成 README 里包含 CMake skeleton 和 no-heap profile 说明。在 Windows 和非 POSIX 嵌入式工具链上，应按目标工具链调整数学库和编译 flags，不要无条件复制 ``-lm``\ 。

C poll 模板
-----------

生成 poll 风格 C 代码：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template c_poll -o generated/c_poll --clear

``c_poll`` 不接受每个 cycle 外部传入的 event-id 数组。集成层需要先安装生成的 ``EventChecks`` 表，runtime 在判断迁移时调用对应 ``check_xxx`` 回调。

回调返回值就是当前 cycle 的事件真值：

- 返回非零：该事件此刻 active
- 返回 ``0``\ ：该事件此刻 inactive

如果模型声明了事件，就必须在 ``cycle(&machine)`` 前安装完整表。checked-in 的 C poll driver 还包含很小的 ``print_state`` / ``run_cycle`` helpers；下面摘录保留 event-check callbacks 以及安装/触发路径，完整文件仍在本目录中可直接阅读：

.. literalinclude:: c_poll_driver.c
   :language: c
   :lines: 5-39,59-91

回调函数可以读取采样输入、现场总线镜像、process image bits 或其他用户维护的快照。它们应该像“读取当前扫描拍的只读探针”，而不是 destructive consume/ack 操作。

C++ wrapper 模板
----------------

生成 C++ wrapper 代码：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template cpp -o generated/cpp --clear

``cpp`` 模板包含 C runtime core，但用户侧 C++ 代码应该 include ``machine.hpp`` 并使用生成的 ``MachineWrapper`` facade。教程和应用 driver 都不应该绕开 wrapper，把 ``machine.h`` 当成 C++ 主入口。

.. literalinclude:: cpp_driver.cpp
   :language: cpp
   :lines: 1-5,17-38

该 demo 把 ``machine.c`` 按 C 编译，再把 ``machine.cpp`` 和 ``app.cpp`` 按 C++98-compatible C++ 编译，最后统一链接。

C++ poll wrapper 模板
---------------------

生成 poll 风格 C++ wrapper：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template cpp_poll -o generated/cpp_poll --clear

``cpp_poll`` 遵循和 ``c_poll`` 相同的事件检查契约。C++ 侧的重要纪律是应用代码仍然从 ``machine.hpp`` 和 wrapper methods 进入。wrapper 暴露 ``EventChecks`` 和 ``set_event_checks(...)``\ ，因此 driver 不需要把 C header 当作主集成面。下面摘录保留 wrapper 入口、callback bodies 和安装/触发路径；checked-in 文件里还包含围绕同一套 wrapper API 的小型 ``print_state`` helper。

.. literalinclude:: cpp_poll_driver.cpp
   :language: cpp
   :lines: 1-41,53-85

Native 冒烟输出
---------------

本 native demo 会在本地工具链可用时生成并运行四个 native 风格模板：

.. literalinclude:: native_runtime.demo.sh.txt
   :language: text

用这段输出确认教程示例和当前模板保持同步。超出这个冒烟路径的目标平台构建集成，请继续阅读生成 README。

模板选择提示
------------

.. list-table:: 选择提示
   :header-rows: 1

   * - 需求
     - 优先看
   * - Python-only 集成、测试或与 simulator 对齐的实验
     - ``python``
   * - C 集成，且外围应用已经收集 event ids
     - ``c``
   * - C 扫描循环集成，事件真值按需采样
     - ``c_poll``
   * - C++ 集成，但仍想复用当前 C runtime core
     - ``cpp``
   * - C++ 扫描循环集成，并希望在 wrapper 层安装 event checks
     - ``cpp_poll``

下一步
------

- 使用 :doc:`/tutorials/cli/index_zh` 查询命令行选项。
- 想设计或维护模板时，阅读 :doc:`/tutorials/render/index_zh`\ 。
- 把生成代码集成到真实应用前，阅读各输出目录里的 ``README.md`` / ``README_zh.md``\ 。
