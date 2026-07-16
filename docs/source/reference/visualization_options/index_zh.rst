.. _sec-reference-visualization-options-zh:

可视化选项参考
==============

``pyfcstm plantuml`` 和 ``pyfcstm visualize`` 共用同一套 PlantUML 源码配置。``plantuml`` 写出 PlantUML
源码后停止；``visualize`` 使用同一份源码配置，然后通过 PlantUML 后端渲染图片或 PDF。任务流程请看
:doc:`/how_to/visualization/index_zh`，精确选项事实请查本页。

本页中文术语约定：渲染器（renderer）、渲染后端（backend）、本地渲染（local rendering）、
远程渲染（remote rendering）、缓存（cache）、文件后缀（suffix）、无图形界面（headless）、查看器（viewer）、
隐私边界（privacy boundary）和选项解析（option parsing）首次在这里对应英文；后文普通说明使用中文术语。命令、字段名、
环境变量、枚举值和错误摘录仍保持原文。

下面的同步标记是给 ``tools/check_visualization_reference_docs.py`` 使用的注释，覆盖每个 ``PlantUMLOptions`` 字段，
以及命令行渲染器、文件类型、环境变量、解析器和失败边界事实。

.. visualization-ref-field: name=detail_level default=normal
.. visualization-ref-field: name=show_variable_definitions default=None
.. visualization-ref-field: name=variable_display_mode default=legend
.. visualization-ref-field: name=variable_legend_position default="top left"
.. visualization-ref-field: name=state_name_format default=extra_name
.. visualization-ref-field: name=show_pseudo_state_style default=None
.. visualization-ref-field: name=collapse_empty_states default=False
.. visualization-ref-field: name=show_lifecycle_actions default=None
.. visualization-ref-field: name=show_enter_actions default=None
.. visualization-ref-field: name=show_during_actions default=None
.. visualization-ref-field: name=show_exit_actions default=None
.. visualization-ref-field: name=show_aspect_actions default=None
.. visualization-ref-field: name=show_abstract_actions default=None
.. visualization-ref-field: name=show_concrete_actions default=None
.. visualization-ref-field: name=abstract_action_marker default=text
.. visualization-ref-field: name=max_action_lines default=None
.. visualization-ref-field: name=show_transition_guards default=None
.. visualization-ref-field: name=show_transition_effects default=None
.. visualization-ref-field: name=transition_effect_mode default=note
.. visualization-ref-field: name=show_events default=None
.. visualization-ref-field: name=event_name_format default=extra_name,relpath
.. visualization-ref-field: name=event_visualization_mode default=none
.. visualization-ref-field: name=event_legend_position default=right
.. visualization-ref-field: name=max_depth default=None
.. visualization-ref-field: name=collapsed_state_marker default=...
.. visualization-ref-field: name=use_skinparam default=True
.. visualization-ref-field: name=use_stereotypes default=True
.. visualization-ref-field: name=custom_colors default=None
.. visualization-ref-preset: name=minimal defaults=show_variable_definitions=True,show_pseudo_state_style=False,show_lifecycle_actions=False,show_enter_actions=False,show_during_actions=False,show_exit_actions=False,show_aspect_actions=False,show_abstract_actions=False,show_concrete_actions=False,show_transition_guards=True,show_transition_effects=True,show_events=True
.. visualization-ref-preset: name=normal defaults=show_variable_definitions=True,show_pseudo_state_style=True,show_lifecycle_actions=False,show_enter_actions=False,show_during_actions=False,show_exit_actions=False,show_aspect_actions=False,show_abstract_actions=False,show_concrete_actions=False,show_transition_guards=True,show_transition_effects=True,show_events=True
.. visualization-ref-preset: name=full defaults=show_variable_definitions=True,show_pseudo_state_style=True,show_lifecycle_actions=True,show_enter_actions=True,show_during_actions=True,show_exit_actions=True,show_aspect_actions=True,show_abstract_actions=True,show_concrete_actions=True,show_transition_guards=True,show_transition_effects=True,show_events=True
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

参考级选项场景
--------------

下面的参考表按字段做到闭合，但单个字段行不能展示选项如何组合。下列场景把最常见组合绑定到可观察结果和失败边界。

.. list-table:: 选项场景和边界
   :header-rows: 1

   * - 场景
     - 示例
     - 预期效果
     - 边界或反例
   * - 只用预设导出源码。
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -l minimal -o /tmp/minimal.puml``
     - 使用 ``minimal`` 预设生成源码文本，不写图片。
     - 把 ``-t svg`` 传给 ``plantuml`` 是非法的；渲染类型属于 ``visualize``。
   * - 预设加窄覆盖。
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -l full -c max_action_lines=3 -o /tmp/compact.puml``
     - 保持 full 可见性，同时把每个动作块限制为三行。
     - 预设建议使用 ``-l full``；``-c detail_level=full`` 也合法，若与显式 ``-l`` 冲突会输出 warning 并以 ``-l`` 为准。
   * - 事件导向图。
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -c event_visualization_mode=both -o /tmp/events.puml``
     - 同时在转换和事件辅助结构中显示事件。
     - 非法枚举值会在选项解析阶段失败，不会调用渲染器。
   * - 无图形界面渲染。
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm -t svg -o /tmp/example.svg --no-open``
     - 写出 SVG，并跳过桌面查看器启动。
     - 没有 ``--no-open`` 时，即使渲染成功，图形界面可用性也可能影响最后的打开步骤。
   * - 本地渲染隐私。
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm --renderer local -p ./plantuml.jar --no-open``
     - 当 Java 和 jar 可用时，PlantUML 源码保留在本机。
     - 缺少 jar 或 Java 是本地后端失败，不是模型或 PlantUML 选项失败。
   * - 远程渲染便利性。
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm --renderer remote --no-open``
     - 把 PlantUML 源码发送到配置的远程主机，并写出渲染产物。
     - 除非允许把源码发送到该主机，否则不要用于私有图表。

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
     - 主预设。也可以通过 ``-c detail_level=...`` 提供。如果显式 ``-l/--level`` 与 ``-c`` 的值不一致，CLI 会输出 warning，并以显式 ``-l/--level`` 的值为准。
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
     - 仅 Python API（应用程序接口）
     - ``None``
     - 映射或 ``None``
     - ``color`` 和 ``both`` 事件模式使用的自定义事件颜色映射。命令行不解析该字典选项。

字段和渲染器例子卡片
--------------------------------

上面的表给出闭合字段列表；下面的卡片说明字段组在真实命令中怎样相互影响。这里故意重复：每一行都给具体命令、预期源码或渲染信号，以及选择或避免它的原因。

预设解析例子
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 例子
   :header-rows: 1

   * - 用途
     - 命令
     - 预期效果
     - 选择规则
   * - 最小结构审查
     - ``pyfcstm plantuml -i machine.fcstm -l minimal -o machine.min.puml``
     - 显示层级、变量、转换保护条件/效果和事件；隐藏生命周期动作文本和伪状态样式。
     - 用于架构讨论，避免实现体分散注意力。
   * - 普通文档视图
     - ``pyfcstm plantuml -i machine.fcstm -l normal -o machine.normal.puml``
     - 增加伪状态样式，同时隐藏生命周期动作。
     - 用于大多数文档和审查片段。
   * - 完整语义审查
     - ``pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml``
     - 显示生命周期动作族，以及由细节预设控制的具体/抽象动作可见性。
     - 用于语义审查、生成运行时对齐或调试。
   * - 预设后覆盖
     - ``pyfcstm plantuml -i machine.fcstm -l minimal -c show_lifecycle_actions=true -o machine.min-actions.puml``
     - 显式值优先于预设默认值。
     - 仅在最小图需要补一个语义维度时少量使用。

审查说明：
  如果命令改变源码可见性，检查生成的 ``.puml``。如果命令改变渲染行为，检查 ``visualize --check`` 或渲染产物路径。

变量和状态标签例子
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 例子
   :header-rows: 1

   * - 用途
     - 命令
     - 预期效果
     - 选择规则
   * - 图例变量
     - ``pyfcstm plantuml -i machine.fcstm -c variable_display_mode=legend -o machine.vars.puml``
     - 变量定义渲染在 PlantUML 图例中。
     - 适合变量是整张图全局上下文的情况。
   * - 隐藏变量
     - ``pyfcstm plantuml -i machine.fcstm -c variable_display_mode=hide -o machine.no-vars.puml``
     - 变量清单会从源码中移除。
     - 适合只展示结构的图。
   * - 双状态标签
     - ``pyfcstm plantuml -i machine.fcstm -c state_name_format=extra_name,name -o machine.labels.puml``
     - 状态标签同时包含可读额外名称和原始模型名。
     - 适合生成标识符和 DSL 名称都重要的情况。
   * - 折叠深度
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=2 -c collapsed_state_marker="[more]" -o machine.depth.puml``
     - 超过深度的后代会被标记替代。
     - 适合大型层级模型。

审查说明：
  如果命令改变源码可见性，检查生成的 ``.puml``。如果命令改变渲染行为，检查 ``visualize --check`` 或渲染产物路径。

生命周期可见性例子
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 例子
   :header-rows: 1

   * - 用途
     - 命令
     - 预期效果
     - 选择规则
   * - 生命周期总开关
     - ``pyfcstm plantuml -i machine.fcstm -c show_lifecycle_actions=true -o machine.lifecycle.puml``
     - enter、during、exit、切面、抽象和具体动作族继承可见性默认值。
     - 用于生命周期顺序属于审查内容的情况。
   * - 只看抽象钩子
     - ``pyfcstm plantuml -i machine.fcstm -c show_lifecycle_actions=false -c show_abstract_actions=true -o machine.hooks.puml``
     - 抽象扩展点保持可见，具体动作体保持隐藏。
     - 用于集成表面审查。
   * - 限制动作文本
     - ``pyfcstm plantuml -i machine.fcstm -l full -c max_action_lines=3 -o machine.short-actions.puml``
     - 长动作体会在配置行数后截断。
     - 用于完整图过高的情况。
   * - 只审查切面
     - ``pyfcstm plantuml -i machine.fcstm -c show_lifecycle_actions=false -c show_aspect_actions=true -o machine.aspects.puml``
     - 后代周期 before/after 切面可见，其他生命周期体隐藏。
     - 用于审查横切行为。

审查说明：
  如果命令改变源码可见性，检查生成的 ``.puml``。如果命令改变渲染行为，检查 ``visualize --check`` 或渲染产物路径。

转换和事件例子
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 例子
   :header-rows: 1

   * - 用途
     - 命令
     - 预期效果
     - 选择规则
   * - 隐藏保护条件
     - ``pyfcstm plantuml -i machine.fcstm -c show_transition_guards=false -o machine.no-guards.puml``
     - 转换标签省略保护条件。
     - 仅在保护条件与读者无关时使用。
   * - 内联效果
     - ``pyfcstm plantuml -i machine.fcstm -c transition_effect_mode=inline -o machine.inline-effects.puml``
     - 转换效果紧凑显示在转换上，而不是注释块中。
     - 用于较短的效果体。
   * - 事件图例
     - ``pyfcstm plantuml -i machine.fcstm -c event_visualization_mode=legend -o machine.event-legend.puml``
     - 事件进入图例，但不为转换着色。
     - 用于事件名频繁重复的情况。
   * - 事件颜色和图例
     - ``pyfcstm plantuml -i machine.fcstm -c event_visualization_mode=both -o machine.event-colors.puml``
     - 事件会被着色并列入图例。
     - 用于事件流图。

审查说明：
  如果命令改变源码可见性，检查生成的 ``.puml``。如果命令改变渲染行为，检查 ``visualize --check`` 或渲染产物路径。

渲染器和环境例子
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 例子
   :header-rows: 1

   * - 用途
     - 命令
     - 预期效果
     - 选择规则
   * - 只导出源码
     - ``pyfcstm plantuml -i machine.fcstm -o machine.puml``
     - 不检查也不使用渲染器。
     - 即使 Java 或网络渲染不可用也安全。
   * - 后端检查
     - ``pyfcstm visualize --check --renderer auto``
     - 报告本地和远程可用性，并在不解析 DSL 的情况下退出。
     - 在 CI 渲染任务前使用。
   * - 缓存输出
     - ``pyfcstm visualize -i machine.fcstm --no-open``
     - 省略 -o 时写入 pyfcstm visualize 缓存。
     - 仅用于本地预览，不用于可复现构建输出。
   * - 严格打开
     - ``pyfcstm visualize -i machine.fcstm --strict-open``
     - 查看器启动失败会变成命令失败。
     - 只用于必须打开图片的桌面工作流。

审查说明：
  如果命令改变源码可见性，检查生成的 ``.puml``。如果命令改变渲染行为，检查 ``visualize --check`` 或渲染产物路径。

非法取值例子
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 例子
   :header-rows: 1

   * - 用途
     - 命令
     - 预期效果
     - 选择规则
   * - 未知字段
     - ``pyfcstm plantuml -i machine.fcstm -c does_not_exist=true``
     - 失败原因是该键不是 PlantUMLOptions 字段。
     - 检查完整字段表。
   * - 错误整数
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=abc``
     - 失败原因是 max_depth 需要整数或 None。
     - 使用 2 这样的数字。
   * - 错误渲染类型后缀
     - ``pyfcstm visualize -i machine.fcstm -o machine.svg -t png --no-open``
     - 在渲染前失败，因为后缀和类型不一致。
     - 使用 -o machine.png 或 -t svg。
   * - 私有源码走远程
     - ``pyfcstm visualize -i private.fcstm --renderer remote --no-open``
     - 这可能成功，但会把 PlantUML 源码发送给服务。
     - 私有图使用本地渲染。

审查说明：
  如果命令改变源码可见性，检查生成的 ``.puml``。如果命令改变渲染行为，检查 ``visualize --check`` 或渲染产物路径。

解析轨迹：生命周期动作
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

生命周期可见性是用户最容易误解选项模型的地方。解析后的值并不只是 dataclass 默认值：

1. 显式子开关（例如 ``show_enter_actions=false``）最优先。
2. 如果子开关是 ``None``，并且父开关 ``show_lifecycle_actions`` 是显式值，则继承父开关。
3. 如果父开关也是 ``None``，则由所选细节预设提供默认值。
4. 最终兜底值只在这些步骤之后应用。

.. list-table:: 生命周期解析例子
   :header-rows: 1

   * - 输入
     - 解析含义
     - 读者可见结果
   * - ``-l minimal``
     - 生命周期父开关和子开关解析为 false。
     - 生命周期文本隐藏。
   * - ``-l full``
     - 生命周期父开关和子开关解析为 true。
     - 除非其他选项隐藏，enter/during/exit/切面/抽象/具体动作都可见。
   * - ``-l full -c show_concrete_actions=false``
     - 具体动作体可见性显式为 false；其他 full 预设动作组保持可见。
     - 抽象钩子可以保持可见，同时隐藏实现体。
   * - ``-c show_lifecycle_actions=false -c show_enter_actions=true``
     - 对 enter 动作来说，显式子开关覆盖显式父开关。
     - 即使其他生命周期组保持隐藏，enter 动作仍可见。


中文说明
~~~~~~~~

命令、选项、字段名和环境变量保持原文；解释性文字应使用中文术语。后续扩写本页时，不要用 marker 行数代替真实例子和边界说明。


逐字段场景矩阵
--------------

上面的完整字段表是封闭清单；下面的矩阵更偏实际审查：每个公开字段都有两个常规例子和一个边界例子。需要证明某个图形选择是有意为之，而不是偶然产物时，应使用这组矩阵。

.. list-table:: 源可见性与标签字段
   :header-rows: 1

   * - 字段
     - 例子 A
     - 例子 B
     - 边界或反例
   * - ``detail_level``
     - ``-l minimal`` 用于小型层次审查。
     - ``-l full`` 用于生命周期动作主题。
     - ``-l normal -c detail_level=full`` 会输出冲突 warning，并使用 ``normal``，因为显式 ``-l`` 的值优先。
   * - ``show_variable_definitions``
     - ``-c show_variable_definitions=true`` 用于在审查中证明变量声明。
     - ``-c show_variable_definitions=false`` 用于只看结构的图。
     - 即使本开关为 true，``variable_display_mode=hide`` 也会隐藏变量。
   * - ``variable_display_mode``
     - ``legend`` 让文档页面里的变量更紧凑。
     - ``note`` 让变量在状态图旁更醒目。
     - ``hide`` 不是位置选项，而是抑制变量输出。
   * - ``variable_legend_position``
     - ``top left`` 会把右侧留给事件图例。
     - ``bottom right`` 适合图顶部很密的情况。
     - shell 中包含空格的值需要加引号。
   * - ``state_name_format``
     - ``extra_name`` 在存在显示名时展示显示名。
     - ``extra_name,name`` 同时保留人类标签和 DSL 标识符。
     - ``path`` 可能让大图变吵；只在需要消歧时使用。
   * - ``show_pseudo_state_style``
     - ``true`` 让 normal/full 图里的伪状态更容易辨认。
     - ``false`` 让 minimal 图更少样式干扰。
     - 它只影响样式，不影响模型中是否存在伪状态。
   * - ``collapse_empty_states``
     - ``true`` 缩短没有可见动作文本的状态。
     - ``false`` 保留常规 PlantUML 状态块，便于阅读。
     - 如果生命周期细节被隐藏，某个状态可能视觉上为空，但实际有隐藏动作。
   * - ``max_depth``
     - ``1`` 只保留根层结构，适合高层审查。
     - ``2`` 展示一层嵌套，同时隐藏更深细节。
     - 它只隐藏图形细节，不删除模型状态。
   * - ``collapsed_state_marker``
     - ``...`` 紧凑且中性。
     - ``[hidden children]`` 对文档读者更明确。
     - 只有 ``max_depth`` 确实折叠后代时，标记才会出现。

.. list-table:: 生命周期与动作字段
   :header-rows: 1

   * - 字段
     - 例子 A
     - 例子 B
     - 边界或反例
   * - ``show_lifecycle_actions``
     - ``true`` 用于审查 entry/during/exit 顺序。
     - ``false`` 用于更关注转换和层次而不是动作体的图。
     - 子开关只有显式设置时才会覆盖它。
   * - ``show_enter_actions``
     - 配合 ``show_lifecycle_actions=false`` 和 ``true``，单独突出初始化钩子。
     - 配合 ``show_lifecycle_actions=true`` 和 ``false``，隐藏嘈杂的 entry 细节。
     - Python 中的 ``None`` 表示继承，不是 false。
   * - ``show_during_actions``
     - ``true`` 用于周期行为审查。
     - ``false`` 用于只强调转换。
     - aspect 形式的 ``during`` 钩子由 ``show_aspect_actions`` 分开控制。
   * - ``show_exit_actions``
     - ``true`` 用于清理行为重要的场景。
     - ``false`` 用于紧凑状态清单。
     - 隐藏 exit 动作不会隐藏转换 effect。
   * - ``show_aspect_actions``
     - ``true`` 展示 ``>> during before`` 和 ``>> during after`` 钩子。
     - ``false`` 表示读者只需要叶状态本地动作。
     - 它关注 aspect 钩子，不是普通转换 guard。
   * - ``show_abstract_actions``
     - ``true`` 用于让生成代码集成钩子可见。
     - ``false`` 用于只审查具体操作。
     - 生命周期可见性允许动作组之后，它才继续过滤动作。
   * - ``show_concrete_actions``
     - ``true`` 用于审查赋值和操作体。
     - ``false`` 用于只展示抽象扩展点。
     - 它不改变生成运行时代码行为。
   * - ``abstract_action_marker``
     - ``text`` 保留 DSL 词 ``abstract``。
     - ``symbol`` 使用紧凑的 ``«abstract»`` 标记。
     - ``none`` 可能隐藏差异；只有图注解释了选择时才使用。
   * - ``max_action_lines``
     - ``3`` 让 normal 图中的长动作更可读。
     - ``1`` 只显示第一行作为定位信息。
     - ``0`` 或 ``None`` 不像正整数那样提供有用的行数限制。

.. list-table:: 转换、事件与样式字段
   :header-rows: 1

   * - 字段
     - 例子 A
     - 例子 B
     - 边界或反例
   * - ``show_transition_guards``
     - ``true`` 用于可达性和条件审查。
     - ``false`` 用于纯拓扑图。
     - 隐藏 guard 可能让互斥路径看起来有歧义。
   * - ``show_transition_effects``
     - ``true`` 用于变量更新重要的场景。
     - ``false`` 用于紧凑路由图。
     - 即使图中隐藏，effect 仍可能存在于模型中。
   * - ``transition_effect_mode``
     - ``note`` 让长 effect 不挤在边标签上。
     - ``inline`` 适合短赋值。
     - ``hide`` 会在 effect 存在时也抑制文本。
   * - ``show_events``
     - ``true`` 用于解释事件触发转换。
     - ``false`` 用于只关注可能移动路径的图。
     - 事件被隐藏时，事件颜色和图例没有意义。
   * - ``event_name_format``
     - ``extra_name,relpath`` 紧凑且面向用户。
     - ``name,path`` 适合绝对归属很重要的场景。
     - ``relpath`` 会在可用时跟随转换里的事件引用。
   * - ``event_visualization_mode``
     - ``color`` 给事件族着色但不增加图例。
     - ``both`` 同时使用颜色和图例，适合文档。
     - ``dependency_view`` 是保留模式，不应当作普通事件模式。
   * - ``event_legend_position``
     - ``right`` 把事件解释放在图旁边。
     - ``bottom center`` 适合宽图。
     - 只有启用事件图例输出时，它才有意义。
   * - ``use_skinparam``
     - ``true`` 应用 pyfcstm 默认 PlantUML 样式。
     - ``false`` 让下游 PlantUML 主题接管样式。
     - 关闭它可能降低伪状态/组合状态差异的可见性。
   * - ``use_stereotypes``
     - ``true`` 输出 ``<<pseudo>>`` 等 stereotype。
     - ``false`` 产生更朴素的 PlantUML 源。
     - 某些样式规则依赖 stereotype，因此关闭它可能改变视觉含义。
   * - ``custom_colors``
     - Python API 可以把事件组映射到稳定颜色。
     - 用于需要匹配图例调色板的发布级图。
     - CLI 不能解析这个字段的字典值。

.. list-table:: 渲染器与环境决策字段
   :header-rows: 1

   * - 决策
     - 例子 A
     - 例子 B
     - 边界或反例
   * - 渲染类型
     - ``-t svg`` 用于可缩放文档。
     - ``-t png`` 用于截图或快速预览。
     - 提供后缀时，输出后缀必须匹配类型。
   * - 渲染器模式
     - ``--renderer local`` 用于私有图。
     - ``--renderer remote`` 用于由已批准服务负责渲染的场景。
     - ``--renderer auto`` 可能在本地失败后退回远程。
   * - 本地后端路径
     - ``-j /usr/bin/java`` 固定 Java 可执行文件。
     - ``-p ./plantuml.jar`` 固定 PlantUML jar。
     - 这些选项不影响远程渲染。
   * - 远程后端主机
     - ``-r http://www.plantuml.com/plantuml`` 显式使用公共默认服务。
     - ``PLANTUML_HOST=https://plantuml.internal/plantuml`` 使用内部服务。
     - 远程渲染会把源文本发送到该主机。
   * - 查看器行为
     - ``--no-open`` 是稳定脚本写法。
     - 只有打开查看器本身也是需求时，才使用 ``--strict-open``。
     - CI、``PYFCSTM_NO_GUI`` 和缺失显示变量都可能跳过普通 ``--open``。

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
     - 未知键会在 CLI 配置边界被拒绝，并给出支持键列表；接近的拼写还会给出建议。
   * - 无效值
     - ``-c max_depth=abc``
     - 命令失败
     - 类型解析会报告出错的键。

命令行例子：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -c show_events=true -c max_depth=2
   pyfcstm plantuml -i machine.fcstm -c state_name_format=extra_name,name
   pyfcstm plantuml -i machine.fcstm -c 'variable_legend_position=bottom right'

Python API（应用程序接口）例子：

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
