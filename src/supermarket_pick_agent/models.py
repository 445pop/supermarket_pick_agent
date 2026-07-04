from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TaskStatus = Literal["running", "success", "failed"]
ActionKind = Literal["grasp", "place"]


@dataclass(frozen=True)
class Product:
    product_id: str
    display_name: str
    aliases: list[str]
    category: str
    stock: int
    shelf_id: str
    approach_point: str
    delivery_point: str
    appearance: str
    vla_skill: str
    vla_endpoint: str
    grasp_prompt: str
    place_vla_skill: str
    place_vla_endpoint: str
    place_prompt: str
    max_retry: int = 2


@dataclass
class RobotState:
    joints: list[float] = field(default_factory=lambda: [0.0] * 6)
    end_effector_pose: list[float] = field(default_factory=lambda: [0.0] * 6)


@dataclass
class GripperState:
    width_mm: float
    force: float
    fault: bool = False


@dataclass
class Observation:
    source: str
    success: bool
    reason: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class VLAActionChunk:
    kind: ActionKind
    steps: list[list[float]]
    gripper_commands: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    executed: bool
    safe_stop: bool
    reason: str
    gripper_state: GripperState
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    success: bool
    confidence: float
    reason: str
    target_visible_on_shelf: bool | None = None
    target_in_gripper: bool | None = None
    target_in_delivery_area: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    status: TaskStatus
    reason: str
    product: Product | None = None
    history: list[Observation] = field(default_factory=list)
