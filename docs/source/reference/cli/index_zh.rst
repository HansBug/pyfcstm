.. _sec-reference-cli-zh:

命令行参考
==========

本页是公开 ``pyfcstm`` 命令的精确参考，记录选项名称、可接受取值、输出通道、副作用和失败边界。
如果你需要按任务操作，请看 :doc:`/how_to/cli_workflows/index_zh`；如果你需要 ``plantuml`` 和
``visualize`` 共用的图表选项，请看 :doc:`/reference/visualization_options/index_zh`。

下面的同步标记是给 ``tools/check_cli_reference_docs.py`` 使用的注释，用于让本页和 Click 命令树、
人工确认的边界事实保持一致。

.. cli-ref-command: name=generate
.. cli-ref-option: command=generate option=-i
.. cli-ref-option: command=generate option=--input-code
.. cli-ref-option: command=generate option=-t
.. cli-ref-option: command=generate option=--template-dir
.. cli-ref-option: command=generate option=--template choices=c,c_poll,cpp,cpp_poll,python
.. cli-ref-option: command=generate option=-o
.. cli-ref-option: command=generate option=--output-dir
.. cli-ref-option: command=generate option=--clear
.. cli-ref-option: command=generate option=--clear-directory
.. cli-ref-option: command=generate option=--help
.. cli-ref-command: name=inspect
.. cli-ref-option: command=inspect option=-i
.. cli-ref-option: command=inspect option=--input-code
.. cli-ref-option: command=inspect option=-o
.. cli-ref-option: command=inspect option=--output
.. cli-ref-option: command=inspect option=--format choices=human,json,llm-json,llm-md default=human
.. cli-ref-option: command=inspect option=--color choices=auto,always,never default=auto
.. cli-ref-option: command=inspect option=--enable-verify
.. cli-ref-option: command=inspect option=--max-complexity-tier choices=structural,smt_linear,smt_nonlinear_decidable,smt_undecidable_heuristic,bmc_search default=structural
.. cli-ref-option: command=inspect option=--max-call-count-scaling choices=none,one,linear_in_states,linear_in_transitions,linear_in_vars,linear_in_leaves,quadratic_in_outgoing_per_state,quadratic_in_states,vars_times_transitions,k_unrollings,k_unrollings_times_branching default=linear_in_transitions
.. cli-ref-option: command=inspect option=--smt-timeout-ms
.. cli-ref-option: command=inspect option=--help
.. cli-ref-command: name=plantuml
.. cli-ref-option: command=plantuml option=-i
.. cli-ref-option: command=plantuml option=--input-code
.. cli-ref-option: command=plantuml option=-o
.. cli-ref-option: command=plantuml option=--output
.. cli-ref-option: command=plantuml option=-l choices=minimal,normal,full default=normal
.. cli-ref-option: command=plantuml option=--level choices=minimal,normal,full default=normal
.. cli-ref-option: command=plantuml option=-c
.. cli-ref-option: command=plantuml option=--config
.. cli-ref-option: command=plantuml option=--help
.. cli-ref-command: name=simulate
.. cli-ref-option: command=simulate option=-i
.. cli-ref-option: command=simulate option=--input-code
.. cli-ref-option: command=simulate option=-e
.. cli-ref-option: command=simulate option=--execute
.. cli-ref-option: command=simulate option=--no-color
.. cli-ref-option: command=simulate option=--help
.. cli-ref-command: name=visualize
.. cli-ref-option: command=visualize option=-i
.. cli-ref-option: command=visualize option=--input-code
.. cli-ref-option: command=visualize option=-o
.. cli-ref-option: command=visualize option=--output
.. cli-ref-option: command=visualize option=-l choices=minimal,normal,full default=normal
.. cli-ref-option: command=visualize option=--level choices=minimal,normal,full default=normal
.. cli-ref-option: command=visualize option=-c
.. cli-ref-option: command=visualize option=--config
.. cli-ref-option: command=visualize option=-t choices=png,svg,pdf default=png
.. cli-ref-option: command=visualize option=--type choices=png,svg,pdf default=png
.. cli-ref-option: command=visualize option=--renderer choices=local,remote,auto default=auto
.. cli-ref-option: command=visualize option=-j
.. cli-ref-option: command=visualize option=--java
.. cli-ref-option: command=visualize option=-p
.. cli-ref-option: command=visualize option=--plantuml
.. cli-ref-option: command=visualize option=--plantuml-jar
.. cli-ref-option: command=visualize option=-r
.. cli-ref-option: command=visualize option=--remote-host
.. cli-ref-option: command=visualize option=--check
.. cli-ref-option: command=visualize option=--open
.. cli-ref-option: command=visualize option=--no-open
.. cli-ref-option: command=visualize option=--strict-open
.. cli-ref-option: command=visualize option=--help
.. cli-ref-option: command=top-level option=--version
.. cli-ref-option: command=top-level option=--help
.. cli-ref-boundary: command=generate stdout stderr exit-status side-effects success-signal failure-taxonomy clear
.. cli-ref-boundary: command=inspect stdout stderr exit-status side-effects success-signal failure-taxonomy output-formats verify-policy
.. cli-ref-boundary: command=plantuml stdout stderr exit-status side-effects success-signal failure-taxonomy source-only
.. cli-ref-boundary: command=simulate stdout stderr exit-status side-effects success-signal failure-taxonomy interactive batch
.. cli-ref-boundary: command=visualize stdout stderr exit-status side-effects success-signal failure-taxonomy cache suffix open headless check-mode

顶层命令
--------

.. code-block:: text

   pyfcstm [OPTIONS] COMMAND [ARGS]...

.. list-table:: 顶层选项
   :header-rows: 1

   * - 选项
     - 含义
     - 说明
   * - ``-v, --version``
     - 显示 pyfcstm 版本信息。
     - 只读，打印版本后退出。
   * - ``-h, --help``
     - 显示帮助并退出。
     - 顶层命令和每个子命令都支持。

.. list-table:: 子命令
   :header-rows: 1

   * - 命令
     - 主要输入
     - 主要输出
     - 适用场景
   * - ``simulate``
     - FCSTM 领域特定语言（DSL）文件
     - 交互式控制台记录或批处理记录
     - 不生成目标代码，只执行模型语义。
   * - ``inspect``
     - FCSTM DSL 文件
     - 人类文本、JSON、面向大语言模型（LLM）的 JSON 或 Markdown
     - 查看解析器和模型事实、诊断，以及可选的有界验证诊断。
   * - ``generate``
     - FCSTM DSL 文件加内置模板或自定义模板
     - 输出目录里的渲染文件
     - 生成目标语言运行时代码。
   * - ``plantuml``
     - FCSTM DSL 文件
     - PlantUML 源码文本
     - 需要稳定、可审阅、可版本管理的图表源码。
   * - ``visualize``
     - FCSTM DSL 文件或渲染器检查请求
     - ``png``、``svg`` 或 ``pdf`` 图表
     - 让 pyfcstm 直接调用 PlantUML 渲染器。

通用命令契约
------------

命令行接口有意区分“只产出源码/事实”的命令和“可能依赖外部工具”的命令：

* ``simulate``、``inspect``、``generate`` 和 ``plantuml`` 读取 DSL 并使用 Python 侧 pyfcstm 功能；它们不需要
  Java、PlantUML jar 或网络渲染器。
* ``visualize`` 先构造 PlantUML 源码，再调用 ``plantumlcli``；本地渲染可能需要 Java 和 PlantUML jar，远程渲染
  需要可访问的 PlantUML 服务。
* 成功命令退出码为 ``0``。Click 参数错误、缺失文件、解析错误、模型验证错误、渲染失败和策略拒绝会产生非零退出码。
* 面向用户的进度和成功消息写入标准输出；Click 格式化的错误写入标准错误。
* 写文件命令只创建或替换请求的输出路径或目录。这里唯一会有意删除已有输出目录内容的选项是 ``generate --clear``。

``simulate``
------------

.. code-block:: text

   pyfcstm simulate -i <input-code> [-e "current; cycle; current"] [--no-color]

``simulate`` 构建模型并运行 Python 模拟器。不带 ``-e`` 时进入交互式控制台；带 ``-e`` 时执行分号分隔的命令脚本后退出。

.. list-table:: ``simulate`` 选项
   :header-rows: 1

   * - 选项
     - 必填
     - 取值
     - 含义
   * - ``-i, --input-code``
     - 是
     - 路径
     - FCSTM DSL 入口文件。
   * - ``-e, --execute``
     - 否
     - 字符串
     - 批处理模拟器命令，例如 ``"current; cycle Start; current"``。
   * - ``--no-color``
     - 否
     - 标志
     - 禁用交互式或人类输出中的颜色。
   * - ``-h, --help``
     - 否
     - 标志
     - 显示命令帮助。

输出和失败事实：

* 交互模式向标准输出打印提示符和运行时信息，并等待用户命令。
* 批处理模式向标准输出打印命令结果，脚本结束后退出。
* 除非使用 shell 重定向，否则该命令没有文件副作用。
* 典型失败包括输入不可读、解析错误、模型验证错误、未知模拟器命令、无效事件名、无效热启动状态或变量赋值。

典型例子：

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm
   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"
   pyfcstm simulate -i machine.fcstm -e "init System.Active counter=10; cycle 5"

``inspect``
-----------

.. code-block:: text

   pyfcstm inspect -i <input-code> [-o <output>] [--format human|json|llm-json|llm-md]

``inspect`` 报告解析器和模型导入器从 DSL 文件中知道的事实。它是诊断和事实导向工具：不执行模拟器轨迹，也不证明生成代码。

.. list-table:: ``inspect`` 选项
   :header-rows: 1

   * - 选项
     - 默认
     - 取值
     - 含义
   * - ``-i, --input-code``
     - 必填
     - 路径
     - FCSTM DSL 入口文件。
   * - ``-o, --output``
     - 标准输出
     - 路径
     - 输出文件。后缀不匹配可能产生警告，但不会自动改变格式。
   * - ``--format``
     - ``human``
     - ``human``、``json``、``llm-json``、``llm-md``
     - 输出格式。完整机器可读报告请使用 ``json``。
   * - ``--color``
     - ``auto``
     - ``auto``、``always``、``never``
     - 仅对 ``human`` 输出生效的 ANSI 颜色策略。
   * - ``--enable-verify``
     - 关闭
     - 标志
     - 加入 inspect 允许范围内的验证诊断。
   * - ``--max-complexity-tier``
     - ``structural``
     - ``structural``、``smt_linear``、``smt_nonlinear_decidable``、``smt_undecidable_heuristic``、``bmc_search``
     - inspect 接受的最高验证复杂度。``bmc_search`` 只用于报告策略错误。
   * - ``--max-call-count-scaling``
     - ``linear_in_transitions``
     - ``none``、``one``、``linear_in_states``、``linear_in_transitions``、``linear_in_vars``、``linear_in_leaves``、``quadratic_in_outgoing_per_state``、``quadratic_in_states``、``vars_times_transitions``、``k_unrollings``、``k_unrollings_times_branching``
     - inspect 允许的最高调用次数规模。``k_unrollings`` 标签只用于报告策略错误。
   * - ``--smt-timeout-ms``
     - 未设置
     - ``>= 0`` 的整数
     - 可选 Z3 超时时间，单位毫秒。``0`` 表示不设置有限超时。
   * - ``-h, --help``
     - 不适用
     - 标志
     - 显示命令帮助。

输出和失败事实：

* ``human`` 面向终端和人类；``json`` 是完整结构化报告；``llm-json`` 和 ``llm-md`` 是稳定、紧凑、面向修复的视图。
* 机器格式永远不包含 ANSI 颜色。人类输出写入文件时也不带颜色，即使请求 ``--color always``。
* 成功写文件时只写请求的报告文件；省略 ``-o`` 时写标准输出。
* 验证策略选项会在读取输入文件之前校验，让被禁止的高成本模式快速失败，而不是偷偷执行昂贵检查。

典型例子：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm
   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json
   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md
   pyfcstm inspect -i machine.fcstm --enable-verify --smt-timeout-ms 2000

``generate``
------------

.. code-block:: text

   pyfcstm generate -i <input-code> --template <name> -o <output-dir> [--clear]
   pyfcstm generate -i <input-code> -t <template-dir> -o <output-dir> [--clear]

``generate`` 从语义模型渲染目标产物。它接受打包内置模板名，或显式自定义模板目录。不要同时传 ``--template`` 和
``--template-dir``。

.. list-table:: ``generate`` 选项
   :header-rows: 1

   * - 选项
     - 必填
     - 取值
     - 含义
   * - ``-i, --input-code``
     - 是
     - 路径
     - FCSTM DSL 入口文件。
   * - ``--template``
     - 模板名或模板目录二选一
     - ``python``、``c``、``c_poll``、``cpp``、``cpp_poll``
     - 打包内置模板。
   * - ``-t, --template-dir``
     - 模板名或模板目录二选一
     - 路径
     - 调用方维护的自定义模板目录。
   * - ``-o, --output-dir``
     - 是
     - 路径
     - 渲染文件的目标目录。
   * - ``--clear, --clear-directory``
     - 否
     - 标志
     - 渲染前移除已有输出目录内容。
   * - ``-h, --help``
     - 否
     - 标志
     - 显示命令帮助。

输出和失败事实：

* 标准输出通常只包含 Click 或渲染器的进度/错误；生成产物写入 ``--output-dir``。
* 内置模板先从打包模板资产中抽取，再走和自定义模板相同的渲染器路径。
* ``--clear`` 会对输出目录造成破坏性清理。只应该用于可以安全替换的生成目录。
* 典型失败包括输入缺失、解析或模型错误、模板缺失或无效、Jinja 渲染错误、输出权限错误、模板参数互相冲突。

典型例子：

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated/python --clear
   pyfcstm generate -i machine.fcstm --template c -o generated/c
   pyfcstm generate -i machine.fcstm -t ./my_template -o generated/custom --clear

``plantuml``
------------

.. code-block:: text

   pyfcstm plantuml -i <input-code> [-o <output>] [-l minimal|normal|full] [-c key=value]

``plantuml`` 只输出 PlantUML 源码文本。它不渲染图片、不调用 Java，也不访问远程 PlantUML 服务。

.. list-table:: ``plantuml`` 选项
   :header-rows: 1

   * - 选项
     - 默认
     - 取值
     - 含义
   * - ``-i, --input-code``
     - 必填
     - 路径
     - FCSTM DSL 入口文件。
   * - ``-o, --output``
     - 标准输出
     - 路径
     - PlantUML 源码输出文件。
   * - ``-l, --level``
     - ``normal``
     - ``minimal``、``normal``、``full``
     - 与 ``visualize`` 共用的细节预设。
   * - ``-c, --config``
     - 无
     - ``key=value``；可重复
     - 细粒度 PlantUML 选项覆盖。
   * - ``-h, --help``
     - 不适用
     - 标志
     - 显示命令帮助。

输出和失败事实：

* 带 ``-o`` 时把 PlantUML 源码写入请求文件；不带 ``-o`` 时打印到标准输出。
* ``-c`` 接受 :doc:`/reference/visualization_options/index_zh` 中的类型化取值语法。
* 典型失败包括输入不可读、解析或模型错误、未知 PlantUML 选项键、取值解析错误，或无效 ``PlantUMLOptions`` 值。

典型例子：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml
   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml
   pyfcstm plantuml -i machine.fcstm -c show_events=true -c max_depth=2

``visualize``
-------------

.. code-block:: text

   pyfcstm visualize -i <input-code> [-o <output>] [-t png|svg|pdf] [--renderer auto|local|remote]
   pyfcstm visualize --check [--renderer auto|local|remote]

``visualize`` 先构造 PlantUML 源码，再请求 ``plantumlcli`` 渲染最终文件。它适合本地预览，或适合把渲染器也纳入流程的文档产物。

.. list-table:: ``visualize`` 选项
   :header-rows: 1

   * - 选项
     - 默认
     - 取值
     - 含义
   * - ``-i, --input-code``
     - 除 ``--check`` 外必填
     - 路径
     - FCSTM DSL 入口文件。
   * - ``-o, --output``
     - 缓存路径
     - 路径
     - 渲染输出文件。省略时写入 pyfcstm 的可视化缓存目录。
   * - ``-l, --level``
     - ``normal``
     - ``minimal``、``normal``、``full``
     - 与 ``plantuml`` 共用的细节预设。
   * - ``-c, --config``
     - 无
     - ``key=value``；可重复
     - 细粒度 PlantUML 选项覆盖。
   * - ``-t, --type``
     - ``png``
     - ``png``、``svg``、``pdf``
     - 渲染图表类型。
   * - ``--renderer``
     - ``auto``
     - ``local``、``remote``、``auto``
     - 后端选择。``auto`` 先试本地，再试远程。
   * - ``-j, --java``
     - ``PATH`` 中的 ``java``
     - 路径
     - 本地渲染使用的 Java 可执行文件。
   * - ``-p, --plantuml, --plantuml-jar``
     - ``PLANTUML_JAR`` 或未设置
     - 路径
     - 本地渲染使用的 PlantUML jar。
   * - ``-r, --remote-host``
     - ``PLANTUML_HOST`` 或公开 PlantUML 服务
     - URL
     - 远程 PlantUML 服务基础地址。
   * - ``--check``
     - 关闭
     - 标志
     - 只检查渲染器可用性，不读取 DSL 文件。
   * - ``--open / --no-open``
     - ``--open``
     - 标志对
     - 是否用系统默认查看器打开渲染文件。
   * - ``--strict-open``
     - 关闭
     - 标志
     - 把查看器启动失败视为命令错误。
   * - ``-h, --help``
     - 不适用
     - 标志
     - 显示命令帮助。

输出和失败事实：

* 成功渲染会打印实际使用的渲染器和输出路径。
* 省略 ``-o`` 时，输出写入平台缓存目录：Linux 上是 ``$XDG_CACHE_HOME/pyfcstm/visualize`` 或
  ``~/.cache/pyfcstm/visualize``，macOS 上是 ``~/Library/Caches/pyfcstm/visualize``，Windows 上是
  ``%LOCALAPPDATA%\\pyfcstm\\visualize``。
* 如果 ``-o`` 带后缀，后缀必须和 ``--type`` 一致；无后缀输出路径会自动补上所选后缀。
* ``--check`` 在请求后端可用时返回 ``0``。对于 ``--renderer auto``，本地或远程任一可用即可。
* 在 CI、``PYFCSTM_NO_GUI`` 为真，或 Linux 上缺少显示环境变量时，``--open`` 会自动跳过。带 ``--strict-open`` 时，
  这种跳过会变成命令失败。
* 远程渲染会把生成的 PlantUML 文本发送给配置的 PlantUML 服务。不能离开本机的图表应使用 ``--renderer local``。

典型例子：

.. code-block:: bash

   pyfcstm visualize --check --renderer auto
   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open
   pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open
   pyfcstm visualize -i machine.fcstm --renderer remote -r http://www.plantuml.com/plantuml --no-open

命令证据卡片
----------------------

下面的表故意写得比普通帮助更具体。选项表定义精确形式；这些证据卡片说明正常运行和失败运行分别会产生什么信号。

顶层命令证据
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 成功形式
   :header-rows: 1

   * - 场景
     - 命令
     - 预期信号
     - 副作用或原因
   * - Confirm the console script
     - ``pyfcstm --help``
     - Help starts with Usage and lists all public commands.
     - None
   * - Confirm module fallback
     - ``python -m pyfcstm --help``
     - Help starts with Usage: python -m pyfcstm.
     - None
   * - Record version
     - ``pyfcstm -v``
     - Output includes Pyfcstm, version and maintainer contact.
     - None

.. list-table:: 失败和边界形式
   :header-rows: 1

   * - 情况
     - 示例
     - 预期信号
     - 首要修复
   * - Console script missing
     - ``pyfcstm --help``
     - Shell command-not-found before pyfcstm starts.
     - Run python -m pyfcstm --help with the intended interpreter.
   * - Unknown subcommand
     - ``pyfcstm render``
     - Click reports no such command.
     - Use pyfcstm --help and choose a public command.
   * - Option on wrong command
     - ``pyfcstm --format json inspect -i machine.fcstm``
     - Click reports unknown top-level option.
     - Move command options after the subcommand.

证据规则：
  把这些例子当成行为探针。如果实现输出变化，更新这里的短信号，并保持选项 marker checker 为绿。

``simulate`` 证据
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 成功形式
   :header-rows: 1

   * - 场景
     - 命令
     - 预期信号
     - 副作用或原因
   * - Deterministic batch trace
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``
     - Transcript includes Cycle: 0, then Cycle: 1 and the active state.
     - No file side effect.
   * - Explicit event cycle
     - ``pyfcstm simulate -i machine.fcstm -e "cycle Start; current"``
     - Transcript records the event-bearing cycle and resulting active path.
     - No file side effect.
   * - Hot start
     - ``pyfcstm simulate -i machine.fcstm -e "init System.Active counter=10; cycle; current"``
     - Run starts from the requested active path and variable values.
     - No file side effect.

.. list-table:: 失败和边界形式
   :header-rows: 1

   * - 情况
     - 示例
     - 预期信号
     - 首要修复
   * - Missing input
     - ``pyfcstm simulate``
     - Click reports Missing option '-i' / '--input-code'.
     - Pass the DSL file with -i.
   * - Unknown batch command
     - ``pyfcstm simulate -i machine.fcstm -e "rewind"``
     - Simulator command layer reports the unknown command.
     - Use the simulation command reference.
   * - Invalid hot-start values
     - ``pyfcstm simulate -i machine.fcstm -e "init System.Active counter=oops"``
     - Hot-start validation rejects invalid assignments.
     - Provide every required variable with a typed value.

证据规则：
  把这些例子当成行为探针。如果实现输出变化，更新这里的短信号，并保持选项 marker checker 为绿。

``inspect`` 证据
~~~~~~~~~~~~~~~~~~~~

.. list-table:: 成功形式
   :header-rows: 1

   * - 场景
     - 命令
     - 预期信号
     - 副作用或原因
   * - Human report
     - ``pyfcstm inspect -i traffic_light.fcstm``
     - Output begins with [OK] FCSTM Inspect Report and count summary.
     - No file side effect.
   * - JSON report
     - ``pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json``
     - JSON includes metrics, diagnostics, states, transitions, and graph sections.
     - Writes the requested JSON file.
   * - LLM Markdown report
     - ``pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md``
     - File contains compact repair-oriented facts and diagnostics.
     - Writes the requested Markdown file.
   * - Bounded verify report
     - ``pyfcstm inspect -i machine.fcstm --enable-verify --smt-timeout-ms 2000``
     - Report includes inspect-eligible verification diagnostics.
     - No file side effect unless -o is used.

.. list-table:: 失败和边界形式
   :header-rows: 1

   * - 情况
     - 示例
     - 预期信号
     - 首要修复
   * - Missing input
     - ``pyfcstm inspect``
     - Click reports Missing option '-i' / '--input-code'.
     - Pass the DSL file explicitly.
   * - Invalid format
     - ``pyfcstm inspect -i machine.fcstm --format xml``
     - Click reports xml is not one of human/json/llm-json/llm-md.
     - Choose a documented format.
   * - Forbidden verify policy
     - ``pyfcstm inspect -i machine.fcstm --enable-verify --max-complexity-tier bmc_search``
     - Inspect policy rejects the expensive tier before parsing the model.
     - Keep routine checks within allowed tiers.
   * - Suffix mismatch warning
     - ``pyfcstm inspect -i machine.fcstm --format json -o machine.txt``
     - Format remains json; suffix warning is informational.
     - Use a matching suffix for clarity.

证据规则：
  把这些例子当成行为探针。如果实现输出变化，更新这里的短信号，并保持选项 marker checker 为绿。

``generate`` 证据
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 成功形式
   :header-rows: 1

   * - 场景
     - 命令
     - 预期信号
     - 副作用或原因
   * - Python built-in template
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``
     - Directory contains machine.py, README.md, README_zh.md.
     - Clears and rewrites target directory.
   * - C built-in template
     - ``pyfcstm generate -i machine.fcstm --template c -o generated/c``
     - Directory contains C artifacts described by generated README.
     - Writes files; does not compile.
   * - Custom template
     - ``pyfcstm generate -i machine.fcstm -t ./templates/my_target -o generated/my_target``
     - Files follow config.yaml and .j2 output paths.
     - Writes custom output tree.

.. list-table:: 失败和边界形式
   :header-rows: 1

   * - 情况
     - 示例
     - 预期信号
     - 首要修复
   * - Both template inputs
     - ``pyfcstm generate -i machine.fcstm --template python -t ./templates/python -o out``
     - Command rejects conflicting template arguments.
     - Use exactly one template source.
   * - Unknown built-in template
     - ``pyfcstm generate -i machine.fcstm --template ruby -o out``
     - Template lookup reports unavailable name.
     - Use a documented built-in name.
   * - Dangerous clear
     - ``pyfcstm generate -i machine.fcstm --template python -o . --clear``
     - Request is destructive even if accepted.
     - Use a dedicated generated directory.
   * - Broken custom template
     - ``pyfcstm generate -i machine.fcstm -t ./broken_template -o out``
     - Renderer reports config, import, Jinja, or filesystem error.
     - Debug custom template before blaming DSL.

证据规则：
  把这些例子当成行为探针。如果实现输出变化，更新这里的短信号，并保持选项 marker checker 为绿。

``plantuml`` 证据
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 成功形式
   :header-rows: 1

   * - 场景
     - 命令
     - 预期信号
     - 副作用或原因
   * - Write source file
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``
     - File begins with @startuml and includes the root state block.
     - Writes requested .puml file.
   * - Print source
     - ``pyfcstm plantuml -i traffic_light.fcstm``
     - stdout begins with @startuml.
     - No file side effect unless redirected.
   * - Dense review source
     - ``pyfcstm plantuml -i machine.fcstm -l full -c max_action_lines=3 -o machine.full.puml``
     - Source includes allowed lifecycle/action details.
     - Writes source only.

.. list-table:: 失败和边界形式
   :header-rows: 1

   * - 情况
     - 示例
     - 预期信号
     - 首要修复
   * - Unknown config key
     - ``pyfcstm plantuml -i machine.fcstm -c typo_option=true``
     - PlantUMLOptions construction rejects the key.
     - Use the closed option list.
   * - Invalid typed value
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=abc``
     - Value parser reports the offending key.
     - Use an integer or omit the option.
   * - Expecting image output
     - ``pyfcstm plantuml -i machine.fcstm -o machine.svg``
     - Command writes source text to that path, not SVG image data.
     - Use visualize -t svg for rendered images.

证据规则：
  把这些例子当成行为探针。如果实现输出变化，更新这里的短信号，并保持选项 marker checker 为绿。

``visualize`` 证据
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 成功形式
   :header-rows: 1

   * - 场景
     - 命令
     - 预期信号
     - 副作用或原因
   * - Check backend
     - ``pyfcstm visualize --check --renderer auto``
     - Reports local and/or remote renderer availability.
     - Does not parse DSL or write a diagram.
   * - Render SVG in CI
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``
     - Reports renderer and output path on success.
     - Writes SVG file.
   * - Force local renderer
     - ``pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open``
     - Uses Java plus supplied PlantUML jar.
     - Writes requested or cache output.
   * - Force remote renderer
     - ``pyfcstm visualize -i machine.fcstm --renderer remote -r http://www.plantuml.com/plantuml --no-open``
     - Sends generated PlantUML source to configured service.
     - Writes rendered artifact.

.. list-table:: 失败和边界形式
   :header-rows: 1

   * - 情况
     - 示例
     - 预期信号
     - 首要修复
   * - Suffix/type conflict
     - ``pyfcstm visualize -i machine.fcstm -o diagram.svg -t png --no-open``
     - Fails before rendering because .svg does not match png.
     - Align suffix and --type.
   * - Missing local jar
     - ``pyfcstm visualize --check --renderer local``
     - Local check names missing PlantUML jar or Java/path failure.
     - Set PLANTUML_JAR or pass -p.
   * - Headless open
     - ``pyfcstm visualize -i machine.fcstm --open``
     - Normal open is skipped in CI/headless; strict-open makes it fatal.
     - Use --no-open for scripts.
   * - Remote unreachable
     - ``pyfcstm visualize --check --renderer remote -r http://example.invalid/plantuml``
     - Remote check reports backend/network failure.
     - Fix network/host or use local.

证据规则：
  把这些例子当成行为探针。如果实现输出变化，更新这里的短信号，并保持选项 marker checker 为绿。


中文说明
~~~~~~~~

上表中的命令、文件名、选项、错误关键字保持原文，是为了可复制和可搜索。普通说明应使用中文术语；如果后续继续扩写本页，应避免把 command、option、output、failure 这类词反复写进中文 prose。



逐选项决策卡片
--------------

前面的命令例子展示整条命令的行为；下面的卡片进一步落到选项层级，方便审查者判断一条命令是否用对了开关。每行都包含合法写法、边界或反例，以及运行后应该检查的证据。

.. list-table:: 顶层选项决策
   :header-rows: 1

   * - 选项
     - 合法写法
     - 边界或反例
     - 应检查的证据
   * - ``-h, --help``
     - ``pyfcstm --help``；``python -m pyfcstm --help``；``pyfcstm generate --help``。
     - ``pyfcstm --help generate`` 不是本 CLI 使用的 Click 写法；子命令帮助应把 ``--help`` 放在子命令后面。
     - 帮助输出列出 ``generate``、``inspect``、``plantuml``、``visualize`` 和 ``simulate``。
   * - ``-v, --version``
     - ``pyfcstm -v``；``pyfcstm --version``；``python -m pyfcstm -v``。
     - ``pyfcstm generate -v`` 不是子命令选项。
     - 标准输出包含项目版本和维护者信息，然后在任何子命令运行前退出。

.. list-table:: ``simulate`` 选项决策
   :header-rows: 1

   * - 选项
     - 合法写法
     - 边界或反例
     - 应检查的证据
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``；``--input-code machines/control.fcstm``；带空格路径需要 shell 引号。
     - 省略它会在模拟器启动前被 Click 拒绝。
     - 最初几行转录会显示执行的命令和周期状态；不会创建输出文件。
   * - ``-e, --execute``
     - ``-e "current"``；``-e "cycle; current"``；``-e "init Root.Leaf timer=2; cycle Start; current"``。
     - shell 引号错误会在 pyfcstm 收到脚本前就把分号脚本拆开。
     - 批处理模式执行完脚本后退出，并打印适合日志保存的确定性转录。
   * - ``--no-color``
     - 可用于交互模式或批处理模式。
     - 它不改变模拟语义或活动状态选择。
     - 终端转录中不应出现 ANSI 转义序列。

.. list-table:: ``inspect`` 选项决策
   :header-rows: 1

   * - 选项
     - 合法写法
     - 边界或反例
     - 应检查的证据
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``；``--input-code imported/root.fcstm``；编辑器任务正在使用的路径。
     - 缺失或不可读路径会被报告为受控 CLI 错误。
     - 报告会先给出根状态，或者给出读文件/解析失败；在此之前不要信任输出文件。
   * - ``-o, --output``
     - ``-o report.json``；``-o reports/model.inspect.md``；不传 ``-o`` 表示标准输出。
     - 父目录不存在会导致写文件错误；后缀不匹配可能给出警告，但不会改变所选格式。
     - 目标文件只包含所选 inspect 文本，警告走标准错误。
   * - ``--format``
     - ``human`` 面向终端阅读；``json`` 面向完整机器数据；``llm-json`` 和 ``llm-md`` 面向修复提示词。
     - ``xml`` 或 ``yaml`` 这类值会被 Click 拒绝。
     - 机器格式不含 ANSI 颜色，并足够稳定，适合脚本解析。
   * - ``--color``
     - ``auto`` 用于终端；``always`` 强制 human 标准输出着色；``never`` 用于日志。
     - 对 ``json``、``llm-json``、``llm-md`` 以及任何 ``-o`` 文件都会忽略颜色。
     - 只应在人类可读标准输出模式中检查 ANSI 序列。
   * - ``--enable-verify``
     - 当确实需要结构性或 SMT 本地 verify 事实时使用。
     - 默认关闭；开启它也不允许使用被策略禁止的层级。
     - 诊断部分可能包含 verify 派生条目，但 inspect 仍受策略边界限制。
   * - ``--max-complexity-tier``
     - ``structural``；``smt_linear``；调用者接受成本时可用 ``smt_nonlinear_decidable``。
     - ``bmc_search`` 只由 Click 接收，以便 inspect 给出策略拒绝消息。
     - 策略失败可在不依赖模型解析的情况下诊断。
   * - ``--max-call-count-scaling``
     - ``none``；``one``；``linear_in_transitions``；其他受允许的有限 taxonomy 值。
     - ``k_unrollings`` 和 ``k_unrollings_times_branching`` 会在自动 inspect 运行中被策略拒绝。
     - 错误会点名被禁止的 scaling 标签。
   * - ``--smt-timeout-ms``
     - ``--smt-timeout-ms 2000``；``--smt-timeout-ms 0``；省略则使用默认求解器行为。
     - 负数会被 Click 整数范围校验拒绝。
     - SMT 本地检查会收到该超时；仅结构性运行不会因此变成穷尽验证。

.. list-table:: ``generate`` 选项决策
   :header-rows: 1

   * - 选项
     - 合法写法
     - 边界或反例
     - 应检查的证据
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``；``--input-code machines/root.fcstm``；模型加载器可解析导入的文件。
     - 解析或模型错误会在模板输出可信之前停止生成。
     - 只有命令成功退出后，输出目录才可视为当前生成结果。
   * - ``--template``
     - ``--template python``；``--template c``；``--template cpp_poll``。
     - 未知名称会被 Click 拒绝，因为候选来自打包模板元数据。
     - 内置模板会先解压到临时目录，再交给渲染器。
   * - ``-t, --template-dir``
     - ``-t ./my_template``；``--template-dir /abs/template``；测试控制下的临时模板。
     - 它与 ``--template`` 互斥。
     - 渲染会读取该目录的 ``config.yaml``、``.j2`` 文件、静态文件和忽略规则。
   * - ``-o, --output-dir``
     - ``-o generated/python``；``--output-dir build/fcstm``；新的临时目录。
     - 权限错误或父目录问题会表现为文件系统/模板错误。
     - 目录只在渲染成功完成后才包含可信的生成产物。
   * - ``--clear, --clear-directory``
     - 只用于专门的生成目录，例如 ``generated/python``。
     - 不要指向源码树、仓库根目录或手工维护目录。
     - 旧输出会在渲染前被移除；审查者应先确认目标路径再接受该命令。

.. list-table:: ``plantuml`` 选项决策
   :header-rows: 1

   * - 选项
     - 合法写法
     - 边界或反例
     - 应检查的证据
   * - ``-i, --input-code``
     - ``-i traffic_light.fcstm``；``--input-code machines/control.fcstm``；文档夹具路径。
     - 无效 DSL 会阻止 PlantUML 源导出。
     - 成功输出以 ``@startuml`` 开头，并以 ``@enduml`` 结尾。
   * - ``-o, --output``
     - ``-o traffic_light.puml``；``-o build/diagram.txt``；省略则打印源码。
     - 后缀不会被解释为渲染类型；``machine.svg`` 也会收到 PlantUML 文本。
     - 应按文本检查文件，而不是按图片检查。
   * - ``-l, --level``
     - ``minimal`` 用于紧凑结构；``normal`` 用于平衡审查；``full`` 用于生命周期/动作审查。
     - 拼错的预设会被 Click 拒绝。
     - 生成源码只改变可见 PlantUML 事实，不改变模型语义。
   * - ``-c, --config``
     - ``-c show_events=false``；``-c max_depth=2``；``-c state_name_format=extra_name,name``。
     - 未知键、畸形 ``key=value`` 或非法类型值会在源码被接受前失败。
     - 输出源码应体现目标选项，例如隐藏事件或折叠深度。

.. list-table:: ``visualize`` 选项决策
   :header-rows: 1

   * - 选项
     - 合法写法
     - 边界或反例
     - 应检查的证据
   * - ``-i, --input-code``
     - 渲染时必需：``-i traffic_light.fcstm``；只有 ``--check`` 可以省略。
     - ``pyfcstm visualize --renderer auto`` 在没有 ``--check`` 和 ``-i`` 时是受控错误。
     - 渲染运行会先从同一路径生成 PlantUML 源。
   * - ``-o, --output``
     - ``-o traffic_light.svg -t svg``；``-o traffic_light -t png``；省略则使用缓存输出。
     - ``-o diagram.svg -t png`` 这种后缀/类型不一致会在渲染前被拒绝。
     - 无后缀路径会补上所选后缀；省略路径会使用平台缓存目录。
   * - ``-l, --level`` 和 ``-c, --config``
     - 与 ``plantuml`` 相同的源内容塑形选项。
     - 它们不控制渲染器、文件类型、缓存路径或打开查看器行为。
     - 对比生成图片或 PlantUML 源，确认目标事实确实可见。
   * - ``-t, --type``
     - ``png`` 用于截图；``svg`` 用于可缩放文档；``pdf`` 用于可打印产物。
     - ``jpg`` 或 ``xml`` 会被 Click 拒绝。
     - 后端会写出所选扩展名和格式的产物。
   * - ``--renderer``
     - ``auto`` 先尝试本地再尝试远程；``local`` 需要 Java/JAR；``remote`` 使用配置的 HTTP 服务。
     - 如果本地渲染失败，``auto`` 可能联系远程服务。
     - 成功消息会说明本次实际使用的渲染器。
   * - ``-j, --java``
     - ``-j /usr/bin/java``；省略则使用 ``PATH`` 里的 ``java``。
     - 它只影响本地渲染，不影响远程渲染。
     - 本地失败会在 Java 或路径不可用时说明对应问题。
   * - ``-p, --plantuml, --plantuml-jar``
     - ``-p ./plantuml.jar``；``--plantuml-jar /opt/plantuml.jar``；``PLANTUML_JAR=/opt/plantuml.jar``。
     - jar 缺失或无效会使本地渲染不可用。
     - ``visualize --check --renderer local`` 会报告 jar 路径是否可用。
   * - ``-r, --remote-host``
     - ``-r http://www.plantuml.com/plantuml``；``PLANTUML_HOST=https://internal.example/plantuml``。
     - 远程渲染会把生成的 PlantUML 源发给该服务。
     - 机密图应使用本地渲染，或在项目策略里记录被允许的主机。
   * - ``--check``
     - ``pyfcstm visualize --check``；``--check --renderer local``；``--check --renderer remote``。
     - 它不读取 ``-i``，也不证明任何具体 DSL 文件可以渲染。
     - 退出状态只报告后端可用性。
   * - ``--open / --no-open``
     - ``--no-open`` 用于脚本和 CI；默认 ``--open`` 用于桌面预览。
     - 无图形环境会跳过查看器启动，除非设置 ``--strict-open``。
     - 渲染成功与查看器启动成功是两件事。
   * - ``--strict-open``
     - 当桌面预览本身就是目标产物时，和 ``--open`` 配套使用。
     - 除非 CI 明确提供图形打开器，否则不要在 CI 中使用。
     - 它会把渲染后的非致命图形跳过转换成命令错误。

失败分类
--------

.. list-table:: 常见失败
   :header-rows: 1

   * - 区域
     - 示例原因
     - 典型信号
     - 优先修复
   * - 输入文件
     - 路径不存在或不可读。
     - 非零退出，并显示 Click 错误或 Python 读文件错误。
     - 检查路径和工作目录。
   * - DSL 语法
     - FCSTM 语法无效。
     - 带源码位置的语法解析诊断。
     - 运行 ``inspect`` 获取诊断报告并修复 DSL。
   * - 模型导入
     - 状态重名、转换无效、引用无法解析，或声明无效。
     - 模型验证诊断。
     - 渲染或生成前先修复 DSL 语义问题。
   * - 输出路径
     - 权限不足、后缀不匹配，或 ``--clear`` 指向不安全目录。
     - 写文件前或写文件时非零退出。
     - 使用可写路径，并让 ``visualize -o`` 后缀与 ``--type`` 一致。
   * - 模板渲染
     - 模板缺失、``config.yaml`` 错误，或 Jinja 渲染错误。
     - ``generate`` 非零退出。
     - 优先尝试内置 ``--template``；自定义模板单独调试。
   * - 验证策略
     - ``inspect`` 请求了被禁止的复杂度或展开预算。
     - 模型解析前出现策略错误。
     - 自动 inspect 检查保持在结构性/线性预算内。
   * - 渲染后端
     - 缺少 ``plantumlcli``、Java、PlantUML jar，或网络服务不可达。
     - ``visualize --check`` 或渲染失败。
     - 配置本地渲染，或使用允许的远程渲染器。
