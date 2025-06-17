import builtins
import inspect

import jinja2

from .text import normalize, to_identifier


def add_builtins_to_env(env):
    """
    将 Python 内置函数挂载到 Jinja2 环境中

    Args:
        env: jinja2.Environment 实例

    Returns:
        挂载完毕后的 jinja2.Environment 实例
    """
    # Jinja2 已有的内置过滤器、测试器和全局函数
    existing_filters = set(env.filters.keys())
    existing_tests = set(env.tests.keys())
    existing_globals = set(env.globals.keys())

    # 获取所有 Python 内置函数
    builtin_items = [(name, obj) for name, obj in inspect.getmembers(builtins)
                     if not name.startswith('_')]  # 排除以下划线开头的内部函数

    # 分类函数适合的挂载位置
    for name, func in builtin_items:
        # 跳过非函数对象
        if not callable(func):
            continue

        # 判断函数是否适合作为过滤器
        is_filter_candidate = (
            # 过滤器通常接受一个主要参数并可能有其他可选参数
                inspect.isfunction(func) or inspect.isbuiltin(func)
        )

        # 判断函数是否适合作为测试器
        is_test_candidate = (
            # 测试函数通常返回布尔值，如 isinstance, issubclass 等
                name.startswith('is') or
                name in ('all', 'any', 'callable', 'hasattr')
        )

        # 挂载为过滤器（如果适合且不冲突）
        filter_name = name
        if is_filter_candidate and filter_name not in existing_filters:
            env.filters[filter_name] = func

        # 挂载为测试器（如果适合且不冲突）
        test_name = name
        if name.startswith('is'):
            # 对于 is 开头的函数，可以去掉 is 前缀作为测试器名称
            test_name = name[2:].lower()
        if is_test_candidate and test_name not in existing_tests:
            env.tests[test_name] = func

        # 挂载为全局函数（如果不冲突）
        if name not in existing_globals:
            env.globals[name] = func

    return env


def add_settings_for_env(env: jinja2.Environment):
    env = add_builtins_to_env(env)
    env.filters['normalize'] = normalize
    env.filters['to_identifier'] = to_identifier
    return env
