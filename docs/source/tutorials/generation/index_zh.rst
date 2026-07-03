第一次生成 runtime
==================

本教程展示使用打包内置模板生成 runtime 的最短路径。它刻意使用 ``--template``，而不是仓库里的 ``templates/`` 路径。

需要所有内置模板、native 冒烟构建或生成 README 入口的任务配方时，请阅读 :doc:`/how_to/generation/index_zh`。需要紧凑模板事实表时，请阅读 :doc:`/reference/builtin_templates/index_zh`。

示例模型
--------

所有示例使用这个很小的事件驱动模型：

.. literalinclude:: simple_machine.fcstm
   :language: fcstm

生成 Python 代码
----------------

渲染打包 Python 模板：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

输出目录包含 ``machine.py`` 和生成 README。runtime 自身是自包含的；使用生成输出时，用户代码不需要在运行时 import ``pyfcstm``。

运行生成 class
---------------

最小消费者 import 生成 class，创建机器，然后调用 ``cycle(...)``：

.. literalinclude:: python_runtime.demo.py
   :language: python
   :lines: 47-60

demo 输出证明生成的公开 API 可用：

.. literalinclude:: python_runtime.demo.py.txt
   :language: text

本教程省略了什么
----------------

native 模板和 polling 模板需要更多集成上下文。继续阅读 :doc:`/how_to/generation/index_zh`，了解：

* 生成 ``python``、``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 输出；
* 按生成目录说明编译 native 输出；
* 找到生成 README 和扩展点；
* 为应用选择合适的模板家族。
