# FCSTM VSCode 扩展功能测试指南

## 重要提示

扩展已经修复并重新安装。请按照以下步骤测试：

## 步骤 1: 重新加载 VSCode 窗口

**必须执行此步骤，否则扩展不会生效！**

1. 按 `Ctrl+Shift+P`（Windows/Linux）或 `Cmd+Shift+P`（Mac）打开命令面板
2. 输入 "Developer: Reload Window"
3. 选择并执行该命令
4. VSCode 会重新加载，扩展会重新激活

## 步骤 2: 打开测试文件

打开文件：`/home/hansbug/oo-projects/pyfcstm/editors/vscode/test-extension.fcstm`

或者创建一个新的 `.fcstm` 文件（文件扩展名必须是 `.fcstm`）

## 功能 1: 语法诊断 (Syntax Diagnostics)

### 测试方法：

1. 打开 `test-extension.fcstm` 文件
2. 查看文件最后一行：`state Error`（故意缺少分号）
3. **等待 500ms**（扩展有防抖延迟）

### 预期效果：

- **红色波浪线**：`state Error` 这一行应该有红色波浪线
- **Problems 面板**：
  - 按 `Ctrl+Shift+M` 打开 Problems 面板
  - 或者点击 VSCode 底部状态栏的错误图标
  - 应该显示 1 个错误，类似：
    ```
    Invalid syntax - check for missing semicolons, braces, or operators
    ```
- **鼠标悬停**：将鼠标悬停在红色波浪线上，会显示错误提示

### 如果没有效果：

1. 确认文件扩展名是 `.fcstm`
2. 确认 VSCode 右下角显示 "FCSTM" 语言标识
3. 等待至少 1 秒（防抖延迟）
4. 尝试修改文件（添加一个空格再删除）触发重新解析

## 功能 2: 文档符号 (Document Symbols / Outline)

### 测试方法：

1. 打开 `test-extension.fcstm` 文件
2. 查看左侧 Explorer 面板下方的 "OUTLINE" 部分
3. 或者按 `Ctrl+Shift+O` 打开符号快速导航

### 预期效果：

**Outline 面板应该显示：**

```
📄 test-extension.fcstm
  ├─ 📦 counter (int)
  ├─ 📦 temperature (float)
  └─ 📋 System
      ├─ ⚡ Start (Start Event)
      ├─ ⚡ Stop
      ├─ 📋 Idle
      └─ 📋 Running
          ├─ 📋 Active
          └─ 📋 Paused
```

**符号快速导航（Ctrl+Shift+O）：**
- 显示所有符号的下拉列表
- 可以输入名称快速过滤
- 选择符号后跳转到对应位置

**面包屑导航：**
- 编辑器顶部显示当前位置的符号路径
- 例如：光标在 `Active` 状态内时，显示 `System > Running > Active`

### 如果没有效果：

1. 确认文件扩展名是 `.fcstm`
2. 确认 Outline 面板已展开（不是折叠状态）
3. 尝试关闭文件再重新打开

## 功能 3: 悬停文档 (Hover Documentation)

### 测试方法：

将鼠标悬停在以下位置（不要点击，只是悬停）：

#### 测试 1: 悬停在 `::` 操作符上

找到这一行：
```fcstm
Idle -> Running :: Start;
```

将鼠标悬停在 `::` 上，应该显示：

```
Local Event Scope

Creates an event scoped to the source state. Each source state gets its own event instance.

Example:
StateA -> StateB :: LocalEvent;
// Event: Parent.StateA.LocalEvent
```

#### 测试 2: 悬停在 `:` 操作符上

找到这一行：
```fcstm
Running -> Idle : Stop;
```

将鼠标悬停在 `:` 上（注意：这里的 `:` 后面紧跟着 `Stop`，没有空格），应该显示：

```
Chain Event Scope

References an event scoped to the parent state. Multiple transitions in the same scope share the event.

Example:
StateA -> StateB : ChainEvent;
// Event: Parent.ChainEvent
```

#### 测试 3: 悬停在 `[*]` 上

找到这一行：
```fcstm
[*] -> Idle;
```

将鼠标悬停在 `[*]` 上，应该显示：

```
Pseudo-State Marker

Represents a pseudo-state for initial or final transitions. Used for entry and exit points.

Example:
[*] -> InitialState;  // Entry transition
FinalState -> [*];    // Exit transition
```

#### 测试 4: 悬停在关键字上

将鼠标悬停在以下关键字上（悬停在单词中间，不是开头或结尾）：

- `state` → 应该显示 "State Definition"
- `event` → 应该显示 "Event Definition"
- `enter` → 应该显示 "Enter Action"
- `during` → 应该显示 "During Action"
- `>> during before` → 应该显示 "Global During Before Aspect"

### 如果没有效果：

1. 确认鼠标悬停在正确的位置（操作符或关键字上）
2. 确认鼠标悬停时间足够长（至少 0.5 秒）
3. 对于关键字，确保悬停在单词中间，不是空格上
4. 对于 `:` 操作符，确保后面紧跟着标识符（没有空格）

## 功能 4: 代码补全 (Code Completion)

### 测试方法：

1. 在文件末尾新起一行
2. 输入 `st`
3. 应该出现补全列表，包含 `state` 关键字

### 其他补全测试：

- 输入 `def int x = `，应该出现 `pi`, `E`, `tau` 等常量
- 输入 `sin`，应该出现 `sin()` 函数补全
- 输入 `cou`，应该出现 `counter` 变量补全

## 故障排查

### 如果所有功能都不工作：

1. **检查扩展是否安装：**
   ```bash
   code --list-extensions | grep fcstm
   ```
   应该显示：`hansbug.fcstm-language-support`

2. **检查扩展是否激活：**
   - 按 `Ctrl+Shift+P` 打开命令面板
   - 输入 "FCSTM: Test Parser"
   - 应该显示 "FCSTM parser is available"

3. **查看开发者工具：**
   - 按 `Ctrl+Shift+P` 打开命令面板
   - 输入 "Developer: Toggle Developer Tools"
   - 在 Console 标签页查看是否有错误信息
   - 应该看到 "FCSTM Language Support extension is now active"

4. **重新安装扩展：**
   ```bash
   cd /home/hansbug/oo-projects/pyfcstm/editors/vscode
   code --install-extension build/fcstm-language-support-0.1.0.vsix --force
   ```
   然后重新加载 VSCode 窗口

### 如果只有部分功能不工作：

- **语法诊断不工作**：检查 Problems 面板是否打开，等待 500ms 防抖延迟
- **Outline 不工作**：检查 Outline 面板是否展开，尝试关闭文件再重新打开
- **Hover 不工作**：确保悬停在正确的位置，悬停时间足够长

## 成功标志

如果以下三个功能都正常工作，说明扩展已经成功修复：

1. ✅ 最后一行 `state Error` 有红色波浪线，Problems 面板显示错误
2. ✅ Outline 面板显示完整的符号树（变量、状态、事件）
3. ✅ 悬停在 `::`, `:`, `[*]`, 关键字上显示文档

## 修复内容

本次修复解决了以下问题：

1. **添加了 `parser/package.json`**：声明 parser 模块为 ES module
2. **修复了动态 import 路径**：使用绝对路径和 file:// URL 确保在 VSCode 扩展环境中正确加载
3. **重新打包扩展**：确保所有文件都包含在 VSIX 包中

这些修复确保了 parser 能够在 VSCode 扩展环境中正确加载和工作。
