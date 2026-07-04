from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .agent import SupermarketPickAgent
from .config import Settings
from .database import ProductDatabase
from .interfaces.navigation import HttpNavigationClient, MockNavigationClient
from .interfaces.openai_verifier import MockVisionVerifier, OpenAIVisionVerifier
from .interfaces.vla_pi05 import HttpPi05VLAClient, MockPi05VLAClient
from .robot.executor import SafetyExecutor
from .tools import AgentTools


def build_agent(settings: Settings) -> SupermarketPickAgent:
    root = Path(__file__).resolve().parents[2]
    product_db = ProductDatabase(root / "data" / "products.json")

    if settings.use_mocks:
        navigation = MockNavigationClient()
        vla = MockPi05VLAClient()
        verifier = MockVisionVerifier()
    else:
        navigation = HttpNavigationClient(settings.navigation_endpoint)
        vla = HttpPi05VLAClient(settings.pi05_endpoint)
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when USE_MOCKS=false")
        verifier = OpenAIVisionVerifier(
            api_key=settings.openai_api_key,
            model=settings.openai_verifier_model,
        )

    tools = AgentTools(
        product_db=product_db,
        navigation=navigation,
        vla=vla,
        verifier=verifier,
        executor=SafetyExecutor(),
    )
    return SupermarketPickAgent(tools)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if load_dotenv:
        load_dotenv()

    user_task = " ".join(sys.argv[1:]).strip() or "帮我拿一瓶矿泉水"
    agent = build_agent(Settings.from_env())
    result = agent.run(user_task)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
