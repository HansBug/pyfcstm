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
| `cycle`   | `[count] [event1 event2 ...]` | 执行指定次数的周期，可选事件列表 | `cycle`, `cycle 5`, `cycle 3 Start` |
| `clear`   | 无                           | 重置状态机到初始状态          | `clear`                                |
| `current` | 无                           | 显示当前状态路径和所有变量值    | `current`                              |
| `events`  | 无                           | 列出当前状态可触发的事件       | `events`                               |
| `history` | `[n\|all]`                  | 显示执行历史记录            | `history`, `history 20`, `history all` |
| `setting` | `[key] [value]`             | 查看或设置配置项            | `setting`, `setting table_max_rows 30` |
| `export`  | `<filename>`                | 导出历史到文件              | `export history.csv`, `export data.json` |
| `help`    | 无                           | 显示帮助信息               | `help`                                 |
| `quit`    | 无                           | 退出模拟器                 | `quit`                                 |
| `exit`    | 无                           | 退出模拟器（同 quit）      | `exit`                                 |

**注意**：`cycle` 命令的 `count` 参数为可选整数，默认值为 1。如果提供，必须是正整数。

### 2.2 自动补全规则

**命令补全**：
- 输入命令开头字母后：显示匹配的命令列表
- 输入 `cy` 后：补全为 `cycle`
- 输入 `se` 后：补全为 `setting`
- 输入 `hi` 后：补全为 `history`

**cycle 命令参数补全**：
- 输入 `cycle ` 后：显示常用计数值（1, 5, 10, 20, 50, 100）和当前状态可用事件列表
- 输入 `cycle 1` 后：显示以 1 开头的计数值（1, 10, 100）和事件
- 输入 `cycle 5 ` 后：显示可用事件列表（支持多个事件）

**history 命令参数补全**：
- 输入 `history ` 后：显示 `all` 关键字和常用计数值（5, 10, 20, 50, 100）
- 输入 `history a` 后：补全为 `all`

**setting 命令参数补全**：
- 输入 `setting ` 后：显示可用的设置项（table_max_rows, history_size, color, log_level）
- 输入 `setting log_level ` 后：显示日志级别（debug, info, warning, error, off）
- 输入 `setting color ` 后：显示布尔值（on, off, true, false）
- 输入 `setting table_max_rows ` 后：显示常用数值（10, 20, 50, 100, 200, 500, 1000）
- 输入 `setting history_size ` 后：显示常用数值（10, 20, 50, 100, 200, 500, 1000）

**export 命令参数补全**：
- 输入 `export ` 后：显示建议的文件名（history.csv, history.json, history.yaml, history.jsonl）
- 每个建议都带有格式类型提示（CSV format, JSON format等）

**事件补全**：
- 显示当前状态可用事件列表（全路径和简短版本）
- 支持部分匹配（输入 `S` 显示以 S 开头的事件）

**操作方式**：
- Tab 键触发补全，右箭头键接受建议
- 所有补全项都带有帮助文本（display_meta）

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
        'cycle', 'clear', 'current', 'events',
        'history', 'setting', 'help', 'quit', 'exit'
    ]

    LOG_LEVELS = ['debug', 'info', 'warning', 'error', 'off']

    def __init__(self, runtime):
        self.runtime = runtime

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        # 命令补全 - 输入命令开头字母时
        if not words or (len(words) == 1 and ' ' not in text):
            prefix = text.strip()
            for cmd in self.COMMANDS:
                if cmd.startswith(prefix):
                    yield Completion(
                        cmd,
                        start_position=-len(prefix),
                        display_meta=self._get_command_help(cmd)
                    )
            return

        command = words[0]

        # cycle 命令 - 补全计数值和事件
        if command == 'cycle':
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                prefix = words[1] if len(words) == 2 else ''

                # 建议常用计数值
                for count in ['1', '5', '10', '20', '50', '100']:
                    if count.startswith(prefix):
                        yield Completion(count, start_position=-len(prefix),
                                       display_meta='cycle count')

                # 建议事件
                events = self._get_current_events()
                for event in events:
                    if event.startswith(prefix):
                        yield Completion(event, start_position=-len(prefix),
                                       display_meta='event name')
            else:
                # 计数后继续补全事件
                prefix = words[-1] if not text.endswith(' ') else ''
                events = self._get_current_events()
                for event in events:
                    if event.startswith(prefix):
                        yield Completion(event, start_position=-len(prefix),
                                       display_meta='event name')

        # history 命令 - 补全 'all' 和计数值
        elif command == 'history':
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                prefix = words[1] if len(words) == 2 else ''

                if 'all'.startswith(prefix):
                    yield Completion('all', start_position=-len(prefix),
                                   display_meta='show all history')

                for count in ['5', '10', '20', '50', '100']:
                    if count.startswith(prefix):
                        yield Completion(count, start_position=-len(prefix),
                                       display_meta='history count')

        # setting 命令 - 补全键和值
        elif command == 'setting':
            setting_keys = ['table_max_rows', 'history_size', 'color', 'log_level']

            # 第一个参数 - 设置键
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                prefix = words[1] if len(words) == 2 else ''
                for key in setting_keys:
                    if key.startswith(prefix):
                        yield Completion(key, start_position=-len(prefix),
                                       display_meta=self._get_setting_help(key))

            # 第二个参数 - 设置值
            elif len(words) >= 2:
                setting_key = words[1]
                prefix = words[2] if len(words) == 3 and not text.endswith(' ') else ''

                if setting_key == 'log_level':
                    for level in self.LOG_LEVELS:
                        if level.startswith(prefix):
                            yield Completion(level, start_position=-len(prefix),
                                           display_meta='log level')
                elif setting_key == 'color':
                    for value in ['on', 'off', 'true', 'false']:
                        if value.startswith(prefix):
                            yield Completion(value, start_position=-len(prefix),
                                           display_meta='color setting')
                elif setting_key in ['table_max_rows', 'history_size']:
                    for value in ['10', '20', '50', '100', '200', '500', '1000']:
                        if value.startswith(prefix):
                            yield Completion(value, start_position=-len(prefix),
                                           display_meta='numeric value')

    def _get_current_events(self):
        """获取当前状态可触发的事件（全路径和简短版本）"""
        if not self.runtime.current_state:
            return []

        events = set()
        current_state = self.runtime.current_state
        current_state_name = current_state.name

        if current_state.parent:
            parent = current_state.parent
            for transition in parent.transitions:
                if transition.from_state == current_state_name and transition.event:
                    # 添加全路径
                    event_path = '.'.join(transition.event.state_path) + '.' + transition.event.name
                    events.add(event_path)
                    # 添加简短名称
                    events.add(transition.event.name)

        return sorted(events)

    def _get_command_help(self, cmd):
        """获取命令帮助信息"""
        help_map = {
            'cycle': 'Execute cycle(s) with optional events',
            'clear': 'Reset to initial state',
            'current': 'Show current state and variables',
            'events': 'List available events',
            'history': 'Show execution history',
            'setting': 'View or change settings',
            'help': 'Show help',
            'quit': 'Exit simulator',
            'exit': 'Exit simulator',
        }
        return help_map.get(cmd, '')

    def _get_setting_help(self, key):
        """获取设置项帮助信息"""
        help_map = {
            'table_max_rows': 'max rows in tables (default: 20)',
            'history_size': 'max history entries (default: 100)',
            'color': 'enable/disable colors (on/off)',
            'log_level': 'logging level (debug/info/warning/error/off)',
        }
        return help_map.get(key, '')
```
            'help': 'Show help',
            'quit': 'Exit simulator',
            'exit': 'Exit simulator',
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
    def __init__(self, runtime, use_color: bool = True):
        self.runtime = runtime
        self.settings = Settings()
        self.settings.color = use_color
        self.display = StateDisplay(use_color=use_color, logger=runtime.logger)

    def process(self, user_input: str) -> CommandResult:
        parts = user_input.strip().split()
        if not parts:
            return CommandResult("")

        command = parts[0]
        args = parts[1:]

        try:
            if command == 'cycle':
                return self._handle_cycle(args)
            elif command == 'clear':
                return self._handle_clear()
            elif command == 'current':
                return self._handle_current()
            elif command == 'events':
                return self._handle_events()
            elif command == 'history':
                return self._handle_history(args)
            elif command == 'setting':
                return self._handle_setting(args)
            elif command == 'help':
                return self._handle_help()
            elif command in ['quit', 'exit']:
                return CommandResult("Goodbye!", should_exit=True)
            else:
                return CommandResult(f"Unknown command: {command}. Type 'help' for available commands.")
        except Exception as e:
            return CommandResult(f"Error: {e}")

    def _handle_cycle(self, events: List[str]) -> CommandResult:
        """Handle cycle command with optional count parameter"""
        # Parse count parameter if present
        count = 1
        event_list = events

        if events and events[0].isdigit():
            count = int(events[0])
            event_list = events[1:]

        # Execute cycles and return formatted output
        # (implementation details omitted for brevity)

    def _handle_clear(self) -> CommandResult:
        """Handle clear command"""
        self.runtime.clear()
        self.display.log("State machine reset to initial state", "info")
        return CommandResult(self.display.format_current_state(self.runtime))

    def _handle_current(self) -> CommandResult:
        """Handle current command"""
        return CommandResult(self.display.format_current_state(self.runtime))

    def _handle_events(self) -> CommandResult:
        """Handle events command"""
        events = self._get_current_events()
        return CommandResult(self.display.format_events(events))

    def _handle_history(self, args: List[str]) -> CommandResult:
        """Handle history command"""
        # Show execution history in table format
        # (implementation details omitted for brevity)

    def _handle_setting(self, args: List[str]) -> CommandResult:
        """Handle setting command"""
        # View or change settings like log_level, table_max_rows, etc.
        # (implementation details omitted for brevity)

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


def create_cross_platform_output_func() -> Callable[[str], None]:
    """
    Create a cross-platform output function that handles Unicode correctly.

    On Windows, writes directly to binary stdout with UTF-8 encoding to avoid
    cp1252 encoding issues. On other platforms, uses standard print.
    """
    # (implementation details omitted for brevity)


class BatchProcessor:
    def __init__(self, runtime, use_color: bool = True, output_func: Callable[[str], None] = None):
        self.runtime = runtime
        self.command_processor = CommandProcessor(runtime, use_color=use_color)
        self.output_func = output_func or create_cross_platform_output_func()

    def execute_commands(self, command_string: str) -> None:
        """执行批处理命令字符串，立即输出结果以保持日志顺序"""
        commands = [cmd.strip() for cmd in command_string.split(';') if cmd.strip()]

        for i, command in enumerate(commands):
            # Add command header
            separator = "─" * 60
            command_header = f">>> {command}"
            self.output_func(f"{separator}\n{command_header}\n{separator}")

            result = self.command_processor.process(command)
            if result.output:
                self.output_func(result.output)

            # Add spacing between commands
            if i < len(commands) - 1:
                self.output_func("")

            if result.should_exit:
                break
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
        help='Interactive state machine simulator',
    )
    @click.option(
        '-i', '--input-code', 'input_code_file',
        type=str, required=True,
        help='State machine DSL code file path',
    )
    @click.option(
        '-e', '--execute', 'batch_commands',
        type=str, default=None,
        help='Batch commands (semicolon-separated), e.g.: "current; cycle Start; current"',
    )
    @click.option(
        '--no-color', is_flag=True,
        help='Disable color output',
    )
    def simulate(input_code_file: str, batch_commands: str, no_color: bool) -> None:
        # Parse DSL
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
            processor = BatchProcessor(runtime, use_color=not no_color)
            processor.execute_commands(batch_commands)
            return

        # Interactive mode
        repl = SimulationREPL(runtime, use_color=not no_color)

        # Print banner with Unicode box-drawing characters
        banner_lines = [
            "╔" + "═" * 58 + "╗",
            "║  State Machine Interactive Simulator" + " " * 21 + "║",
            "╟" + "─" * 58 + "╢",
            "║  Type 'help' to see available commands" + " " * 19 + "║",
            "╚" + "═" * 58 + "╝",
            ""
        ]

        # Use cross-platform output function for banner
        output_func = create_cross_platform_output_func()
        for line in banner_lines:
            output_func(line)

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
║  Type 'help' to see available commands                   ║
╚══════════════════════════════════════════════════════════╝

simulate> help
Available commands:
  cycle [count] [events...]  - Execute cycle(s) with optional events
                               count: number of cycles (default: 1)
                               Examples: cycle, cycle 5, cycle 3 Start
  clear                      - Reset to initial state
  current                    - Show current state and all variables
  events                     - List available events in current state
  history [n|all]            - Show execution history (default: 10 recent entries)
  setting [key] [value]      - View or change settings (including log_level)
  help                       - Show this help message
  quit, exit                 - Exit simulator

simulate> current
Cycle: 0
Current State: System.Idle
Variables:
  counter = 0
  temperature = 25.0

simulate> events
Available Events:
  • Start (System.Events.Start)
  • Reset (System.Events.Reset)

simulate> cycle Start
Cycle: 1
Current State: System.Running.Active
Variables:
  counter = 1
  temperature = 25.1

simulate> cycle

Cycle: 2
Current State: System.Running.Active
Variables:
  counter = 2
  temperature = 25.2

simulate> quit
Goodbye!

simulate> setting log_level debug
Setting 'log_level' set to: debug

simulate> cycle
[DEBUG] Executing cycle with events: none
Current State: System.Running.Processing
Variables:
  counter = 2
  temperature = 25.2

simulate> quit
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
- [x] 实现 `cycle [events...]` 命令处理器
- [x] 实现 `clear` 命令处理器
- [x] 实现 `current` 命令处理器
- [x] 实现 `events` 命令处理器
- [x] 实现 `quit` 和 `exit` 命令处理器
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
- [x] 实现即时输出（不缓冲）
- [x] 与 `CommandProcessor` 集成
- [x] 使用 `-e` 标志测试批处理命令执行

**P0.6：单元测试** ✅
- [x] 为 `CommandProcessor` 编写单元测试
- [x] 为 `StateDisplay` 编写单元测试
- [x] 为 `BatchProcessor` 编写单元测试
- [x] 编写集成测试
- [x] 所有测试通过（34/34 tests passing）

**P0.7：增强 cycle 命令（新增功能）** ✅
- [x] 扩展 `cycle` 命令支持重复次数参数：`cycle [count] [events...]`
- [x] `count` 为可选整数参数，默认值为 1
- [x] 示例：`cycle 5` - 执行 5 次周期（无事件）
- [x] 示例：`cycle 3 Start` - 执行 3 次周期，每次触发 Start 事件
- [x] 示例：`cycle 10 Start Stop` - 执行 10 次周期，每次触发 Start 和 Stop 事件
- [x] 在每次周期后显示当前状态（大于 5 次时仅显示首尾状态）
- [x] 添加参数验证（count 必须为正整数）
- [x] 更新 `help` 命令文档
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
- [x] 添加命令名称补全
- [x] 添加事件名称补全（在 `cycle ` 之后）
- [x] 添加设置键补全（在 `setting ` 之后）
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

**P1.5：增强输出格式化** ✅
- [x] 批处理模式（`-e`）输出优化
  - [x] 为每条命令添加清晰的分隔符
  - [x] 显示正在执行的命令
  - [x] 区分不同命令的输出内容
- [x] `cycle` 多次执行表格化输出
  - [x] 使用手写表格实现（不依赖tabulate）
  - [x] 所有列居中显示
  - [x] 表格列：cycle（序号）、state（状态）、各变量列
  - [x] count < 20：显示所有周期
  - [x] count >= 20：仅显示前 10 次和后 10 次
  - [x] 行分隔符仅在 header 和 rows 之间，rows 内部无分隔
  - [x] 从 `requirements.txt` 移除 `tabulate` 依赖
  - [x] Cycle 列从当前 runtime 已执行的 cycle 数开始计数（而非从 1 开始）
  - [x] 表格添加颜色支持：
    - [x] Cycle header: 蓝色
    - [x] Cycle values: Cyan
    - [x] State header: 蓝色
    - [x] State values: 绿色
    - [x] 变量 headers: 黄色
    - [x] 变量 values: Cyan
- [x] `current` 和单个 `cycle` 显示 Cycle 计数
  - [x] 在 Current State 上方添加 "Cycle: xxx" 显示当前周期数
- [x] 修复 ANSI 颜色代码问题
  - [x] 修复 `0m` 后缀问题
  - [x] 使用正则表达式单词边界避免header着色冲突

### 阶段 P2：高级功能

**P2.1：日志级别控制** ✅
- [x] `LogLevel` 枚举已在 P0 实现（debug、info、warning、error、off）
- [x] 日志级别状态已添加到 `Settings` 类
- [x] `setting log_level [level]` 命令处理器已实现
- [x] 根据当前级别的条件日志记录已实现
- [x] `StateDisplay.log()` 方法及基于级别的着色已实现
- [x] 日志前缀格式化已实现（`[DEBUG]`、`[INFO]` 等）
- [x] 在不同级别测试日志过滤

**P2.2：执行历史记录** ✅
- [x] 在 `SimulationRuntime` 中添加历史记录功能
  - [x] 添加 `history` 列表存储执行记录
  - [x] 每次 cycle 后记录：cycle number, state, variables, events
  - [x] 支持历史记录大小限制（可配置，默认 None 表示无限）
- [x] 实现 `history [n]` 命令处理器
  - [x] 从 runtime.history 检索历史记录
  - [x] 使用表格格式显示历史（类似 cycle 多次执行）
  - [x] 支持可选计数参数（默认：10，显示最近10条）
  - [x] 为历史显示添加颜色编码
  - [x] 支持 `history all` 显示所有历史

**P2.3：增强帮助系统** ✅
- [x] `help` 命令处理器已在 P0 实现
- [x] 格式化帮助文本已创建
- [x] 命令描述和使用示例已添加
- [x] 添加键盘快捷键文档（Tab、Ctrl+R 等）
- [x] 添加更详细的事件名称格式说明（全路径 vs 简短）

**P2.4：错误处理与用户体验** ✅
- [x] 捕获 `SimulationRuntimeDfsError` 并显示友好消息
- [x] 为所有命令添加输入验证
- [x] 改进错误消息并提供建议
- [x] 为边缘情况添加警告消息
- [x] 实现缺失功能的优雅降级
- [x] 全面测试错误场景

**P2.5：可配置设置系统** ✅
- [x] 实现 `setting` 命令用于配置运行时参数
  - [x] `setting` - 显示所有当前设置
  - [x] `setting <key>` - 显示特定设置的值
  - [x] `setting <key> <value>` - 设置特定配置项
- [x] 支持的配置项：
  - [x] `table_max_rows` - 表格最大显示行数（默认：20）
  - [x] `history_size` - 历史记录最大条数（默认：100）
  - [x] `color` - 启用/禁用颜色（on/off，默认：on）
  - [x] `log_level` - 日志级别（debug/info/warning/error/off）
- [x] 设置验证和错误处理
- [x] 设置更改时立即应用（如 history_size 会立即裁剪历史）
- [ ] 设置持久化（可选，保存到配置文件）

### 阶段 P3：完善与文档

**P3.1：测试** ✅
- [x] 为 `CommandProcessor` 编写单元测试
- [x] 为 `StateDisplay` 格式化编写单元测试
- [x] 为 `BatchProcessor` 编写单元测试
- [x] 为完整 REPL 工作流编写集成测试
- [x] 为 `history` 命令编写测试（空历史、计数、all、无效输入）
- [x] 为 `setting` 命令编写测试（列表、获取、设置、验证、历史裁剪）
- [x] 为 `Settings` 类编写单元测试（初始化、get/set、验证、list_all）
- [x] 为 `SimulationCompleter` 编写单元测试（命令补全、事件补全、设置键补全）
- [x] 为 CLI 入口点编写测试（批处理模式、无效文件、no-color标志）
- [x] 为 `SimulationREPL` 编写基础测试
- [x] 达到92%测试覆盖率（batch.py 100%，commands.py 97%，display.py 97%，completer.py 94%）
- [x] 测试跨平台兼容性（颜色支持检测、路径处理、行尾处理、Unicode处理、无颜色模式）
- [x] 使用各种 DSL 文件测试（简单、复杂层次、转换、守卫、效果、进入/退出动作、多变量、空状态、终止）
- [x] 测试终端兼容性（ANSI颜色代码、表格格式化、宽字符、日志级别、空输出）
- [x] 总计137个测试，全部通过

**P3.2：历史导出功能** ✅
- [x] 实现 `export` 命令用于导出执行历史
  - [x] `export <filename>` - 根据文件扩展名自动选择格式
- [x] 支持的导出格式：
  - [x] `.csv` - CSV格式，列：cycle, state, var1, var2, ...
  - [x] `.json` - JSON数组格式，每个条目包含 cycle, state, vars
  - [x] `.yaml` - YAML数组格式，每个条目包含 cycle, state, vars
  - [x] `.jsonl` - JSON Lines格式，每行一个JSON对象
- [x] 自动补全支持：
  - [x] 命令名称补全（`ex` → `export`）
  - [x] 文件名建议（`history.csv`, `history.json`, `history.yaml`, `history.jsonl`）
  - [x] 扩展名提示（显示格式类型）
- [x] 错误处理：
  - [x] 无参数时显示用法说明
  - [x] 无历史记录时提示用户
  - [x] 不支持的格式时显示错误
  - [x] 文件写入失败时捕获异常
- [x] 单元测试：
  - [x] 测试无参数情况
  - [x] 测试无历史记录情况
  - [x] 测试不支持的格式
  - [x] 测试CSV导出和验证
  - [x] 测试JSON导出和验证
  - [x] 测试YAML导出和验证
  - [x] 测试JSONL导出和验证
  - [x] 测试命令补全
  - [x] 测试文件名补全
