# LANGCHECK_POSITIVE

本文收集的是“**本身就是合法 FCSTM**，但旧版 `pyfcstm.highlight.FcstmLexer.analyse_text` 仍会给出极低分”的正例。
这些例子现在作为 highlight 模块的正向回归集使用：要求它们在 **parse 成语法树** 且 **通过 `parse_dsl_node_to_state_machine(...)` 成功加载为 `StateMachine`** 的前提下，被当前实现稳定识别为 FCSTM。

## 校验说明

- 本页共 110 个例子，全部实测通过 `parse_with_grammar_entry(code, 'state_machine_dsl')`。
- 全部实测通过 `parse_dsl_node_to_state_machine(ast)` 并得到 `StateMachine` 对象。
- 当前实现下，这些例子都应被判为 FCSTM；对应回归测试要求分数 `>= 0.95`。
- 第 66-110 条为本次新增的现实业务建模正例，代码长度全部控制在 10-75 行，并逐条实测了 `FcstmLexer.analyse_text(...)`。
- 第 1-65 条标题里的 `(0.00)` 是修复前旧判定器上的复现分值，用来标识原始误判现象；第 66-110 条标题里的分数则是当前实现上的实测值。
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

## 2026-03-13 追加样例

前 35 个例子保留原语义：它们是“曾经会被低分误判，但已被修复并纳入正向回归”的样例。

下面新增的 30 个例子（36-65）与前面不同：它们同样都是**合法 FCSTM**，并且已经实测通过：

- `parse_with_grammar_entry(code, 'state_machine_dsl')`
- `parse_dsl_node_to_state_machine(ast)` 并得到 `StateMachine`

但在 **2026-03-13 当前仓库版本** 的 `pyfcstm.highlight.FcstmLexer.analyse_text(...)` 上，它们仍然会被压到 `0.00`。

这一组样例的核心思路不再是“把 FCSTM token 拆碎”，而是**反向命中当前实现里的异语言负向模式**：

- 用 `allowmixing`、`object`、`class`、`package`、`impl`、`public`、`export`、`struct`、`module`、`const` 等名字直接撞 PlantUML / Java / Go / Rust / JS 的负向规则。
- 把这些名字放进 `enter` / `exit` / `during` / `>> during` / `effect` 块里，制造大量“看起来像别的语言代码行”的文本。
- 利用 `globalThis`、`String.raw`、`java.util.function` 这类路径名，直接命中非 FCSTM 语言特征。
- 利用 `class -> do :`、`for -> do :`、`finally -> do :` 这类**行首关键字 + 行尾冒号**写法，定向触发 Python 风格的负向规则。
- 把 `pseudo` / `named` / `abstract` / `ref` / `effect` 故意塞进同一行，再叠加其它负向特征，形成“高密度混合诱饵”。

### 36. Enter Keyword Spray (0.00)

把一组异语言关键字伪装成合法变量名，集中塞进叶子状态的 `enter` 赋值块里。

```fcstm
def int allowmixing = 0;
def int object = 0;
def int class = 0;
def int package = 0;
def int impl = 0;
def int public = 0;
def int export = 0;
def int struct = 0;
def int module = 0;
def int const = 0;
state Root {
    [*] -> Work;
    state Work {
        enter {
            allowmixing = 1;
            object = 2;
            class = 3;
            package = 4;
            impl = 5;
            public = 6;
            export = 7;
            struct = 8;
            module = 9;
            const = 10;
        }
    }
}
```

### 37. Exit Keyword Spray (0.00)

改走 `exit` 分支，验证负向模式并不依赖 `enter` 关键词本身。

```fcstm
def int allowmixing = 0;
def int boundary = 0;
def int type = 0;
def int trait = 0;
def int private = 0;
def int interface = 0;
def int nullptr = 0;
def int end = 0;
def int let = 0;
state Root {
    [*] -> Work;
    state Work {
        exit {
            allowmixing = 1;
            boundary = 2;
            type = 3;
            trait = 4;
            private = 5;
            interface = 6;
            nullptr = 7;
            end = 8;
            let = 9;
        }
    }
}
```

### 38. Composite During-Before Keyword Spray (0.00)

把“关键词喷洒”搬到复合状态级别的 `during before` 块里。

```fcstm
def int allowmixing = 0;
def int annotation = 0;
def int func = 0;
def int pub = 0;
def int protected = 0;
def int namespace = 0;
def int typedef = 0;
def int function = 0;
def int module = 0;
state Root {
    [*] -> Work;
    during before {
        allowmixing = 1;
        annotation = 2;
        func = 3;
        pub = 4;
        protected = 5;
        namespace = 6;
        typedef = 7;
        function = 8;
        module = 9;
    }
    state Work;
}
```

### 39. Composite During-After Keyword Spray (0.00)

同样走复合状态，但切到 `during after`，并引入 `globalThis` / `try` 这一类更偏 JS / Python 的诱饵。

```fcstm
def int allowmixing = 0;
def int database = 0;
def int var = 0;
def int impl = 0;
def int public = 0;
def int globalThis = 0;
def int struct = 0;
def int module = 0;
def int try = 0;
state Root {
    [*] -> Work;
    during after {
        allowmixing = 1;
        database = 2;
        var = 3;
        impl = 4;
        public = 5;
        globalThis = 6;
        struct = 7;
        module = 8;
        try = 9;
    }
    state Work;
}
```

### 40. Aspect-Before Keyword Spray (0.00)

转到 `>> during before` 的 aspect 形态，确认 aspect handler 也能承载同样的误导文本。

```fcstm
def int allowmixing = 0;
def int object = 0;
def int class = 0;
def int package = 0;
def int impl = 0;
def int public = 0;
def int export = 0;
def int struct = 0;
def int module = 0;
def int const = 0;
state Root {
    [*] -> Work;
    state Work {
        >> during before {
            allowmixing = 1;
            object = 2;
            class = 3;
            package = 4;
            impl = 5;
            public = 6;
            export = 7;
            struct = 8;
            module = 9;
            const = 10;
        }
    }
}
```

### 41. Aspect-After Keyword Spray (0.00)

再换成根状态上的 `>> during after`，覆盖另一条 aspect 分支。

```fcstm
def int allowmixing = 0;
def int boundary = 0;
def int type = 0;
def int trait = 0;
def int private = 0;
def int interface = 0;
def int nullptr = 0;
def int end = 0;
def int let = 0;
state Root {
    [*] -> Work;
    >> during after {
        allowmixing = 1;
        boundary = 2;
        type = 3;
        trait = 4;
        private = 5;
        interface = 6;
        nullptr = 7;
        end = 8;
        let = 9;
    }
    state Work;
}
```

### 42. Entry Effect Keyword Spray (0.00)

不靠 lifecycle，而是把关键词集中塞进初始迁移的 `effect` 块里。

```fcstm
def int allowmixing = 0;
def int annotation = 0;
def int func = 0;
def int pub = 0;
def int protected = 0;
def int namespace = 0;
def int typedef = 0;
def int function = 0;
def int module = 0;
state Root {
    [*] -> Work effect {
        allowmixing = 1;
        annotation = 2;
        func = 3;
        pub = 4;
        protected = 5;
        namespace = 6;
        typedef = 7;
        function = 8;
        module = 9;
    }
    state Work;
}
```

### 43. Normal Effect Keyword Spray (0.00)

改成普通迁移 `A -> B effect { ... }`，保持合法语义但继续叠负向模式。

```fcstm
def int allowmixing = 0;
def int database = 0;
def int var = 0;
def int impl = 0;
def int public = 0;
def int globalThis = 0;
def int struct = 0;
def int module = 0;
def int try = 0;
state Root {
    [*] -> A;
    A -> B effect {
        allowmixing = 1;
        database = 2;
        var = 3;
        impl = 4;
        public = 5;
        globalThis = 6;
        struct = 7;
        module = 8;
        try = 9;
    }
    state A;
    state B;
}
```

### 44. Exit Effect Keyword Spray (0.00)

走 `A -> [*] effect { ... }` 分支，验证退出迁移也同样可被利用。

```fcstm
def int allowmixing = 0;
def int object = 0;
def int class = 0;
def int package = 0;
def int impl = 0;
def int public = 0;
def int export = 0;
def int struct = 0;
def int module = 0;
def int const = 0;
state Root {
    [*] -> A;
    A -> [*] effect {
        allowmixing = 1;
        object = 2;
        class = 3;
        package = 4;
        impl = 5;
        public = 6;
        export = 7;
        struct = 8;
        module = 9;
        const = 10;
    }
    state A;
}
```

### 45. Nested Effect Keyword Spray (0.00)

把 effect 攻击放到二级子状态里，确认层级不会削弱误判。

```fcstm
def int allowmixing = 0;
def int boundary = 0;
def int type = 0;
def int trait = 0;
def int private = 0;
def int interface = 0;
def int nullptr = 0;
def int end = 0;
def int let = 0;
state Root {
    [*] -> A;
    state A {
        [*] -> B;
        B -> C effect {
            allowmixing = 1;
            boundary = 2;
            type = 3;
            trait = 4;
            private = 5;
            interface = 6;
            nullptr = 7;
            end = 8;
            let = 9;
        }
        state B;
        state C;
    }
}
```

### 46. Foreign-Named Transition Chain (0.00)

完全不靠变量定义，直接把状态名和迁移源状态名改成“异语言关键字”。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    const -> do;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state const;
}
```

### 47. Forced Foreign-Named Transition Chain (0.00)

在关键词迁移链里插入 `! object -> class;`，覆盖强制迁移分支。

```fcstm
state Root {
    [*] -> allowmixing;
    ! object -> class;
    allowmixing -> do;
    package -> impl;
    public -> export;
    struct -> module;
    const -> do;
    state allowmixing;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state const;
    state do;
}
```

### 48. All-Force Into Do (0.00)

再把 `! * -> do;` 拉进来，利用 `-> do` 这一条额外负向特征。

```fcstm
state Root {
    [*] -> object;
    ! * -> do;
    allowmixing -> class;
    package -> impl;
    public -> export;
    struct -> module;
    const -> do;
    state object;
    state do;
    state allowmixing;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state const;
}
```

### 49. Exit Cascade With Keyword Sources (0.00)

混入 `class -> [*];` 这种退出迁移，让 `class` 直接出现在行首。

```fcstm
state Root {
    [*] -> allowmixing;
    class -> [*];
    object -> class;
    package -> impl;
    public -> do;
    struct -> module;
    state allowmixing;
    state class;
    state object;
    state package;
    state impl;
    state public;
    state struct;
    state module;
    state do;
}
```

### 50. Class Colon Trap (0.00)

构造 `class -> do :` 再把事件路径放到下一行，专门命中“行首关键字 + 行尾冒号”的负向规则。

```fcstm
state Root {
    [*] -> class;
    class -> do :
        /Tick;
    allowmixing -> object;
    package -> impl;
    public -> export;
    struct -> module;
    state class;
    state do;
    state allowmixing;
    state object;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
}
```

### 51. For Colon Trap (0.00)

把 `class` 换成 `for`，更贴近 Python / Ruby 风格的伪装。

```fcstm
state Root {
    [*] -> for;
    for -> do :
        /Tick;
    allowmixing -> object;
    package -> impl;
    public -> export;
    struct -> module;
    state for;
    state do;
    state allowmixing;
    state object;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
}
```

### 52. Finally Colon Trap (0.00)

再换成 `finally -> do :`，同时保留其它关键词迁移来叠加惩罚。

```fcstm
state Root {
    [*] -> finally;
    finally -> do :
        /Tick;
    allowmixing -> object;
    class -> package;
    impl -> public;
    export -> struct;
    state finally;
    state do;
    state allowmixing;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
}
```

### 53. Scoped Event GlobalThis (0.00)

不使用绝对路径，只在普通迁移上挂 `:: globalThis`，直接命中 JS/TS 关键字负向模式。

```fcstm
state Root {
    [*] -> allowmixing;
    object -> class :: globalThis;
    package -> impl;
    public -> export;
    struct -> module;
    const -> do;
    state allowmixing;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state const;
    state do;
}
```

### 54. Absolute Event `java.util.function` (0.00)

利用绝对事件路径把 `java.util.function` 原样写进 FCSTM 源码文本里。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do : /java.util.function;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state java {
        [*] -> util;
        state util;
    }
}
```

### 55. Absolute Event `String.raw` (0.00)

同样利用绝对事件路径，但换成更偏 JS/TS 的 `String.raw`。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do : /String.raw;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state String;
}
```

### 56. Ref Path `globalThis.bridge` (0.00)

把 `globalThis` 藏进合法的 handler 绝对引用路径里。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state globalThis {
        enter abstract bridge;
    }
    state Worker {
        enter alias ref /globalThis.bridge;
    }
}
```

### 57. Ref Path `String.raw` (0.00)

把 `String.raw` 放进 `exit` 的绝对引用路径里，和事件路径版本区分开。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state String {
        exit abstract raw;
    }
    state Worker {
        exit alias ref /String.raw;
    }
}
```

### 58. Ref Path `java.util.function` (0.00)

进一步把 Java 风格路径变成真正可解析的嵌套 handler 引用。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state java {
        [*] -> util;
        state util {
            enter abstract function;
        }
    }
    state Worker {
        enter alias ref /java.util.function;
    }
}
```

### 59. Dense Pseudo-Named-Abstract-Ref-Effect Line (0.00)

先把 `pseudo` / `named` / `abstract` / `ref` / `effect` 全塞进同一行，再追加一个 `enter` 关键词喷洒块把分数彻底压到 0。

```fcstm
def int allowmixing = 0;
def int object = 0;
def int class = 0;
def int package = 0;
def int impl = 0;
def int public = 0;
def int export = 0;
def int struct = 0;
def int module = 0;
def int const = 0;
state Root {
    pseudo state Meta named "m"; [*] -> allowmixing effect { allowmixing = 1; object = 2; class = 3; package = 4; impl = 5; public = 6; export = 7; struct = 8; module = 9; const = 10; } enter abstract hook; exit alias ref hook;
    allowmixing -> do;
    state allowmixing {
        enter {
            allowmixing = 1;
            object = 2;
            class = 3;
            package = 4;
            impl = 5;
            public = 6;
            export = 7;
            struct = 8;
            module = 9;
            const = 10;
        }
    }
    state do;
}
```

### 60. Dense Line Plus `String.raw` Ref (0.00)

这一版把单行高密度诱饵、`String.raw` 引用路径和额外的 `exit` 关键词喷洒叠在一起。

```fcstm
def int allowmixing = 0;
def int boundary = 0;
def int type = 0;
def int trait = 0;
def int private = 0;
def int interface = 0;
def int nullptr = 0;
def int end = 0;
def int let = 0;
state Root {
    pseudo state Meta named "m"; [*] -> Work effect { allowmixing = 1; boundary = 2; type = 3; trait = 4; private = 5; interface = 6; nullptr = 7; end = 8; let = 9; } enter abstract hook; state String { exit abstract raw; } state Work { exit alias ref /String.raw; }
    allowmixing -> do;
    state allowmixing;
    state do;
    state Sink {
        exit {
            allowmixing = 1;
            boundary = 2;
            type = 3;
            trait = 4;
            private = 5;
            interface = 6;
            nullptr = 7;
            end = 8;
            let = 9;
        }
    }
}
```

### 61. Dense Line Plus `java.util.function` Event (0.00)

和上一条不同，这里把单行高密度诱饵和 `java.util.function` 绝对事件路径、`>> during after` 关键词喷洒叠加。

```fcstm
def int allowmixing = 0;
def int annotation = 0;
def int func = 0;
def int pub = 0;
def int protected = 0;
def int namespace = 0;
def int typedef = 0;
def int function = 0;
def int module = 0;
state Root {
    pseudo state Meta named "m"; [*] -> Work effect { allowmixing = 1; annotation = 2; func = 3; pub = 4; protected = 5; namespace = 6; typedef = 7; function = 8; module = 9; } enter abstract hook; exit alias ref hook; state java { [*] -> util; state util; } state Work;
    allowmixing -> do : /java.util.function;
    state allowmixing;
    state do;
    >> during after {
        allowmixing = 1;
        annotation = 2;
        func = 3;
        pub = 4;
        protected = 5;
        namespace = 6;
        typedef = 7;
        function = 8;
        module = 9;
    }
}
```

### 62. Pseudo Sibling Plus Keyword Chain (0.00)

在关键词迁移链里额外塞一个 `pseudo state` 兄弟节点，确认伪状态不会妨碍误判构造。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    pseudo state pseudoNode;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
}
```

### 63. Named State Plus Local Event Keyword Bait (0.00)

利用 `named` 扩展名保留合法别名语义，同时继续用 `:: globalThis` 和关键词迁移压低分数。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do;
    object -> class :: globalThis;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing named "live";
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export named "pub";
    state struct;
    state module;
}
```

### 64. Deep Hierarchy Keyword Parents (0.00)

把绝对事件路径升级成 `/module.const.Tick` 这种更深的层级形式。

```fcstm
state Root {
    [*] -> allowmixing;
    allowmixing -> do : /module.const.Tick;
    object -> class;
    package -> impl;
    public -> export;
    struct -> module;
    state allowmixing;
    state do;
    state object;
    state class;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module {
        [*] -> const;
        state const;
    }
}
```

### 65. Mixed Ref And Colon Trap (0.00)

最后一条把三种不同打法叠加到一起：`class -> do :` 的冒号陷阱、`globalThis.bridge` 的绝对引用，以及整串关键词迁移。

```fcstm
state Root {
    [*] -> class;
    class -> do :
        /namespace.Tick;
    allowmixing -> object;
    package -> impl;
    public -> export;
    struct -> module;
    state class;
    state do;
    state allowmixing;
    state object;
    state package;
    state impl;
    state public;
    state export;
    state struct;
    state module;
    state globalThis {
        enter abstract bridge;
    }
    state Worker {
        enter alias ref /globalThis.bridge;
    }
    state namespace;
}
```

### 66. Elevator Door Reopen Cycle (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Elevator door controller with obstruction reopen logic
def int door_pos = 0;
def int hold_ticks = 0;
def int reopen_count = 0;

state ElevatorDoor {
    state Closed;

    state Opening {
        during {
            door_pos = door_pos + 50;
        }
    }

    state Opened {
        during {
            hold_ticks = hold_ticks + 1;
        }
    }

    state Closing {
        during {
            door_pos = door_pos - 50;
        }
    }

    [*] -> Closed;
    Closed -> Opening : HallCall effect {
        hold_ticks = 0;
    };
    Opening -> Opened : if [door_pos >= 100] effect {
        door_pos = 100;
        hold_ticks = 0;
    };
    Opened -> Closing : if [hold_ticks >= 2];
    Closing -> Opened : BeamBlocked effect {
        reopen_count = reopen_count + 1;
        door_pos = 100;
        hold_ticks = 0;
    };
    Closing -> Closed : if [door_pos <= 0] effect {
        door_pos = 0;
    };
}
```

### 67. Two-Phase Traffic Signal (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Main road plus pedestrian request phase
def int green_ticks = 0;
def int yellow_ticks = 0;
def int walk_ticks = 0;
def int ped_waiting = 0;

state TrafficSignal {
    state MainGreen {
        during {
            green_ticks = green_ticks + 1;
        }
    }

    state PedestrianPhase {
        state MainYellow {
            during {
                yellow_ticks = yellow_ticks + 1;
            }
        }

        state Walk {
            during {
                walk_ticks = walk_ticks + 1;
            }
        }

        [*] -> MainYellow;
        MainYellow -> Walk : if [yellow_ticks >= 1];
        Walk -> [*] : if [walk_ticks >= 2];
    }

    [*] -> MainGreen;
    MainGreen -> PedestrianPhase : if [ped_waiting == 1 && green_ticks >= 3] effect {
        ped_waiting = 0;
        yellow_ticks = 0;
        walk_ticks = 0;
    };
    MainGreen -> MainGreen : PedestrianRequest effect {
        ped_waiting = 1;
    };
    PedestrianPhase -> MainGreen effect {
        green_ticks = 0;
    };
}
```

### 68. Water Tank Fill Controller (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Maintain tank level and stop on overflow
def int level = 55;
def int fill_cycles = 0;
def int overflow_count = 0;

state WaterTank {
    state Idle {
        during {
            level = level - 1;
        }
    }

    state Filling {
        during {
            level = level + 4;
            fill_cycles = fill_cycles + 1;
        }
    }

    state Alarm {
        enter {
            overflow_count = overflow_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Filling : if [level <= 40];
    Filling -> Idle : if [level >= 70];
    Filling -> Alarm : if [level > 90];
    Alarm -> Idle : Reset effect {
        level = 60;
    };
}
```

### 69. Batch Mixer Recipe Flow (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Mixing skid with load, mix and discharge phases
def int mix_ticks = 0;
def int discharge_ticks = 0;
def int batch_count = 0;

state MixerSkid {
    state Ready;

    state BatchCycle {
        state Load {
            enter {
                mix_ticks = 0;
                discharge_ticks = 0;
            }
        }

        state Mix {
            during {
                mix_ticks = mix_ticks + 1;
            }
        }

        state Discharge {
            during {
                discharge_ticks = discharge_ticks + 1;
            }
        }

        [*] -> Load;
        Load -> Mix : IngredientsReady;
        Mix -> Discharge : if [mix_ticks >= 3];
        Discharge -> [*] : if [discharge_ticks >= 2];
    }

    [*] -> Ready;
    Ready -> BatchCycle : StartBatch;
    BatchCycle -> Ready effect {
        batch_count = batch_count + 1;
    };
}
```

### 70. Turnstile Entry Control (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Standard paid-entry turnstile
def int passage_count = 0;
def int alarm_count = 0;

state Turnstile {
    state Locked;
    state Unlocked;

    state Alarm {
        enter {
            alarm_count = alarm_count + 1;
        }
    }

    [*] -> Locked;
    Locked -> Unlocked : Coin;
    Locked -> Alarm : Push;
    Unlocked -> Locked : Push effect {
        passage_count = passage_count + 1;
    };
    Alarm -> Locked : Reset;
}
```

### 71. Vending Machine Dispense Cycle (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Simple snack vending workflow
def int credit = 0;
def int stock = 5;
def int vend_count = 0;

state VendingMachine {
    state Idle;

    state CreditReady {
        during {
            credit = credit + 0;
        }
    }

    state Dispensing {
        enter {
            stock = stock - 1;
            vend_count = vend_count + 1;
        }
    }

    state OutOfService;

    [*] -> Idle;
    Idle -> CreditReady : InsertCoin effect {
        credit = credit + 1;
    };
    CreditReady -> Dispensing : SelectItem effect {
        credit = credit - 1;
    };
    Dispensing -> Idle : DispenseDone;
    Dispensing -> OutOfService : if [stock <= 0];
    OutOfService -> Idle : Refill effect {
        stock = 5;
    };
}
```

### 72. Smart Lock Auto Relock (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Badge access lock with timed relock
def int relock_ticks = 0;
def int invalid_tries = 0;

state SmartLock {
    state Locked;

    state Unlocked {
        during {
            relock_ticks = relock_ticks + 1;
        }
    }

    state Alarm {
        enter {
            invalid_tries = invalid_tries + 1;
        }
    }

    [*] -> Locked;
    Locked -> Unlocked : ValidBadge effect {
        relock_ticks = 0;
    };
    Locked -> Alarm : InvalidBadge;
    Unlocked -> Locked : if [relock_ticks >= 3];
    Alarm -> Locked : MasterReset effect {
        invalid_tries = 0;
    };
}
```

### 73. Conveyor Jam Recovery (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Conveyor with manual jam clearing sequence
def int run_ticks = 0;
def int clear_ticks = 0;
def int jam_count = 0;

state ConveyorLine {
    state Stopped;

    state Running {
        during {
            run_ticks = run_ticks + 1;
        }
    }

    state Jam {
        enter {
            jam_count = jam_count + 1;
        }
    }

    state Clearing {
        during {
            clear_ticks = clear_ticks + 1;
        }
    }

    [*] -> Stopped;
    Stopped -> Running : StartCommand effect {
        run_ticks = 0;
    };
    Running -> Stopped : StopCommand;
    Running -> Jam : JamDetected;
    Jam -> Clearing : ClearJam effect {
        clear_ticks = 0;
    };
    Clearing -> Running : if [clear_ticks >= 2] effect {
        run_ticks = 0;
    };
}
```

### 74. HVAC Occupancy Scheduler (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Occupancy-based zone conditioning schedule
def int setpoint = 26;
def int prestart_ticks = 0;
def int occupied_ticks = 0;

state ZoneScheduler {
    event OccupancyStart named "occupancy-start";
    event OccupancyEnd named "occupancy-end";

    state Unoccupied {
        during {
            prestart_ticks = prestart_ticks + 1;
        }
    }

    state PreCool {
        during {
            setpoint = 23;
        }
    }

    state Occupied named "day-mode" {
        during {
            occupied_ticks = occupied_ticks + 1;
        }
    }

    [*] -> Unoccupied;
    Unoccupied -> PreCool : if [prestart_ticks >= 2];
    PreCool -> Occupied : OccupancyStart effect {
        occupied_ticks = 0;
    };
    Occupied -> Unoccupied : OccupancyEnd effect {
        setpoint = 26;
        prestart_ticks = 0;
    };
}
```

### 75. Battery Charger Three Stage (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Bulk, absorption and float charging controller
def int pack_voltage = 300;
def int charge_ticks = 0;
def int temp_c = 25;
def int fault_count = 0;

state BatteryCharger {
    state Idle;

    state Bulk {
        during {
            pack_voltage = pack_voltage + 20;
            charge_ticks = charge_ticks + 1;
        }
    }

    state Absorption {
        during {
            pack_voltage = pack_voltage + 5;
            charge_ticks = charge_ticks + 1;
        }
    }

    state Float;

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Bulk : PlugIn effect {
        charge_ticks = 0;
    };
    Bulk -> Absorption : if [pack_voltage >= 360];
    Absorption -> Float : if [charge_ticks >= 4];
    Bulk -> Fault : if [temp_c > 60];
    Absorption -> Fault : if [temp_c > 60];
    Float -> Idle : Unplug;
    Fault -> Idle : Reset effect {
        temp_c = 25;
    };
}
```

### 76. Garage Door Obstacle Handling (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Residential garage door with obstacle reversal
def int travel = 0;
def int open_hold = 0;

state GarageDoor named "garage-door" {
    event RemotePulse named "remote-pulse";
    state Closed;

    state Opening {
        during {
            travel = travel + 25;
        }
    }

    state Open {
        during {
            open_hold = open_hold + 1;
        }
    }

    state Closing {
        during {
            travel = travel - 25;
        }
    }

    [*] -> Closed;
    Closed -> Opening : RemotePulse;
    Opening -> Open : if [travel >= 100] effect {
        travel = 100;
        open_hold = 0;
    };
    Open -> Closing : if [open_hold >= 2];
    Closing -> Opening : Obstruction effect {
        travel = 25;
    };
    Closing -> Closed : if [travel <= 0] effect {
        travel = 0;
    };
}
```

### 77. Printer Job Lifecycle (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Office printer with pause and jam handling
def int pages_left = 0;
def int completed_jobs = 0;
def int error_count = 0;

state PrintServer {
    state Idle;

    state Printing {
        during {
            pages_left = pages_left - 1;
        }
    }

    state Paused;

    state Error {
        enter {
            error_count = error_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Printing : SubmitJob effect {
        pages_left = 3;
    };
    Printing -> Paused : PauseJob;
    Paused -> Printing : ResumeJob;
    Printing -> Idle : if [pages_left <= 0] effect {
        completed_jobs = completed_jobs + 1;
    };
    Printing -> Error : JamDetected;
    Error -> Idle : ClearJam effect {
        pages_left = 0;
    };
}
```

### 78. Network Link Reconnect Backoff (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Client retries with an increasing reconnect delay
def int retries = 0;
def int backoff_ticks = 0;
def int online_ticks = 0;

state NetworkClient {
    state Disconnected;
    state Connecting;

    state Online {
        during {
            online_ticks = online_ticks + 1;
        }
    }

    state Backoff {
        during {
            backoff_ticks = backoff_ticks + 1;
        }
    }

    [*] -> Disconnected;
    Disconnected -> Connecting : StartLink;
    Connecting -> Online : LinkUp effect {
        retries = 0;
        online_ticks = 0;
    };
    Connecting -> Backoff : LinkFailed effect {
        retries = retries + 1;
        backoff_ticks = 0;
    };
    Online -> Connecting : LinkDropped;
    Backoff -> Connecting : if [backoff_ticks >= retries + 1];
}
```

### 79. Boiler Burner Lockout (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Burner start-up with purge, ignition and lockout
def int purge_ticks = 0;
def int trial_count = 0;
def int run_ticks = 0;
def int lockouts = 0;

state BoilerBurner {
    state Idle;

    state Purge {
        during {
            purge_ticks = purge_ticks + 1;
        }
    }

    state Igniting;

    state Run {
        during {
            run_ticks = run_ticks + 1;
        }
    }

    state Lockout {
        enter {
            lockouts = lockouts + 1;
        }
    }

    [*] -> Idle;
    Idle -> Purge : HeatDemand effect {
        purge_ticks = 0;
    };
    Purge -> Igniting : if [purge_ticks >= 2];
    Igniting -> Run : FlameProven effect {
        run_ticks = 0;
    };
    Igniting -> Lockout : IgnitionFailed effect {
        trial_count = trial_count + 1;
    };
    Run -> Idle : DemandSatisfied;
    Lockout -> Idle : ResetBurner effect {
        trial_count = 0;
    };
}
```

### 80. EV Charger Session Flow (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Public charger session from plug-in to fault reset
def int energy_pulses = 0;
def int auth_ok = 0;
def int fault_count = 0;

state EVCharger {
    state Available;
    state Handshake;

    state Charging {
        during {
            energy_pulses = energy_pulses + 1;
        }
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Available;
    Available -> Handshake : PlugIn;
    Handshake -> Charging : Authorize effect {
        auth_ok = 1;
        energy_pulses = 0;
    };
    Handshake -> Available : CancelSession;
    Charging -> Available : Unplug effect {
        auth_ok = 0;
    };
    Charging -> Fault : GroundFault;
    Fault -> Available : ResetFault effect {
        auth_ok = 0;
    };
}
```

### 81. Refrigerator Defrost Cycle (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Refrigeration loop with defrost and drain wait
def int compressor_ticks = 0;
def int frost_level = 0;
def int drain_ticks = 0;

state Refrigerator {
    state Cooling {
        during {
            compressor_ticks = compressor_ticks + 1;
            frost_level = frost_level + 1;
        }
    }

    state Defrost {
        during {
            frost_level = frost_level - 2;
        }
    }

    state DrainWait {
        during {
            drain_ticks = drain_ticks + 1;
        }
    }

    [*] -> Cooling;
    Cooling -> Defrost : if [frost_level >= 5] effect {
        drain_ticks = 0;
    };
    Defrost -> DrainWait : if [frost_level <= 0];
    DrainWait -> Cooling : if [drain_ticks >= 2] effect {
        compressor_ticks = 0;
    };
}
```

### 82. Railway Crossing Gate (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Road crossing gate around train approach events
def int warning_ticks = 0;
def int gate_cycles = 0;
def int train_detected = 0;

state RailCrossing {
    state Clear;

    state Warning {
        during {
            warning_ticks = warning_ticks + 1;
        }
    }

    state Lowered;
    state Raising;

    [*] -> Clear;
    Clear -> Warning : TrackOccupied effect {
        train_detected = 1;
        warning_ticks = 0;
    };
    Warning -> Lowered : if [warning_ticks >= 2];
    Lowered -> Raising : TrackClear effect {
        train_detected = 0;
    };
    Raising -> Clear : GateUp effect {
        gate_cycles = gate_cycles + 1;
    };
}
```

### 83. Pump Lead-Lag Swap (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Alternate duty between primary and secondary pumps
def int primary_starts = 0;
def int secondary_starts = 0;
def int demand = 0;
def int fault_count = 0;

state PumpPair {
    state Standby;

    state PrimaryRun {
        enter {
            primary_starts = primary_starts + 1;
        }
    }

    state SecondaryRun {
        enter {
            secondary_starts = secondary_starts + 1;
        }
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Standby;
    Standby -> PrimaryRun : StartDemand effect {
        demand = 1;
    };
    PrimaryRun -> Standby : StopDemand effect {
        demand = 0;
    };
    PrimaryRun -> SecondaryRun : PrimaryFault;
    SecondaryRun -> Standby : StopDemand effect {
        demand = 0;
    };
    SecondaryRun -> Fault : SecondaryFault;
    Fault -> Standby : ResetPumps;
}
```

### 84. AGV Docking Procedure (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Automated guided vehicle docking and verification
def int align_ticks = 0;
def int dock_ticks = 0;
def int mission_count = 0;
def int dock_ok = 1;

state AGVDocking {
    state Idle;
    state Navigate;

    state Align {
        during {
            align_ticks = align_ticks + 1;
        }
    }

    pseudo state VerifyDock;

    state Docked {
        during {
            dock_ticks = dock_ticks + 1;
        }
    }

    state Error;

    [*] -> Idle;
    Idle -> Navigate : DispatchToDock;
    Navigate -> Align : AtStation effect {
        align_ticks = 0;
    };
    Align -> VerifyDock : if [align_ticks >= 2];
    VerifyDock -> Docked : if [dock_ok == 1];
    VerifyDock -> Error : if [dock_ok == 0];
    Docked -> Idle : Undock effect {
        mission_count = mission_count + 1;
    };
    Error -> Navigate : RetryDock;
}
```

### 85. Air Compressor Pressure Band (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Compressor starts and stops on pressure bands
def int pressure = 85;
def int cooldown_ticks = 0;
def int high_temp_count = 0;

state AirCompressor {
    state Off {
        during {
            pressure = pressure - 2;
        }
    }

    state Running {
        during {
            pressure = pressure + 4;
        }
    }

    state Cooldown {
        during {
            cooldown_ticks = cooldown_ticks + 1;
        }
    }

    state Fault {
        enter {
            high_temp_count = high_temp_count + 1;
        }
    }

    [*] -> Off;
    Off -> Running : if [pressure <= 70];
    Running -> Cooldown : if [pressure >= 95] effect {
        cooldown_ticks = 0;
    };
    Running -> Fault : OverTemp;
    Cooldown -> Off : if [cooldown_ticks >= 2];
    Fault -> Off : ResetCompressor effect {
        pressure = 85;
    };
}
```

### 86. Security Alarm Arming Flow (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Intrusion panel with exit and entry delays
def int exit_delay = 0;
def int entry_delay = 0;
def int siren_count = 0;

state SecurityPanel {
    event ArmAway named "arm-away";
    event Disarm named "disarm";

    state Disarmed;

    state ExitDelay {
        during {
            exit_delay = exit_delay + 1;
        }
    }

    state Armed;

    state EntryDelay {
        during {
            entry_delay = entry_delay + 1;
        }
    }

    state Alarm {
        enter {
            siren_count = siren_count + 1;
        }
    }

    [*] -> Disarmed;
    Disarmed -> ExitDelay : ArmAway effect {
        exit_delay = 0;
    };
    ExitDelay -> Armed : if [exit_delay >= 2];
    Armed -> EntryDelay : DoorOpen effect {
        entry_delay = 0;
    };
    EntryDelay -> Alarm : if [entry_delay >= 2];
    EntryDelay -> Disarmed : Disarm;
    Armed -> Disarmed : Disarm;
    Alarm -> Disarmed : Disarm;
}
```

### 87. Camera Recording Policy (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Recorder with prebuffer, clip close and upload
def int motion_ticks = 0;
def int clip_count = 0;
def int upload_ticks = 0;

state CameraRecorder {
    event MotionStart named "motion-start";
    event MotionEnd named "motion-end";

    state Standby;

    state Prebuffer {
        during {
            motion_ticks = motion_ticks + 1;
        }
    }

    state Recording {
        during {
            motion_ticks = motion_ticks + 1;
        }
    }

    state Uploading {
        during {
            upload_ticks = upload_ticks + 1;
        }
    }

    [*] -> Standby;
    Standby -> Prebuffer : MotionStart effect {
        motion_ticks = 0;
    };
    Prebuffer -> Recording : if [motion_ticks >= 1];
    Recording -> Uploading : MotionEnd effect {
        clip_count = clip_count + 1;
        upload_ticks = 0;
    };
    Uploading -> Standby : if [upload_ticks >= 2];
}
```

### 88. Solar Inverter Grid Support (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// PV inverter from sunrise wait to generation and fault
def int irradiance = 0;
def int sync_ticks = 0;
def int fault_count = 0;

state SolarInverter {
    state WaitingSun;

    state Sync {
        during {
            sync_ticks = sync_ticks + 1;
        }
    }

    state Generating {
        during {
            irradiance = irradiance + 0;
        }
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> WaitingSun;
    WaitingSun -> Sync : if [irradiance >= 4] effect {
        sync_ticks = 0;
    };
    Sync -> Generating : if [sync_ticks >= 2];
    Generating -> WaitingSun : if [irradiance <= 1];
    Generating -> Fault : GridFault;
    Fault -> WaitingSun : ResetGridFault;
}
```

### 89. Cleanroom Airlock Interlock (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Personnel airlock keeps only one door sequence active
def int transfer_ticks = 0;
def int cycle_count = 0;

state Airlock named "airlock-1" {
    state Idle;
    state OuterOpen;

    state Transfer {
        during {
            transfer_ticks = transfer_ticks + 1;
        }
    }

    state InnerOpen;

    [*] -> Idle;
    Idle -> OuterOpen : OuterRequest;
    OuterOpen -> Transfer : OuterClosed effect {
        transfer_ticks = 0;
    };
    Transfer -> InnerOpen : if [transfer_ticks >= 1];
    InnerOpen -> Idle : InnerClosed effect {
        cycle_count = cycle_count + 1;
    };
}
```

### 90. Fire Pump Weekly Test (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Scheduled weekly churn test for a fire pump
def int test_ticks = 0;
def int ready_flag = 0;
def int fail_count = 0;

state FirePumpTest {
    state Idle;

    state Testing {
        during {
            test_ticks = test_ticks + 1;
        }
    }

    state Ready {
        enter {
            ready_flag = 1;
        }
    }

    state Fault {
        enter {
            fail_count = fail_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Testing : WeeklySchedule effect {
        test_ticks = 0;
        ready_flag = 0;
    };
    Testing -> Ready : if [test_ticks >= 2];
    Testing -> Fault : TestFail;
    Ready -> Idle : TestComplete effect {
        ready_flag = 0;
    };
    Fault -> Idle : ResetTest;
}
```

### 91. Escalator Energy Save (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Escalator wakes on demand and idles after cooldown
def int people_seen = 0;
def int run_ticks = 0;
def int cooldown_ticks = 0;

state Escalator {
    state Sleep;
    state Starting;

    state Running {
        during {
            run_ticks = run_ticks + 1;
        }
    }

    state Cooldown {
        during {
            cooldown_ticks = cooldown_ticks + 1;
        }
    }

    state Fault;

    [*] -> Sleep;
    Sleep -> Starting : PersonDetected effect {
        people_seen = people_seen + 1;
    };
    Starting -> Running : MotorReady effect {
        run_ticks = 0;
    };
    Running -> Cooldown : NoPassenger effect {
        cooldown_ticks = 0;
    };
    Cooldown -> Sleep : if [cooldown_ticks >= 2];
    Running -> Fault : SafetyTrip;
    Fault -> Sleep : ResetEscalator;
}
```

### 92. Pipeline Valve Remote Local (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Remote/local handover for a pipeline block valve
def int command_source = 0;
def int cycle_count = 0;

state PipelineValve named "remote-valve" {
    event RemoteOpen named "remote-open";
    event RemoteClose named "remote-close";

    state Local;
    state RemoteClosed named "closed";
    state RemoteOpenState named "open";

    [*] -> Local;
    Local -> RemoteClosed : HandToRemote effect {
        command_source = 1;
    };
    RemoteClosed -> RemoteOpenState : RemoteOpen effect {
        cycle_count = cycle_count + 1;
    };
    RemoteOpenState -> RemoteClosed : RemoteClose effect {
        cycle_count = cycle_count + 1;
    };
    RemoteClosed -> Local : HandToLocal effect {
        command_source = 0;
    };
    RemoteOpenState -> Local : HandToLocal effect {
        command_source = 0;
    };
}
```

### 93. Medical Infusion Pump (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Infusion pump from prime to infusion and KVO
def int prime_ticks = 0;
def int volume_left = 20;
def int alarm_count = 0;

state InfusionPump {
    state Idle;

    state Priming {
        during {
            prime_ticks = prime_ticks + 1;
        }
    }

    state Infusing {
        during {
            volume_left = volume_left - 2;
        }
    }

    state KVO;

    state Alarm {
        enter {
            alarm_count = alarm_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Priming : StartSet effect {
        prime_ticks = 0;
        volume_left = 20;
    };
    Priming -> Infusing : if [prime_ticks >= 2];
    Infusing -> KVO : if [volume_left <= 0];
    Infusing -> Alarm : OcclusionDetected;
    KVO -> Idle : StopInfusion;
    Alarm -> Idle : AcknowledgeAlarm;
}
```

### 94. Data Center UPS Transfer (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// UPS transfers between mains, battery and bypass
def int battery_level = 100;
def int transfer_count = 0;
def int bypass_count = 0;

state UPSController {
    state Normal {
        during {
            battery_level = battery_level + 0;
        }
    }

    state OnBattery {
        during {
            battery_level = battery_level - 5;
        }
    }

    state Bypass {
        enter {
            bypass_count = bypass_count + 1;
        }
    }

    state Fault;

    [*] -> Normal;
    Normal -> OnBattery : MainsLost effect {
        transfer_count = transfer_count + 1;
    };
    OnBattery -> Normal : MainsRestored;
    OnBattery -> Bypass : if [battery_level <= 20];
    OnBattery -> Fault : BatteryFault;
    Bypass -> Normal : ManualReturn;
    Fault -> Normal : ResetUPS effect {
        battery_level = 100;
    };
}
```

### 95. Warehouse Sorter Merge (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Merge sorter alternates between induction and diverting
def int cartons_seen = 0;
def int divert_ticks = 0;
def int jam_count = 0;

state SorterMerge {
    state Idle;

    state Inducting {
        during {
            cartons_seen = cartons_seen + 1;
        }
    }

    state Diverting {
        during {
            divert_ticks = divert_ticks + 1;
        }
    }

    state Jam {
        enter {
            jam_count = jam_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Inducting : StartWave;
    Inducting -> Diverting : DivertCommand effect {
        divert_ticks = 0;
    };
    Diverting -> Inducting : if [divert_ticks >= 1];
    Inducting -> Jam : MergeBlocked;
    Jam -> Idle : ClearSorter;
}
```

### 96. Robot Cell Maintenance Mode (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Robot cell switches between auto, manual and fault states
def int part_count = 0;
def int fault_count = 0;

state RobotCell {
    enter abstract LockCell;
    exit abstract UnlockCell;
    >> during before abstract AuditCell;

    state Auto {
        state Load;

        state Process {
            during {
                part_count = part_count + 1;
            }
        }

        [*] -> Load;
        Load -> Process : PartPresent;
        Process -> Load : CycleComplete;
    }

    state Manual {
        enter ref /LockCell;
        exit ref /UnlockCell;
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Auto;
    Auto -> Manual : MaintenanceRequest;
    Manual -> Auto : ResumeAuto;
    Auto -> Fault : SafetyGateOpen;
    Fault -> Manual : ResetCell;
}
```

### 97. Heat Pump Defrost Recovery (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Heat pump periodically defrosts the outdoor coil
def int coil_temp = -5;
def int defrost_ticks = 0;
def int room_heat = 0;

state HeatPump {
    state Heating {
        during {
            coil_temp = coil_temp - 1;
            room_heat = room_heat + 1;
        }
    }

    state Defrost {
        during {
            coil_temp = coil_temp + 3;
            defrost_ticks = defrost_ticks + 1;
        }
    }

    state DripDelay {
        during {
            defrost_ticks = defrost_ticks + 1;
        }
    }

    state Fault;

    [*] -> Heating;
    Heating -> Defrost : if [coil_temp <= -10] effect {
        defrost_ticks = 0;
    };
    Defrost -> DripDelay : if [coil_temp >= 2] effect {
        defrost_ticks = 0;
    };
    DripDelay -> Heating : if [defrost_ticks >= 1];
    Heating -> Fault : SensorFault;
    Fault -> Heating : ResetHeatPump effect {
        coil_temp = -5;
    };
}
```

### 98. Reactor Temperature Control (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Batch reactor with heat, hold and cool phases
def int temp = 20;
def int hold_ticks = 0;
def int batch_done = 0;

state ReactorControl {
    state Idle;

    state Batch {
        state Heat {
            during {
                temp = temp + 10;
            }
        }

        state Hold {
            during {
                hold_ticks = hold_ticks + 1;
            }
        }

        state Cool {
            during {
                temp = temp - 8;
            }
        }

        [*] -> Heat;
        Heat -> Hold : if [temp >= 80] effect {
            hold_ticks = 0;
        };
        Hold -> Cool : if [hold_ticks >= 3];
        Cool -> [*] : if [temp <= 30];
    }

    state Abort;

    [*] -> Idle;
    Idle -> Batch : StartBatch effect {
        temp = 20;
    };
    Batch -> Idle effect {
        batch_done = batch_done + 1;
    };
    Batch -> Abort : EmergencyStop;
    Abort -> Idle : ResetReactor effect {
        temp = 20;
    };
}
```

### 99. Loading Dock Leveler (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Dock leveler deploys, serves a truck and returns home
def int platform_pos = 0;
def int service_ticks = 0;
def int fault_count = 0;

state DockLeveler {
    state Stored;

    state Deploying {
        during {
            platform_pos = platform_pos + 50;
        }
    }

    state Service {
        during {
            service_ticks = service_ticks + 1;
        }
    }

    state Returning {
        during {
            platform_pos = platform_pos - 50;
        }
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Stored;
    Stored -> Deploying : DockTruck;
    Deploying -> Service : if [platform_pos >= 100] effect {
        platform_pos = 100;
        service_ticks = 0;
    };
    Service -> Returning : LoadComplete;
    Returning -> Stored : if [platform_pos <= 0] effect {
        platform_pos = 0;
    };
    Service -> Fault : VehicleMoved;
    Fault -> Stored : ResetLeveler effect {
        platform_pos = 0;
    };
}
```

### 100. Wind Turbine Yaw Alignment (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Wind turbine aligns nacelle before generating power
def int yaw_error = 12;
def int power_ticks = 0;
def int storm_count = 0;

state WindTurbine {
    state Parked;

    state Yawing {
        during {
            yaw_error = yaw_error - 4;
        }
    }

    state Generating {
        during {
            power_ticks = power_ticks + 1;
        }
    }

    state StormLock {
        enter {
            storm_count = storm_count + 1;
        }
    }

    [*] -> Parked;
    Parked -> Yawing : WindAvailable;
    Yawing -> Generating : if [yaw_error <= 0] effect {
        power_ticks = 0;
    };
    Generating -> Parked : WindGone effect {
        yaw_error = 12;
    };
    Generating -> StormLock : HighWind;
    StormLock -> Parked : ResetTurbine effect {
        yaw_error = 12;
    };
}
```

### 101. Reservoir Level Band Control (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Reservoir fill control with normal, full and alarm bands
def int level = 50;
def int fill_ticks = 0;
def int alarm_count = 0;

state Reservoir {
    state Normal {
        during {
            level = level - 1;
        }
    }

    state Filling {
        during {
            level = level + 3;
            fill_ticks = fill_ticks + 1;
        }
    }

    state Full;

    state Alarm {
        enter {
            alarm_count = alarm_count + 1;
        }
    }

    [*] -> Normal;
    Normal -> Filling : if [level <= 35] effect {
        fill_ticks = 0;
    };
    Filling -> Full : if [level >= 70];
    Full -> Normal : DemandDraw effect {
        level = 60;
    };
    Filling -> Alarm : if [fill_ticks >= 20];
    Alarm -> Normal : ResetReservoir effect {
        level = 50;
    };
}
```

### 102. Parcel Locker Pickup Session (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Locker reservation expires if pickup never happens
def int reserve_ticks = 0;
def int door_ticks = 0;
def int expired_count = 0;

state ParcelLocker {
    event PickupCode named "pickup-code";

    state Available;

    state Reserved {
        during {
            reserve_ticks = reserve_ticks + 1;
        }
    }

    state DoorOpen {
        during {
            door_ticks = door_ticks + 1;
        }
    }

    state Expired {
        enter {
            expired_count = expired_count + 1;
        }
    }

    state Fault;

    [*] -> Available;
    Available -> Reserved : PlaceParcel effect {
        reserve_ticks = 0;
    };
    Reserved -> DoorOpen : PickupCode effect {
        door_ticks = 0;
    };
    Reserved -> Expired : if [reserve_ticks >= 3];
    DoorOpen -> Available : if [door_ticks >= 1];
    DoorOpen -> Fault : DoorForced;
    Expired -> Available : ClearExpired;
    Fault -> Available : ResetLocker;
}
```

### 103. CNC Spindle Warmup Sequence (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// CNC spindle warms up before cutting production parts
def int warm_ticks = 0;
def int cut_ticks = 0;
def int part_count = 0;
def int fault_count = 0;

state CNCMachine {
    >> during before abstract SampleSpindle;

    state Idle;

    state Warmup {
        during {
            warm_ticks = warm_ticks + 1;
        }
    }

    state Ready;

    state Cutting {
        during {
            cut_ticks = cut_ticks + 1;
        }
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> Warmup : StartMachine effect {
        warm_ticks = 0;
    };
    Warmup -> Ready : if [warm_ticks >= 2];
    Ready -> Cutting : StartCycle effect {
        cut_ticks = 0;
    };
    Cutting -> Ready : if [cut_ticks >= 3] effect {
        part_count = part_count + 1;
    };
    Cutting -> Fault : SpindleTrip;
    Fault -> Idle : ResetMachine;
}
```

### 104. Building Access Visitor Flow (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Lobby visitor flow from badge scan to door release
def int approval_ticks = 0;
def int release_ticks = 0;
def int alarm_count = 0;

state VisitorAccess {
    state Idle;
    state BadgeScan;

    state Approval {
        during {
            approval_ticks = approval_ticks + 1;
        }
    }

    state DoorRelease {
        during {
            release_ticks = release_ticks + 1;
        }
    }

    state Alarm {
        enter {
            alarm_count = alarm_count + 1;
        }
    }

    [*] -> Idle;
    Idle -> BadgeScan : BadgePresented;
    BadgeScan -> Approval : VisitorSelected effect {
        approval_ticks = 0;
    };
    Approval -> DoorRelease : HostApproved effect {
        release_ticks = 0;
    };
    Approval -> Alarm : if [approval_ticks >= 3];
    DoorRelease -> Idle : if [release_ticks >= 1];
    Alarm -> Idle : ResetLobby;
}
```

### 105. Machine Vision Inspection Cell (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Inspection cell captures an image and branches on result
def int capture_ticks = 0;
def int reject_count = 0;
def int inspection_ok = 1;

state VisionCell {
    state Waiting;

    state Capture {
        during {
            capture_ticks = capture_ticks + 1;
        }
    }

    pseudo state DecideGrade;
    state Pass;

    state Reject {
        enter {
            reject_count = reject_count + 1;
        }
    }

    state Fault;

    [*] -> Waiting;
    Waiting -> Capture : PartArrived effect {
        capture_ticks = 0;
    };
    Capture -> DecideGrade : if [capture_ticks >= 1];
    DecideGrade -> Pass : if [inspection_ok == 1];
    DecideGrade -> Reject : if [inspection_ok == 0];
    Pass -> Waiting : TransferPart;
    Reject -> Waiting : BinReject;
    Capture -> Fault : CameraFault;
    Fault -> Waiting : ResetVision;
}
```

### 106. Fleet Drone Mission Supervisor (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Drone mission with takeoff, mission, return and error handling
def int leg_ticks = 0;
def int sortie_count = 0;
def int battery_low = 0;

state DroneMission {
    state Ready;

    state Takeoff {
        during {
            leg_ticks = leg_ticks + 1;
        }
    }

    state Mission {
        state Survey {
            during {
                leg_ticks = leg_ticks + 1;
            }
        }

        state Deliver;

        [*] -> Survey;
        Survey -> Deliver : WaypointReached;
        Deliver -> [*] : PackageDropped;
    }

    state ReturnHome;
    state Error;

    [*] -> Ready;
    Ready -> Takeoff : Launch effect {
        leg_ticks = 0;
    };
    Takeoff -> Mission : if [leg_ticks >= 1] effect {
        leg_ticks = 0;
    };
    Mission -> ReturnHome : if [battery_low == 1];
    ReturnHome -> Ready : Landed effect {
        sortie_count = sortie_count + 1;
    };
    Mission -> Error : LostLink;
    Error -> Ready : ResetDrone effect {
        battery_low = 0;
    };
}
```

### 107. Water Treatment Backwash (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Filter train backwashes when pressure drop rises too high
def int filter_dp = 0;
def int rinse_ticks = 0;
def int service_count = 0;
def int fault_count = 0;

state FilterTrain {
    state Filtering {
        during {
            filter_dp = filter_dp + 1;
        }
    }

    state Backwash {
        during {
            filter_dp = filter_dp - 2;
        }
    }

    state Rinse {
        during {
            rinse_ticks = rinse_ticks + 1;
        }
    }

    state Service;

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Filtering;
    Filtering -> Backwash : if [filter_dp >= 5] effect {
        rinse_ticks = 0;
    };
    Backwash -> Rinse : if [filter_dp <= 0];
    Rinse -> Service : if [rinse_ticks >= 2] effect {
        service_count = service_count + 1;
    };
    Service -> Filtering : ReturnToFilter;
    Filtering -> Fault : PumpTrip;
    Fault -> Filtering : ResetTrain effect {
        filter_dp = 0;
    };
}
```

### 108. Cold Storage Door Alarm (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Cold room alarm when the insulated door stays open too long
def int open_ticks = 0;
def int alarm_count = 0;

state ColdRoomDoor {
    state Closed;

    state Open {
        during {
            open_ticks = open_ticks + 1;
        }
    }

    state Alarm {
        enter {
            alarm_count = alarm_count + 1;
        }
    }

    state Acked;

    [*] -> Closed;
    Closed -> Open : DoorOpened effect {
        open_ticks = 0;
    };
    Open -> Closed : DoorClosed;
    Open -> Alarm : if [open_ticks >= 2];
    Alarm -> Acked : SilenceAlarm;
    Acked -> Closed : DoorClosed;
}
```

### 109. Microgrid Islanding Controller (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Microgrid islands on utility loss and later resynchronizes
def int sync_ticks = 0;
def int island_count = 0;
def int fault_count = 0;

state Microgrid {
    event UtilityRecovered named "utility-recovered";

    state GridTied;

    state IslandPrep {
        during {
            sync_ticks = sync_ticks + 1;
        }
    }

    state Islanded;

    state Resync {
        during {
            sync_ticks = sync_ticks + 1;
        }
    }

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> GridTied;
    GridTied -> IslandPrep : UtilityLost effect {
        sync_ticks = 0;
    };
    IslandPrep -> Islanded : if [sync_ticks >= 1] effect {
        island_count = island_count + 1;
    };
    Islanded -> Resync : UtilityRecovered effect {
        sync_ticks = 0;
    };
    Resync -> GridTied : if [sync_ticks >= 2];
    Islanded -> Fault : InverterFault;
    Fault -> GridTied : ResetMicrogrid;
}
```

### 110. Packaging Cartoner Changeover (1.00)

现实业务建模正例，当前 `analyse_text` 得分为 `1.00`。

```fcstm
// Cartoner line handles starvation, recipe change and jam reset
def int carton_count = 0;
def int starve_ticks = 0;
def int changeover_ticks = 0;
def int fault_count = 0;

state Cartoner {
    state Production {
        during {
            carton_count = carton_count + 1;
        }
    }

    state Starve {
        during {
            starve_ticks = starve_ticks + 1;
        }
    }

    state Changeover named "recipe-change" {
        during {
            changeover_ticks = changeover_ticks + 1;
        }
    }

    state Ready;

    state Fault {
        enter {
            fault_count = fault_count + 1;
        }
    }

    [*] -> Production;
    Production -> Starve : NoInfeed effect {
        starve_ticks = 0;
    };
    Starve -> Production : ProductArrived;
    Production -> Changeover : RecipeChange effect {
        changeover_ticks = 0;
    };
    Changeover -> Ready : if [changeover_ticks >= 2];
    Ready -> Production : ResumeRun;
    Production -> Fault : CartonJam;
    Fault -> Ready : ResetCartoner;
}
```
