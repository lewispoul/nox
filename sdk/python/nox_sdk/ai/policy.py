#!/usr/bin/env python3
"""
Nox API Python SDK - AI Policy Client
v8.0.0 Developer Experience Enhancement

AI-powered policy engine integration for intelligent access control,
dynamic policy enforcement, and adaptive security policies.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    """Policy action types."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_MFA = "require_mfa"
    REQUIRE_APPROVAL = "require_approval"
    LOG_AND_CONTINUE = "log_and_continue"
    CHALLENGE = "challenge"


class PolicyCondition(Enum):
    """Policy condition types."""

    TIME_BASED = "time_based"
    LOCATION_BASED = "location_based"
    RISK_BASED = "risk_based"
    ROLE_BASED = "role_based"
    BEHAVIORAL = "behavioral"
    RESOURCE_BASED = "resource_based"


@dataclass
class PolicyRule:
    """Policy rule definition."""

    rule_id: str
    name: str
    description: str
    action: PolicyAction
    conditions: List[Dict[str, Any]]
    priority: int = 100
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class PolicyEvaluation:
    """Policy evaluation result."""

    decision: PolicyAction
    matched_rules: List[str]
    confidence_score: float
    evaluation_time_ms: float
    additional_requirements: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class PolicyContext:
    """Context for policy evaluation."""

    user_id: str
    resource: str
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


class PolicyClient:
    """
    AI Policy client for intelligent access control and policy management.

    Integrates with the AI Policy Engine to provide:
    - Dynamic policy evaluation
    - Adaptive security policies
    - Context-aware access control
    - Policy analytics and recommendations
    """

    def __init__(self, main_client):
        """
        Initialize policy client.

        Args:
            main_client: Main NoxClient instance
        """
        self.client = main_client
        self.policy_cache: Dict[str, PolicyRule] = {}
        self.evaluation_history: List[PolicyEvaluation] = []
        self.max_history_size = 200

        logger.info("AI Policy client initialized")

    async def evaluate_policy(
        self, context: PolicyContext
    ) -> Optional[PolicyEvaluation]:
        """
        Evaluate policies for a given context.

        Args:
            context: Policy evaluation context

        Returns:
            Policy evaluation result or None
        """

        try:
            # Prepare context data
            context_data = asdict(context)
            if not context_data.get("timestamp"):
                context_data["timestamp"] = datetime.utcnow().isoformat()

            # Send to AI policy engine
            response = await self.client.post(
                "/api/ai/policy/evaluate", data=context_data
            )

            if response.success and response.data:
                evaluation = PolicyEvaluation(
                    decision=PolicyAction(response.data.get("decision", "allow")),
                    matched_rules=response.data.get("matched_rules", []),
                    confidence_score=response.data.get("confidence_score", 0.0),
                    evaluation_time_ms=response.response_time_ms or 0.0,
                    additional_requirements=response.data.get(
                        "additional_requirements"
                    ),
                    context=response.data.get("context"),
                )

                # Add to history
                self._add_to_history(evaluation)

                return evaluation

            return None

        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            return None

    async def create_policy_rule(self, rule: PolicyRule) -> bool:
        """
        Create a new policy rule.

        Args:
            rule: Policy rule to create

        Returns:
            True if rule created successfully
        """

        try:
            rule_data = asdict(rule)
            rule_data["action"] = rule.action.value

            response = await self.client.post("/api/ai/policy/rules", data=rule_data)

            if response.success:
                # Update cache
                self.policy_cache[rule.rule_id] = rule
                logger.info(f"Policy rule created: {rule.rule_id}")
                return True

            logger.warning(f"Failed to create policy rule: {rule.rule_id}")
            return False

        except Exception as e:
            logger.error(f"Error creating policy rule: {e}")
            return False

    async def update_policy_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing policy rule.

        Args:
            rule_id: Rule ID to update
            updates: Updates to apply

        Returns:
            True if rule updated successfully
        """

        try:
            response = await self.client.put(
                f"/api/ai/policy/rules/{rule_id}", data=updates
            )

            if response.success:
                # Update cache if exists
                if rule_id in self.policy_cache:
                    rule = self.policy_cache[rule_id]
                    for key, value in updates.items():
                        if hasattr(rule, key):
                            setattr(rule, key, value)

                logger.info(f"Policy rule updated: {rule_id}")
                return True

            logger.warning(f"Failed to update policy rule: {rule_id}")
            return False

        except Exception as e:
            logger.error(f"Error updating policy rule: {e}")
            return False

    async def delete_policy_rule(self, rule_id: str) -> bool:
        """
        Delete a policy rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if rule deleted successfully
        """

        try:
            response = await self.client.delete(f"/api/ai/policy/rules/{rule_id}")

            if response.success:
                # Remove from cache
                self.policy_cache.pop(rule_id, None)
                logger.info(f"Policy rule deleted: {rule_id}")
                return True

            logger.warning(f"Failed to delete policy rule: {rule_id}")
            return False

        except Exception as e:
            logger.error(f"Error deleting policy rule: {e}")
            return False

    async def get_policy_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """
        Get a policy rule by ID.

        Args:
            rule_id: Rule ID to retrieve

        Returns:
            Policy rule or None
        """

        # Check cache first
        if rule_id in self.policy_cache:
            return self.policy_cache[rule_id]

        try:
            response = await self.client.get(f"/api/ai/policy/rules/{rule_id}")

            if response.success and response.data:
                rule = PolicyRule(
                    rule_id=response.data["rule_id"],
                    name=response.data["name"],
                    description=response.data["description"],
                    action=PolicyAction(response.data["action"]),
                    conditions=response.data["conditions"],
                    priority=response.data.get("priority", 100),
                    enabled=response.data.get("enabled", True),
                    created_at=response.data.get("created_at"),
                    updated_at=response.data.get("updated_at"),
                )

                # Update cache
                self.policy_cache[rule_id] = rule
                return rule

            return None

        except Exception as e:
            logger.error(f"Failed to get policy rule: {e}")
            return None

    async def list_policy_rules(
        self, enabled_only: bool = True, priority_min: Optional[int] = None
    ) -> List[PolicyRule]:
        """
        List policy rules.

        Args:
            enabled_only: Only return enabled rules
            priority_min: Minimum priority filter

        Returns:
            List of policy rules
        """

        try:
            params = {}
            if enabled_only:
                params["enabled"] = "true"
            if priority_min is not None:
                params["priority_min"] = str(priority_min)

            response = await self.client.get("/api/ai/policy/rules", params=params)

            if response.success and response.data:
                rules = []
                for rule_data in response.data.get("rules", []):
                    rule = PolicyRule(
                        rule_id=rule_data["rule_id"],
                        name=rule_data["name"],
                        description=rule_data["description"],
                        action=PolicyAction(rule_data["action"]),
                        conditions=rule_data["conditions"],
                        priority=rule_data.get("priority", 100),
                        enabled=rule_data.get("enabled", True),
                        created_at=rule_data.get("created_at"),
                        updated_at=rule_data.get("updated_at"),
                    )
                    rules.append(rule)

                    # Update cache
                    self.policy_cache[rule.rule_id] = rule

                return rules

            return []

        except Exception as e:
            logger.error(f"Failed to list policy rules: {e}")
            return []

    async def test_policy_rule(
        self, rule_id: str, context: PolicyContext
    ) -> Optional[Dict[str, Any]]:
        """
        Test a policy rule against a context.

        Args:
            rule_id: Rule ID to test
            context: Test context

        Returns:
            Test results or None
        """

        try:
            test_data = {"rule_id": rule_id, "context": asdict(context)}

            response = await self.client.post("/api/ai/policy/test", data=test_data)

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to test policy rule: {e}")
            return None

    async def get_policy_recommendations(
        self, user_id: str, analysis_period: str = "7d"
    ) -> List[Dict[str, Any]]:
        """
        Get AI-powered policy recommendations.

        Args:
            user_id: User ID for recommendations
            analysis_period: Analysis period (1d, 7d, 30d)

        Returns:
            List of policy recommendations
        """

        try:
            params = {"user_id": user_id, "period": analysis_period}

            response = await self.client.get(
                "/api/ai/policy/recommendations", params=params
            )

            if response.success and response.data:
                return response.data.get("recommendations", [])

            return []

        except Exception as e:
            logger.error(f"Failed to get policy recommendations: {e}")
            return []

    async def analyze_policy_violations(
        self, time_range: str = "24h"
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze policy violations using AI.

        Args:
            time_range: Time range for analysis

        Returns:
            Violation analysis or None
        """

        try:
            response = await self.client.get(
                "/api/ai/policy/violations/analyze", params={"range": time_range}
            )

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to analyze policy violations: {e}")
            return None

    async def create_adaptive_policy(
        self, base_rule: PolicyRule, adaptation_config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create an adaptive policy that learns from behavior.

        Args:
            base_rule: Base policy rule
            adaptation_config: Adaptation configuration

        Returns:
            Adaptive policy ID or None
        """

        try:
            adaptive_data = {
                "base_rule": asdict(base_rule),
                "adaptation_config": adaptation_config,
            }
            adaptive_data["base_rule"]["action"] = base_rule.action.value

            response = await self.client.post(
                "/api/ai/policy/adaptive", data=adaptive_data
            )

            if response.success and response.data:
                policy_id = response.data.get("policy_id")
                logger.info(f"Adaptive policy created: {policy_id}")
                return policy_id

            return None

        except Exception as e:
            logger.error(f"Failed to create adaptive policy: {e}")
            return None

    async def get_policy_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get policy system metrics.

        Returns:
            Policy metrics or None
        """

        try:
            response = await self.client.get("/api/ai/policy/metrics")

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to get policy metrics: {e}")
            return None

    async def export_policies(self, format_type: str = "json") -> Optional[str]:
        """
        Export all policies.

        Args:
            format_type: Export format (json, yaml)

        Returns:
            Export data or None
        """

        try:
            response = await self.client.get(
                "/api/ai/policy/export", params={"format": format_type}
            )

            if response.success:
                return response.raw_content

            return None

        except Exception as e:
            logger.error(f"Failed to export policies: {e}")
            return None

    async def import_policies(
        self, policy_data: str, format_type: str = "json"
    ) -> bool:
        """
        Import policies from data.

        Args:
            policy_data: Policy data to import
            format_type: Data format (json, yaml)

        Returns:
            True if import successful
        """

        try:
            import_data = {"data": policy_data, "format": format_type}

            response = await self.client.post("/api/ai/policy/import", data=import_data)

            if response.success:
                # Clear cache to force refresh
                self.policy_cache.clear()
                logger.info("Policies imported successfully")
                return True

            logger.warning("Failed to import policies")
            return False

        except Exception as e:
            logger.error(f"Error importing policies: {e}")
            return False

    def _add_to_history(self, evaluation: PolicyEvaluation):
        """Add policy evaluation to history."""
        self.evaluation_history.append(evaluation)

        # Maintain max history size
        if len(self.evaluation_history) > self.max_history_size:
            self.evaluation_history = self.evaluation_history[-self.max_history_size :]

    def get_evaluation_history(self) -> List[PolicyEvaluation]:
        """Get policy evaluation history."""
        return self.evaluation_history.copy()

    def get_policy_statistics(self) -> Dict[str, Any]:
        """Get policy evaluation statistics."""
        if not self.evaluation_history:
            return {
                "total_evaluations": 0,
                "decision_breakdown": {},
                "average_confidence": 0.0,
                "average_evaluation_time": 0.0,
            }

        # Calculate statistics
        decisions = {}
        total_confidence = 0.0
        total_time = 0.0

        for evaluation in self.evaluation_history:
            # Count decisions
            decision = evaluation.decision.value
            decisions[decision] = decisions.get(decision, 0) + 1

            # Sum confidence and time
            total_confidence += evaluation.confidence_score
            total_time += evaluation.evaluation_time_ms

        return {
            "total_evaluations": len(self.evaluation_history),
            "decision_breakdown": decisions,
            "average_confidence": total_confidence / len(self.evaluation_history),
            "average_evaluation_time": total_time / len(self.evaluation_history),
        }
