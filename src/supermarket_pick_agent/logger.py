from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import TaskResult


class TaskLogger:
    def __init__(self, log_dir: str | Path | None) -> None:
        self.log_dir = Path(log_dir) if log_dir else None

    @property
    def enabled(self) -> bool:
        return self.log_dir is not None

    def write(self, result: TaskResult) -> Path | None:
        if self.log_dir is None:
            return None

        self.log_dir.mkdir(parents=True, exist_ok=True)
        product_id = result.product.product_id if result.product else "unknown"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = self.log_dir / f"{timestamp}-{product_id}.json"
        output_path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path
