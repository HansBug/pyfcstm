# FSM 模拟运行器设计文档

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.4.0 | 2026-03-06 | 完善 simulate 设计文档，补充执行语义细节、aspect actions 说明与完整测试用例推导 | Claude |
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

**定义**: 执行一个完整的 cycle，直到到达可稳定驻停的边界

**执行流程**:
1. 在当前 cycle 内，按定义顺序尝试转换与必要的后续链路，直到满足以下任一条件：
   - 到达一个 stoppable 状态（叶子状态且非伪状态）
   - 确认无法继续到达任何 stoppable 状态
   - 状态机结束

2. 若到达 stoppable 状态，则执行该状态的 during 动作

**关键约束**:
- Cycle 的终点必须是 stoppable 状态，或者状态机已结束
- 复合状态、伪状态不能作为 cycle 的稳定终点
- 若整轮搜索无法到达任何 stoppable，则不应提交模拟阶段的副作用

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
| `runtime.cycle(['Root.System.A.GoP'])` | A | 2 | A->P->[\*] 验证：P->[\*] 退到 System，但 System 没有后续转换可以到达 stoppable，转换无效，停在 A，执行 A.during |

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
      检查 P->[*]: 退出到 System（复合状态）
      检查 System 是否有后续转换可以到达 stoppable: 无
    验证失败
  停在 A
  A.during:                 1 + 1 = 2
```

**注意**: P->[*] 退到父状态 System 后，System 没有后续转换可以到达 stoppable 状态，所以 A->P 转换无效。关键不是 System 是复合状态，而是 System 无法继续到达 stoppable。

**关键概念：退出到父状态后的执行逻辑**

当从子状态执行 `P -> [*]` 退出到父状态（比如 System）后：

1. **不能执行父状态内部的初始转换** `[*] -> XXX`
   - 父状态的初始转换只在**从外部进入父状态时**才执行
   - 包括：`??? -> System`（从其他状态进入）或 `System -> System`（自跳转）

2. **只能检查父状态这一层的转换**
   - 退出到 System 后，处于 System 这一层
   - 只能检查 System 是否有可跳转的 transition（如 `System -> OtherState`）
   - 这些转换可以有事件要求或守卫条件

3. **验证逻辑**
   - 验证 `P -> [*]` 时，需要检查退出到 System 后，System 是否有后续转换能到达 stoppable
   - 如果 System 有 `System -> B :: Event` 或 `System -> B : if [guard]`，且条件满足，则验证成功
   - 如果 System 只有 `[*] -> B`（初始转换），这**不算**后续转换，验证失败

### 4.17.1 伪状态链路测试：退出到父状态后可达 stoppable（带事件）

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

    state B {
        during {
            counter = counter + 100;
        }
    }

    [*] -> System;
    System -> B :: ToB;  // Root 这一层的转换，需要 ToB 事件
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 System->A，执行 A.during |
| `runtime.cycle(['Root.System.A.GoP'])` | A | 2 | A->P->[\*] 验证：P->[\*] 退到 System，检查 System->B 需要 ToB 事件但未提供，无法到达 stoppable，转换无效，停在 A，执行 A.during |
| `runtime.cycle(['Root.System.A.GoP', 'Root.System.ToB'])` | B | 112 | A->P(+10)->[\*]->System，System->B（ToB 事件满足），执行 B.during(+100) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 Root
  Root.enter
  Root->[*]->System
  System.enter
  System->[*]->A
  A.enter
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoP 事件):
  检查转换 A->P:
    验证 A->P (使用变量快照 counter=1):
      模拟 P.enter: counter = 1 + 10 = 11
      检查 P->[*]: 退出到 System
      检查 System 所在层（Root 层）的转换:
        System->B :: ToB: 需要 ToB 事件，但未提供
      无法到达 stoppable
    验证失败
  停在 A
  A.during:                 1 + 1 = 2

第3次 cycle (提供 GoP 和 ToB 事件):
  检查转换 A->P:
    验证 A->P (使用变量快照 counter=2):
      模拟 P.enter: counter = 2 + 10 = 12
      检查 P->[*]: 退出到 System
      检查 System 所在层（Root 层）的转换:
        System->B :: ToB: ToB 事件满足
      到达 B (stoppable)
    验证成功
  A.exit
  A->P
  P.enter:                  2 + 10 = 12
  P.exit
  P->[*] (退出到 System)
  检查 System 所在层（Root 层）的转换:
    System->B :: ToB 满足
  System.exit
  System->B
  B.enter
  B.during:                 12 + 100 = 112
```

**注意**: P->[*] 退到 System 后，不会执行 System 内部的初始转换 `[*] -> XXX`。只能检查 System 所在层（Root 层）的转换（如 `System -> B`）。当提供 ToB 事件时，System->B 转换满足，可以到达 stoppable 状态 B。

### 4.17.2 伪状态链路测试：退出到父状态后经伪状态可达 stoppable（带守卫）

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

        pseudo state P1 {
            enter {
                counter = counter + 10;
            }
        }

        [*] -> A;
        A -> P1 :: GoP;
        P1 -> [*];
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

    [*] -> System;
    System -> P2;  // Root 层的转换，无条件
    P2 -> B : if [counter >= 115];  // 需要守卫条件：P1.enter(+10) + P2.enter(+100) = 110，需要初始 counter >= 5
}
'''
```

**执行序列**:

| 操作 | 当前状态 | counter | 说明 |
|------|----------|---------|------|
| `runtime.cycle()` | A | 1 | 进入 System->A，执行 A.during |
| `runtime.cycle(['Root.System.A.GoP'])` | A | 2 | A->P1->[\*] 验证：counter=1，P1.enter(+10=11)，System->P2，P2.enter(+100=111)，P2->B 需要 counter>=115 不满足，转换无效，停在 A，执行 A.during |
| `runtime.cycle()` | A | 3 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 4 | 无转换，执行 A.during |
| `runtime.cycle()` | A | 5 | 无转换，执行 A.during |
| `runtime.cycle(['Root.System.A.GoP'])` | B | 1115 | A->P1(+10=15)->[\*]->System，System->P2(+100=115)，P2->B 守卫满足(115>=115)，执行 B.during(+1000) |

**详细计算**:
```
初始: counter = 0

第1次 cycle:
  进入 Root
  Root.enter
  Root->[*]->System
  System.enter
  System->[*]->A
  A.enter
  A.during:                 0 + 1 = 1

第2次 cycle (提供 GoP 事件):
  检查转换 A->P1:
    验证 A->P1 (使用变量快照 counter=1):
      模拟 P1.enter: counter = 1 + 10 = 11
      检查 P1->[*]: 退出到 System
      检查 System 所在层（Root 层）的转换:
        System->P2: 无条件，满足
      模拟 P2.enter: counter = 11 + 100 = 111
      检查 P2->B: counter >= 115，111 < 115 不满足
    验证失败
  停在 A
  A.during:                 1 + 1 = 2

第3-5次 cycle:
  无转换可触发
  A.during 累加: 2 -> 3 -> 4 -> 5

第6次 cycle (提供 GoP 事件):
  检查转换 A->P1:
    验证 A->P1 (使用变量快照 counter=5):
      模拟 P1.enter: counter = 5 + 10 = 15
      检查 P1->[*]: 退出到 System
      检查 System 所在层（Root 层）的转换:
        System->P2: 无条件，满足
      模拟 P2.enter: counter = 15 + 100 = 115
      检查 P2->B: counter >= 115，115 >= 115 满足
      到达 B (stoppable)
    验证成功
  A.exit
  A->P1
  P1.enter:                 5 + 10 = 15
  P1.exit
  P1->[*] (退出到 System)
  检查 System 所在层（Root 层）的转换:
    System->P2: 无条件，满足
  System.exit
  System->P2
  P2.enter:                 15 + 100 = 115
  检查 P2->B: counter >= 115，115 >= 115 满足
  P2.exit
  P2->B
  B.enter
  B.during:                 115 + 1000 = 1115
```

**注意**: P1->[*] 退到 System 后，不会执行 System 内部的初始转换。只能检查 System 所在层（Root 层）的转换。这里 System->P2 是无条件转换，然后 P2->B 需要守卫条件 counter>=115。只有当 A 的 counter 累加到 5 时，验证才能成功。关键是验证时需要模拟整个链路，包括所有 enter 动作和守卫条件，确保最终能到达 stoppable 状态。

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
| `runtime.cycle(['Root.System1.Go'])` | A | 220222 | 当前 runtime 实际不会触发 `System1 -> System2`，而是继续停留在 System1.A，并再次执行相同的 aspect/during 链路 |

**详细计算**:
```
第1次 cycle (进入 System1.A):
  Root >> during before:     0 + 1 = 1
  System1 >> during before:  1 + 10 = 11
  A.during:                  11 + 100 = 111
  System1 >> during after:   111 + 10000 = 10111
  Root >> during after:      10111 + 100000 = 110111

第2次 cycle (提供 Root.System1.Go 事件):
  当前 runtime 保持在 System1.A，不触发 System1->System2
  再次执行 System1.A 的 during 链路:
    Root >> during before:     110111 + 1 = 110112
    System1 >> during before:  110112 + 10 = 110122
    A.during:                  110122 + 100 = 110222
    System1 >> during after:   110222 + 10000 = 120222
    Root >> during after:      120222 + 100000 = 220222
```

**注意**:
- 按当前 [pyfcstm/simulate/runtime.py](pyfcstm/simulate/runtime.py) 的实际输出，`Root.System1.Go` 不会使状态从 `System1.A` 切换到 `System2.B`
- 因此此处文档已按实际 runtime 行为修正为“保持在 `System1.A` 并再次执行同一条 aspect/during 链路”
- 若后续需要支持这类跨层级转换，应以 runtime 语义修正为准，再同步更新本节示例

### 4.26 Aspect Actions 测试：带分阶段出口条件的跨层级转换

这个测试点以 **4.25** 为蓝本，但补上了从 `A` 退出 `System1` 所必需的出口 `A -> [*]`，并且把三段关键链路都分别加上守卫条件：

1. `A -> [*]`：控制**能否先离开叶子状态 A**
2. `System1 -> System2`：控制**能否从 System1 跨层级切换到 System2**
3. `System2` 内部的 `[*] -> B`：控制**进入 System2 后能否最终到达 stoppable 状态 B**

这样可以形成三个分阶段“卡住”的区间：

- 前几个 cycle：卡在 `A -> [*]` 不满足
- 中间几个 cycle：`A -> [*]` 已满足，但 `System1 -> System2` 不满足
- 后面几个 cycle：前两段都满足，但 `System2 -> B` 不满足
- 最后才整体链路打通，到达 `B`

```python
dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    >> during before {
        trace = trace + 1;
    }

    >> during after {
        trace = trace + 100000;
    }

    state System1 {
        >> during before {
            trace = trace + 10;
        }

        >> during after {
            trace = trace + 10000;
        }

        state A {
            during {
                phase = phase + 1;
                trace = trace + 100;
            }
        }

        [*] -> A;
        A -> [*] : if [phase >= 3];
    }

    state System2 {
        >> during before {
            trace = trace + 1000;
        }

        >> during after {
            trace = trace + 1000000;
        }

        state B {
            during {
                trace = trace + 10000;
            }
        }

        [*] -> B : if [phase >= 7];
    }

    [*] -> System1;
    System1 -> System2 : if [phase >= 5];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | phase | trace | 说明 |
|------|----------|-------|-------|------|
| `runtime.cycle()` | A | 1 | 110111 | 进入 `System1.A`，执行 `System1.A` 的 aspect/during 链路 |
| `runtime.cycle()` | A | 2 | 220222 | `A -> [*]` 尚不满足，继续停在 `A` |
| `runtime.cycle()` | A | 3 | 330333 | 本 cycle 检查时 `phase=2`，`A -> [*]` 仍不满足，执行 `A.during` 后变为 3 |
| `runtime.cycle()` | A | 4 | 440444 | `A -> [*]` 已满足，但 `System1 -> System2` 不满足，整条链路验证失败，停在 `A` |
| `runtime.cycle()` | A | 5 | 550555 | 同上；本 cycle 后 `phase` 增至 5 |
| `runtime.cycle()` | A | 6 | 660666 | `A -> [*]` 与 `System1 -> System2` 都满足，但 `System2 -> B` 不满足，整条链路仍失败 |
| `runtime.cycle()` | A | 7 | 770777 | 同上；本 cycle 后 `phase` 增至 7 |
| `runtime.cycle()` | B | 7 | 1881778 | 三段条件全部满足，完成 `A -> [*] -> System1 -> System2 -> B`，并执行 `B.during` |
| `runtime.cycle()` | B | 7 | 2992779 | 已稳定停在 `B`，继续执行 `System2.B` 的 aspect/during 链路 |

**详细计算**:
```
初始: phase = 0, trace = 0

第1次 cycle:
  Root >> during before:      0 + 1 = 1
  System1 >> during before:   1 + 10 = 11
  A.during:
    phase = 0 + 1 = 1
    trace = 11 + 100 = 111
  System1 >> during after:    111 + 10000 = 10111
  Root >> during after:       10111 + 100000 = 110111

第2次 cycle:
  检查 A->[*]: phase >= 3 不满足 (当前 phase = 1)
  继续执行 A.during 链路
  本次结束后: phase = 2, trace = 220222

第3次 cycle:
  检查 A->[*]: phase >= 3 不满足 (当前 phase = 2)
  继续执行 A.during 链路
  本次结束后: phase = 3, trace = 330333

第4次 cycle:
  检查 A->[*]: phase >= 3 满足
  退出到 System1 后继续检查 System1->System2: phase >= 5 不满足 (当前 phase = 3)
  整条链路验证失败，停在 A
  本次结束后: phase = 4, trace = 440444

第5次 cycle:
  检查 A->[*]: phase >= 3 满足
  检查 System1->System2: phase >= 5 不满足 (当前 phase = 4)
  整条链路验证失败，停在 A
  本次结束后: phase = 5, trace = 550555

第6次 cycle:
  检查 A->[*]: phase >= 3 满足
  检查 System1->System2: phase >= 5 满足
  进入 System2 后检查 [*]->B: phase >= 7 不满足 (当前 phase = 5)
  整条链路验证失败，停在 A
  本次结束后: phase = 6, trace = 660666

第7次 cycle:
  检查 A->[*]: phase >= 3 满足
  检查 System1->System2: phase >= 5 满足
  进入 System2 后检查 [*]->B: phase >= 7 不满足 (当前 phase = 6)
  整条链路验证失败，停在 A
  本次结束后: phase = 7, trace = 770777

第8次 cycle:
  检查 A->[*]: phase >= 3 满足
  检查 System1->System2: phase >= 5 满足
  检查 System2 内部 [*]->B: phase >= 7 满足
  链路验证成功
  A.exit
  A->[*] (退出到 System1)
  System1->System2
  System2.enter
  System2->[*]->B
  B.enter
  B.during:
    Root >> during before:      770777 + 1 = 770778
    System2 >> during before:   770778 + 1000 = 771778
    B.during:                   771778 + 10000 = 781778
    System2 >> during after:    781778 + 1000000 = 1781778
    Root >> during after:       1781778 + 100000 = 1881778

第9次 cycle:
  已稳定处于 B
  再次执行 System2.B 的 during 链路:
    Root >> during before:      1881778 + 1 = 1881779
    System2 >> during before:   1881779 + 1000 = 1882779
    B.during:                   1882779 + 10000 = 1892779
    System2 >> during after:    1892779 + 1000000 = 2892779
    Root >> during after:       2892779 + 100000 = 2992779
```

**注意**:
- 这个例子已经按当前 [pyfcstm/simulate/runtime.py](pyfcstm/simulate/runtime.py) 的实际输出校正
- `phase` 专门用于控制 guard 的阶段性满足；`trace` 专门用于观察 aspect actions 和 `during` 的累积效果
- 这个案例适合验证三类独立阻塞路径：
  - 叶子状态出口未满足
  - 父层跨层级转换未满足
  - 目标复合状态内部无法到达 stoppable

### 4.27 复合状态进入后没有可用的初始转换

这个测试点现在按本轮讨论后的设计语义理解：当一个 cycle 从初始状态开始执行时，应先以 **Root** 为起点做一轮 DFS 式可达性搜索，尝试找到一个可驻停的 stoppable state。若整条链路无法到达任何 stoppable，则本次 cycle 应整体失败，回退到最初状态，并且不保留任何模拟阶段的副作用。

因此，这个例子里虽然 `Root.[*] -> System` 可以进入复合状态 `System`，但因为 `System.[*] -> A` 永远不满足，所以整轮 cycle 最终找不到任何 stoppable。按照这里确认的设计语义，runtime 应保持在 `Root`，并且 `phase`、`trace` 都维持初始值 0。

```python
dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    state System {
        enter {
            trace = trace + 1;
        }
        during before {
            trace = trace + 10;
        }

        state A {
            during {
                phase = phase + 1;
                trace = trace + 100;
            }
        }

        [*] -> A : if [phase >= 3];
    }

    [*] -> System;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | phase | trace | 说明 |
|------|----------|-------|-------|------|
| `runtime.cycle()` | Root | 0 | 0 | 从 `Root` 开始做 DFS 式搜索，尝试 `Root -> System -> A`，但 `System.[*] -> A` 不满足，整轮找不到 stoppable，因此回退到 `Root`，不提交任何副作用，并给出 warning |
| `runtime.cycle()` | Root | 0 | 0 | 与上一次相同，仍无法找到 stoppable，状态继续卡在 `Root`，变量保持不变，并再次给出 warning |
| `runtime.cycle()` | Root | 0 | 0 | 同上，状态机持续卡死在初始状态 |

**详细计算**:
```
初始: 当前状态 = Root, phase = 0, trace = 0

第1次 cycle:
  从 Root 开始 DFS 式尝试：
    Root.[*] -> System
    System.enter / System.during before 在模拟过程中可被尝试
    继续检查 System.[*] -> A: phase >= 3 不满足
  因此整条链路无法到达任何 stoppable
  本次 cycle 判定失败
  回退到最初状态 Root
  丢弃所有模拟副作用
  本次结束后: 当前状态 = Root, phase = 0, trace = 0
  并给出 warning：无法正常转入 stoppable state

第2次 cycle:
  与第1次 cycle 相同
  本次结束后: 当前状态 = Root, phase = 0, trace = 0
  并再次给出 warning

第3次 cycle:
  与第2次 cycle 相同
  本次结束后: 当前状态 = Root, phase = 0, trace = 0
```

**注意**:
- 这里强调的是本轮讨论确认后的设计语义，而不是当前 `runtime.py` 的既有实现
- 关键点不是“停在 `System(init_wait)`”，而是“整轮 cycle 无法找到可驻停的 stoppable，因此回退到 `Root`”
- 所有模拟阶段的 enter / during before 等副作用都不应提交到真实 runtime 状态
- 这种情况应抛出 warning，提示用户当前状态机无法正常转入 stoppable state

### 4.28 子状态退出到父状态后没有后续 transition

这个测试点也按本轮讨论后的设计语义重新理解：cycle 不应只看局部是否能暂时前进，而应从起点整体判断是否最终可达某个 stoppable。若整条链路最终仍找不到可驻停状态，则所有模拟副作用都应回滚，runtime 保持在最初状态 `Root`。

在这个例子里，虽然 `Root.[*] -> System -> A` 可以成立，`A -> [*]` 也可以退出到父状态 `System`，但退出后 `System` 没有任何可继续推进到 stoppable 的后续 transition，因此整轮 cycle 仍然失败。结果应是回退到 `Root`，并保持 `phase=0`、`trace=0`。

```python
dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    state System {
        during after {
            trace = trace + 1000;
        }

        pseudo state A {
            during {
                phase = phase + 1;
                trace = trace + 10;
            }
        }

        [*] -> A;
        A -> [*] : if [phase >= 2];
    }

    [*] -> System;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | phase | trace | 说明 |
|------|----------|-------|-------|------|
| `runtime.cycle()` | Root | 0 | 0 | 虽然模拟上可走到 `System -> A -> [*] -> System`，但退出到父状态后仍无后续链路到达 stoppable，所以整轮 cycle 失败，回退到 `Root`，变量不变，并给出 warning |
| `runtime.cycle()` | Root | 0 | 0 | 再次尝试仍然无法形成可驻停链路，状态继续停在 `Root`，变量保持 0，并再次给出 warning |
| `runtime.cycle()` | Root | 0 | 0 | 同上，状态机持续卡死在初始状态 |

**详细计算**:
```
初始: 当前状态 = Root, phase = 0, trace = 0

第1次 cycle:
  从 Root 开始 DFS 式尝试：
    Root.[*] -> System
    System.[*] -> A
    在模拟过程中，A.during / A -> [*] / System.during after 都可能被尝试
    但退出回 System 后，System 没有任何后续 transition 可以继续到达 stoppable
  因此整轮 cycle 仍判定失败
  回退到最初状态 Root
  丢弃所有模拟副作用
  本次结束后: 当前状态 = Root, phase = 0, trace = 0
  并给出 warning：无法正常转入 stoppable state

第2次 cycle:
  与第1次 cycle 相同
  本次结束后: 当前状态 = Root, phase = 0, trace = 0
  并再次给出 warning

第3次 cycle:
  与第2次 cycle 相同
  本次结束后: 当前状态 = Root, phase = 0, trace = 0
```

**注意**:
- 这里也表达的是本轮讨论确认后的设计语义，而不是当前 `runtime.py` 的既有实现
- 关键点不是“停在 `System(post_child_exit)`”，而是“整轮 cycle 最终不能到达 stoppable，因此必须整体回滚到 `Root`”
- 所有模拟阶段里对 `phase`、`trace` 的修改都不应写回真实状态
- 这种情况同样应抛出 warning，提示用户当前状态机无法形成可驻停链路

### 4.30 显式退出到根并结束

这个测试点覆盖的是：叶子状态通过 `A -> [*]` 直接退出到 root，runtime 清空 stack，整个状态机结束；之后再次调用 `cycle()` 都是 no-op。

```python
dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    state A {
        during {
            phase = phase + 1;
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> [*] : if [phase >= 2];
}
'''
```

**执行序列**:

| 操作 | 当前状态 | phase | trace | 说明 |
|------|----------|-------|-------|------|
| `runtime.cycle()` | A | 1 | 10 | 首次进入 `A` 并执行 `A.during` |
| `runtime.cycle()` | A | 2 | 20 | `A -> [*]` 还不满足，再执行一次 `A.during` |
| `runtime.cycle()` | ended | 2 | 20 | `A -> [*]` 成功，直接退出到 root，runtime 结束并清空 stack |
| `runtime.cycle()` | ended | 2 | 20 | 在 cycle 开始前 runtime 已经结束，因此不再执行任何动作；按本轮讨论后的设计语义，这里应额外给出 warning 提示“runtime 已结束” |

**详细计算**:
```
初始: phase = 0, trace = 0

第1次 cycle:
  Root.[*] -> A
  A.during:
    phase = 0 + 1 = 1
    trace = 0 + 10 = 10

第2次 cycle:
  检查 A -> [*]: phase >= 2 不满足 (当前 phase = 1)
  再执行 A.during:
    phase = 1 + 1 = 2
    trace = 10 + 10 = 20

第3次 cycle:
  检查 A -> [*]: phase >= 2 满足
  A 直接退出到 root
  runtime 清空 stack，is_ended = True
  本次结束后: phase = 2, trace = 20

第4次 cycle:
  cycle 开始前 runtime 已结束
  不再执行任何动作
  phase = 2, trace = 20
  并给出 warning：runtime 已结束
```

**注意**:
- 这个例子保留“退出到 root 后整机结束”的主体语义
- 按本轮讨论后的设计语义，当 `cycle()` 开始前已经 `is_ended=True` 时，应显式给出 warning，而不仅仅是静默 no-op
- 与 4.28 的区别在于：4.28 是因为无法形成可驻停链路而整体回滚到 `Root`；4.30 则是已经成功结束整机

### 4.33 `ref` 复用 enter 动作

这个测试点覆盖的是：多个状态通过 `ref` 复用同一个具名 enter 动作。对 simulate 而言，`ref` 的本质仍然是执行目标 lifecycle action，因此进入不同状态时应产生一致的初始化副作用。

```python
dsl_code = '''
def int init_count = 0;
def int trace = 0;
state Root {
    enter CommonInit {
        init_count = init_count + 1;
        trace = trace + 100;
    }

    state A {
        enter ref /CommonInit;
        during {
            trace = trace + 1;
        }
    }

    state B {
        enter ref /CommonInit;
        during {
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> B :: Go;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | init_count | trace | 说明 |
|------|----------|------------|-------|------|
| `runtime.cycle()` | A | 2 | 201 | 首次 cycle 先进入 `Root` 并执行 `Root.enter CommonInit`，随后 `Root.[*] -> A`，`A.enter ref /CommonInit` 再次执行同一个具名 enter 动作，最后执行 `A.during` |
| `runtime.cycle(['Root.A.Go'])` | B | 3 | 311 | `A -> B`，`B.enter ref /CommonInit` 再次执行同一个具名 enter 动作，随后执行 `B.during` |
| `runtime.cycle()` | B | 3 | 321 | 无转换，继续执行 `B.during` |

**详细计算**:
```
初始: init_count = 0, trace = 0

第1次 cycle:
  进入 Root:
    Root.enter CommonInit:
      init_count = 0 + 1 = 1
      trace = 0 + 100 = 100
  Root.[*] -> A
  A.enter ref /CommonInit:
    init_count = 1 + 1 = 2
    trace = 100 + 100 = 200
  A.during:
    trace = 200 + 1 = 201

第2次 cycle (提供 Go 事件):
  A.exit
  A -> B
  B.enter ref /CommonInit:
    init_count = 2 + 1 = 3
    trace = 201 + 100 = 301
  B.during:
    trace = 301 + 10 = 311

第3次 cycle:
  无转换可触发
  B.during:
    trace = 311 + 10 = 321
```

**注意**:
- `ref` 引用的是已命名动作，不是状态或事件
- 在 simulate 中，`enter ref /CommonInit` 的执行效果应与把 `CommonInit` 的动作体直接写在目标状态中一致
- 这个例子适合验证 runtime 对具名 enter action 复用的处理是否一致

### 4.34 `ref` 复用抽象动作

这个测试点覆盖的是：`ref` 的目标不仅可以是具体动作，也可以是抽象动作。对 simulate 而言，抽象动作本身不包含变量赋值，因此被 `ref` 命中时不应产生额外数据副作用，但执行链路仍应保持合法。

```python
dsl_code = '''
def int trace = 0;
state Root {
    enter abstract PlatformInit;

    state A {
        enter ref /PlatformInit;
        during {
            trace = trace + 1;
        }
    }

    state B {
        enter ref /PlatformInit;
        during {
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> B :: Go;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | trace | 说明 |
|------|----------|-------|------|
| `runtime.cycle()` | A | 1 | 进入 `A` 时命中 `enter ref /PlatformInit`，但该目标是 abstract action，本身不修改变量；随后执行 `A.during` |
| `runtime.cycle(['Root.A.Go'])` | B | 11 | `A -> B` 后再次命中同一个 abstract action，仍无数据副作用；随后执行 `B.during` |
| `runtime.cycle()` | B | 21 | 无转换，继续执行 `B.during` |

**详细计算**:
```
初始: trace = 0

第1次 cycle:
  Root.[*] -> A
  A.enter ref /PlatformInit:
    目标为 abstract action
    不产生变量修改
  A.during:
    trace = 0 + 1 = 1

第2次 cycle (提供 Go 事件):
  A.exit
  A -> B
  B.enter ref /PlatformInit:
    仍命中同一个 abstract action
    不产生变量修改
  B.during:
    trace = 1 + 10 = 11

第3次 cycle:
  无转换可触发
  B.during:
    trace = 11 + 10 = 21
```

**注意**:
- 这里强调的是 `ref` 的解析目标可以是 abstract action
- simulate 不负责“实现”抽象动作；若目标 abstract action 本身无可执行副作用，则运行时变量不应变化
- 这个例子适合验证 runtime 不会把 `ref` 错误地当成普通状态跳转或事件触发

### 4.35 `ref` 复用 `>> during` aspect action

这个测试点覆盖的是：`ref` 可以指向具名 aspect action。对 simulate 而言，若叶子状态的 cycle 会执行祖先 aspect actions，则通过 `ref` 复用的 aspect action 也应按同样顺序参与执行。

```python
dsl_code = '''
def int trace = 0;
state Root {
    >> during before SharedBefore {
        trace = trace + 100;
    }

    state System {
        >> during before ref /SharedBefore;

        state A {
            during {
                trace = trace + 1;
            }
        }

        state B {
            during {
                trace = trace + 10;
            }
        }

        [*] -> A;
        A -> B :: Go;
    }

    [*] -> System;
}
'''
```

**执行序列**:

| 操作 | 当前状态 | trace | 说明 |
|------|----------|-------|------|
| `runtime.cycle()` | A | 201 | 进入 `System -> A` 后，执行 `Root >> during before SharedBefore` 与 `System >> during before ref /SharedBefore`，两者都指向同一套 before 逻辑，然后执行 `A.during` |
| `runtime.cycle(['Root.System.A.Go'])` | B | 411 | `A -> B` 后再次执行两层 before 逻辑，然后执行 `B.during` |
| `runtime.cycle()` | B | 621 | 无转换，继续执行相同的 aspect 链与 `B.during` |

**详细计算**:
```
初始: trace = 0

第1次 cycle:
  Root.[*] -> System -> A
  进入 stoppable 状态 A 后执行 during 链:
    Root >> during before SharedBefore:      trace = 0 + 100 = 100
    System >> during before ref /SharedBefore:
      复用 Root.SharedBefore                trace = 100 + 100 = 200
    A.during:                                trace = 200 + 1 = 201

第2次 cycle (提供 Go 事件):
  A.exit
  A -> B
  进入 B 后执行 during 链:
    Root >> during before SharedBefore:      trace = 201 + 100 = 301
    System >> during before ref /SharedBefore:
      复用 Root.SharedBefore                trace = 301 + 100 = 401
    B.during:                                trace = 401 + 10 = 411

第3次 cycle:
  无转换可触发
  再次执行相同的 before 链:
    Root.SharedBefore                        trace = 411 + 100 = 511
    System ref /SharedBefore                 trace = 511 + 100 = 611
    B.during                                 trace = 611 + 10 = 621
```

**注意**:
- 这里验证的是 `ref` 指向 aspect action 时，simulate 仍按正常 aspect 执行链处理
- `System >> during before ref /SharedBefore` 不是“跳过一层直接调用”，而是把该位置的动作解析为同一个具名 before action
- 这个例子适合验证 aspect 顺序与 `ref` 复用叠加后的执行一致性

### 4.100 真实系统用例：电梯轿门控制

这个例子模拟常见电梯的轿门控制逻辑：收到呼梯后开门，开到位后保持一段时间，再自动关门；如果关门过程中红外光幕检测到有人或物体遮挡，则立即重新开门并重新计时。

以下两条执行序列彼此独立，均从相同的初始状态开始。

```python
dsl_code = '''
def int door_pos = 0;
def int hold = 0;
def int reopen_count = 0;
state Root {
    state Closed {
        during {
            hold = 0;
        }
    }

    state Opening {
        during {
            door_pos = door_pos + 50;
        }
    }

    state Opened {
        during {
            hold = hold + 1;
        }
    }

    state Closing {
        during {
            door_pos = door_pos - 50;
        }
    }

    [*] -> Closed;
    Closed -> Opening :: HallCall effect {
        hold = 0;
    };
    Opening -> Opened : if [door_pos >= 100] effect {
        hold = 0;
    };
    Opened -> Closing : if [hold >= 2];
    Closing -> Opened :: BeamBlocked effect {
        reopen_count = reopen_count + 1;
        door_pos = 100;
        hold = 0;
    };
    Closing -> Closed : if [door_pos <= 0] effect {
        hold = 0;
    };
}
'''
```

**执行序列 A（正常开门、保持、自动关门）**:

| 操作 | 当前状态 | door_pos | hold | reopen_count | 说明 |
|------|----------|----------|------|--------------|------|
| `runtime.cycle()` | Closed | 0 | 0 | 0 | 初始进入 `Closed` |
| `runtime.cycle(['Root.Closed.HallCall'])` | Opening | 50 | 0 | 0 | 收到呼梯，开始开门 |
| `runtime.cycle()` | Opening | 100 | 0 | 0 | 开门继续，达到全开位 |
| `runtime.cycle()` | Opened | 100 | 1 | 0 | 进入 `Opened`，开始保持开门 |
| `runtime.cycle()` | Opened | 100 | 2 | 0 | 保持开门继续计时 |
| `runtime.cycle()` | Closing | 50 | 2 | 0 | 保持时间达到阈值，开始关门 |
| `runtime.cycle()` | Closing | 0 | 2 | 0 | 继续关门到闭合位 |
| `runtime.cycle()` | Closed | 0 | 0 | 0 | 门完全关闭，回到待命 |

**详细计算 A**:
```text
初始: door_pos = 0, hold = 0, reopen_count = 0

第1次 cycle:
  进入 Closed
  Closed.during:
    hold = 0

第2次 cycle (提供 HallCall 事件):
  Closed.exit
  Closed->Opening effect:
    hold = 0
  Opening.enter
  Opening.during:
    door_pos = 0 + 50 = 50

第3次 cycle:
  检查 Opening->Opened: door_pos >= 100 不满足 (当前 door_pos = 50)
  Opening.during:
    door_pos = 50 + 50 = 100

第4次 cycle:
  检查 Opening->Opened: door_pos >= 100 满足
  Opening.exit
  Opening->Opened effect:
    hold = 0
  Opened.enter
  Opened.during:
    hold = 0 + 1 = 1

第5次 cycle:
  检查 Opened->Closing: hold >= 2 不满足 (当前 hold = 1)
  Opened.during:
    hold = 1 + 1 = 2

第6次 cycle:
  检查 Opened->Closing: hold >= 2 满足
  Opened.exit
  Opened->Closing
  Closing.enter
  Closing.during:
    door_pos = 100 - 50 = 50

第7次 cycle:
  检查 Closing->Closed: door_pos <= 0 不满足 (当前 door_pos = 50)
  Closing.during:
    door_pos = 50 - 50 = 0

第8次 cycle:
  检查 Closing->Closed: door_pos <= 0 满足
  Closing.exit
  Closing->Closed effect:
    hold = 0
  Closed.enter
  Closed.during:
    hold = 0
```

**执行序列 B（关门时光幕遮挡，重新开门）**:

| 操作 | 当前状态 | door_pos | hold | reopen_count | 说明 |
|------|----------|----------|------|--------------|------|
| `runtime.cycle()` | Closed | 0 | 0 | 0 | 初始进入 `Closed` |
| `runtime.cycle(['Root.Closed.HallCall'])` | Opening | 50 | 0 | 0 | 收到呼梯，开始开门 |
| `runtime.cycle()` | Opening | 100 | 0 | 0 | 开门继续，达到全开位 |
| `runtime.cycle()` | Opened | 100 | 1 | 0 | 进入 `Opened`，开始保持开门 |
| `runtime.cycle()` | Opened | 100 | 2 | 0 | 保持开门继续计时 |
| `runtime.cycle()` | Closing | 50 | 2 | 0 | 开始自动关门 |
| `runtime.cycle(['Root.Closing.BeamBlocked'])` | Opened | 100 | 1 | 1 | 关门途中检测到遮挡，立即重开并记录一次重开 |

**详细计算 B**:
```text
初始: door_pos = 0, hold = 0, reopen_count = 0

第1~6次 cycle:
  与执行序列 A 的第1~6次 cycle 相同
  第6次结束后:
    当前状态 = Closing
    door_pos = 50, hold = 2, reopen_count = 0

第7次 cycle (提供 BeamBlocked 事件):
  检查 Closing->Opened: BeamBlocked 事件满足
  Closing.exit
  Closing->Opened effect:
    reopen_count = 0 + 1 = 1
    door_pos = 50 -> 100
    hold = 0
  Opened.enter
  Opened.during:
    hold = 0 + 1 = 1
```

**注意**:
- 这里把 `door_pos` 抽象成 0、50、100 三个位置，分别表示全关、半开/半关、全开
- `BeamBlocked` 只在 `Closing` 状态下有意义，符合光幕仅在关门阶段触发重开的真实逻辑
- 重新开门后会重新进入 `Opened` 的保持计时阶段，而不是直接回到 `Opening`

### 4.101 真实系统用例：储水式电热水器控温

这个例子模拟常见家用储水式电热水器：待机时水温缓慢下降，降到下限后自动加热；如果用户集中用水，则水温会在一个 cycle 内显著下降，从而更早触发加热。

以下两条执行序列彼此独立，均从相同的初始状态开始。

```python
dsl_code = '''
def int water_temp = 55;
def int draw_count = 0;
state Root {
    state Standby {
        during {
            water_temp = water_temp - 1;
        }
    }

    state Heating {
        during {
            water_temp = water_temp + 4;
        }
    }

    [*] -> Standby;
    Standby -> Heating : if [water_temp <= 50];
    Standby -> Standby :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
    Heating -> Standby : if [water_temp >= 60];
    Heating -> Heating :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
}
'''
```

**执行序列 A（无人集中用水，温度自然下降后再加热）**:

| 操作 | 当前状态 | water_temp | draw_count | 说明 |
|------|----------|------------|------------|------|
| `runtime.cycle()` | Standby | 54 | 0 | 初始进入待机，水温自然散热 |
| `runtime.cycle()` | Standby | 53 | 0 | 持续散热 |
| `runtime.cycle()` | Standby | 52 | 0 | 持续散热 |
| `runtime.cycle()` | Standby | 51 | 0 | 持续散热 |
| `runtime.cycle()` | Standby | 50 | 0 | 降到加热阈值 |
| `runtime.cycle()` | Heating | 54 | 0 | 触发加热，温度开始回升 |
| `runtime.cycle()` | Heating | 58 | 0 | 持续加热 |

**详细计算 A**:
```text
初始: water_temp = 55, draw_count = 0

第1次 cycle:
  进入 Standby
  Standby.during:
    water_temp = 55 - 1 = 54

第2次 cycle:
  检查 Standby->Heating: water_temp <= 50 不满足 (当前 water_temp = 54)
  Standby.during:
    water_temp = 54 - 1 = 53

第3次 cycle:
  检查 Standby->Heating: water_temp <= 50 不满足 (当前 water_temp = 53)
  Standby.during:
    water_temp = 53 - 1 = 52

第4次 cycle:
  检查 Standby->Heating: water_temp <= 50 不满足 (当前 water_temp = 52)
  Standby.during:
    water_temp = 52 - 1 = 51

第5次 cycle:
  检查 Standby->Heating: water_temp <= 50 不满足 (当前 water_temp = 51)
  Standby.during:
    water_temp = 51 - 1 = 50

第6次 cycle:
  检查 Standby->Heating: water_temp <= 50 满足
  Standby.exit
  Standby->Heating
  Heating.enter
  Heating.during:
    water_temp = 50 + 4 = 54

第7次 cycle:
  检查 Heating->Standby: water_temp >= 60 不满足 (当前 water_temp = 54)
  Heating.during:
    water_temp = 54 + 4 = 58
```

**执行序列 B（早晨连续用水，提前触发加热）**:

| 操作 | 当前状态 | water_temp | draw_count | 说明 |
|------|----------|------------|------------|------|
| `runtime.cycle()` | Standby | 54 | 0 | 初始进入待机，水温自然散热 |
| `runtime.cycle(['Root.Standby.HotWaterDraw'])` | Standby | 45 | 1 | 用户大量用水，温度在一个 cycle 内显著下降 |
| `runtime.cycle()` | Heating | 49 | 1 | 因温度已低于下限，立即进入加热 |
| `runtime.cycle()` | Heating | 53 | 1 | 持续加热 |
| `runtime.cycle()` | Heating | 57 | 1 | 持续加热 |
| `runtime.cycle()` | Heating | 61 | 1 | 加热达到停机阈值以上 |
| `runtime.cycle()` | Standby | 60 | 1 | 控制器停加热并回到待机 |

**详细计算 B**:
```text
初始: water_temp = 55, draw_count = 0

第1次 cycle:
  进入 Standby
  Standby.during:
    water_temp = 55 - 1 = 54

第2次 cycle (提供 HotWaterDraw 事件):
  检查 Standby->Standby: HotWaterDraw 事件满足
  Standby.exit
  Standby->Standby effect:
    water_temp = 54 - 8 = 46
    draw_count = 0 + 1 = 1
  Standby.enter
  Standby.during:
    water_temp = 46 - 1 = 45

第3次 cycle:
  检查 Standby->Heating: water_temp <= 50 满足
  Standby.exit
  Standby->Heating
  Heating.enter
  Heating.during:
    water_temp = 45 + 4 = 49

第4次 cycle:
  检查 Heating->Standby: water_temp >= 60 不满足 (当前 water_temp = 49)
  Heating.during:
    water_temp = 49 + 4 = 53

第5次 cycle:
  检查 Heating->Standby: water_temp >= 60 不满足 (当前 water_temp = 53)
  Heating.during:
    water_temp = 53 + 4 = 57

第6次 cycle:
  检查 Heating->Standby: water_temp >= 60 不满足 (当前 water_temp = 57)
  Heating.during:
    water_temp = 57 + 4 = 61

第7次 cycle:
  检查 Heating->Standby: water_temp >= 60 满足
  Heating.exit
  Heating->Standby
  Standby.enter
  Standby.during:
    water_temp = 61 - 1 = 60
```

**注意**:
- `HotWaterDraw` 被建模为一个显著降温事件，符合储水式热水器在短时间集中用水时的温降特征
- `Standby -> Heating` 与 `Heating -> Standby` 形成典型的上下限迟滞控制
- 在 `Heating` 状态下如果继续发生 `HotWaterDraw`，本模型也能表示“边补热边被抽冷水”的场景

### 4.102 真实系统用例：主干道信号灯带行人过街请求

这个例子模拟城市路口中常见的信号控制器：主干道默认保持绿灯；行人按钮被按下后，请求会先被锁存；只有主干道最小绿灯时间达到后，控制器才进入黄灯和行人放行阶段，结束后再回到主干道绿灯。

以下两条执行序列彼此独立，均从相同的初始状态开始。

```python
dsl_code = '''
def int green_ticks = 0;
def int request_latched = 0;
def int yellow_ticks = 0;
def int walk_ticks = 0;
state Root {
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

        state PedWalk {
            during {
                walk_ticks = walk_ticks + 1;
            }
        }

        [*] -> MainYellow;
        MainYellow -> PedWalk : if [yellow_ticks >= 1];
        PedWalk -> [*] : if [walk_ticks >= 2];
    }

    [*] -> MainGreen;
    MainGreen -> PedestrianPhase : if [request_latched == 1 && green_ticks >= 3] effect {
        request_latched = 0;
        yellow_ticks = 0;
        walk_ticks = 0;
    };
    MainGreen -> MainGreen :: PedRequest effect {
        request_latched = 1;
    };
    PedestrianPhase -> MainGreen effect {
        green_ticks = 0;
        yellow_ticks = 0;
        walk_ticks = 0;
    };
}
'''
```

**执行序列 A（没有行人请求，主干道持续放行）**:

| 操作 | 当前状态 | green_ticks | request_latched | yellow_ticks | walk_ticks | 说明 |
|------|----------|-------------|-----------------|--------------|------------|------|
| `runtime.cycle()` | MainGreen | 1 | 0 | 0 | 0 | 初始进入主干道绿灯 |
| `runtime.cycle()` | MainGreen | 2 | 0 | 0 | 0 | 无人请求，继续保持绿灯 |
| `runtime.cycle()` | MainGreen | 3 | 0 | 0 | 0 | 最小绿灯达到，但仍无行人请求 |
| `runtime.cycle()` | MainGreen | 4 | 0 | 0 | 0 | 继续保持主干道优先 |

**详细计算 A**:
```text
初始: green_ticks = 0, request_latched = 0, yellow_ticks = 0, walk_ticks = 0

第1次 cycle:
  进入 MainGreen
  MainGreen.during:
    green_ticks = 0 + 1 = 1

第2次 cycle:
  检查 MainGreen->PedestrianPhase: request_latched == 1 && green_ticks >= 3 不满足
  MainGreen.during:
    green_ticks = 1 + 1 = 2

第3次 cycle:
  检查 MainGreen->PedestrianPhase: request_latched == 1 && green_ticks >= 3 不满足
  MainGreen.during:
    green_ticks = 2 + 1 = 3

第4次 cycle:
  检查 MainGreen->PedestrianPhase: request_latched == 1 && green_ticks >= 3 不满足
  MainGreen.during:
    green_ticks = 3 + 1 = 4
```

**执行序列 B（行人提前按键，请求被锁存并在允许时放行）**:

| 操作 | 当前状态 | green_ticks | request_latched | yellow_ticks | walk_ticks | 说明 |
|------|----------|-------------|-----------------|--------------|------------|------|
| `runtime.cycle()` | MainGreen | 1 | 0 | 0 | 0 | 初始进入主干道绿灯 |
| `runtime.cycle(['Root.MainGreen.PedRequest'])` | MainGreen | 2 | 1 | 0 | 0 | 行人按钮按下，请求先被锁存 |
| `runtime.cycle()` | MainGreen | 3 | 1 | 0 | 0 | 最小绿灯尚未满足前，继续主干道放行 |
| `runtime.cycle()` | MainYellow | 3 | 0 | 1 | 0 | 进入行人阶段，先执行车辆黄灯 |
| `runtime.cycle()` | PedWalk | 3 | 0 | 1 | 1 | 黄灯结束，开始行人放行 |
| `runtime.cycle()` | PedWalk | 3 | 0 | 1 | 2 | 行人继续通行 |
| `runtime.cycle()` | MainGreen | 1 | 0 | 0 | 0 | 行人阶段结束，恢复主干道绿灯 |

**详细计算 B**:
```text
初始: green_ticks = 0, request_latched = 0, yellow_ticks = 0, walk_ticks = 0

第1次 cycle:
  进入 MainGreen
  MainGreen.during:
    green_ticks = 0 + 1 = 1

第2次 cycle (提供 PedRequest 事件):
  检查 MainGreen->PedestrianPhase: request_latched == 1 && green_ticks >= 3 不满足
  MainGreen->MainGreen effect:
    request_latched = 1
  MainGreen.during:
    green_ticks = 1 + 1 = 2

第3次 cycle:
  检查 MainGreen->PedestrianPhase: request_latched == 1 && green_ticks >= 3 不满足 (当前 green_ticks = 2)
  MainGreen.during:
    green_ticks = 2 + 1 = 3

第4次 cycle:
  检查 MainGreen->PedestrianPhase: request_latched == 1 && green_ticks >= 3 满足
  MainGreen.exit
  MainGreen->PedestrianPhase effect:
    request_latched = 1 -> 0
    yellow_ticks = 0
    walk_ticks = 0
  PedestrianPhase.enter
  PedestrianPhase.[*] -> MainYellow
  MainYellow.enter
  MainYellow.during:
    yellow_ticks = 0 + 1 = 1

第5次 cycle:
  检查 MainYellow->PedWalk: yellow_ticks >= 1 满足
  MainYellow.exit
  MainYellow->PedWalk
  PedWalk.enter
  PedWalk.during:
    walk_ticks = 0 + 1 = 1

第6次 cycle:
  检查 PedWalk->[*]: walk_ticks >= 2 不满足 (当前 walk_ticks = 1)
  PedWalk.during:
    walk_ticks = 1 + 1 = 2

第7次 cycle:
  检查 PedWalk->[*]: walk_ticks >= 2 满足
  PedWalk.exit
  PedWalk->[*]
  回到 PedestrianPhase
  检查 PedestrianPhase->MainGreen: 无条件满足
  PedestrianPhase.exit
  PedestrianPhase->MainGreen effect:
    green_ticks = 0
    yellow_ticks = 0
    walk_ticks = 0
  MainGreen.enter
  MainGreen.during:
    green_ticks = 0 + 1 = 1
```

**注意**:
- `request_latched` 表示按钮请求被控制器锁存，而不是要求按钮持续按住
- `PedestrianPhase` 被建模为复合状态，反映“黄灯清空车辆流 -> 行人放行 -> 返回主干道”的真实阶段划分
- `PedWalk -> [*]` 后再由 `PedestrianPhase -> MainGreen` 回到父层级，符合 runtime 的复合状态退出语义

### 4.103 真实系统用例：交流充电桩会话控制

这个例子模拟常见交流充电桩的简化会话逻辑：车辆插枪后开始充电，电量达到满电后转入完成态；用户也可能因为临时出发而提前拔枪结束会话。

以下两条执行序列彼此独立，均从相同的初始状态开始。

```python
dsl_code = '''
def int soc = 70;
def int sessions = 0;
state Root {
    state Idle;

    state Charging {
        during {
            soc = soc + 10;
        }
    }

    state Complete;

    [*] -> Idle;
    Idle -> Charging :: PlugIn;
    Charging -> Complete : if [soc >= 100];
    Charging -> Idle :: Unplug effect {
        sessions = sessions + 1;
    };
    Complete -> Idle :: Unplug effect {
        sessions = sessions + 1;
    };
}
'''
```

**执行序列 A（正常充满后拔枪）**:

| 操作 | 当前状态 | soc | sessions | 说明 |
|------|----------|-----|----------|------|
| `runtime.cycle()` | Idle | 70 | 0 | 初始进入空闲态 |
| `runtime.cycle(['Root.Idle.PlugIn'])` | Charging | 80 | 0 | 插枪后开始充电 |
| `runtime.cycle()` | Charging | 90 | 0 | 持续充电 |
| `runtime.cycle()` | Charging | 100 | 0 | 电量达到满电阈值 |
| `runtime.cycle()` | Complete | 100 | 0 | 进入充电完成态 |
| `runtime.cycle(['Root.Complete.Unplug'])` | Idle | 100 | 1 | 用户拔枪，完成一次会话 |

**详细计算 A**:
```text
初始: soc = 70, sessions = 0

第1次 cycle:
  进入 Idle
  Idle 无 during 动作

第2次 cycle (提供 PlugIn 事件):
  Idle.exit
  Idle->Charging
  Charging.enter
  Charging.during:
    soc = 70 + 10 = 80

第3次 cycle:
  检查 Charging->Complete: soc >= 100 不满足 (当前 soc = 80)
  Charging.during:
    soc = 80 + 10 = 90

第4次 cycle:
  检查 Charging->Complete: soc >= 100 不满足 (当前 soc = 90)
  Charging.during:
    soc = 90 + 10 = 100

第5次 cycle:
  检查 Charging->Complete: soc >= 100 满足
  Charging.exit
  Charging->Complete
  Complete.enter
  Complete 无 during 动作

第6次 cycle (提供 Unplug 事件):
  Complete.exit
  Complete->Idle effect:
    sessions = 0 + 1 = 1
  Idle.enter
  Idle 无 during 动作
```

**执行序列 B（用户提前拔枪离开）**:

| 操作 | 当前状态 | soc | sessions | 说明 |
|------|----------|-----|----------|------|
| `runtime.cycle()` | Idle | 70 | 0 | 初始进入空闲态 |
| `runtime.cycle(['Root.Idle.PlugIn'])` | Charging | 80 | 0 | 插枪后开始充电 |
| `runtime.cycle(['Root.Charging.Unplug'])` | Idle | 80 | 1 | 用户临时离开，提前结束充电会话 |
| `runtime.cycle(['Root.Idle.PlugIn'])` | Charging | 90 | 1 | 车辆重新插枪，继续补电 |
| `runtime.cycle()` | Charging | 100 | 1 | 继续充电到满电阈值 |

**详细计算 B**:
```text
初始: soc = 70, sessions = 0

第1次 cycle:
  进入 Idle
  Idle 无 during 动作

第2次 cycle (提供 PlugIn 事件):
  Idle.exit
  Idle->Charging
  Charging.enter
  Charging.during:
    soc = 70 + 10 = 80

第3次 cycle (提供 Unplug 事件):
  检查 Charging->Complete: soc >= 100 不满足 (当前 soc = 80)
  Charging.exit
  Charging->Idle effect:
    sessions = 0 + 1 = 1
  Idle.enter
  Idle 无 during 动作

第4次 cycle (再次提供 PlugIn 事件):
  Idle.exit
  Idle->Charging
  Charging.enter
  Charging.during:
    soc = 80 + 10 = 90

第5次 cycle:
  检查 Charging->Complete: soc >= 100 不满足 (当前 soc = 90)
  Charging.during:
    soc = 90 + 10 = 100
```

**注意**:
- 这里把 `soc` 简化为每个 cycle 增加固定 10%，用于表达会话级状态转换而不是精确电池模型
- `Complete` 没有 `during` 动作，表示车辆已满电但枪仍插着，桩端处于等待拔枪的完成态
- “提前拔枪”和“充满后拔枪”都记为一次完成的插枪会话，因此都会增加 `sessions`

### 4.104 真实系统用例：机房 ATS 市电/发电机切换

这个例子模拟机房或小型数据中心常见的自动切换开关（ATS）场景：默认由市电供电；市电故障后启动发电机并预热，预热完成后切到发电机；市电恢复后再切回市电。

以下两条执行序列彼此独立，均从相同的初始状态开始。

```python
dsl_code = '''
def int warmup = 0;
def int transfer_count = 0;
state Root {
    state OnMains {
        during {
            warmup = 0;
        }
    }

    state StartingGen {
        during {
            warmup = warmup + 1;
        }
    }

    state OnGenerator;

    [*] -> OnMains;
    OnMains -> StartingGen :: GridFail effect {
        warmup = 0;
    };
    StartingGen -> OnGenerator : if [warmup >= 2] effect {
        transfer_count = transfer_count + 1;
    };
    OnGenerator -> OnMains :: GridRestore effect {
        transfer_count = transfer_count + 1;
        warmup = 0;
    };
}
'''
```

**执行序列 A（市电稳定，始终不切换）**:

| 操作 | 当前状态 | warmup | transfer_count | 说明 |
|------|----------|--------|----------------|------|
| `runtime.cycle()` | OnMains | 0 | 0 | 初始由市电供电 |
| `runtime.cycle()` | OnMains | 0 | 0 | 市电稳定，继续保持 |
| `runtime.cycle()` | OnMains | 0 | 0 | 市电稳定，继续保持 |

**详细计算 A**:
```text
初始: warmup = 0, transfer_count = 0

第1次 cycle:
  进入 OnMains
  OnMains.during:
    warmup = 0

第2次 cycle:
  无 GridFail 事件
  OnMains.during:
    warmup = 0

第3次 cycle:
  无 GridFail 事件
  OnMains.during:
    warmup = 0
```

**执行序列 B（市电故障后切到发电机，再切回市电）**:

| 操作 | 当前状态 | warmup | transfer_count | 说明 |
|------|----------|--------|----------------|------|
| `runtime.cycle()` | OnMains | 0 | 0 | 初始由市电供电 |
| `runtime.cycle(['Root.OnMains.GridFail'])` | StartingGen | 1 | 0 | 市电中断，发电机启动并开始预热 |
| `runtime.cycle()` | StartingGen | 2 | 0 | 发电机继续预热 |
| `runtime.cycle()` | OnGenerator | 2 | 1 | 预热完成，ATS 将负载切到发电机 |
| `runtime.cycle(['Root.OnGenerator.GridRestore'])` | OnMains | 0 | 2 | 市电恢复，ATS 切回市电 |

**详细计算 B**:
```text
初始: warmup = 0, transfer_count = 0

第1次 cycle:
  进入 OnMains
  OnMains.during:
    warmup = 0

第2次 cycle (提供 GridFail 事件):
  OnMains.exit
  OnMains->StartingGen effect:
    warmup = 0
  StartingGen.enter
  StartingGen.during:
    warmup = 0 + 1 = 1

第3次 cycle:
  检查 StartingGen->OnGenerator: warmup >= 2 不满足 (当前 warmup = 1)
  StartingGen.during:
    warmup = 1 + 1 = 2

第4次 cycle:
  检查 StartingGen->OnGenerator: warmup >= 2 满足
  StartingGen.exit
  StartingGen->OnGenerator effect:
    transfer_count = 0 + 1 = 1
  OnGenerator.enter
  OnGenerator 无 during 动作

第5次 cycle (提供 GridRestore 事件):
  OnGenerator.exit
  OnGenerator->OnMains effect:
    transfer_count = 1 + 1 = 2
    warmup = 0
  OnMains.enter
  OnMains.during:
    warmup = 0
```

**注意**:
- `warmup` 表示发电机预热计数，真实工程里通常对应若干秒到数十秒的稳定建压/建频时间
- `transfer_count` 记录 ATS 发生过多少次负载切换：一次切到发电机，一次切回市电
- 这里没有加入发电机启动失败分支，目的是聚焦“事件触发 + 预热守卫 + 供电切换”的主链路

### 4.105 真实系统用例：冷库蒸发器除霜周期

这个例子模拟冷库蒸发器的典型控制：正常制冷时结霜量逐步累积；达到阈值后进入除霜周期；融霜结束后还需要短暂滴水阶段，避免残留水滴被风机再次带入库内，之后才能回到正常制冷。

以下两条执行序列彼此独立，均从相同的初始状态开始。

```python
dsl_code = '''
def int frost = 0;
def int drip_ticks = 0;
state Root {
    state Cooling {
        during {
            frost = frost + 2;
        }
    }

    state DefrostCycle {
        state Defrost {
            during {
                frost = frost - 5;
            }
        }

        state Drip {
            during {
                drip_ticks = drip_ticks + 1;
            }
        }

        [*] -> Defrost;
        Defrost -> Drip : if [frost <= 0] effect {
            frost = 0;
            drip_ticks = 0;
        };
        Drip -> [*] : if [drip_ticks >= 1];
    }

    [*] -> Cooling;
    Cooling -> DefrostCycle : if [frost >= 6];
    DefrostCycle -> Cooling effect {
        drip_ticks = 0;
    };
}
'''
```

**执行序列 A（结霜尚未触发除霜）**:

| 操作 | 当前状态 | frost | drip_ticks | 说明 |
|------|----------|-------|------------|------|
| `runtime.cycle()` | Cooling | 2 | 0 | 初始进入制冷，开始累积结霜 |
| `runtime.cycle()` | Cooling | 4 | 0 | 持续制冷，结霜增加 |
| `runtime.cycle()` | Cooling | 6 | 0 | 结霜达到阈值，下一轮才会切入除霜 |

**详细计算 A**:
```text
初始: frost = 0, drip_ticks = 0

第1次 cycle:
  进入 Cooling
  Cooling.during:
    frost = 0 + 2 = 2

第2次 cycle:
  检查 Cooling->DefrostCycle: frost >= 6 不满足 (当前 frost = 2)
  Cooling.during:
    frost = 2 + 2 = 4

第3次 cycle:
  检查 Cooling->DefrostCycle: frost >= 6 不满足 (当前 frost = 4)
  Cooling.during:
    frost = 4 + 2 = 6
```

**执行序列 B（达到除霜阈值后完成一轮除霜并回制冷）**:

| 操作 | 当前状态 | frost | drip_ticks | 说明 |
|------|----------|-------|------------|------|
| `runtime.cycle()` | Cooling | 2 | 0 | 初始进入制冷 |
| `runtime.cycle()` | Cooling | 4 | 0 | 继续制冷 |
| `runtime.cycle()` | Cooling | 6 | 0 | 结霜达到阈值 |
| `runtime.cycle()` | Defrost | 1 | 0 | 进入除霜周期，先执行融霜 |
| `runtime.cycle()` | Defrost | -4 | 0 | 继续融霜，本轮结束时已足以转入滴水 |
| `runtime.cycle()` | Drip | 0 | 1 | 融霜完成，进入滴水阶段 |
| `runtime.cycle()` | Cooling | 2 | 0 | 滴水结束，恢复制冷 |

**详细计算 B**:
```text
初始: frost = 0, drip_ticks = 0

第1~3次 cycle:
  与执行序列 A 的第1~3次 cycle 相同
  第3次结束后:
    当前状态 = Cooling
    frost = 6, drip_ticks = 0

第4次 cycle:
  检查 Cooling->DefrostCycle: frost >= 6 满足
  Cooling.exit
  Cooling->DefrostCycle
  DefrostCycle.enter
  DefrostCycle.[*] -> Defrost
  Defrost.enter
  Defrost.during:
    frost = 6 - 5 = 1

第5次 cycle:
  检查 Defrost->Drip: frost <= 0 不满足 (当前 frost = 1)
  Defrost.during:
    frost = 1 - 5 = -4

第6次 cycle:
  检查 Defrost->Drip: frost <= 0 满足
  Defrost.exit
  Defrost->Drip effect:
    frost = -4 -> 0
    drip_ticks = 0
  Drip.enter
  Drip.during:
    drip_ticks = 0 + 1 = 1

第7次 cycle:
  检查 Drip->[*]: drip_ticks >= 1 满足
  Drip.exit
  Drip->[*]
  回到 DefrostCycle
  检查 DefrostCycle->Cooling: 无条件满足
  DefrostCycle.exit
  DefrostCycle->Cooling effect:
    drip_ticks = 1 -> 0
  Cooling.enter
  Cooling.during:
    frost = 0 + 2 = 2
```

**注意**:
- `DefrostCycle` 被建模为复合状态，用来表达“融霜 -> 滴水 -> 返回制冷”的工程顺序
- `Defrost -> Drip` 会把负值结霜量归零，表示在业务语义上不关心过融多少，只关心霜层已清除
- 滴水阶段结束后才回到 `Cooling`，符合冷库设备避免带水复风的常见控制习惯

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

### 5.3 Cycle 的实现框架

```python
def cycle(events):
    """
    执行一个完整的 cycle

    参数:
        events: 事件列表
    """
    snapshot = save_runtime_snapshot()

    while True:
        current_state = get_current_state()

        # 如果到达 stoppable 状态，执行 during 并停止
        if current_state.is_stoppable:
            execute_during(current_state, vars)
            break

        progressed = try_advance_with_validation(events)
        if not progressed:
            restore_runtime_snapshot(snapshot)
            warn('Unable to reach stoppable state in current cycle.')
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
- 所有转换都可以使用 cycle 提供的事件

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
- 定义了 cycle 的语义
- 定义了转换验证规则
- 添加了 12 个测试用例
- 明确了执行顺序和优先级规则
