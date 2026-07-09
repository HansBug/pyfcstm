.. _sec-explanations-architecture-zh:

架构解释
========

pyfcstm 围绕模型中心流水线组织。领域特定语言（DSL）文本先变成解析器节点，解析器节点再变成语义状态机模型，之后模型可以被模拟、
检查、在有界策略内验证、可视化，或渲染为目标语言代码。

本页中文术语约定：流水线（pipeline）、解析器（parser）、语义模型（semantic model）、诊断（diagnostics）、
验证（verification）、渲染器（renderer）、模板（template）、生成运行时（generated runtime）和证据边界（evidence boundary）
首次在这里对应英文；后文普通说明使用中文术语。模块路径、命令、DSL、AST、LLM 和文件格式保持原文。

主流水线
--------

.. figure:: structure.puml.svg
   :alt: pyfcstm 架构流水线
   :align: center

   仓库高层流水线。

关键设计选择是：大多数功能都汇聚到模型层。解析器不应该知道目标语言代码生成；模板不应该重新解析 DSL 文本；可视化不应该编造模型导入器没有产生的事实。

.. list-table:: 层级职责
   :header-rows: 1

   * - 层级
     - 代表路径
     - 负责
     - 不应负责
   * - DSL 解析
     - ``pyfcstm/dsl/grammar/``、``pyfcstm/dsl/parse.py``、``pyfcstm/dsl/listener.py``
     - 语法入口、解析错误、AST 节点构造。
     - 需要已解析模型上下文的语义验证。
   * - 模型导入和模型对象
     - ``pyfcstm/model/``
     - 状态、变量、转换、事件、生命周期动作、引用、PlantUML 导出、验证诊断。
     - 命令行展示或模板特定目标运行时行为。
   * - 模拟
     - ``pyfcstm/simulate/`` 和 ``pyfcstm/entry/simulate/``
     - 周期、事件、热启动、动作顺序和活跃状态轨迹的可执行参考语义。
     - 生成目标语言运行时的实现细节。
   * - 诊断和验证集成
     - ``pyfcstm/diagnostics/``、``pyfcstm/verify/``、``pyfcstm/solver/``
     - 结构化模型事实、诊断消息、有界验证检查、SMT 翻译。
     - 隐藏在日常 inspect 命令里的无界证明。
   * - 渲染和模板
     - ``pyfcstm/render/``、``templates/``、``pyfcstm/template/``
     - Jinja 环境、表达式/语句渲染、打包模板资产、生成产物。
     - 解析器语法或模拟器捷径。
   * - 命令行入口
     - ``pyfcstm/entry/``
     - 用户命令接线、选项解析、输出路由和命令特定错误边界。
     - 应属于模型、渲染、模拟或诊断模块的业务逻辑。
   * - 文档和大语言模型（LLM）资产
     - ``docs/``、``pyfcstm/llm/``
     - 用户指南、生成资源、面向提示词的语法指南、校验和纪律。
     - 未经代码或示例校验的运行时事实。

为什么模型是中心
----------------

DSL 有意保持紧凑，但语义需要解析：转换目标需要所属作用域，事件需要作用域规则，生命周期动作需要确定顺序，强制转换和组合转换会展开成普通模型事实。把这些解析放在模型层，可以让所有下游工具共享同一事实来源。

这避免三类常见漂移：

* 模拟器和模板各自解释 DSL 文本，导致行为不一致。
* 图表输出展示了模型导入器会拒绝的语法。
* inspect 报告和诊断描述的图，与代码生成消费的图不同。

命令流
------

公开命令行命令只是同一流水线上的薄编排层：

.. list-table:: 命令行流程
   :header-rows: 1

   * - 命令
     - 读取 DSL
     - 构建模型
     - 下游动作
     - 外部依赖边界
   * - ``simulate``
     - 是
     - 是
     - 运行 ``SimulationRuntime``。
     - 普通使用不需要。
   * - ``inspect``
     - 是
     - 是
     - 运行诊断和可选 inspect 范围内的验证检查。
     - SMT 工作受显式 inspect 策略选项约束。
   * - ``generate``
     - 是
     - 是
     - 使用内置或自定义模板运行 ``StateMachineCodeRenderer``。
     - 目标编译器不属于生成本身。
   * - ``plantuml``
     - 是
     - 是
     - 调用模型 PlantUML 导出并写源码文本。
     - 不需要渲染器。
   * - ``visualize``
     - 是，除 ``--check`` 外
     - 是，除 ``--check`` 外
     - 构造 PlantUML 源码，再通过 ``plantumlcli`` 渲染。
     - 可能需要 Java/jar 或远程 PlantUML 服务。

模板资产拆分
------------

内置模板有两个位置，原因不同：

* ``templates/`` 是维护者编辑的仓库源码。
* ``pyfcstm/template/`` 包含安装用户使用的打包 zip 资产和 ``index.json``。

``make tpl`` 从仓库源码刷新打包资产。测试和命令行路径验证内置模板时，应通过打包/公开表面进入，才能匹配用户行为。因此文档会区分维护者模板编辑和普通 ``pyfcstm generate --template python`` 使用。

诊断、验证和 inspect
--------------------

诊断和 inspect 输出暴露模型事实与可操作消息。它们足够详细，可以指导人类和 LLM 辅助修复，但边界明确：

* inspect 始终报告解析/模型事实和诊断。
* 可选验证集成必须显式开启，并受策略限制。
* 高成本或无界验证族不会被日常 inspect 命令偷偷运行。
* 诊断能指出可能原因和源码位置；它不能替代模拟、目标编译或生成运行时测试。

模拟和生成运行时
----------------

Python 模拟器是仓库一致性检查里的可执行参考语义。声明与模拟器一致的内置运行时模板，应与模拟器轨迹对齐测试，而不是只验证能编译。这为生命周期顺序、热启动、转换效果和活跃状态更新提供了具体契约。

生成目标运行时仍然有目标语言问题：应用程序接口形状、格式化稳定性、编译器/工具链行为，以及抽象动作的集成钩子。这些属于模板设计和测试，不属于解析器。

可视化边界
----------

PlantUML 导出属于模型，因为图表需要已解析模型事实。渲染属于命令行和可选运行环境，因为它依赖 Java、PlantUML jar、远程服务、文件后缀、缓存和桌面查看器行为。

这就是 ``plantuml`` 是源码导出命令，而 ``visualize`` 是渲染命令的原因。用户即使没有安装渲染后端，也能依赖源码导出。

生成资产边界
------------

仓库中有几类文件是生成物，不应直接手改：

* 语法输出目录下的 ANTLR 解析器输出。
* 模板源码变化后生成的打包模板 zip 资产和模板索引。
* 文档构建规则生成的图表、演示输出和笔记本结果文件。
* RST 生成器产生的应用程序接口参考文件。

安全模式始终是：编辑源文件，运行生成器，审阅差异，记录验证命令。

示例轨迹：同一个源码，多种证据
----------------------------------

以 quick-start 的 ``traffic_light.fcstm`` 为例。同一份源码可以生成多种产物，但每种产物证明的事情不同。

.. list-table:: 从源码到产物的轨迹
   :header-rows: 1

   * - 步骤
     - 组件边界
     - 示例命令或对象
     - 该证据证明什么
     - 不证明什么
   * - 解析文本。
     - ``pyfcstm.dsl``
     - ``pyfcstm inspect -i traffic_light.fcstm`` 首先解析文件。
     - 文件在语法上是合法 FCSTM。
     - 不证明目标运行时行为。
   * - 导入语义模型。
     - ``pyfcstm.model``
     - inspect 报告给出根 ``TrafficLight``，并统计 4 个状态 / 4 条转换。
     - 模型导入器接受了命名、层级、变量和转换。
     - 不渲染图片，也不编译生成代码。
   * - 执行参考语义。
     - ``pyfcstm.simulate``
     - ``pyfcstm simulate -i traffic_light.fcstm -e "current; cycle; current"``。
     - 冷启动和一个周期产生具体活跃状态轨迹。
     - 不证明所有生成目标模板都与模拟器一致。
   * - 检查结构化事实。
     - ``pyfcstm.diagnostics`` 和 inspect 适配层
     - ``pyfcstm inspect -i traffic_light.fcstm --format json``。
     - 指标和诊断可供脚本和大语言模型修复流程使用。
     - 不会偷偷运行无界验证。
   * - 导出图表源码。
     - ``model.to_plantuml``
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``。
     - 模型可以表示为确定性 PlantUML 源码。
     - 不证明渲染器已安装。
   * - 渲染图表。
     - ``pyfcstm visualize`` 加外部后端
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``。
     - 配置好的 PlantUML 后端可以把源码变成图片。
     - 不证明源码之外的模型语义正确。
   * - 生成运行时文件。
     - ``pyfcstm.render`` 和打包模板
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``。
     - 模板可以消费模型并写出目标文件。
     - 本身不证明生成运行时等价；等价声明由对齐测试负责。

命令边界轨迹
------------

同一个 ``traffic_light.fcstm`` 输入可以经过多条命令路径。这些路径彼此相关，但每条路径证明的边界不同。这也是文档把 CLI 配方、可视化配方和参考事实分开的原因。

.. list-table:: 从同一个输入文件出发的边界轨迹
   :header-rows: 1

   * - 步骤
     - 命令或 API 层
     - 产物
     - 该产物证明什么
     - 不证明什么
   * - 解析和导入
     - 命令入口调用 ``load_state_machine_from_file``
     - 内存中的语义模型
     - DSL 可以被解码、解析、作用域解析，并作为状态机通过校验。
     - 不证明任何渲染器、模板或外部工具已经安装。
   * - 检查事实
     - ``pyfcstm inspect -i traffic_light.fcstm``
     - human、JSON 或 LLM 定向报告
     - 诊断和指标描述 pyfcstm 看到的模型事实。
     - 不执行目标语言代码。
   * - 模拟行为
     - ``pyfcstm simulate -i traffic_light.fcstm -e "cycle; current"``
     - 模拟器转录
     - Python 模拟器可以执行所选周期路径。
     - 它本身不证明生成的 C/C++/Python 运行时一致。
   * - 导出图源码
     - ``pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml``
     - PlantUML 文本
     - 模型可以表示为文本图源码。
     - 不证明 Java、PlantUML、远程渲染或视觉可读性。
   * - 渲染图
     - ``pyfcstm visualize -i traffic_light.fcstm -t svg -o traffic_light.svg --no-open``
     - SVG、PNG 或 PDF 产物
     - 所选渲染后端能把 PlantUML 源变成产物。
     - 不证明所选细节级别是最清楚的解释；这由视觉审查负责。
   * - 生成运行时文件
     - ``pyfcstm generate -i traffic_light.fcstm --template python -o generated/python --clear``
     - 生成运行时目录树
     - 打包模板可以消费模型并写出目标文件。
     - 不证明原生工具链或下游集成测试已经运行。

后续边界失败时，不应靠猜测去改更早的层。例如，远程 PlantUML 服务中断是可视化环境问题，不是 DSL 解析器问题。反过来，模型校验错误应先在 DSL/模型路径修复，再重试模板或渲染器。

保持边界诚实的反例
~~~~~~~~~~~~~~~~~~

* ``plantuml`` 成功只证明源码导出；没有 Java、没有 PlantUML jar、没有网络渲染器时也可以成功。
* ``visualize`` 成功证明本次渲染器可用，但远程模式可能把 PlantUML 源码发送到本机之外。
* ``generate`` 成功证明渲染完成，不证明 C/C++ 编译器已安装，也不证明原生可执行文件已测试。
* 干净的 inspect 报告能帮助人类和大语言模型修复，但不是所有运行路径都被探索过的承诺。

图示证据审查
~~~~~~~~~~~~

上方架构图在本次 PR-Q 加厚中从 ``structure.puml`` 重新生成。它只用于证明三件事：

1. 所有面向命令的功能共享语义模型边界；
2. PlantUML 源码导出和图片渲染是两层；
3. 源模板和打包模板有不同维护角色。

它不是应用程序接口地图，也不能替代自动生成的应用程序接口参考。修改此图时，应重新生成 SVG/PNG，并检查 HTML 渲染结果，确保文档宽度下标签仍然可读。


后续阅读
--------

* 语法和含义：:doc:`../dsl_semantics/index_zh`
* 运行时顺序：:doc:`../execution_semantics/index_zh`
* 诊断边界：:doc:`../diagnostics/index_zh`
* 模板设计：:doc:`../template_rendering/index_zh`
* 语法和编辑器耦合：:doc:`../grammar_tooling/index_zh`
