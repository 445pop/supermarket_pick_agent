from __future__ import annotations

from .models import Observation, Product, TaskResult
from .tools import AgentTools


class SupermarketPickAgent:
    def __init__(self, tools: AgentTools) -> None:
        self.tools = tools

    def run(self, user_task: str) -> TaskResult:
        history: list[Observation] = []

        product_result = self._select_product(user_task)
        if isinstance(product_result, Observation):
            history.append(product_result)
            return TaskResult(status="failed", reason=product_result.reason, history=history)

        product = product_result
        history.append(
            Observation(
                source="query_product_db",
                success=True,
                reason="product_selected",
                data={
                    "product_id": product.product_id,
                    "display_name": product.display_name,
                    "approach_point": product.approach_point,
                    "delivery_point": product.delivery_point,
                    "vla_skill": product.vla_skill,
                    "vla_endpoint": product.vla_endpoint,
                    "fixed_prompt": product.grasp_prompt,
                    "max_retry": product.max_retry,
                },
            )
        )

        nav_obs = self.tools.navigate_to(product.approach_point)
        history.append(nav_obs)
        if not nav_obs.success:
            return TaskResult(status="failed", reason="navigation_to_shelf_failed", product=product, history=history)

        grasp_success = self._try_grasp(product, history)
        if not grasp_success:
            return TaskResult(status="failed", reason="grasp_failed_after_retries", product=product, history=history)

        delivery_obs = self.tools.navigate_to(product.delivery_point)
        history.append(delivery_obs)
        if not delivery_obs.success:
            return TaskResult(status="failed", reason="navigation_to_delivery_failed", product=product, history=history)

        place_success = self._try_place(product, history)
        if not place_success:
            return TaskResult(status="failed", reason="place_failed", product=product, history=history)

        return TaskResult(status="success", reason="task_completed", product=product, history=history)

    def _select_product(self, user_task: str) -> Product | Observation:
        matches = self.tools.query_product_db(user_task)
        available = [product for product in matches if product.stock > 0]
        if not available:
            return Observation(
                source="query_product_db",
                success=False,
                reason="product_not_found_or_out_of_stock",
                data={"user_task": user_task},
            )
        if len(available) > 1:
            return Observation(
                source="query_product_db",
                success=False,
                reason="ambiguous_product",
                data={"candidates": [product.display_name for product in available]},
            )
        return available[0]

    def _try_grasp(self, product: Product, history: list[Observation]) -> bool:
        last_reason = ""
        failure_context: dict | None = None
        for attempt in range(product.max_retry + 1):
            before_image, robot_state, gripper_state = self.tools.capture_observation()
            history.append(
                Observation(
                    source="react_agent",
                    success=True,
                    reason="call_product_vla_grasp",
                    data={
                        "attempt": attempt,
                        "product_id": product.product_id,
                        "vla_skill": product.vla_skill,
                        "vla_endpoint": product.vla_endpoint,
                        "failure_context": failure_context or {},
                    },
                )
            )
            action = self.tools.call_product_vla_grasp(
                product=product,
                image_path=before_image,
                robot_state=robot_state,
                gripper_state=gripper_state,
                failure_context=failure_context,
            )
            execution = self.tools.execute_action_chunk(action)
            history.append(
                Observation(
                    source="executor",
                    success=execution.executed and not execution.safe_stop,
                    reason=execution.reason,
                    data={"attempt": attempt, "kind": "grasp", **execution.data},
                )
            )
            if not execution.executed or execution.safe_stop:
                last_reason = execution.reason
                break

            after_image, _, _ = self.tools.capture_observation()
            verification = self.tools.verify_grasp(
                product=product,
                before_image_path=before_image,
                after_image_path=after_image,
            )
            fused_success = (
                verification.success
                and verification.confidence >= 0.70
                and execution.gripper_state.width_mm > 5.0
            )
            history.append(
                Observation(
                    source="observation_fusion",
                    success=fused_success,
                    reason="grasp_success" if fused_success else "grasp_failed",
                    data={
                        "attempt": attempt,
                        "verifier_reason": verification.reason,
                        "confidence": verification.confidence,
                        "target_in_gripper": verification.target_in_gripper,
                        "target_visible_on_shelf": verification.target_visible_on_shelf,
                        "gripper_width_mm": execution.gripper_state.width_mm,
                        "executor_status": execution.reason,
                        "next_recommended_action": "continue" if fused_success else "reobserve_and_retry",
                    },
                )
            )
            if fused_success:
                return True
            last_reason = verification.reason
            failure_context = {
                "last_reason": last_reason,
                "target_visible_on_shelf": verification.target_visible_on_shelf,
                "target_in_gripper": verification.target_in_gripper,
                "gripper_width_mm": execution.gripper_state.width_mm,
                "recovery_policy": "reobserve_adjust_view_retry_same_product_endpoint",
            }
            if attempt < product.max_retry:
                history.append(
                    Observation(
                        source="react_agent",
                        success=True,
                        reason="reobserve_and_retry_same_product_endpoint",
                        data={
                            "next_endpoint": product.vla_endpoint,
                            "next_skill": product.vla_skill,
                            "failure_context": failure_context,
                        },
                    )
                )

        history.append(
            Observation(
                source="react_agent",
                success=False,
                reason="max_grasp_retry_exceeded",
                data={"last_reason": last_reason},
            )
        )
        return False

    def _try_place(self, product: Product, history: list[Observation]) -> bool:
        image, robot_state, gripper_state = self.tools.capture_observation()
        history.append(
            Observation(
                source="react_agent",
                success=True,
                reason="call_product_vla_place",
                data={
                    "product_id": product.product_id,
                    "vla_skill": product.place_vla_skill,
                    "vla_endpoint": product.place_vla_endpoint,
                },
            )
        )
        action = self.tools.call_product_vla_place(
            product=product,
            image_path=image,
            robot_state=robot_state,
            gripper_state=gripper_state,
        )
        execution = self.tools.execute_action_chunk(action)
        history.append(
            Observation(
                source="executor",
                success=execution.executed and not execution.safe_stop,
                reason=execution.reason,
                data={"kind": "place", **execution.data},
            )
        )
        if not execution.executed:
            return False

        after_image, _, _ = self.tools.capture_observation()
        verification = self.tools.verify_place(
            product=product,
            before_image_path=image,
            after_image_path=after_image,
        )
        success = verification.success and verification.confidence >= 0.70
        history.append(
            Observation(
                source="observation_fusion",
                success=success,
                reason="place_success" if success else "place_failed",
                data={
                    "verifier_reason": verification.reason,
                    "confidence": verification.confidence,
                    "target_in_delivery_area": verification.target_in_delivery_area,
                    "executor_status": execution.reason,
                },
            )
        )
        return success
