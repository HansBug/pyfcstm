PyFCSTM 命令行界面指南
===============================================

pyfcstm 是一个强大的状态机 DSL 工具，提供命令行界面用于解析、可视化和从层次化有限状态机生成代码。

安装
---------------------------------------

安装方式
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. pip 安装**（推荐）：

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

   # 2. 生成 PlantUML
   pyfcstm plantuml -i my_machine.fcstm -o my_machine.puml

   # 3. 渲染图表（在线或本地）
   plantuml my_machine.puml

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

在提交前验证 DSL 语法：

.. code-block:: bash

   # 快速语法检查（生成 PlantUML）
   pyfcstm plantuml -i machine.fcstm > /dev/null && echo "语法正确"

   # 生成测试代码
   pyfcstm generate -i machine.fcstm -t ./templates/test -o ./tests/generated

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
