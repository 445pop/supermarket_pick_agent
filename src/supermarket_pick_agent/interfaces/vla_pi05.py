from __future__ import annotations

import json
from json import JSONDecodeError
from urllib.parse import urljoin
from urllib.error import URLError
import urllib.request
from dataclasses import asdict
from typing import Protocol

from ..models import ActionKind, GripperState, RobotState, VLAActionChunk


class VLAClientError(RuntimeError):
    pass


class Pi05VLAClient(Protocol):
    def generate_action_chunk(
        self,
        *,
        kind: ActionKind,
        product_id: str,
        skill: str,
        endpoint: str,
        image_path: str,
        robot_state: RobotState,
        gripper_state: GripperState,
        prompt: str,
        failure_context: dict | None = None,
    ) -> VLAActionChunk:
        """Generate a short action chunk with a product-bound pi0.5/VLA skill."""


class LocalPi05VLAClient:
    def generate_action_chunk(
        self,
        *,
        kind: ActionKind,
        product_id: str,
        skill: str,
        endpoint: str,
        image_path: str,
        robot_state: RobotState,
        gripper_state: GripperState,
        prompt: str,
        failure_context: dict | None = None,
    ) -> VLAActionChunk:
        del product_id, image_path, robot_state, gripper_state, failure_context
        if kind == "grasp":
            steps = [[0.02, 0.0, -0.01, 0.0, 0.0, 0.0] for _ in range(5)]
            gripper_commands = [75.0, 60.0, 40.0, 28.0, 28.0]
        else:
            steps = [[0.0, 0.02, -0.01, 0.0, 0.0, 0.0] for _ in range(4)]
            gripper_commands = [28.0, 45.0, 65.0, 75.0]

        return VLAActionChunk(
            kind=kind,
            steps=steps,
            gripper_commands=gripper_commands,
            metadata={
                "mode": "local_adapter",
                "skill": skill,
                "endpoint": endpoint,
                "fixed_prompt": prompt,
            },
        )


class HttpPi05VLAClient:
    def __init__(self, default_endpoint: str, timeout_s: float = 30.0) -> None:
        self.default_endpoint = default_endpoint
        self.timeout_s = timeout_s

    def generate_action_chunk(
        self,
        *,
        kind: ActionKind,
        product_id: str,
        skill: str,
        endpoint: str,
        image_path: str,
        robot_state: RobotState,
        gripper_state: GripperState,
        prompt: str,
        failure_context: dict | None = None,
    ) -> VLAActionChunk:
        payload = {
            "kind": kind,
            "product_id": product_id,
            "vla_skill": skill,
            "image_path": image_path,
            "robot_state": asdict(robot_state),
            "gripper_state": asdict(gripper_state),
            "fixed_prompt": prompt,
            "failure_context": failure_context or {},
        }
        target_endpoint = self._resolve_endpoint(endpoint)
        request = urllib.request.Request(
            target_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except JSONDecodeError as exc:
            raise VLAClientError("vla_response_invalid_json") from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise VLAClientError(f"vla_request_failed:{type(exc).__name__}") from exc

        if not isinstance(body, dict):
            raise VLAClientError("vla_response_invalid_schema")
        if "steps" not in body:
            raise VLAClientError("vla_response_missing_steps")
        if not isinstance(body["steps"], list):
            raise VLAClientError("vla_response_steps_not_list")
        if "gripper_commands" in body and not isinstance(body["gripper_commands"], list):
            raise VLAClientError("vla_response_gripper_commands_not_list")

        return VLAActionChunk(
            kind=kind,
            steps=body["steps"],
            gripper_commands=body.get("gripper_commands", []),
            metadata={
                "skill": skill,
                "endpoint": target_endpoint,
                "fixed_prompt": prompt,
                **body.get("metadata", {}),
            },
        )

    def _resolve_endpoint(self, endpoint: str) -> str:
        if not endpoint:
            return self.default_endpoint
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        if endpoint.startswith("vla://"):
            skill_path = endpoint.removeprefix("vla://").strip("/")
            return urljoin(self.default_endpoint.rstrip("/") + "/", f"v1/skills/{skill_path}")
        return urljoin(self.default_endpoint.rstrip("/") + "/", endpoint.lstrip("/"))
