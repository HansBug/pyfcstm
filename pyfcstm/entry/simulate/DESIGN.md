# State Machine 交互式仿真器设计与实现方案

## 1. 整体架构

### 1.1 核心组件

- **CLI 入口**：`pyfcstm/entry/simulate/__init__.py` - 注册 simulate 子命令
- **交互式 REPL**：`pyfcstm/entry/simulate/repl.py` - 实现交互式命令行界面
- **命令处理器**：`pyfcstm/entry/simulate/commands.py` - 处理各种交互命令
- **状态显示器**：`pyfcstm/entry/simulate/display.py` - 格式化输出状态信息
- **自动补全器**：`pyfcstm/entry/simulate/completer.py` - 自动补全逻辑
- **批处理模式**：`pyfcstm/entry/simulate/batch.py` - 非交互式批处理

### 1.2 技术选型

使用 `prompt_toolkit` 实现交互式功能：

- ✅ 跨平台支持（Windows/Linux/macOS）
- ✅ 强大的自动补全和语法高亮
- ✅ 历史记录管理
- ✅ 多行编辑支持
- ✅ 自定义键绑定
- ✅ 丰富的样式系统

**依赖**：

```
prompt_toolkit>=3.0.0
```

## 2. 命令设计

### 2.1 命令列表

| 命令         | 参数                          | 功能                      | 示例                                    |
|------------|-----------------------------|--------------------------|-----------------------------------------|
| `/cycle`   | `[count] [event1 event2 ...]` | 执行指定次数的周期，可选事件列表 | `/cycle`, `/cycle 5`, `/cycle 3 Start` |
| `/clear`   | 无                           | 重置状态机到初始状态          | `/clear`                                |
| `/current` | 无                           | 显示当前状态路径和所有变量值    | `/current`                              |
| `/events`  | 无                           | 列出当前状态可触发的事件       | `/events`                               |
| `/log`     | `[level]`                   | 设置或显示日志级别           | `/log debug`, `/log`                    |
| `/history` | `[n]`                       | 显示最近 n 条历史（默认 10）  | `/history`, `/history 20`               |
| `/help`    | 无                           | 显示帮助信息               | `/help`                                 |
| `/quit`    | 无                           | 退出模拟器                 | `/quit`                                 |
| `/exit`    | 无                           | 退出模拟器（同 /quit）      | `/exit`                                 |

**注意**：`/cycle` 命令的 `count` 参数为可选整数，默认值为 1。如果提供，必须是正整数。

### 2.2 自动补全规则

- 输入 `/` 后：显示所有命令列表
- 输入 `/cy` 后：补全为 `/cycle`
- 输入 `/cycle ` 后：显示当前状态可用事件列表（全路径和简短版本）
- 输入 `/log ` 后：显示可用日志级别
- Tab 键触发补全，右箭头键接受建议

### 2.3 事件名称支持

基于 `SimulationRuntime._parse_event` 的双重机制：

- **全路径事件**：`System.Running.Active.Start`
- **简短事件**：`Start`（自动解析为当前上下文中的匹配事件）
- 自动补全时同时显示两种格式

## 3. 文件结构

```
pyfcstm/
├── entry/
│   ├── cli.py                    # 修改：添加 simulate 装饰器
│   └── simulate/
│       ├── __init__.py           # 新增：CLI 入口和子命令注册
│       ├── repl.py               # 新增：交互式 REPL 主逻辑
│       ├── batch.py              # 新增：批处理模式
│       ├── commands.py           # 新增：命令处理器
│       ├── display.py            # 新增：状态显示格式化
│       ├── completer.py          # 新增：自动补全逻辑
│       └── TODO.md               # 本文档
└── simulate/
    ├── __init__.py               # 已存在
    └── runtime.py                # 已存在：核心仿真逻辑
```

## 4. 核心实现细节

### 4.1 REPL 主循环（repl.py）

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
import os
from pathlib import Path


class SimulationREPL:
    def __init__(self, runtime: SimulationRuntime):
        self.runtime = runtime
        self.history = self._get_history()
        self.session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            completer=SimulationCompleter(runtime),
            enable_history_search=True,
            style=self._get_style(),
        )
        self.command_processor = CommandProcessor(runtime)

    def _get_history(self):
        """获取跨平台的历史记录文件路径"""
        if os.name == 'nt':  # Windows
            history_dir = Path(os.environ.get('APPDATA', '~')) / 'pyfcstm'
        else:  # Unix-like
            history_dir = Path.home() / '.config' / 'pyfcstm'

        history_dir.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(history_dir / 'simulate_history'))

    def _get_style(self):
        """百搭配色方案，兼容亮色和暗色终端"""
        return Style.from_dict({
            'command': '#0066cc bold',  # 蓝色命令
            'argument': '#666666',  # 灰色参数
            'success': '#00aa00',  # 绿色成功
            'error': '#cc0000',  # 红色错误
            'warning': '#ff8800',  # 橙色警告
            'info': '#0088cc',  # 青色信息
        })

    def run(self):
        """主循环"""
        while True:
            try:
                user_input = self.session.prompt('simulate> ')
                if not user_input.strip():
                    continue

                result = self.command_processor.process(user_input)
                if result.should_exit:
                    break

                if result.output:
                    print(result.output)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
```

### 4.2 自动补全器（completer.py）

```python
from prompt_toolkit.completion import Completer, Completion


class SimulationCompleter(Completer):
    COMMANDS = [
        '/cycle', '/clear', '/current', '/events',
        '/log', '/history', '/help', '/quit', '/exit'
    ]

    LOG_LEVELS = ['debug', 'info', 'warning', 'error', 'off']

    def __init__(self, runtime):
        self.runtime = runtime

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # 命令补全
        if text.startswith('/') and ' ' not in text:
            for cmd in self.COMMANDS:
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=self._get_command_help(cmd)
                    )

        # /cycle 后的事件补全
        elif text.startswith('/cycle '):
            event_prefix = text.split()[-1]
            events = self._get_current_events()
            for event in events:
                if event.startswith(event_prefix):
                    yield Completion(event, start_position=-len(event_prefix))

        # /log 后的级别补全
        elif text.startswith('/log '):
            level_prefix = text.split()[-1]
            for level in self.LOG_LEVELS:
                if level.startswith(level_prefix):
                    yield Completion(level, start_position=-len(level_prefix))

    def _get_current_events(self):
        """获取当前状态可触发的事件（全路径和简短版本）"""
        if not self.runtime.current_state:
            return []

        events = set()
        current_state = self.runtime.model.get_state_by_path(self.runtime.current_state)

        if current_state and hasattr(current_state, 'transitions'):
            for transition in current_state.transitions:
                if hasattr(transition, 'events'):
                    for event in transition.events:
                        # 添加全路径版本
                        events.add(event)
                        # 添加简短版本（如果不同）
                        short_name = event.split('.')[-1]
                        if short_name != event:
                            events.add(short_name)

        return sorted(events)

    def _get_command_help(self, cmd):
        """获取命令帮助信息"""
        help_map = {
            '/cycle': 'Execute one cycle',
            '/clear': 'Reset to initial state',
            '/current': 'Show current state and variables',
            '/events': 'List available events',
            '/log': 'Set log level',
            '/history': 'Show command history',
            '/help': 'Show help',
            '/quit': 'Exit simulator',
            '/exit': 'Exit simulator',
        }
        return help_map.get(cmd, '')
```

### 4.3 命令处理器（commands.py）

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    OFF = "off"


@dataclass
class CommandResult:
    output: str
    should_exit: bool = False


class CommandProcessor:
    def __init__(self, runtime):
        self.runtime = runtime
        self.display = StateDisplay()
        self.log_level = LogLevel.INFO

    def process(self, user_input: str) -> CommandResult:
        parts = user_input.strip().split()
        if not parts:
            return CommandResult("")

        command = parts[0]
        args = parts[1:]

        try:
            if command == '/cycle':
                return self._handle_cycle(args)
            elif command == '/clear':
                return self._handle_clear()
            elif command == '/current':
                return self._handle_current()
            elif command == '/events':
                return self._handle_events()
            elif command == '/log':
                return self._handle_log(args)
            elif command == '/history':
                return self._handle_history(args)
            elif command == '/help':
                return self._handle_help()
            elif command in ['/quit', '/exit']:
                return CommandResult("Goodbye!", should_exit=True)
            else:
                return CommandResult(f"Unknown command: {command}. Type /help for available commands.")
        except Exception as e:
            return CommandResult(f"Error: {e}")

    def _handle_cycle(self, events: List[str]) -> CommandResult:
        """Handle /cycle command"""
        try:
            if self.log_level == LogLevel.DEBUG:
                self.display.log("Executing cycle with events:", events if events else "none")

            self.runtime.cycle(events if events else None)
            return CommandResult(self.display.format_current_state(self.runtime))
        except Exception as e:
            return CommandResult(f"Cycle execution failed: {e}")

    def _handle_clear(self) -> CommandResult:
        """Handle /clear command"""
        self.runtime.clear()
        if self.log_level in [LogLevel.DEBUG, LogLevel.INFO]:
            self.display.log("State machine reset to initial state")
        return CommandResult(self.display.format_current_state(self.runtime))

    def _handle_current(self) -> CommandResult:
        """Handle /current command"""
        return CommandResult(self.display.format_current_state(self.runtime))

    def _handle_events(self) -> CommandResult:
        """处理 /events 命令"""
        events = self._get_current_events()
        return CommandResult(self.display.format_events(events))

    def _handle_log(self, args: List[str]) -> CommandResult:
        """Handle /log command"""
        if not args:
            return CommandResult(f"Current log level: {self.log_level.value}")

        level_str = args[0].lower()
        try:
            self.log_level = LogLevel(level_str)
            return CommandResult(f"Log level set to: {level_str}")
        except ValueError:
            valid_levels = [level.value for level in LogLevel]
            return CommandResult(f"Invalid log level. Available levels: {', '.join(valid_levels)}")

    def _get_current_events(self):
        """获取当前状态的可用事件"""
        if not self.runtime.current_state:
            return []

        events = []
        current_state = self.runtime.model.get_state_by_path(self.runtime.current_state)

        if current_state and hasattr(current_state, 'transitions'):
            for transition in current_state.transitions:
                if hasattr(transition, 'events'):
                    for event in transition.events:
                        # 添加全路径和简短版本
                        full_path = event
                        short_name = event.split('.')[-1]

                        if short_name != full_path:
                            events.append((full_path, short_name))
                        else:
                            events.append((full_path, None))

        return events
```

### 4.4 状态显示器（display.py）

```python
import sys
from typing import List, Tuple, Optional


class StateDisplay:
    # ANSI 颜色码 - 百搭配色
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'blue': '\033[94m',  # 蓝色 - 标题
        'green': '\033[92m',  # 绿色 - 成功/正常状态
        'yellow': '\033[93m',  # 黄色 - 警告/变量名
        'red': '\033[91m',  # 红色 - 错误
        'cyan': '\033[96m',  # 青色 - 信息
        'gray': '\033[90m',  # 灰色 - 次要信息
    }

    def __init__(self):
        # 检测是否支持颜色
        self.use_color = self._supports_color()

    def _supports_color(self):
        """检测终端是否支持颜色"""
        return (
                hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                'TERM' in os.environ and os.environ['TERM'] != 'dumb'
        )

    def _colorize(self, text: str, color: str) -> str:
        """给文本添加颜色"""
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def format_current_state(self, runtime) -> str:
        """Format current state and variable information"""
        lines = []

        # Current state
        state_text = runtime.current_state or "(terminated)"
        state_label = self._colorize("Current State:", 'blue')
        state_value = self._colorize(state_text, 'green' if runtime.current_state else 'red')
        lines.append(f"{state_label} {state_value}")

        # Variables
        if runtime.vars:
            var_label = self._colorize("Variables:", 'blue')
            lines.append(var_label)
            for name, value in sorted(runtime.vars.items()):
                name_colored = self._colorize(name, 'yellow')
                value_colored = self._colorize(str(value), 'cyan')
                lines.append(f"  {name_colored} = {value_colored}")

        return "\n".join(lines)

    def format_events(self, events: List[Tuple[str, Optional[str]]]) -> str:
        """Format event list"""
        if not events:
            return self._colorize("No events available in current state", 'gray')

        lines = []
        lines.append(self._colorize("Available Events:", 'blue'))

        for full_path, short_name in events:
            if short_name:
                full_colored = self._colorize(full_path, 'cyan')
                short_colored = self._colorize(short_name, 'green')
                lines.append(f"  • {short_colored} ({full_colored})")
            else:
                event_colored = self._colorize(full_path, 'green')
                lines.append(f"  • {event_colored}")

        return "\n".join(lines)

    def log(self, message: str, level: str = "info"):
        """输出日志信息"""
        color_map = {
            'debug': 'gray',
            'info': 'cyan',
            'warning': 'yellow',
            'error': 'red',
        }
        color = color_map.get(level, 'reset')
        prefix = f"[{level.upper()}]" if level != 'info' else ""
        print(f"{self._colorize(prefix, color)} {message}")
```

### 4.5 批处理模式（batch.py）

```python
from typing import List
from .commands import CommandProcessor


class BatchProcessor:
    def __init__(self, runtime):
        self.runtime = runtime
        self.command_processor = CommandProcessor(runtime)

    def execute_commands(self, command_string: str) -> str:
        """执行批处理命令字符串"""
        commands = [cmd.strip() for cmd in command_string.split(';') if cmd.strip()]
        results = []

        for command in commands:
            if not command.startswith('/'):
                command = '/' + command  # 自动添加 / 前缀

            result = self.command_processor.process(command)
            if result.output:
                results.append(result.output)

            if result.should_exit:
                break

        return '\n\n'.join(results)
```

### 4.6 CLI 入口（__init__.py）

```python
import click
from pathlib import Path
from ..base import CONTEXT_SETTINGS
from ...dsl import parse_with_grammar_entry
from ...model import parse_dsl_node_to_state_machine
from ...simulate import SimulationRuntime
from ...utils import auto_decode
from .repl import SimulationREPL
from .batch import BatchProcessor


def _add_simulate_subcommand(cli: click.Group) -> click.Group:
    @cli.command(
        'simulate',
        help='交互式状态机仿真器',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i', '--input-code', 'input_code_file',
        type=str, required=True,
        help='状态机 DSL 代码文件路径',
    )
    @click.option(
        '-e', '--execute', 'batch_commands',
        type=str, default=None,
        help='批处理命令（用分号分隔），例如: "cycle Start; current; cycle Stop"',
    )
    @click.option(
        '--no-color', is_flag=True,
        help='禁用颜色输出',
    )
    def simulate(input_code_file: str, batch_commands: str, no_color: bool) -> None:
        # 解析 DSL
        try:
            code = auto_decode(Path(input_code_file).read_bytes())
            ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
            model = parse_dsl_node_to_state_machine(ast_node)
        except Exception as e:
            click.echo(f"Failed to parse DSL file: {e}", err=True)
            return

        # Create runtime
        runtime = SimulationRuntime(model)

        # Batch mode
        if batch_commands:
            processor = BatchProcessor(runtime)
            if no_color:
                # Disable color output logic
                pass
            result = processor.execute_commands(batch_commands)
            click.echo(result)
            return

        # Interactive mode
        repl = SimulationREPL(runtime)
        click.echo("╔" + "═" * 58 + "╗")
        click.echo("║  State Machine Interactive Simulator" + " " * 21 + "║")
        click.echo("╟" + "─" * 58 + "╢")
        click.echo("║  Type /help to see available commands" + " " * 19 + "║")
        click.echo("╚" + "═" * 58 + "╝")
        click.echo()
        repl.run()

    return cli
```

## 5. 增强特性

### 5.1 跨平台历史记录

- Windows: `%APPDATA%/pyfcstm/simulate_history`
- Unix-like: `~/.config/pyfcstm/simulate_history`
- 自动创建目录结构

### 5.2 百搭配色方案

使用 ANSI 颜色码，兼容亮色和暗色终端：

- 蓝色：标题和分隔线
- 绿色：正常状态和简短事件名
- 黄色：变量名
- 青色：变量值和全路径事件名
- 灰色：次要信息
- 红色：错误和终止状态

### 5.3 日志级别控制

- `debug`: 显示详细执行信息
- `info`: 显示一般信息（默认）
- `warning`: 只显示警告和错误
- `error`: 只显示错误
- `off`: 关闭日志输出

### 5.4 错误处理

- 捕获 `SimulationRuntimeDfsError` 并友好显示
- 捕获解析错误并提示正确格式
- Ctrl+C 不退出，只取消当前输入
- 输入验证和参数检查

## 6. 使用示例

### 6.1 交互模式

```bash
$ pyfcstm simulate -i example.fcstm

╔══════════════════════════════════════════════════════════╗
║  State Machine Interactive Simulator                     ║
╟──────────────────────────────────────────────────────────╢
║  Type /help to see available commands                    ║
╚══════════════════════════════════════════════════════════╝

simulate> /help
Available commands:
  /cycle [events...]  - Execute one cycle with optional events
  /clear              - Reset to initial state
  /current            - Show current state and all variables
  /events             - List available events in current state
  /log [level]        - Set or display log level
  /history [n]        - Show command history
  /help               - Show this help message
  /quit, /exit        - Exit simulator

simulate> /current
Current State: System.Idle
Variables:
  counter = 0
  temperature = 25.0

simulate> /events
Available Events:
  • Start (System.Events.Start)
  • Reset (System.Events.Reset)

simulate> /cycle Start
Current State: System.Running.Active
Variables:
  counter = 1
  temperature = 25.1

simulate> /log debug
Log level set to: debug

simulate> /cycle
[DEBUG] Executing cycle with events: none
Current State: System.Running.Processing
Variables:
  counter = 2
  temperature = 25.2

simulate> /quit
Goodbye!
```

### 6.2 批处理模式

```bash
$ pyfcstm simulate -i example.fcstm -e "current; cycle Start; current; events"

Current State: System.Idle
Variables:
  counter = 0
  temperature = 25.0

Current State: System.Running.Active
Variables:
  counter = 1
  temperature = 25.1

Available Events:
  • Stop (System.Events.Stop)
  • Pause (System.Events.Pause)
```

## 7. 实现 TODO 清单

### 阶段 P0：基础与核心运行时（MVP）✅

**P0.1：基础 CLI 入口与命令基础设施** ✅
- [x] 创建 `pyfcstm/entry/simulate/__init__.py` 并实现 CLI 入口点
- [x] 在 `pyfcstm/entry/cli.py` 中注册 `simulate` 子命令
- [x] 实现基本参数解析（`-i/--input-code`、`-e/--execute`、`--no-color`）
- [x] 添加 DSL 文件加载和解析逻辑
- [x] 从解析后的模型初始化 `SimulationRuntime`
- [x] 添加文件 I/O 和解析错误的基本错误处理

**P0.2：核心命令处理器** ✅
- [x] 创建 `pyfcstm/entry/simulate/commands.py`
- [x] 实现 `CommandResult` 数据类
- [x] 实现 `CommandProcessor` 类及命令路由
- [x] 实现 `/cycle [events...]` 命令处理器
- [x] 实现 `/clear` 命令处理器
- [x] 实现 `/current` 命令处理器
- [x] 实现 `/events` 命令处理器
- [x] 实现 `/quit` 和 `/exit` 命令处理器
- [x] 添加命令执行的基本异常处理

**P0.3：基础显示与输出** ✅
- [x] 创建 `pyfcstm/entry/simulate/display.py`
- [x] 实现 `StateDisplay` 类及颜色支持检测
- [x] 实现 `format_current_state()`（简洁格式，无制表符）
- [x] 实现 `format_events()`（简洁格式，无制表符）
- [x] 添加 ANSI 颜色支持（蓝、绿、黄、青、灰、红）
- [x] 实现 `--no-color` 标志处理
- [x] 在亮色和暗色终端主题下测试输出

**P0.4：简单 REPL 循环** ✅
- [x] 创建 `pyfcstm/entry/simulate/repl.py`（不使用 prompt_toolkit 的基础版本）
- [x] 使用 `input()` 函数实现基本输入循环
- [x] 集成 `CommandProcessor` 进行命令执行
- [x] 添加 Ctrl+C 处理（继续，不退出）
- [x] 添加 EOF 处理（优雅退出）
- [x] 显示带制表符的欢迎横幅
- [x] 测试基本交互工作流

**P0.5：批处理模式** ✅
- [x] 创建 `pyfcstm/entry/simulate/batch.py`
- [x] 实现 `BatchProcessor` 类
- [x] 添加命令字符串解析（分号分隔）
- [x] 为命令自动添加 `/` 前缀
- [x] 与 `CommandProcessor` 集成
- [x] 使用 `-e` 标志测试批处理命令执行

**P0.6：单元测试** ✅
- [x] 为 `CommandProcessor` 编写单元测试
- [x] 为 `StateDisplay` 编写单元测试
- [x] 为 `BatchProcessor` 编写单元测试
- [x] 编写集成测试
- [x] 所有测试通过（34/34 tests passing）

**P0.7：增强 /cycle 命令（新增功能）** ✅
- [x] 扩展 `/cycle` 命令支持重复次数参数：`/cycle [count] [events...]`
- [x] `count` 为可选整数参数，默认值为 1
- [x] 示例：`/cycle 5` - 执行 5 次周期（无事件）
- [x] 示例：`/cycle 3 Start` - 执行 3 次周期，每次触发 Start 事件
- [x] 示例：`/cycle 10 Start Stop` - 执行 10 次周期，每次触发 Start 和 Stop 事件
- [x] 在每次周期后显示当前状态（大于 5 次时仅显示首尾状态）
- [x] 添加参数验证（count 必须为正整数）
- [x] 更新 `/help` 命令文档
- [x] 添加单元测试覆盖新功能（6 个新测试，全部通过）

### 阶段 P1：增强交互性 ✅

**P1.1：prompt_toolkit 集成** ✅
- [x] 将 `prompt_toolkit>=3.0.0` 添加到 `requirements.txt`
- [x] 升级 `repl.py` 以使用 `PromptSession`
- [x] 配置提示符样式和颜色
- [x] 添加历史搜索支持（`enable_history_search=True`）
- [x] 跨平台支持（Windows、Linux 和 macOS）

**P1.2：命令自动补全** ✅
- [x] 创建 `pyfcstm/entry/simulate/completer.py`
- [x] 实现 `SimulationCompleter` 类
- [x] 添加命令名称补全（在 `/` 之后）
- [x] 添加事件名称补全（在 `/cycle ` 之后）
- [x] 添加日志级别补全（在 `/log ` 之后）
- [x] 添加补全元数据（帮助文本显示）
- [x] 支持全路径和简短事件名称
- [x] Tab 键触发补全，右箭头键接受建议

**P1.3：命令历史持久化** ✅
- [x] 实现跨平台历史文件路径检测
  - [x] Windows：`%APPDATA%/pyfcstm/simulate_history`
  - [x] Unix-like：`~/.config/pyfcstm/simulate_history`
- [x] 添加自动目录创建
- [x] 将 `FileHistory` 与 `PromptSession` 集成
- [x] 使用 Ctrl+R 添加历史搜索
- [x] 跨会话历史持久化

**P1.4：基于历史的自动建议** ✅
- [x] 在 `PromptSession` 中启用 `AutoSuggestFromHistory`
- [x] 配置建议显示样式（灰色文本）
- [x] 右箭头键接受建议
- [x] 支持空历史时的正常行为

### 阶段 P2：高级功能

**P2.1：日志级别控制**
- [ ] 实现 `LogLevel` 枚举（debug、info、warning、error、off）
- [ ] 将日志级别状态添加到 `CommandProcessor`
- [ ] 实现 `/log [level]` 命令处理器
- [ ] 根据当前级别添加条件日志记录
- [ ] 实现 `StateDisplay.log()` 方法及基于级别的着色
- [ ] 添加日志前缀格式化（`[DEBUG]`、`[INFO]` 等）
- [ ] 在不同级别测试日志过滤

**P2.2：命令历史显示**
- [ ] 实现 `/history [n]` 命令处理器
- [ ] 从 `FileHistory` 添加历史检索
- [ ] 使用行号格式化历史输出
- [ ] 支持可选计数参数（默认：10）
- [ ] 为历史显示添加颜色编码
- [ ] 使用各种历史大小进行测试

**P2.3：增强帮助系统**
- [ ] 实现 `/help` 命令处理器
- [ ] 创建带制表符的格式化帮助文本
- [ ] 添加命令描述和使用示例
- [ ] 包含事件名称格式说明（全路径 vs 简短）
- [ ] 添加键盘快捷键文档
- [ ] 格式化帮助输出以提高可读性

**P2.4：错误处理与用户体验**
- [ ] 捕获 `SimulationRuntimeDfsError` 并显示友好消息
- [ ] 为所有命令添加输入验证
- [ ] 改进错误消息并提供建议
- [ ] 为边缘情况添加警告消息
- [ ] 实现缺失功能的优雅降级
- [ ] 全面测试错误场景

### 阶段 P3：完善与文档

**P3.1：测试**
- [ ] 为 `CommandProcessor` 编写单元测试
- [ ] 为 `SimulationCompleter` 编写单元测试
- [ ] 为 `StateDisplay` 格式化编写单元测试
- [ ] 为 `BatchProcessor` 编写单元测试
- [ ] 为完整 REPL 工作流编写集成测试
- [ ] 测试跨平台兼容性（Windows、Linux、macOS）
- [ ] 使用各种 DSL 文件测试（简单、复杂、边缘情况）
- [ ] 测试终端兼容性（不同模拟器、配色方案）

**P3.2：文档**
- [ ] 为所有类和方法添加文档字符串（reST 格式）
- [ ] 使用 `simulate` 命令示例更新主 README
- [ ] 为交互模式创建教程文档
- [ ] 为批处理模式创建教程文档
- [ ] 添加常见问题的故障排除部分
- [ ] 记录键盘快捷键和导航
- [ ] 添加交互会话的截图/GIF

**P3.3：性能与优化**
- [ ] 分析自动补全性能
- [ ] 优化大型状态机的事件列表检索
- [ ] 为频繁访问的数据添加缓存
- [ ] 使用大型 DSL 文件测试（100+ 状态）
- [ ] 优化大型变量集的显示格式化

**P3.4：最终完善**
- [ ] 审查并优化配色方案以提高可访问性
- [ ] 添加自定义颜色主题支持（可选）
- [ ] 改进制表符对齐
- [ ] 在欢迎横幅中添加版本信息
- [ ] 实现终端调整大小的优雅处理
- [ ] 最终代码审查和清理
- [ ] 使用新功能更新 CHANGELOG

### 阶段 P4：未来增强（可选）

**P4.1：高级调试**
- [ ] 添加 `/step` 命令进行单步执行
- [ ] 添加 `/breakpoint` 命令进行条件断点
- [ ] 添加 `/watch` 命令进行变量监控
- [ ] 实现执行跟踪日志记录
- [ ] 添加状态转换可视化

**P4.2：脚本与自动化**
- [ ] 支持从文件加载命令脚本
- [ ] 在批处理模式下添加条件执行
- [ ] 实现用于测试的循环结构
- [ ] 添加用于验证的变量断言
- [ ] 创建测试场景框架

**P4.3：导出与报告**
- [ ] 添加 `/export` 命令进行状态/变量转储
- [ ] 支持 JSON/YAML 输出格式
- [ ] 生成执行报告
- [ ] 添加时间线可视化
- [ ] 创建状态/转换的覆盖率分析

**P4.4：集成与可扩展性**
- [ ] 为自定义命令添加插件系统
- [ ] 支持外部事件源（文件、套接字）
- [ ] 添加用于远程控制的 REST API
- [ ] 实现状态机录制/回放
- [ ] 创建与测试框架的集成

## 8. 测试策略

### 8.1 单元测试

- 命令处理器各命令的功能测试
- 自动补全逻辑测试
- 状态显示格式化测试
- 批处理命令解析测试

### 8.2 集成测试

- 完整的交互流程测试
- 跨平台兼容性测试
- 各种 DSL 文件的兼容性测试

### 8.3 用户体验测试

- 在不同终端环境下的显示效果
- 颜色在亮色/暗色主题下的可读性
- 自动补全的准确性和响应速度
