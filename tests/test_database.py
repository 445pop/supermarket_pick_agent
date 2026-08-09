import json

from supermarket_pick_agent.database import ProductDatabase


def _product(product_id, display_name, aliases, stock=1):
    return {
        "product_id": product_id,
        "display_name": display_name,
        "aliases": aliases,
        "category": "test",
        "stock": stock,
        "shelf_id": "shelf",
        "approach_point": "approach",
        "delivery_point": "delivery",
        "appearance": "package",
        "vla_skill": f"{product_id}_grasp_pi05",
        "vla_endpoint": f"vla://{product_id}",
        "grasp_prompt": "grasp target",
        "place_vla_skill": "delivery_area_place_pi05",
        "place_vla_endpoint": "vla://delivery-area-place",
        "place_prompt": "place target",
        "max_retry": 2,
    }


def test_query_returns_unique_match(tmp_path):
    products_path = tmp_path / "products.json"
    products_path.write_text(
        json.dumps([_product("water", "矿泉水", ["水"])]), encoding="utf-8"
    )
    database = ProductDatabase(products_path)

    matches = database.query("矿泉水")

    assert [product.product_id for product in matches] == ["water"]


def test_query_can_return_ambiguous_matches(tmp_path):
    products_path = tmp_path / "products.json"
    products_path.write_text(
        json.dumps(
            [
                _product("water", "矿泉水", ["饮品"]),
                _product("tea", "茶饮", ["饮品"]),
            ]
        ),
        encoding="utf-8",
    )
    database = ProductDatabase(products_path)

    matches = database.query("饮品")

    assert {product.product_id for product in matches} == {"water", "tea"}


def test_query_returns_empty_for_missing_product(tmp_path):
    products_path = tmp_path / "products.json"
    products_path.write_text(
        json.dumps([_product("water", "矿泉水", ["水"])]), encoding="utf-8"
    )
    database = ProductDatabase(products_path)

    assert database.query("咖啡") == []
