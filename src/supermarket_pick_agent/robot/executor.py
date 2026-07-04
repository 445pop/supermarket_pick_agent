from __future__ import annotations

from ..models import ExecutionResult, GripperState, VLAActionChunk


class SafetyExecutor:
    def __init__(self, max_abs_delta: float = 0.20) -> None:
        self.max_abs_delta = max_abs_delta

    def execute(self, chunk: VLAActionChunk) -> ExecutionResult:
        safety_error = self._validate(chunk)
        if safety_error:
            return ExecutionResult(
                executed=False,
                safe_stop=True,
                reason=safety_error,
                gripper_state=GripperState(width_mm=75.0, force=0.0),
                data={
                    "all_steps_sent": False,
                    "controller_done": False,
                    "settled": False,
                    "chunk_metadata": chunk.metadata,
                },
            )

        final_width = chunk.gripper_commands[-1] if chunk.gripper_commands else 75.0
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

    def _validate(self, chunk: VLAActionChunk) -> str | None:
        if not chunk.steps:
            return "empty_action_chunk"
        for index, step in enumerate(chunk.steps):
            if len(step) != 6:
                return f"invalid_action_dimension_at_step_{index}"
            if any(abs(value) > self.max_abs_delta for value in step):
                return f"action_delta_limit_exceeded_at_step_{index}"
        if any(width < 0.0 or width > 85.0 for width in chunk.gripper_commands):
            return "gripper_width_out_of_range"
        return None
