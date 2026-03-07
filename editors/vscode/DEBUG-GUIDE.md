# VSCode 扩展调试完整指南

## 当前状态

扩展已经添加了详细的调试日志，并重新安装。现在需要你按照以下步骤获取日志信息。

## 步骤 1: 打开开发者工具（最重要！）

1. 在 VSCode 中按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Developer: Toggle Developer Tools"
3. 选择并执行
4. 会打开一个类似浏览器开发者工具的窗口

## 步骤 2: 重新加载 VSCode 窗口

**这一步非常重要！必须在打开开发者工具后重新加载！**

1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Developer: Reload Window"
3. 选择并执行
4. VSCode 会重新加载，扩展会重新激活

## 步骤 3: 查看控制台日志

在开发者工具窗口中：

1. 点击 "Console" 标签页
2. 你应该能看到以下日志（如果扩展正常激活）：

```
[FCSTM Extension] Starting activation...
[FCSTM Extension] Extension path: /home/.../.vscode/extensions/hansbug.fcstm-language-support-0.1.0
[FCSTM Extension] Parser instance created
[FCSTM Parser] Starting to load parser modules...
[FCSTM Parser] Parser directory: /home/.../parser
[FCSTM Parser] Lexer path: /home/.../parser/GrammarLexer.js
[FCSTM Parser] Parser path: /home/.../parser/GrammarParser.js
[FCSTM Parser] Lexer exists: true
[FCSTM Parser] Parser exists: true
[FCSTM Parser] Lexer URL: file:///home/.../parser/GrammarLexer.js
[FCSTM Parser] Parser URL: file:///home/.../parser/GrammarParser.js
[FCSTM Parser] Starting dynamic import...
[FCSTM Parser] Lexer module loaded: true
[FCSTM Parser] Lexer default: true
[FCSTM Parser] Parser module loaded: true
[FCSTM Parser] Parser default: true
[FCSTM Parser] Parser modules loaded successfully!
[FCSTM Extension] Registering diagnostics provider...
[FCSTM Diagnostics] Registering diagnostics provider...
[FCSTM Diagnostics] Diagnostic collection created
[FCSTM Diagnostics] Diagnostics provider registered successfully
[FCSTM Extension] Diagnostics provider registered
[FCSTM Extension] Registering document symbol provider...
[FCSTM Extension] Document symbol provider registered
[FCSTM Extension] Registering completion provider...
[FCSTM Extension] Completion provider registered
[FCSTM Extension] Registering hover provider...
[FCSTM Extension] Hover provider registered
[FCSTM Extension] FCSTM Language Support extension is now active
```

## 步骤 4: 打开测试文件

打开文件：`/home/hansbug/oo-projects/pyfcstm/editors/vscode/test-extension.fcstm`

在控制台中你应该看到：

```
[FCSTM Diagnostics] Document opened: file:///home/.../test-extension.fcstm
[FCSTM Diagnostics] Updating diagnostics for: file:///home/.../test-extension.fcstm
[FCSTM Diagnostics] Document text length: 520
[FCSTM Diagnostics] Calling parser.parse()...
[FCSTM Diagnostics] Parse result: { success: false, errorCount: 1 }
[FCSTM Diagnostics] Setting 1 diagnostics
```

## 步骤 5: 复制所有日志

1. 在控制台中，右键点击任意日志
2. 选择 "Save as..." 或者全选复制
3. 将所有日志内容发送给我

## 需要特别注意的错误信息

如果你看到以下任何错误，请完整复制给我：

### 1. Parser 加载失败

```
[FCSTM Parser] Failed to load parser modules: ...
[FCSTM Parser] Error stack: ...
```

### 2. 文件不存在

```
[FCSTM Parser] Lexer exists: false
[FCSTM Parser] Parser exists: false
[FCSTM Parser] Parser files not found!
```

### 3. 动态 import 失败

```
[FCSTM Parser] Starting dynamic import...
[FCSTM Parser] Failed to load parser modules: ...
```

### 4. Diagnostics 更新失败

```
[FCSTM Diagnostics] Error updating diagnostics: ...
[FCSTM Diagnostics] Error stack: ...
```

## 其他调试方法

### 方法 2: 查看扩展主机日志

1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Developer: Show Logs"
3. 选择 "Extension Host"
4. 查看日志输出

### 方法 3: 查看输出面板

1. 按 `Ctrl+Shift+U` 打开输出面板
2. 在右上角下拉菜单选择 "Extension Host"
3. 查看日志输出

### 方法 4: 测试 Parser 命令

1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "FCSTM: Test Parser"
3. 执行命令
4. 查看控制台日志：

```
[FCSTM Extension] Test parser command invoked
[FCSTM Extension] Parser available: true
```

如果显示 `Parser available: false`，说明 parser 没有加载成功。

## 我需要的信息

请提供以下信息：

1. **完整的控制台日志**（从重新加载窗口开始到打开 .fcstm 文件）
2. **是否看到任何红色错误信息**
3. **Parser available 是 true 还是 false**（运行 "FCSTM: Test Parser" 命令）
4. **VSCode 版本**（Help → About）
5. **操作系统版本**

## 快速测试脚本

你也可以在终端运行这个脚本来测试 parser 是否能在 Node.js 环境中工作：

```bash
cd /home/hansbug/oo-projects/pyfcstm/editors/vscode

node -e "
(async () => {
    console.log('Testing parser...');
    const parser = require('./out/parser.js');
    const p = parser.getParser();

    // Wait for async loading
    await new Promise(resolve => setTimeout(resolve, 500));

    console.log('Parser available:', p.isAvailable());

    if (p.isAvailable()) {
        const result = await p.parse('state Root;');
        console.log('Parse valid code - success:', result.success);

        const result2 = await p.parse('state Root');
        console.log('Parse invalid code - success:', result2.success);
        console.log('Parse invalid code - errors:', result2.errors.length);
        if (result2.errors.length > 0) {
            console.log('Error message:', result2.errors[0].message);
        }
    } else {
        console.log('Parser is not available!');
    }
})();
"
```

这个脚本应该输出：

```
Testing parser...
Parser available: true
Parse valid code - success: true
Parse invalid code - success: false
Parse invalid code - errors: 1
Error message: Invalid syntax - check for missing semicolons, braces, or operators
```

如果输出不同，请把完整输出发给我。

## 常见问题解决方案

### 问题: Cannot find module 'antlr4'

**症状**: 在开发者控制台中看到错误:
```
Activating extension 'hansbug.fcstm-language-support' failed: Cannot find module 'antlr4'
```

**原因**: VSCode 扩展打包时默认排除了 `node_modules` 目录,导致运行时依赖 `antlr4` 无法加载。

**解决方案**: 已在 `.vscodeignore` 文件中添加了例外规则:
```
# CRITICAL: Include antlr4 runtime dependency
# VSCode extensions need runtime dependencies bundled
!node_modules/antlr4/**
```

**验证修复**:
1. 重新打包扩展: `npm run package`
2. 检查打包内容: `unzip -l build/fcstm-language-support-0.1.0.vsix | grep antlr4`
3. 应该看到 `extension/node_modules/antlr4/` 目录及其文件
4. 重新安装扩展: `code --install-extension build/fcstm-language-support-0.1.0.vsix --force`
5. 重新加载 VSCode 窗口并检查控制台日志

**技术说明**:
- VSCode 扩展使用 `.vscodeignore` 文件控制打包内容
- 默认情况下 `node_modules/**` 会排除所有依赖
- 使用 `!node_modules/antlr4/**` 可以强制包含特定依赖
- 这是临时解决方案,更好的做法是使用 webpack/esbuild 打包所有依赖到单个文件

