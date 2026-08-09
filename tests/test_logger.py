import json

from supermarket_pick_agent.logger import TaskLogger
from supermarket_pick_agent.models import Product, TaskResult


def test_task_logger_is_disabled_without_directory():
    result = TaskResult(status="failed", reason="not_started")

    assert TaskLogger(None).write(result) is None


def test_task_logger_writes_result_json(tmp_path):
    product = Product(
        product_id="mineral_water",
        display_name="矿泉水",
        aliases=["水"],
        category="drink",
        stock=1,
        shelf_id="shelf_a",
        approach_point="water_shelf_approach",
        delivery_point="delivery_point",
        appearance="bottle",
        vla_skill="water_bottle_grasp_pi05",
        vla_endpoint="vla://water-bottle-grasp",
        grasp_prompt="grasp",
        place_vla_skill="delivery_area_place_pi05",
        place_vla_endpoint="vla://delivery-area-place",
        place_prompt="place",
    )
    result = TaskResult(status="success", reason="task_completed", product=product)

    output_path = TaskLogger(tmp_path).write(result)

    assert output_path is not None
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["product"]["product_id"] == "mineral_water"
