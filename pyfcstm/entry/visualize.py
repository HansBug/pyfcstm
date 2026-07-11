"""
Visualization CLI integration for rendered state machine diagrams.

This module adds a ``visualize`` subcommand to the main CLI. The command reads
an FCSTM DSL file, reuses the existing PlantUML generation pipeline, renders
an image through the Python ``plantumlcli`` library, and optionally opens the
rendered file with the operating system's default viewer.

The implementation keeps runtime dependencies minimal by delegating rendering
and display to tools that are commonly available in the target environment
instead of embedding a GUI toolkit in the CLI process.

Example::

    >>> import click
    >>> from pyfcstm.entry.visualize import _add_visualize_subcommand
    >>> cli = click.Group()
    >>> _add_visualize_subcommand(cli)  # doctest: +ELLIPSIS
    <...Group...>
"""

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Optional, Tuple

import click

from .base import CONTEXT_SETTINGS, ClickErrorException
from .plantuml import build_plantuml_output

_VISUALIZE_RENDER_TYPES = ("png", "svg", "pdf")
_VISUALIZE_RENDERERS = ("local", "remote", "auto")
_PLANTUML_JAR_ENV = "PLANTUML_JAR"
_PLANTUML_HOST_ENV = "PLANTUML_HOST"
_OFFICIAL_PLANTUML_HOST = "http://www.plantuml.com/plantuml"


def _plantumlcli_runtime_errors() -> tuple:
    """
    Build the tuple of exception classes that ``plantumlcli`` realistically
    raises during ``check()`` / ``dump()`` calls.

    Listed classes and why they can fire:

    * ``CommandLineExecuteError`` -- raised by ``plantumlcli.models.local``
      when the bundled ``java -jar plantuml.jar`` invocation fails (non-zero
      exit, bad jar, missing class). It subclasses ``Exception`` directly.
    * ``ValueError`` -- ``plantumlcli`` raises this for input validation
      (missing java path, malformed host URL, unsupported resource type).
    * ``FileNotFoundError`` / ``IsADirectoryError`` / ``PermissionError`` --
      raised when the java executable or plantuml jar path is wrong.
    * ``OSError`` -- general filesystem / subprocess errors during local
      rendering. (``FileNotFoundError`` etc. subclass it but we list it
      explicitly to also catch lower-level subprocess failures.)
    * ``requests.exceptions.RequestException`` -- raised by the remote
      backend when the HTTP request to the PlantUML server fails (network
      down, DNS failure, timeout, 5xx). Lazily imported so the dependency
      stays optional in environments that only use the local backend.

    Unexpected classes (``TypeError`` / ``AttributeError`` / ``KeyError`` /
    ``ImportError``) are deliberately *not* swallowed -- they indicate a
    programmer bug in this module or in ``plantumlcli`` itself and must
    surface, not be reformatted into a user-facing ``ClickErrorException``.
    """
    classes = [OSError, ValueError]
    try:
        from plantumlcli.utils.execute import CommandLineExecuteError
    except (
        ImportError
    ):  # pragma: no cover - plantumlcli ships this since 0.0.1; defensive only.
        # The only reason this import would fail is a corrupted plantumlcli
        # install. The outer load_plantumlcli_classes() barrier would already
        # have surfaced the problem before we got here.
        pass
    else:
        classes.append(CommandLineExecuteError)
    try:
        import requests.exceptions as _rex
    except ImportError:  # pragma: no cover - requests is a hard dep of plantumlcli.
        # plantumlcli pins ``requests``; this branch is purely belt-and-braces.
        pass
    else:
        classes.append(_rex.RequestException)
    return tuple(classes)


_PLANTUMLCLI_RUNTIME_ERRORS = _plantumlcli_runtime_errors()


def _env_flag(name: str) -> bool:
    """
    Check whether an environment variable is set to a truthy value.

    :param name: Environment variable name.
    :type name: str
    :return: ``True`` if the variable is set to a truthy value, otherwise
        ``False``.
    :rtype: bool
    """
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def get_visualize_cache_dir() -> pathlib.Path:
    """
    Get the cache directory used for auto-generated diagram outputs.

    The location follows platform conventions to keep rendered preview files in
    a stable place long enough for external viewers to open them successfully.

    :return: Cache directory path.
    :rtype: pathlib.Path

    Example::

        >>> get_visualize_cache_dir().name  # doctest: +SKIP
        'visualize'
    """
    home = pathlib.Path.home()
    if (
        sys.platform == "win32"
    ):  # pragma: no cover -- exercised on the Windows CI runner only.
        # Windows uses %LOCALAPPDATA% so the cache survives roaming-profile
        # syncs. Falls back to the documented default when the env var is
        # unset (locked-down user profiles).
        base_dir = pathlib.Path(
            os.environ.get("LOCALAPPDATA") or (home / "AppData" / "Local")
        )
    elif (
        sys.platform == "darwin"
    ):  # pragma: no cover -- exercised on the macOS CI runner only.
        # macOS convention; ~/Library/Caches is the documented per-user
        # cache root.
        base_dir = home / "Library" / "Caches"
    else:
        base_dir = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or (home / ".cache"))

    cache_dir = base_dir / "pyfcstm" / "visualize"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def resolve_visualize_output_path(
    input_code_file: str,
    output_file: Optional[str],
    render_type: str,
) -> pathlib.Path:
    """
    Resolve the final rendered output path.

    :param input_code_file: Input DSL file path.
    :type input_code_file: str
    :param output_file: User-specified output path, or ``None`` to use the
        cache directory.
    :type output_file: str or None
    :param render_type: Rendered file type.
    :type render_type: str
    :return: Absolute output path.
    :rtype: pathlib.Path
    :raises pyfcstm.entry.base.ClickErrorException: If the output suffix
        conflicts with ``render_type``.

    Example::

        >>> resolve_visualize_output_path(
        ...     'machine.fcstm', 'diagram', 'svg'
        ... ).name
        'diagram.svg'
    """
    suffix = f".{render_type}"
    if output_file:
        output_path = pathlib.Path(output_file)
        if output_path.suffix:
            if output_path.suffix.lower() != suffix:
                raise ClickErrorException(
                    f"Output file suffix {output_path.suffix!r} does not match render type {render_type!r}."
                )
        else:
            output_path = output_path.with_suffix(suffix)
        return pathlib.Path(os.path.abspath(str(output_path.expanduser())))

    input_path = pathlib.Path(input_code_file).expanduser()
    digest = hashlib.sha1(str(input_path.resolve()).encode("utf-8")).hexdigest()[:12]
    filename = f"{input_path.stem or 'diagram'}-{digest}.{render_type}"
    return get_visualize_cache_dir() / filename


def load_plantumlcli_classes():
    """
    Load Python API classes from ``plantumlcli``.

    :return: Two-tuple of ``(LocalPlantuml, RemotePlantuml)`` classes.
    :rtype: Tuple[type, type]
    :raises pyfcstm.entry.base.ClickErrorException: If the package is not
        available.

    Example::

        >>> local_type, remote_type = load_plantumlcli_classes()  # doctest: +SKIP
        >>> local_type.__name__, remote_type.__name__  # doctest: +SKIP
        ('LocalPlantuml', 'RemotePlantuml')
    """
    try:
        from plantumlcli import LocalPlantuml, RemotePlantuml
    except (ImportError, ModuleNotFoundError) as err:
        raise ClickErrorException(
            f'Python package "plantumlcli" is not installed or failed to import: {err}'
        )
    return LocalPlantuml, RemotePlantuml


def _format_exception_message(err: Exception) -> str:
    """
    Format an exception as a short one-line message.

    :param err: Exception instance.
    :type err: Exception
    :return: Formatted message.
    :rtype: str
    """
    message = str(err).strip()
    if message:
        return f"{type(err).__name__}: {message}"
    return type(err).__name__


def create_local_plantuml_backend(
    java: Optional[str] = None,
    plantuml_jar: Optional[str] = None,
):
    """
    Create a local PlantUML backend from ``plantumlcli``.

    :param java: Optional Java executable path.
    :type java: str or None
    :param plantuml_jar: Optional PlantUML jar path.
    :type plantuml_jar: str or None
    :return: Local backend object.
    :rtype: Any

    Example::

        >>> create_local_plantuml_backend()  # doctest: +SKIP
        <plantumlcli.models.local.LocalPlantuml object at ...>
    """
    LocalPlantuml, _ = load_plantumlcli_classes()
    return LocalPlantuml.autoload(java=java, plantuml=plantuml_jar)


def create_remote_plantuml_backend(remote_host: Optional[str] = None):
    """
    Create a remote PlantUML backend from ``plantumlcli``.

    :param remote_host: Optional remote host URL.
    :type remote_host: str or None
    :return: Remote backend object.
    :rtype: Any

    Example::

        >>> create_remote_plantuml_backend()  # doctest: +SKIP
        <plantumlcli.models.remote.RemotePlantuml object at ...>
    """
    _, RemotePlantuml = load_plantumlcli_classes()
    return RemotePlantuml.autoload(host=remote_host)


def run_plantumlcli_builtin_check(
    renderer: str,
    java: Optional[str] = None,
    plantuml_jar: Optional[str] = None,
    remote_host: Optional[str] = None,
) -> Dict[str, Tuple[bool, str]]:
    """
    Run ``plantumlcli``'s built-in check flow and return availability status.

    This uses the same Python entry logic behind ``plantumlcli -c`` rather than
    reimplementing the checks locally.

    :param renderer: Requested renderer mode.
    :type renderer: str
    :param java: Optional Java executable path for local rendering.
    :type java: str or None
    :param plantuml_jar: Optional PlantUML jar path for local rendering.
    :type plantuml_jar: str or None
    :param remote_host: Optional remote PlantUML host URL.
    :type remote_host: str or None
    :return: Mapping from renderer name to ``(available, message)``.
    :rtype: Dict[str, Tuple[bool, str]]

    Example::

        >>> run_plantumlcli_builtin_check('auto')  # doctest: +SKIP
        {...}
    """
    try:
        LocalPlantuml, RemotePlantuml = load_plantumlcli_classes()
        from plantumlcli.entry.general import print_check_info, PlantumlCheckType
        from plantumlcli.models.base import try_plantuml
    except ClickErrorException as err:
        message = err.message
        return {
            "package": (False, message),
            "local": (False, message),
            "remote": (False, message),
        }

    local_ok, local = try_plantuml(LocalPlantuml, java=java, plantuml=plantuml_jar)
    remote_ok, remote = try_plantuml(RemotePlantuml, host=remote_host)

    if renderer == "local":
        check_type = PlantumlCheckType.LOCAL
    elif renderer == "remote":
        check_type = PlantumlCheckType.REMOTE
    else:
        check_type = PlantumlCheckType.BOTH

    print_check_info(check_type, local_ok, local, remote_ok, remote)

    return {
        "package": (True, "plantumlcli Python package is available."),
        "local": (local_ok, "available" if local_ok else repr(local)),
        "remote": (remote_ok, "available" if remote_ok else repr(remote)),
    }


def resolve_renderer_backend(
    renderer: str,
    java: Optional[str] = None,
    plantuml_jar: Optional[str] = None,
    remote_host: Optional[str] = None,
) -> Tuple[str, Any]:
    """
    Resolve the effective renderer backend object.

    :param renderer: Requested renderer mode.
    :type renderer: str
    :param java: Optional Java executable path for local rendering.
    :type java: str or None
    :param plantuml_jar: Optional PlantUML jar path for local rendering.
    :type plantuml_jar: str or None
    :param remote_host: Optional remote PlantUML host URL.
    :type remote_host: str or None
    :return: Two-tuple of ``(renderer_name, backend_object)``.
    :rtype: Tuple[str, Any]
    :raises pyfcstm.entry.base.ClickErrorException: If no usable backend is
        available for the requested mode.

    Example::

        >>> resolve_renderer_backend('auto')  # doctest: +SKIP
        ('local', <plantumlcli.models.local.LocalPlantuml object at ...>)
    """
    if renderer == "local":
        try:
            backend = create_local_plantuml_backend(
                java=java, plantuml_jar=plantuml_jar
            )
            backend.check()
        except _PLANTUMLCLI_RUNTIME_ERRORS as err:
            # See _plantumlcli_runtime_errors() for the documented class set.
            raise ClickErrorException(
                f"Local PlantUML renderer is unavailable: {_format_exception_message(err)}"
            )
        return "local", backend

    if renderer == "remote":
        try:
            backend = create_remote_plantuml_backend(remote_host=remote_host)
            backend.check()
        except _PLANTUMLCLI_RUNTIME_ERRORS as err:
            # See _plantumlcli_runtime_errors() for the documented class set.
            raise ClickErrorException(
                f"Remote PlantUML renderer is unavailable: {_format_exception_message(err)}"
            )
        return "remote", backend

    try:
        backend = create_local_plantuml_backend(java=java, plantuml_jar=plantuml_jar)
        backend.check()
    except _PLANTUMLCLI_RUNTIME_ERRORS as local_err:
        # See _plantumlcli_runtime_errors() for the documented class set.
        try:
            backend = create_remote_plantuml_backend(remote_host=remote_host)
            backend.check()
        except _PLANTUMLCLI_RUNTIME_ERRORS as remote_err:
            # See _plantumlcli_runtime_errors() for the documented class set.
            raise ClickErrorException(
                "No usable PlantUML renderer found. "
                f"Local failed: {_format_exception_message(local_err)}. "
                f"Remote failed: {_format_exception_message(remote_err)}."
            )
        else:
            return "remote", backend
    else:
        return "local", backend


def _render_local_plantuml_on_windows(
    backend: Any,
    output_file: pathlib.Path,
    render_type: str,
    plantuml_output: str,
) -> None:
    """
    Render locally on Windows without keeping the PlantUML source open.

    ``plantumlcli`` 0.0.3 renders through a ``NamedTemporaryFile`` that remains
    open while Java reads it. Windows locks that file, so the external process
    receives ``PermissionError``. This adapter materializes and closes the
    source before invoking the same Java/JAR pair exposed by the backend. For
    PDF output it also preserves ``plantumlcli``'s optional CairoSVG path,
    because the standalone PlantUML JAR does not bundle Batik's PDF converter.

    :param backend: Loaded ``plantumlcli.LocalPlantuml`` backend.
    :type backend: Any
    :param output_file: Target rendered file path.
    :type output_file: pathlib.Path
    :param render_type: PlantUML output type.
    :type render_type: str
    :param plantuml_output: PlantUML source text.
    :type plantuml_output: str
    :return: ``None``.
    :rtype: None
    :raises OSError: If Java exits unsuccessfully.
    :raises FileNotFoundError: If PlantUML does not create exactly one output
        file of the requested type.

    Example::

        >>> backend = create_local_plantuml_backend()  # doctest: +SKIP
        >>> _render_local_plantuml_on_windows(  # doctest: +SKIP
        ...     backend, pathlib.Path('machine.png'), 'png', '@startuml\\n@enduml'
        ... )
    """
    with tempfile.TemporaryDirectory(prefix="pyfcstm-plantuml-") as directory:
        root = pathlib.Path(directory)
        source_file = root / "diagram.puml"
        output_dir = root / "output"
        output_dir.mkdir()
        source_file.write_text(plantuml_output, encoding="utf-8")

        generated_type = render_type
        cairosvg = None
        if render_type == "pdf":
            try:
                import cairosvg as cairosvg_module
            except ImportError:
                # CairoSVG is optional in plantumlcli; without it, retain the
                # backend's direct PlantUML PDF behavior and resulting error.
                pass
            else:
                cairosvg = cairosvg_module
                generated_type = "svg"

        command = [
            str(backend.java),
            "-jar",
            str(backend.plantuml),
            f"-t{generated_type}",
            "-charset",
            "UTF-8",
            "-o",
            str(output_dir),
            str(source_file),
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise OSError(
                "Local PlantUML process exited with status "
                f"{result.returncode}: {detail or 'no process output'}"
            )

        generated_files = tuple(output_dir.glob(f"*.{generated_type}"))
        if len(generated_files) != 1:
            raise FileNotFoundError(
                "Local PlantUML produced "
                f"{len(generated_files)} {generated_type!r} files; "
                "expected exactly one."
            )
        if cairosvg is not None:
            cairosvg.svg2pdf(
                bytestring=generated_files[0].read_bytes(),
                write_to=str(output_file),
            )
        else:
            shutil.copyfile(str(generated_files[0]), str(output_file))


def render_plantuml_diagram(
    plantuml_output: str,
    output_file: pathlib.Path,
    render_type: str,
    renderer: str,
    java: Optional[str] = None,
    plantuml_jar: Optional[str] = None,
    remote_host: Optional[str] = None,
) -> str:
    """
    Render PlantUML text into a diagram file through ``plantumlcli``.

    :param plantuml_output: PlantUML source text.
    :type plantuml_output: str
    :param output_file: Target output file path.
    :type output_file: pathlib.Path
    :param render_type: Rendered file type.
    :type render_type: str
    :param renderer: Requested renderer mode.
    :type renderer: str
    :param java: Optional Java executable path for local rendering.
    :type java: str or None
    :param plantuml_jar: Optional PlantUML jar path for local rendering.
    :type plantuml_jar: str or None
    :param remote_host: Optional remote PlantUML host URL.
    :type remote_host: str or None
    :return: Effective renderer mode used for the render.
    :rtype: str
    :raises pyfcstm.entry.base.ClickErrorException: If rendering fails.

    Example::

        >>> render_plantuml_diagram(  # doctest: +SKIP
        ...     '@startuml\\n@enduml', pathlib.Path('machine.svg'), 'svg', 'auto'
        ... )
        'local'
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    effective_renderer, backend = resolve_renderer_backend(
        renderer=renderer,
        java=java,
        plantuml_jar=plantuml_jar,
        remote_host=remote_host,
    )

    try:
        if effective_renderer == "local" and sys.platform == "win32":
            _render_local_plantuml_on_windows(
                backend,
                output_file,
                render_type,
                plantuml_output,
            )
        else:
            backend.dump(str(output_file), render_type, plantuml_output)
    except _PLANTUMLCLI_RUNTIME_ERRORS as err:
        # See _plantumlcli_runtime_errors() for the documented class set.
        raise ClickErrorException(
            f"Failed to render diagram with plantumlcli ({effective_renderer}): {_format_exception_message(err)}"
        )

    if not output_file.exists():
        raise ClickErrorException(
            f"plantumlcli reported success but no output file was created: {output_file}"
        )

    return effective_renderer


def detect_headless_environment() -> Tuple[bool, Optional[str]]:
    """
    Detect whether the current process should avoid GUI operations.

    :return: Two-tuple of ``(is_headless, reason)``.
    :rtype: Tuple[bool, Optional[str]]

    Example::

        >>> isinstance(detect_headless_environment()[0], bool)
        True
    """
    if _env_flag("PYFCSTM_NO_GUI"):
        return True, "GUI display disabled by PYFCSTM_NO_GUI."
    if _env_flag("CI"):
        return True, "GUI display disabled in CI environment."

    if sys.platform.startswith("linux"):
        if not any(
            os.environ.get(key) for key in ("DISPLAY", "WAYLAND_DISPLAY", "MIR_SOCKET")
        ):
            return (
                True,
                "No desktop session detected (DISPLAY/WAYLAND_DISPLAY/MIR_SOCKET is unset).",
            )

    return False, None


def open_diagram_with_default_app(file_path: pathlib.Path) -> Tuple[bool, str]:
    """
    Open a rendered diagram file with the operating system's default viewer.

    :param file_path: Rendered diagram path.
    :type file_path: pathlib.Path
    :return: Two-tuple of ``(opened, reason)``.
    :rtype: Tuple[bool, str]

    Example::

        >>> open_diagram_with_default_app(pathlib.Path('machine.png'))  # doctest: +SKIP
        (True, '')
    """
    headless, reason = detect_headless_environment()
    if headless:
        return False, reason or "GUI display is not available."

    try:
        if sys.platform == "win32":  # pragma: no cover -- exercised on Windows CI only.
            # ``os.startfile`` is Windows-only; the type-ignore is intentional.
            os.startfile(str(file_path))  # type: ignore[attr-defined]
            return True, ""
        if sys.platform == "darwin":  # pragma: no cover -- exercised on macOS CI only.
            # macOS uses the ``open`` CLI to dispatch to the registered
            # viewer for the file extension.
            subprocess.Popen(
                ["open", str(file_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, ""

        xdg_open = shutil.which("xdg-open")
        if xdg_open is not None:
            subprocess.Popen(
                [xdg_open, str(file_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, ""

        gio = shutil.which("gio")
        if gio is not None:
            subprocess.Popen(
                [gio, "open", str(file_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, ""

        return False, "No supported system opener was found."
    except OSError as err:
        return False, f"Failed to launch system viewer: {err}"


def _add_visualize_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``visualize`` subcommand to a Click CLI group.

    :param cli: Click group to extend.
    :type cli: click.Group
    :return: The mutated Click group.
    :rtype: click.Group

    Example::

        >>> group = click.Group()
        >>> 'visualize' in _add_visualize_subcommand(group).commands
        True
    """

    @cli.command(
        "visualize",
        help="Render a state machine DSL file into a diagram and optionally open it.",
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        "-i",
        "--input-code",
        "input_code_file",
        type=str,
        required=False,
        help="Input code file of state machine DSL.",
    )
    @click.option(
        "-o",
        "--output",
        "output_file",
        type=str,
        default=None,
        help="Output diagram file. Uses a cache directory when omitted.",
    )
    @click.option(
        "-l",
        "--level",
        "detail_level",
        type=click.Choice(["minimal", "normal", "full"], case_sensitive=False),
        default="normal",
        help="Detail level preset (minimal/normal/full). Default: normal.",
    )
    @click.option(
        "-c",
        "--config",
        "config_options",
        multiple=True,
        help="Configuration options in key=value format. Can be specified multiple times.",
    )
    @click.option(
        "-t",
        "--type",
        "render_type",
        type=click.Choice(_VISUALIZE_RENDER_TYPES, case_sensitive=False),
        default="png",
        help="Rendered diagram type. Default: png.",
    )
    @click.option(
        "--renderer",
        type=click.Choice(_VISUALIZE_RENDERERS, case_sensitive=False),
        default="auto",
        help="Renderer mode: local, remote or auto. Default: auto.",
    )
    @click.option(
        "-j",
        "--java",
        "java",
        type=str,
        default=shutil.which("java"),
        help="Path of java executable file (will load from environment when not given).",
        show_default="java from ${PATH}",
    )
    @click.option(
        "-p",
        "--plantuml",
        "--plantuml-jar",
        "plantuml_jar",
        envvar=_PLANTUML_JAR_ENV,
        type=str,
        default=None,
        help=f"Path of PlantUML jar file (will load from ${{{_PLANTUML_JAR_ENV}}} when not given).",
    )
    @click.option(
        "-r",
        "--remote-host",
        "remote_host",
        envvar=_PLANTUML_HOST_ENV,
        type=str,
        default=_OFFICIAL_PLANTUML_HOST,
        help=f"Remote host of the online PlantUML editor "
        f"(will load from ${{{_PLANTUML_HOST_ENV}}} when not given).",
        show_default=True,
    )
    @click.option(
        "--check",
        "check_only",
        is_flag=True,
        default=False,
        help="Check renderer availability and exit without rendering a diagram.",
    )
    @click.option(
        "--open/--no-open",
        "open_after_render",
        default=True,
        help="Open the rendered file with the system default viewer.",
    )
    @click.option(
        "--strict-open",
        is_flag=True,
        default=False,
        help="Treat viewer launch failure as an error.",
    )
    def visualize(
        input_code_file: str,
        output_file: Optional[str],
        detail_level: str,
        config_options: Tuple[str, ...],
        render_type: str,
        renderer: str,
        java: Optional[str],
        plantuml_jar: Optional[str],
        remote_host: Optional[str],
        check_only: bool,
        open_after_render: bool,
        strict_open: bool,
    ) -> None:
        """
        Render and optionally open a diagram for a state machine DSL file.

        :param input_code_file: Input DSL file path.
        :type input_code_file: str
        :param output_file: Optional rendered diagram output path.
        :type output_file: str or None
        :param detail_level: PlantUML detail level preset.
        :type detail_level: str
        :param config_options: Additional PlantUML configuration overrides.
        :type config_options: Tuple[str, ...]
        :param render_type: Rendered diagram type.
        :type render_type: str
        :param renderer: Rendering backend mode.
        :type renderer: str
        :param java: Optional Java executable path for local rendering.
        :type java: str or None
        :param plantuml_jar: Optional PlantUML jar path for local rendering.
        :type plantuml_jar: str or None
        :param remote_host: Optional remote PlantUML host URL.
        :type remote_host: str or None
        :param check_only: Whether to only check backend availability.
        :type check_only: bool
        :param open_after_render: Whether to open the diagram after rendering.
        :type open_after_render: bool
        :param strict_open: Whether viewer launch failure should be fatal.
        :type strict_open: bool
        :return: ``None``.
        :rtype: None
        """
        if check_only:
            status = run_plantumlcli_builtin_check(
                renderer=renderer.lower(),
                java=java,
                plantuml_jar=plantuml_jar,
                remote_host=remote_host,
            )
            if renderer.lower() == "local":
                click.get_current_context().exit(0 if status["local"][0] else 1)
            elif renderer.lower() == "remote":
                click.get_current_context().exit(0 if status["remote"][0] else 1)
            else:
                click.get_current_context().exit(
                    0 if (status["local"][0] or status["remote"][0]) else 1
                )

        if not input_code_file:
            raise ClickErrorException(
                "Input DSL file is required unless --check is used."
            )

        output_path = resolve_visualize_output_path(
            input_code_file, output_file, render_type.lower()
        )
        plantuml_output = build_plantuml_output(
            input_code_file=input_code_file,
            detail_level=detail_level,
            config_options=config_options,
        )
        effective_renderer = render_plantuml_diagram(
            plantuml_output=plantuml_output,
            output_file=output_path,
            render_type=render_type.lower(),
            renderer=renderer.lower(),
            java=java,
            plantuml_jar=plantuml_jar,
            remote_host=remote_host,
        )

        click.echo(f"Diagram rendered successfully with {effective_renderer} renderer.")
        click.echo(f"Output file: {output_path}")

        if not open_after_render:
            return

        opened, reason = open_diagram_with_default_app(output_path)
        if opened:
            click.echo("Opened rendered diagram with the system default viewer.")
            return

        if strict_open:
            raise ClickErrorException(
                f"Failed to open rendered diagram automatically. Output file: {output_path}. Reason: {reason}"
            )

        click.echo(f"GUI display skipped: {reason}")

    return cli
