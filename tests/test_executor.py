from supermarket_pick_agent.models import VLAActionChunk
from supermarket_pick_agent.robot.executor import SafetyExecutor, SafetyLimits


def _chunk(steps, gripper_commands=None):
    return VLAActionChunk(
        kind="grasp",
        steps=steps,
        gripper_commands=gripper_commands or [30.0],
    )


def test_executor_accepts_valid_action_chunk():
    executor = SafetyExecutor()

    result = executor.execute(_chunk([[0.01, 0.0, 0.0, 0.0, 0.0, 0.0]]))

    assert result.executed is True
    assert result.safe_stop is False
    assert result.reason == "completed"


def test_executor_rejects_empty_action_chunk():
    result = SafetyExecutor().execute(_chunk([]))

    assert result.executed is False
    assert result.reason == "empty_action_chunk"
    assert result.data["rejected"]["reason"] == "empty_action_chunk"


def test_executor_rejects_invalid_action_dimension():
    result = SafetyExecutor().execute(_chunk([[0.01, 0.0]]))

    assert result.executed is False
    assert result.reason == "invalid_action_dimension_at_step_0"
    assert result.data["rejected"]["expected_dimension"] == 6
    assert result.data["rejected"]["actual_dimension"] == 2


def test_executor_rejects_delta_above_limit():
    executor = SafetyExecutor(SafetyLimits(max_abs_delta=0.05))

    result = executor.execute(_chunk([[0.06, 0.0, 0.0, 0.0, 0.0, 0.0]]))

    assert result.executed is False
    assert result.reason == "action_delta_limit_exceeded_at_step_0"
    assert result.data["rejected"]["actual_value"] == 0.06


def test_executor_rejects_gripper_width_out_of_range():
    result = SafetyExecutor().execute(
        _chunk([[0.01, 0.0, 0.0, 0.0, 0.0, 0.0]], gripper_commands=[90.0])
    )

    assert result.executed is False
    assert result.reason == "gripper_width_out_of_range"
    assert result.data["rejected"]["actual_width_mm"] == 90.0
