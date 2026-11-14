"""The Panda3D warehouse scene graph.

``build`` creates the static warehouse for a scenario; ``sync`` moves the
dynamic entities to match a state snapshot; ``animate`` eases them towards
their targets every frame. Scene nodes are only ever touched from the Panda3D
task loop.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from panda3d.core import (
    AmbientLight,
    BitMask32,
    CollisionBox,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionSphere,
    CollisionTraverser,
    DirectionalLight,
    LineSegs,
    NodePath,
    Point3,
    TextNode,
    TextureStage,
    TransparencyAttrib,
)

from simulation import geometry as geo
from simulation.scenarios import get_scenario
from simulation.scenarios.base import ScenarioDefinition
from simulation.types import Cell, Orientation, ZoneKind

OBSTACLE_MASK = BitMask32.bit(1)
BACKGROUND = (0.043, 0.07, 0.125, 1)
ACCENT = geo.hex_color("#22d3ee")
CARTON_COLORS = ("#b08968", "#9c6644", "#ddb892", "#7f5539", "#a98467", "#588157", "#457b9d")
STATE_LIGHT_COLORS = {
    "IDLE": "#94a3b8",
    "NAVIGATING_TO_OBJECT": "#22d3ee",
    "PICKING_UP": "#f59e0b",
    "NAVIGATING_TO_TARGET": "#22d3ee",
    "DROPPING_OBJECT": "#f59e0b",
    "COMPLETED": "#22c55e",
    "FAILED": "#ef4444",
}
MOVE_RATE = 9.0
TURN_RATE = 11.0


@dataclass
class SceneOptions:
    grid: bool = False
    paths: bool = True
    collisions: bool = True
    labels: bool = True


@dataclass
class _Mover:
    """A node that eases towards a target position and heading."""

    node: NodePath
    target: tuple[float, float]
    heading: float

    def snap(self) -> None:
        self.node.setPos(self.target[0], self.target[1], 0)
        self.node.setH(self.heading)

    def ease(self, dt: float, speed: float) -> None:
        blend = min(1.0, dt * MOVE_RATE * max(1.0, speed))
        x, y = self.node.getX(), self.node.getY()
        self.node.setPos(x + (self.target[0] - x) * blend, y + (self.target[1] - y) * blend, 0)
        delta = (self.heading - self.node.getH() + 180) % 360 - 180
        self.node.setH(self.node.getH() + delta * min(1.0, dt * TURN_RATE * max(1.0, speed)))


class WarehouseScene:
    def __init__(self, render: NodePath) -> None:
        self._render = render
        self.root = render.attachNewNode("warehouse")
        self.options = SceneOptions()
        self.scenario: ScenarioDefinition | None = None
        self._floor_texture = geo.make_floor_texture()
        self._hazard_texture = geo.make_hazard_texture()
        self._static = self.root.attachNewNode("static")
        self._dynamic = self.root.attachNewNode("dynamic")
        self._overlay = self.root.attachNewNode("overlay")
        self._labels = self._overlay.attachNewNode("labels")
        self._grid = self._overlay.attachNewNode("grid")
        self._path = self._overlay.attachNewNode("path")
        self._incidents = self._overlay.attachNewNode("incidents")
        self._collision_nodes: list[NodePath] = []
        self._robot: _Mover | None = None
        self._robot_parts: dict[str, NodePath] = {}
        self._packages: dict[str, NodePath] = {}
        self._obstacles: dict[str, _Mover] = {}
        self._target_marker: NodePath | None = None
        self._path_cells: list[list[int]] = []
        self._incident_count = -1
        self._carrying = False
        self._clock = 0.0
        self._traverser = CollisionTraverser("warehouse")
        self._contacts = CollisionHandlerQueue()
        self._setup_lights()

    # -- lighting ------------------------------------------------------------

    def _setup_lights(self) -> None:
        ambient = AmbientLight("ambient")
        ambient.setColor((0.42, 0.45, 0.52, 1))
        self._render.setLight(self._render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor((0.95, 0.92, 0.86, 1))
        sun.setShadowCaster(True, 2048, 2048)
        lens = sun.getLens()
        lens.setFilmSize(34, 34)
        lens.setNearFar(1, 70)
        self._sun = self._render.attachNewNode(sun)
        self._render.setLight(self._sun)

        fill = DirectionalLight("fill")
        fill.setColor((0.16, 0.22, 0.3, 1))
        fill_path = self._render.attachNewNode(fill)
        fill_path.setHpr(140, -35, 0)
        self._render.setLight(fill_path)
        self._render.setShaderAuto()

    def _aim_sun(self, scenario: ScenarioDefinition) -> None:
        centre = Point3(scenario.width / 2, scenario.height / 2, 0)
        self._sun.setPos(centre + Point3(-9, -14, 24))
        self._sun.lookAt(centre)

    # -- static world --------------------------------------------------------

    def build(self, state: dict[str, Any]) -> None:
        """Rebuild the whole scene for the scenario in ``state``."""
        scenario = get_scenario(state["scenario_id"])
        self.scenario = scenario
        for group in (self._static, self._dynamic, self._labels, self._grid, self._path, self._incidents):
            group.getChildren().detach()
        self._collision_nodes.clear()
        self._packages.clear()
        self._obstacles.clear()
        self._path_cells = []
        self._incident_count = -1
        self._carrying = False

        self._aim_sun(scenario)
        self._build_floor(scenario)
        self._build_walls(scenario)
        for cell in sorted(scenario.shelves):
            self._build_shelf(cell)
        for cell in sorted(scenario.static_obstacles):
            self._build_pallet(cell)
        for zone in scenario.zones:
            self._build_zone(zone)
        for cell in scenario.checkpoints:
            self._build_checkpoint(cell)
        self._build_grid(scenario)
        self._build_robot()
        self._build_target_marker()

        observation = state["observation"]
        for item in observation["objects"]:
            self._build_package(item)
        for obstacle in observation["obstacles"]["moving"]:
            self._build_forklift(obstacle)
        self.sync(state, snap=True)
        self.apply_options()

    def _build_floor(self, scenario: ScenarioDefinition) -> None:
        floor = geo.make_floor(-0.5, -0.5, scenario.width - 0.5, scenario.height - 0.5)
        floor.setTexture(self._floor_texture)
        floor.setTexScale(TextureStage.getDefault(), scenario.width, scenario.height)
        floor.reparentTo(self._static)
        apron = geo.make_box(scenario.width + 3, scenario.height + 3, 0.2, (0.07, 0.1, 0.16, 1), "apron")
        apron.setPos(scenario.width / 2 - 0.5, scenario.height / 2 - 0.5, -0.21)
        apron.reparentTo(self._static)

    def _build_walls(self, scenario: ScenarioDefinition) -> None:
        width, height = scenario.width, scenario.height
        wall_color = (0.36, 0.41, 0.5, 1)
        stripe_color = geo.shade(ACCENT, 0.42)
        spans = (
            (width + 0.4, 0.2, width / 2 - 0.5, -0.6),
            (width + 0.4, 0.2, width / 2 - 0.5, height - 0.4),
            (0.2, height + 0.4, -0.6, height / 2 - 0.5),
            (0.2, height + 0.4, width - 0.4, height / 2 - 0.5),
        )
        for size_x, size_y, x, y in spans:
            wall = geo.make_box(size_x, size_y, 0.9, wall_color, "wall")
            wall.setPos(x, y, 0)
            wall.reparentTo(self._static)
            stripe = geo.make_box(size_x + 0.02, size_y + 0.02, 0.07, stripe_color, "wall-stripe")
            stripe.setPos(x, y, 0.9)
            stripe.reparentTo(self._static)

    def _build_shelf(self, cell: Cell) -> None:
        rng = random.Random(cell[0] * 131 + cell[1] * 17)
        shelf = self._static.attachNewNode(f"shelf-{cell[0]}-{cell[1]}")
        shelf.setPos(cell[0], cell[1], 0)
        steel = (0.2, 0.33, 0.55, 1)
        for dx in (-0.45, 0.45):
            for dy in (-0.45, 0.45):
                post = geo.make_box(0.07, 0.07, 1.9, steel, "post")
                post.setPos(dx, dy, 0)
                post.reparentTo(shelf)
        for level in (0.12, 0.72, 1.32):
            board = geo.make_box(1.0, 0.98, 0.05, (0.93, 0.56, 0.16, 1), "board")
            board.setZ(level)
            board.reparentTo(shelf)
            for slot in (-0.24, 0.24):
                if rng.random() < 0.82:
                    size = rng.uniform(0.3, 0.42)
                    carton = geo.make_box(
                        size,
                        rng.uniform(0.45, 0.8),
                        rng.uniform(0.25, 0.48),
                        geo.hex_color(rng.choice(CARTON_COLORS)),
                        "carton",
                    )
                    carton.setPos(slot + rng.uniform(-0.03, 0.03), rng.uniform(-0.05, 0.05), level + 0.05)
                    carton.reparentTo(shelf)
        self._add_collision_box(shelf, 0.5, 0.5, 0.95, f"shelf-{cell[0]}-{cell[1]}")

    def _build_pallet(self, cell: Cell) -> None:
        rng = random.Random(cell[0] * 53 + cell[1] * 7)
        pallet = self._static.attachNewNode(f"pallet-{cell[0]}-{cell[1]}")
        pallet.setPos(cell[0], cell[1], 0)
        base = geo.make_box(0.9, 0.9, 0.12, (0.55, 0.39, 0.22, 1), "pallet-base")
        base.reparentTo(pallet)
        height = 0.12
        for _ in range(rng.choice((2, 3))):
            size = rng.uniform(0.62, 0.82)
            box_height = rng.uniform(0.28, 0.4)
            carton = geo.make_box(size, size, box_height, geo.hex_color(rng.choice(CARTON_COLORS)), "carton")
            carton.setPos(rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), height)
            carton.setH(rng.uniform(-9, 9))
            carton.reparentTo(pallet)
            height += box_height
        cone = geo.make_cylinder(0.07, 0.3, geo.hex_color("#f97316"), 10, "marker")
        cone.setPos(0.36, -0.36, 0.12)
        cone.reparentTo(pallet)
        self._add_collision_box(pallet, 0.45, 0.45, 0.5, f"pallet-{cell[0]}-{cell[1]}")

    def _build_zone(self, zone) -> None:
        if not zone.cells:
            return
        color = geo.hex_color(zone.color)
        xs = [cell[0] for cell in zone.cells]
        ys = [cell[1] for cell in zone.cells]
        x0, x1, y0, y1 = min(xs) - 0.5, max(xs) + 0.5, min(ys) - 0.5, max(ys) + 0.5
        restricted = zone.kind is ZoneKind.RESTRICTED
        decal = geo.make_floor_decal(x0, y0, x1, y1, (1, 1, 1, 1) if restricted else (*color[:3], 0.3), 0.012)
        if restricted:
            decal.setTexture(self._hazard_texture)
            decal.setTexScale(TextureStage.getDefault(), (x1 - x0) * 2, (y1 - y0) * 2)
        decal.reparentTo(self._static)
        border = geo.make_outline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], (*color[:3], 1), 0.02, 3.5)
        border.reparentTo(self._static)
        if zone.kind in (ZoneKind.DELIVERY, ZoneKind.RESTRICTED):
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                post = geo.make_cylinder(0.05, 0.45, color, 10, "zone-post")
                post.setPos(x, y, 0)
                post.reparentTo(self._static)
        self._add_label(zone.name, ((x0 + x1) / 2, (y0 + y1) / 2, 1.5), color)

    def _build_checkpoint(self, cell: Cell) -> None:
        disc = geo.make_cylinder(0.14, 0.012, (*ACCENT[:3], 1), 4, "checkpoint")
        disc.setPos(cell[0], cell[1], 0.006)
        disc.setH(45)
        disc.setLightOff()
        disc.reparentTo(self._static)

    def _build_grid(self, scenario: ScenarioDefinition) -> None:
        lines = LineSegs("grid")
        lines.setColor(0.55, 0.75, 0.95, 0.35)
        lines.setThickness(1.0)
        for x in range(scenario.width + 1):
            lines.moveTo(x - 0.5, -0.5, 0.025)
            lines.drawTo(x - 0.5, scenario.height - 0.5, 0.025)
        for y in range(scenario.height + 1):
            lines.moveTo(-0.5, y - 0.5, 0.025)
            lines.drawTo(scenario.width - 0.5, y - 0.5, 0.025)
        grid = self._grid.attachNewNode(lines.create())
        grid.setLightOff()
        grid.setTransparency(TransparencyAttrib.MAlpha)

    # -- dynamic entities ----------------------------------------------------

    def _build_robot(self) -> None:
        robot_root = self._dynamic.attachNewNode("robot")
        robot = robot_root.attachNewNode("robot-model")
        robot.setScale(1.18)
        body = geo.make_box(0.62, 0.74, 0.2, (0.13, 0.16, 0.22, 1), "chassis")
        body.setZ(0.1)
        body.reparentTo(robot)
        deck = geo.make_box(0.54, 0.5, 0.12, (0.86, 0.9, 0.95, 1), "deck")
        deck.setPos(0, -0.08, 0.3)
        deck.reparentTo(robot)
        for dx in (-0.33, 0.33):
            for dy in (-0.24, 0.24):
                axle = robot.attachNewNode("axle")
                axle.setPos(dx, dy, 0.12)
                axle.setR(90)
                wheel = geo.make_cylinder(0.12, 0.08, (0.05, 0.05, 0.06, 1), 14, "wheel")
                wheel.setZ(-0.04)
                wheel.reparentTo(axle)
        arrow = geo.make_arrow(0.34, 0.3, ACCENT, "heading")
        arrow.setPos(0, -0.06, 0.425)
        arrow.reparentTo(robot)
        mast = geo.make_box(0.05, 0.05, 0.34, (0.3, 0.34, 0.4, 1), "mast")
        mast.setPos(0.2, -0.28, 0.42)
        mast.reparentTo(robot)
        light = geo.make_cylinder(0.07, 0.07, geo.hex_color("#94a3b8"), 12, "status-light")
        light.setPos(0.2, -0.28, 0.76)
        light.setLightOff()
        light.reparentTo(robot)
        forks = robot.attachNewNode("forks")
        for dx in (-0.16, 0.16):
            fork = geo.make_box(0.08, 0.42, 0.04, (0.75, 0.78, 0.82, 1), "fork")
            fork.setPos(dx, 0.52, 0)
            fork.reparentTo(forks)
        forks.setZ(0.1)
        carry = forks.attachNewNode("carry-slot")
        carry.setPos(0, 0.52, 0.04)

        sphere = CollisionNode("robot-collider")
        sphere.addSolid(CollisionSphere(0, 0, 0.3, 0.34))
        sphere.setFromCollideMask(OBSTACLE_MASK)
        sphere.setIntoCollideMask(BitMask32.allOff())
        sphere_path = robot.attachNewNode(sphere)
        self._collision_nodes.append(sphere_path)
        self._traverser.clearColliders()
        self._contacts.clearEntries()
        self._traverser.addCollider(sphere_path, self._contacts)

        self._robot = _Mover(robot_root, (0.0, 0.0), 0.0)
        self._robot_parts = {"forks": forks, "carry": carry, "light": light}

    def _build_package(self, item: dict[str, Any]) -> None:
        color = geo.hex_color(item["color"])
        package = self._dynamic.attachNewNode(item["id"])
        box = geo.make_box(0.46, 0.46, 0.36, color, "package-body")
        box.reparentTo(package)
        tape = geo.make_box(0.1, 0.47, 0.365, geo.shade(color, 1.6), "tape")
        tape.reparentTo(package)
        label = geo.make_box(0.2, 0.005, 0.12, (0.96, 0.96, 0.96, 1), "shipping-label")
        label.setPos(-0.1, -0.233, 0.14)
        label.reparentTo(package)
        self._packages[item["id"]] = package
        text = self._add_label(item["name"], (0, 0, 0.75), color, parent=package)
        text.setName("label")

    def _build_forklift(self, obstacle: dict[str, Any]) -> None:
        yellow = geo.hex_color("#facc15")
        forklift = self._dynamic.attachNewNode(obstacle["id"])
        body = geo.make_box(0.66, 0.8, 0.36, yellow, "forklift-body")
        body.setZ(0.1)
        body.reparentTo(forklift)
        cab = geo.make_box(0.5, 0.36, 0.42, (0.12, 0.13, 0.16, 1), "cab")
        cab.setPos(0, -0.14, 0.46)
        cab.reparentTo(forklift)
        for dx in (-0.2, 0.2):
            mast = geo.make_box(0.06, 0.06, 1.05, (0.2, 0.2, 0.24, 1), "mast")
            mast.setPos(dx, 0.34, 0.1)
            mast.reparentTo(forklift)
        stripe = geo.make_box(0.68, 0.06, 0.1, (0.1, 0.1, 0.1, 1), "hazard-stripe")
        stripe.setPos(0, -0.39, 0.2)
        stripe.reparentTo(forklift)
        beacon = geo.make_cylinder(0.07, 0.08, geo.hex_color("#f97316"), 12, "beacon")
        beacon.setPos(0, -0.14, 0.88)
        beacon.setLightOff()
        beacon.reparentTo(forklift)
        self._add_collision_box(forklift, 0.36, 0.42, 0.5, obstacle["id"])
        self._add_label(obstacle["name"], (0, 0, 1.45), yellow, parent=forklift)
        self._obstacles[obstacle["id"]] = _Mover(forklift, (0.0, 0.0), 0.0)

    def _build_target_marker(self) -> None:
        marker = self._overlay.attachNewNode("target-marker")
        tip = geo.make_cylinder(0.17, 0.3, (*ACCENT[:3], 1), 4, "target-tip")
        tip.setLightOff()
        tip.setZ(0.3)
        tip.reparentTo(marker)
        self._target_marker = marker

    # -- helpers -------------------------------------------------------------

    def _add_collision_box(self, parent: NodePath, hx: float, hy: float, hz: float, name: str) -> None:
        node = CollisionNode(name)
        node.addSolid(CollisionBox(Point3(0, 0, hz), hx, hy, hz))
        node.setIntoCollideMask(OBSTACLE_MASK)
        node.setFromCollideMask(BitMask32.allOff())
        self._collision_nodes.append(parent.attachNewNode(node))

    def _add_label(self, text: str, position, color, parent: NodePath | None = None) -> NodePath:
        node = TextNode("label")
        node.setText(text)
        node.setAlign(TextNode.ACenter)
        node.setTextColor(1, 1, 1, 1)
        node.setCardColor(color[0] * 0.35, color[1] * 0.35, color[2] * 0.35, 0.82)
        node.setCardAsMargin(0.35, 0.35, 0.18, 0.18)
        node.setCardDecal(True)
        path = (parent or self._labels).attachNewNode(node)
        path.setScale(0.32)
        path.setPos(*position)
        path.setBillboardPointEye()
        path.setLightOff()
        path.setShaderOff()
        path.setDepthTest(False)
        path.setDepthWrite(False)
        path.setBin("fixed", 60)
        if parent is not None:
            path.setTag("entity-label", "1")
        return path

    # -- synchronisation -----------------------------------------------------

    def sync(self, state: dict[str, Any], snap: bool = False) -> None:
        """Point every dynamic entity at its position in ``state``."""
        if self._robot is None:
            return
        observation = state["observation"]
        agent = observation["agent"]
        self._robot.target = tuple(agent["position"])
        self._robot.heading = Orientation(agent["orientation"]).heading_degrees
        self._carrying = agent["carrying"]
        self._robot_parts["light"].setColor(geo.hex_color(STATE_LIGHT_COLORS[agent["state"]]))

        for item in observation["objects"]:
            package = self._packages.get(item["id"])
            if package is None:
                continue
            if item["state"] == "carried":
                package.reparentTo(self._robot_parts["carry"])
                package.setPosHpr(0, 0, 0, 0, 0, 0)
            else:
                package.reparentTo(self._dynamic)
                package.setPosHpr(item["position"][0], item["position"][1], 0, 0, 0, 0)

        for obstacle in observation["obstacles"]["moving"]:
            mover = self._obstacles.get(obstacle["id"])
            if mover is None:
                continue
            mover.target = tuple(obstacle["position"])
            dx = obstacle["next_position"][0] - obstacle["position"][0]
            dy = obstacle["next_position"][1] - obstacle["position"][1]
            if dx or dy:
                mover.heading = math.degrees(math.atan2(-dx, dy))
            if snap:
                mover.snap()
        if snap:
            self._robot.snap()
            self._robot_parts["forks"].setZ(0.42 if self._carrying else 0.1)

        self._place_target_marker(observation)
        self._update_path(state.get("planned_path", []))
        self._update_incidents(state.get("incidents", []))

    def _place_target_marker(self, observation: dict[str, Any]) -> None:
        marker = self._target_marker
        target = observation["target"]
        if marker is None:
            return
        if target is None or observation["status"] in ("completed", "failed"):
            marker.hide()
            return
        marker.show()
        if target["position"] is not None:
            marker.setPos(target["position"][0], target["position"][1], 1.1)
        else:
            cells = target["delivery_cells"]
            marker.setPos(sum(cell[0] for cell in cells) / len(cells), sum(cell[1] for cell in cells) / len(cells), 0.7)

    def _update_path(self, cells: list[list[int]]) -> None:
        if cells == self._path_cells:
            return
        self._path_cells = cells
        self._path.getChildren().detach()
        if len(cells) < 2:
            return
        line = geo.make_polyline([(x, y, 0.06) for x, y in cells], (*ACCENT[:3], 0.95), 4.0)
        line.reparentTo(self._path)
        for x, y in cells[1:]:
            dot = geo.make_cylinder(0.07, 0.01, (*ACCENT[:3], 1), 10, "path-dot")
            dot.setPos(x, y, 0.055)
            dot.setLightOff()
            dot.reparentTo(self._path)

    def _update_incidents(self, incidents: list[dict[str, Any]]) -> None:
        if len(incidents) == self._incident_count:
            return
        self._incident_count = len(incidents)
        self._incidents.getChildren().detach()
        red = geo.hex_color("#ef4444")
        for incident in incidents:
            x, y = incident["cell"]
            cross = LineSegs("incident")
            cross.setColor(red)
            cross.setThickness(5)
            for (ax, ay), (bx, by) in (((-0.3, -0.3), (0.3, 0.3)), ((-0.3, 0.3), (0.3, -0.3))):
                cross.moveTo(x + ax, y + ay, 0.09)
                cross.drawTo(x + bx, y + by, 0.09)
            mark = self._incidents.attachNewNode(cross.create())
            mark.setLightOff()

    def animate(self, dt: float, speed: float) -> None:
        """Ease entities towards their targets. Called once per rendered frame."""
        if self._robot is None:
            return
        self._clock += dt
        self._robot.ease(dt, speed)
        for mover in self._obstacles.values():
            mover.ease(dt, speed)
        forks = self._robot_parts["forks"]
        lift = 0.42 if self._carrying else 0.1
        forks.setZ(forks.getZ() + (lift - forks.getZ()) * min(1.0, dt * 8))
        if self._target_marker is not None and not self._target_marker.isHidden():
            self._target_marker.setH(self._clock * 90)
            self._target_marker.getChild(0).setZ(0.3 + 0.08 * math.sin(self._clock * 3))

    # -- options and debugging -----------------------------------------------

    def apply_options(self) -> None:
        options = self.options
        _toggle(self._grid, options.grid)
        _toggle(self._path, options.paths)
        _toggle(self._incidents, options.collisions)
        _toggle(self._labels, options.labels)
        for label in self._dynamic.findAllMatches("**/=entity-label"):
            _toggle(label, options.labels)

    def show_collision_shapes(self, visible: bool) -> None:
        """Debug view: draw the Panda3D collision solids of the robot and obstacles."""
        for node in self._collision_nodes:
            if not node.isEmpty():
                _toggle(node, visible)

    def physical_contacts(self) -> list[str]:
        """Names of collision solids the robot's sphere overlaps right now.

        The grid rules decide what counts as a collision; this is an independent
        check, using Panda3D's collision system, that the rendered scene agrees.
        """
        self._traverser.traverse(self.root)
        return sorted({entry.getIntoNode().getName() for entry in self._contacts.getEntries()})


def _toggle(node: NodePath, visible: bool) -> None:
    if visible:
        node.show()
    else:
        node.hide()
