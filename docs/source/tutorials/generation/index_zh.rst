第一次生成运行时
================

本教程展示从一个 FCSTM 模型到一个可运行生成代码的最短路径。这里通过 ``--template`` 使用打包的 Python 内置模板（built-in template），不会把仓库里的 ``templates/`` 源码目录当成用户入口。

需要所有内置模板、本机目标（native target）冒烟检查（smoke check）、生成 README 入口或失败处理时，请阅读 :doc:`/how_to/generation/index_zh`。需要精确事实时，请阅读 :doc:`/reference/builtin_templates/index_zh` 和 :doc:`/reference/template_config/index_zh`。

本教程会运行什么
----------------

输入模型有三个叶状态和三条事件触发转换：

.. literalinclude:: simple_machine.fcstm
   :language: fcstm

生成 Python 代码
----------------

把打包的 Python 模板渲染到一个新的输出目录：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear

这个命令里最重要的是：

* ``--template python`` 选择已安装内置模板 ``python``。
* ``-o generated/python`` 指定生成输出目录。
* ``--clear`` 会先删除旧输出内容，让教程可以反复运行。

成功后会写出针对这个模型的文件。对本模型来说，顶层输出是：

.. code-block:: text

   README.md
   README_zh.md
   machine.py

``machine.py`` 是生成的运行时代码（runtime）。两个 README 也由同一个模型生成，是输出契约的一部分；集成具体生成机器时应先阅读它们。

运行生成类
----------

最小消费者导入生成类、构造实例、执行初始周期，然后提交事件路径：

.. literalinclude:: python_runtime.demo.py
   :language: python
   :lines: 47-60

已纳入文档构建的演示会先打印生成文件，再展示每个事件后的状态和 ``counter`` 值：

.. literalinclude:: python_runtime.demo.py.txt
   :language: text

这只证明第一次成功路径：生成成功、生成的 Python 文件可导入、一个小事件序列可运行。它不是所有 FCSTM 构造的完整语义对齐（semantic alignment）证明。

下一步
------

* 用 :doc:`/how_to/generation/index_zh` 生成 ``c``、``c_poll``、``cpp`` 或 ``cpp_poll`` 输出。
* 用 :doc:`/how_to/templates/index_zh` 编写自定义模板（custom template）目录。
* 用 :doc:`/explanations/template_rendering/index_zh` 理解渲染器（renderer）流程。
* 用 :doc:`/reference/builtin_templates/index_zh` 查内置模板契约。
