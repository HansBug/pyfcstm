# operation block 中 if block 设计文档

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1.0 | 2026-03-18 | 初始版本，定义 operation block 的 if / nested if 语法、AST、model、simulate、solver 与落地计划 | Codex |

---

## 1. 背景与目标

当前 `pyfcstm` 的 operation block 只支持**线性赋值语句序列**，例如：

```fcstm
effect {
    a = b + 1;
    c = a * 2;
}
```

这套模型已经具备两条非常重要的语义基础：

- **顺序生效**：后续语句可以看到前面语句写入的值
- **块内临时变量**：在 block 内首次赋值的新名字可作为临时变量继续使用，但不会泄漏到 block 外

因此，这次扩展不应只零散地补一个 `if` 关键字，而应把 operation block 从“赋值列表”升级为“**可递归语句块**”。这样才能自然支持：

- 普通 `if`
- `else if`
- `else`
- `nested if`
- 未来可能继续扩展的 block 内控制结构

本文目标是给出一套**完整且可落地**的技术方案，覆盖：

- 语法修改
- AST data model 修改
- model 子模块修改
- simulate 执行语义与实现方向
- solver 中 block 的 Z3 化方案
- 连带影响、测试方案与实施顺序

---

## 2. 设计目标

本次设计应满足以下目标：

1. **支持 nested if**
   - `if` 的分支体内可以继续出现 `if`
   - 任意层级嵌套都应成立

2. **保持现有 block 语义风格**
   - 仍然是顺序执行
   - 仍然允许块内临时变量
   - 仍然禁止“先用后定义”

3. **不破坏现有表达式系统**
   - 条件继续使用现有 `cond_expression`
   - 赋值右侧继续使用现有 `num_expression`
   - 不引入把 statement 当 expression 的新机制

4. **仿真与 solver 语义一致**
   - concrete execution 和 symbolic execution 对同一 block 的理解必须一致
   - `if` 的分支合并规则必须清晰可复现

5. **对未来可扩展**
   - 以后若要增加 `while`、`assert`、`let` 等 block 语句，不需要再次推翻结构

---

## 3. 建议语法

## 3.1 推荐 DSL 语法

建议采用如下形式：

```fcstm
enter {
    if [x > 0] {
        y = 1;
    } else if [x == 0] {
        y = 0;
    } else {
        y = -1;
    }
}
```

支持 nested if：

```fcstm
during {
    if [mode == 0] {
        if [temp > 80] {
            level = 3;
        } else {
            level = 1;
        }
    } else if [mode == 1] {
        level = 2;
    } else {
        level = 0;
    }
}
```

## 3.2 为什么继续使用 `if [cond]`

建议条件语法继续沿用 guard 风格，而不是引入裸 `if cond`：

- 当前 transition guard 已经使用 `if [cond_expression]`
- `num_expression` 与 `cond_expression` 在语法上明确分离，复用 `[]` 最清晰
- ANTLR 冲突更少，错误提示更容易保持稳定
- 用户看到 `if [cond]` 时能立刻意识到这里必须是布尔条件，而不是数值表达式

## 3.3 `else if` 与 `elif`

V1 建议只支持：

- `if`
- `else if`
- `else`

不建议 V1 同时支持 `elif`。原因：

- `else if` 已足够表达所有需求
- `elif` 只是语法糖，不增加表达能力
- 先缩小语法面，有利于 parser、错误信息和高亮稳定

后续如果需要，可将 `elif` 作为纯语法糖映射到 `else if`。

---

## 4. 语法层修改方案

当前 grammar 中 operation block 的核心限制是：

- `operation_assignment: ID '=' num_expression ';'`
- `operational_statement` 只允许 assignment 或空语句
- `operational_statement_set` 本质只是 assignment list

建议调整为“statement + block”结构。

## 4.1 Grammar 目标结构

建议新增如下规则：

```antlr
operation_assignment
    : ID '=' num_expression ';'
    ;

operation_block
    : '{' operational_statement_set '}'
    ;

if_statement
    : 'if' '[' cond_expression ']' operation_block
      ('else' 'if' '[' cond_expression ']' operation_block)*
      ('else' operation_block)?
    ;

operational_statement
    : operation_assignment
    | if_statement
    | ';'
    ;

operational_statement_set
    : operational_statement*
    ;

operation_program
    : operational_statement* EOF
    ;
```

## 4.2 关键说明

### 4.2.1 `operation_block` 单独成规则

这样做有两个好处：

- 语义上清晰，`if` 的每个分支都显式绑定一个 block
- 以后若有其他 block 语句可以直接复用

### 4.2.2 `effect` / `enter` / `during` / `exit` 外层不变

例如：

```antlr
'effect' '{' operational_statement_set '}'
```

这里不必强行替换成 `operation_block`，保持兼容即可。内部仍然可以递归支持 `if`。

### 4.2.3 `nested if` 自然支持

因为 `operation_block -> operational_statement_set -> if_statement -> operation_block`，语法本身就是递归的，所以天然支持 nested if。

---

## 5. AST 设计

## 5.1 当前问题

当前 AST 里 block 中只有：

- `OperationAssignment`

这意味着 AST 结构默认 block 里的元素全是“叶子赋值”，无法表示 statement tree。

## 5.2 建议的 AST 抽象层次

建议新增一个专门的 operation statement 层：

```python
@dataclass
class OperationalStatement(Statement):
    pass


@dataclass
class OperationAssignment(OperationalStatement):
    name: str
    expr: Expr


@dataclass
class OperationIfBranch(ASTNode):
    condition: Optional[Expr]
    statements: List[OperationalStatement]


@dataclass
class OperationIf(OperationalStatement):
    branches: List[OperationIfBranch]
```

语义约束：

- `branches[0].condition` 必须非空
- 中间的 `else if` 分支 `condition` 必须非空
- 只有最后一个分支允许 `condition is None`，表示 `else`

## 5.3 为什么不用 `else_body`

相比：

```python
OperationIf(
    cond=...,
    body=[...],
    elifs=[...],
    else_body=[...],
)
```

统一成 `branches` 更好，原因是：

- 结构更统一
- `else if` 不需要特殊对待
- runtime 和 solver 都可以直接“从前到后找第一个命中的 branch”
- 后续如果想引入 source position、branch metadata，也更整齐

## 5.4 AST 上的连带修改

以下 AST 节点中的 block 字段都应从 `List[OperationAssignment]` 改为 `List[OperationalStatement]`：

- `TransitionDefinition.post_operations`
- `EnterOperations.operations`
- `DuringOperations.operations`
- `ExitOperations.operations`
- `DuringAspectOperations.operations`
- 其他所有承载 operation block 的 AST 位置

## 5.5 AST `__str__()` 输出

需要递归打印：

- `OperationAssignment` 仍然输出 `a = b + 1;`
- `OperationIf` 输出标准 DSL 结构
- branch 内部 statements 继续缩进

示例输出：

```fcstm
if [x > 0] {
    y = 1;
    if [z > 0] {
        w = 2;
    } else {
        w = 3;
    }
} else {
    y = 0;
}
```

---

## 6. Listener 与 Parse 层修改

## 6.1 Listener 新增节点构建

`dsl.listener` 需要新增：

- `exitIf_statement()`
- `exitOperation_block()`
- `exitOperational_statement()` 中识别 `if_statement`

构建过程建议是：

1. `operation_block` 返回 `List[OperationalStatement]`
2. `if_statement` 组装成 `OperationIf(branches=[...])`
3. `operational_statement_set` 继续返回 statement list

## 6.2 Parse 入口兼容

`parse_with_grammar_entry(..., "operational_statement_set")` 和 `parse_operation()` 都要同步更新说明：

- 以前返回 assignment list
- 现在返回 statement list

调用方不应再假设返回结果中的每个元素都有 `.name` 和 `.expr`。

---

## 7. model 层设计

## 7.1 当前问题

当前 model 的核心结构还是：

```python
@dataclass
class Operation:
    var_name: str
    expr: Expr
```

这对应的是“赋值语句”，不是“语句树”。

当前 `_parse_operation_block()` 也是按平铺赋值顺序构造 `List[Operation]`。

## 7.2 建议的 model 结构

建议保留现有 `Operation`，但明确它只表示**赋值语句**。同时新增：

```python
@dataclass
class OperationStatement:
    pass


@dataclass
class Operation(OperationStatement):
    var_name: str
    expr: Expr


@dataclass
class IfBlockBranch:
    condition: Optional[Expr]
    statements: List[OperationStatement]


@dataclass
class IfBlock(OperationStatement):
    branches: List[IfBlockBranch]
```

这样最稳妥：

- 现有大量以 `Operation(...)` 作为赋值语句的逻辑仍可复用
- 只是在 block 列表上把 `List[Operation]` 升级为 `List[OperationStatement]`

## 7.3 所有 block 字段的类型升级

以下字段建议统一改成：

- `Transition.effects: List[OperationStatement]`
- `OnStage.operations: List[OperationStatement]`
- `OnAspect.operations: List[OperationStatement]`

虽然字段名仍叫 `operations`，但内部元素已不只是赋值，而是通用 operation statement。

如果希望命名更准确，也可以后续逐步重命名为 `statements`。但为了降低改动面，V1 可以先保留字段名。

## 7.4 `to_ast_node()` 递归导出

`Operation.to_ast_node()` 仍然导出 `dsl_nodes.OperationAssignment`。

新增：

- `IfBlock.to_ast_node() -> dsl_nodes.OperationIf`
- `IfBlockBranch.to_ast_node() -> dsl_nodes.OperationIfBranch`

这样 model -> AST -> DSL 的 round-trip 才能保持成立。

---

## 8. model 层静态校验与作用域规则

这里是整套设计最重要的部分之一。

## 8.1 必须保持的既有规则

当前 block 的行为是：

- 右值表达式只能引用“当前已可见”的变量
- 赋值目标若是新名字，则在当前 block 内引入临时变量
- 后续语句可以使用这个临时变量
- block 结束后，临时变量消失

这些规则必须保留。

## 8.2 建议的作用域定义

定义每个 block 都有一个“当前可见名字集合” `available_vars`。

外层 block 初始：

- 所有全局 `def` 变量

执行赋值语句：

- RHS 中出现的变量名必须已经在 `available_vars` 中
- LHS 名字赋值后加入 `available_vars`

## 8.3 `if` 的作用域规则

对于：

```fcstm
if [cond] {
    ...
} else if [cond2] {
    ...
} else {
    ...
}
```

建议规则如下：

1. `cond` / `cond2` 只能引用进入该 `if` 前已可见的变量
2. 每个 branch 在**自己的子作用域**中解析
3. branch 的初始可见变量集合是进入 `if` 前的 `available_vars` 拷贝
4. branch 内新建临时变量不向外泄漏
5. branch 可以写回外层已存在的变量
6. branch 可以写回外层已存在的临时变量

## 8.4 明确不做的能力

V1 不建议做“跨 branch 的 definite assignment 合流分析”。

也就是说，下面这种写法在 V1 中建议**非法**：

```fcstm
if [x > 0] {
    tmp = 1;
} else {
    tmp = 2;
}
y = tmp + 1;
```

虽然从很多高级语言的角度看，它是可分析的，但这里不建议放行，原因：

- 需要在静态分析阶段计算所有 branch 的交集定义集
- 需要和 nested if 递归组合
- 会显著增加 model 校验与 solver merge 的复杂度
- 对 DSL 用户来说，规则会变得不够直观

V1 建议保持简单规则：

- **branch 内新引入的临时变量永不泄漏到 if 外**

上面的正确写法应为：

```fcstm
tmp = 0;
if [x > 0] {
    tmp = 1;
} else {
    tmp = 2;
}
y = tmp + 1;
```

## 8.5 nested if 的静态分析

nested if 不需要单独发明规则，直接递归套用同一套作用域规则即可。

例如：

```fcstm
if [a > 0] {
    b = 1;
    if [b > 0] {
        c = b + 1;
    }
    d = b + 2;
}
```

这里：

- 内层 `if [b > 0]` 合法，因为 `b` 是外层 branch 里已可见变量
- `c` 只存在于内层 `if` 的 branch 中，不可在内层 `if` 之后直接使用
- `d = b + 2` 合法，因为 `b` 在外层 branch 内仍可见

## 8.6 建议的 model 递归分析接口

建议把当前 `_parse_operation_block()` 拆成递归结构，例如：

```python
def _parse_operation_block(
    op_nodes: List[dsl_nodes.OperationalStatement],
    unknown_var_message: str,
    owner_node: AstExportable,
    available_vars: Optional[Set[str]] = None,
) -> List[OperationStatement]:
    ...
```

内部递归处理：

- `OperationAssignment`
- `OperationIf`

并将校验逻辑分离成辅助函数：

- `_parse_operation_statement(...)`
- `_parse_if_block(...)`

---

## 9. simulate 层执行语义

## 9.1 当前执行模型

当前 runtime 的 block 执行是：

1. `local_scope = dict(vars_)`
2. 顺序执行平铺赋值
3. 最后仅把全局变量写回 `vars_`

## 9.2 目标执行语义

引入 `if` 后，runtime 应升级为**递归解释器**。

建议接口结构：

```python
def _execute_operation_block(statements, vars_, ...):
    ...

def _execute_operation_statements(statements, local_scope):
    ...

def _execute_operation_statement(statement, local_scope):
    ...
```

## 9.3 赋值语句执行

与现有完全一致：

```python
local_scope[operation.var_name] = operation.expr(**local_scope)
```

## 9.4 `if` 语句执行

执行算法建议如下：

1. 从前到后遍历 `branches`
2. 对每个带条件的 branch，在当前 `local_scope` 上求值
3. 找到第一个条件为真者
4. 若命中：
   - `branch_scope = dict(local_scope)`
   - 在 `branch_scope` 中递归执行该 branch 的 statements
   - 将 branch 执行后的**外层已存在名字**同步回 `local_scope`
   - 停止后续分支判断
5. 若没有任何条件命中且存在 `else`：
   - 同样以 `branch_scope` 进入 `else`

## 9.5 为什么只回写“原本已存在的名字”

这是为了严格实现“branch 新临时变量不外泄”。

例如：

```fcstm
tmp = 10;
if [x > 0] {
    tmp = 20;
    inner = 1;
}
y = tmp;
```

执行后：

- `tmp` 应更新为 20
- `inner` 不应出现在外层 scope

因此回写逻辑应基于：

```python
outer_names = set(local_scope.keys())
for name in outer_names:
    local_scope[name] = branch_scope[name]
```

## 9.6 nested if 的运行语义

nested if 不需要特殊规则，递归解释即可。

这样可自动保证：

- 内层分支可见外层 branch 里的临时变量
- 内层新建临时变量不会穿透回外层 branch 之外

---

## 10. solver 层 Z3 化方案

这是第二个核心难点。

## 10.1 当前 solver 模型

当前 `execute_operations()` 的语义是：

- 输入：当前符号环境 `current_exprs`
- 对每个赋值：
  - `z3_expr = expr_to_z3(expr, current_exprs)`
  - `current_exprs[var_name] = z3_expr`
- 输出：仅返回原始外层变量名对应的表达式

这本质上是“**顺序符号赋值**”。

## 10.2 目标：递归符号执行

`if` 加入后，solver 应当支持：

- 在每个 branch 上独立符号执行
- 然后用 `z3.If(...)` 对外层可见变量逐一 merge

## 10.3 基本示例

DSL：

```fcstm
if [x > 0] {
    y = 1;
} else {
    y = 2;
}
```

Z3 后状态：

```python
y' = z3.If(x > 0, 1, 2)
```

若没有 `else`：

```fcstm
if [x > 0] {
    y = 1;
}
```

则应视为隐式 no-op：

```python
y' = z3.If(x > 0, 1, y)
```

## 10.4 建议的 solver 递归接口

```python
def execute_operations(
    operations: Union[OperationStatement, List[OperationStatement]],
    var_exprs: Dict[str, z3.ExprRef],
) -> Dict[str, z3.ExprRef]:
    ...

def _execute_operation_statements_symbolically(
    statements: List[OperationStatement],
    current_exprs: Dict[str, z3.ExprRef],
) -> Dict[str, z3.ExprRef]:
    ...

def _execute_if_block_symbolically(
    if_block: IfBlock,
    current_exprs: Dict[str, z3.ExprRef],
) -> Dict[str, z3.ExprRef]:
    ...
```

## 10.5 branch merge 规则

设进入 `if` 时外层符号环境是 `base_exprs`。

对于每个 branch：

1. 用 `branch_exprs = dict(base_exprs)` 进入 branch
2. 对 branch 的 statements 递归符号执行
3. 得到该 branch 的结束环境 `branch_result`

然后只对进入 `if` 前已经可见的名字 `visible_names = set(base_exprs.keys())` 做 merge。

### 10.5.1 只有 if，无 else

```python
merged[name] = z3.If(cond, branch_result[name], base_exprs[name])
```

### 10.5.2 if / else if / else

建议按链式方式 merge：

```python
merged[name] = z3.If(cond1, env1[name],
               z3.If(cond2, env2[name],
               z3.If(cond3, env3[name],
                     else_env[name])))
```

如果没有 `else`，最底层回落到 `base_exprs[name]`。

## 10.6 branch 内临时变量的 solver 语义

branch 内可以新建临时变量，例如：

```fcstm
if [x > 0] {
    tmp = x + 1;
    y = tmp * 2;
}
```

这里 `tmp` 在 branch 的局部符号环境中是允许存在的。

但 merge 后：

- 若 `tmp` 在进入 `if` 前不存在，则不应出现在 merge 后环境中
- 若 `tmp` 在进入 `if` 前就已存在，则应参与 merge

这与 runtime 的“只回写外层原有名字”保持一致。

## 10.7 nested if 的 Z3 语义

nested if 同样不需要额外机制，只需递归执行 branch 即可。

例如：

```fcstm
if [a > 0] {
    if [b > 0] {
        x = 1;
    } else {
        x = 2;
    }
} else {
    x = 3;
}
```

最终得到：

```python
x' = If(a > 0,
        If(b > 0, 1, 2),
        3)
```

## 10.8 为什么不直接把 if 降解成三元表达式赋值

虽然某些简单情况可以转换成：

```fcstm
x = (cond) ? a : b;
```

但 block 级 `if` 与三元表达式不是一回事：

- block `if` 可以包含多条语句
- 语句之间有顺序依赖
- branch 内可能创建临时变量
- nested if 会形成 statement tree，而不是单一 expression tree

因此 solver 必须做 statement 级 symbolic execution，而不是仅靠表达式重写。

---

## 11. 渲染、导出与其他连带影响

## 11.1 PlantUML / DSL 导出

当前很多导出逻辑默认 transition effect 是平铺赋值列表。

需要改为递归渲染 statement：

- assignment 直接输出
- if block 输出多行结构

否则 round-trip 和可视化会断。

## 11.2 render 模板

模板侧如果直接遍历 `transition.effects` 并假设每项都有：

- `var_name`
- `expr`

那么在引入 `IfBlock` 后会失效。

建议补充统一的 statement renderer：

- Jinja2 filter：`operation_stmt_render`
- 或在 model 上提供 `to_ast_node()` / `__str__()` 后由模板直接使用

## 11.3 语法高亮与编辑器支持

以下位置需要同步：

- Pygments lexer
- VSCode extension grammar / keywords

至少要高亮：

- `if`
- `else`

---

## 12. 测试方案

## 12.1 DSL / parser 测试

应新增：

- 单层 `if`
- `if + else`
- `if + else if + else`
- nested if
- 空 branch
- branch 内空语句
- 非法语法：
  - `if [cond] a = 1;`
  - `else` 没有前导 `if`
  - `if [num_expr]`

## 12.2 model 测试

应覆盖：

- 条件中未知变量报错
- branch 内先用后定义报错
- branch 内新临时变量可用
- branch 新临时变量不外泄
- 外层已有临时变量可在 branch 中读写
- nested if 中内层可见外层 branch 临时变量

## 12.3 simulate 测试

建议新增：

- 单层 if 命中 / 不命中
- if / else
- else if 链
- nested if 多层路径
- branch 内临时变量不泄漏
- 外层临时变量经 branch 修改后后续可见

## 12.4 solver 测试

建议新增：

- `if` 无 `else` 的 no-op merge
- `if / else` 的 `z3.If`
- `else if` 链式 merge
- nested if 生成嵌套 `z3.If`
- branch 内临时变量不泄漏到最终环境
- 外层已有临时变量参与 merge

---

## 13. 分阶段实施建议

## 13.1 第一阶段：语法与 AST

目标：

- grammar 支持 `if`
- listener 构造 AST
- AST 能 `__str__()`

交付标准：

- parser 测试通过
- DSL round-trip 成立

## 13.2 第二阶段：model 静态分析

目标：

- statement tree 映射到 model
- 递归作用域检查
- nested if 校验稳定

交付标准：

- model 测试覆盖条件与作用域规则

## 13.3 第三阶段：simulate 执行器

目标：

- concrete execution 支持 if / nested if
- block 内临时变量语义与设计一致

交付标准：

- runtime 测试稳定

## 13.4 第四阶段：solver 符号执行

目标：

- branch symbolic execution
- `z3.If` merge
- nested if 递归成立

交付标准：

- solver 测试稳定
- 与 runtime 语义一致

## 13.5 第五阶段：外围生态

目标：

- 高亮
- VSCode
- 文档
- 模板兼容性

---

## 14. 关键设计结论

本设计的核心结论如下：

1. 这次不应只增加一个“特殊的 if 语句”，而应把 operation block 升级为**递归语句块**
2. `if` 条件继续使用 `if [cond_expression]`，保持与 transition guard 一致
3. V1 支持：
   - `if`
   - `else if`
   - `else`
   - nested if
4. V1 不支持 `elif`
5. V1 不支持 branch 新临时变量向 if 外泄漏
6. runtime 与 solver 都采用“**递归执行 / 递归符号执行**”
7. solver 的本质方案是“**branch 独立执行 + 对外层可见名字做 `z3.If` merge**”
8. 该结构为后续扩展其他 operation statement 留出了明确空间

---

## 15. 推荐后续实现顺序

如果开始正式编码，建议严格按下面顺序推进：

1. grammar + listener + AST
2. model statement tree + 递归静态校验
3. simulate 递归解释器
4. solver 递归 symbolic execution 与 merge
5. 高亮 / 文档 / 模板 / VSCode

这样做的原因是：

- 先把语法树打通，后续各层讨论对象才稳定
- model 先把语义边界钉死，runtime 和 solver 才不会各自发明规则
- runtime 通常更容易调试，适合作为 solver 前的 concrete semantic 基线

---

## 16. 附：建议接受的典型 DSL 示例

```fcstm
def int mode = 0;
def int temp = 25;
def int level = 0;
def int output = 0;

state Root {
    state Active {
        during {
            if [mode == 0] {
                level = 1;

                if [temp > 80] {
                    output = 100;
                } else if [temp > 60] {
                    output = 60;
                } else {
                    output = 20;
                }
            } else if [mode == 1] {
                tmp = temp + 5;
                level = 2;
                output = tmp;
            } else {
                level = 0;
                output = 0;
            }
        }
    }

    [*] -> Active;
}
```

这段示例体现了：

- `if / else if / else`
- nested if
- branch 内临时变量
- branch 间不同赋值路径
- 仍然保持 operation block 的顺序语义
