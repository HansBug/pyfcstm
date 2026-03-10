# Formal Verification Design for pyfcstm State Machines

## 1. Overview

本设计文档描述了基于Z3求解器的状态机形式化验证系统。该系统旨在验证从给定初始状态和变量约束出发，是否存在一条路径能够到达目标状态，并给出满足条件的变量赋值和事件序列。

### 1.1 核心思想

- **符号执行**: 使用Z3约束求解器对状态机进行符号执行
- **BFS搜索**: 采用广度优先搜索策略探索状态空间
- **事件建模**: 将事件的触发与否建模为布尔变量
- **约束传播**: 通过约束式的合取来表达到达某状态的条件
- **剪枝策略**: 基于约束解空间的扩展性进行剪枝

### 1.2 与simulate模块的关系

- **相似点**: 遵循相同的状态机语义（生命周期动作、转换逻辑、层次结构）
- **不同点**:
  - 不执行DFS（不会自动寻找stoppable state）
  - 不执行abstract handlers
  - 使用符号约束而非具体值
  - 探索所有可能路径而非单一执行路径

## 2. State Representation

### 2.1 状态分类

根据状态机模型，状态分为两类：

1. **叶子状态 (Leaf State)**: `state.is_leaf_state == True`
   - 包括可停留状态 (Stoppable): `state.is_stoppable == True` (非pseudo)
   - 包括伪状态 (Pseudo): `state.is_pseudo == True`
   - **关键区别**：
     - 可停留状态执行aspect actions，BFS时cycle计数+1
     - 伪状态不执行aspect actions，BFS时cycle计数不变

2. **复合状态 (Composite State)**: `state.is_leaf_state == False`
   - 包含子状态的状态
   - BFS时cycle计数不变

### 2.2 验证状态节点 (Verification State Node)

为了进行BFS搜索和剪枝，我们需要定义验证状态节点的概念：

```python
@dataclass
class VerificationStateNode:
    """
    表示验证过程中的一个状态节点
    """
    state: Optional[State]  # 对应的状态机状态（end节点时为None）
    node_type: Literal['leaf', 'composite_in', 'composite_out', 'end']
    # leaf: 叶子状态（包括pseudo和stoppable）
    # composite_in: 复合状态的入口（刚进入复合状态，尚未进入子状态）
    # composite_out: 复合状态的出口（子状态已退出，尚未离开复合状态）
    # end: 终止状态（状态机结束，state为None）

    var_state: Dict[str, z3.ArithRef]  # 到达此节点时的变量状态（符号表达式）
    cycle: int  # 到达此节点经过的周期数
```

**关键设计决策**：

- **复合状态的双节点表示**: 复合状态需要区分"入口"和"出口"两个节点
  - `composite_in`: 表示刚进入复合状态，执行了enter和during before，但尚未进入子状态
  - `composite_out`: 表示子状态已通过`[*]`退出，执行了during after，处于`post_child_exit`模式

- **为什么需要双节点**:
  - 复合状态的during before/after只在边界执行（进入/退出复合状态时）
  - 子状态之间的转换不触发父状态的during before/after
  - 需要区分"从父状态进入"和"从子状态退出"两种情况

## 3. Transition Classification

转换根据源状态和目标状态的类型，可以分为以下11种情况，按4个类别组织：

### 3.1 同级转换 (Same-Level Transitions)

同级转换指源状态和目标状态在同一父状态下的转换。

#### 3.1.1 leaf → leaf (同级叶子状态转换)

**场景**: 同一父状态下的兄弟叶子状态之间的转换（包括stoppable和pseudo）

**执行顺序**:
1. 源状态的exit actions
2. 转换的effect operations
3. 目标状态的enter actions
4. 目标状态的during actions（如果是stoppable则包括aspect actions，如果是pseudo则不包括）

**Cycle计数**: 如果目标状态是stoppable则+1，如果是pseudo则不变

**约束生成**:
```python
# 假设从 StateA -> StateB
constraint_at_A = ...  # 从全局约束管理获取
vars_at_A = ...

# 1. 执行exit actions (通常为空或不影响约束)
# 2. 执行transition effects
vars_after_effect = execute_operations(transition.effects, vars_at_A)

# 3. 执行enter actions
vars_after_enter = execute_operations(StateB.on_enters, vars_after_effect)

# 4. 执行during actions
if StateB.is_pseudo:
    # 伪状态：只执行自己的during，不包括aspect
    vars_after_during = execute_operations(
        StateB.list_on_durings(aspect=None),
        vars_after_enter
    )
    new_cycle = current_cycle  # cycle不变
else:
    # 可停留状态：执行完整的during chain（包括aspect）
    vars_after_during = execute_during_chain(StateB, vars_after_enter)
    new_cycle = current_cycle + 1  # cycle+1

# 最终约束（从全局约束管理获取并更新）
new_constraint = constraint_at_A
if transition.guard:
    new_constraint = z3.And(new_constraint, eval_guard(transition.guard, vars_at_A))
if transition.event:
    new_constraint = z3.And(new_constraint, event_vars[transition.event.path_name])
```

#### 3.1.2 composite_out → leaf (同级复合状态到叶子状态)

**场景**: 从复合状态（composite_out节点）转换到同级叶子状态

**前提**: 源节点必须是`composite_out`类型，表示子状态已退出

**执行顺序**:
1. 源复合状态的exit actions
2. 转换的effect operations
3. 目标叶子状态的enter actions
4. 目标叶子状态的during actions（根据是否pseudo决定是否包括aspect）

**Cycle计数**: 如果目标是stoppable则+1，如果是pseudo则不变

#### 3.1.3 composite_out → composite_in (同级复合状态间转换)

**场景**: 从复合状态（composite_out节点）转换到另一个同级复合状态

**执行顺序**:
1. 源复合状态的exit actions
2. 转换的effect operations
3. 目标复合状态的enter actions
4. **停止** - 生成`composite_in`节点，等待后续探索进入子状态

**Cycle计数**: 不变

**注意**: 目标复合状态的during before actions在后续进入子状态时才执行（见3.2节）

#### 3.1.4 leaf → composite_in (同级叶子状态到复合状态)

**场景**: 从叶子状态转换到同级复合状态

**执行顺序**:
1. 源叶子状态的exit actions
2. 转换的effect operations
3. 目标复合状态的enter actions
4. **停止** - 生成`composite_in`节点，等待后续探索进入子状态

**Cycle计数**: 不变

**注意**: 目标复合状态的during before actions在后续进入子状态时才执行（见3.2节）

#### 3.1.5 leaf stay (可停留状态驻停)

**场景**: 在可停留状态（stoppable leaf state）驻停一个周期

**前提**: 只有stoppable状态可以驻停，pseudo状态不能驻停

**执行顺序**:
1. 执行during chain（包括aspect actions）

**Cycle计数**: +1

**约束生成**:
```python
# 在stoppable state驻停
vars_after_stay = execute_during_chain(stoppable_state, vars_at_state)

# 生成新的leaf节点（状态不变，但变量可能改变）
node = VerificationStateNode(
    state=stoppable_state,
    node_type='leaf',
    var_state=vars_after_stay,
    cycle=current_cycle + 1  # cycle+1
)
```

**注意**:
- 只有stoppable state可以驻停
- 伪状态不能驻停（必须立即转换）
- 复合状态不能驻停（必须进入子状态或退出）

### 3.2 复合状态进入子状态 (Composite to Child Transitions)

这类转换发生在复合状态的入口节点（composite_in）进入其子状态时。

**关键时机**: 父状态的during before actions在此时执行（进入子状态之前）

#### 3.2.1 composite_in → leaf (复合状态进入叶子子状态)

**场景**: 从复合状态的入口节点进入叶子子状态（通过初始转换）

**前提**: 源节点类型为`composite_in`

**执行顺序**:
1. **父状态的during before actions** (关键！)
2. 执行初始转换的effect operations（如果有）
3. 目标子状态的enter actions
4. 目标子状态的during actions（根据是否pseudo决定是否包括aspect）

**Cycle计数**: 如果目标是stoppable则+1，如果是pseudo则不变

**约束生成**:
```python
# 从composite_in节点出发
constraint_at_composite_in = ...
vars_at_composite_in = ...

# 1. 执行父状态的during before actions
vars_after_during_before = execute_operations(
    composite_state.list_on_durings(aspect='before'),
    vars_at_composite_in
)

# 2. 遍历所有初始转换（考虑转换顺序，见3.5节）
for init_transition in composite_state.init_transitions:
    # 检查guard和event
    # ...
    
    # 3. 执行effect
    vars_after_effect = execute_operations(
        init_transition.effects, 
        vars_after_during_before
    )
    
    # 4. 进入目标子状态
    target_child = composite_state.substates[init_transition.to_state]
    # ... 根据target_child类型生成相应节点
```

#### 3.2.2 composite_in → composite_in (复合状态进入复合子状态)

**场景**: 从复合状态的入口节点进入复合子状态（通过初始转换）

**执行顺序**:
1. **父状态的during before actions** (关键！)
2. 执行初始转换的effect operations（如果有）
3. 目标子复合状态的enter actions
4. **停止** - 生成新的`composite_in`节点

**Cycle计数**: 不变

**注意**: 目标子复合状态的during before actions在后续进入其子状态时才执行

### 3.3 子状态退回父状态 (Child to Parent Transitions)

这类转换发生在子状态通过`[*]`退出到父状态时。

**关键时机**: 父状态的during after actions在此时执行（子状态退出之后）

#### 3.3.1 leaf → composite_out (叶子状态退回父复合状态)

**场景**: 从叶子状态退出到父状态（父状态不是root）

**执行顺序**:
1. 源叶子状态的exit actions
2. 转换的effect operations
3. **父状态的during after actions** (关键！)
4. 生成父状态的`composite_out`节点

**Cycle计数**: 不变

**约束生成**:
```python
# 执行exit和effect
vars_after_exit = execute_operations(LeafState.on_exits, vars_at_leaf)
vars_after_effect = execute_operations(transition.effects, vars_after_exit)

# 执行父状态的during after
parent = LeafState.parent
vars_after_during_after = execute_operations(
    parent.list_on_durings(aspect='after'),
    vars_after_effect
)

# 生成composite_out节点
node = VerificationStateNode(
    state=parent,
    node_type='composite_out',
    var_state=vars_after_during_after,
    cycle=current_cycle  # cycle不变
)
```

#### 3.3.2 composite_out → composite_out (复合子状态退回父复合状态)

**场景**: 从复合子状态（composite_out节点）退出到父复合状态

**执行顺序**:
1. 源子复合状态的exit actions
2. 转换的effect operations
3. **父复合状态的during after actions** (关键！)
4. 生成父复合状态的`composite_out`节点

**Cycle计数**: 不变

### 3.4 终止转换 (Termination Transitions)

这类转换导致状态机终止（退出到root状态）。由于root状态必然是composite状态，因此只有composite_out节点可以退出到end。

#### 3.4.1 composite_out → end (复合状态退出到终止)

**场景**: 从复合状态（composite_out节点）退出到父状态，且父状态是root

**执行顺序**:
1. 源复合状态的exit actions
2. 转换的effect operations
3. **父状态（root）的during after actions** (关键！)
4. 生成`end`节点（state为None）

**Cycle计数**: 不变

**注意**: 不存在 leaf → end 的情况，因为：
- 只有root状态可以退出到end
- root状态必然是composite状态（包含所有其他状态）
- 因此只能从composite_out节点退出到end

### 3.5 转换顺序与约束处理

**关键问题**: 状态的转换列表是有顺序的，靠后的转换只有在前面的转换都未触发时才会被考虑。

**适用场景**:
- 对于 leaf 和 composite_out 节点：使用 `list_transitions` 获取转换列表
- 对于 composite_in 节点：使用 `init_transitions` 获取初始转换列表

**处理策略**:

当从某个状态列举可能的转换时，需要考虑转换的先后顺序：

```python
def generate_transition_successors(node, transitions):
    """
    生成转换后继节点，考虑转换顺序

    :param node: 当前节点
    :param transitions: 转换列表（有序）
    :return: 后继节点列表
    """
    successors = []
    accumulated_negation = z3.Bool(True)  # 累积的"前面转换都未触发"条件

    for transition in transitions:
        # 当前转换的真正触发条件 = 前面转换都未触发 AND 当前转换条件
        transition_condition = accumulated_negation

        # 添加当前转换的guard条件
        if transition.guard:
            guard_expr = eval_guard(transition.guard, node.var_state)
            transition_condition = z3.And(transition_condition, guard_expr)

        # 添加当前转换的event条件
        if transition.event:
            event_var = event_vars[transition.event.path_name]
            transition_condition = z3.And(transition_condition, event_var)

        # 生成后继节点（带上完整的转换条件）
        successor = generate_successor_with_constraint(
            node,
            transition,
            transition_condition
        )
        successors.append(successor)

        # 更新累积否定条件：前面转换都未触发 AND 当前转换也未触发
        current_not_taken = z3.Not(transition_condition)
        accumulated_negation = z3.And(accumulated_negation, current_not_taken)

    # 如果当前状态是stoppable，添加驻停后继
    # 驻停的条件是：所有转换都未触发
    if node.node_type == 'leaf' and node.state.is_stoppable:
        stay_successor = generate_stay_successor_with_constraint(
            node,
            accumulated_negation  # 所有转换都未触发的条件
        )
        successors.append(stay_successor)

    return successors
```

**示例**:

假设状态A（stoppable）有三个转换：
1. `A -> B : if [x > 10]`
2. `A -> C : if [x > 5]`
3. `A -> D`

实际的触发条件应该是：
1. 转换1: `x > 10`
2. 转换2: `NOT(x > 10) AND (x > 5)` = `x > 5 AND x <= 10`
3. 转换3: `NOT(x > 10) AND NOT(x > 5)` = `x <= 5`
4. 驻停: `NOT(x > 10) AND NOT(x > 5) AND NOT(True)` = `x <= 5 AND False` = **永远不会驻停**

**注意**：在上面的例子中，由于转换3没有guard条件（无条件转换），所以驻停永远不会发生。只有当所有转换都有可能不满足时，驻停才可能发生。

**更实际的例子**:

假设状态A（stoppable）有两个转换：
1. `A -> B : if [x > 10]`
2. `A -> C : if [x < 5]`

实际的触发条件应该是：
1. 转换1: `x > 10`
2. 转换2: `NOT(x > 10) AND (x < 5)` = `x < 5`
3. 驻停: `NOT(x > 10) AND NOT(x < 5)` = `5 <= x <= 10`

这样可以确保转换和驻停之间是互斥的，符合状态机的语义。

**注意事项**:
- 转换顺序在DSL中定义，必须严格遵守
- 每个转换的实际触发条件是其自身条件与前面所有转换未触发条件的合取
- 这个处理对于 leaf、composite_out 的普通转换和 composite_in 的初始转换都适用
- **驻停操作的触发条件是所有转换都未触发**（accumulated_negation）
- 只有 stoppable 状态可以驻停，pseudo 状态和 composite 状态不能驻停
- 如果存在无条件转换（无guard和event），则驻停永远不会发生

## 4. Aspect Actions 执行逻辑

### 4.1 Aspect Actions的层次结构

根据`model.py`中的实现，aspect actions的执行顺序如下：

```python
# 对于叶子状态的during chain
def execute_during_chain(leaf_state, vars):
    # 1. Before aspect actions (从root到当前状态)
    for ancestor in path_from_root_to_state(leaf_state):
        for action in ancestor.list_on_during_aspects(aspect='before'):
            execute(action, vars)

    # 2. 当前状态的during actions
    for action in leaf_state.list_on_durings(aspect=None):
        execute(action, vars)

    # 3. After aspect actions (从当前状态到root)
    for ancestor in path_from_state_to_root(leaf_state):
        for action in ancestor.list_on_during_aspects(aspect='after'):
            execute(action, vars)
```

**关键点**:
- Aspect actions (`>> during before/after`) 只在叶子状态的during phase执行
- 伪状态跳过所有aspect actions
- 复合状态的during before/after（无`>>`）只在边界执行，不是aspect actions

### 4.2 复合状态的during before/after

**重要区别**: 复合状态的during before/after（无`>>`前缀）与aspect actions不同：

```python
state CompositeState {
    during before {  # 只在进入复合状态时执行（[*] -> Child）
        // ...
    }

    during after {   # 只在退出复合状态时执行（Child -> [*]）
        // ...
    }

    >> during before {  # 这是aspect action，在所有后代叶子状态的during phase执行
        // ...
    }
}
```

**执行时机**:
- `during before` (无`>>`): 在`composite_in`节点生成时执行
- `during after` (无`>>`): 在子状态退出到父状态时执行（生成`composite_out`节点）
- `>> during before/after`: 在后代叶子状态的during chain中执行

## 5. Pruning Strategy (剪枝策略)

### 5.1 核心思想

**关键观察**: 对于状态机验证，到达某个状态的"历史路径"并不重要，重要的是：
1. 能否到达该状态
2. 到达时变量的可能取值范围

因此，我们对每个验证状态节点维护一个全局的"到达约束"，表示所有可能到达该节点的条件。约束不存储在节点内部，而是由全局约束管理器统一维护。

### 5.2 约束合并与剪枝

**数据结构**:
```python
# 全局约束管理器：为每个验证状态节点维护已访问记录
visited: Dict[Tuple[Optional[State], NodeType], z3.BoolRef] = {}
# Key: (state, node_type)
#   - state可以是None（对于end节点）
#   - node_type: 'leaf', 'composite_in', 'composite_out', 'end'
# Value: 到达该节点的约束（多条路径的析取）
```

**剪枝规则**:

当BFS探索到一个新节点时：
1. 计算到达该节点的约束 `new_constraint`（基于父节点约束 + guard + event）
2. 查找 `visited[(state, node_type)]` 获取已有约束 `old_constraint`
3. 检查是否存在解空间扩展：
   ```python
   # 检查是否存在满足new但不满足old的解
   solver = z3.Solver()
   solver.add(new_constraint)
   solver.add(z3.Not(old_constraint))
   
   if solver.check() == z3.sat:
       # 存在解空间扩展，需要继续探索
       visited[(state, node_type)] = z3.Or(old_constraint, new_constraint)
       return True  # 继续探索
   else:
       # 新约束完全被旧约束包含，剪枝
       return False  # 剪枝
   ```

**优化**: 为了避免频繁的求解器调用，可以使用以下策略：
- 如果 `new_constraint` 在语法上与 `old_constraint` 相同，直接剪枝
- 维护一个约束的"规范化"形式，便于比较
- 使用超时机制，避免复杂约束的求解时间过长

### 5.3 为什么这个剪枝策略有效

**正确性论证**:

1. **单调性**: 约束的析取只会扩大解空间，不会缩小
2. **完备性**: 如果存在一条路径到达目标，该路径的约束必然会被记录
3. **终止性**: 状态空间有限，约束的析取最终会收敛

**示例**:

假设有两条路径到达状态S：
- 路径1: `x > 10 and y < 5`
- 路径2: `x > 5 and y < 10`

合并后的约束: `(x > 10 and y < 5) or (x > 5 and y < 10)`

如果后续出现路径3: `x > 15 and y < 3`，检查发现：
- 路径3的约束被路径1包含（`x > 15 => x > 10`, `y < 3 => y < 5`）
- 因此路径3不会扩展解空间，可以剪枝

## 6. BFS Algorithm

### 6.1 算法框架

```python
def verify_reachability(
    state_machine: StateMachine,
    initial_state: State,
    initial_constraint: z3.BoolRef,
    initial_vars: Dict[str, z3.ArithRef],
    target_state: State,
    target_node_type: NodeType,
    max_depth: int = 1000,
    max_cycle: int = 100,
    max_solutions: int = 10
) -> Optional[VerificationResult]:
    """
    验证从初始状态是否能到达目标状态

    :param max_depth: 最大搜索深度（防止大量non-stoppable状态无限循环）
    :param max_cycle: 最大周期数（主要限制条件）
    :param max_solutions: 最大解数（默认10），达到此数量后停止搜索
    """
    # 初始化
    queue = deque()
    visited = {}  # 全局约束管理器
    solutions = []  # 存储找到的解

    # 创建初始节点
    initial_node = VerificationStateNode(
        state=initial_state,
        node_type=determine_node_type(initial_state),
        var_state=initial_vars,
        cycle=0  # 初始周期为0
    )
    queue.append((initial_node, initial_constraint))  # (节点, 约束)

    # BFS主循环
    depth = 0
    while queue and depth < max_depth:
        current_node, current_constraint = queue.popleft()
        depth += 1

        # 检查cycle限制
        if current_node.cycle > max_cycle:
            continue

        # 检查剪枝
        key = (current_node.state, current_node.node_type)
        if not should_explore(current_constraint, visited.get(key)):
            continue

        # 更新visited（全局约束管理）
        old_constraint = visited.get(key)
        if old_constraint is not None:
            visited[key] = z3.Or(old_constraint, current_constraint)
        else:
            visited[key] = current_constraint

        # 检查是否到达目标状态
        target_key = (target_state, target_node_type)
        if key == target_key:
            # 目标状态的约束被更新，尝试求解
            target_constraint = visited[target_key]
            result = solve(
                constraints=target_constraint,
                max_solutions=max_solutions
            )
            solutions = result.solutions

            # 如果一次性获得了足够的解，停止搜索
            if len(solutions) >= max_solutions:
                return VerificationResult(
                    reachable=True,
                    constraint=target_constraint,
                    solutions=solutions[:max_solutions],  # 只返回max_solutions个解
                    cycles=current_node.cycle
                )
            # 否则继续搜索，期待约束进一步扩展后能获得更多解

        # 扩展后继节点
        successors = generate_successors(current_node, current_constraint, state_machine)
        queue.extend(successors)  # successors是(节点, 约束)的列表

    # 搜索结束，检查是否找到了足够的解
    target_key = (target_state, target_node_type)
    if target_key in visited:
        target_constraint = visited[target_key]
        result = solve(
            constraints=target_constraint,
            max_solutions=max_solutions
        )
        solutions = result.solutions

        if len(solutions) >= max_solutions:
            return VerificationResult(
                reachable=True,
                constraint=target_constraint,
                solutions=solutions[:max_solutions],
                cycles=None  # 多个解可能有不同的cycle数
            )
        else:
            # 找到了目标状态但解数不足
            return VerificationResult(
                reachable=True,
                constraint=target_constraint,
                solutions=solutions,
                cycles=None,
                insufficient_solutions=True  # 标记解数不足
            )
    else:
        # 未找到目标状态
        return VerificationResult(
            reachable=False,
            constraint=None,
            solutions=[],
            cycles=None
        )
```

**使用pyfcstm.solver.solve求解**:

验证系统使用`pyfcstm.solver.solve`函数进行约束求解，该函数已经实现了多解求解功能。

```python
from pyfcstm.solver import solve

# 调用solve函数获取多个解
result = solve(
    constraints=target_constraint,     # Z3约束表达式（单个或列表）
    max_solutions=max_solutions        # 最大解数
)

# result是SolveResult对象
# result.status: 'sat', 'unsat', 或 'unknown'
# result.solutions: 解的列表，每个元素是变量名到值的字典
# result.variables: 变量名列表

# 例如:
# result.solutions = [{'x': 5, 'y': 10}, {'x': 7, 'y': 8}, ...]
```

**solve函数说明**:
- 位于`pyfcstm.solver`模块
- 函数签名：`solve(constraints, max_solutions=10, timeout=None, warn_threshold=1000)`
- 参数：
  - `constraints`: Z3约束表达式（单个ExprRef或列表）
  - `max_solutions`: 最大解数（默认10），None表示所有解
  - `timeout`: 求解器超时时间（毫秒）
  - `warn_threshold`: 当max_solutions=None时的警告阈值
- 返回：`SolveResult`对象，包含status、solutions和variables
- 自动从约束中提取所有变量
- 内部使用blocking clause确保解的多样性
- 如果约束无解，返回status='unsat'和空solutions列表

**关键设计决策**:

1. **一次性求解**: 每次到达目标状态（或目标状态约束更新）时，调用solve函数尝试一次性获取max_solutions个解
2. **非累积策略**: 解数不能累积，必须一次性获得max_solutions数量的解才算成功
3. **提前终止**: 一旦一次性获得足够的解（≥max_solutions），立即停止BFS搜索
4. **约束扩展**: 如果当前约束无法提供足够的解，继续BFS以扩展约束（通过Or合并更多路径）
5. **解的多样性**: solve函数内部使用blocking clause确保每次求解得到不同的解

**求解流程**:

```
BFS循环 {
    到达目标状态 -> 约束更新 -> 尝试求解max_solutions个解

    if 解数 >= max_solutions:
        停止搜索，返回成功
    else:
        继续BFS，期待约束进一步扩展
}

搜索结束 {
    if 解数 >= max_solutions:
        返回成功
    else if 解数 > 0:
        返回成功但标记解数不足
    else:
        返回不可达
}
```

**注意事项**:
- max_solutions默认为10，可以根据需要调整
- 如果搜索结束时解数少于max_solutions，返回insufficient_solutions标记
- 每个解包含所有变量的具体赋值
- 不同的解可能对应不同的到达路径和cycle数
- 约束的扩展（通过Or合并）会增加解空间，从而可能产生更多解

### 6.2 后继节点生成

```python
def generate_successors(
    node: VerificationStateNode,
    constraint: z3.BoolRef,
    state_machine: StateMachine
) -> List[Tuple[VerificationStateNode, z3.BoolRef]]:
    """
    生成当前节点的所有后继节点

    :param node: 当前节点
    :param constraint: 到达当前节点的约束
    :param state_machine: 状态机模型
    :return: (后继节点, 后继约束)的列表
    """
    successors = []

    if node.node_type == 'leaf':
        # 叶子状态的后继
        if node.state.is_stoppable:
            # 1. 驻停（执行during chain）
            stay_node, stay_constraint = generate_stay_successor(node, constraint)
            successors.append((stay_node, stay_constraint))

        # 2. 转换到其他状态（考虑转换顺序）
        transition_successors = generate_transition_successors(
            node, constraint, node.state.transitions_from
        )
        successors.extend(transition_successors)

    elif node.node_type == 'composite_in':
        # 复合状态入口的后继：初始转换（考虑转换顺序）
        init_successors = generate_transition_successors(
            node, constraint, node.state.init_transitions
        )
        successors.extend(init_successors)

    elif node.node_type == 'composite_out':
        # 复合状态出口的后继：父级转换（考虑转换顺序）
        transition_successors = generate_transition_successors(
            node, constraint, node.state.transitions_from
        )
        successors.extend(transition_successors)

    elif node.node_type == 'end':
        # 终止状态无后继
        pass

    return successors

def generate_stay_successor(
    node: VerificationStateNode,
    constraint: z3.BoolRef
) -> Tuple[VerificationStateNode, z3.BoolRef]:
    """
    生成驻停后继节点（只适用于stoppable状态）

    :return: (后继节点, 后继约束)
    """
    # 执行during chain
    vars_after_stay = execute_during_chain(node.state, node.var_state)

    # 生成新节点
    stay_node = VerificationStateNode(
        state=node.state,
        node_type='leaf',
        var_state=vars_after_stay,
        cycle=node.cycle + 1  # cycle+1
    )

    return stay_node, constraint  # 约束不变
```

    elif node.node_type == 'composite_out':
        # 复合状态出口的后继：父级转换
        for transition in node.state.transitions_from:
            succ = generate_transition_successor(node, transition)
            if succ:
                successors.append(succ)
    
    elif node.node_type == 'end':
        # 终止状态无后继
        pass
    
    return successors
```

### 6.3 事件建模

**事件变量**:
```python
# 为每个事件创建一个布尔变量
event_vars: Dict[str, z3.Bool] = {}
for event in state_machine.all_events():
    event_vars[event.path_name] = z3.Bool(f'event_{event.path_name}')
```

**事件约束**:
- 当转换需要事件时，添加约束 `event_vars[event_name] == True`
- 事件变量在整个验证过程中保持符号化，由求解器决定其取值

**事件序列提取**:
- 当找到可达路径时，从求解器的模型中提取事件变量的赋值
- 只保留值为True的事件，构成事件序列

## 7. Implementation Considerations

### 7.1 变量状态的符号化

**挑战**: 变量状态需要在整个BFS过程中保持符号化

**解决方案**:
```python
# 使用Z3的符号变量表示变量状态
z3_vars = {
    'x': z3.Int('x'),
    'y': z3.Real('y'),
    # ...
}

# 变量状态是Z3表达式的字典
var_state: Dict[str, z3.ArithRef] = {
    'x': z3.Int('x') + 5,  # 表示x的当前值是初始值+5
    'y': z3.Real('y') * 2,
    # ...
}
```

### 7.2 操作执行的符号化

**操作执行**:
```python
def execute_operations_symbolic(
    operations: List[Operation],
    var_state: Dict[str, z3.ArithRef],
    z3_vars: Dict[str, z3.ArithRef]
) -> Dict[str, z3.ArithRef]:
    """
    符号化执行操作序列
    """
    new_state = dict(var_state)
    for op in operations:
        # 将表达式转换为Z3表达式
        z3_expr = expr_to_z3(op.expr, new_state)
        new_state[op.var_name] = z3_expr
    return new_state
```

### 7.3 约束简化

**问题**: 随着BFS深度增加，约束会变得越来越复杂

**优化策略**:
1. **定期简化**: 使用 `z3.simplify()` 简化约束
2. **约束分解**: 将大的约束分解为多个小约束
3. **冗余消除**: 检测并移除冗余约束

### 7.4 性能优化

**超时机制**:
```python
# 为求解器设置超时
solver.set('timeout', 5000)  # 5秒超时
```

**增量求解**:
```python
# 使用增量求解器，避免重复添加相同约束
solver = z3.Solver()
solver.push()  # 保存状态
solver.add(new_constraint)
result = solver.check()
solver.pop()   # 恢复状态
```

**并行化**:
- 可以考虑并行探索多个分支
- 使用多个求解器实例

## 8. API Design

### 8.1 主要接口

```python
@dataclass
class VerificationResult:
    """验证结果"""
    reachable: bool  # 是否可达
    constraint: Optional[z3.BoolRef]  # 可达的约束条件
    solutions: List[Dict[str, Union[int, float]]]  # 变量赋值解的列表
    event_sequence: Optional[List[str]]  # 事件序列
    path: Optional[List[VerificationStateNode]]  # 路径（可选）
    cycles: Optional[int]  # 到达目标所需的周期数（单解情况）
    insufficient_solutions: bool = False  # 是否解数不足（找到目标但解数<max_solutions）

def verify_reachability(
    state_machine: StateMachine,
    initial_state: Union[str, State],
    initial_constraint: Optional[z3.BoolRef] = None,
    initial_vars: Optional[Dict[str, Union[int, float, z3.ArithRef]]] = None,
    target_state: Union[str, State],
    target_node_type: Optional[NodeType] = None,
    timeout: Optional[int] = None,
    max_depth: Optional[int] = 1000,
    max_cycle: Optional[int] = 100,
    max_solutions: Optional[int] = 10
) -> VerificationResult:
    """
    验证从初始状态是否能到达目标状态

    :param state_machine: 状态机模型
    :param initial_state: 初始状态（状态对象或路径字符串）
    :param initial_constraint: 初始约束（默认为True）
    :param initial_vars: 初始变量值或约束
    :param target_state: 目标状态
    :param target_node_type: 目标节点类型（默认自动推断）
    :param timeout: 超时时间（秒）
    :param max_depth: 最大搜索深度（防止大量non-stoppable状态无限循环），默认1000
    :param max_cycle: 最大周期数（主要限制条件），默认100
    :param max_solutions: 最大解数（默认10），达到此数量后停止搜索
    :return: 验证结果
    """
    pass

def verify_invariant(
    state_machine: StateMachine,
    invariant: z3.BoolRef,
    initial_state: Optional[Union[str, State]] = None,
    initial_constraint: Optional[z3.BoolRef] = None,
    timeout: Optional[int] = None,
    max_depth: Optional[int] = 1000,
    max_cycle: Optional[int] = 100
) -> VerificationResult:
    state_machine: StateMachine,
    initial_state: Union[str, State],
    initial_constraint: Optional[z3.BoolRef] = None,
    initial_vars: Optional[Dict[str, Union[int, float, z3.ArithRef]]] = None,
    target_state: Union[str, State],
    target_node_type: Optional[NodeType] = None,
    timeout: Optional[int] = None,
    max_depth: Optional[int] = 1000,
    max_cycle: Optional[int] = 100
) -> VerificationResult:
    """
    验证从初始状态是否能到达目标状态

    :param state_machine: 状态机模型
    :param initial_state: 初始状态（状态对象或路径字符串）
    :param initial_constraint: 初始约束（默认为True）
    :param initial_vars: 初始变量值或约束
    :param target_state: 目标状态
    :param target_node_type: 目标节点类型（默认自动推断）
    :param timeout: 超时时间（秒）
    :param max_depth: 最大搜索深度（防止大量non-stoppable状态无限循环），默认1000
    :param max_cycle: 最大周期数（主要限制条件），默认100
    :return: 验证结果
    """
    pass

def verify_invariant(
    state_machine: StateMachine,
    invariant: z3.BoolRef,
    initial_state: Optional[Union[str, State]] = None,
    initial_constraint: Optional[z3.BoolRef] = None,
    timeout: Optional[int] = None,
    max_depth: Optional[int] = 1000,
    max_cycle: Optional[int] = 100
) -> VerificationResult:
    """
    验证不变式是否在所有可达状态下成立

    :param state_machine: 状态机模型
    :param invariant: 不变式（Z3布尔表达式）
    :param initial_state: 初始状态（默认从root开始）
    :param initial_constraint: 初始约束
    :param timeout: 超时时间（秒）
    :param max_depth: 最大搜索深度，默认1000
    :param max_cycle: 最大周期数，默认100
    :return: 验证结果（如果不变式被违反，返回反例）
    """
    pass
```

### 8.2 辅助函数

```python
def create_z3_constraint_from_dsl(
    constraint_code: str,
    z3_vars: Dict[str, z3.ArithRef]
) -> z3.BoolRef:
    """
    从DSL约束代码创建Z3约束

    :param constraint_code: DSL约束代码（如 "x > 10 and y < 5"）
    :param z3_vars: Z3变量字典
    :return: Z3约束
    """
    pass

def extract_concrete_values(
    model: z3.ModelRef,
    z3_vars: Dict[str, z3.ArithRef]
) -> Dict[str, Union[int, float]]:
    """
    从Z3模型中提取具体变量值

    :param model: Z3模型
    :param z3_vars: Z3变量字典
    :return: 变量赋值字典
    """
    pass
```

## 9. Example Usage

### 9.1 基本可达性验证

```python
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.verify import verify_reachability
import z3

# 解析状态机
dsl_code = '''
def int counter = 0;

state System {
    state Idle {
        during { counter = counter + 1; }
    }
    state Active {
        during { counter = counter + 10; }
    }
    [*] -> Idle;
    Idle -> Active : if [counter >= 5];
}
'''
ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
sm = parse_dsl_node_to_state_machine(ast)

# 验证可达性
result = verify_reachability(
    state_machine=sm,
    initial_state="System.Idle",
    initial_constraint=z3.Bool(True),  # 无额外约束
    target_state="System.Active"
)

if result.reachable:
    print(f"可达！")
    print(f"变量赋值示例: {result.var_assignment}")
    print(f"事件序列: {result.event_sequence}")
else:
    print("不可达")
```

### 9.2 带约束的验证

```python
# 创建Z3变量
z3_vars = {'counter': z3.Int('counter')}

# 验证：从counter=0开始，能否在counter<10的约束下到达Active状态
result = verify_reachability(
    state_machine=sm,
    initial_state="System.Idle",
    initial_constraint=z3_vars['counter'] == 0,
    target_state="System.Active",
    # 额外约束：到达时counter必须小于10
    # 这可以通过修改target_constraint参数实现（需要扩展API）
)
```

### 9.3 不变式验证

```python
# 验证不变式：counter永远不会超过100
z3_vars = {'counter': z3.Int('counter')}
invariant = z3_vars['counter'] <= 100

result = verify_invariant(
    state_machine=sm,
    invariant=invariant,
    initial_state="System.Idle"
)

if result.reachable:
    # 找到反例
    print(f"不变式被违反！")
    print(f"反例状态: {result.path[-1].state.path}")
    print(f"反例变量值: {result.var_assignment}")
else:
    print("不变式成立")
```

## 10. Testing Strategy

### 10.1 单元测试

**测试覆盖**:
1. 每种转换类型（9种 + 特殊转换）
2. Aspect actions的执行顺序
3. 约束合并和剪枝逻辑
4. 事件建模
5. 符号执行的正确性

**测试用例示例**:
```python
def test_leaf_to_leaf_transition():
    """测试叶子状态到叶子状态的转换"""
    dsl_code = '''
    def int x = 0;
    state Root {
        state A { during { x = x + 1; } }
        state B { during { x = x + 10; } }
        [*] -> A;
        A -> B : if [x >= 5];
    }
    '''
    # ... 验证逻辑
```

### 10.2 集成测试

**测试场景**:
1. 简单状态机（2-3个状态）
2. 复杂层次状态机（多层嵌套）
3. 带循环的状态机
4. 带事件的状态机
5. 带复杂约束的状态机

### 10.3 性能测试

**测试指标**:
1. 不同状态数量下的验证时间
2. 不同约束复杂度下的验证时间
3. 剪枝效果（访问节点数 vs 总节点数）
4. 内存使用

## 11. Future Enhancements

### 11.1 短期改进

1. **路径提取**: 记录完整的路径信息，便于调试
2. **反例最小化**: 当不变式被违反时，生成最小反例
3. **约束优化**: 更智能的约束简化策略
4. **并行化**: 并行探索多个分支

### 11.2 长期扩展

1. **时序逻辑**: 支持LTL/CTL时序逻辑验证
2. **概率验证**: 支持概率状态机的验证
3. **反向搜索**: 从目标状态反向搜索到初始状态
4. **抽象解释**: 使用抽象解释技术加速验证

## 12. Open Questions

### 12.1 需要讨论的问题

1. **驻停的语义**:
   - 驻停是否应该消耗"时间"？
   - 是否需要限制驻停次数？
   - 驻停时during chain的执行是否应该建模为约束？

2. **事件的语义**:
   - 事件是否可以在同一个cycle中多次触发？
   - 事件的作用域如何影响验证？
   - 全局事件 vs 局部事件的建模差异？

3. **约束复杂度**:
   - 如何处理非线性约束？
   - 如何处理浮点数约束？
   - 是否需要支持位运算约束？

4. **剪枝策略的调优**:
   - 何时调用求解器检查解空间扩展？
   - 是否需要启发式策略？
   - 如何平衡精确性和性能？

5. **与simulate的一致性**:
   - 如何确保验证结果与实际执行一致？
   - 是否需要交叉验证机制？

### 12.2 实现优先级

**Phase 1** (核心功能):
- [ ] 基本的BFS框架
- [ ] 9种转换类型的实现
- [ ] 简单的剪枝策略（语法相等）
- [ ] 基本的可达性验证API

**Phase 2** (优化):
- [ ] 基于求解器的剪枝策略
- [ ] 事件建模
- [ ] 约束简化
- [ ] 性能优化

**Phase 3** (扩展):
- [ ] 不变式验证
- [ ] 路径提取
- [ ] 反例生成
- [ ] 文档和测试

## 13. References

### 13.1 相关代码

- `pyfcstm/model/model.py`: 状态机模型定义
- `pyfcstm/simulate/runtime.py`: 运行时执行逻辑
- `pyfcstm/solver/expr.py`: Z3表达式转换
- `pyfcstm/solver/operation.py`: 操作解析和执行

### 13.2 相关文档

- `CLAUDE.md`: 项目架构和DSL语言参考
- `docs/source/tutorials/`: 教程文档

---

**文档版本**: v0.9
**最后更新**: 2026-03-11
**作者**: AI Assistant
**状态**: Draft - 待讨论

**v0.9 更新内容**:
- 修正solve函数的正确用法：
  - 参数是`constraints`（Z3约束表达式），不是`var_defines`
  - 返回`SolveResult`对象，包含status、solutions和variables
  - solve函数自动从约束中提取变量，无需手动传入变量列表
- 更新代码示例，使用`result.solutions`获取解列表
- 添加solve函数的完整签名和参数说明

**v0.8 更新内容**:
- 使用`pyfcstm.solver.solve`函数进行约束求解，而不是自定义的extract_solutions
- solve函数接受constraint、var_defines和max_solutions参数
- 删除extract_solutions函数定义，改为说明solve函数的使用方法
- 明确solve函数位于pyfcstm.solver模块

**v0.7 更新内容**:
- 添加max_solutions参数（默认10）到BFS算法和API
- 实现多解求解策略：一次性获得max_solutions个解才算成功
- 解数不能累积，每次到达目标状态时重新求解
- 添加insufficient_solutions标记，表示找到目标但解数不足
- 更新VerificationResult，将var_assignment改为solutions列表
- 详细说明求解流程和约束扩展机制

**v0.6 更新内容**:
- 修正驻停操作的处理逻辑：驻停也需要考虑转换顺序
- 驻停的触发条件是所有转换都未触发（accumulated_negation）
- 在3.5节中添加驻停处理的代码示例
- 添加两个示例说明驻停条件的计算
- 明确只有stoppable状态可以驻停

**v0.5 更新内容**:
- 恢复3.5节"转换顺序与约束处理"的完整内容
- 明确转换顺序处理逻辑：靠后的转换需要考虑前面所有转换都未触发的条件
- 说明适用场景：leaf/composite_out使用list_transitions，composite_in使用init_transitions
- 添加详细的代码示例和注意事项

**v0.4 更新内容**:
- 补充同级转换：leaf → composite_in（3.1.4节）
- 删除不存在的转换：leaf → end（因为root必然是composite，只能从composite_out退出到end）
- 转换类型最终确定为11种：
  - 3.1 同级转换 (5种)
  - 3.2 复合状态进入子状态 (2种)
  - 3.3 子状态退回父状态 (2种)
  - 3.4 终止转换 (1种)
  - 3.5 转换顺序与约束处理

**v0.3 更新内容**:
- 纠正during before/after的执行时机：during before在父状态进入子状态时执行，during after在子状态退回父状态时执行
- 补充遗漏的 leaf → composite_out 转换类型
- 重新组织转换类型按4个类别分组
- 明确各类转换中during before/after的执行位置

**v0.2 更新内容**:
- 统一叶子状态分类（合并pseudo和stoppable，区别在于aspect执行和cycle计数）
- 移除节点内部的constraint字段，改为全局约束管理
- state字段改为Optional（end节点时为None）
- 添加cycle字段到VerificationStateNode
- 添加转换顺序处理逻辑（考虑前序转换未触发条件）
- 添加max_cycle参数（主要限制条件）和max_depth参数（防御性限制）
- 明确cycle计数规则：stoppable状态+1，pseudo和composite状态不变

- 移除节点内部的constraint字段，改为全局约束管理
- state字段改为Optional（end节点时为None）
- 添加cycle字段到VerificationStateNode
- 添加转换顺序处理逻辑（考虑前序转换未触发条件）
- 添加max_cycle参数（主要限制条件）和max_depth参数（防御性限制）
- 明确cycle计数规则：stoppable状态+1，pseudo和composite状态不变

- 明确各类转换中during before/after的执行位置

**v0.2 更新内容**:
- 统一叶子状态分类（合并pseudo和stoppable，区别在于aspect执行和cycle计数）
- 移除节点内部的constraint字段，改为全局约束管理
- state字段改为Optional（end节点时为None）
- 添加cycle字段到VerificationStateNode
- 添加转换顺序处理逻辑（考虑前序转换未触发条件）
- 添加max_cycle参数（主要限制条件）和max_depth参数（防御性限制）
- 明确cycle计数规则：stoppable状态+1，pseudo和composite状态不变

- 添加转换顺序处理逻辑（考虑前序转换未触发条件）
- 添加max_cycle参数（主要限制条件）和max_depth参数（防御性限制）
- 明确cycle计数规则：stoppable状态+1，pseudo和composite状态不变

- 添加转换顺序处理逻辑（考虑前序转换未触发条件）
- 添加max_cycle参数（主要限制条件）和max_depth参数（防御性限制）
- 明确cycle计数规则：stoppable状态+1，pseudo和composite状态不变

