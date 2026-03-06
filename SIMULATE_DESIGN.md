# FSM 模拟运行器设计文档

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
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
A (stoppable) -> B (non-stoppable) -> C (stoppable)  ✓ 有效
A (stoppable) -> B (non-stoppable, 无初始转换)      ✗ 无效
A (stoppable) -> B (non-stoppable) -> [*]           ✗ 无效（退出不算 stoppable）
```

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

**注意**: 伪状态会跳过所有祖先的 aspect actions，只执行自己的 during

### 3.3 转换的执行顺序

执行转换 A -> B 时：
1. 执行 A 的 exit 动作
2. 执行转换的 effect
3. 执行 B 的 enter 动作
4. 如果 B 是复合状态，处理初始转换
5. 如果 B 是叶子状态，执行 B 的 during（包含 aspect actions）

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

**注意**: 伪状态不是 stoppable，所以第一次 cycle 后应该立即退出，但这里有守卫条件 `trace >= 2`，所以会停在 A。

**修正**: 伪状态虽然跳过 aspect，但仍然是叶子状态。如果没有转换可触发，应该停在伪状态并执行 during。

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

**注意**: 当 counter=3 时，A->B 的守卫 `counter >= 5` 不满足，但 A->C 的守卫 `counter >= 3` 满足，所以触发 A->C。

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

**注意**: 这里的验证需要模拟执行 B.enter，发现 flag 会被设置为 1，但初始转换需要 flag==2，所以无法进入 B1。

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

**当前理解**:
- 验证时应该使用变量的快照
- 验证失败后，变量应该恢复到验证前的状态
- 验证成功后，需要重新执行一遍（因为验证时只是模拟）

**待确认**: 是否有更好的实现方式？

### 6.3 事件的作用域

**问题**: 在验证多级转换时，事件是否在整个验证过程中都有效？

**当前理解**:
- 事件在一个 cycle 内都有效
- 验证过程中的所有转换都可以使用这些事件

**待确认**: 是否正确？

### 6.4 During 的执行时机

**问题**: 进入 stoppable 状态后，是立即执行 during 还是等下一次 cycle？

**答案**: 立即执行 during（已确认）

### 6.5 转换后的 during

**问题**: 从 A 转换到 B 后，是否立即执行 B 的 during？

**答案**: 如果 B 是 stoppable，则立即执行 during（已确认）

---

## 7. 更新日志

### v0.1.0 (2026-03-06)
- 初始版本
- 定义了 step 和 cycle 的语义
- 定义了转换验证规则
- 添加了 12 个测试用例
- 明确了执行顺序和优先级规则
