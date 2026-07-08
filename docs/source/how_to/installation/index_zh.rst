.. _sec-how-to-installation-zh:

安装 pyfcstm
============

当你需要在本机或持续集成（CI）运行器上得到可用的 ``pyfcstm`` 命令时使用本指南。项目支持 Python 3.7 到 3.14，所以下面的命令避免只适用于最新 Python 的假设。

安装包含什么
------------

普通包安装是当前公开运行依赖的一体化安装。它会安装命令行、解析器、模型层、模拟器、渲染器、诊断、验证支持和可视化集成。
它不会安装 Java、PlantUML jar、Graphviz 或桌面查看器这类外部系统程序。

.. list-table:: 包安装后的能力
   :header-rows: 1

   * - 能力
     - Python 包安装是否包含
     - 有时需要的外部工具
   * - 解析领域特定语言（DSL）并构建模型
     - 是
     - 不需要
   * - ``simulate``
     - 是
     - 不需要
   * - ``inspect`` 和有界验证集成
     - 是
     - 普通 inspect 使用不需要额外系统工具
   * - 使用打包模板的 ``generate``
     - 是
     - Python 生成不需要；只有构建生成的 C/C++ 产物时才需要目标编译器
   * - ``plantuml`` 源码导出
     - 是
     - 不需要
   * - ``visualize`` 渲染输出
     - Python 集成包含
     - 本地渲染需要 Java 和 PlantUML jar，或需要能访问远程 PlantUML 服务

从 PyPI 安装
------------

普通使用时，用将要运行命令行的解释器安装发布包：

.. code-block:: bash

   python -m pip install pyfcstm

如果机器上有多个 Python 解释器，请显式指定：

.. code-block:: bash

   python3 -m pip install pyfcstm
   python3 -m pyfcstm --help

项目本地工作建议使用虚拟环境：

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -U pip
   python -m pip install pyfcstm
   pyfcstm --help

Windows ``cmd.exe`` 中通常这样激活：

.. code-block:: bat

   py -m venv .venv
   .venv\Scripts\activate
   python -m pip install -U pip
   python -m pip install pyfcstm
   pyfcstm --help

从 main 分支安装
----------------

只有你明确需要当前仓库状态而不是最新 PyPI 发布时，才使用源码安装：

.. code-block:: bash

   python -m pip install -U git+https://github.com/hansbug/pyfcstm@main

在项目自动化里固定分支、标签或提交。未固定的源码安装可能在构建配置不变时改变结果。

使用预构建可执行文件
--------------------

如果部署环境不能直接安装 Python 包，请查看 `GitHub Releases 页面 <https://github.com/HansBug/pyfcstm/releases>`_ 是否有预构建可执行产物。普通开发和 CI 优先使用 PyPI；只有部署模型适合时才使用发布产物。

验证 Python 包
--------------

安装教程保留了一个纳入文档构建的检查脚本。它导入包元数据，证明 Python 能加载已安装包：

.. literalinclude:: ../../tutorials/installation/install_check.demo.py
   :language: python
   :linenos:

预期输出形态：

.. literalinclude:: ../../tutorials/installation/install_check.demo.py.txt
   :language: text
   :linenos:

更短的人工检查如下：

.. code-block:: bash

   python - <<'PY'
   import pyfcstm
   print(pyfcstm.__title__)
   print(pyfcstm.__version__)
   PY

验证命令行
----------

先检查版本和帮助：

.. code-block:: bash

   pyfcstm -v
   pyfcstm --help

文档构建也会执行这个 shell 检查：

.. literalinclude:: ../../tutorials/installation/cli_check.demo.sh
   :language: shell
   :linenos:

.. literalinclude:: ../../tutorials/installation/cli_check.demo.sh.txt
   :language: text
   :linenos:

验证一个最小 DSL 往返
---------------------

命令存在后，用一个小文件检查解析器和一个非渲染命令：

.. code-block:: bash

   cat > smoke.fcstm <<'FCSTM'
   state Root {
       state Idle;
       [*] -> Idle;
   }
   FCSTM
   pyfcstm inspect -i smoke.fcstm
   pyfcstm plantuml -i smoke.fcstm -o smoke.puml

这个检查不需要 Java、PlantUML、编译器或图形桌面。

可选渲染器设置
--------------

``pyfcstm plantuml`` 写 PlantUML 源码，不需要渲染器。只有 ``pyfcstm visualize`` 需要渲染后端。

本地渲染需要安装 Java 并提供 PlantUML jar：

.. code-block:: bash

   export PLANTUML_JAR=/path/to/plantuml.jar
   pyfcstm visualize --check --renderer local

远程渲染如果不使用公开默认服务，可以配置 PlantUML 服务：

.. code-block:: bash

   export PLANTUML_HOST=http://www.plantuml.com/plantuml
   pyfcstm visualize --check --renderer remote

远程渲染会把生成的 PlantUML 源码发送到配置服务。私有图表请使用本地渲染。

CI 安装模式
-----------

在 CI 中，把包安装和命令执行拆开，方便定位失败：

.. code-block:: bash

   python -m pip install -U pip
   python -m pip install pyfcstm
   python -m pyfcstm --help
   pyfcstm inspect -i machines/main.fcstm --format json -o build/main.inspect.json

CI 中渲染图表时，不要启动查看器：

.. code-block:: bash

   pyfcstm visualize -i machines/main.fcstm -t svg -o build/main.svg --no-open

排查清单
--------

.. list-table:: 安装排查
   :header-rows: 1

   * - 现象
     - 可能原因
     - 修复方式
   * - 找不到 ``pyfcstm``
     - 脚本目录不在 ``PATH``，或使用了错误解释器安装。
     - 用目标解释器运行 ``python -m pyfcstm --help``，再修复环境激活或 ``PATH``。
   * - ``python -m pyfcstm`` 导入失败
     - 该解释器没有安装包。
     - 运行 ``python -m pip show pyfcstm``，并用同一解释器重新安装。
   * - 命令行存在但 DSL 命令失败
     - 输入路径、语法或模型验证问题。
     - 运行 ``pyfcstm inspect -i <file>`` 并查看诊断输出。
   * - ``visualize --check --renderer local`` 失败
     - 缺少 Java、PlantUML jar、jar 路径无效，或本地后端失败。
     - 安装 Java，设置 ``PLANTUML_JAR``，或传 ``-p /path/to/plantuml.jar``。
   * - ``visualize --check --renderer remote`` 失败
     - 网络、代理或远程服务问题。
     - 把 ``PLANTUML_HOST`` 设为允许访问的服务，或使用本地渲染。
   * - 渲染后没有打开查看器
     - 无图形界面环境或没有系统打开器。
     - 脚本中使用 ``--no-open``；只有确实要求打开时才用 ``--strict-open``。

验证例子和失败信号
--------------------

安装后先跑这些短检查。它们故意不依赖渲染后端，所以适合刚安装好的 Python-only 环境。

.. list-table:: 安装验证矩阵
   :header-rows: 1

   * - 检查
     - 命令
     - 预期信号
     - 如果失败
   * - 包导入。
     - ``python -c "import pyfcstm; print(pyfcstm.__title__)"``
     - 打印包标题。
     - 这个解释器里没有安装包。
   * - 控制台脚本。
     - ``pyfcstm --help``
     - 列出公开命令。
     - 用 ``python -m pyfcstm --help`` 判断是否是 PATH/虚拟环境不一致。
   * - 版本。
     - ``pyfcstm -v``
     - 打印 ``Pyfcstm, version``。
     - 确认命令属于目标环境。
   * - Python-only DSL 冒烟检查。
     - ``pyfcstm inspect -i smoke.fcstm``
     - 最小模型打印 ``[OK] FCSTM Inspect Report``。
     - 先修 DSL 语法或安装，再检查渲染器。
   * - 源码图表冒烟检查。
     - ``pyfcstm plantuml -i smoke.fcstm -o smoke.puml``
     - ``smoke.puml`` 以 ``@startuml`` 开头。
     - 不需要 Java 或 PlantUML jar。
   * - 渲染器冒烟检查。
     - ``pyfcstm visualize --check --renderer auto``
     - 报告本地和/或远程渲染器可用性。
     - 只有需要渲染图片时才配置 Java/jar 或远程主机。

常见安装诊断例子
~~~~~~~~~~~~~~~~

.. list-table:: 诊断例子
   :header-rows: 1

   * - 现象
     - 探针
     - 含义
     - 修复
   * - 找不到 ``pyfcstm``。
     - ``python -m pyfcstm --help``
     - 包可能已安装，但控制台脚本不在 ``PATH``。
     - 激活虚拟环境，或用目标解释器重新安装。
   * - import 可用但命令版本不同。
     - ``python -m pyfcstm -v`` 和 ``pyfcstm -v``。
     - 解释器和控制台脚本指向不同环境。
     - 自动化中先用 ``python -m pyfcstm``，直到环境修好。
   * - ``plantuml`` 成功但 ``visualize`` 失败。
     - ``pyfcstm visualize --check --renderer local``。
     - Python 包已安装；缺的是渲染后端。
     - 安装 Java 和 PlantUML jar，或使用允许的远程渲染器。
   * - native 生成运行时构建失败。
     - 按生成 README 的命令构建生成目录。
     - pyfcstm 生成可能没问题；缺的是目标编译器/工具链。
     - 安装目标工具链，并保持 native 检查显式触发。


后续阅读
--------

* :doc:`/tutorials/quick_start/index_zh` 给出最短端到端路径。
* :doc:`/how_to/cli_workflows/index_zh` 展示常用命令行任务。
* :doc:`/reference/cli/index_zh` 列出命令和选项事实。
* 已发布文档位于 `hansbug.github.io/pyfcstm <https://hansbug.github.io/pyfcstm/main/index.html>`_。
