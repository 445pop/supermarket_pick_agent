from __future__ import annotations

from pathlib import Path

from .database import ProductDatabase
from .interfaces.navigation import NavigationClient, NavigationTarget
from .interfaces.openai_verifier import VisionVerifier
from .interfaces.vla_pi05 import Pi05VLAClient
from .models import (
    ExecutionResult,
    GripperState,
    Observation,
    Product,
    RobotState,
    VerificationResult,
    VLAActionChunk,
)
from .robot.executor import SafetyExecutor


class AgentTools:
    def __init__(
        self,
        *,
        product_db: ProductDatabase,
        navigation: NavigationClient,
        vla: Pi05VLAClient,
        verifier: VisionVerifier,
        executor: SafetyExecutor,
    ) -> None:
        self.product_db = product_db
        self.navigation = navigation
        self.vla = vla
        self.verifier = verifier
        self.executor = executor

    def query_product_db(self, keyword: str) -> list[Product]:
        return self.product_db.query(keyword)

    def navigate_to(self, point: str) -> Observation:
        return self.navigation.navigate_to(NavigationTarget(point=point))

    def capture_observation(self) -> tuple[str, RobotState, GripperState]:
        image_path = str(Path(__file__).resolve().parents[2] / "data" / "mock_after.png")
        robot_state = RobotState()
        gripper_state = GripperState(width_mm=75.0, force=0.0)
        return image_path, robot_state, gripper_state

    def call_product_vla_grasp(
        self,
        *,
        product: Product,
        image_path: str,
        robot_state: RobotState,
        gripper_state: GripperState,
        failure_context: dict | None = None,
    ) -> VLAActionChunk:
        return self.vla.generate_action_chunk(
            kind="grasp",
            product_id=product.product_id,
            skill=product.vla_skill,
            endpoint=product.vla_endpoint,
            image_path=image_path,
            robot_state=robot_state,
            gripper_state=gripper_state,
            prompt=product.grasp_prompt,
            failure_context=failure_context,
        )

    def call_product_vla_place(
        self,
        *,
        product: Product,
        image_path: str,
        robot_state: RobotState,
        gripper_state: GripperState,
        failure_context: dict | None = None,
    ) -> VLAActionChunk:
        return self.vla.generate_action_chunk(
            kind="place",
            product_id=product.product_id,
            skill=product.place_vla_skill,
            endpoint=product.place_vla_endpoint,
            image_path=image_path,
            robot_state=robot_state,
            gripper_state=gripper_state,
            prompt=product.place_prompt,
            failure_context=failure_context,
        )

    def execute_action_chunk(self, chunk: VLAActionChunk) -> ExecutionResult:
        return self.executor.execute(chunk)

    def verify_grasp(
        self,
        *,
        product: Product,
        before_image_path: str | None,
        after_image_path: str,
    ) -> VerificationResult:
        return self.verifier.verify(
            mode="grasp",
            product=product,
            before_image_path=before_image_path,
            after_image_path=after_image_path,
        )

    def verify_place(
        self,
        *,
        product: Product,
        before_image_path: str | None,
        after_image_path: str,
    ) -> VerificationResult:
        return self.verifier.verify(
            mode="place",
            product=product,
            before_image_path=before_image_path,
            after_image_path=after_image_path,
        )
