# FSM 模拟运行器设计文档

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.2.0 | 2026-03-06 | 补充伪状态和退出转换的验证规则，新增 9 个复杂测试用例 | Claude |
| 0.1.0 | 2026-03-06 | 初始版本，定义核心概念和执行语义 | Claude |

---

## 1. 核心概念

### 1.1 状态类型

- **叶子状态 (Leaf State)**: 没有子状态的状态
- **复合状态 (Composite State)**: 包含子状态的状态
- **伪状态 (Pseudo State)**: 特殊的叶子状态，跳过祖先的 aspect actions
- **可停靠状态 (Stoppable State)**: 叶子状态且非伪状态，可以作为 cycle 的终点

### 1.2 生命周期动作

- **enter**: 进入状态时执行
- **during**: 在状态中执行（每个 cycle 都会执行）
- **exit**: 离开状态时执行

### 1.3 方面动作 (Aspect Actions)

- **>> during before**: 在所有后代叶子状态的 during 之前执行
- **>> during after**: 在所有后代叶子状态的 during 之后执行
- 伪状态会跳过祖先的 aspect actions

### 1.4 转换类型

- **状态间转换**: A -> B
- **自转换**: A -> A
- **初始转换**: [*] -> A（从父状态进入子状态）
- **退出转换**: A -> [*]（从子状态退出到父状态）

---

## 2. 执行语义

### 2.1 Step 语义

**定义**: 执行一次转换，或在当前状态执行一次 during

**执行流程**:
1. 如果当前在叶子状态：
   - 按顺序检查该状态的所有转换（transitions_from）
   - 找到第一个满足条件的转换并执行
   - 如果没有转换可触发，执行当前状态的 during（包含祖先 aspect actions）

2. 如果当前在复合状态：
   - 按顺序检查该状态的初始转换（init_transitions）
   - 找到第一个满足条件的转换并执行，进入子状态

**转换执行**:
1. 执行源状态的 exit 动作
2. 执行转换的 effect
3. 执行目标状态的 enter 动作
4. 如果目标是复合状态，继续处理初始转换

### 2.2 Cycle 语义

**定义**: 执行多个 step，直到到达一个 stoppable 状态

**执行流程**:
1. 重复执行 step，直到满足以下任一条件：
   - 到达一个 stoppable 状态（叶子状态且非伪状态）
   - 确认没有任何转换可以触发（停在当前叶子状态）
   - 状态机结束

2. 到达 stoppable 状态后，执行该状态的 during 动作

**关键约束**:
- Cycle 的终点必须是 stoppable 状态
- 复合状态、伪状态不能作为 cycle 的终点

### 2.3 转换验证规则

**规则**: 从 stoppable 状态转换到 non-stoppable 状态时，必须验证最终能到达 stoppable 状态

**验证方法**:
1. 模拟执行从 non-stoppable 状态开始的所有后续转换
2. 过程中可能经过：
   - 多级 non-stoppable 状态
   - 多个伪状态
   - 带有事件/守卫/效果的转换
   - 各种 enter/during/exit 动作
3. 只有当最终到达一个 stoppable 状态时，才认为原始转换有效
4. 如果无法到达 stoppable 状态，则该转换不应触发，尝试下一个转换

**示例**:
```
A (stoppable) -> B (non-stoppable) -> C (stoppable)           ✓ 有效
A (stoppable) -> B (non-stoppable, 无初始转换)                ✗ 无效
A (stoppable) -> B (non-stoppable) -> C (non-stoppable)       ✗ 无效（C 也是 non-stoppable）
A (stoppable) -> B (pseudo) -> C (pseudo)                     ✗ 无效（伪状态不是 stoppable）
A (stoppable) -> B (non-stoppable) -> [*] -> 状态机结束       ✓ 有效（整个状态机结束）
A (stoppable) -> B (non-stoppable) -> [*] -> 父状态           ✗ 无效（退到复合状态，不是 stoppable）
```

**退出转换的特殊规则**:
- 如果退出转换 `[*]` 导致整个状态机结束（栈为空），则该转换有效
- 如果退出转换 `[*]` 只是退到父状态（父状态是复合状态），则该转换无效
- 判断方法：检查退出后的状态栈，如果为空则有效，否则检查栈顶是否为 stoppable

---

## 3. 执行顺序详解

### 3.1 进入状态的执行顺序

当进入一个状态时：
1. 执行该状态的 enter 动作
2. 如果是叶子状态：
   - 执行祖先的 >> during before（从根到叶）
   - 执行自己的 during
   - 执行祖先的 >> during after（从叶到根）
3. 如果是复合状态：
   - 处理初始转换，进入子状态

### 3.2 During 动作的执行顺序

对于叶子状态 S，during 的完整执行顺序：
1. 根状态的 >> during before
2. 父状态的 >> during before
3. ...（按层级从根到叶）
4. S 的 during
5. ...（按层级从叶到根）
6. 父状态的 >> during after
7. 根状态的 >> during after

**伪状态的特殊规则**:
- 伪状态会跳过所有祖先的 aspect actions（>> during before/after）
- 伪状态仍然会执行自己的 during 动作
- 伪状态执行完 during 后立即继续转换，不会停留
- 伪状态不能作为 cycle 的终点（不是 stoppable）

### 3.3 转换的执行顺序

执行转换 A -> B 时：
1. 执行 A 的 exit 动作
2. 执行转换的 effect
3. 执行 B 的 enter 动作
4. **如果 B 是叶子状态（包括伪状态），执行 B 的 during**
5. 如果 B 是复合状态，处理初始转换
6. 如果 B 是 stoppable 状态，cycle 在此停止

### 3.4 复合状态的初始转换

当进入复合状态 P 时：
1. 执行 P 的 enter 动作
2. 检查 P 的初始转换（init_transitions）
3. 找到第一个满足条件的初始转换并执行
4. 进入子状态，重复上述过程

**特殊情况**:
- 如果初始转换需要事件但未提供，则无法进入子状态
- 这种情况下，从外部转换到 P 的转换应被视为无效（无法到达 stoppable）

---

## 4. 测试用例

### 4.1 基础测试：简单转换

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }
    state B {
        during {
            counter = counter + 10;
        }
    }
    [*] -> A;
    A -> B :: Go;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle()` | A | 2 | 无转换，执行 A.during |
| `runtime.cycle(['Root.A.Go'])` | B | 12 | A->B，执行 B.during |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle:
  无转换可触发
  A.during:                 1 + 1 = 2

第3次 cycle (提供 Go 事件):
  A.exit
  A->B
  B.enter
  B.during:                 2 + 10 = 12
```

### 4.2 复合状态测试

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        state B2 {
            during {
                counter = counter + 100;
            }
        }
        [*] -> B1;
        B1 -> B2 :: Next;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | B1 | 11 | A->B->B1，执行 B1.during |
| `runtime.cycle(['Root.B.B1.Next'])` | B2 | 111 | B1->B2，执行 B2.during |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  A.exit
  A->B
  B.enter
  B->[*]->B1 (初始转换)
  B1.enter
  B1.during:                1 + 10 = 11

第3次 cycle (提供 Next 事件):
  B1.exit
  B1->B2
  B2.enter
  B2.during:                11 + 100 = 111
```

### 4.3 转换验证测试：无法到达 stoppable

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1;
        // 注意：B 没有初始转换！
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | A | 2 | A->B 无效（B 无法到达 stoppable），停在 A，执行 A.during |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  A->B 验证：B 没有初始转换，无法进入子状态，无法到达 stoppable
  验证失败，停在 A
  A.during:                 1 + 1 = 2
```

### 4.4 转换验证测试：需要事件的初始转换

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        [*] -> B1 :: Start;  // 需要 Start 事件
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | A | 2 | A->B 无效（B 需要 Start 事件才能进入 B1），停在 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB', 'Root.B.Start'])` | B1 | 12 | A->B->B1，执行 B1.during |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  A->B 验证：B->[*]->B1 需要 Start 事件，但未提供，无法到达 stoppable
  验证失败，停在 A
  A.during:                 1 + 1 = 2

第3次 cycle (提供 GoB 和 Start 事件):
  A.exit
  A->B
  B.enter
  B->[*]->B1 (Start 事件满足)
  B1.enter
  B1.during:                2 + 10 = 12
```

### 4.5 方面动作测试

```python
dsl_code = '''
def int trace = 0;
state Root {
    >> during before {
        trace = trace * 10 + 1;
    }
    >> during after {
        trace = trace * 10 + 3;
    }

    state A {
        during {
            trace = trace * 10 + 2;
        }
    }

    [*] -> A;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | trace | 说明 |
|------|----------|-------|------|
| `runtime.cycle()` | A | 123 | 进入 A，执行 before(1) -> during(2) -> after(3) |
| `runtime.cycle()` | A | 123123 | 执行 before(1) -> during(2) -> after(3) |

**详细计算**:
```
初始: trace = 0

第1次 cycle:
  进入 A
  A.during:
    Root >> during before:  0 * 10 + 1 = 1
    A.during:               1 * 10 + 2 = 12
    Root >> during after:   12 * 10 + 3 = 123

第2次 cycle:
  无转换可触发
  A.during:
    Root >> during before:  123 * 10 + 1 = 1231
    A.during:               1231 * 10 + 2 = 12312
    Root >> during after:   12312 * 10 + 3 = 123123
```

### 4.6 伪状态测试

```python
dsl_code = '''
def int trace = 0;
state Root {
    >> during before {
        trace = trace * 10 + 1;
    }
    >> during after {
        trace = trace * 10 + 3;
    }

    pseudo state A {
        during {
            trace = trace * 10 + 2;
        }
    }

    [*] -> A;
    A -> [*] : if [trace >= 2];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | trace | 说明 |
|------|----------|-------|------|
| `runtime.cycle()` | A | 2 | 进入 A，跳过 aspect，只执行 during(2) |
| `runtime.cycle()` | 已结束 | 2 | A->[*]，退出 |

**详细计算**:
```
初始: trace = 0

第1次 cycle:
  进入 A (伪状态)
  A.during:                 0 * 10 + 2 = 2  (跳过 aspect actions)
  检查转换 A->[*]：trace >= 2 满足
  A.exit
  A->[*] (状态机结束)
```

**注意**: 伪状态不是 stoppable，但如果有转换可触发，会立即执行转换。

### 4.7 复杂链路测试：多级 non-stoppable

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1 {
            state B1a {
                during {
                    counter = counter + 10;
                }
            }
            [*] -> B1a;
        }
        [*] -> B1;
    }

    state C {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> B :: GoB;
    A -> C :: GoC;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | B1a | 11 | A->B->B1->B1a，执行 B1a.during |
| 重新开始 | | | |
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoC'])` | C | 101 | A->C，执行 C.during |

**详细计算**:
```
场景1 (A->B):
初始: counter = 0
第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  A.exit
  A->B
  B.enter
  B->[*]->B1 (初始转换)
  B1.enter
  B1->[*]->B1a (初始转换)
  B1a.enter
  B1a.during:               1 + 10 = 11

场景2 (A->C):
初始: counter = 0
第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoC 事件):
  A.exit
  A->C
  C.enter
  C.during:                 1 + 100 = 101
```

### 4.8 转换优先级测试

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }
    state B {
        during {
            counter = counter + 10;
        }
    }
    state C {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> B : if [counter >= 5];
    A -> C : if [counter >= 3];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle()` | A | 2 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 3 | 无转换（A->B 不满足），执行 A.during |
| `runtime.cycle()` | C | 103 | A->C 满足（优先级低但先满足），执行 C.during |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle:
  检查转换：A->B (counter >= 5) 不满足，A->C (counter >= 3) 不满足
  A.during:                 1 + 1 = 2

第3次 cycle:
  检查转换：A->B (counter >= 5) 不满足，A->C (counter >= 3) 不满足
  A.during:                 2 + 1 = 3

第4次 cycle:
  检查转换：A->B (counter >= 5) 不满足，A->C (counter >= 3) 满足
  A.exit
  A->C
  C.enter
  C.during:                 3 + 100 = 103
```

**注意**: 转换按定义顺序检查，A->B 虽然优先级高，但守卫不满足，所以检查下一个转换 A->C。

### 4.9 自转换测试

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        enter {
            counter = counter + 1;
        }
        during {
            counter = counter + 10;
        }
        exit {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> A :: Loop;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 11 | 进入 A，enter(+1)，during(+10) |
| `runtime.cycle(['Root.A.Loop'])` | A | 122 | A->A，exit(+100)，enter(+1)，during(+10) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.enter:                  0 + 1 = 1
  A.during:                 1 + 10 = 11

第2次 cycle (提供 Loop 事件):
  A.exit:                   11 + 100 = 111
  A->A (自转换)
  A.enter:                  111 + 1 = 112
  A.during:                 112 + 10 = 122
```

### 4.10 退出状态测试

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
        exit {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> [*] : if [counter >= 3];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle()` | A | 2 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 3 | 无转换，执行 A.during |
| `runtime.cycle()` | 已结束 | 103 | A->[*]，exit(+100) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle:
  检查转换 A->[*]: counter >= 3 不满足
  A.during:                 1 + 1 = 2

第3次 cycle:
  检查转换 A->[*]: counter >= 3 不满足
  A.during:                 2 + 1 = 3

第4次 cycle:
  检查转换 A->[*]: counter >= 3 满足
  A.exit:                   3 + 100 = 103
  A->[*] (状态机结束)
```

### 4.11 复杂场景：带守卫和效果的多级转换

```python
dsl_code = '''
def int counter = 0;
def int flag = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        enter {
            flag = 1;
        }
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        [*] -> B1 : if [flag == 1];
    }

    state C {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> B : if [counter >= 3] effect {
        flag = 1;
    };
    A -> C :: GoC;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | flag | 说明 |
|------|----------|---------|------|------|
| `runtime.cycle()` | A | 1 | 0 | 进入 A，执行 A.during |
| `runtime.cycle()` | A | 2 | 0 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 3 | 0 | 无转换，执行 A.during |
| `runtime.cycle()` | B1 | 13 | 1 | A->B（守卫满足，effect 设置 flag=1），B.enter（flag=1），B->[*]->B1（守卫满足），执行 B1.during |

**详细计算**:
```
初始: counter = 0, flag = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle:
  检查转换 A->B: counter >= 3 不满足
  A.during:                 1 + 1 = 2

第3次 cycle:
  检查转换 A->B: counter >= 3 不满足
  A.during:                 2 + 1 = 3

第4次 cycle:
  检查转换 A->B: counter >= 3 满足
  A.exit
  A->B effect: flag = 1
  B.enter: flag = 1
  B->[*]->B1: flag == 1 满足
  B1.enter
  B1.during:                3 + 10 = 13
```

### 4.12 复杂场景：验证失败的多级转换

```python
dsl_code = '''
def int counter = 0;
def int flag = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        enter {
            flag = 1;
        }
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        [*] -> B1 : if [flag == 2];  // 注意：flag 永远不会是 2
    }

    [*] -> A;
    A -> B : if [counter >= 3] effect {
        flag = 1;
    };
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | flag | 说明 |
|------|----------|---------|------|------|
| `runtime.cycle()` | A | 1 | 0 | 进入 A，执行 A.during |
| `runtime.cycle()` | A | 2 | 0 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 3 | 0 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 4 | 0 | A->B 验证失败（B.enter 设置 flag=1，但 B->[*]->B1 需要 flag==2，无法到达 stoppable），停在 A，执行 A.during |

**详细计算**:
```
初始: counter = 0, flag = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle:
  检查转换 A->B: counter >= 3 不满足
  A.during:                 1 + 1 = 2

第3次 cycle:
  检查转换 A->B: counter >= 3 不满足
  A.during:                 2 + 1 = 3

第4次 cycle:
  检查转换 A->B: counter >= 3 满足
  验证 A->B:
    模拟 A.exit
    模拟 A->B effect: flag = 1
    模拟 B.enter: flag = 1
    检查 B->[*]->B1: flag == 2 不满足
    无法到达 stoppable
  验证失败，停在 A
  A.during:                 3 + 1 = 4
```

**注意**: 验证过程中模拟执行 B.enter，发现 flag 会被设置为 1，但初始转换需要 flag==2，所以无法进入 B1。

### 4.13 伪状态链路测试：单个伪状态

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P {
        enter {
            counter = counter + 10;
        }
        during {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> A;
    A -> P :: GoP;
    P -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoP'])` | A | 2 | A->P 无效（P 是伪状态，不是 stoppable），停在 A，执行 A.during |
| `runtime.cycle(['Root.A.GoP', 'Root.P.GoB'])` | B | 1112 | A->P（enter +10, during +100），P->B，执行 B.during(+1000) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoP 事件):
  A->P 验证失败（P 是伪状态，non-stoppable）
  停在 A
  A.during:                 1 + 1 = 2

第3次 cycle (提供 GoP 和 GoB 事件):
  A.exit
  A->P
  P.enter:                  2 + 10 = 12
  P.during:                 12 + 100 = 112  (伪状态执行 during，但不执行 aspect actions)
  P.exit
  P->B
  B.enter
  B.during:                 112 + 1000 = 1112
```

**注意**:
- 第2次 cycle 时，虽然提供了 GoP 事件，但 P 是伪状态（non-stoppable），验证时发现无法停在 P，所以转换无效
- 第3次 cycle 时，同时提供 GoP 和 GoB 事件，验证时 DFS 搜索：A->P->B 到达 B（stoppable），转换有效
- **重要**: 伪状态虽然不是 stoppable，但仍然会执行 during 动作，只是：
  - 不会执行 aspect actions（>> during before/after）
  - 执行完 during 后立即继续转换，不会停留
  - 不能作为 cycle 的终点

### 4.14 伪状态链路测试：多个伪状态串联

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P1 {
        enter {
            counter = counter + 10;
        }
    }

    pseudo state P2 {
        enter {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> A;
    A -> P1 :: Go1;
    P1 -> P2 :: Go2;
    P2 -> B :: Go3;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.Go1'])` | A | 2 | A->P1 无效（P1 是伪状态），停在 A，执行 A.during |
| `runtime.cycle(['Root.A.Go1', 'Root.P1.Go2'])` | A | 3 | A->P1->P2 无效（P2 也是伪状态），停在 A，执行 A.during |
| `runtime.cycle(['Root.A.Go1', 'Root.P1.Go2', 'Root.P2.Go3'])` | B | 1113 | A->P1(+10)->P2(+100)->B，执行 B.during(+1000) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 Go1 事件):
  A->P1 验证：P1 是伪状态，non-stoppable
  验证失败，停在 A
  A.during:                 1 + 1 = 2

第3次 cycle (提供 Go1, Go2 事件):
  A->P1 验证：
    P1.enter: counter = 12
    P1->P2: P2 是伪状态，non-stoppable
  验证失败，停在 A
  A.during:                 2 + 1 = 3

第4次 cycle (提供 Go1, Go2, Go3 事件):
  A.exit
  A->P1
  P1.enter:                 3 + 10 = 13
  P1.exit
  P1->P2
  P2.enter:                 13 + 100 = 113
  P2.exit
  P2->B
  B.enter
  B.during:                 113 + 1000 = 1113
```

### 4.15 伪状态链路测试：带守卫条件

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P {
        enter {
            counter = counter + 10;
        }
    }

    state B {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> P : if [counter >= 3];
    P -> B : if [counter >= 15];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle()` | A | 2 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 3 | A->P 验证：counter=3，P.enter 后 counter=13，P->B 需要 counter>=15，不满足，转换无效，停在 A，执行 A.during |
| `runtime.cycle()` | A | 4 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 5 | 无转换，执行 A.during |
| `runtime.cycle()` | B | 115 | A->P 验证：counter=5，P.enter 后 counter=15，P->B 满足，转换有效，执行 B.during |

**详细计算**:
```
初始: counter = 0

第1-2次 cycle: A.during 累加，counter = 1, 2

第3次 cycle:
  检查转换 A->P: counter >= 3 满足
  验证 A->P:
    模拟 P.enter: counter = 3 + 10 = 13
    检查 P->B: counter >= 15 不满足
  验证失败，停在 A
  A.during:                 2 + 1 = 3

第4-5次 cycle: A.during 累加，counter = 4, 5

第6次 cycle:
  检查转换 A->P: counter >= 3 满足
  验证 A->P:
    模拟 P.enter: counter = 5 + 10 = 15
    检查 P->B: counter >= 15 满足
  验证成功
  A.exit
  A->P
  P.enter:                  5 + 10 = 15
  P.exit
  P->B
  B.enter
  B.during:                 15 + 100 = 115
```

### 4.16 伪状态链路测试：退出到状态机结束

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P {
        enter {
            counter = counter + 10;
        }
    }

    [*] -> A;
    A -> P :: GoP;
    P -> [*];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoP'])` | 已结束 | 11 | A->P(+10)->[\*]（状态机结束），转换有效 |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoP 事件):
  检查转换 A->P:
    验证 A->P:
      模拟 P.enter: counter = 1 + 10 = 11
      检查 P->[*]: 退出到状态机结束（栈为空）
    验证成功
  A.exit
  A->P
  P.enter:                  1 + 10 = 11
  P.exit
  P->[*] (状态机结束)
```

**注意**: P->[*] 导致状态机结束（栈为空），所以 A->P 转换有效。

### 4.17 伪状态链路测试：退出到父状态（无效）

```python
dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state A {
            during {
                counter = counter + 1;
            }
        }

        pseudo state P {
            enter {
                counter = counter + 10;
            }
        }

        [*] -> A;
        A -> P :: GoP;
        P -> [*];
    }

    [*] -> System;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 System->A，执行 A.during |
| `runtime.cycle(['Root.System.A.GoP'])` | A | 2 | A->P->[\*] 验证：P->[\*] 退到 System（复合状态，non-stoppable），转换无效，停在 A，执行 A.during |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 System
  System.enter
  System->[*]->A
  A.enter
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoP 事件):
  检查转换 A->P:
    验证 A->P:
      模拟 P.enter: counter = 1 + 10 = 11
      检查 P->[*]: 退出到 System（复合状态，non-stoppable）
    验证失败
  停在 A
  A.during:                 1 + 1 = 2
```

**注意**: P->[*] 只是退到父状态 System，而 System 是复合状态（non-stoppable），所以 A->P 转换无效。

### 4.18 伪状态链路测试：复合状态中的伪状态链

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        pseudo state P1 {
            enter {
                counter = counter + 10;
            }
        }

        pseudo state P2 {
            enter {
                counter = counter + 100;
            }
        }

        state B1 {
            during {
                counter = counter + 1000;
            }
        }

        [*] -> P1;
        P1 -> P2;
        P2 -> B1;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | B1 | 1111 | A->B，B->[\*]->P1(+10)->P2(+100)->B1，执行 B1.during(+1000) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  A.exit
  A->B
  B.enter
  B->[*]->P1 (初始转换)
  P1.enter:                 1 + 10 = 11
  P1->P2 (无条件转换)
  P2.enter:                 11 + 100 = 111
  P2->B1 (无条件转换)
  B1.enter
  B1.during:                111 + 1000 = 1111
```

**注意**:
- B 的初始转换链路：[*]->P1->P2->B1，全部是无条件转换
- 验证时会自动执行整个链路，最终到达 B1（stoppable）

### 4.19 伪状态链路测试：带事件的伪状态链（无效）

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        pseudo state P1 {
            enter {
                counter = counter + 10;
            }
        }

        state B1 {
            during {
                counter = counter + 100;
            }
        }

        [*] -> P1;
        P1 -> B1 :: Event;  // 需要事件
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | A | 2 | A->B 验证：B->[\*]->P1，但 P1->B1 需要 Event，无法到达 stoppable，转换无效，停在 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB', 'Root.B.P1.Event'])` | B1 | 112 | A->B，B->[\*]->P1(+10)->B1，执行 B1.during(+100) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  检查转换 A->B:
    验证 A->B:
      模拟 B.enter
      模拟 B->[*]->P1
      模拟 P1.enter: counter = 11
      检查 P1->B1: 需要 Event，但未提供
    验证失败
  停在 A
  A.during:                 1 + 1 = 2

第3次 cycle (提供 GoB 和 Event 事件):
  A.exit
  A->B
  B.enter
  B->[*]->P1
  P1.enter:                 2 + 10 = 12
  P1->B1 (Event 满足)
  B1.enter
  B1.during:                12 + 100 = 112
```

### 4.20 伪状态链路测试：混合复合状态和伪状态

```python
dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        pseudo state P {
            enter {
                counter = counter + 10;
            }
        }

        state C {
            state C1 {
                during {
                    counter = counter + 100;
                }
            }
            [*] -> C1;
        }

        [*] -> P;
        P -> C;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 A，执行 A.during |
| `runtime.cycle(['Root.A.GoB'])` | C1 | 111 | A->B，B->[\*]->P(+10)->C，C->[\*]->C1，执行 C1.during(+100) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoB 事件):
  A.exit
  A->B
  B.enter
  B->[*]->P (初始转换)
  P.enter:                  1 + 10 = 11
  P->C (无条件转换)
  C.enter
  C->[*]->C1 (初始转换)
  C1.enter
  C1.during:                11 + 100 = 111
```

**注意**: 验证链路：B（复合）->P（伪状态）->C（复合）->C1（stoppable）

### 4.21 Aspect Actions 测试：单层 aspect actions

```python
dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 10000;
    }

    state A {
        during {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> A;
    A -> B :: Go;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 10101 | 进入 A，执行 during：Root >> before (+1), A.during (+100), Root >> after (+10000) |
| `runtime.cycle(['Root.A.Go'])` | B | 21102 | A->B，执行 during：Root >> before (+1), B.during (+1000), Root >> after (+10000) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 A
  A.during:
    Root >> during before:  0 + 1 = 1
    A.during:               1 + 100 = 101
    Root >> during after:   101 + 10000 = 10101

第2次 cycle (提供 Go 事件):
  A.exit
  A->B
  B.enter
  B.during:
    Root >> during before:  10101 + 1 = 10102
    B.during:               10102 + 1000 = 11102
    Root >> during after:   11102 + 10000 = 21102
```

**注意**:
- Root 的 aspect actions 对所有叶子状态生效
- 执行顺序：>> before -> during -> >> after

### 4.22 Aspect Actions 测试：多层嵌套 aspect actions

```python
dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 100000;
    }

    state System {
        >> during before {
            counter = counter + 10;
        }

        >> during after {
            counter = counter + 10000;
        }

        state Module {
            >> during before {
                counter = counter + 100;
            }

            >> during after {
                counter = counter + 1000;
            }

            state Active {
                during {
                    counter = counter + 1;
                }
            }

            [*] -> Active;
        }

        [*] -> Module;
    }

    [*] -> System;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | Active | 111112 | 进入 System.Module.Active，执行 during：Root >> before (+1), System >> before (+10), Module >> before (+100), Active.during (+1), Module >> after (+1000), System >> after (+10000), Root >> after (+100000) |

**详细计算**:
```
初始: counter = 0
进入 Active 后执行 during:
  Root >> during before:    0 + 1 = 1
  System >> during before:  1 + 10 = 11
  Module >> during before:  11 + 100 = 111
  Active.during:            111 + 1 = 112
  Module >> during after:   112 + 1000 = 1112
  System >> during after:   1112 + 10000 = 11112
  Root >> during after:     11112 + 100000 = 111112
```

**注意**:
- Aspect actions 按层级从根到叶执行 before，从叶到根执行 after
- 每一层的 aspect actions 都会被执行

### 4.23 Aspect Actions 测试：伪状态跳过 aspect actions

```python
dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 10000;
    }

    state A {
        during {
            counter = counter + 100;
        }
    }

    pseudo state P {
        during {
            counter = counter + 1000;
        }
    }

    state B {
        during {
            counter = counter + 100000;
        }
    }

    [*] -> A;
    A -> P :: GoP;
    P -> B :: GoB;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 10101 | 进入 A，执行 during：Root >> before (+1), A.during (+100), Root >> after (+10000) |
| `runtime.cycle(['Root.A.GoP', 'Root.P.GoB'])` | B | 121102 | A->P（P.during +1000，**不执行 aspect actions**），P->B，执行 during：Root >> before (+1), B.during (+100000), Root >> after (+10000) |

**详细计算**:
```
第1次 cycle:
  Root >> during before:    0 + 1 = 1
  A.during:                 1 + 100 = 101
  Root >> during after:     101 + 10000 = 10101

第2次 cycle:
  A.exit
  A->P
  P.enter
  P.during:                 10101 + 1000 = 11101  (不执行 aspect actions)
  P.exit
  P->B
  B.enter
  B.during:
    Root >> during before:  11101 + 1 = 11102
    B.during:               11102 + 100000 = 111102
    Root >> during after:   111102 + 10000 = 121102
```

**注意**:
- 伪状态执行自己的 during，但跳过所有祖先的 aspect actions
- 普通状态会执行完整的 aspect actions

### 4.24 Aspect Actions 测试：多个叶子状态共享 aspect actions

```python
dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 1000;
    }

    state System {
        >> during before {
            counter = counter + 10;
        }

        >> during after {
            counter = counter + 100;
        }

        state A {
            during {
                counter = counter + 1;
            }
        }

        state B {
            during {
                counter = counter + 10;
            }
        }

        state C {
            during {
                counter = counter + 100;
            }
        }

        [*] -> A;
        A -> B :: GoB;
        B -> C :: GoC;
    }

    [*] -> System;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1112 | 进入 A，执行 during：Root >> before (+1), System >> before (+10), A.during (+1), System >> after (+100), Root >> after (+1000) |
| `runtime.cycle(['Root.System.A.GoB'])` | B | 2233 | A->B，执行 during：Root >> before (+1), System >> before (+10), B.during (+10), System >> after (+100), Root >> after (+1000) |
| `runtime.cycle(['Root.System.B.GoC'])` | C | 3444 | B->C，执行 during：Root >> before (+1), System >> before (+10), C.during (+100), System >> after (+100), Root >> after (+1000) |

**详细计算**:
```
第1次 cycle (进入 A):
  Root >> during before:    0 + 1 = 1
  System >> during before:  1 + 10 = 11
  A.during:                 11 + 1 = 12
  System >> during after:   12 + 100 = 112
  Root >> during after:     112 + 1000 = 1112

第2次 cycle (A->B):
  A.exit
  A->B
  B.enter
  B.during:
    Root >> during before:  1112 + 1 = 1113
    System >> during before: 1113 + 10 = 1123
    B.during:               1123 + 10 = 1133
    System >> during after: 1133 + 100 = 1233
    Root >> during after:   1233 + 1000 = 2233

第3次 cycle (B->C):
  B.exit
  B->C
  C.enter
  C.during:
    Root >> during before:  2233 + 1 = 2234
    System >> during before: 2234 + 10 = 2244
    C.during:               2244 + 100 = 2344
    System >> during after: 2344 + 100 = 2444
    Root >> during after:   2444 + 1000 = 3444
```

**注意**:
- 同一复合状态下的所有叶子状态共享父状态的 aspect actions
- 每次转换到新的叶子状态，都会重新执行完整的 aspect actions

### 4.25 Aspect Actions 测试：跨层级转换

```python
dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 100000;
    }

    state System1 {
        >> during before {
            counter = counter + 10;
        }

        >> during after {
            counter = counter + 10000;
        }

        state A {
            during {
                counter = counter + 100;
            }
        }

        [*] -> A;
    }

    state System2 {
        >> during before {
            counter = counter + 1000;
        }

        >> during after {
            counter = counter + 1000000;
        }

        state B {
            during {
                counter = counter + 10000;
            }
        }

        [*] -> B;
    }

    [*] -> System1;
    System1 -> System2 :: Go;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 110111 | 进入 System1.A，执行 during：Root >> before (+1), System1 >> before (+10), A.during (+100), System1 >> after (+10000), Root >> after (+100000) |
| `runtime.cycle(['Root.System1.Go'])` | B | 1221112 | System1->System2，进入 System2.B，执行 during：Root >> before (+1), System2 >> before (+1000), B.during (+10000), System2 >> after (+1000000), Root >> after (+100000) |

**详细计算**:
```
第1次 cycle (进入 System1.A):
  Root >> during before:     0 + 1 = 1
  System1 >> during before:  1 + 10 = 11
  A.during:                  11 + 100 = 111
  System1 >> during after:   111 + 10000 = 10111
  Root >> during after:      10111 + 100000 = 110111

第2次 cycle (System1->System2):
  A.exit
  System1.exit
  System1->System2
  System2.enter
  System2->[*]->B
  B.enter
  B.during:
    Root >> during before:   110111 + 1 = 110112
    System2 >> during before: 110112 + 1000 = 111112
    B.during:                111112 + 10000 = 121112
    System2 >> during after: 121112 + 1000000 = 1121112
    Root >> during after:    1121112 + 100000 = 1221112
```

**注意**:
- 跨层级转换时，aspect actions 会根据新的状态层级重新执行
- System1 的 aspect actions 不再执行，System2 的 aspect actions 开始执行
- Root 的 aspect actions 始终执行（因为所有状态都是 Root 的后代）

---

## 5. 实现要点

### 5.1 转换验证的实现

验证从 stoppable 转换到 non-stoppable 是否有效：

```python
def validate_transition(from_state, to_state, events, vars_snapshot):
    """
    验证转换是否能最终到达 stoppable 状态

    参数:
        from_state: 源状态（必须是 stoppable）
        to_state: 目标状态（可能是 non-stoppable）
        events: 当前可用的事件列表
        vars_snapshot: 变量的快照（用于模拟）

    返回:
        True 如果能到达 stoppable，False 否则
    """
    if to_state.is_stoppable:
        return True

    # 创建模拟环境
    sim_vars = vars_snapshot.copy()
    sim_state = to_state

    # 模拟执行
    while not sim_state.is_stoppable:
        # 执行 enter 动作
        execute_enter(sim_state, sim_vars)

        # 如果是复合状态，尝试初始转换
        if not sim_state.is_leaf_state:
            transition = find_triggered_transition(
                sim_state.init_transitions,
                events,
                sim_vars
            )
            if transition is None:
                return False  # 无法进入子状态

            # 执行转换
            execute_effect(transition, sim_vars)
            sim_state = get_target_state(transition)
        else:
            return False  # 叶子状态但不是 stoppable（伪状态）

    return True
```

### 5.2 During 动作的执行

```python
def execute_during(state, vars):
    """
    执行状态的 during 动作（包含 aspect actions）

    参数:
        state: 当前状态（必须是叶子状态）
        vars: 变量字典
    """
    # 使用 state 对象提供的方法获取完整的 during 动作列表
    for action_state, action in state.iter_on_during_aspect_recursively():
        execute_action(action, vars)
```

### 5.3 Step 的实现框架

```python
def step(events):
    """
    执行一次 step

    参数:
        events: 事件列表
    """
    current_state = get_current_state()

    if current_state.is_leaf_state:
        # 尝试触发转换
        for transition in current_state.transitions_from:
            if is_triggered(transition, events, vars):
                # 如果源状态是 stoppable 且目标是 non-stoppable，需要验证
                if current_state.is_stoppable and not get_target_state(transition).is_stoppable:
                    if not validate_transition(current_state, get_target_state(transition), events, vars):
                        continue  # 验证失败，尝试下一个转换

                # 执行转换
                execute_transition(transition)
                return

        # 没有转换可触发，执行 during
        execute_during(current_state, vars)
    else:
        # 复合状态，处理初始转换
        for transition in current_state.init_transitions:
            if is_triggered(transition, events, vars):
                execute_transition(transition)
                return
```

### 5.4 Cycle 的实现框架

```python
def cycle(events):
    """
    执行一个完整的 cycle

    参数:
        events: 事件列表
    """
    while True:
        current_state = get_current_state()

        # 如果到达 stoppable 状态，执行 during 并停止
        if current_state.is_stoppable:
            execute_during(current_state, vars)
            break

        # 执行 step
        prev_state = current_state
        step(events)

        # 如果状态没有变化且是叶子状态，说明没有转换可触发
        if get_current_state() == prev_state and prev_state.is_leaf_state:
            break
```

---

## 6. 待确认问题

### 6.1 伪状态的 stoppable 属性

**问题**: 伪状态是否是 stoppable？

**当前理解**:
- 伪状态是叶子状态
- 伪状态跳过祖先的 aspect actions
- `state.is_stoppable` 返回 `is_leaf_state and not is_pseudo`

**结论**: 伪状态不是 stoppable，不能作为 cycle 的终点

### 6.2 验证过程中的副作用

**问题**: 验证转换时模拟执行的 enter/effect 等动作，是否会产生副作用？

**答案**: 在 cycle 的时候进行一轮类似 DFS 的操作（已确认）
- 验证时使用变量的快照进行模拟
- 验证失败后，变量恢复到验证前的状态
- 验证成功后，需要重新执行一遍（因为验证时只是模拟）
- **重要**: 使用 DFS 而非 BFS，因为转换有顺序，需要按照定义顺序尝试

### 6.3 事件的作用域

**问题**: 在验证多级转换时，事件是否在整个验证过程中都有效？

**答案**: 事件在整个 cycle 内都有效（已确认）
- 事件在一个 cycle 内都有效
- 验证过程中的所有转换都可以使用这些事件
- 所有 step 和转换都可以使用 cycle 提供的事件

### 6.4 During 的执行时机

**问题**: 进入 stoppable 状态后，是立即执行 during 还是等下一次 cycle？

**答案**: 立即执行 during（已确认）

### 6.5 转换后的 during

**问题**: 从 A 转换到 B 后，是否立即执行 B 的 during？

**答案**: 如果 B 是 stoppable，则立即执行 during（已确认）

---

## 7. 更新日志

### v0.3.0 (2026-03-06)
- 新增 5 个 Aspect Actions 复杂测试用例（4.21-4.25）：
  - 4.21: 单层 aspect actions 基础测试
  - 4.22: 多层嵌套 aspect actions（3层嵌套）
  - 4.23: 伪状态跳过 aspect actions 的验证
  - 4.24: 多个叶子状态共享 aspect actions
  - 4.25: 跨层级转换时 aspect actions 的变化
- 详细展示了 aspect actions 的执行顺序和层级关系
- 提供了完整的计算过程和说明

### v0.2.2 (2026-03-06)
- **重要修正**: 明确伪状态会执行 during 动作
  - 伪状态跳过 aspect actions（>> during before/after）
  - 伪状态仍然执行自己的 during 动作
  - 伪状态执行完 during 后立即继续转换
- 修正测试用例 4.13 的计算（1012 -> 1112）
- 更新核心概念和执行顺序说明

### v0.2.1 (2026-03-06)
- 修正测试用例 4.13 的计算错误（1111 -> 1012）
- 确认所有测试用例（4.13-4.20）的计算正确性
- 更新验证方法说明：明确使用 DFS 而非 BFS
- 确认事件作用域：事件在整个 cycle 内有效

### v0.2.0 (2026-03-06)
- 补充转换验证规则：
  - 明确 non-stoppable 到 non-stoppable 的转换无效
  - 明确伪状态链路的验证规则
  - 明确退出转换的特殊规则（状态机结束 vs 退到父状态）
- 新增 9 个复杂测试用例（4.13-4.20）：
  - 单个伪状态测试
  - 多个伪状态串联测试
  - 带守卫条件的伪状态链路
  - 退出到状态机结束 vs 退到父状态
  - 复合状态中的伪状态链
  - 带事件的伪状态链
  - 混合复合状态和伪状态
- 完善转换验证示例

### v0.1.0 (2026-03-06)
- 初始版本
- 定义了 step 和 cycle 的语义
- 定义了转换验证规则
- 添加了 12 个测试用例
- 明确了执行顺序和优先级规则
