PyFCSTM 命令行界面指南
===============================================

pyfcstm 是一个强大的状态机 DSL 工具，提供命令行界面用于解析、可视化和从层次化有限状态机生成代码。

文档中最常用的几个命令是：

- ``pyfcstm simulate``：运行交互式或批处理仿真器
- ``pyfcstm plantuml``：生成原始 PlantUML 文本
- ``pyfcstm visualize``：直接渲染最终图像文件
- ``pyfcstm inspect``：默认输出人类可读诊断，也可通过 ``--format json`` 显式输出结构化 JSON
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

.. code-block:: bash

   pyfcstm --version

安装成功时会打印包版本和维护者信息。

获取帮助
---------------------

CLI 会为顶层命令和每个子命令提供简洁帮助：

.. code-block:: bash

   pyfcstm --help
   pyfcstm simulate --help
   pyfcstm plantuml --help
   pyfcstm generate --help
   pyfcstm visualize --help

在编写脚本时，请以子命令帮助中的选项名为准。下面的示例只保留稳定、短小的命令形态；如果需要完整命令转录，docs 资源构建会刷新对应 demo 输出。

命令参考
-------------------------------------


simulate 命令
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

直接从 DSL 文件运行状态机。交互模式适合手动探索；``-e`` 可以传入分号分隔的命令链，适合可复现示例和脚本。

**语法**：

.. code-block:: bash

   pyfcstm simulate -i <输入文件> [-e "current; cycle Start; current"] [--no-color]

**参数**：

- ``-i, --input-code``：输入状态机 DSL 文件路径（必需）
- ``-e, --execute``：执行批处理命令后退出
- ``--no-color``：禁用 ANSI 彩色输出

**示例**：

.. code-block:: bash

   # 启动交互式 REPL
   pyfcstm simulate -i simple_machine.fcstm

   # 运行一小段批处理命令链
   pyfcstm simulate -i simple_machine.fcstm -e "current; cycle; current"

完整运行时教程请参见 :doc:`/tutorials/simulation/index_zh`。

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

检查状态机 DSL 文件。该命令默认输出人类可读报告；需要机器可读报告时，应显式使用 ``--format``。本页只保留短命令参考；完整诊断教程请见 :doc:`/tutorials/inspect/index_zh`。

**语法**：

.. code-block:: bash

   pyfcstm inspect -i <输入文件> [-o <输出文件>] [--format human|json|llm-json|llm-md] \
     [--color auto|always|never] [--enable-verify]

**常用示例**：

.. code-block:: bash

   # 人类可读诊断
   pyfcstm inspect -i simple_machine.fcstm

   # 面向 CI 或编辑器工具的完整结构化报告
   pyfcstm inspect -i simple_machine.fcstm --format json -o simple_machine.inspect.json

   # 面向 LLM 修复上下文的报告
   pyfcstm inspect -i simple_machine.fcstm --format llm-md -o simple_machine.inspect.md

``-o`` 只改变输出位置；脚本需要 JSON 时请传入 ``--format json``。``--color`` 只影响 human 输出。需要 verify 支撑诊断时显式开启 ``--enable-verify``，并遵守 inspect policy 的成本边界。

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

从状态机 DSL 生成可执行代码。对打包内置模板，优先使用 ``--template``：

.. code-block:: bash

   pyfcstm generate -i <输入文件> --template <python|c|c_poll|cpp|cpp_poll> \
     -o <输出目录> [--clear]

只有在你明确提供自定义模板目录时，才使用 ``-t/--template-dir``：

.. code-block:: bash

   pyfcstm generate -i <输入文件> -t <自定义模板目录> -o <输出目录>

**参数**：

- ``-i, --input-code``：输入状态机 DSL 文件路径（必需）
- ``--template``：打包内置模板名称
- ``-t, --template-dir``：自定义模板目录路径
- ``-o, --output-dir``：生成代码输出目录（必需）
- ``--clear``：生成前清空输出目录（可选）

**内置模板示例**：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o ./output --clear

**自定义模板目录示例**：

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm -t ./my_template -o ./output

完整内置模板教程见 :doc:`/tutorials/generation/index_zh`。模板作者细节仍然放在 :doc:`/tutorials/render/index_zh`。

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

   # 2. 从打包内置模板生成 C 代码
   pyfcstm generate -i controller.fcstm --template c -o ./src/generated --clear

   # 3. 与项目集成
   make build

工作流 3：验证和测试
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在提交前验证 DSL 语法和结构化诊断：

.. code-block:: bash

   # 快速语法检查，并输出人类可读诊断
   pyfcstm inspect -i machine.fcstm

   # 面向 CI artifact 或编辑器工具的完整结构化 JSON
   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

   # 在可接受 SMT 检查成本的 CI 中，显式启用 verify 支撑的诊断
   pyfcstm inspect -i machine.fcstm --format json --enable-verify \
     --max-complexity-tier smt_linear --smt-timeout-ms 1000 \
     -o machine.verify.inspect.json

   # 当项目维护自己的测试模板目录时，从自定义模板生成测试代码
   pyfcstm generate -i machine.fcstm -t ./my_test_template -o ./tests/generated

对于 import 工程，只需要检查入口文件：

.. code-block:: bash

   pyfcstm inspect -i ./docs/source/tutorials/dsl/import_host_directory.fcstm \
     --format json -o import_project.inspect.json

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

   # 从打包内置模板生成代码
   pyfcstm generate -i src/machines/main.fcstm --template python -o generated/ --clear

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
