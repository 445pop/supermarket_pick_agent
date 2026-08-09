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
from .interfaces.navigation import HttpNavigationClient, LocalNavigationClient
from .interfaces.observation import LocalObservationProvider
from .interfaces.openai_verifier import LocalVisionVerifier, OpenAIVisionVerifier
from .interfaces.vla_pi05 import HttpPi05VLAClient, LocalPi05VLAClient
from .logger import TaskLogger
from .robot.executor import SafetyExecutor
from .tools import AgentTools


def build_agent(settings: Settings) -> SupermarketPickAgent:
    settings.validate()
    root = Path(__file__).resolve().parents[2]
    product_db = ProductDatabase(root / "data" / "products.json")
    observation_provider = LocalObservationProvider(root / "data" / "current_observation.png")

    if settings.use_local_adapters:
        navigation = LocalNavigationClient()
        vla = LocalPi05VLAClient()
        verifier = LocalVisionVerifier()
    else:
        navigation = HttpNavigationClient(settings.navigation_endpoint)
        vla = HttpPi05VLAClient(settings.pi05_endpoint)
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when USE_LOCAL_ADAPTERS=false")
        verifier = OpenAIVisionVerifier(
            api_key=settings.openai_api_key,
            model=settings.openai_verifier_model,
        )

    tools = AgentTools(
        product_db=product_db,
        navigation=navigation,
        observation_provider=observation_provider,
        vla=vla,
        verifier=verifier,
        executor=SafetyExecutor(),
    )
    return SupermarketPickAgent(tools)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if load_dotenv:
        load_dotenv()

    if argv and argv[0] in {"-h", "--help"}:
        print("Usage: supermarket-pick-agent [product_id|task text]")
        return 0

    user_task = " ".join(argv).strip() or "帮我拿一瓶矿泉水"
    try:
        agent = build_agent(Settings.from_env())
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    result = agent.run(user_task)
    TaskLogger(Settings.from_env().task_log_dir).write(result)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
