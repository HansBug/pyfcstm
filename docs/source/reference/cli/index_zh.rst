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
