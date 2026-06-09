"""
Tests for :func:`pyfcstm.visualize.render_svg` and
:func:`pyfcstm.visualize.render_png`.
"""
import pytest

from pyfcstm.jsruntime import reset_engine
from pyfcstm.visualize import VisualizeOptions, render_png, render_svg


SIMPLE_DSL = (
    'def int counter = 0;\n'
    'state Demo { [*] -> Idle; state Idle; }\n'
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_engine()
    yield
    reset_engine()


@pytest.mark.unittest
class TestRenderSvg:
    def test_default(self):
        svg = render_svg(SIMPLE_DSL)
        assert svg.startswith('<svg')
        assert svg.rstrip().endswith('</svg>')
        assert 'Demo' in svg
        assert 'Idle' in svg

    def test_options_dataclass(self):
        svg = render_svg(SIMPLE_DSL, VisualizeOptions(direction='RIGHT'))
        assert 'data-fcstm-direction="RIGHT"' in svg

    def test_options_dict(self):
        svg = render_svg(SIMPLE_DSL, {'direction': 'LEFT'})
        assert 'data-fcstm-direction="LEFT"' in svg

    def test_options_none_uses_defaults(self):
        svg = render_svg(SIMPLE_DSL, None)
        assert 'data-fcstm-direction="TB"' in svg

    def test_invalid_options_type(self):
        with pytest.raises(TypeError, match='options must be'):
            render_svg(SIMPLE_DSL, options=123)


@pytest.mark.unittest
class TestRenderPng:
    def test_default_scale(self):
        png = render_png(SIMPLE_DSL)
        assert png[:8] == b'\x89PNG\r\n\x1a\n'

    def test_explicit_scale(self):
        small = render_png(SIMPLE_DSL, scale=1.0)
        large = render_png(SIMPLE_DSL, scale=2.0)
        assert small[:8] == b'\x89PNG\r\n\x1a\n'
        assert large[:8] == b'\x89PNG\r\n\x1a\n'
        # 2× should produce ~4× the pixel area, hence a noticeably
        # larger PNG. We only check ordering, not exact ratios.
        assert len(large) > len(small)

    def test_invalid_scale(self):
        with pytest.raises(ValueError, match='scale must be positive'):
            render_png(SIMPLE_DSL, scale=0)
        with pytest.raises(ValueError, match='scale must be positive'):
            render_png(SIMPLE_DSL, scale=-1.0)

    def test_with_options(self):
        png = render_png(
            SIMPLE_DSL,
            VisualizeOptions(direction='DOWN', detail_level='minimal'),
            scale=1.0,
        )
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
