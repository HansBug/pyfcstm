FCSTM 可视化指南
===============================================

本指南全面介绍如何可视化 FCSTM DSL 定义的有限状态机。你将学习如何使用 Python 代码和命令行界面生成 PlantUML 图表，以及如何使用灵活的配置系统自定义可视化输出。

概述
---------------------------------------

pyfcstm 提供两种主要的状态机可视化方法：

1. **Python API**：通过 ``PlantUMLOptions`` 类进行编程控制
2. **命令行界面**：使用灵活的配置选项快速可视化

两种方法都支持相同的综合配置系统，允许你控制生成的 PlantUML 图表的各个方面。

示例状态机
---------------------------------------

在本指南中，我们将使用以下示例状态机来演示所有可视化功能：

.. literalinclude:: example.fcstm
   :language: fcstm
   :caption: example.fcstm

这个状态机演示了 FCSTM 的关键特性：

- **变量**：``counter`` 和 ``error_count`` 用于状态跟踪
- **层次化状态**：``Active`` 包含嵌套的 ``Processing`` 和 ``Waiting`` 状态
- **生命周期动作**：``enter`` 和 ``during`` 动作定义状态行为
- **切面动作**：``>> during before`` 应用于所有后代状态
- **抽象动作**：``GlobalMonitor`` 必须在生成的代码中实现
- **带守卫的转换**：``Active -> Error : if [counter > 100]``
- **带效果的转换**：``Active -> Idle :: Stop effect { counter = 0; }``
- **强制转换**：``!* -> Error :: FatalError`` 从所有状态触发

**可视化效果**

以下是使用默认设置可视化该状态机的效果：

.. figure:: example.fcstm.puml.svg
   :alt: 示例状态机可视化
   :align: center
   :width: 100%

   示例状态机的默认可视化效果

可视化方法
---------------------------------------

Python API 可视化
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python API 通过 ``PlantUMLOptions`` 类提供对可视化的编程控制。

**基本用法**

.. literalinclude:: python_basic.demo.py
   :language: python
   :caption: 基本 Python 可视化

输出：

.. literalinclude:: python_basic.demo.py.txt
   :language: text

**使用自定义选项**

.. literalinclude:: python_options.demo.py
   :language: python
   :caption: 使用 PlantUMLOptions 的 Python 可视化

输出：

.. literalinclude:: python_options.demo.py.txt
   :language: text

CLI 可视化
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

命令行界面提供快速访问可视化功能，配置灵活。

**基本用法**

.. literalinclude:: cli_basic.demo.sh
   :language: bash
   :caption: 基本 CLI 可视化

输出：

.. literalinclude:: cli_basic.demo.sh.txt
   :language: text

配置系统
---------------------------------------

可视化系统通过 ``PlantUMLOptions`` 提供全面的配置。所有选项在 Python API 和 CLI 中都可用。

详细级别预设
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

详细级别预设为常见用例提供快速配置：

- **minimal**：最小细节的基本结构
- **normal**：包含基本信息的平衡视图（默认）
- **full**：包括所有动作和事件的完整细节

**Python API**

.. literalinclude:: python_detail_levels.demo.py
   :language: python
   :caption: Python 中的详细级别

输出：

.. literalinclude:: python_detail_levels.demo.py.txt
   :language: text

**CLI**

.. literalinclude:: cli_level.demo.sh
   :language: bash
   :caption: CLI 中的详细级别

输出：

.. literalinclude:: cli_level.demo.sh.txt
   :language: text

变量显示选项
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

控制状态机变量在图表中的显示方式。

**配置选项**

- ``show_variable_definitions`` (bool)：在顶部显示变量定义
- ``variable_display_mode`` (str)：显示模式 - ``'none'``、``'note'`` 或 ``'legend'``

**示例**

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   # 将变量显示为图例
   options = PlantUMLOptions(
       show_variable_definitions=True,
       variable_display_mode='legend'
   )

**CLI 等效命令**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c show_variable_definitions=true \
     -c variable_display_mode=legend \
     -o output.puml

状态名称格式化
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

自定义状态名称在图表中的显示方式。

**配置选项**

- ``state_name_format`` (tuple[str, ...])：格式组件 - ``'name'``、``'path'``、``'relpath'``
- ``show_pseudo_state_style`` (bool)：对伪状态应用特殊样式
- ``collapse_empty_states`` (bool)：折叠没有动作或子状态的状态

**示例**

.. code-block:: python

   # 同时显示名称和完整路径
   options = PlantUMLOptions(
       state_name_format=('name', 'path'),
       show_pseudo_state_style=True,
       collapse_empty_states=False
   )

**CLI 等效命令**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c state_name_format=name,path \
     -c show_pseudo_state_style=true \
     -c collapse_empty_states=false \
     -o output.puml

生命周期动作显示
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

控制在图表中显示哪些生命周期动作（enter、during、exit）。

**配置选项**

- ``show_lifecycle_actions`` (bool)：所有生命周期动作的主开关
- ``show_enter_actions`` (bool)：显示 enter 动作
- ``show_during_actions`` (bool)：显示 during 动作
- ``show_exit_actions`` (bool)：显示 exit 动作
- ``show_aspect_actions`` (bool)：显示切面动作（``>> during before/after``）
- ``show_abstract_actions`` (bool)：显示抽象动作声明
- ``show_concrete_actions`` (bool)：显示具体动作实现
- ``abstract_action_marker`` (str)：抽象动作的标记（默认：``'«abstract»'``）
- ``max_action_lines`` (int)：每个动作块显示的最大行数

**示例**

.. code-block:: python

   # 仅显示 enter 和 during 动作，隐藏 exit 动作
   options = PlantUMLOptions(
       show_lifecycle_actions=True,
       show_enter_actions=True,
       show_during_actions=True,
       show_exit_actions=False,
       show_abstract_actions=True,
       max_action_lines=10
   )

**CLI 等效命令**

.. literalinclude:: cli_config.demo.sh
   :language: bash
   :caption: 生命周期动作配置

输出：

.. literalinclude:: cli_config.demo.sh.txt
   :language: text

转换显示选项
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

控制转换在图表中的显示方式。

**配置选项**

- ``show_transition_guards`` (bool)：在转换上显示守卫条件
- ``show_transition_effects`` (bool)：在转换上显示效果块
- ``transition_effect_mode`` (str)：如何显示效果 - ``'note'`` 或 ``'inline'``

**示例**

.. code-block:: python

   # 将守卫和效果显示为注释
   options = PlantUMLOptions(
       show_transition_guards=True,
       show_transition_effects=True,
       transition_effect_mode='note'
   )

**CLI 等效命令**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c show_transition_guards=true \
     -c show_transition_effects=true \
     -c transition_effect_mode=note \
     -o output.puml

事件可视化
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

控制事件在图表中的显示方式。

**配置选项**

- ``show_events`` (bool)：在转换上显示事件名称
- ``event_name_format`` (tuple[str, ...])：格式组件 - ``'name'``、``'path'``、``'relpath'``
- ``event_visualization_mode`` (str)：可视化模式 - ``'none'``、``'label'``、``'color'`` 或 ``'both'``

**示例**

.. code-block:: python

   # 使用颜色编码显示事件
   options = PlantUMLOptions(
       show_events=True,
       event_name_format=('name', 'relpath'),
       event_visualization_mode='color'
   )

**CLI 等效命令**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c show_events=true \
     -c event_name_format=name,relpath \
     -c event_visualization_mode=color \
     -o output.puml

深度控制
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

控制可视化深入嵌套状态的程度。

**配置选项**

- ``max_depth`` (int)：可视化的最大嵌套深度（0 = 无限制）
- ``collapsed_state_marker`` (str)：折叠状态的标记（默认：``'...'``）

**示例**

.. code-block:: python

   # 限制为 2 层嵌套
   options = PlantUMLOptions(
       max_depth=2,
       collapsed_state_marker='[collapsed]'
   )

**CLI 等效命令**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c max_depth=2 \
     -c collapsed_state_marker=[collapsed] \
     -o output.puml

PlantUML 样式
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

控制 PlantUML 特定的样式功能。

**配置选项**

- ``use_skinparam`` (bool)：使用 skinparam 进行样式设置（默认：True）
- ``use_stereotypes`` (bool)：使用构造型进行状态分类（默认：True）

**示例**

.. code-block:: python

   # 禁用 skinparam 和构造型
   options = PlantUMLOptions(
       use_skinparam=False,
       use_stereotypes=False
   )

**CLI 等效命令**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c use_skinparam=false \
     -c use_stereotypes=false \
     -o output.puml

高级配置
---------------------------------------

组合多个选项
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

你可以组合多个配置选项来创建高度自定义的可视化。

**Python API**

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   # 创建综合自定义配置
   options = PlantUMLOptions(
       detail_level='full',
       show_events=True,
       event_visualization_mode='both',
       show_lifecycle_actions=True,
       show_enter_actions=True,
       show_during_actions=True,
       show_exit_actions=True,
       show_abstract_actions=True,
       max_action_lines=10,
       state_name_format=('name', 'path'),
       event_name_format=('name', 'relpath'),
       max_depth=3,
       use_stereotypes=True,
       use_skinparam=True
   )

   plantuml_output = model.to_plantuml(options)

**CLI**

.. literalinclude:: cli_advanced.demo.sh
   :language: bash
   :caption: 高级 CLI 配置

输出：

.. literalinclude:: cli_advanced.demo.sh.txt
   :language: text

配置类型系统
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CLI 配置系统支持自动类型推断和显式类型提示：

**支持的类型**

- ``bool``：``true``/``false``、``yes``/``no``、``1``/``0``
- ``int``：整数值（例如 ``42``、``0xFF``、``0b1010``）
- ``float``：浮点数值（例如 ``3.14``、``2.5``）
- ``str``：字符串值（带引号或不带引号）
- ``tuple[T, ...]``：可变长度元组（例如 ``name,path``）
- ``tuple[T1, T2]``：具有特定类型的固定长度元组

**类型推断**

当没有提供类型提示时，CLI 会自动推断类型：

.. code-block:: bash

   # 推断为 int
   pyfcstm plantuml -i example.fcstm -c max_depth=3

   # 推断为 bool
   pyfcstm plantuml -i example.fcstm -c show_events=true

   # 推断为 tuple[str, ...]
   pyfcstm plantuml -i example.fcstm -c state_name_format=name,path

最佳实践
---------------------------------------

选择详细级别
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **minimal**：用于高层架构概览或向非技术利益相关者展示
- **normal**：用于一般文档和代码审查
- **full**：用于详细的实现文档或调试

优化图表可读性
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **从默认设置开始**：从默认设置开始，根据需要进行调整
2. **使用深度限制**：对于复杂的状态机，使用 ``max_depth`` 专注于特定层级
3. **隐藏不必要的细节**：禁用与你的用例无关的动作或事件
4. **使用事件可视化**：启用 ``event_visualization_mode='color'`` 以更好地跟踪事件
5. **折叠空状态**：启用 ``collapse_empty_states`` 以减少视觉混乱

性能考虑
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 大型状态机可能生成非常大的 PlantUML 文件
- 使用 ``max_depth`` 限制复杂性以进行初步探索
- 考虑为不同受众生成不同详细级别的多个图表

下一步
---------------------------------------

- 探索 :doc:`../cli/index_zh` 了解更多 CLI 功能
- 学习 :doc:`../dsl/index_zh` 创建你自己的状态机
- 查看 :doc:`../render/index` 了解从状态机生成代码

总结
---------------------------------------

本指南涵盖了：

- 两种可视化方法：Python API 和 CLI
- 使用 ``PlantUMLOptions`` 的综合配置系统
- 详细级别预设（minimal、normal、full）
- 对变量、状态、动作、转换和事件的细粒度控制
- 高级配置技术和最佳实践

灵活的配置系统允许你创建针对特定需求的可视化，从高层概览到详细的实现图表。
