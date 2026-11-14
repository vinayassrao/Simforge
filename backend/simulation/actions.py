"""Action rules: preconditions, execution and the outcome of each robot action."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from simulation.collision import Blocker, find_blocker
from simulation.events import EventCategory, EventType
from simulation.types import Action, Cell, PackageState
from simulation.world import Package, World

ACTION_DESCRIPTIONS: dict[Action, dict[str, str]] = {
    Action.MOVE_FORWARD: {
        "meaning": "Drive one cell in the direction the robot faces.",
        "precondition": "The cell in front is inside the warehouse and empty.",
        "failure": "The robot stays where it is and a collision is recorded.",
    },
    Action.MOVE_BACKWARD: {
        "meaning": "Reverse one cell without turning.",
        "precondition": "The cell behind is inside the warehouse and empty.",
        "failure": "The robot stays where it is and a collision is recorded.",
    },
    Action.TURN_LEFT: {
        "meaning": "Rotate 90 degrees counter-clockwise on the spot.",
        "precondition": "None. Turning is always possible.",
        "failure": "Cannot fail.",
    },
    Action.TURN_RIGHT: {
        "meaning": "Rotate 90 degrees clockwise on the spot.",
        "precondition": "None. Turning is always possible.",
        "failure": "Cannot fail.",
    },
    Action.PICK_UP: {
        "meaning": "Lift the package in the cell directly in front of the robot.",
        "precondition": ("The robot carries nothing, and the package in front is the current target."),
        "failure": "Nothing is lifted and an invalid action is recorded with the reason.",
    },
    Action.DROP: {
        "meaning": "Place the carried package in the cell directly in front of the robot.",
        "precondition": "The robot carries a package and the cell in front is empty.",
        "failure": "The package stays on the robot and an invalid action is recorded.",
    },
    Action.WAIT: {
        "meaning": "Do nothing for one step. Moving obstacles keep moving.",
        "precondition": "None.",
        "failure": "Cannot fail.",
    },
}


@dataclass
class ActionOutcome:
    """What happened when an action was applied."""

    action: Action
    success: bool
    event_type: EventType
    category: EventCategory
    message: str
    error_code: str | None = None
    entity_id: str | None = None
    collision: Blocker | None = None
    collision_cell: Cell | None = None
    restricted_entry: bool = False
    picked_up: Package | None = None
    dropped: Package | None = None
    delivered: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_invalid(self) -> bool:
        """True when the action's preconditions were not met."""
        return not self.success and self.collision is None


class ActionExecutor:
    """Applies actions to a world. ``current_target_id`` is the package the task wants next."""

    def __init__(self, world: World) -> None:
        self._world = world

    def execute(self, action: Action, current_target_id: str | None) -> ActionOutcome:
        if action in (Action.MOVE_FORWARD, Action.MOVE_BACKWARD):
            return self._move(action)
        if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
            return self._turn(action)
        if action is Action.PICK_UP:
            return self._pick_up(current_target_id)
        if action is Action.DROP:
            return self._drop()
        return ActionOutcome(action, True, EventType.WAITED, EventCategory.ACTION, "The robot waited for one step.")

    def legal_actions(self, current_target_id: str | None) -> list[Action]:
        """Actions that would succeed right now."""
        world = self._world
        pose = world.robot.pose
        legal = [Action.TURN_LEFT, Action.TURN_RIGHT, Action.WAIT]
        if find_blocker(world, pose.front) is None:
            legal.append(Action.MOVE_FORWARD)
        if find_blocker(world, pose.back) is None:
            legal.append(Action.MOVE_BACKWARD)
        if self._pickup_error(current_target_id) is None:
            legal.append(Action.PICK_UP)
        if self._drop_error() is None:
            legal.append(Action.DROP)
        return [action for action in Action if action in legal]

    # -- movement ----------------------------------------------------------

    def _move(self, action: Action) -> ActionOutcome:
        world = self._world
        pose = world.robot.pose
        target = pose.front if action is Action.MOVE_FORWARD else pose.back
        blocker = find_blocker(world, target)
        if blocker is not None:
            return ActionOutcome(
                action,
                False,
                EventType.COLLISION,
                EventCategory.COLLISION,
                f"Collision: the robot hit {blocker.description} at {list(target)} and did not move.",
                error_code="collision",
                entity_id=blocker.entity_id,
                collision=blocker,
                collision_cell=target,
                data={"cell": list(target), "blocker": blocker.kind.value},
            )
        origin = world.robot.position
        world.robot.position = target
        direction = "forward" if action is Action.MOVE_FORWARD else "backward"
        return ActionOutcome(
            action,
            True,
            EventType.MOVE_COMPLETED,
            EventCategory.ACTION,
            f"Moved {direction} from {list(origin)} to {list(target)}.",
            restricted_entry=world.is_restricted(target),
            data={"from": list(origin), "to": list(target)},
        )

    def _turn(self, action: Action) -> ActionOutcome:
        robot = self._world.robot
        robot.orientation = robot.orientation.left if action is Action.TURN_LEFT else robot.orientation.right
        side = "left" if action is Action.TURN_LEFT else "right"
        return ActionOutcome(
            action,
            True,
            EventType.TURN_COMPLETED,
            EventCategory.ACTION,
            f"Turned {side}; now facing {robot.orientation.value.lower()}.",
            data={"orientation": robot.orientation.value},
        )

    # -- pick up -----------------------------------------------------------

    def _pickup_error(self, current_target_id: str | None) -> tuple[str, str] | None:
        world = self._world
        if world.robot.carrying is not None:
            return "already_carrying", "The robot is already carrying a package."
        package = world.package_at(world.robot.pose.front)
        if package is None:
            return "no_object_in_range", "There is no package directly in front of the robot."
        if package.state is PackageState.DELIVERED:
            return "object_unavailable", f"The {package.spec.name.lower()} was already delivered."
        if package.id != current_target_id:
            return (
                "object_unavailable",
                f"The {package.spec.name.lower()} is not the current target and cannot be collected yet.",
            )
        return None

    def _pick_up(self, current_target_id: str | None) -> ActionOutcome:
        world = self._world
        error = self._pickup_error(current_target_id)
        if error is not None:
            code, message = error
            return ActionOutcome(
                Action.PICK_UP,
                False,
                EventType.PICKUP_FAILED,
                EventCategory.ERROR,
                f"Pick-up failed: {message}",
                error_code=code,
            )
        package = world.package_at(world.robot.pose.front)
        assert package is not None  # guaranteed by _pickup_error
        origin = package.position
        package.position = None
        package.state = PackageState.CARRIED
        world.robot.carrying = package.id
        return ActionOutcome(
            Action.PICK_UP,
            True,
            EventType.PICKUP_SUCCESS,
            EventCategory.MILESTONE,
            f"Picked up the {package.spec.name.lower()}.",
            entity_id=package.id,
            picked_up=package,
            data={"from": list(origin) if origin else None},
        )

    # -- drop --------------------------------------------------------------

    def _drop_error(self) -> tuple[str, str] | None:
        world = self._world
        if world.robot.carrying is None:
            return "not_carrying", "The robot is not carrying anything."
        blocker = find_blocker(world, world.robot.pose.front)
        if blocker is not None:
            return "drop_blocked", f"The cell in front is occupied by {blocker.description}."
        return None

    def _drop(self) -> ActionOutcome:
        world = self._world
        error = self._drop_error()
        if error is not None:
            code, message = error
            return ActionOutcome(
                Action.DROP,
                False,
                EventType.DROP_FAILED,
                EventCategory.ERROR,
                f"Drop failed: {message}",
                error_code=code,
            )
        package = world.carried_package
        assert package is not None  # guaranteed by _drop_error
        target = world.robot.pose.front
        destination = world.scenario.zone(package.spec.destination_zone_id)
        delivered = target in destination.cells
        package.position = target
        package.state = PackageState.DELIVERED if delivered else PackageState.AVAILABLE
        world.robot.carrying = None
        if delivered:
            return ActionOutcome(
                Action.DROP,
                True,
                EventType.DELIVERY_SUCCESS,
                EventCategory.MILESTONE,
                f"Delivered the {package.spec.name.lower()} to the {destination.name.lower()}.",
                entity_id=package.id,
                dropped=package,
                delivered=True,
                data={"cell": list(target), "zone": destination.id},
            )
        return ActionOutcome(
            Action.DROP,
            True,
            EventType.OBJECT_DROPPED,
            EventCategory.INFO,
            f"Dropped the {package.spec.name.lower()} at {list(target)}, outside its delivery zone.",
            entity_id=package.id,
            dropped=package,
            data={"cell": list(target)},
        )
