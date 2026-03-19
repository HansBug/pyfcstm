# pyfcstm 模板系统与 Python 内置模板方案

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.2.0 | 2026-03-19 | 补充根目录 `templates/`、模板总 README、Makefile 打包与 `pyfcstm/template/` 释放模块设计 | Codex |
| 0.1.0 | 2026-03-19 | 初始版本，整理模板系统现状并提出 Python 内置模板方案 | Codex |

---

## 1. 背景与目标

目前 `pyfcstm` 的代码生成能力本质上是一个 Jinja2 模板渲染系统：输入为 `StateMachine` 模型，输出为模板目录渲染后的文件集合。  
本次希望新增一个**自带的 Python 模板**，并且它满足以下约束：

- 生成结果是**纯 Python 标准库可运行代码**
- 生成结果**不依赖 pyfcstm 自身**
- 生成结果**不依赖 pip 安装任何第三方包**
- 生成出来的 Python 文件应当像 ANTLR 生成代码那样，属于“可直接 import 的硬编码产物”
- 状态机运行逻辑不放在外部运行时包中，而是**内置到生成类中**
- `cycle` 逻辑、给定状态热启动逻辑、状态变量初始化逻辑都需要内置
- 该 Python 模板应作为 `pyfcstm` **自带 builtin templates 之一**
- 后续还会扩展其他语言模板，因此这次方案不能只为 Python 特判到不可复用

这里的核心目标不是“生成一个 Python 版解释器壳子”，而是：

1. 利用 `pyfcstm` 现有模型层和模板系统完成代码生成  
2. 让最终产物成为**独立可分发、可 import、可长期稳定使用**的 Python 模块  
3. 为未来的内置模板体系建立统一的组织方式

这里再补一个组织原则：

- 仓库中的**模板源码目录**
- 安装包中的**模板发布载体目录**

这两者建议分离。前者便于开发维护，后者便于分发和运行时释放。

---

## 2. 对参考模板的观察

参考目录：`~/oo-projects/fsm_generation_template`

该参考模板体现的是一种典型的“生成代码 + 固定运行时骨架 + 用户扩展点”的思路：

- `config.yaml` 中主要定义表达式风格、名字生成规则、过滤器和全局函数
- `XXXLX_auto.c.j2` / `XXXLX_auto.h.j2` 负责生成**状态机结构、调度函数、状态表、事件表**
- `XXXLX_extra.c.j2` / `XXXLX_extra.h.j2` 负责生成**用户可补充实现的抽象函数与事件检查函数**
- `FSM_Step.h` / `FSM_Step.c` / `tpDef.h` / `cStruct.h` 是固定运行时支撑代码，直接复制到输出目录

这个方案的优点是：

- 模板输出结构清晰
- 生成部分和固定运行时部分职责分离
- 代码风格是硬编码的，最终产物不依赖模板系统本身

但它不完全符合这次 Python 模板的目标，原因有三点：

1. 它依赖外部固定运行时文件  
   这在 C 里合理，但本次 Python 方向更希望生成产物本身就是完整模块。

2. 它鼓励用户继续修改生成出的 `extra.*` 文件  
   这与“生成 Python 文件保持不变，外部代码直接 import 使用”的目标不一致。

3. 它把事件触发和抽象动作实现留给用户手写函数  
   Python 版本更适合改成**运行时注册回调**，而不是要求用户改生成文件。

因此，Python 模板应当借鉴它的“硬编码生成”思想，但不能简单照搬其文件布局。

---

## 3. pyfcstm 现有模板系统能力与限制

### 3.1 已有能力

从 `pyfcstm/render/render.py` 看，当前模板系统已经具备以下能力：

- 读取模板目录中的 `config.yaml`
- 为模板提供 Jinja2 `globals` / `filters` / `tests`
- 支持表达式渲染 `expr_render`
- 递归扫描模板目录
- 对 `.j2` 文件做渲染
- 对非 `.j2` 文件做原样拷贝
- 支持 ignore 规则

这意味着下面这些目标**已经可以直接支持**：

- 生成一个固定文件名的 `machine.py`
- 额外生成 `__init__.py`、`README.md`、示例文件等
- 拷贝静态 Python 文件到输出目录
- 在模板里基于 `model.walk_states()` 等模型能力做硬编码展开

### 3.2 已知限制

当前系统也有几个关键限制，需要在方案中显式考虑：

#### 限制 1：输出文件名不能模板化

现在 `.j2` 只渲染文件内容，不渲染输出文件名。  
也就是说模板目录里如果有 `machine.py.j2`，输出一定是 `machine.py`，而不是 `{{ model.root_state.name }}.py`。

这会直接影响内置 Python 模板的接口设计。  
因此第一版建议采用**固定文件名**方案，例如：

- `machine.py`
- `__init__.py`
- `README.md`

如果未来确实需要“根据状态机名自动生成模块文件名”，再扩展 render 层。

#### 限制 2：当前只有表达式 renderer，没有目标语言级 statement renderer

现在已经有：

- `expr_render(style='python')`

但对于 `enter/during/exit/effect` 中的操作块，现阶段只有：

- `operation_stmt_render`
- `operation_stmts_render`

它们输出的是 **DSL 文本**，适合注释和展示，不适合直接生成 Python 可执行语句。

而 Python 模板要真正生成可执行代码，必须把下面这些操作块编译成 Python 语句：

- `Operation`
- `IfBlock`

特别是还要保留**块级临时变量语义**。

因此，Python 模板落地前，建议先补一个**statement renderer 层**，至少支持：

- 赋值语句渲染
- `if / elif / else` 语句渲染
- 缩进输出
- 基于当前块上下文区分“全局状态变量”和“临时变量”

#### 限制 3：当前 CLI 只有 `--template-dir`

目前 `generate` 命令要求用户显式传目录：

```bash
pyfcstm generate -i input.fcstm -t template_dir -o output_dir
```

如果要支持“自带模板”，需要新增一层 builtin template 解析机制，否则用户无法方便使用包内模板。

#### 限制 4：当前打包配置不会自动带上模板源码或模板压缩包

当前 `setup.py` / `MANIFEST.in` 中的 `package_data` 主要包含：

- `*.yaml`
- `*.yml`
- `*.json`
- `*.png`
- `*.g4`
- `*.tokens`
- `*.interp`

如果采用“根目录 `templates/` 维护源码，发布时打包到 `pyfcstm/template/`”这条路线，则至少还要补充：

- `pyfcstm/template/*.zip`
- `pyfcstm/template/*.json`
- `pyfcstm/template/__init__.py`

如果源码模板也希望随源码包一起分发，则还要额外考虑：

- `templates/**/*.j2`
- `templates/**/*.md`
- `templates/**/config.yaml`
- 其他静态模板资源

否则安装后的包中 builtin template 的列举与释放能力不会完整存在。

---

## 4. Python 内置模板的总体设计

### 4.1 设计原则

Python 内置模板建议遵循以下原则：

1. **生成产物自包含**
   不依赖 `pyfcstm` 包，不依赖第三方库。

2. **固定公开 API**
   用户不修改生成文件，而是在自己的业务代码中 import 并调用。

3. **运行时逻辑内置**
   `cycle`、hot start、变量初始化、事件匹配、生命周期执行都在生成类中完成。

4. **生成结果硬编码**
   状态结构、转换表、动作逻辑都以展开后的 Python 代码落在文件里，而不是再依赖 DSL 或模型对象。

5. **模板系统内外职责清晰**
   `pyfcstm` 负责“生成”；生成结果负责“运行”。

6. **模板产物严格平台无关**
   生成出来的 Python 代码必须在 Windows、主流 Linux 发行版、macOS 上保持一致行为，不依赖任何平台特定机制。

7. **模板产物严格兼容 Python 3.7-3.14**
   生成代码不能使用较高版本 Python 才有的语法、标准库接口或行为假设。

### 4.2 平台与版本兼容性红线

这是 Python 内置模板的硬约束，不是优化项。

生成出来的模板产物必须满足：

- **平台无关**
  不依赖操作系统差异，不依赖 shell，不依赖路径分隔符约定，不依赖大小写敏感文件系统，不依赖特定换行风格。

- **Python 3.7-3.14 全兼容**
  生成代码必须能在该区间内直接运行，不能要求用户升级解释器。

- **纯标准库**
  不使用任何第三方包，也不使用需要额外安装的运行时组件。

- **避免实现依赖**
  不依赖 CPython 某些版本的实现细节，不依赖未文档化行为，不依赖不同平台上的浮点、文件系统、编码边角差异。

因此在模板实现时，应明确避免以下内容：

- `match/case`
- `except*`
- `typing` 中较新的运行时对象和语法糖
- `dataclasses` 中超出 Python 3.7 可稳定使用范围的特性假设
- `importlib.resources` 新式高版本接口
- 仅在部分平台行为一致的临时文件、权限、路径处理写法
- 任何对本地时区、区域设置、终端编码、系统 shell 的隐式依赖

更具体地说，生成代码应优先采用：

- 朴素 class
- 基本容器类型
- 显式字符串与字典操作
- 显式异常类型
- 保守的标准库用法

不要为了“代码更现代”而引入任何会破坏 3.7-3.14 兼容性的写法。

### 4.3 第一版推荐输出结构

第一版建议输出一个最小 Python 包目录：

```text
output_dir/
├── __init__.py
├── machine.py
└── README.md
```

其中：

- `machine.py` 是核心生成文件
- `__init__.py` 负责导出公共类
- `README.md` 给出最小使用说明

之所以不是单文件裸输出，而是小包形式，是因为：

- 仍然保持可 import
- 以后若需要补静态辅助模块，有扩展空间
- 当前 render 系统对固定文件名支持天然友好

但在公开接口上，我们仍然应当把 `machine.py` 设计成**用户主要面对的单一实现文件**。

---

## 5. 生成出来的 Python 模块形态

### 5.1 对外 API 目标

建议生成一个公开类，名字可以固定，也可以由模板按根状态名生成类名。

第一版建议：

- 文件名固定：`machine.py`
- 类名按根状态名生成，例如 `TrafficLightMachine`

这样既不要求动态文件名，也保留了可读性。

建议公开 API 至少包括：

```python
class TrafficLightMachine:
    def __init__(self, initial_state=None, initial_vars=None):
        ...

    def cycle(self, events=None):
        ...

    def reset(self, initial_state=None, initial_vars=None):
        ...

    @property
    def current_state(self):
        ...

    @property
    def current_state_path(self):
        ...

    @property
    def vars(self):
        ...

    @property
    def is_ended(self):
        ...

    def register_abstract_handler(self, action_path, handler):
        ...

    def unregister_abstract_handler(self, action_path, handler=None):
        ...
```

可选增强 API：

- `brief_stack`
- `cycle_count`
- `has_abstract_handlers`
- `clear_all_abstract_handlers`

这些 API 命名最好尽量对齐 `SimulationRuntime`，这样用户迁移成本最低。

### 5.2 用户使用方式

目标使用方式应当类似：

```python
from my_machine.machine import TrafficLightMachine

sm = TrafficLightMachine()
sm.cycle()
sm.cycle(['TrafficLight.InService.Red.Start'])

print(sm.current_state_path)
print(sm.vars)
```

对于抽象动作：

```python
def on_init(ctx):
    print(ctx.state_path, ctx.vars)

sm.register_abstract_handler('TrafficLight.InService.InitHardware', on_init)
```

这里不要求用户改生成文件，只要求在外部业务代码中注册回调。

---

## 6. 生成文件内部的实现思路

### 6.1 总体结构

建议 `machine.py` 采用“**一个公开类 + 若干私有常量/私有辅助方法**”的组织方式：

- 公共类：状态机运行实例
- 私有常量：状态 ID、事件路径、动作路径、状态路径
- 私有结构：转换表、初始转换表、状态元数据
- 私有方法：执行 enter/during/exit/effect、选转换、执行转换、hot start 建栈等

实现风格上更接近“ANTLR 生成的硬编码 Python 类”，而不是“解释器加载外部配置”。

### 6.2 推荐采用“硬编码表 + 通用执行引擎”的混合方案

这里有两种实现方向：

#### 方案 A：纯函数分发式

为每个状态、每个动作、每条转换都生成独立方法，例如：

- `_enter_state_7()`
- `_during_leaf_12()`
- `_transition_12_3()`

优点：

- 生成结果非常直观
- 接近参考 C 模板风格

缺点：

- 文件会很大
- 很多逻辑重复
- 调试与维护成本偏高

#### 方案 B：数据表 + 通用引擎

把状态结构、转换关系、动作索引生成为常量表；执行语义由类内部一组通用方法负责。

优点：

- 代码尺寸更可控
- 语义集中，易于和 `SimulationRuntime` 对齐
- 后续做其他语言模板时更容易抽象公共生成策略

缺点：

- 需要设计一套生成时数据布局

#### 建议

推荐采用**混合方案**：

- 结构关系用硬编码常量表表示
- 动作块用生成的专用私有方法表示
- 通用调度逻辑放在固定类方法里

这样既保持“硬编码生成”的风格，又不会把每个执行步骤都膨胀成重复代码。

---

## 7. 运行时语义设计

Python 模板内置运行时时，建议尽量对齐当前 `pyfcstm.simulate.runtime.SimulationRuntime` 的核心语义。  
这样做的好处是：

- 模板生成结果行为更容易预期
- 模拟器和生成代码可以共享同一套测试样例
- 以后出现语义 bug 时更容易做对照

### 7.1 应当继承的核心语义

第一版建议明确支持以下语义：

1. **层次状态机栈执行模型**
   栈从根到叶保存当前激活路径。

2. **frame mode 机制**
   至少保留：
   - `active`
   - `after_entry`
   - `init_wait`
   - `post_child_exit`

3. **enter / during / exit 执行顺序**
   与现有模拟器一致。

4. **aspect during 语义**
   - `>> during before`
   - `>> during after`
   - pseudo state 跳过祖先 aspect

5. **复合状态 during before / after 语义**
   仅在父子边界进入/退出时执行，不在 sibling 间切换时执行。

6. **初始转换链**
   进入复合状态后自动尝试 `[*] -> child`。

7. **退出转换语义**
   `A -> [*]` 退出到父状态，根级退出则结束状态机。

8. **transition effects**
   退出动作后执行 effect，再进入目标状态。

9. **给定位置初始化 / hot start**
   允许从指定状态路径构建栈。

10. **块级临时变量语义**
    操作块中未声明但首次赋值的变量是块内临时变量，不能泄漏到机器全局变量中。

### 7.2 关于 transition validation

当前 `SimulationRuntime` 对 stoppable 状态触发的转换有一套“先 DFS 验证能否到达稳定边界，再提交”的机制。  
这是现有模拟器语义里的重要部分。

这里建议分阶段处理：

#### 第一阶段目标

Python 生成模板**保留 validation 语义**，尽量与现有模拟器一致，包括：

- 克隆栈与变量做模拟
- 验证进入 non-stoppable 链后是否能到达 stoppable 或结束
- 失败时回滚

原因是：

- 这部分虽然复杂，但它直接影响状态机行为正确性
- 如果生成代码和模拟器在这里不一致，后续调试会非常痛苦

#### 如果实现复杂度过高时的降级策略

如果第一版实现压力过大，可以把降级策略写死在文档里：

- V1 只支持“无 validation 简化执行”
- V2 再补全 validation

但我更建议**一开始就按现有模拟器对齐**，因为这部分本质上已经有明确可抄写的执行语义，不是重新发明。

### 7.3 给定位置初始化的建议语义

建议直接对齐现有 `SimulationRuntime`：

- `initial_state` 可以是字符串路径
- `initial_vars` 在指定 `initial_state` 时必须提供完整变量集
- 目标叶子状态的最后 frame mode 为 `active`
- 目标复合状态的最后 frame mode 为 `init_wait`
- hot start 不执行 enter 动作
- 第一次 `cycle()` 从该位置继续推进

这部分用户已经明确提出需要内置，应当作为模板公开能力，而不是测试接口。

---

## 8. 操作块代码生成方案

这是 Python 模板能否真正落地的关键点。

### 8.1 为什么不能只靠现有 `expr_render`

现有模板系统对表达式已经支持 Python 渲染，例如：

- 算术表达式
- 布尔表达式
- 条件表达式
- 常见数学函数

但一个完整的动作块并不只是表达式，它还包含：

- 顺序赋值
- `if / else if / else`
- 临时变量作用域

因此不能简单把每个 `operation.expr` 渲染完后手写拼接，必须有**语句级生成策略**。

### 8.2 推荐的 statement renderer 设计

建议在 render 层补一个与 `expr_render` 对应的 statement renderer，例如：

- `stmt_render`
- `stmts_render`

最小支持的节点种类：

- `Operation`
- `IfBlock`

对 Python 模板来说，输出的不是 DSL，而是 Python 语句块。

### 8.3 块级临时变量的处理方式

当前模拟器对操作块的执行逻辑非常清晰：

- 操作块执行时先复制一份 `local_scope = dict(vars_)`
- 在块内，赋值到未声明名字时，自动落到 `local_scope` 中，形成临时变量
- `if` 分支执行时，只把进入分支前已经可见的名字写回外层作用域
- 块结束后，只把全局状态变量写回 `vars_`

因此生成代码时，建议**直接复制这一语义**，不要做过度静态分析。

建议生成模式如下：

1. 每个动作块生成一个私有方法，如 `_run_action_17(self)`
2. 方法体内部创建 `scope = dict(self._vars)`
3. 通过生成的 Python 语句执行整个块
4. 块结束后只回写状态机定义中的变量名

这样有几个好处：

- 与现有模拟器语义一致
- 不需要为临时变量单独做复杂数据流分析
- 嵌套 if 的作用域行为更容易保持一致

### 8.4 语句生成的一个建议样式

生成出的私有方法风格可以类似：

```python
def _action_17(self):
    scope = dict(self._vars)

    scope['tmp'] = scope['x'] + 1
    if scope['flag'] > 0:
        branch_scope = dict(scope)
        branch_scope['tmp'] = branch_scope['tmp'] + 10
        branch_scope['y'] = branch_scope['tmp']
        for name in ('x', 'y', 'flag', 'tmp'):
            scope[name] = branch_scope[name]
    else:
        branch_scope = dict(scope)
        branch_scope['y'] = branch_scope['tmp'] - 1
        for name in ('x', 'y', 'flag', 'tmp'):
            scope[name] = branch_scope[name]

    self._vars['x'] = scope['x']
    self._vars['y'] = scope['y']
    self._vars['flag'] = scope['flag']
```

这里即使 `tmp` 是临时变量，也只存在于块内部的 `scope` 中，不会写回 `self._vars`。

这个实现虽然比直接生成“自然 Python 代码”稍笨一些，但它：

- 语义稳定
- 生成器实现难度低
- 更容易覆盖测试

我认为这是一个很值得的工程取舍。

---

## 9. 事件与抽象动作的设计

### 9.1 事件输入

Python 生成模块不再像 C 模板那样要求用户手写“事件是否触发”的函数。  
建议直接沿用模拟器接口：

```python
sm.cycle(events=['Root.System.Idle.Start'])
```

也就是说，事件由调用方在每个 cycle 明确提供。

第一版建议至少支持：

- 规范全路径事件名，即 `event.path_name`

相对路径、绝对路径、父级相对路径这类“事件解析便利语法”可以作为增强项，后续再补。

原因是：

- 全路径事件名最稳定
- 生成代码实现最简单
- 对外语义最明确

### 9.2 抽象动作

用户不应修改生成文件去填空。  
因此建议改为**回调注册机制**，而不是生成 `extra.py` 让用户编辑。

建议行为：

- 命名 abstract action 可通过 `register_abstract_handler(action_path, handler)` 注册
- 未注册时默认跳过
- 匿名 abstract action 发出警告或直接跳过
- handler 接收只读上下文对象

这套接口可以尽量对齐当前 `SimulationRuntime` 的命名。

### 9.3 只读上下文

生成代码里可以内置一个轻量只读上下文对象，或者直接传入一个简单对象/字典。  
考虑到“一个 class 内置逻辑”的目标，建议尽量轻量：

- 可以用私有嵌套类
- 也可以用简单对象包装

只要满足以下字段即可：

- `state_path`
- `vars`
- `action_name`
- `action_stage`

这部分全部使用标准库即可，不构成额外依赖。

---

## 10. builtin template 组织与发布方案

### 10.1 源码模板目录建议

建议直接采用仓库根目录 `templates/` 作为官方模板源码目录。  
这一点也与当前 `Makefile` 里已有的 `TEMPLATES_DIR := ${PROJ_DIR}/templates` 保持一致。

推荐结构如下：

```text
templates/
├── README.md
├── README_zh.md
├── python_native/
│   ├── config.yaml
│   ├── machine.py.j2
│   ├── __init__.py.j2
│   └── README.md
├── c_hardcoded/
│   └── ...
└── ...
```

约定如下：

- `templates/` 下每一个一级子目录都代表一个 builtin template
- `templates/README.md` 负责说明模板系统用途、组织方式、英文引导
- `templates/README_zh.md` 提供中文总入口与使用引导
- 每个模板子目录内部的 `README.md` 负责说明该模板的用途、输出结构、适用场景、示例命令、限制项

这种组织方式的优点是：

- 模板源码集中在仓库根目录，便于维护和评审
- 模板总说明与单模板说明都容易找
- 后续扩展其他语言模板时结构统一

### 10.2 包内发布目录建议

安装包中的 builtin template 不直接暴露源码目录，而是暴露**打包后的模板产物**。  
建议在包内新增：

```text
pyfcstm/template/
├── __init__.py
├── index.json
├── python_native.zip
├── c_hardcoded.zip
└── ...
```

其中：

- `pyfcstm/template/` 是一个 Python module
- 它本身不承载渲染逻辑
- 只负责列举有哪些 builtin template，并把对应模板释放到给定目录

这样做比直接把源码模板目录塞进包里更稳，原因是：

- wheel / sdist 的携带形式更简单
- CLI 只要“释放 zip -> 得到目录 -> 复用现有 renderer”
- 运行时对模板的依赖形式清晰，不和源码组织耦合

### 10.3 `pyfcstm/template/__init__.py` 的职责建议

建议该模块只暴露少量明确函数，例如：

```python
def list_templates():
    ...

def has_template(name):
    ...

def get_template_info(name):
    ...

def extract_template(name, output_dir):
    ...
```

建议职责边界如下：

- `list_templates()` 返回所有 builtin template 名称
- `has_template(name)` 判断模板是否存在
- `get_template_info(name)` 返回模板元信息
- `extract_template(name, output_dir)` 将模板 zip 解压到指定目录，并返回模板目录路径

它不应该负责：

- 解析 DSL
- 直接做 Jinja 渲染
- 实现状态机运行逻辑

这样 `pyfcstm/template/` 就是一个非常干净的“模板资源发布模块”。

### 10.4 模板索引文件建议

建议在 `pyfcstm/template/` 下同时生成一个索引文件，例如 `index.json`，内容包含：

- 模板名
- 简短描述
- zip 文件名
- 推荐语言
- 是否实验性

这样：

- CLI 可以直接用它给 `--template` 做帮助信息
- `pyfcstm/template/__init__.py` 不需要把所有元数据硬编码在 Python 文件里

### 10.5 Makefile 打包流程建议

建议在根 `Makefile` 中新增一个模板打包命令，例如：

- `make templates_package`

该命令建议完成以下工作：

1. 扫描根目录 `templates/` 下的一级子目录
2. 跳过 `README.md`、`README_zh.md` 等总说明文件
3. 将每个模板子目录单独打包为 zip
4. 输出到 `pyfcstm/template/`
5. 同步生成 `pyfcstm/template/index.json`

建议 zip 内部保持模板目录自身为根，例如 `python_native.zip` 内部结构为：

```text
python_native/
├── config.yaml
├── machine.py.j2
├── __init__.py.j2
└── README.md
```

这样 `extract_template(name, output_dir)` 解压后可以直接得到：

```text
<output_dir>/python_native/
```

返回值也就可以直接作为模板目录传给 `StateMachineCodeRenderer`。

### 10.6 CLI 建议

建议保留现有：

- `--template-dir`

再新增：

- `--template`

示例：

```bash
pyfcstm generate -i traffic.fcstm --template python_native -o ./traffic_machine
```

约束建议：

- `--template-dir` 与 `--template` 二选一
- 两者同时给出时报错
- 两者都没给时报错

对 builtin template 的内部处理建议是：

1. CLI 识别 `--template python_native`
2. 调用 `pyfcstm.template.extract_template(...)`
3. 将模板释放到一个临时目录或调用方给定目录
4. 把释放后的模板目录路径传给现有 `StateMachineCodeRenderer`

这样自定义模板和官方模板都能保留，而且现有渲染器几乎不用改。

---

## 11. 对 render 层的建议改造

### 11.1 低优先级，可暂不改

#### 动态输出文件名

如果第一版接受固定文件名，则 render 层可以暂时不动。

### 11.2 高优先级，建议先补

#### statement renderer

这是 Python 内置模板真正落地的前置条件之一。  
建议新增与 `expr_render` 平行的语句渲染能力，至少支持：

- `Operation -> Python assignment`
- `IfBlock -> Python if/elif/else`
- 语句列表按缩进输出

同时要允许模板传入上下文，例如：

- 当前全局变量集合
- 当前缩进级别
- 当前块内可见变量集合

如果不想一开始就把 render 层做得很通用，也可以先做“Python 专用 statement renderer”，后续再抽象。

### 11.3 可选增强

为模板环境增加更多与模型遍历有关的辅助 filter / global，例如：

- 获取所有事件路径
- 获取所有命名抽象动作路径
- 获取状态索引
- 获取 transition 索引

这些不是必须项，但能显著减轻 `machine.py.j2` 的复杂度。

---

## 12. 测试策略

Python 内置模板如果要真正可靠，测试不能只做“是否生成成功”，而要做“生成结果运行行为是否正确”。

### 12.1 生成层测试

需要保留现有 render/entry 测试风格：

- 指定 DSL
- 指定 builtin template
- 生成目录
- 对比生成产物结构

### 12.2 行为层测试

更重要的是新增“生成结果执行测试”：

1. 用 DSL 生成 Python 模块
2. 用标准库 `importlib` 动态 import 生成的 `machine.py`
3. 创建实例并调用 `cycle`
4. 验证状态路径、变量、结束状态、hot start 结果

### 12.3 建议直接复用 simulate 测试语义

最值得做的方案是挑选一批 `SimulationRuntime` 已有测试样例，构建成共享基准：

- 简单叶子状态切换
- 复合状态初始转换
- aspect during
- `during before/after`
- `[*]` 退出
- hot start
- 临时变量
- 嵌套 if
- 抽象动作回调
- validation 成功/失败

这样可以同时验证：

- 模型层
- 模板层
- 生成运行时

三者语义是否一致。

---

## 13. 工作安排与 Phase Checklist

建议按顺序推进，不要并行把所有事情一起做。  
推荐依赖关系如下：

```text
Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5
```

其中：

- `Phase 1` 解决模板源码与发布链路
- `Phase 2` 解决 Python 模板最关键的语句生成基础设施
- `Phase 3` 才正式实现 `python_native`
- `Phase 4` 做语义对齐验证
- `Phase 5` 再考虑增强项

### 13.1 PR 跟踪与 Checklist 同步规则

本设计文档对应的实施 PR：

- PR 链接：[PR #70](https://github.com/HansBug/pyfcstm/pull/70)

这里的约束是：

- 文档中的 Phase Checklist 是**本地真源**
- PR 描述中的 checklist 是**协作用镜像**
- 两者在合并前应保持一致

因此后续执行时应遵守：

- 本地文档 checklist 发生变化后，提交并 push
- push 完成后，应同步更新 PR 描述中的 checklist
- 如果 PR 范围、阶段目标、完成标准发生变化，文档与 PR 描述必须一起改
- 不允许只改 PR 描述而不改文档，也不建议只改文档而长期不改 PR 描述

推荐操作顺序：

1. 先修改本地 [mds/TEMPLATE_SYSTEM.md](/home/hansbug/oo-projects/pyfcstm-2/mds/TEMPLATE_SYSTEM.md)
2. 提交并 push
3. 更新 PR 描述中的 Phase / checklist / 目标说明

这样可以避免“PR 写的是一套，仓库文档又是另一套”的双轨漂移。

### Phase 1：模板源码目录与包内发布链路

目标：

- 打通“模板源码目录 -> zip -> `pyfcstm/template/` -> 解压目录 -> renderer”链路
- 确立 builtin template 的源码组织方式和发布方式

Checklist：

- [x] 在仓库根目录建立 `templates/`
- [x] 新增 `templates/README.md`
- [x] 新增 `templates/README_zh.md`
- [x] 约定 `templates/` 下每个一级子目录就是一个 builtin template
- [x] 在 `pyfcstm/` 下建立 `template/` 模块目录
- [x] 在 [__init__.py](/home/hansbug/oo-projects/pyfcstm-2/pyfcstm/__init__.py) 或相关入口中接通 `pyfcstm.template` 的可访问性
- [x] 为 `pyfcstm/template/` 设计 `index.json` 结构
- [x] 在根 [Makefile](/home/hansbug/oo-projects/pyfcstm-2/Makefile) 中新增 `templates_package`
- [x] `templates_package` 能扫描 `templates/` 下的模板子目录
- [x] `templates_package` 能为每个模板生成单独 zip
- [x] `templates_package` 能同步生成 `pyfcstm/template/index.json`
- [x] 调整 [setup.py](/home/hansbug/oo-projects/pyfcstm-2/setup.py) 与 [MANIFEST.in](/home/hansbug/oo-projects/pyfcstm-2/MANIFEST.in)，确保 zip 与索引文件随包发布
- [x] 在 `pyfcstm/template/__init__.py` 中提供列举与释放接口
- [x] CLI 支持 `--template`
- [x] CLI 中 `--template` 与 `--template-dir` 的互斥关系明确
- [x] 本地 `make build` 在 CLI 构建前会准备模板打包产物
- [x] GitHub 的 whl / sdist 打包 workflow 在执行 `python -m build` 前显式执行 `make templates_package` 或等价步骤
- [x] GitHub 的 release / release_test / test 中所有 CLI 构建 workflow 都要明确依赖最新模板打包产物，而不是隐式依赖仓库中已有 zip 文件状态

完成标准：

- 可以通过 `--template <name>` 使用某个内置模板
- CLI 内部已经是“释放到目录后再交给现有 renderer”
- 安装包中包含完整的模板 zip 与索引信息

### Phase 2：statement renderer 基础设施

目标：

- 让模板层能够生成 Python 可执行语句块，而不只是 DSL 文本

Checklist：

- [ ] 明确 statement renderer 的接口形式
- [ ] 确定是新增通用 `stmt_render` / `stmts_render`，还是先做 Python 专用版本
- [ ] 支持 `Operation` 渲染为 Python 赋值语句
- [ ] 支持 `IfBlock` 渲染为 Python `if / elif / else`
- [ ] 支持语句列表缩进控制
- [ ] 支持块内临时变量可见性语义
- [ ] 支持嵌套 `if`
- [ ] 在模板环境中注册相关 filter / global
- [ ] 为 statement renderer 补独立单元测试
- [ ] 验证生成结果不使用 Python 3.7 以上才有的高版本语法

完成标准：

- 模板里可以稳定生成 Python 操作块代码
- 语句级生成与现有模型层的临时变量语义不冲突

### Phase 3：实现 `python_native` builtin template

目标：

- 交付第一个官方内置 Python 模板
- 生成结果为可直接 import 的、纯标准库、平台无关的状态机模块

Checklist：

- [ ] 在 `templates/python_native/` 建立模板目录
- [ ] 编写该模板的 `README.md`
- [ ] 实现 `config.yaml`
- [ ] 实现 `machine.py.j2`
- [ ] 实现 `__init__.py.j2`
- [ ] 如有需要，实现模板内的 `README.md.j2` 或静态 README
- [ ] 生成固定文件名输出结构
- [ ] 在 `machine.py` 中生成公开状态机类
- [ ] 内置变量初始化逻辑
- [ ] 内置 `cycle` 逻辑
- [ ] 内置初始转换逻辑
- [ ] 内置 `[*]` 退出逻辑
- [ ] 内置 hot start / 给定位置初始化逻辑
- [ ] 内置抽象动作回调注册逻辑
- [ ] 保持生成结果平台无关
- [ ] 保持生成结果兼容 Python 3.7-3.14
- [ ] 保持生成结果仅依赖 Python 标准库

完成标准：

- 用户可以直接 `pyfcstm generate --template python_native`
- 生成产物无需安装任何第三方包即可被 import 和运行

### Phase 4：行为对齐测试与验收

目标：

- 验证生成运行时与 `SimulationRuntime` 的关键语义一致

Checklist：

- [ ] 为 builtin template 增加生成层测试
- [ ] 为 `--template` CLI 路径增加入口测试
- [ ] 增加“生成后 import 执行”的行为测试
- [ ] 覆盖简单叶子状态切换
- [ ] 覆盖复合状态初始转换
- [ ] 覆盖 aspect during
- [ ] 覆盖 `during before/after`
- [ ] 覆盖 `[*]` 退出
- [ ] 覆盖 hot start
- [ ] 覆盖块级临时变量
- [ ] 覆盖嵌套 `if`
- [ ] 覆盖抽象动作回调
- [ ] 覆盖 validation 成功路径
- [ ] 覆盖 validation 失败路径
- [ ] 在 Windows / Linux / macOS 维度上确认没有平台差异性实现假设
- [ ] 在 Python 3.7-3.14 范围内确认语法和运行兼容性

完成标准：

- 关键样例在模拟器和生成代码上表现一致
- 没有引入平台相关或高版本 Python 依赖

### Phase 5：增强项与后续扩展

目标：

- 在首版稳定后，再考虑易用性和扩展性增强

Checklist：

- [ ] 评估是否支持事件相对路径解析
- [ ] 评估是否支持动态输出文件名
- [ ] 评估是否提供更丰富的调试接口
- [ ] 评估是否拆分为多文件运行时结构
- [ ] 评估是否对其他语言模板复用相同发布链路
- [ ] 评估 `templates/README.md` 与 `README_zh.md` 中的模板索引是否需要自动生成

完成标准：

- 不破坏首版 `python_native` 的稳定 API
- 新增强项不破坏平台无关与 Python 3.7-3.14 兼容性约束

---

## 14. 关键工程取舍

### 14.1 是否拆成“静态 runtime.py + 生成 machine.py”

我不建议第一版这么做。

原因：

- 用户明确倾向“生成出来就是可直接 import 的硬编码文件”
- 单文件更接近 ANTLR 风格
- 分发与拷贝更简单
- 避免用户误删静态 runtime 文件后无法运行

如果将来发现生成文件过大，再考虑拆分。

### 14.2 是否要求生成代码完全对齐 `SimulationRuntime`

我建议在**行为语义上尽量对齐**，但在代码组织上不强制一比一复刻。

也就是说：

- 可以复用它的状态机语义
- 可以复用它的 hot start 规则
- 可以复用它的 block scope 规则
- 但不必把日志、history、错误模式等所有附加功能都首版塞进去

第一版应优先保证：

- 状态切换正确
- 变量更新正确
- hot start 正确
- 抽象动作回调可用
- 生成代码不依赖外部包

### 14.3 是否首版就支持所有便利语法

不建议。  
首版可以优先支持“最稳定、最明确”的那部分：

- 规范事件全路径
- 命名 abstract handlers
- 固定输出文件名

把复杂便利特性放到后续增强阶段，可以显著降低首版复杂度。

---

## 15. 建议的首版结论

综合现有模板系统、参考模板结构和 Python 无依赖目标，建议首版方案如下：

1. 在仓库根目录新增 `templates/`，每个一级子目录表示一个 builtin template
2. 增加 `templates/README.md` 与 `templates/README_zh.md` 作为模板总入口说明
3. 在 `Makefile` 中新增 `templates_package`，把每个模板子目录打成 zip
4. 在 `pyfcstm/template/` 中存放这些 zip、`index.json` 和释放模块
5. `pyfcstm/template/__init__.py` 只负责列举模板、读取元信息、释放模板到指定目录
6. CLI 新增 `--template python_native`，内部先释放模板，再复用现有渲染器
7. 先补 Python 语句块 renderer，再写模板
8. 生成固定文件名的小包输出，核心逻辑集中在 `machine.py`
9. `machine.py` 中生成一个公开状态机类，内置：
   - 变量初始化
   - 栈执行模型
   - `cycle`
   - 初始转换
   - `[*]` 退出
   - hot start
   - 抽象动作回调注册
   - 块级临时变量语义
10. 首版事件接口先要求全路径事件名，避免过早引入复杂解析逻辑
11. 生成出来的 Python 模板本身必须保持平台无关，并严格兼容 Python 3.7-3.14
12. 行为语义尽量对齐 `SimulationRuntime`，尤其是 validation 与 block scope

这条路线的优点是：

- 充分利用 `pyfcstm` 现有模型层与模板层
- 生成产物真正独立
- 对用户来说使用方式明确
- 对后续其他语言 builtin template 也具有可复制性

---

## 16. 后续实现时的注意事项

1. 生成代码必须考虑 Python 3.7 到 3.14 的兼容性  
   不要依赖过新的语法或标准库接口。

2. 生成代码必须保持平台无关  
   不要依赖 Windows / Linux / macOS 的平台差异，不要引入路径、权限、编码、换行、shell 相关假设。

3. 生成代码必须只使用标准库  
   `math`、`typing`、`warnings` 这类可以使用，但不能引入第三方依赖。

4. 模板生成出来的类 API 一旦发布，尽量保持稳定  
   否则用户业务代码会被迫跟着改。

5. 模拟器和生成代码要尽量共用测试语义  
   否则后面会出现“simulate 行为对，生成代码行为不对”的双轨维护问题。

6. 文档要明确区分“生成期依赖”和“运行期依赖”  
   `pyfcstm` 自己生成代码时可以有依赖，但生成产物运行时不能依赖这些包。

7. 对生成代码风格要保持保守  
   优先使用 Python 3.7 就稳定可用的语法与标准库接口，不要为了“现代化”引入高版本语法糖。

8. `pyfcstm/template/` 的模块职责一定要收紧  
   它是模板资源分发模块，不要演化成第二套渲染框架或第二套模板系统。

---

## 17. 一句话结论

这件事完全可做，而且和 `pyfcstm` 现有模板系统并不冲突。  
真正的关键不在“能不能生成 Python 文件”，而在于先把**根目录 `templates/` 的源码组织、`pyfcstm/template/` 的 zip 发布链路、statement renderer、以及内置运行时语义边界**这四件事设计清楚。按“源码目录维护，Makefile 打包，包内模块释放，CLI 再复用现有 renderer”这条路走，`python_native` 作为官方自带模板落地会更稳。
