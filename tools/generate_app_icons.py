#!/usr/bin/env python3
"""
Generate build-time application icons from the canonical project logo.
"""

import argparse
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image


ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICNS_SIZES = (16, 32, 64, 128, 256, 512, 1024)


def _square_rgba(image: Image.Image) -> Image.Image:
    """Pad the source image onto a transparent square canvas."""
    image = image.convert("RGBA")
    size = max(image.size)
    if image.size == (size, size):
        return image

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - image.width) // 2, (size - image.height) // 2)
    canvas.paste(image, offset)
    return canvas


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resize(image: Image.Image, size: int) -> Image.Image:
    return image.resize((size, size), Image.Resampling.LANCZOS)


def _save_png(image: Image.Image, output: Path, size: int) -> None:
    _ensure_parent(output)
    _resize(image, size).save(output, format="PNG")


def _save_ico(image: Image.Image, output: Path, sizes: Iterable[int]) -> None:
    _ensure_parent(output)
    normalized_sizes = [(size, size) for size in sizes]
    image.save(output, format="ICO", sizes=normalized_sizes)


def _save_icns(image: Image.Image, output: Path, sizes: Iterable[int]) -> None:
    _ensure_parent(output)
    normalized_sizes = [(size, size) for size in sizes]
    image.save(output, format="ICNS", sizes=normalized_sizes)


def generate_icons(
    input_path: Path,
    pyinstaller_ico: Path,
    pyinstaller_icns: Path,
    pyinstaller_png: Path,
    vscode_png: Path,
    pyinstaller_png_size: int,
    vscode_png_size: int,
) -> Tuple[Path, Path, Path, Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input logo file does not exist: {input_path}")

    image = _square_rgba(Image.open(input_path))

    _save_ico(image, pyinstaller_ico, ICO_SIZES)
    _save_icns(image, pyinstaller_icns, ICNS_SIZES)
    _save_png(image, pyinstaller_png, pyinstaller_png_size)
    _save_png(image, vscode_png, vscode_png_size)

    return pyinstaller_ico, pyinstaller_icns, pyinstaller_png, vscode_png


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate PyInstaller and VSCode extension icons from logo.png."
    )
    parser.add_argument(
        "--input",
        default="logos/logo.png",
        help="Source logo PNG path.",
    )
    parser.add_argument(
        "--pyinstaller-ico",
        default="build/icons/pyfcstm.ico",
        help="Output .ico path for Windows PyInstaller builds.",
    )
    parser.add_argument(
        "--pyinstaller-icns",
        default="build/icons/pyfcstm.icns",
        help="Output .icns path for macOS PyInstaller builds.",
    )
    parser.add_argument(
        "--pyinstaller-png",
        default="build/icons/pyfcstm.png",
        help="Output PNG path bundled with the PyInstaller artifact.",
    )
    parser.add_argument(
        "--vscode-png",
        default="editors/vscode/resources/icon.png",
        help="Output PNG path for the VSCode extension marketplace icon.",
    )
    parser.add_argument(
        "--pyinstaller-png-size",
        type=int,
        default=256,
        help="Square size for the bundled PyInstaller PNG asset.",
    )
    parser.add_argument(
        "--vscode-png-size",
        type=int,
        default=128,
        help="Square size for the VSCode extension icon.",
    )
    args = parser.parse_args()

    outputs = generate_icons(
        input_path=Path(args.input),
        pyinstaller_ico=Path(args.pyinstaller_ico),
        pyinstaller_icns=Path(args.pyinstaller_icns),
        pyinstaller_png=Path(args.pyinstaller_png),
        vscode_png=Path(args.vscode_png),
        pyinstaller_png_size=args.pyinstaller_png_size,
        vscode_png_size=args.vscode_png_size,
    )

    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
