.. _sec-reference-cli-zh:

CLI 参考
========

本页列出公开 ``pyfcstm`` CLI 的命令事实。需要按任务操作时，请阅读 :doc:`/how_to/cli_workflows/index_zh`。

顶层命令
--------

.. code-block:: text

   pyfcstm [OPTIONS] COMMAND [ARGS]...

.. list-table:: 顶层选项
   :header-rows: 1

   * - 选项
     - 含义
   * - ``-v, --version``
     - 显示包版本信息。
   * - ``-h, --help``
     - 显示帮助并退出。

命令
----

.. list-table:: 命令
   :header-rows: 1

   * - 命令
     - 用途
   * - ``simulate``
     - 运行交互式或批处理状态机仿真器。
   * - ``inspect``
     - 输出 human、JSON 或 LLM-oriented 模型检查报告。
   * - ``generate``
     - 从自定义模板目录或打包内置模板生成源码。
   * - ``plantuml``
     - 输出 PlantUML 源文本。
   * - ``visualize``
     - 通过 PlantUML backend 渲染图表文件。

``simulate`` 选项
-----------------

.. code-block:: text

   pyfcstm simulate -i <input-code> [-e "current; cycle; current"] [--no-color]

.. list-table:: ``simulate`` 选项
   :header-rows: 1

   * - 选项
     - 是否必需
     - 含义
   * - ``-i, --input-code``
     - 是
     - FCSTM DSL 入口文件。
   * - ``-e, --execute``
     - 否
     - 分号分隔的 simulator 命令，执行后退出。
   * - ``--no-color``
     - 否
     - 禁用彩色输出。

``inspect`` 选项
----------------

.. code-block:: text

   pyfcstm inspect -i <input-code> [-o <output>] [--format human|json|llm-json|llm-md]

.. list-table:: ``inspect`` 选项
   :header-rows: 1

   * - 选项
     - 默认值
     - 含义
   * - ``-i, --input-code``
     - 必需
     - FCSTM DSL 入口文件。
   * - ``-o, --output``
     - 标准输出
     - 输出文件路径。
   * - ``--format``
     - ``human``
     - 输出格式：``human``、``json``、``llm-json`` 或 ``llm-md``。
   * - ``--color``
     - ``auto``
     - 只影响 human 输出的 ANSI color policy：``auto``、``always`` 或 ``never``。
   * - ``--enable-verify``
     - 关闭
     - 添加 inspect-eligible verify 诊断。
   * - ``--max-complexity-tier``
     - ``structural``
     - inspect 接受的最高 verify complexity tier。
   * - ``--max-call-count-scaling``
     - ``linear_in_transitions``
     - inspect 接受的最高 verify call-count scaling。
   * - ``--smt-timeout-ms``
     - 未设置
     - 可选 SMT solver 毫秒级超时；``0`` 表示不为 Z3 配置有限超时。

``generate`` 选项
-----------------

.. code-block:: text

   pyfcstm generate -i <input-code> --template <name> -o <output-dir> [--clear]
   pyfcstm generate -i <input-code> -t <template-dir> -o <output-dir> [--clear]

打包内置模板使用 ``--template``\ 。只有你维护自定义模板目录时，才使用
``-t`` / ``--template-dir``\ 。

.. list-table:: ``generate`` 选项
   :header-rows: 1

   * - 选项
     - 是否必需
     - 含义
   * - ``-i, --input-code``
     - 是
     - FCSTM DSL 入口文件。
   * - ``--template``
     - ``--template`` 或 ``-t`` 二选一
     - 打包内置模板：``python``、``c``、``c_poll``、``cpp`` 或 ``cpp_poll``。
   * - ``-t, --template-dir``
     - ``--template`` 或 ``-t`` 二选一
     - 自定义模板目录。只有在你明确维护该模板目录时才使用。
   * - ``-o, --output-dir``
     - 是
     - 生成输出目录。
   * - ``--clear, --clear-directory``
     - 否
     - 渲染前清空输出目录。

``plantuml`` 选项
-----------------

.. code-block:: text

   pyfcstm plantuml -i <input-code> [-o <output>] [-l minimal|normal|full] [-c key=value]

.. list-table:: ``plantuml`` 选项
   :header-rows: 1

   * - 选项
     - 默认值
     - 含义
   * - ``-i, --input-code``
     - 必需
     - FCSTM DSL 入口文件。
   * - ``-o, --output``
     - 标准输出
     - PlantUML 源码输出路径。
   * - ``-l, --level``
     - ``normal``
     - 详细级别预设：``minimal``、``normal`` 或 ``full``。
   * - ``-c, --config``
     - 无
     - ``key=value`` 形式的 PlantUML 选项覆盖项，可重复。

``visualize`` 选项
------------------

.. code-block:: text

   pyfcstm visualize -i <input-code> [-o <output>] [-t png|svg|pdf] [--renderer auto|local|remote]

.. list-table:: ``visualize`` 选项
   :header-rows: 1

   * - 选项
     - 默认值
     - 含义
   * - ``-i, --input-code``
     - 除 ``--check`` 外必需
     - FCSTM DSL 入口文件。
   * - ``-o, --output``
     - 缓存路径
     - 渲染后的输出文件。
   * - ``-l, --level``
     - ``normal``
     - 与 ``plantuml`` 共用的详细级别预设。
   * - ``-c, --config``
     - 无
     - ``key=value`` 形式的 PlantUML 选项覆盖项，可重复。
   * - ``-t, --type``
     - ``png``
     - 渲染图类型：``png``、``svg`` 或 ``pdf``。
   * - ``--renderer``
     - ``auto``
     - 渲染 backend：``auto``、``local`` 或 ``remote``。
   * - ``-j, --java``
     - ``PATH`` 中的 ``java``
     - 本地渲染使用的 Java 可执行文件。
   * - ``-p, --plantuml, --plantuml-jar``
     - ``PLANTUML_JAR`` 或未设置
     - 本地渲染使用的 PlantUML jar 路径。
   * - ``-r, --remote-host``
     - PlantUML 公共服务默认值
     - 远端 PlantUML 服务 base URL。
   * - ``--check``
     - 关闭
     - 检查 renderer 可用性后退出，不渲染图表。
   * - ``--open / --no-open``
     - 命令默认值
     - 是否用系统 viewer 打开渲染文件。
   * - ``--strict-open``
     - 关闭
     - 将 viewer 启动失败视为错误。
