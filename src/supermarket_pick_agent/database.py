from __future__ import annotations

import json
from pathlib import Path

from .models import Product


class ProductDatabase:
    def __init__(self, products_path: Path) -> None:
        self.products_path = products_path
        self.products = self._load_products(products_path)

    def query(self, keyword: str) -> list[Product]:
        normalized = keyword.strip().lower()
        if not normalized:
            return []

        matches: list[Product] = []
        for product in self.products:
            fields = [product.display_name, product.product_id, product.category, *product.aliases]
            if any(normalized in field.lower() or field.lower() in normalized for field in fields):
                matches.append(product)
        return matches

    @staticmethod
    def _load_products(path: Path) -> list[Product]:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return [Product(**row) for row in rows]

