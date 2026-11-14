"""Procedural Panda3D geometry: lit boxes, cylinders, floor decals and textures.

Everything in the warehouse is built from these helpers, so the project ships
no external model or texture files.
"""

from __future__ import annotations

import math
import random

from panda3d.core import (
    CardMaker,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    NodePath,
    PNMImage,
    SamplerState,
    Texture,
    TransparencyAttrib,
)

Color = tuple[float, float, float, float]


def hex_color(value: str, alpha: float = 1.0) -> Color:
    """Convert '#rrggbb' to a Panda3D colour tuple."""
    value = value.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return (red, green, blue, alpha)


def shade(color: Color, factor: float) -> Color:
    return (min(color[0] * factor, 1), min(color[1] * factor, 1), min(color[2] * factor, 1), color[3])


class _MeshBuilder:
    """Collects quads and triangles with flat normals into one Geom."""

    def __init__(self, name: str) -> None:
        self._data = GeomVertexData(name, GeomVertexFormat.getV3n3(), Geom.UHStatic)
        self._vertex = GeomVertexWriter(self._data, "vertex")
        self._normal = GeomVertexWriter(self._data, "normal")
        self._triangles = GeomTriangles(Geom.UHStatic)
        self._count = 0
        self._name = name

    def _add(self, points, normal) -> int:
        first = self._count
        for point in points:
            self._vertex.addData3(*point)
            self._normal.addData3(*normal)
        self._count += len(points)
        return first

    def quad(self, a, b, c, d, normal) -> None:
        first = self._add((a, b, c, d), normal)
        self._triangles.addVertices(first, first + 1, first + 2)
        self._triangles.addVertices(first, first + 2, first + 3)

    def triangle(self, a, b, c, normal) -> None:
        first = self._add((a, b, c), normal)
        self._triangles.addVertices(first, first + 1, first + 2)

    def build(self, color: Color) -> NodePath:
        geom = Geom(self._data)
        geom.addPrimitive(self._triangles)
        node = GeomNode(self._name)
        node.addGeom(geom)
        path = NodePath(node)
        path.setColor(color)
        return path


def make_box(size_x: float, size_y: float, size_z: float, color: Color, name: str = "box") -> NodePath:
    """A lit box centred on the origin in X and Y, with its base at Z = 0."""
    hx, hy = size_x / 2, size_y / 2
    z0, z1 = 0.0, size_z
    mesh = _MeshBuilder(name)
    mesh.quad((-hx, -hy, z1), (hx, -hy, z1), (hx, hy, z1), (-hx, hy, z1), (0, 0, 1))
    mesh.quad((-hx, hy, z0), (hx, hy, z0), (hx, -hy, z0), (-hx, -hy, z0), (0, 0, -1))
    mesh.quad((-hx, -hy, z0), (hx, -hy, z0), (hx, -hy, z1), (-hx, -hy, z1), (0, -1, 0))
    mesh.quad((hx, hy, z0), (-hx, hy, z0), (-hx, hy, z1), (hx, hy, z1), (0, 1, 0))
    mesh.quad((hx, -hy, z0), (hx, hy, z0), (hx, hy, z1), (hx, -hy, z1), (1, 0, 0))
    mesh.quad((-hx, hy, z0), (-hx, -hy, z0), (-hx, -hy, z1), (-hx, hy, z1), (-1, 0, 0))
    return mesh.build(color)


def make_cylinder(radius: float, height: float, color: Color, segments: int = 20, name: str = "cylinder") -> NodePath:
    """A lit cylinder along Z, centred on the origin in X and Y, base at Z = 0."""
    mesh = _MeshBuilder(name)
    ring = [
        (radius * math.cos(2 * math.pi * i / segments), radius * math.sin(2 * math.pi * i / segments))
        for i in range(segments + 1)
    ]
    for (x0, y0), (x1, y1) in zip(ring, ring[1:], strict=False):
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        length = math.hypot(mid_x, mid_y) or 1.0
        mesh.quad((x0, y0, 0), (x1, y1, 0), (x1, y1, height), (x0, y0, height), (mid_x / length, mid_y / length, 0))
        mesh.triangle((0, 0, height), (x0, y0, height), (x1, y1, height), (0, 0, 1))
        mesh.triangle((0, 0, 0), (x1, y1, 0), (x0, y0, 0), (0, 0, -1))
    return mesh.build(color)


def make_arrow(length: float, width: float, color: Color, name: str = "arrow") -> NodePath:
    """A flat arrow head lying in the XY plane and pointing along +Y."""
    mesh = _MeshBuilder(name)
    mesh.triangle((-width / 2, -length / 2, 0), (width / 2, -length / 2, 0), (0, length / 2, 0), (0, 0, 1))
    path = mesh.build(color)
    path.setLightOff()
    return path


def make_floor(x0: float, y0: float, x1: float, y1: float, name: str = "floor") -> NodePath:
    """A lit rectangle in the XY plane at Z = 0, with texture coordinates from 0 to 1."""
    maker = CardMaker(name)
    maker.setFrame(x0, x1, y0, y1)
    path = NodePath(maker.generate())
    path.setP(-90)
    return path


def make_floor_decal(
    x0: float, y0: float, x1: float, y1: float, color: Color, height: float, name: str = "decal"
) -> NodePath:
    """An unlit, optionally translucent rectangle lying just above the floor."""
    maker = CardMaker(name)
    maker.setFrame(x0, x1, y0, y1)
    path = NodePath(maker.generate())
    path.setP(-90)
    path.setZ(height)
    path.setColor(color)
    path.setLightOff()
    path.setTransparency(TransparencyAttrib.MAlpha)
    path.setDepthWrite(False)
    path.setBin("fixed", int(height * 1000))
    return path


def make_outline(points: list[tuple[float, float]], color: Color, height: float, thickness: float) -> NodePath:
    """A closed polyline on the floor, used for zone borders."""
    segments = LineSegs("outline")
    segments.setColor(color)
    segments.setThickness(thickness)
    segments.moveTo(points[0][0], points[0][1], height)
    for x, y in [*points[1:], points[0]]:
        segments.drawTo(x, y, height)
    path = NodePath(segments.create())
    path.setLightOff()
    return path


def make_polyline(points: list[tuple[float, float, float]], color: Color, thickness: float) -> NodePath:
    segments = LineSegs("polyline")
    segments.setColor(color)
    segments.setThickness(thickness)
    segments.moveTo(*points[0])
    for point in points[1:]:
        segments.drawTo(*point)
    path = NodePath(segments.create())
    path.setLightOff()
    path.setTransparency(TransparencyAttrib.MAlpha)
    return path


def _finish_texture(image: PNMImage, name: str) -> Texture:
    texture = Texture(name)
    texture.load(image)
    texture.setWrapU(SamplerState.WM_repeat)
    texture.setWrapV(SamplerState.WM_repeat)
    texture.setMinfilter(SamplerState.FT_linear_mipmap_linear)
    texture.setMagfilter(SamplerState.FT_linear)
    texture.setAnisotropicDegree(8)
    return texture


def make_floor_texture(size: int = 256) -> Texture:
    """Polished concrete tile with a darker joint line and light speckle. One tile per cell."""
    rng = random.Random(11)
    image = PNMImage(size, size)
    joint = max(2, size // 64)
    for x in range(size):
        for y in range(size):
            value = 0.30 + rng.uniform(-0.012, 0.012)
            if x < joint or y < joint:
                value = 0.21
            image.setXel(x, y, value * 0.86, value * 0.92, value * 1.04)
    return _finish_texture(image, "floor")


def make_hazard_texture(size: int = 64) -> Texture:
    """Diagonal red warning stripes with transparency, for restricted areas."""
    image = PNMImage(size, size, 4)
    for x in range(size):
        for y in range(size):
            stripe = ((x + y) // (size // 4)) % 2 == 0
            if stripe:
                image.setXelA(x, y, 0.94, 0.27, 0.27, 0.78)
            else:
                image.setXelA(x, y, 0.94, 0.27, 0.27, 0.16)
    return _finish_texture(image, "hazard")
