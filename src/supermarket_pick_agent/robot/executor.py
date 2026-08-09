from __future__ import annotations

from dataclasses import dataclass

from ..models import ExecutionResult, GripperState, VLAActionChunk


@dataclass(frozen=True)
class SafetyLimits:
    action_dimension: int = 6
    max_abs_delta: float = 0.20
    min_gripper_width_mm: float = 0.0
    max_gripper_width_mm: float = 85.0
    default_gripper_width_mm: float = 75.0


class SafetyExecutor:
    def __init__(self, limits: SafetyLimits | None = None) -> None:
        self.limits = limits or SafetyLimits()

    def execute(self, chunk: VLAActionChunk) -> ExecutionResult:
        safety_error = self._validate(chunk)
        if safety_error:
            return ExecutionResult(
                executed=False,
                safe_stop=True,
                reason=safety_error["reason"],
                gripper_state=GripperState(width_mm=self.limits.default_gripper_width_mm, force=0.0),
                data={
                    "all_steps_sent": False,
                    "controller_done": False,
                    "settled": False,
                    "rejected": safety_error,
                    "chunk_metadata": chunk.metadata,
                },
            )

        final_width = (
            chunk.gripper_commands[-1]
            if chunk.gripper_commands
            else self.limits.default_gripper_width_mm
        )
        force = 1.4 if chunk.kind == "grasp" and final_width < 45.0 else 0.2
        return ExecutionResult(
            executed=True,
            safe_stop=False,
            reason="completed",
            gripper_state=GripperState(width_mm=final_width, force=force),
            data={
                "steps_executed": len(chunk.steps),
                "all_steps_sent": True,
                "controller_done": True,
                "settled": True,
                "chunk_metadata": chunk.metadata,
            },
        )

    def _validate(self, chunk: VLAActionChunk) -> dict | None:
        if not chunk.steps:
            return {"reason": "empty_action_chunk"}
        for index, step in enumerate(chunk.steps):
            if len(step) != self.limits.action_dimension:
                return {
                    "reason": f"invalid_action_dimension_at_step_{index}",
                    "step_index": index,
                    "expected_dimension": self.limits.action_dimension,
                    "actual_dimension": len(step),
                }
            for value_index, value in enumerate(step):
                if abs(value) > self.limits.max_abs_delta:
                    return {
                        "reason": f"action_delta_limit_exceeded_at_step_{index}",
                        "step_index": index,
                        "value_index": value_index,
                        "max_abs_delta": self.limits.max_abs_delta,
                        "actual_value": value,
                    }
        for index, width in enumerate(chunk.gripper_commands):
            if (
                width < self.limits.min_gripper_width_mm
                or width > self.limits.max_gripper_width_mm
            ):
                return {
                    "reason": "gripper_width_out_of_range",
                    "command_index": index,
                    "min_width_mm": self.limits.min_gripper_width_mm,
                    "max_width_mm": self.limits.max_gripper_width_mm,
                    "actual_width_mm": width,
                }
        return None
