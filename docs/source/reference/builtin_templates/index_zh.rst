.. _sec-reference-builtin-templates-zh:

内置模板参考
============

这些名称用于 ``pyfcstm generate --template <name>``。不要把仓库 ``templates/`` 路径当成普通内置模板入口；那是维护者源码。

当前所有内置模板（built-in template）都在打包元数据中标记为 ``experimental: true``。在本参考里，**实验状态** 表示生成输出具有当前仓库测试和冒烟证据，但它不是生产认证或所有平台保证。

.. template-ref-meta: name=python title=Python language=python archive=python.zip root_dir=python experimental=true description="Native Python built-in template with embedded runtime logic."
.. template-ref-meta: name=c title=C99 language=c archive=c.zip root_dir=c experimental=true description="Native C99 built-in template with embedded runtime logic and abstract hook callbacks."
.. template-ref-meta: name=c_poll title="C Poll" language=c archive=c_poll.zip root_dir=c_poll experimental=true description="Native C99 / C++98 built-in template with hook-polled events and embedded runtime logic."
.. template-ref-meta: name=cpp title="C++ Wrapper" language=cpp archive=cpp.zip root_dir=cpp experimental=true description="Early-stage first-class C++ template that reuses the C99 runtime core and emits C++ wrapper files."
.. template-ref-meta: name=cpp_poll title="C++ Poll Wrapper" language=cpp archive=cpp_poll.zip root_dir=cpp_poll experimental=true description="Early-stage first-class C++ poll template that reuses the C poll runtime core and emits C++ wrapper files."

.. template-ref-contract: name=python generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=c generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=c_poll generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=cpp generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status
.. template-ref-contract: name=cpp_poll generated_files entry_point event_model extension_point lifecycle target_boundary evidence_boundary generated_readme experimental_status

.. template-ref-profile: name=python event_input=cycle_events wrapper=false core=python native_evidence=false semantic_alignment=true formatter=ruff poll=false
.. template-ref-profile: name=c event_input=explicit_event_ids wrapper=false core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=false
.. template-ref-profile: name=c_poll event_input=event_checks wrapper=false core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=true
.. template-ref-profile: name=cpp event_input=explicit_event_ids wrapper=true core=c99 native_evidence=true semantic_alignment=true formatter=clang-format poll=false
.. template-ref-profile: name=cpp_poll event_input=event_checks wrapper=true core=c_poll native_evidence=true semantic_alignment=true formatter=clang-format poll=true

上面的隐藏 ``template-ref-profile`` 标记包含 ``core`` 值，它只供文档漂移检查使用。这个值是从生成文件和模板测试推导出的文档内部字段，不是 ``template.json`` 或 ``index.json`` 的公开元数据键。

元数据矩阵
----------

下表结合 ``pyfcstm/template/index.json`` 与 ``templates/<name>/template.json``。``archive`` 和 ``root_dir`` 来自打包索引；其余可见元数据由源码 ``template.json`` 镜像。

.. list-table:: 内置模板元数据
   :header-rows: 1

   * - 名称
     - 标题
     - 语言
     - 归档 / 根目录
     - 实验状态
     - 描述
   * - ``python``
     - Python
     - ``python``
     - ``python.zip`` / ``python``
     - ``true``
     - 嵌入运行时逻辑的原生 Python 内置模板。
   * - ``c``
     - C99
     - ``c``
     - ``c.zip`` / ``c``
     - ``true``
     - 带抽象钩子回调和嵌入运行时逻辑的 C99 内置模板。
   * - ``c_poll``
     - C Poll
     - ``c``
     - ``c_poll.zip`` / ``c_poll``
     - ``true``
     - 通过钩子轮询事件的 C99 / C++98 内置模板。
   * - ``cpp``
     - C++ Wrapper
     - ``cpp``
     - ``cpp.zip`` / ``cpp``
     - ``true``
     - 复用 C99 运行时核心的 C++ 包装层模板。
   * - ``cpp_poll``
     - C++ Poll Wrapper
     - ``cpp``
     - ``cpp_poll.zip`` / ``cpp_poll``
     - ``true``
     - 复用 C 轮询运行时核心的 C++ 包装层模板。

发现公开接口（API）
------------------------

``pyfcstm.template`` 中的公开包接口很小：

.. list-table:: 内置模板接口
   :header-rows: 1

   * - 函数
     - 用途
     - 边界
   * - ``list_templates()``
     - 按打包索引顺序返回已安装内置模板名。
     - 只用于发现；不渲染也不验证模型。
   * - ``has_template(name)``
     - 检查某个名称是否存在。
     - 如果包元数据缺失或无效，会抛出索引加载错误。
   * - ``get_template_info(name)``
     - 返回某个元数据条目的浅拷贝。
     - 未知名称抛出 ``LookupError``。
   * - ``extract_template(name, output_dir)``
     - 把打包归档解包成普通目录，供渲染器消费。
     - 开发检出中若归档不存在，可能复制仓库源码目录。

生成 README 契约
----------------

每个内置模板都会生成 ``README.md`` 和 ``README_zh.md``。这些文件由模型生成，应视为该生成机器的具体集成契约。它们提供本通用参考无法完全预知的名称和编号：类名、C 前缀、钩子名、事件编号、状态编号、热启动例子和目标构建片段。

模板契约
--------

``python``
~~~~~~~~~~

* 生成文件：``machine.py``、``README.md`` 和 ``README_zh.md``。
* 入口：从 ``machine.py`` 导入生成机器类。教程模型的类名是 ``SimpleMachineMachine``。
* 事件模型：``cycle(events=None)`` 接受无事件、一个事件字符串或事件字符串集合。
* 扩展点：继承生成类，覆写生成 README 中列出的受保护抽象钩子方法。
* 生命周期概念：构造、初始 ``cycle()``、后续 ``cycle(...)``、通过构造参数热启动、读取当前状态和变量快照。
* 目标边界：Python 3.7+ 标准库运行时；生成代码不应导入 ``pyfcstm``。
* 证据边界：Python 模板测试和语义对齐测试覆盖受支持生成行为；教程冒烟检查只是第一次成功信号。

``c``
~~~~~

* 生成文件：``machine.h``、``machine.c``、``README.md`` 和 ``README_zh.md``。
* 入口：include ``machine.h``，调用 ``..._init(...)``、``..._cycle(machine, event_ids, event_count)``、``..._vars(...)`` 和启用堆辅助时的 ``..._destroy(...)`` 等生成 C 函数。
* 事件模型：应用在每个周期把生成的整数事件编号传入运行时。
* 扩展点：安装抽象钩子表，回调签名由生成头文件和 README 描述。
* 生命周期概念：调用者持有或堆分配机器对象、初始化、热启动、周期、变量读取、状态读取和销毁。
* 目标边界：C99 核心、C++98 兼容头文件用法、默认只依赖标准库、整数变量使用固定宽度生成整数配置。
* 证据边界：本机冒烟和模板对齐检查是工具链证据，不是所有编译器或部署配置认证。

``c_poll``
~~~~~~~~~~

* 生成文件：``machine.h``、``machine.c``、``README.md`` 和 ``README_zh.md``。
* 入口：include ``machine.h``，初始化机器，安装钩子和完整 ``EventChecks`` 表，然后调用轮询周期接口。
* 事件模型：运行时在周期中调用已安装事件检查函数；不接收逐周期外部事件编号数组。
* 扩展点：抽象钩子使用 ``Hooks``；事件真值来自 ``EventChecks`` 回调。
* 生命周期概念：初始化、事件检查安装、热启动、周期、变量读取、状态读取和销毁。
* 目标边界：与 ``c`` 相同的 C 家族配置，并在公开接口中增加事件轮询。
* 证据边界：本机和对齐证据必须包含事件检查行为；回调结果应在单个周期中表现为只读探针。

``cpp``
~~~~~~~

* 生成文件：``machine.h``、``machine.c``、``machine.hpp``、``machine.cpp``、``README.md`` 和 ``README_zh.md``。
* 入口：include ``machine.hpp``，使用 ``pyfcstm_generated::<Machine>_cpp::MachineWrapper``。模板包含 C 核心，但 C++ 用户代码不应绕过包装层作为主集成面。
* 事件模型：包装层周期方法把生成事件编号提交给复用的 C 核心。
* 扩展点：包装层通过 C++ 别名暴露 C 钩子注册；运行时行为仍在生成 C 核心中。
* 生命周期概念：包装层构造、钩子注册、周期重载、变量/状态读取、按文档通过公开 C 核心热启动，以及包装层持有的初始化。
* 目标边界：C99 执行核心加 C++98 兼容、无异常、无 RTTI、无 STL 容器要求的包装层。
* 证据边界：C++ 冒烟测试必须走 ``machine.hpp`` / ``machine.cpp`` 包装层入口，即使最终可执行文件会链接生成 C 核心。

``cpp_poll``
~~~~~~~~~~~~

* 生成文件：``machine.h``、``machine.c``、``machine.hpp``、``machine.cpp``、``README.md`` 和 ``README_zh.md``。
* 入口：include ``machine.hpp``，构造 ``pyfcstm_generated::<Machine>_cpp::MachineWrapper``，安装包装层钩子和事件检查，然后调用 ``cycle()``。
* 事件模型：复用的 C 轮询核心调用已安装事件检查函数；C++ 包装层提供别名和设置方法。
* 扩展点：抽象钩子和事件检查都通过包装层接口安装。
* 生命周期概念：包装层构造、钩子/事件检查安装、周期、变量/状态读取、按文档通过底层公开接口热启动，以及包装层持有的初始化。
* 目标边界：C 轮询核心加 C++98 兼容包装层；不是完全独立的 C++ 运行时。
* 证据边界：冒烟和对齐测试必须覆盖包装层和轮询事件模型，而不只是复用的 C 核心。

目标配置说明
------------

C 家族模板在默认配置中使用固定宽度生成整数存储。因此数值部署警告适用于 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 目标。不要把它表述成 Python 生成运行时也有同样的固定宽度整数承载风险。

C++ 模板按设计复用 C 核心。``cpp`` 复用 C99 核心；``cpp_poll`` 复用 C 轮询核心。它们的 C++ 价值是包装层集成面，不是另一套执行语义实现。

选择与误用矩阵
--------------

.. list-table:: 选择矩阵
   :header-rows: 1

   * - 模板
     - 适合的第一用途
     - 应避免的误用
     - 第一验证
   * - ``python``
     - 应用或测试代码可以导入 Python 模块并调用 ``cycle``。
     - 把 Python 冒烟成功当成 C 家族整数存储或编译器行为证据。
     - 导入 ``machine.py``，按生成 README 运行短事件序列。
   * - ``c``
     - C 主机收集事件，并在每个周期提交生成事件编号。
     - 期待显式事件接口查询轮询回调。
     - 用 include ``machine.h`` 的驱动编译 ``machine.c`` 并提交编号。
   * - ``c_poll``
     - C 主机希望在周期中通过回调查询事件真值。
     - 留空某个 ``EventChecks`` 项，并假设所有集成形状都把缺失回调当作 false。
     - 编译并运行安装完整事件检查表的驱动。
   * - ``cpp``
     - C++ 主机希望使用包装层方法，同时接受生成 C 核心。
     - 把它称为完全独立的 C++ 运行时，或只测试 C 核心。
     - 编译 include ``machine.hpp`` 并使用包装层的消费者。
   * - ``cpp_poll``
     - C++ 主机希望使用包装层事件检查回调。
     - 把显式事件编号和轮询包装层混用，并期待二者接口等价。
     - 编译安装事件检查并调用 ``cycle()`` 的包装层消费者。

逐模板证据卡
------------

.. list-table:: 证据卡
   :header-rows: 1

   * - 模板
     - 事实源
     - 运行时证据
     - 边界证据
   * - ``python``
     - 包元数据、Python 模板配置、生成 README 模板、Python 模板测试。
     - 导入/周期冒烟，以及受支持 Python 生成运行时的模拟器对齐测试。
     - 没有本机编译器证明；生成代码应是自包含的 Python 标准库代码。
   * - ``c``
     - C 模板配置、``pyfcstm/render/c_runtime.py`` 中的 C 运行时辅助、生成 C README、本机测试。
     - C 编译器冒烟和显式事件编号的语义对齐覆盖。
     - 固定宽度整数配置和具体工具链证据必须可见。
   * - ``c_poll``
     - C 轮询模板配置、事件检查生成文件、C 运行时辅助事实。
     - 覆盖轮询回调的本机冒烟，以及轮询事件模型的对齐覆盖。
     - 轮询改变事件输入，不改变 FCSTM 生命周期语义。
   * - ``cpp``
     - C 核心模板事实，加包装层 ``machine.hpp`` / ``machine.cpp`` 模板。
     - C++ 包装层冒烟，而不仅是 C 核心编译成功。
     - 包装层集成面兼容 C++98，并复用生成 C 核心。
   * - ``cpp_poll``
     - C 轮询核心事实，加轮询包装层模板。
     - 通过包装层表面安装事件检查的包装层冒烟。
     - 不是独立 C++ 轮询运行时，而是 C 轮询核心加包装层。

通用例子形状
------------

具体名称来自模型。下面只是形状例子，实际符号必须读生成 README。

.. list-table:: 集成形状
   :header-rows: 1

   * - 模板
     - 形状例子
     - 生成 README 提供什么
   * - ``python``
     - ``from machine import <GeneratedMachine>; machine = <GeneratedMachine>(); machine.cycle()``
     - 类名、事件字符串、钩子方法名、状态和变量读取方式。
   * - ``c``
     - ``#include "machine.h"``，然后初始化机器对象，把事件编号数组传给生成周期函数。
     - C 前缀、类型名、事件编号、钩子表字段、初始化/周期/销毁名称。
   * - ``c_poll``
     - 初始化机器，安装钩子，安装 ``EventChecks``，调用轮询周期函数。
     - 事件检查表字段、回调签名、生命周期函数名。
   * - ``cpp``
     - ``#include "machine.hpp"``，然后构造生成包装层并调用包装层周期方法。
     - 命名空间、包装类名、钩子别名、周期重载。
   * - ``cpp_poll``
     - 构造包装层，安装包装层钩子和事件检查，然后调用 ``cycle()``。
     - 包装层事件检查别名、设置器名称和轮询生命周期片段。

不支持或高风险假设
------------------

.. list-table:: 反例
   :header-rows: 1

   * - 假设
     - 为什么错
     - 更安全表述
   * - “所有内置模板都已经生产认证。”
     - 元数据当前把五个模板都标成 experimental。
     - 它们有当前仓库测试和冒烟证据，不是全平台认证。
   * - “仓库 ``templates/`` 目录就是用户接口。”
     - 普通用户应通过 ``--template`` 使用打包资产。
     - 仓库模板源码是维护者输入和打包来源。
   * - “C++ 模板不需要 C 生成核心。”
     - ``cpp`` 和 ``cpp_poll`` 会复用生成 C 核心。
     - C++ 模板提供生成 C 核心之上的包装层集成面。
   * - “轮询模板改变状态机语义。”
     - 轮询改变事件真值的提供方式。
     - 生命周期和转换语义应在已记录排除项内与模拟器对齐。
   * - “生成文件树证明运行时正确。”
     - 渲染成功只证明文件创建。
     - 运行时、本机和语义声明需要对应冒烟或对齐证据。

事实源审计地图
--------------

reviewer 可以按下面的来源审计本页，而不需要猜测：

* 包列表和归档名：``pyfcstm/template/index.json``；
* 每个模板的标题、语言、描述和实验状态：``templates/<name>/template.json``；
* 生成文件和集成片段：每个模板生成的 ``README.md`` 和 ``README_zh.md``；
* 事件输入模型：生成 README、运行时模板和模板测试；
* C 家族辅助和固定宽度代码体事实：``pyfcstm/render/c_runtime.py``；
* 包装层事实：``templates/cpp``、``templates/cpp_poll`` 源模板和包装层冒烟测试；
* 当前证据边界：模板单元测试、语义对齐测试、格式化检查，以及主机工具链可用时的本机冒烟检查。
