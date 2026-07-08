.. _sec-reference-visualization-options-zh:

可视化选项参考
==============

``pyfcstm plantuml`` 和 ``pyfcstm visualize`` 共用同一套 PlantUML 源码配置。``plantuml`` 写出 PlantUML
源码后停止；``visualize`` 使用同一份源码配置，然后通过 PlantUML 后端渲染图片或 PDF。任务流程请看
:doc:`/how_to/visualization/index_zh`，精确选项事实请查本页。

下面的同步标记是给 ``tools/check_visualization_reference_docs.py`` 使用的注释，覆盖每个 ``PlantUMLOptions`` 字段，
以及命令行渲染器、文件类型、环境变量、解析器和失败边界事实。

.. visualization-ref-field: name=detail_level
.. visualization-ref-field: name=show_variable_definitions
.. visualization-ref-field: name=variable_display_mode
.. visualization-ref-field: name=variable_legend_position
.. visualization-ref-field: name=state_name_format
.. visualization-ref-field: name=show_pseudo_state_style
.. visualization-ref-field: name=collapse_empty_states
.. visualization-ref-field: name=show_lifecycle_actions
.. visualization-ref-field: name=show_enter_actions
.. visualization-ref-field: name=show_during_actions
.. visualization-ref-field: name=show_exit_actions
.. visualization-ref-field: name=show_aspect_actions
.. visualization-ref-field: name=show_abstract_actions
.. visualization-ref-field: name=show_concrete_actions
.. visualization-ref-field: name=abstract_action_marker
.. visualization-ref-field: name=max_action_lines
.. visualization-ref-field: name=show_transition_guards
.. visualization-ref-field: name=show_transition_effects
.. visualization-ref-field: name=transition_effect_mode
.. visualization-ref-field: name=show_events
.. visualization-ref-field: name=event_name_format
.. visualization-ref-field: name=event_visualization_mode
.. visualization-ref-field: name=event_legend_position
.. visualization-ref-field: name=max_depth
.. visualization-ref-field: name=collapsed_state_marker
.. visualization-ref-field: name=use_skinparam
.. visualization-ref-field: name=use_stereotypes
.. visualization-ref-field: name=custom_colors
.. visualization-ref-preset: name=minimal
.. visualization-ref-preset: name=normal
.. visualization-ref-preset: name=full
.. visualization-ref-renderer: name=local
.. visualization-ref-renderer: name=remote
.. visualization-ref-renderer: name=auto
.. visualization-ref-render-type: name=png
.. visualization-ref-render-type: name=svg
.. visualization-ref-render-type: name=pdf
.. visualization-ref-envvar: name=PLANTUML_JAR
.. visualization-ref-envvar: name=PLANTUML_HOST
.. visualization-ref-envvar: name=PYFCSTM_NO_GUI
.. visualization-ref-envvar: name=CI
.. visualization-ref-envvar: name=DISPLAY
.. visualization-ref-envvar: name=WAYLAND_DISPLAY
.. visualization-ref-envvar: name=MIR_SOCKET
.. visualization-ref-envvar: name=XDG_CACHE_HOME
.. visualization-ref-envvar: name=LOCALAPPDATA
.. visualization-ref-parser-form: group=value bool int float quoted-string none null tuple optional invalid-key invalid-value
.. visualization-ref-boundary: group=behavior renderer-auto-fallback suffix-mismatch check-mode headless-open strict-open remote-privacy cache-output local-backend-failure remote-network-failure backend-success-without-output source-only-plantuml rendered-image-visualize

心智模型
--------

可视化分成两个彼此独立的层次：

1. **PlantUML 源码层**。``PlantUMLOptions`` 决定生成的 PlantUML 文本里能看到哪些模型事实：变量、生命周期动作、
   保护条件、效果、事件、状态标签、层级深度和样式。
2. **渲染产物层**。``visualize`` 选择渲染后端、文件类型、输出路径和查看器行为。这些设置不改变 PlantUML 源码里的模型事实，
   只决定源码如何变成 ``png``、``svg`` 或 ``pdf``。

细节预设
--------

命令行 ``-l`` / ``--level`` 选项对应 ``PlantUMLOptions.detail_level``。先用它决定主要读者，再用 ``-c key=value``
补少量偏离预设的细节。

.. list-table:: 细节预设
   :header-rows: 1

   * - 预设
     - 解析后默认值
     - 适用场景
   * - ``minimal``
     - 显示变量定义、转换保护条件、转换效果和事件；隐藏生命周期动作和伪状态样式。
     - 面向汇报和架构视图，强调状态结构而非实现细节。
   * - ``normal``
     - 显示变量定义、转换保护条件、转换效果、事件和伪状态样式；隐藏生命周期动作。
     - 通用文档、代码审查和快速理解模型。
   * - ``full``
     - 显示变量定义、生命周期动作、转换保护条件、转换效果、事件和伪状态样式。
     - 深入调试、语义审查和生成运行时一致性讨论。

预设例子：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l minimal -o machine.minimal.puml
   pyfcstm plantuml -i machine.fcstm -l normal -o machine.normal.puml
   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

PlantUML 选项字段
-----------------

默认值为 ``None`` 的选项由 ``PlantUMLOptions.to_config()`` 解析。解析顺序是：显式值、父级开关、细节预设、最终兜底值。
父级开关尤其影响生命周期动作：``show_enter_actions``、``show_during_actions``、``show_exit_actions``、
``show_aspect_actions``、``show_abstract_actions`` 和 ``show_concrete_actions`` 在为 ``None`` 时继承
``show_lifecycle_actions``。

.. list-table:: 完整 ``PlantUMLOptions`` 字段表
   :header-rows: 1

   * - 字段
     - 命令行形式
     - 默认值
     - 取值
     - 影响和说明
   * - ``detail_level``
     - ``-l minimal|normal|full``
     - ``normal``
     - ``minimal``、``normal``、``full``
     - 主预设。命令行使用 ``-l``；不要传 ``-c detail_level=...``，因为命令已经单独传入预设。
   * - ``show_variable_definitions``
     - ``-c show_variable_definitions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示 ``def`` 变量清单。``None`` 从预设解析。
   * - ``variable_display_mode``
     - ``-c variable_display_mode=legend``
     - ``legend``
     - ``note``、``legend``、``hide``
     - 变量显示为 PlantUML 注释、图例表，或完全隐藏。
   * - ``variable_legend_position``
     - ``-c 'variable_legend_position=bottom right'``
     - ``top left``
     - ``top left``、``top center``、``top right``、``bottom left``、``bottom center``、``bottom right``、``left``、``right``、``center``
     - 变量图例位置。值里有空格时需要给整个 shell 参数加引号。
   * - ``state_name_format``
     - ``-c state_name_format=extra_name,name``
     - ``('extra_name',)``
     - ``name``、``extra_name``、``path`` 组成的元组
     - 状态标签组件。第一个可见组件是主标签，其余组件放在括号里。
   * - ``show_pseudo_state_style``
     - ``-c show_pseudo_state_style=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 应用伪状态视觉样式。``minimal`` 解析为 ``False``；``normal`` 和 ``full`` 解析为 ``True``。
   * - ``collapse_empty_states``
     - ``-c collapse_empty_states=true``
     - ``False``
     - 布尔值
     - 压缩没有可见动作文本的状态。
   * - ``show_lifecycle_actions``
     - ``-c show_lifecycle_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 进入、期间、退出、切面、抽象和具体动作可见性的总开关。
   * - ``show_enter_actions``
     - ``-c show_enter_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 覆盖生命周期父级开关时，只显示进入动作。
   * - ``show_during_actions``
     - ``-c show_during_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 在需要可见生命周期细节时显示期间动作。
   * - ``show_exit_actions``
     - ``-c show_exit_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示退出动作。
   * - ``show_aspect_actions``
     - ``-c show_aspect_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示 ``>> during before`` 和 ``>> during after`` 切面动作。
   * - ``show_abstract_actions``
     - ``-c show_abstract_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示抽象生命周期动作，常用于集成表面说明。
   * - ``show_concrete_actions``
     - ``-c show_concrete_actions=true``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示具体操作体，常用于实现审查。
   * - ``abstract_action_marker``
     - ``-c abstract_action_marker=symbol``
     - ``text``
     - ``text``、``symbol``、``none``
     - 抽象动作显示为文字、书名号样式标记，或不显示抽象标记。
   * - ``max_action_lines``
     - ``-c max_action_lines=3``
     - ``None``
     - 整数，Python 中也可为 ``None``
     - 限制每个动作的可见行数，适合完整图过高时使用。
   * - ``show_transition_guards``
     - ``-c show_transition_guards=false``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示或隐藏转换保护条件。
   * - ``show_transition_effects``
     - ``-c show_transition_effects=false``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示或隐藏转换效果块。
   * - ``transition_effect_mode``
     - ``-c transition_effect_mode=inline``
     - ``note``
     - ``note``、``inline``、``hide``
     - 选择链路注释效果、紧凑行内效果，或隐藏效果。
   * - ``show_events``
     - ``-c show_events=false``
     - ``None``
     - 布尔值，Python 中也可为 ``None``
     - 显示或隐藏转换上的事件名称。
   * - ``event_name_format``
     - ``-c event_name_format=extra_name,relpath``
     - ``('extra_name', 'relpath')``
     - ``name``、``extra_name``、``path``、``relpath`` 组成的元组
     - 事件标签组件。``path`` 是绝对路径；``relpath`` 在可用时沿用转换里的事件引用。
   * - ``event_visualization_mode``
     - ``-c event_visualization_mode=both``
     - ``none``
     - ``none``、``color``、``legend``、``both``、``dependency_view``
     - 加事件颜色、事件图例、两者都加，或不加特殊事件可视化。``dependency_view`` 是保留模式，不应作为普通图模式使用。
   * - ``event_legend_position``
     - ``-c event_legend_position=right``
     - ``right``
     - 与 ``variable_legend_position`` 相同的位置标签
     - 启用事件图例时的图例位置。
   * - ``max_depth``
     - ``-c max_depth=2``
     - ``None``
     - 整数，Python 中也可为 ``None``
     - 限制展开的层级深度，在更深处插入折叠状态标记。
   * - ``collapsed_state_marker``
     - ``-c collapsed_state_marker='[more]'``
     - ``...``
     - 字符串
     - ``max_depth`` 隐藏更深状态时显示的文本。
   * - ``use_skinparam``
     - ``-c use_skinparam=false``
     - ``True``
     - 布尔值
     - 是否包含 pyfcstm PlantUML 样式块。
   * - ``use_stereotypes``
     - ``-c use_stereotypes=false``
     - ``True``
     - 布尔值
     - 是否包含 ``<<pseudo>>``、``<<composite>>`` 等 PlantUML 构造型。
   * - ``custom_colors``
     - 仅 Python 应用程序接口（API）
     - ``None``
     - 映射或 ``None``
     - ``color`` 和 ``both`` 事件模式使用的自定义事件颜色映射。命令行不解析该字典选项。

类型化 ``-c`` 取值语法
----------------------

命令行接受重复的 ``-c key=value`` 参数，并使用 pyfcstm 其他配置路径共用的解析辅助函数解析取值。

.. list-table:: 取值形式
   :header-rows: 1

   * - 形式
     - 例子
     - 结果
     - 说明
   * - 布尔值
     - ``true``、``yes``、``1``、``false``、``no``、``0``
     - Python ``bool``
     - 布尔字段只接受这些形式。
   * - 整数
     - ``3``、``0``
     - Python ``int``
     - 用于 ``max_depth`` 和 ``max_action_lines``。
   * - 浮点数
     - ``1.5``
     - Python ``float``
     - 自动解析器支持浮点数，当前 PlantUML 命令行字段不需要浮点专用选项。
   * - 带引号字符串
     - ``'variable_legend_position=bottom right'``
     - Python ``str``
     - 值中含空格时，应给整个 shell 参数加引号。
   * - ``none`` / ``null``
     - ``none``、``null``
     - 自动模式或 None 类型字段里的 Python ``None``
     - 多数命令行字段使用显式具体类型，因此 ``None`` 主要用于 Python API。
   * - 元组
     - ``state_name_format=extra_name,name``
     - 字符串元组
     - 用于 ``state_name_format`` 和 ``event_name_format``。
   * - 可选值
     - 省略选项，或 Python 中显式传 ``None``
     - 继承/解析后的值
     - 可选布尔值经由父级开关和预设解析。
   * - 无效键
     - ``-c does_not_exist=true``
     - 命令失败
     - 未知键会传到 ``PlantUMLOptions`` 构造并被拒绝。
   * - 无效值
     - ``-c max_depth=abc``
     - 命令失败
     - 类型解析会报告出错的键。

命令行例子：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -c show_events=true -c max_depth=2
   pyfcstm plantuml -i machine.fcstm -c state_name_format=extra_name,name
   pyfcstm plantuml -i machine.fcstm -c 'variable_legend_position=bottom right'

Python 应用程序接口（API）例子：

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   api_surface = PlantUMLOptions(
       detail_level='full',
       show_concrete_actions=False,
       show_abstract_actions=True,
       abstract_action_marker='symbol',
   )

   event_view = PlantUMLOptions(
       event_visualization_mode='both',
       custom_colors={'System.Start': '#00AA00'},
   )

渲染器和文件选项
----------------

这些选项只属于 ``visualize``，不影响 PlantUML 源码内容。

.. list-table:: 渲染器和文件事实
   :header-rows: 1

   * - 事实
     - 取值
     - 含义
   * - 渲染器模式
     - ``local``、``remote``、``auto``
     - ``local`` 使用 Java 和 PlantUML jar；``remote`` 使用 PlantUML 服务；``auto`` 先试本地再试远程。
   * - 渲染类型
     - ``png``、``svg``、``pdf``
     - 输出文件类型。提供后缀时，输出后缀必须和所选类型一致。
   * - 缓存路径
     - 平台相关
     - 省略 ``visualize -o`` 时使用。Linux 遵循 ``XDG_CACHE_HOME``；Windows 遵循 ``LOCALAPPDATA``。
   * - 检查模式
     - ``pyfcstm visualize --check``
     - 检查渲染器可用性并退出，不解析 DSL 文件。
   * - 打开模式
     - ``--open`` / ``--no-open`` / ``--strict-open``
     - 控制渲染后是否启动查看器。无图形界面环境会跳过查看器，除非请求严格模式。

环境变量
--------

.. list-table:: 环境变量
   :header-rows: 1

   * - 变量
     - 使用者
     - 含义
   * - ``PLANTUML_JAR``
     - ``visualize --renderer local``
     - 省略 ``-p`` / ``--plantuml-jar`` 时的默认 PlantUML jar 路径。
   * - ``PLANTUML_HOST``
     - ``visualize --renderer remote``
     - 省略 ``-r`` / ``--remote-host`` 时的默认远程 PlantUML 服务。
   * - ``PYFCSTM_NO_GUI``
     - ``visualize --open``
     - 真值会禁用自动启动查看器。
   * - ``CI``
     - ``visualize --open``
     - 真值会把环境视作无图形界面环境。
   * - ``DISPLAY`` / ``WAYLAND_DISPLAY`` / ``MIR_SOCKET``
     - Linux 查看器检测
     - Linux 上通常至少有一个变量表示图形会话存在。
   * - ``XDG_CACHE_HOME``
     - Linux 缓存输出
     - 省略 ``visualize -o`` 时的基础缓存目录。
   * - ``LOCALAPPDATA``
     - Windows 缓存输出
     - Windows 上省略 ``visualize -o`` 时的基础缓存目录。

行为边界
--------

.. list-table:: 边界事实
   :header-rows: 1

   * - 边界
     - 精确行为
   * - ``renderer-auto-fallback``
     - ``auto`` 先试本地渲染；只有本地后端创建或检查失败时才回退远程。
   * - ``suffix-mismatch``
     - ``visualize -o diagram.svg -t png`` 会在渲染前失败，因为 ``.svg`` 和 ``png`` 不匹配。
   * - ``check-mode``
     - ``--check`` 不需要 ``-i``，也不解析任何 DSL 文件。
   * - ``headless-open``
     - 无图形界面环境下，普通 ``--open`` 打印跳过消息，并保持成功渲染仍然成功。
   * - ``strict-open``
     - ``--strict-open`` 会把查看器启动失败或无图形界面跳过变成命令失败。
   * - ``remote-privacy``
     - 远程渲染会把生成的 PlantUML 源码发送到配置服务。私有图表应使用本地渲染。
   * - ``cache-output``
     - 省略 ``-o`` 时写入 pyfcstm 可视化缓存，而不是当前目录。
   * - ``local-backend-failure``
     - 本地失败会说明本地渲染器，并在可用时包含底层 ``plantumlcli`` / Java / 路径错误类别。
   * - ``remote-network-failure``
     - 远程失败会说明远程渲染器，并在可用时包含底层网络或请求错误。
   * - ``backend-success-without-output``
     - 如果 ``plantumlcli`` 报告成功但没有创建文件，pyfcstm 会把它视为失败。
   * - ``source-only-plantuml``
     - ``plantuml`` 永远不渲染图片，也不检查渲染器可用性。
   * - ``rendered-image-visualize``
     - ``visualize`` 总是先生成 PlantUML 源码，再渲染请求的产物类型。
