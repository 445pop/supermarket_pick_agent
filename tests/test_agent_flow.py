from supermarket_pick_agent.config import Settings
from supermarket_pick_agent.main import build_agent


def _local_settings():
    return Settings(
        openai_api_key=None,
        openai_verifier_model="your-vlm-model",
        pi05_endpoint="http://127.0.0.1:8088/v1/action",
        navigation_endpoint="http://127.0.0.1:8090/v1/navigate",
        use_local_adapters=True,
        task_log_dir=None,
    )


def test_local_flow_succeeds_for_mineral_water():
    agent = build_agent(_local_settings())

    result = agent.run("mineral_water")

    assert result.status == "success"
    assert result.product is not None
    assert result.product.product_id == "mineral_water"
    assert result.history[-1].reason == "place_success"


def test_local_flow_succeeds_for_instant_noodle():
    agent = build_agent(_local_settings())

    result = agent.run("instant_noodle")

    assert result.status == "success"
    assert result.product is not None
    assert result.product.product_id == "instant_noodle"
    assert result.history[-1].reason == "place_success"
