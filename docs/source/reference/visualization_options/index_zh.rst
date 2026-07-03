.. _sec-reference-visualization-options-zh:

可视化选项参考
==============

``pyfcstm plantuml`` 和 ``pyfcstm visualize`` 共用 PlantUML 输出选项。CLI 使用 ``-l`` 选择详细级别预设，使用重复的 ``-c key=value`` 参数覆盖类型化选项。

详细级别预设
------------

.. list-table:: 详细级别预设
   :header-rows: 1

   * - 预设
     - 用途
   * - ``minimal``
     - 高层结构图，细节最少。
   * - ``normal``
     - 平衡视图，也是 CLI 默认值。
   * - ``full``
     - 更详细的实现视图，显示更多 actions、events、guards 和 effects。

CLI 示例：

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

常见选项组
----------

.. list-table:: PlantUML 选项组
   :header-rows: 1

   * - 选项
     - 值 / 类型
     - 含义
   * - ``show_variable_definitions``
     - bool
     - 显示变量定义。
   * - ``variable_display_mode``
     - ``note``、``legend``、``hide``
     - 变量显示方式。
   * - ``variable_legend_position``
     - 位置字符串
     - 变量使用 legend 模式时的图例位置。
   * - ``state_name_format``
     - ``name``、``extra_name``、``path`` 组成的 tuple
     - 状态 label 组成部分。
   * - ``show_pseudo_state_style``
     - bool
     - 应用 pseudo-state 样式。
   * - ``collapse_empty_states``
     - bool
     - 折叠没有可见内容的状态。
   * - ``show_lifecycle_actions``
     - bool
     - lifecycle-action 显示总开关。
   * - ``show_enter_actions`` / ``show_during_actions`` / ``show_exit_actions``
     - bool
     - 单独 lifecycle-action 开关。
   * - ``show_aspect_actions``
     - bool
     - 显示 ``>> during before/after`` aspect actions。
   * - ``show_transition_guards``
     - bool
     - 显示 transition guards。
   * - ``show_transition_effects``
     - bool
     - 显示 transition effect blocks。
   * - ``transition_effect_mode``
     - ``note``、``inline``、``hide``
     - effects 的显示方式。
   * - ``show_events``
     - bool
     - 在 transitions 上显示 event 名称。
   * - ``event_name_format``
     - ``name``、``extra_name``、``path``、``relpath`` 组成的 tuple
     - event label 组成部分。
   * - ``event_visualization_mode``
     - ``none``、``color``、``legend``、``both``、``dependency_view``
     - event 可视化模式；``dependency_view`` 保留给 dependency-view 输出。
   * - ``event_legend_position``
     - 位置字符串
     - event 图例位置。
   * - ``max_depth``
     - int
     - 最大展开嵌套深度。
   * - ``collapsed_state_marker``
     - str
     - 折叠状态标记。
   * - ``use_skinparam`` / ``use_stereotypes``
     - bool
     - PlantUML 样式开关。

CLI 类型语法
------------

* Boolean 值接受 ``true`` / ``false`` 等形式。
* Tuple 值使用逗号分隔，例如 ``-c state_name_format=name,path``。
* ``detail_level`` 使用 ``-l``，不要通过 ``-c`` 传入。
* 自定义颜色字典等 Python-only 对象值需要使用 Python API。

示例
----

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c event_visualization_mode=both \
     -o machine.events.puml

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_lifecycle_actions=true \
     -c show_exit_actions=false \
     -c max_depth=3 \
     -o machine.focused.puml
