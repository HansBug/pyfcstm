.. _sec-how-to-generation-zh:

生成任务指南
============

当你需要生成并冒烟检查内置模板输出时，使用本指南。紧凑模板事实请查 :doc:`/reference/builtin_templates/index_zh`。

准备输入模型
------------

checked-in 示例使用这个模型：

.. literalinclude:: ../../tutorials/generation/simple_machine.fcstm
   :language: fcstm

生成并运行 Python 输出
----------------------

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

``--clear`` 适合可重复示例，因为它会在渲染前删除输出目录中的旧内容。如果输出目录里有 pyfcstm 应保留的文件，请省略该选项。

最小 Python 消费者从 ``machine.py`` import 生成 class：

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py
   :language: python
   :lines: 47-60

预期冒烟输出：

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py.txt
   :language: text

生成 C 或 C++ 输出
------------------

使用打包模板名：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template c -o generated/c --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp -o generated/cpp --clear

生成目录包含 ``README.md`` 和 ``README_zh.md``。这些 README 是具体生成机器的集成指南，包括 CMake skeleton 和 no-heap profile 说明。

当 ``cc``、``c++`` 和 ``cmake`` 可用时，文档 native 冒烟脚本会证明所有 native 家族的公开入口：

.. literalinclude:: ../../tutorials/generation/native_runtime.demo.sh.txt
   :language: text
   :lines: 1-43

生成 polling 输出
-----------------

Polling 模板把事件检测移动到集成层安装的 callbacks：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template c_poll -o generated/c_poll --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp_poll -o generated/cpp_poll --clear

当 C 集成代码需要安装 ``EventChecks`` 表，并让 runtime 在 ``cycle`` 中调用事件探针时，使用 ``c_poll``。当 C++ 应用代码应从 ``machine.hpp`` 和 wrapper methods 进入，同时在 wrapper 层安装 ``EventChecks`` 时，使用 ``cpp_poll``。

找到生成 README 和扩展点
------------------------

每个内置模板都会把生成 README 写在 runtime 旁边。把生成机器接入真实控制循环前，阅读这些文件以确认：

* 公开入口和 hook 名称；
* event-check 或 event-id 纪律；
* hot-start 和 lifecycle notes；
* 目标语言构建指南。

不要对内置模板使用 ``-t``
---------------------------

只有在你明确提供自定义模板目录时，才使用 ``-t`` / ``--template-dir``。内置模板应使用 ``--template``，这样打包资源会通过 pyfcstm 的模板系统被提取出来。
