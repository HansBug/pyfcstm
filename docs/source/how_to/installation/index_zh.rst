.. _sec-how-to-installation-zh:

安装 pyfcstm
============

当你需要在本机或 CI runner 中得到可用的 ``pyfcstm`` 命令时，使用本指南。项目支持 Python 3.7 到 3.14，因此下面的命令避免依赖过新的 Python 工具假设。

从 PyPI 安装
------------

普通使用场景下，安装已发布的包：

.. code-block:: bash

   python -m pip install pyfcstm

如果环境里有多个 Python 解释器，请使用真正要运行 CLI 的解释器：

.. code-block:: bash

   python3 -m pip install pyfcstm

从 main 分支安装
----------------

只有在你明确想使用仓库最新状态，而不是最新 PyPI release 时，才使用 GitHub 源码安装：

.. code-block:: bash

   python -m pip install -U git+https://github.com/hansbug/pyfcstm@main

验证 Python 包
--------------

安装教程里保留了一个 checked-in 验证脚本。任何项目都可以用同样思路导入包元数据：

.. literalinclude:: ../../tutorials/installation/install_check.demo.py
   :language: python
   :linenos:

预期输出形态：

.. literalinclude:: ../../tutorials/installation/install_check.demo.py.txt
   :language: text
   :linenos:

验证 CLI
--------

先检查顶层命令：

.. code-block:: bash

   pyfcstm -v
   pyfcstm --help

文档构建也会运行这个 shell 检查：

.. literalinclude:: ../../tutorials/installation/cli_check.demo.sh
   :language: shell
   :linenos:

.. literalinclude:: ../../tutorials/installation/cli_check.demo.sh.txt
   :language: text
   :linenos:

排查清单
--------

* 如果 ``pyfcstm`` 不在 ``PATH`` 中，用安装该包的解释器运行 ``python -m pyfcstm --help``。
* 如果 CI job 使用 virtual environment，请先激活环境再安装 pyfcstm。
* 如果需要渲染 PlantUML 图片，需要额外安装和配置 PlantUML backend。``simulate``、``inspect``、``generate`` 以及 ``plantuml`` 源码导出等核心命令不需要本地渲染器。

下一步
------

* :doc:`/tutorials/quick_start/index_zh` 给出最短端到端路径。
* :doc:`/how_to/cli_workflows/index_zh` 展示常见命令行任务。
* :doc:`/reference/cli/index_zh` 列出命令和选项事实。
