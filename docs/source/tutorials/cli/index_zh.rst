PyFCSTM 命令行界面指南
===============================================

pyfcstm 是一个强大的状态机 DSL 工具，提供命令行界面用于解析、可视化和从层次化有限状态机生成代码。

文档中最常用的几个命令是：

- ``pyfcstm plantuml``：生成原始 PlantUML 文本
- ``pyfcstm visualize``：直接渲染最终图像文件
- ``pyfcstm inspect``：输出结构化模型和诊断 JSON
- ``pyfcstm generate``：基于模板生成源码

安装
---------------------------------------

安装方式
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. pip 安装**\ （推荐）：

.. code-block:: bash

   pip install pyfcstm

安装后，可以直接使用 ``pyfcstm`` 命令。

**2. 模块执行**：

.. code-block:: bash

   python -m pyfcstm

**3. 预编译可执行文件**：

从 GitHub Releases 下载预编译版本：
https://github.com/HansBug/pyfcstm/releases

验证安装
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

检查已安装的版本：

.. literalinclude:: version_check.demo.sh
   :language: bash

输出：

.. literalinclude:: version_check.demo.sh.txt
   :language: text

获取帮助
---------------------

CLI 为所有命令提供全面的帮助信息：

.. literalinclude:: help_example.demo.sh
   :language: bash

这将显示：

.. literalinclude:: help_example.demo.sh.txt
   :language: text

命令参考
-------------------------------------

plantuml 命令
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

将状态机 DSL 代码转换为 PlantUML 格式以进行可视化。

**语法**：

.. code-block:: bash

   pyfcstm plantuml -i <输入文件> [-o <输出文件>]

**参数**：

- ``-i, --input-code``：输入状态机 DSL 文件的路径（必需）
- ``-o, --output``：输出 PlantUML 文件的路径（可选，如果未指定则输出到标准输出）

**示例 1：简单状态机**

让我们从一个简单的状态机开始：

.. literalinclude:: simple_machine.fcstm
   :language: fcstm
   :caption: simple_machine.fcstm

生成 PlantUML 图表：

.. code-block:: bash

   pyfcstm plantuml -i simple_machine.fcstm -o simple_machine.puml

生成的 PlantUML 文件可以使用以下方式渲染：

- **在线**：访问 https://www.plantuml.com/plantuml/uml/ 并粘贴代码
- **本地**：安装 PlantUML（https://plantuml.com/）并运行：

  .. code-block:: bash

     plantuml simple_machine.puml

**生成的状态图**：

.. image:: simple_machine.fcstm.puml.svg
   :alt: 简单状态机状态图
   :align: center

**示例 2：文件下载管理器**

这是一个更复杂的示例，包含层次化状态、重试逻辑和错误处理：

.. literalinclude:: file_download.fcstm
   :language: fcstm
   :caption: file_download.fcstm

此示例演示了：

- **层次化状态**：``Downloading`` 包含嵌套子状态（``Connecting``、``Transferring``、``Paused``）
- **重试逻辑**：发生错误时自动重试并跟踪计数器
- **守卫条件**：``Downloading -> Retrying : if [error_code != 0 && retry_count < 3]`` 带复杂条件逻辑
- **生命周期动作**：``enter`` 和 ``during`` 动作用于状态初始化和持续处理
- **强制转换**：``!* -> Failed :: CriticalError`` 从所有子状态创建紧急退出路径
- **进度跟踪**：变量跟踪下载进度、数据大小和错误状态

生成图表：

.. code-block:: bash

   pyfcstm plantuml -i file_download.fcstm -o file_download.puml

**生成的状态图**：

.. image:: file_download.fcstm.puml.svg
   :alt: 文件下载管理器状态图
   :align: center
   :width: 100%

**输出到控制台**

您也可以直接将 PlantUML 输出到控制台以进行快速检查：

.. code-block:: bash

   pyfcstm plantuml -i simple_machine.fcstm

这对以下场景很有用：

- 快速验证 DSL 语法
- 将输出传递给其他工具
- 与 CI/CD 流水线集成

inspect 命令
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

检查状态机 DSL 文件，并以 JSON 输出结构化模型报告。JSON 结构与
``inspect_model(model).to_json()`` 一致，包含状态、转换、变量、指标、
派生图和诊断信息。当模型使用组合 transition trigger 时，报告还会暴露
``combo_transitions`` 和 ``combo_origins``\ ，方便工具把生成的伪状态链边映射回原始 trigger 项。

对于组合 trigger 诊断，``inspect``\ 会把公开 warning code 对应回原始组合项，而不是生成的伪状态：

- ``W_COMBO_DUPLICATE_EVENT``\ ：同一个事件在一个组合 trigger 中出现多次。诊断 ``span``\ 指向重复项，``refs.first_term_span``\ 指向第一次出现的位置。
- ``W_COMBO_GUARD_CONST_TRUE``\ / ``W_COMBO_GUARD_CONST_FALSE``\ ：Python 侧基于 Z3 的分析证明某个组合守卫恒真或恒假。诊断 ``span``\ 指向带方括号的守卫项，``refs.value_span``\ 指向方括号内部表达式。
- ``W_COMBO_GUARD_PREFIX_IMPLIED``\ / ``W_COMBO_GUARD_PREFIX_CONTRADICTS``\ ：前置守卫前缀已经蕴含当前守卫，或使当前守卫不可能成立。诊断 ``span``\ 指向当前守卫，``refs.prior_term_span``\ 指向起决定作用的更早守卫。

所有组合 warning 的 ``refs``\ 都包含 ``origin_id``\ 、``term_index``\ 、``transition_span``\ 、``trigger_span``\ 和相关 term span，方便编辑器和 UI 集成把提示映射回用户手写 DSL 区间。求解器支撑的守卫 warning 是 Python ``inspect``\ 诊断；JavaScript 侧工具应消费这份 JSON 诊断，而不是重新实现本地求解器近似逻辑。

**语法**：

.. code-block:: bash

   pyfcstm inspect -i <输入文件> [-o <输出文件>] [--enable-verify] \
     [--max-complexity-tier structural|smt_linear|smt_nonlinear_decidable|smt_undecidable_heuristic] \
     [--max-call-count-scaling linear_in_transitions] [--smt-timeout-ms <毫秒>]

**参数**：

- ``-i, --input-code``：输入状态机 DSL 文件路径（必需）
- ``-o, --output``：输出 JSON 文件路径（可选，未指定时输出到标准输出）
- ``--enable-verify``：运行可由 ``inspect`` 自动接入的 ``pyfcstm.verify`` 算法，并追加其诊断
- ``--max-complexity-tier``：``inspect`` 允许的最高验证复杂度层级，默认是 ``structural``
- ``--max-call-count-scaling``：``inspect`` 允许的最高调用次数增长等级，默认是 ``linear_in_transitions``
- ``--smt-timeout-ms``：透传给 SMT 本地验证算法的可选超时时间；``0`` 会原样透传，并遵循 Z3 语义，表示不设置有限超时

**默认 JSON 输出**

.. code-block:: bash

   pyfcstm inspect -i simple_machine.fcstm -o simple_machine.inspect.json

默认情况下，``inspect`` 不运行 verify 支撑的检查。这保持了 CLI 与
``inspect_model(model)`` 的默认诊断契约一致。

**显式启用 verify 支撑的诊断**

.. code-block:: bash

   pyfcstm inspect -i simple_machine.fcstm \
     --enable-verify --max-complexity-tier smt_linear --smt-timeout-ms 1000

自动 ``inspect`` 路径仍会拒绝 ``bmc_search``，因为 BMC 需要显式查询深度，
不是有界的本地诊断遍历。它也会拒绝 ``k_unrollings`` 和
``k_unrollings_times_branching`` 调用次数策略。CLI 会解析这些值并返回受控的
策略错误，而不是让它们静默进入自动检查流程。

visualize 命令
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

直接将状态机 DSL 文件渲染为最终图像或 PDF，并可选择使用系统默认查看器打开结果文件。

与 ``plantuml`` 命令的区别：

- ``pyfcstm plantuml`` 输出 PlantUML 源文本，更适合检查、版本管理或交给外部 PlantUML 工具继续处理
- ``pyfcstm visualize`` 通过 ``plantumlcli`` 直接渲染最终产物，更适合本地预览和快速导出图片或 PDF

**语法**：

.. code-block:: bash

   pyfcstm visualize -i <输入文件> [-o <输出文件>] [-t png|svg|pdf] \
     [--renderer auto|local|remote] [--open/--no-open] [--check]

**参数**：

- ``-i, --input-code``：输入状态机 DSL 文件路径（除 ``--check`` 外必需）
- ``-o, --output``：渲染后输出文件路径（可选，未指定时写入缓存目录）
- ``-l, --level``：与 ``plantuml`` 共用的 PlantUML 详细级别预设（``minimal`` / ``normal`` / ``full``）
- ``-c, --config``：``key=value`` 格式的 PlantUML 配置覆盖项，可重复指定
- ``-t, --type``：渲染输出类型，可选 ``png``、``svg`` 或 ``pdf``
- ``--renderer``：后端选择，可选 ``auto``、``local`` 或 ``remote``
- ``--check``：只检查后端可用性，不执行渲染
- ``--open/--no-open``：开启或关闭渲染完成后的自动打开行为
- ``--strict-open``：将查看器启动失败视为错误
- ``-j, --java``：本地渲染器使用的 Java 可执行文件路径
- ``-p, --plantuml-jar``：本地渲染器使用的 PlantUML jar 路径，也可通过 ``PLANTUML_JAR`` 读取
- ``-r, --remote-host``：远端 PlantUML 服务地址，也可通过 ``PLANTUML_HOST`` 读取

**示例**：

.. code-block:: bash

   # 渲染 PNG，并在有图形界面时自动打开
   pyfcstm visualize -i simple_machine.fcstm

   # 导出 SVG，但不自动打开查看器
   pyfcstm visualize -i simple_machine.fcstm -t svg -o simple_machine.svg --no-open

   # 检查本地或远端渲染后端是否可用
   pyfcstm visualize --check --renderer auto

**渲染后端行为**

- ``auto`` 会先尝试本地 PlantUML 后端，失败后再回退到远端后端
- ``local`` 使用 Java 和 PlantUML jar 文件
- ``remote`` 使用 PlantUML 服务端，适合没有 Java 的机器

如果当前进程运行在 CI 等无图形界面的环境中，渲染仍然可以完成，但会跳过自动打开查看器。

``visualize`` 与 ``plantuml`` 共用同一套 ``-l/--level`` 和 ``-c/--config`` PlantUML 输出配置。完整配置项和效果示例请参见 :doc:`/tutorials/visualization/index_zh`。

generate 命令
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用可自定义的模板从状态机 DSL 生成可执行代码。

**语法**：

.. code-block:: bash

   pyfcstm generate -i <输入文件> -t <模板目录> -o <输出目录> [--clear]

**参数**：

- ``-i, --input-code``：输入状态机 DSL 文件的路径（必需）
- ``-t, --template-dir``：模板目录的路径（必需）
- ``-o, --output-dir``：生成代码的输出目录（必需）
- ``--clear``：生成前清空输出目录（可选）

**工作原理**

``generate`` 命令使用基于模板的代码生成系统：

1. **解析 DSL**：读取并解析 ``.fcstm`` 文件到内部模型
2. **加载模板**：从模板目录读取 Jinja2 模板
3. **渲染代码**：使用状态机模型作为上下文处理模板
4. **输出文件**：将生成的代码写入输出目录

**模板结构**

模板目录必须包含：

- ``config.yaml``：配置文件，定义表达式样式、过滤器和全局变量
- ``*.j2``：用于代码生成的 Jinja2 模板文件
- 静态文件：直接复制到输出（保留目录结构）

**示例：生成 C 代码**

.. code-block:: bash

   # 从交通灯状态机生成 C 代码
   pyfcstm generate -i traffic_light.fcstm -t ./templates/c -o ./output

   # 生成前清空输出目录
   pyfcstm generate -i traffic_light.fcstm -t ./templates/c -o ./output --clear

**示例：生成 Python 代码**

.. code-block:: bash

   # 生成 Python 代码
   pyfcstm generate -i simple_machine.fcstm -t ./templates/python -o ./output

**示例：从多文件 import 工程生成代码**

当 DSL 工程开始使用 import 后，对外 CLI 用法并不会变化。您仍然只需要
给出一个入口文件，pyfcstm 会自动装配它导入的其他模块。

.. code-block:: bash

   # 入口文件可以 import 其他 FCSTM 文件，或 import 一个带 main.fcstm 的目录
   pyfcstm generate -i ./docs/source/tutorials/dsl/import_host_directory.fcstm \
     -t ./templates/python -o ./output --clear

**模板上下文**

模板可以访问完整的状态机模型：

- ``model``：根状态机对象
- ``model.variables``：变量定义
- ``model.walk_states()``：遍历所有状态的迭代器
- ``state.name``、``state.is_leaf_state``、``state.transitions``
- ``transition.from_state``、``transition.to_state``、``transition.guard``

**表达式渲染**

使用 ``expr_render`` 过滤器将 DSL 表达式转换为目标语言语法：

.. code-block:: jinja

   // C 风格表达式
   {{ expr | expr_render(style='c') }}

   # Python 风格表达式
   {{ expr | expr_render(style='python') }}

常见用例
-------------------------------------

工作流 1：DSL 到图表
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

可视化您的状态机设计：

.. code-block:: bash

   # 1. 编写状态机 DSL
   vim my_machine.fcstm

   # 2. 直接渲染预览图
   pyfcstm visualize -i my_machine.fcstm -t svg -o my_machine.svg --no-open

   # 3. 如果需要 PlantUML 源文本，再单独生成 .puml
   pyfcstm plantuml -i my_machine.fcstm -o my_machine.puml

对于多文件状态机，同样沿用这一工作流：

.. code-block:: bash

   pyfcstm plantuml -i ./docs/source/tutorials/dsl/import_host_mapped.fcstm \
     -o import_host_mapped.puml

工作流 2：DSL 到代码
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

为嵌入式系统生成可执行代码：

.. code-block:: bash

   # 1. 设计状态机
   vim controller.fcstm

   # 2. 生成 C 代码
   pyfcstm generate -i controller.fcstm -t ./templates/c -o ./src/generated --clear

   # 3. 与项目集成
   make build

工作流 3：验证和测试
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在提交前验证 DSL 语法和结构化诊断：

.. code-block:: bash

   # 快速语法检查，并输出结构化诊断
   pyfcstm inspect -i machine.fcstm -o machine.inspect.json

   # 在可接受 SMT 检查成本的 CI 中，显式启用 verify 支撑的诊断
   pyfcstm inspect -i machine.fcstm --enable-verify \
     --max-complexity-tier smt_linear --smt-timeout-ms 1000 \
     -o machine.verify.inspect.json

   # 生成测试代码
   pyfcstm generate -i machine.fcstm -t ./templates/test -o ./tests/generated

对于 import 工程，只需要检查入口文件：

.. code-block:: bash

   pyfcstm inspect -i ./docs/source/tutorials/dsl/import_host_directory.fcstm \
     -o import_project.inspect.json

工作流 4：CI/CD 集成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在构建流水线中自动化代码生成：

.. code-block:: bash

   #!/bin/bash
   # build.sh

   # 验证所有 DSL 文件
   for file in src/machines/*.fcstm; do
       echo "验证 $file..."
       pyfcstm plantuml -i "$file" > /dev/null || exit 1
   done

   # 生成代码
   pyfcstm generate -i src/machines/main.fcstm -t templates/ -o generated/ --clear

   # 构建项目
   make all

最佳实践
-------------------------------------

DSL 文件组织
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 使用描述性文件名：``traffic_light.fcstm``、``user_auth.fcstm``
- 将相关状态机保存在专用目录中：``src/machines/``
- 将 ``.fcstm`` 文件与代码一起进行版本控制

模板管理
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 为每种目标语言维护单独的模板目录
- 使用 ``config.yaml`` 定义特定于语言的表达式样式
- 在生产使用前使用示例状态机测试模板

代码生成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 在自动化构建中始终使用 ``--clear`` 标志以确保干净的输出
- 在提交前审查生成的代码（如果重新生成则添加到 ``.gitignore``）
- 记录哪些 DSL 文件生成哪些输出文件
