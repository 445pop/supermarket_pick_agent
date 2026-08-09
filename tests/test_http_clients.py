import json
from urllib.error import URLError

import pytest

from supermarket_pick_agent.interfaces.navigation import (
    HttpNavigationClient,
    NavigationTarget,

 )
from supermarket_pick_agent.interfaces.vla_pi05 import HttpPi05VLAClient, VLAClientError
from supermarket_pick_agent.models import GripperState, RobotState


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


def test_navigation_http_success(monkeypatch):
    def urlopen(request, timeout):
        return Response(json.dumps({"success": True, "reason": "arrived"}).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    result = HttpNavigationClient("http://127.0.0.1/nav").navigate_to(
        NavigationTarget("shelf")
    )

    assert result.success is True
    assert result.reason == "arrived"


def test_navigation_http_handles_invalid_json(monkeypatch):
    def urlopen(request, timeout):
        return Response(b"not-json")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    result = HttpNavigationClient("http://127.0.0.1/nav").navigate_to(
        NavigationTarget("shelf")
    )

    assert result.success is False
    assert result.reason == "navigation_response_invalid_json"


def test_navigation_http_handles_missing_success(monkeypatch):
    def urlopen(request, timeout):
        return Response(json.dumps({"reason": "arrived"}).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    result = HttpNavigationClient("http://127.0.0.1/nav").navigate_to(
        NavigationTarget("shelf")
    )

    assert result.success is False
    assert result.reason == "navigation_response_missing_success"


def test_navigation_http_handles_network_failure(monkeypatch):
    def urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    result = HttpNavigationClient("http://127.0.0.1/nav").navigate_to(
        NavigationTarget("shelf")
    )

    assert result.success is False
    assert result.reason == "navigation_request_failed"
    assert result.data["error"] == "URLError"


def _generate(client):
    return client.generate_action_chunk(
        kind="grasp",
        product_id="mineral_water",
        skill="water_bottle_grasp_pi05",
        endpoint="",
        image_path="image.png",
        robot_state=RobotState(),
        gripper_state=GripperState(width_mm=75.0, force=0.0),
        prompt="grasp",
    )


def test_vla_http_success(monkeypatch):
    def urlopen(request, timeout):
        body = {"steps": [[0.01, 0, 0, 0, 0, 0]], "gripper_commands": [30.0]}
        return Response(json.dumps(body).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    chunk = _generate(HttpPi05VLAClient("http://127.0.0.1/vla"))

    assert chunk.steps == [[0.01, 0, 0, 0, 0, 0]]
    assert chunk.gripper_commands == [30.0]


def test_vla_http_resolves_skill_uri(monkeypatch):
    captured = {}

    def urlopen(request, timeout):
        captured["url"] = request.full_url
        body = {"steps": [[0.01, 0, 0, 0, 0, 0]], "gripper_commands": [30.0]}
        return Response(json.dumps(body).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    client = HttpPi05VLAClient("http://127.0.0.1:8088")
    client.generate_action_chunk(
        kind="grasp",
        product_id="mineral_water",
        skill="water_bottle_grasp_pi05",
        endpoint="vla://water-bottle-grasp",
        image_path="image.png",
        robot_state=RobotState(),
        gripper_state=GripperState(width_mm=75.0, force=0.0),
        prompt="grasp",
    )

    assert captured["url"] == "http://127.0.0.1:8088/v1/skills/water-bottle-grasp"


def test_vla_http_rejects_invalid_json(monkeypatch):
    def urlopen(request, timeout):
        return Response(b"not-json")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(VLAClientError, match="vla_response_invalid_json"):
        _generate(HttpPi05VLAClient("http://127.0.0.1/vla"))


def test_vla_http_rejects_missing_steps(monkeypatch):
    def urlopen(request, timeout):
        return Response(json.dumps({"gripper_commands": [30.0]}).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(VLAClientError, match="vla_response_missing_steps"):
        _generate(HttpPi05VLAClient("http://127.0.0.1/vla"))


def test_vla_http_handles_network_failure(monkeypatch):
    def urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(VLAClientError, match="vla_request_failed:URLError"):
        _generate(HttpPi05VLAClient("http://127.0.0.1/vla"))
