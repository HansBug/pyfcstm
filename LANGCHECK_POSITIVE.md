# LANGCHECK_POSITIVE

本文收集的是“**本身就是合法 FCSTM**，但旧版 `pyfcstm.highlight.FcstmLexer.analyse_text` 仍会给出极低分”的正例。
这些例子现在作为 highlight 模块的正向回归集使用：要求它们在 **parse 成语法树** 且 **通过 `parse_dsl_node_to_state_machine(...)` 成功加载为 `StateMachine`** 的前提下，被当前实现稳定识别为 FCSTM。

## 校验说明

- 本页共 35 个例子，全部实测通过 `parse_with_grammar_entry(code, 'state_machine_dsl')`。
- 全部实测通过 `parse_dsl_node_to_state_machine(ast)` 并得到 `StateMachine` 对象。
- 当前实现下，这些例子都应被判为 FCSTM；对应回归测试要求分数 `>= 0.95`。
- 标题里保留的 `(0.00)` 是修复前旧判定器上的复现分值，用来标识原始误判现象。
- 共同利用点：判定器高度依赖“同一行内的结构正则”，而 FCSTM 语法允许在 token 之间自由换行，并允许插入会被解析器跳过的 `//` / `#` 注释。

## 例子

### 1. Minimal Leaf Stair-Step (0.00)

把 `state`、状态名和 `;` 分散到三行，直接绕开 `state_decl`。

```fcstm
state
S
;
```

### 2. Pseudo Leaf Stair-Step (0.00)

连 `pseudo state` 也拆成逐 token 换行，避免被 `state_decl` 捕获。

```fcstm
pseudo
state
P
;
```

### 3. Named Leaf Stair-Step (0.00)

保留 `named` 扩展名，但把关键 token 全部分行。

```fcstm
state
Named
named
"alias"
;
```

### 4. Slash-Comment Split Leaf (0.00)

用 `//` 注释把 `state` 和状态名隔开；解析器会跳过注释，判定器只看到断行。

```fcstm
state // split
Slash
;
```

### 5. Hash-Comment Split Leaf (0.00)

同样利用 `#` 注释打断 `state ... ;` 的同一行结构。

```fcstm
state # split
Hash
;
```

### 6. Composite With Split Entry (0.00)

根状态做成复合状态，但把状态头、初始迁移、子状态声明都拆开。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    state
    A
    ;
}
```

### 7. Composite With Split Normal Transition (0.00)

普通迁移的箭头和分号分行，规避 `transition_pattern`。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    A
    ->
    B
    ;
    state
    A
    ;
    state
    B
    ;
}
```

### 8. Composite With Split Exit Transition (0.00)

对 `A -> [*]` 这种退出迁移同样采用分号另起一行。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    A
    ->
    [*]
    ;
    state
    A
    ;
}
```

### 9. Split Force Transition (0.00)

强制迁移 `! A -> B ;` 拆成四段，语义仍成立。

```fcstm
state
Root
{
    !
    A
    ->
    B
    ;
    [*]
    ->
    A
    ;
    state
    A
    ;
    state
    B
    ;
}
```

### 10. Split All-Force Transition (0.00)

把 `! * -> [*] ;` 拆散，覆盖 all-force 语法分支。

```fcstm
state
Root
{
    !
    *
    ->
    [*]
    ;
    [*]
    ->
    A
    ;
    state
    A
    ;
}
```

### 11. Multiline Int Def (0.00)

顶层 `def int` 完全按 token 级别分行，规避 `def_decl`。

```fcstm
def
int
x
=
0
;
state
S
;
```

### 12. Multiline Float Def Expr (0.00)

浮点定义外加多行表达式，验证表达式不会重新触发正向模式。

```fcstm
def
float
gain
=
1
+
2
/
3
;
state
S
;
```

### 13. Split Event Declaration (0.00)

事件声明本身也只靠换行就能躲过 `event_decl`。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    event
    Tick
    ;
    state
    A
    ;
}
```

### 14. Split Named Event Declaration (0.00)

给事件增加 `named` 别名，同时保持整条声明不在同一行闭合。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    event
    Tick
    named
    "tick"
    ;
    state
    A
    ;
}
```

### 15. Split Enter Operations (0.00)

把 `enter hook { ... }` 拆成纵向结构，避免 `lifecycle_block`。

```fcstm
def
int
x
=
0
;
state
Leaf
{
    enter
    hook
    {
        x
        =
        1
        ;
    }
}
```

### 16. Split Enter Abstract (0.00)

使用 `enter abstract hook ;` 分支，并强制每个关键词各占一行。

```fcstm
state
Leaf
{
    enter
    abstract
    hook
    ;
}
```

### 17. Split Enter Ref (0.00)

先声明一个抽象退出函数，再让 `enter` 通过 `ref` 引用它。

```fcstm
state
Leaf
{
    exit
    abstract
    base
    ;
    enter
    alias
    ref
    base
    ;
}
```

### 18. Split Exit Operations (0.00)

与 enter 对称，`exit hook { ... }` 也能被完全拆开。

```fcstm
def
int
x
=
0
;
state
Leaf
{
    exit
    hook
    {
        x
        =
        2
        ;
    }
}
```

### 19. Split Exit Abstract Doc (0.00)

改用带原始文档块的 `exit abstract` 分支，文档注释不会被计分。

```fcstm
state
Leaf
{
    exit
    abstract
    hook
    /* doc */
}
```

### 20. Split Exit Ref Absolute (0.00)

用绝对 `ref` 路径 `/base`，并把 `/` 与标识符分行。

```fcstm
state
Leaf
{
    enter
    abstract
    base
    ;
    exit
    alias
    ref
    /
    base
    ;
}
```

### 21. Split Leaf During Operations (0.00)

叶子状态里的 `during` 无 aspect，但通过函数名换行规避 bare/block 检测。

```fcstm
def
int
x
=
0
;
state
Leaf
{
    during
    hook
    {
        x
        =
        x
        +
        1
        ;
    }
}
```

### 22. Split Composite During Before Ops (0.00)

复合状态必须有 `before/after`，这里把 `during before hook {}` 拆成纵向写法。

```fcstm
def
int
x
=
0
;
state
Root
{
    [*]
    ->
    A
    ;
    during
    before
    hook
    {
        x
        =
        1
        ;
    }
    state
    A
    ;
}
```

### 23. Split Composite During After Abstract (0.00)

覆盖复合状态上的 `during after abstract` 分支。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    during
    after
    abstract
    hook
    ;
    state
    A
    ;
}
```

### 24. Split Composite During Before Ref (0.00)

同一复合状态里先定义抽象 during，再用 `ref` 指回去。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    during
    before
    abstract
    base
    ;
    during
    before
    alias
    ref
    base
    ;
    state
    A
    ;
}
```

### 25. Split During Aspect Ops (0.00)

把 `>> during before hook {}` 的每个关键词拆开，规避 aspect 正则。

```fcstm
def
int
x
=
0
;
state
Leaf
{
    >>
    during
    before
    hook
    {
        x
        =
        1
        ;
    }
}
```

### 26. Split During Aspect Abstract Doc (0.00)

利用 `>> during after abstract ... /*doc*/` 这个分支，再借助文档块收尾。

```fcstm
state
Leaf
{
    >>
    during
    after
    abstract
    hook
    /* doc */
}
```

### 27. Split Transition Event Auto-Create (0.00)

迁移使用 `:: Tick`，不预先声明事件，依赖 model 自动补建事件对象。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    A
    ->
    B
    ::
    Tick
    ;
    state
    A
    ;
    state
    B
    ;
}
```

### 28. Split Transition Absolute Event Path (0.00)

改成绝对事件路径 `: / Tick ;`，同时把 `/` 也单独占行。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    A
    ->
    B
    :
    /
    Tick
    ;
    state
    A
    ;
    state
    B
    ;
}
```

### 29. Split Transition Guard (0.00)

守卫条件 `: if [x > 0]` 逐 token 摊开，避免 rich/plain transition 识别。

```fcstm
def
int
x
=
0
;
state
Root
{
    [*]
    ->
    A
    ;
    A
    ->
    B
    :
    if
    [
        x
        >
        0
    ]
    ;
    state
    A
    ;
    state
    B
    ;
}
```

### 30. Split Transition Effect Block (0.00)

把 `effect { ... }` 整块纵向展开，保持迁移合法但不命中迁移正则。

```fcstm
def
int
x
=
0
;
state
Root
{
    [*]
    ->
    A
    ;
    A
    ->
    B
    effect
    {
        x
        =
        3
        ;
    }
    state
    A
    ;
    state
    B
    ;
}
```

### 31. Nested Absolute Ref (0.00)

在父状态定义命名函数，子状态里用绝对路径 `/helper` 引用。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    enter
    abstract
    helper
    ;
    state
    A
    {
        [*]
        ->
        B
        ;
        enter
        alias
        ref
        /
        helper
        ;
        state
        B
        ;
    }
}
```

### 32. Pseudo Substate With Split Entry (0.00)

对子状态使用 `pseudo state`，配合拆开的初始迁移。

```fcstm
state
Root
{
    [*]
    ->
    P
    ;
    pseudo
    state
    P
    ;
}
```

### 33. Mixed Comments And No-Op Statements (0.00)

夹杂空语句、`//` 注释和 `#` 注释，确认这些噪声不会抬分。

```fcstm
state
Root
{
    ;
    [*] // init source
    ->
    A
    ;
    ;
    state # child decl
    A
    ;
    ;
}
```

### 34. Split Dotted Ref Path (0.00)

绝对 `ref` 路径的 `.` 也可以拆出来，依然能正确解析并解析引用。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    state
    A
    {
        [*]
        ->
        B
        ;
        exit
        abstract
        helper
        ;
        state
        B
        {
            enter
            alias
            ref
            /
            A
            .
            helper
            ;
        }
    }
}
```

### 35. Deep Hierarchy Auto-Created Path Event (0.00)

更深层次地利用 `/A.Tick` 这种自动建事件路径，覆盖层级事件解析。

```fcstm
state
Root
{
    [*]
    ->
    A
    ;
    state
    A
    {
        [*]
        ->
        B
        ;
        B
        ->
        [*]
        :
        /
        A
        .
        Tick
        ;
        state
        B
        ;
    }
}
```
