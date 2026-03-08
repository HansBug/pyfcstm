#!/usr/bin/env python3
"""
Convert SVG files to PNG with transparent background.

This script uses cairosvg to convert SVG files to PNG format with
transparent backgrounds, suitable for logos and icons.

Example::

    $ python tools/svg2png.py -i logo.svg -o logo.png
    $ python tools/svg2png.py -i logo_banner.svg -o logo_banner.png
"""

import argparse
import sys
from pathlib import Path


def convert_svg_to_png(input_svg: str, output_png: str) -> None:
    """
    Convert an SVG file to PNG with transparent background.

    :param input_svg: Path to the input SVG file
    :type input_svg: str
    :param output_png: Path to the output PNG file
    :type output_png: str
    :return: ``None``.
    :rtype: None
    :raises ImportError: If cairosvg is not installed
    :raises FileNotFoundError: If input SVG file does not exist
    :raises IOError: If conversion fails
    """
    try:
        import cairosvg
    except ImportError:
        print("Error: cairosvg is not installed.", file=sys.stderr)
        print("Install it with: pip install cairosvg", file=sys.stderr)
        sys.exit(1)

    input_path = Path(input_svg)
    if not input_path.exists():
        print(f"Error: Input file '{input_svg}' does not exist.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output_png)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        cairosvg.svg2png(url=str(input_path), write_to=str(output_path))
        print(f"Successfully converted '{input_svg}' to '{output_png}'")
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main entry point for the SVG to PNG converter.

    Parses command-line arguments and performs the conversion.

    :return: ``None``.
    :rtype: None
    """
    parser = argparse.ArgumentParser(
        description="Convert SVG files to PNG with transparent background",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/svg2png.py -i logo.svg -o logo.png
  python tools/svg2png.py -i logo_banner.svg -o logo_banner.png
        """
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input SVG file path'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output PNG file path'
    )

    args = parser.parse_args()
    convert_svg_to_png(args.input, args.output)


if __name__ == '__main__':
    main()
