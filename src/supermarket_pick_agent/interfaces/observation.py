from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models import GripperState, RobotState


class ObservationProvider(Protocol):
    def capture(self) -> tuple[str, RobotState, GripperState]:
        """Capture the latest image, robot state, and gripper state."""


class LocalObservationProvider:
    def __init__(self, image_path: Path) -> None:
        self.image_path = image_path

    def capture(self) -> tuple[str, RobotState, GripperState]:
        robot_state = RobotState()
        gripper_state = GripperState(width_mm=75.0, force=0.0)
        return str(self.image_path), robot_state, gripper_state
