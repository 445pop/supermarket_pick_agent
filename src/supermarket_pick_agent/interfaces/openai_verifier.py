from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Literal, Protocol

from ..models import Product, VerificationResult


VerificationMode = Literal["grasp", "place"]


class VisionVerifier(Protocol):
    def verify(
        self,
        *,
        mode: VerificationMode,
        product: Product,
        before_image_path: str | None,
        after_image_path: str,
    ) -> VerificationResult:
        """Verify grasp/place result from images."""


class MockVisionVerifier:
    def verify(
        self,
        *,
        mode: VerificationMode,
        product: Product,
        before_image_path: str | None,
        after_image_path: str,
    ) -> VerificationResult:
        del before_image_path, after_image_path
        if mode == "grasp":
            return VerificationResult(
                success=True,
                confidence=0.91,
                reason=f"{product.display_name} appears near the gripper",
                target_visible_on_shelf=False,
                target_in_gripper=True,
                raw={"mode": "mock"},
            )
        return VerificationResult(
            success=True,
            confidence=0.93,
            reason=f"{product.display_name} appears in the delivery area",
            target_in_delivery_area=True,
            raw={"mode": "mock"},
        )


class OpenAIVisionVerifier:
    def __init__(self, api_key: str, model: str = "gpt-5.5") -> None:
        self.api_key = api_key
        self.model = model

    def verify(
        self,
        *,
        mode: VerificationMode,
        product: Product,
        before_image_path: str | None,
        after_image_path: str,
    ) -> VerificationResult:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install openai package before using OpenAIVisionVerifier") from exc

        client = OpenAI(api_key=self.api_key)
        prompt = self._build_prompt(mode, product)
        content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
        if before_image_path:
            content.append({"type": "input_text", "text": "Before image:"})
            content.append({"type": "input_image", "image_url": _image_to_data_url(before_image_path)})
        content.append({"type": "input_text", "text": "After image:"})
        content.append({"type": "input_image", "image_url": _image_to_data_url(after_image_path)})

        response = client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": content}],
        )
        text = response.output_text
        data = _parse_json_object(text)

        return VerificationResult(
            success=bool(data.get("success")),
            confidence=float(data.get("confidence", 0.0)),
            reason=str(data.get("reason", "")),
            target_visible_on_shelf=data.get("target_visible_on_shelf"),
            target_in_gripper=data.get("target_in_gripper"),
            target_in_delivery_area=data.get("target_in_delivery_area"),
            raw=data,
        )

    @staticmethod
    def _build_prompt(mode: VerificationMode, product: Product) -> str:
        if mode == "grasp":
            fields = (
                "success, target_visible_on_shelf, target_in_gripper, "
                "gripper_visible, reason, confidence"
            )
            task = "judge whether the target product has been successfully grasped"
        else:
            fields = "success, target_in_delivery_area, reason, confidence"
            task = "judge whether the target product has been placed in the delivery area"

        return (
            "You are a robot task visual verifier. "
            f"Target product: {product.display_name}. "
            f"Appearance hint: {product.appearance}. "
            f"Your task is to {task}. "
            "Return only one JSON object. "
            f"Required fields: {fields}."
        )


def _image_to_data_url(path: str) -> str:
    image_path = Path(path)
    suffix = image_path.suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Verifier did not return JSON: {text}")
    return json.loads(text[start : end + 1])

