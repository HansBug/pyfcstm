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
