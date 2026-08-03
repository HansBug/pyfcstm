"""
Export all three formats from an installed artifact, through the CLI only.

Everything else that checks the export runs from a source checkout, where the
packaged assets sit in the tree next to the code.  An installed wheel or a frozen
executable resolves them differently, and the ways that goes wrong are invisible
from a checkout: an asset left out of the package data, a path assembled from
``__file__`` that no longer exists, a runtime marker that resolved to the wrong
distribution for the interpreter doing the installing.

This command therefore uses nothing but the command line and the filesystem.  It
does not import ``pyfcstm``, so it cannot accidentally satisfy an import that the
installed artifact would fail, and it works the same against a wheel in a fresh
virtual environment and against a one-file executable.

It is deliberately not part of ``pyfcstm --self-check``.  That entry point is a
deployment diagnostic for artifacts which have already passed the test matrix, and
this is a functional export test.

Run it against whatever provides the command::

    $ python tools/check_diagram_installed_export.py --command "pyfcstm"
    $ python tools/check_diagram_installed_export.py --command "dist/pyfcstm"
    diagram installed export: svg/png/pdf produced from the installed artifact
"""

import argparse
import json
import re
import shlex
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

MACHINE = "state Root { state A; state B; [*] -> A; A -> B :: Go; B -> A :: Back; }\n"


def run(command: List[str], *arguments: str) -> Tuple[int, str, str]:
    """
    Invoke the artifact's command line.

    :param command: Command words that launch the artifact.
    :type command: list[str]
    :param arguments: Arguments to append.
    :return: Exit status, stdout and stderr.
    :rtype: tuple[int, str, str]
    """
    completed = subprocess.run(
        list(command) + list(arguments), capture_output=True, text=True
    )
    return completed.returncode, completed.stdout, completed.stderr


def check_png(path: Path, scale: int) -> Tuple[int, int]:
    """
    Require a structurally valid PNG and return its size.

    :param path: File the artifact wrote.
    :type path: pathlib.Path
    :param scale: Scale the export was asked for, used in the message.
    :type scale: int
    :return: Width and height in pixels.
    :rtype: tuple[int, int]
    :raises SystemExit: If the file is not a PNG with an IHDR header.
    """
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        raise SystemExit(
            "the installed artifact wrote something that is not a PNG at scale %d"
            % scale
        )
    return struct.unpack(">II", data[16:24])


def check_pdf(path: Path) -> Tuple[int, int]:
    """
    Require a single-page vector PDF and return its page count and image count.

    :param path: File the artifact wrote.
    :type path: pathlib.Path
    :return: Page count and image-object count.
    :rtype: tuple[int, int]
    :raises SystemExit: If the file is not a PDF, or carries an image object.
    """
    data = path.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise SystemExit("the installed artifact wrote something that is not a PDF")
    pages = len(re.findall(rb"/Type\s*/Page\b", data))
    images = len(re.findall(rb"/Subtype\s*/Image\b|/ImageMask\b", data))
    if images:
        raise SystemExit(
            "the PDF from the installed artifact carries %d image object(s), so the "
            "drawing was rasterised rather than kept as vectors" % images
        )
    if pages != 1:
        raise SystemExit(
            "the PDF from the installed artifact has %d pages, not one" % pages
        )
    return pages, images


def check_svg(path: Path) -> int:
    """
    Require a self-contained expanded SVG and return its path count.

    :param path: File the artifact wrote.
    :type path: pathlib.Path
    :return: How many ``<path>`` elements the document carries.
    :rtype: int
    :raises SystemExit: If the document is not the expanded, self-contained form.
    """
    text = path.read_text(encoding="utf-8")
    problems = []
    if "<svg" not in text:
        problems.append("it is not an SVG document")
    for token in ("<text", "<marker", "font-family"):
        if token in text:
            problems.append(
                "it carries %s, so it is not the expanded form and depends on fonts "
                "the reader may not have" % token
            )
    if "<script" in text:
        problems.append("it carries a script element")
    if problems:
        raise SystemExit(
            "the SVG from the installed artifact is wrong:\n  " + "\n  ".join(problems)
        )
    return len(re.findall(r"<path\b", text))


def main(argv=None) -> int:
    """
    Export every format from the artifact and check each one.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int
    :raises SystemExit: If any export fails or produces the wrong thing.
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--command",
        default="pyfcstm",
        help="command line that launches the installed artifact",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="how many times to export each format, to catch state left between runs",
    )
    arguments = parser.parse_args(argv)
    command = shlex.split(arguments.command)
    if arguments.repeat < 1:
        raise SystemExit("--repeat must be at least 1")

    summary = {}
    with tempfile.TemporaryDirectory(prefix="pyfcstm-installed-") as directory:
        root = Path(directory)
        source = root / "machine.fcstm"
        source.write_text(MACHINE, encoding="utf-8")

        for attempt in range(arguments.repeat):
            svg = root / ("machine-%d.svg" % attempt)
            status, out, err = run(command, "diagram", "-i", str(source), "-o", str(svg))
            if status != 0:
                raise SystemExit(
                    "the installed artifact could not export SVG (exit %d)\n%s\n%s"
                    % (status, out[-2000:], err[-2000:])
                )
            summary["svgPaths"] = check_svg(svg)

            for scale in (1, 2):
                png = root / ("machine-%d-%dx.png" % (attempt, scale))
                status, out, err = run(
                    command,
                    "diagram",
                    "-i",
                    str(source),
                    "-o",
                    str(png),
                    "--scale",
                    str(scale),
                )
                if status != 0:
                    raise SystemExit(
                        "the installed artifact could not export PNG at %dx (exit %d)"
                        "\n%s\n%s" % (scale, status, out[-2000:], err[-2000:])
                    )
                width, height = check_png(png, scale)
                key = "png%dx" % scale
                summary[key] = [width, height]
            one = summary.get("png1x")
            two = summary.get("png2x")
            if one and two and (two[0] != one[0] * 2 or two[1] != one[1] * 2):
                raise SystemExit(
                    "the installed artifact ignored --scale: %r at 1x and %r at 2x"
                    % (one, two)
                )

            pdf = root / ("machine-%d.pdf" % attempt)
            status, out, err = run(command, "diagram", "-i", str(source), "-o", str(pdf))
            if status != 0:
                raise SystemExit(
                    "the installed artifact could not export PDF (exit %d)\n%s\n%s"
                    % (status, out[-2000:], err[-2000:])
                )
            summary["pdfPages"], summary["pdfImages"] = check_pdf(pdf)

    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
