#!/usr/bin/env python3
"""
Nox API v8.0.0 - AI System Coordinator
Central coordination for all AI/ML components

Orchestrates security monitoring, policy enforcement, biometric authentication,
and distributed AI operations across the multi-node cluster architecture.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Redis and database imports
from redis.cluster import RedisCluster

from .biometric_auth import BiometricAuthenticationSystem, BiometricChallenge
from .policy_engine import (AccessRequest, BiometricType,
                            IntelligentPolicyEngine)
# Import AI components
from .security_monitor import AISecurityMonitor, SecurityEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AISystemStatus(Enum):
    """AI system operational status"""

    ACTIVE = "active"
    LEARNING = "learning"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class DecisionType(Enum):
    """Types of AI-driven decisions"""

    ACCESS_CONTROL = "access_control"
    THREAT_RESPONSE = "threat_response"
    BIOMETRIC_AUTH = "biometric_auth"
    POLICY_UPDATE = "policy_update"


@dataclass
class AIDecision:
    """Comprehensive AI decision result"""

    decision_id: str
    decision_type: DecisionType
    user_id: str
    confidence_score: float
    reasoning: str
    actions_taken: List[str]
    timestamp: datetime
    processing_time_ms: int
    ai_components_used: List[str]
    requires_human_review: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AISystemMetrics:
    """AI system performance metrics"""

    security_threats_detected: int
    policies_generated: int
    biometric_verifications: int
    average_response_time_ms: float
    ml_model_accuracy: float
    system_status: AISystemStatus
    last_updated: datetime
    node_distribution: Dict[str, int]


class AISystemCoordinator:
    """
    Central coordinator for all AI/ML components in the distributed architecture.

    Features:
    - Unified AI decision making across all components
    - Distributed AI state management and synchronization
    - Cross-component data sharing and coordination
    - Comprehensive AI system monitoring and metrics
    - Intelligent escalation and human review triggers
    - Real-time AI model performance optimization
    - Centralized AI configuration and policy management
    """

    def __init__(
        self,
        redis_cluster: RedisCluster = None,
        db_connection_params: Dict[str, Any] = None,
    ):
        """
        Initialize AI System Coordinator.

        Args:
            redis_cluster: Redis cluster connection
            db_connection_params: PostgreSQL connection parameters
        """

        self.redis_cluster = redis_cluster or self._init_redis_cluster()
        self.db_params = db_connection_params or self._load_db_params()

        # Initialize AI components
        self.security_monitor = AISecurityMonitor(
            redis_cluster=self.redis_cluster, db_connection_params=self.db_params
        )

        self.policy_engine = IntelligentPolicyEngine(
            redis_cluster=self.redis_cluster, db_connection_params=self.db_params
        )

        self.biometric_auth = BiometricAuthenticationSystem(
            redis_cluster=self.redis_cluster, db_connection_params=self.db_params
        )

        # AI system configuration
        self.system_status = AISystemStatus.ACTIVE
        self.decision_cache = {}
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes

        # Decision thresholds
        self.high_confidence_threshold = 0.8
        self.human_review_threshold = 0.4
        self.escalation_threshold = 0.3

        # Performance tracking
        self.decision_history = []
        self.max_history_size = 1000

        logger.info("AI System Coordinator initialized successfully")

    def _init_redis_cluster(self) -> RedisCluster:
        """Initialize Redis Cluster connection."""
        startup_nodes = [
            {"host": "localhost", "port": 7001},
            {"host": "localhost", "port": 7002},
            {"host": "localhost", "port": 7003},
        ]

        return RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
            socket_connect_timeout=5,
        )

    def _load_db_params(self) -> Dict[str, Any]:
        """Load database connection parameters from environment."""
        return {
            "host": os.getenv("PG_PRIMARY_HOST", "localhost"),
            "port": int(os.getenv("PG_PRIMARY_PORT", "5432")),
            "database": os.getenv("PG_DATABASE", "nox_api"),
            "user": os.getenv("PG_USERNAME", "nox_user"),
            "password": os.getenv("PG_PASSWORD", "secure_password"),
        }

    async def process_comprehensive_security_request(
        self, user_id: str, request_data: Dict[str, Any]
    ) -> AIDecision:
        """
        Process a comprehensive security request using all AI components.

        Args:
            user_id: User identifier
            request_data: Complete request data including access, biometric, behavioral data

        Returns:
            Comprehensive AI decision
        """

        start_time = time.time()
        decision_id = f"ai_decision_{int(time.time())}_{user_id}"

        try:
            # Extract different types of data from request
            access_request = self._extract_access_request(user_id, request_data)
            security_event = self._extract_security_event(user_id, request_data)
            biometric_data = request_data.get("biometric_data", {})

            # Parallel processing of AI components
            tasks = []
            ai_components_used = []

            # 1. Security threat analysis
            if security_event:
                security_task = asyncio.create_task(
                    self.security_monitor.analyze_security_event(security_event)
                )
                tasks.append(("security", security_task))
                ai_components_used.append("security_monitor")

            # 2. Policy-based access evaluation
            if access_request:
                policy_task = asyncio.create_task(
                    self.policy_engine.evaluate_access_request(access_request)
                )
                tasks.append(("policy", policy_task))
                ai_components_used.append("policy_engine")

            # 3. Biometric verification if required
            # No need to initialize biometric_results here as it's not used
            if biometric_data and "challenge_id" in biometric_data:
                challenge_id = biometric_data["challenge_id"]

                if "face_data" in biometric_data:
                    biometric_task = asyncio.create_task(
                        self.biometric_auth.verify_facial_recognition(
                            challenge_id, biometric_data["face_data"]
                        )
                    )
                    tasks.append(("biometric_face", biometric_task))

                if "voice_data" in biometric_data:
                    biometric_task = asyncio.create_task(
                        self.biometric_auth.verify_voice_recognition(
                            challenge_id, biometric_data["voice_data"]
                        )
                    )
                    tasks.append(("biometric_voice", biometric_task))

                if "behavioral_data" in biometric_data:
                    biometric_task = asyncio.create_task(
                        self.biometric_auth.verify_behavioral_biometrics(
                            challenge_id, biometric_data["behavioral_data"]
                        )
                    )
                    tasks.append(("biometric_behavior", biometric_task))

                if biometric_data:
                    ai_components_used.append("biometric_auth")

            # Wait for all tasks to complete
            results = {}
            for task_name, task in tasks:
                try:
                    result = await task
                    results[task_name] = result
                except Exception as e:
                    logger.error(f"Error in {task_name} task: {e}")
                    results[task_name] = None

            # Aggregate and analyze results
            decision = await self._aggregate_ai_decisions(
                decision_id, user_id, results, ai_components_used, start_time
            )

            # Store decision for learning and audit
            await self._store_ai_decision(decision)

            # Update system metrics
            await self._update_system_metrics(decision, ai_components_used)

            # Add to decision history
            self._add_to_decision_history(decision)

            return decision

        except Exception as e:
            logger.error(f"Error in comprehensive security request processing: {e}")

            # Return error decision
            return AIDecision(
                decision_id=decision_id,
                decision_type=DecisionType.ACCESS_CONTROL,
                user_id=user_id,
                confidence_score=0.0,
                reasoning=f"AI system error: {str(e)}",
                actions_taken=["deny_access", "log_error"],
                timestamp=datetime.utcnow(),
                processing_time_ms=int((time.time() - start_time) * 1000),
                ai_components_used=["error_handler"],
                requires_human_review=True,
                metadata={"error": str(e)},
            )

    def _extract_access_request(
        self, user_id: str, request_data: Dict[str, Any]
    ) -> Optional[AccessRequest]:
        """Extract access request data from comprehensive request."""

        if "access" not in request_data:
            return None

        access_data = request_data["access"]

        return AccessRequest(
            user_id=user_id,
            resource=access_data.get("resource", ""),
            action=access_data.get("action", ""),
            context=access_data.get("context", {}),
            timestamp=datetime.utcnow(),
            ip_address=access_data.get("ip_address", ""),
            user_agent=access_data.get("user_agent", ""),
            session_id=access_data.get("session_id"),
        )

    def _extract_security_event(
        self, user_id: str, request_data: Dict[str, Any]
    ) -> Optional[SecurityEvent]:
        """Extract security event data from comprehensive request."""

        if "security" not in request_data:
            return None

        security_data = request_data["security"]

        return SecurityEvent(
            event_id=f"event_{int(time.time())}",
            user_id=user_id,
            event_type=security_data.get("event_type", "access_attempt"),
            severity=security_data.get("severity", "medium"),
            timestamp=datetime.utcnow(),
            source_ip=security_data.get("source_ip", ""),
            user_agent=security_data.get("user_agent", ""),
            resource_accessed=security_data.get("resource", ""),
            action_attempted=security_data.get("action", ""),
            session_id=security_data.get("session_id"),
            additional_context=security_data.get("context", {}),
        )

    async def _aggregate_ai_decisions(
        self,
        decision_id: str,
        user_id: str,
        results: Dict[str, Any],
        ai_components_used: List[str],
        start_time: float,
    ) -> AIDecision:
        """Aggregate results from multiple AI components into final decision."""

        # Initialize aggregation variables
        confidence_scores = []
        actions_taken = []
        reasoning_parts = []
        requires_human_review = False
        decision_type = DecisionType.ACCESS_CONTROL
        metadata = {}

        # Process security analysis results
        if "security" in results and results["security"]:
            threat_detection = results["security"]
            confidence_scores.append(threat_detection.confidence_score)

            if threat_detection.threat_level == "high":
                actions_taken.extend(["block_access", "alert_security_team"])
                requires_human_review = True
            elif threat_detection.threat_level == "medium":
                actions_taken.append("monitor_closely")

            reasoning_parts.append(
                f"Security analysis: {threat_detection.threat_level} threat level"
            )
            metadata["security_analysis"] = asdict(threat_detection)

        # Process policy engine results
        if "policy" in results and results["policy"]:
            policy_decision = results["policy"]
            confidence_scores.append(policy_decision.confidence_score)

            if policy_decision.decision.value == "deny":
                actions_taken.append("deny_access")
            elif policy_decision.decision.value == "challenge":
                actions_taken.append("require_additional_auth")
            elif policy_decision.decision.value == "allow":
                actions_taken.append("allow_access")

            reasoning_parts.append(f"Policy decision: {policy_decision.decision.value}")
            metadata["policy_decision"] = asdict(policy_decision)

        # Process biometric verification results
        biometric_success_count = 0
        biometric_total_count = 0

        for result_key in ["biometric_face", "biometric_voice", "biometric_behavior"]:
            if result_key in results and results[result_key]:
                biometric_result = results[result_key]
                biometric_total_count += 1

                confidence_scores.append(biometric_result.confidence_score)

                if biometric_result.result.value == "success":
                    biometric_success_count += 1
                elif biometric_result.result.value == "failure":
                    actions_taken.append("biometric_verification_failed")

                reasoning_parts.append(f"{result_key}: {biometric_result.result.value}")
                metadata[result_key] = asdict(biometric_result)

        # Determine overall biometric success
        if biometric_total_count > 0:
            biometric_success_rate = biometric_success_count / biometric_total_count
            if biometric_success_rate >= 0.5:
                actions_taken.append("biometric_verification_passed")
            else:
                actions_taken.append("biometric_verification_insufficient")
                requires_human_review = True

        # Calculate overall confidence score
        overall_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        # Apply confidence-based decision logic
        if overall_confidence >= self.high_confidence_threshold:
            # High confidence - proceed with recommended actions
            if "deny_access" in actions_taken or "block_access" in actions_taken:
                final_actions = ["deny_access", "log_security_event"]
            else:
                final_actions = ["allow_access", "log_access_granted"]
        elif overall_confidence >= self.human_review_threshold:
            # Medium confidence - require additional verification
            final_actions = ["require_additional_verification", "escalate_to_human"]
            requires_human_review = True
        else:
            # Low confidence - deny and escalate
            final_actions = ["deny_access", "escalate_to_security_team"]
            requires_human_review = True

        # Add unique actions from individual components
        final_actions.extend(
            [action for action in actions_taken if action not in final_actions]
        )

        # Generate comprehensive reasoning
        reasoning = f"AI decision (confidence: {overall_confidence:.2f}): " + "; ".join(
            reasoning_parts
        )

        return AIDecision(
            decision_id=decision_id,
            decision_type=decision_type,
            user_id=user_id,
            confidence_score=overall_confidence,
            reasoning=reasoning,
            actions_taken=final_actions,
            timestamp=datetime.utcnow(),
            processing_time_ms=int((time.time() - start_time) * 1000),
            ai_components_used=ai_components_used,
            requires_human_review=requires_human_review,
            metadata=metadata,
        )

    async def create_intelligent_biometric_challenge(
        self, user_id: str, risk_assessment: Dict[str, Any]
    ) -> BiometricChallenge:
        """
        Create intelligent biometric challenge based on risk assessment.

        Args:
            user_id: User identifier
            risk_assessment: Risk factors and context

        Returns:
            Tailored biometric challenge
        """

        # Analyze risk factors to determine required biometric types
        required_types = []

        risk_level = risk_assessment.get("risk_level", "medium")
        threat_indicators = risk_assessment.get("threat_indicators", [])
        user_history = risk_assessment.get("user_history", {})

        # Always require facial recognition for identity verification
        required_types.append(BiometricType.FACIAL_RECOGNITION)

        # Add voice recognition for high-risk scenarios
        if risk_level == "high" or "suspicious_location" in threat_indicators:
            required_types.append(BiometricType.VOICE_RECOGNITION)

        # Add behavioral biometrics for additional security
        if (
            risk_level in ["high", "critical"]
            or "unusual_access_pattern" in threat_indicators
        ):
            required_types.append(BiometricType.BEHAVIORAL_PATTERN)

        # Create the challenge
        challenge = await self.biometric_auth.create_biometric_challenge(
            user_id=user_id,
            required_types=required_types,
            session_id=risk_assessment.get("session_id", "unknown"),
            expires_in_minutes=10 if risk_level == "high" else 15,
        )

        # Log challenge creation
        await self._log_challenge_creation(user_id, challenge, risk_assessment)

        return challenge

    async def get_ai_system_metrics(self) -> AISystemMetrics:
        """Get comprehensive AI system performance metrics."""

        # Check cache first
        cache_key = "ai_system_metrics"

        try:
            cached_metrics = self.redis_cluster.get(cache_key)
            if cached_metrics:
                metrics_data = json.loads(cached_metrics)
                metrics_data["last_updated"] = datetime.fromisoformat(
                    metrics_data["last_updated"]
                )
                return AISystemMetrics(**metrics_data)
        except Exception as e:
            logger.warning(f"Cache access failed: {e}")

        # Calculate current metrics
        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Count security threats detected
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM threat_detections WHERE created_at > %s",
                        (datetime.utcnow() - timedelta(hours=24),),
                    )
                    security_threats = cursor.fetchone()["count"]

                    # Count policies generated
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM policy_decisions WHERE created_by_ai = true AND timestamp > %s",
                        (datetime.utcnow() - timedelta(hours=24),),
                    )
                    policies_generated = cursor.fetchone()["count"]

                    # Count biometric verifications
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM biometric_attempts WHERE timestamp > %s",
                        (datetime.utcnow() - timedelta(hours=24),),
                    )
                    biometric_verifications = cursor.fetchone()["count"]

                    # Calculate average response time
                    cursor.execute(
                        """SELECT AVG(processing_time_ms) as avg_time 
                           FROM (
                               SELECT processing_time_ms FROM ai_decisions WHERE timestamp > %s
                               UNION ALL
                               SELECT processing_time_ms FROM biometric_attempts WHERE timestamp > %s
                           ) combined""",
                        (
                            datetime.utcnow() - timedelta(hours=24),
                            datetime.utcnow() - timedelta(hours=24),
                        ),
                    )
                    avg_response_time = cursor.fetchone()["avg_time"] or 0.0

            # Calculate ML model accuracy (simplified)
            ml_accuracy = self._calculate_model_accuracy()

            # Get node distribution
            node_distribution = await self._get_node_distribution()

            metrics = AISystemMetrics(
                security_threats_detected=security_threats,
                policies_generated=policies_generated,
                biometric_verifications=biometric_verifications,
                average_response_time_ms=float(avg_response_time),
                ml_model_accuracy=ml_accuracy,
                system_status=self.system_status,
                last_updated=datetime.utcnow(),
                node_distribution=node_distribution,
            )

            # Cache the metrics
            try:
                metrics_dict = asdict(metrics)
                metrics_dict["last_updated"] = metrics.last_updated.isoformat()
                self.redis_cluster.setex(
                    cache_key, self.cache_ttl, json.dumps(metrics_dict, default=str)
                )
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")

            return metrics

        except Exception as e:
            logger.error(f"Error calculating AI system metrics: {e}")

            # Return default metrics on error
            return AISystemMetrics(
                security_threats_detected=0,
                policies_generated=0,
                biometric_verifications=0,
                average_response_time_ms=0.0,
                ml_model_accuracy=0.0,
                system_status=AISystemStatus.ERROR,
                last_updated=datetime.utcnow(),
                node_distribution={},
            )

    def _calculate_model_accuracy(self) -> float:
        """Calculate overall ML model accuracy from recent decisions."""

        if not self.decision_history:
            return 0.0

        # Calculate accuracy based on confidence scores and outcomes
        recent_decisions = self.decision_history[-100:]  # Last 100 decisions
        total_confidence = sum(d.confidence_score for d in recent_decisions)

        return total_confidence / len(recent_decisions) if recent_decisions else 0.0

    async def _get_node_distribution(self) -> Dict[str, int]:
        """Get AI workload distribution across cluster nodes."""

        try:
            # Query Redis cluster for node-specific metrics
            node_distribution = {}

            for port in [7001, 7002, 7003]:
                node_key = f"ai_metrics:node:{port}"
                node_data = self.redis_cluster.get(node_key)

                if node_data:
                    metrics = json.loads(node_data)
                    node_distribution[f"node_{port}"] = metrics.get("decision_count", 0)
                else:
                    node_distribution[f"node_{port}"] = 0

            return node_distribution

        except Exception as e:
            logger.error(f"Error getting node distribution: {e}")
            return {"node_7001": 0, "node_7002": 0, "node_7003": 0}

    def _add_to_decision_history(self, decision: AIDecision):
        """Add decision to history for performance tracking."""

        self.decision_history.append(decision)

        # Maintain maximum history size
        if len(self.decision_history) > self.max_history_size:
            self.decision_history = self.decision_history[-self.max_history_size :]

    async def _store_ai_decision(self, decision: AIDecision):
        """Store AI decision in database for audit and learning."""

        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO ai_decisions 
                           (decision_id, decision_type, user_id, confidence_score, reasoning,
                            actions_taken, timestamp, processing_time_ms, ai_components_used,
                            requires_human_review, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            decision.decision_id,
                            decision.decision_type.value,
                            decision.user_id,
                            decision.confidence_score,
                            decision.reasoning,
                            json.dumps(decision.actions_taken),
                            decision.timestamp,
                            decision.processing_time_ms,
                            json.dumps(decision.ai_components_used),
                            decision.requires_human_review,
                            json.dumps(decision.metadata),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Error storing AI decision: {e}")

    async def _update_system_metrics(
        self, decision: AIDecision, ai_components: List[str]
    ):
        """Update system metrics based on latest decision."""

        try:
            # Update node-specific metrics
            current_node = hash(decision.user_id) % 3  # Simple node assignment
            node_port = 7001 + current_node
            node_key = f"ai_metrics:node:{node_port}"

            # Get current node metrics
            node_data = self.redis_cluster.get(node_key)
            if node_data:
                metrics = json.loads(node_data)
            else:
                metrics = {"decision_count": 0, "total_processing_time": 0}

            # Update metrics
            metrics["decision_count"] += 1
            metrics["total_processing_time"] += decision.processing_time_ms
            metrics["last_updated"] = datetime.utcnow().isoformat()

            # Store updated metrics
            self.redis_cluster.setex(node_key, 3600, json.dumps(metrics))  # 1 hour TTL

        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")

    async def _log_challenge_creation(
        self,
        user_id: str,
        challenge: BiometricChallenge,
        risk_assessment: Dict[str, Any],
    ):
        """Log biometric challenge creation for audit."""

        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO biometric_challenges 
                           (challenge_id, user_id, required_types, session_id, 
                            created_at, expires_at, risk_level, context)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            challenge.challenge_id,
                            user_id,
                            json.dumps([t.value for t in challenge.required_types]),
                            challenge.session_id,
                            challenge.created_at,
                            challenge.expires_at,
                            risk_assessment.get("risk_level", "medium"),
                            json.dumps(risk_assessment),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Error logging challenge creation: {e}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_ai_coordinator():
        """Test the AI System Coordinator functionality."""

        # Initialize AI coordinator
        coordinator = AISystemCoordinator()

        # Create comprehensive test request
        test_request_data = {
            "access": {
                "resource": "/api/admin/users",
                "action": "read",
                "context": {"department": "IT"},
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "session_id": "session_123",
            },
            "security": {
                "event_type": "access_attempt",
                "severity": "medium",
                "source_ip": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "resource": "/api/admin/users",
                "action": "read",
                "session_id": "session_123",
                "context": {"unusual_time": True},
            },
            "biometric_data": {
                "challenge_id": "test_challenge_123",
                "face_data": b"mock_face_image_data",
                "behavioral_data": {
                    "keystroke_dynamics": [
                        {"key": "h", "key_down_time": 1000, "key_up_time": 1050}
                    ]
                },
            },
        }

        # Process comprehensive security request
        decision = await coordinator.process_comprehensive_security_request(
            user_id="test_user_123", request_data=test_request_data
        )

        print(f"AI Decision ID: {decision.decision_id}")
        print(f"Decision Type: {decision.decision_type.value}")
        print(f"Confidence Score: {decision.confidence_score:.2f}")
        print(f"Reasoning: {decision.reasoning}")
        print(f"Actions Taken: {', '.join(decision.actions_taken)}")
        print(f"Processing Time: {decision.processing_time_ms}ms")
        print(f"AI Components Used: {', '.join(decision.ai_components_used)}")
        print(f"Requires Human Review: {decision.requires_human_review}")

        # Create intelligent biometric challenge
        risk_assessment = {
            "risk_level": "high",
            "threat_indicators": ["suspicious_location", "unusual_access_pattern"],
            "user_history": {"failed_attempts": 2},
            "session_id": "session_123",
        }

        challenge = await coordinator.create_intelligent_biometric_challenge(
            user_id="test_user_123", risk_assessment=risk_assessment
        )

        print("\nBiometric Challenge Created:")
        print(f"Challenge ID: {challenge.challenge_id}")
        print(f"Required Types: {[t.value for t in challenge.required_types]}")
        print(f"Expires At: {challenge.expires_at}")

        # Get AI system metrics
        metrics = await coordinator.get_ai_system_metrics()

        print("\nAI System Metrics:")
        print(f"Security Threats Detected: {metrics.security_threats_detected}")
        print(f"Policies Generated: {metrics.policies_generated}")
        print(f"Biometric Verifications: {metrics.biometric_verifications}")
        print(f"Average Response Time: {metrics.average_response_time_ms:.2f}ms")
        print(f"ML Model Accuracy: {metrics.ml_model_accuracy:.2f}")
        print(f"System Status: {metrics.system_status.value}")
        print(f"Node Distribution: {metrics.node_distribution}")

    # Run test
    asyncio.run(test_ai_coordinator())
