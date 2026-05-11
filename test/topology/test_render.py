"""Tests for :mod:`pyfcstm.topology.render` (mini-racer + ELK + resvg)."""

from __future__ import annotations

import struct

import pytest

from pyfcstm.topology.render import (
    TopologyRenderError,
    build_render_payload,
    render_topology_png,
    render_topology_svg,
)
from pyfcstm.topology import (
    check_finiteness,
    check_inevitability,
    check_reachability,
)


@pytest.mark.unittest
class TestPayloadConstruction:
    def test_payload_keys(self, linear_machine):
        result = check_reachability(linear_machine, target='Root.B')
        payload = build_render_payload(linear_machine, result)
        assert payload['overlay']['kind'] == 'reach'
        assert payload['overlay']['verdict'] == 'ok'
        assert payload['nodes']
        assert any(n['id'] == '__END__' for n in payload['nodes'])
        assert payload['edges']

    def test_payload_rejects_unknown_result_type(self, linear_machine):
        with pytest.raises(TypeError):
            build_render_payload(linear_machine, object())


@pytest.mark.unittest
class TestSvgRender:
    def test_reach_ok_svg_has_witness_color(self, linear_machine):
        result = check_reachability(linear_machine, target='Root.C')
        svg = render_topology_svg(linear_machine, result)
        assert svg.startswith('<?xml')
        assert '<svg' in svg
        assert '#1d7c45' in svg, 'witness path stroke color missing'
        assert 'reachable' in svg.lower()

    def test_reach_fail_svg_has_unreach_marker(self, linear_machine):
        result = check_reachability(linear_machine, target='Root.A', source='Root.C')
        svg = render_topology_svg(linear_machine, result)
        assert 'unreachable' in svg.lower()

    def test_finite_fail_svg_has_cycle_color(self, trap_cycle_machine):
        result = check_finiteness(trap_cycle_machine)
        svg = render_topology_svg(trap_cycle_machine, result)
        assert '#b62a2a' in svg, 'trap-cycle stroke color missing'
        assert 'trap cycle' in svg.lower() or 'cycle' in svg.lower()

    def test_inev_fail_svg_has_avoid_color(self, branching_machine):
        result = check_inevitability(branching_machine, target='Root.Good')
        svg = render_topology_svg(branching_machine, result)
        assert '#cc5a2a' in svg, 'avoidable path color missing'
        assert 'avoidable' in svg.lower()


@pytest.mark.unittest
class TestPngRender:
    def test_reach_ok_png_has_magic_and_dims(self, linear_machine):
        result = check_reachability(linear_machine, target='Root.C')
        png = render_topology_png(linear_machine, result)
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        width, height = struct.unpack('>II', png[16:24])
        assert width > 0 and height > 0

    def test_finite_fail_png(self, trap_cycle_machine):
        result = check_finiteness(trap_cycle_machine)
        png = render_topology_png(trap_cycle_machine, result)
        assert png[:8] == b'\x89PNG\r\n\x1a\n'


@pytest.mark.unittest
class TestRenderHierarchical:
    def test_nested_machine_renders(self, nested_machine):
        result = check_reachability(nested_machine, target='Root.Done')
        svg = render_topology_svg(nested_machine, result)
        # Composite leaves still appear by their short name (last path segment).
        assert '>X<' in svg or 'X<' in svg
        assert '>Y<' in svg or 'Y<' in svg
        assert '>Done<' in svg or 'Done<' in svg
