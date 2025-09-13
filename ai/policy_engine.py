#!/usr/bin/env python3
"""
Nox API v8.0.0 - Intelligent Policy Engine
AI-driven access policy generation and optimization

Provides dynamic policy generation based on user behavior patterns,
intelligent role recommendations, and context-aware access controls
for the distributed multi-node architecture.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

# Redis and database imports
from redis.cluster import RedisCluster
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """Types of access policies"""

    ROLE_BASED = "role_based"
    ATTRIBUTE_BASED = "attribute_based"
    TIME_BASED = "time_based"
    LOCATION_BASED = "location_based"
    RISK_BASED = "risk_based"
    RESOURCE_BASED = "resource_based"


class AccessDecision(Enum):
    """Access control decisions"""

    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"  # Require additional authentication
    MONITOR = "monitor"  # Allow but monitor closely


@dataclass
class PolicyRule:
    """Individual policy rule definition"""

    rule_id: str
    condition: str
    action: AccessDecision
    priority: int
    confidence_score: float
    created_by_ai: bool
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AccessRequest:
    """Access request for policy evaluation"""

    user_id: str
    resource: str
    action: str
    context: Dict[str, Any]
    timestamp: datetime
    ip_address: str
    user_agent: str
    session_id: Optional[str] = None


@dataclass
class PolicyDecision:
    """Policy evaluation result"""

    decision: AccessDecision
    confidence_score: float
    applied_rules: List[str]
    reasoning: str
    risk_factors: List[str]
    additional_requirements: Optional[Dict[str, Any]] = None


@dataclass
class UserAccessProfile:
    """User's access pattern profile for ML analysis"""

    user_id: str
    typical_resources: List[str]
    access_frequency: Dict[str, int]
    preferred_hours: List[int]
    common_locations: List[str]
    role_recommendations: List[str]
    risk_indicators: List[str]
    last_updated: datetime


class IntelligentPolicyEngine:
    """
    AI-powered policy engine for dynamic access control.

    Features:
    - Machine learning-based policy generation
    - Real-time access decision making
    - Dynamic role recommendations
    - Context-aware policy enforcement
    - Risk-based access controls
    - Policy optimization based on outcomes
    """

    def __init__(
        self,
        redis_cluster: RedisCluster = None,
        db_connection_params: Dict[str, Any] = None,
    ):
        """
        Initialize Intelligent Policy Engine.

        Args:
            redis_cluster: Redis cluster connection
            db_connection_params: PostgreSQL connection parameters
        """

        self.redis_cluster = redis_cluster or self._init_redis_cluster()
        self.db_params = db_connection_params or self._load_db_params()

        # ML Models for policy decisions
        self.decision_model = None
        self.role_recommender = None
        self.risk_classifier = None
        self.access_clusterer = None

        # Feature encoders and scalers
        self.label_encoders = {}
        self.feature_scaler = StandardScaler()

        # Policy configuration
        self.default_policy_ttl = 86400  # 24 hours
        self.min_confidence_threshold = 0.7
        self.risk_threshold = 0.6

        # Initialize ML models
        self._initialize_models()

        # Cache for policies and user profiles
        self.policy_cache = {}
        self.user_profile_cache = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info("Intelligent Policy Engine initialized successfully")

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

    def _initialize_models(self):
        """Initialize and load ML models for policy decisions."""

        try:
            # Initialize decision tree for access decisions
            self.decision_model = DecisionTreeClassifier(
                max_depth=10, min_samples_split=5, random_state=42
            )

            # Initialize random forest for role recommendations
            self.role_recommender = RandomForestClassifier(
                n_estimators=50, max_depth=8, random_state=42
            )

            # Initialize classifier for risk assessment
            self.risk_classifier = DecisionTreeClassifier(
                max_depth=6, min_samples_split=10, random_state=42
            )

            # Initialize clustering for access pattern analysis
            self.access_clusterer = KMeans(n_clusters=5, random_state=42)

            # Try to load existing trained models
            model_dir = "/tmp/nox_policy_models/"
            os.makedirs(model_dir, exist_ok=True)

            model_files = {
                "decision_model": "decision_model.pkl",
                "role_recommender": "role_recommender.pkl",
                "risk_classifier": "risk_classifier.pkl",
                "access_clusterer": "access_clusterer.pkl",
                "feature_scaler": "feature_scaler.pkl",
            }

            models_loaded = 0
            for model_name, filename in model_files.items():
                filepath = os.path.join(model_dir, filename)
                if os.path.exists(filepath):
                    try:
                        model = joblib.load(filepath)
                        setattr(self, model_name, model)
                        models_loaded += 1
                        logger.info(f"Loaded existing {model_name}")
                    except Exception as e:
                        logger.warning(f"Failed to load {model_name}: {e}")

            # Initialize with dummy data if no models loaded
            if models_loaded == 0:
                await self._initialize_with_dummy_data()

            logger.info(
                f"Policy engine initialized with {models_loaded} pre-trained models"
            )

        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            await self._initialize_with_dummy_data()

    async def _initialize_with_dummy_data(self):
        """Initialize models with dummy data for cold start."""

        try:
            # Create dummy training data
            n_samples = 1000
            n_features = 15

            # Generate synthetic access request features
            X = np.random.rand(n_samples, n_features)

            # Generate synthetic decisions (allow=1, deny=0, challenge=2)
            y_decisions = np.random.choice([0, 1, 2], n_samples, p=[0.2, 0.7, 0.1])

            # Generate synthetic roles (5 different roles)
            y_roles = np.random.choice([0, 1, 2, 3, 4], n_samples)

            # Generate synthetic risk levels (low=0, medium=1, high=2)
            y_risk = np.random.choice([0, 1, 2], n_samples, p=[0.6, 0.3, 0.1])

            # Train models
            self.feature_scaler.fit(X)
            X_scaled = self.feature_scaler.transform(X)

            self.decision_model.fit(X_scaled, y_decisions)
            self.role_recommender.fit(X_scaled, y_roles)
            self.risk_classifier.fit(X_scaled, y_risk)
            self.access_clusterer.fit(X_scaled)

            logger.info("Initialized models with synthetic training data")

        except Exception as e:
            logger.error(f"Error initializing models with dummy data: {e}")

    async def evaluate_access_request(self, request: AccessRequest) -> PolicyDecision:
        """
        Evaluate an access request and make a policy decision.

        Args:
            request: Access request to evaluate

        Returns:
            Policy decision with reasoning
        """

        try:
            # Get user access profile
            user_profile = await self._get_user_access_profile(request.user_id)

            # Extract features from the request
            features = await self._extract_request_features(request, user_profile)

            if not features:
                return PolicyDecision(
                    decision=AccessDecision.DENY,
                    confidence_score=0.0,
                    applied_rules=["default_deny"],
                    reasoning="Unable to extract request features",
                    risk_factors=["feature_extraction_failed"],
                )

            # Scale features
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.feature_scaler.transform(features_array)

            # Get ML model predictions
            decision_probs = self.decision_model.predict_proba(features_scaled)[0]
            risk_probs = self.risk_classifier.predict_proba(features_scaled)[0]

            # Make primary access decision
            decision_idx = np.argmax(decision_probs)
            decision_confidence = decision_probs[decision_idx]

            decision_mapping = {
                0: AccessDecision.DENY,
                1: AccessDecision.ALLOW,
                2: AccessDecision.CHALLENGE,
            }
            primary_decision = decision_mapping.get(decision_idx, AccessDecision.DENY)

            # Assess risk level
            risk_level = np.argmax(risk_probs)
            risk_confidence = risk_probs[risk_level]
            _risk_labels = ["low", "medium", "high"]

            # Apply risk-based modifications
            final_decision, risk_factors = await self._apply_risk_based_adjustments(
                primary_decision,
                decision_confidence,
                risk_level,
                risk_confidence,
                request,
            )

            # Get applicable policy rules
            applied_rules = await self._get_applicable_rules(request, user_profile)

            # Generate reasoning
            reasoning = self._generate_decision_reasoning(
                final_decision, decision_confidence, risk_level, applied_rules
            )

            # Determine additional requirements if needed
            additional_requirements = None
            if final_decision == AccessDecision.CHALLENGE:
                additional_requirements = await self._determine_challenge_requirements(
                    request, risk_level, user_profile
                )

            policy_decision = PolicyDecision(
                decision=final_decision,
                confidence_score=decision_confidence,
                applied_rules=applied_rules,
                reasoning=reasoning,
                risk_factors=risk_factors,
                additional_requirements=additional_requirements,
            )

            # Log the decision for learning
            await self._log_policy_decision(request, policy_decision)

            return policy_decision

        except Exception as e:
            logger.error(f"Error evaluating access request: {e}")
            return PolicyDecision(
                decision=AccessDecision.DENY,
                confidence_score=0.0,
                applied_rules=["error_fallback"],
                reasoning=f"Policy evaluation error: {str(e)}",
                risk_factors=["system_error"],
            )

    async def _extract_request_features(
        self, request: AccessRequest, user_profile: UserAccessProfile
    ) -> Optional[List[float]]:
        """Extract numerical features from access request."""

        try:
            # Time-based features
            hour_of_day = request.timestamp.hour
            day_of_week = request.timestamp.weekday()

            # User behavior features
            resource_familiarity = (
                1.0 if request.resource in user_profile.typical_resources else 0.0
            )
            access_frequency = user_profile.access_frequency.get(request.resource, 0)
            hour_familiarity = (
                1.0 if hour_of_day in user_profile.preferred_hours else 0.0
            )

            # Context features
            is_weekend = 1.0 if day_of_week >= 5 else 0.0
            is_off_hours = 1.0 if hour_of_day < 8 or hour_of_day > 18 else 0.0

            # IP and location features (simplified)
            ip_parts = request.ip_address.split(".")
            ip_class = int(ip_parts[0]) // 64 if len(ip_parts) == 4 else 0

            # User agent features
            ua_length = len(request.user_agent)
            has_session = 1.0 if request.session_id else 0.0

            # Resource and action features
            resource_hash = hash(request.resource) % 1000
            action_hash = hash(request.action) % 100

            # Risk indicators
            risk_indicator_count = len(user_profile.risk_indicators)

            # Historical success rate (placeholder)
            historical_success_rate = 0.8  # Would be calculated from historical data

            features = [
                hour_of_day / 24.0,  # Normalized hour
                day_of_week / 7.0,  # Normalized day
                resource_familiarity,  # Resource familiarity
                min(access_frequency / 100.0, 1.0),  # Normalized access frequency
                hour_familiarity,  # Hour familiarity
                is_weekend,  # Weekend indicator
                is_off_hours,  # Off-hours indicator
                ip_class / 4.0,  # IP class
                ua_length / 500.0,  # User agent length
                has_session,  # Session indicator
                resource_hash / 1000.0,  # Resource variation
                action_hash / 100.0,  # Action variation
                min(risk_indicator_count / 10.0, 1.0),  # Risk indicators
                historical_success_rate,  # Historical success
                len(user_profile.typical_resources) / 50.0,  # User activity level
            ]

            return features

        except Exception as e:
            logger.error(f"Error extracting request features: {e}")
            return None

    async def _apply_risk_based_adjustments(
        self,
        primary_decision: AccessDecision,
        decision_confidence: float,
        risk_level: int,
        risk_confidence: float,
        request: AccessRequest,
    ) -> Tuple[AccessDecision, List[str]]:
        """Apply risk-based adjustments to the primary decision."""

        risk_factors = []
        final_decision = primary_decision

        # High risk always requires additional verification
        if risk_level == 2 and risk_confidence > 0.7:  # High risk
            risk_factors.append("high_risk_assessment")
            if final_decision == AccessDecision.ALLOW:
                final_decision = AccessDecision.CHALLENGE

        # Medium risk with low confidence requires challenge
        elif (
            risk_level == 1 and decision_confidence < 0.6
        ):  # Medium risk, low confidence
            risk_factors.append("medium_risk_low_confidence")
            if final_decision == AccessDecision.ALLOW:
                final_decision = AccessDecision.CHALLENGE

        # Off-hours access requires additional scrutiny
        hour = request.timestamp.hour
        if hour < 6 or hour > 22:
            risk_factors.append("off_hours_access")
            if final_decision == AccessDecision.ALLOW and decision_confidence < 0.8:
                final_decision = AccessDecision.CHALLENGE

        # Weekend access to sensitive resources
        if request.timestamp.weekday() >= 5 and "admin" in request.resource.lower():
            risk_factors.append("weekend_admin_access")
            if final_decision == AccessDecision.ALLOW:
                final_decision = AccessDecision.CHALLENGE

        return final_decision, risk_factors

    async def _get_applicable_rules(
        self, request: AccessRequest, user_profile: UserAccessProfile
    ) -> List[str]:
        """Get list of policy rules that apply to this request."""

        applicable_rules = []

        try:
            # Query database for applicable rules
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """SELECT rule_id, condition FROM ai_policies 
                           WHERE (user_id = %s OR user_id IS NULL)
                           AND (expires_at IS NULL OR expires_at > %s)
                           ORDER BY priority DESC""",
                        (request.user_id, datetime.utcnow()),
                    )

                    rules = cursor.fetchall()

                    # Evaluate rule conditions (simplified)
                    for rule in rules:
                        if self._evaluate_rule_condition(
                            rule["condition"], request, user_profile
                        ):
                            applicable_rules.append(rule["rule_id"])

        except Exception as e:
            logger.error(f"Error getting applicable rules: {e}")

        return applicable_rules or ["default_rule"]

    def _evaluate_rule_condition(
        self, condition: str, request: AccessRequest, user_profile: UserAccessProfile
    ) -> bool:
        """Evaluate if a rule condition matches the request."""

        # Simple rule evaluation (would be more sophisticated in production)
        try:
            # Replace placeholders with actual values
            context = {
                "hour": request.timestamp.hour,
                "day_of_week": request.timestamp.weekday(),
                "resource": request.resource,
                "action": request.action,
                "user_id": request.user_id,
                "risk_indicators": len(user_profile.risk_indicators),
            }

            # Safe evaluation of conditions
            for key, value in context.items():
                condition = condition.replace(f"{{{key}}}", str(value))

            # Basic condition evaluation
            return "true" in condition.lower() or "allow" in condition.lower()

        except Exception as e:
            logger.warning(f"Error evaluating rule condition: {e}")
            return False

    def _generate_decision_reasoning(
        self,
        decision: AccessDecision,
        confidence: float,
        risk_level: int,
        applied_rules: List[str],
    ) -> str:
        """Generate human-readable reasoning for the decision."""

        risk_labels = ["low", "medium", "high"]
        risk_text = risk_labels[min(risk_level, 2)]

        reasoning_parts = [
            f"Access {decision.value} based on AI analysis",
            f"Confidence: {confidence:.2f}",
            f"Risk level: {risk_text}",
            f"Applied {len(applied_rules)} policy rules",
        ]

        if decision == AccessDecision.CHALLENGE:
            reasoning_parts.append(
                "Additional authentication required due to risk factors"
            )
        elif decision == AccessDecision.DENY:
            reasoning_parts.append("Access denied due to policy violation or high risk")

        return "; ".join(reasoning_parts)

    async def _determine_challenge_requirements(
        self, request: AccessRequest, risk_level: int, user_profile: UserAccessProfile
    ) -> Dict[str, Any]:
        """Determine what additional authentication is required for challenge."""

        requirements = {"methods": [], "timeout": 300, "max_attempts": 3}  # 5 minutes

        # High risk requires multiple factors
        if risk_level >= 2:
            requirements["methods"].extend(["totp", "sms", "email"])
            requirements["timeout"] = 600  # 10 minutes

        # Medium risk requires at least one additional factor
        elif risk_level >= 1:
            requirements["methods"].extend(["totp", "email"])

        # Off-hours access always requires email verification
        hour = request.timestamp.hour
        if hour < 6 or hour > 22:
            if "email" not in requirements["methods"]:
                requirements["methods"].append("email")

        return requirements

    async def _get_user_access_profile(self, user_id: str) -> UserAccessProfile:
        """Get or create user access profile."""

        # Check cache first
        cache_key = f"access_profile:{user_id}"

        try:
            cached_profile = self.redis_cluster.get(cache_key)
            if cached_profile:
                profile_data = json.loads(cached_profile)
                return UserAccessProfile(**profile_data)
        except Exception as e:
            logger.warning(f"Cache access failed: {e}")

        # Query database for access profile
        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get user access patterns
                    cursor.execute(
                        """SELECT resource, action, COUNT(*) as frequency,
                           EXTRACT(hour FROM timestamp) as hour
                           FROM access_logs 
                           WHERE user_id = %s 
                           AND timestamp > %s
                           GROUP BY resource, action, EXTRACT(hour FROM timestamp)
                           ORDER BY frequency DESC""",
                        (user_id, datetime.utcnow() - timedelta(days=30)),
                    )

                    access_data = cursor.fetchall()

                    # Process access patterns
                    typical_resources = list(
                        set([row["resource"] for row in access_data[:10]])
                    )
                    access_frequency = {}
                    preferred_hours = []

                    for row in access_data:
                        resource = row["resource"]
                        frequency = row["frequency"]
                        hour = int(row["hour"]) if row["hour"] else 12

                        if resource not in access_frequency:
                            access_frequency[resource] = 0
                        access_frequency[resource] += frequency

                        if frequency > 5:  # Frequent access hours
                            preferred_hours.append(hour)

                    # Remove duplicates and sort
                    preferred_hours = sorted(list(set(preferred_hours)))

                    profile = UserAccessProfile(
                        user_id=user_id,
                        typical_resources=typical_resources,
                        access_frequency=access_frequency,
                        preferred_hours=preferred_hours,
                        common_locations=[],  # Would be populated from location data
                        role_recommendations=[],  # Would be generated by ML
                        risk_indicators=[],  # Would be populated from security analysis
                        last_updated=datetime.utcnow(),
                    )

                    # Cache the profile
                    try:
                        profile_dict = asdict(profile)
                        profile_dict["last_updated"] = profile.last_updated.isoformat()
                        self.redis_cluster.setex(
                            cache_key,
                            self.cache_ttl,
                            json.dumps(profile_dict, default=str),
                        )
                    except Exception as e:
                        logger.warning(f"Cache storage failed: {e}")

                    return profile

        except Exception as e:
            logger.error(f"Database query failed: {e}")

        # Return default profile for new users
        return UserAccessProfile(
            user_id=user_id,
            typical_resources=[],
            access_frequency={},
            preferred_hours=[9, 10, 11, 14, 15, 16],  # Typical work hours
            common_locations=[],
            role_recommendations=[],
            risk_indicators=[],
            last_updated=datetime.utcnow(),
        )

    async def _log_policy_decision(
        self, request: AccessRequest, decision: PolicyDecision
    ):
        """Log policy decision for learning and auditing."""

        try:
            # Store in database
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO policy_decisions 
                           (user_id, resource, action, decision, confidence_score,
                            applied_rules, reasoning, risk_factors, timestamp, context)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            request.user_id,
                            request.resource,
                            request.action,
                            decision.decision.value,
                            decision.confidence_score,
                            json.dumps(decision.applied_rules),
                            decision.reasoning,
                            json.dumps(decision.risk_factors),
                            request.timestamp,
                            json.dumps(request.context),
                        ),
                    )
                    conn.commit()

            # Store in Redis for real-time analysis
            decision_key = f"policy_decision:{request.user_id}:{int(time.time())}"
            decision_data = {
                "request": asdict(request),
                "decision": asdict(decision),
                "timestamp": request.timestamp.isoformat(),
            }

            self.redis_cluster.setex(
                decision_key,
                86400,  # 24 hours TTL
                json.dumps(decision_data, default=str),
            )

        except Exception as e:
            logger.error(f"Failed to log policy decision: {e}")

    async def generate_role_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate intelligent role recommendations for a user."""

        try:
            # Get user access profile
            user_profile = await self._get_user_access_profile(user_id)

            # Extract features for role recommendation
            features = self._extract_role_features(user_profile)

            if not features:
                return []

            # Scale features
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.feature_scaler.transform(features_array)

            # Get role predictions
            role_probs = self.role_recommender.predict_proba(features_scaled)[0]

            # Map role indices to role names
            role_names = ["viewer", "contributor", "editor", "admin", "owner"]

            # Create recommendations with confidence scores
            recommendations = []
            for i, prob in enumerate(role_probs):
                if prob > 0.1:  # Only include roles with reasonable probability
                    recommendations.append(
                        {
                            "role": role_names[min(i, len(role_names) - 1)],
                            "confidence": prob,
                            "reasoning": self._generate_role_reasoning(
                                role_names[min(i, len(role_names) - 1)], user_profile
                            ),
                        }
                    )

            # Sort by confidence
            recommendations.sort(key=lambda x: x["confidence"], reverse=True)

            return recommendations[:3]  # Return top 3 recommendations

        except Exception as e:
            logger.error(f"Error generating role recommendations: {e}")
            return []

    def _extract_role_features(
        self, user_profile: UserAccessProfile
    ) -> Optional[List[float]]:
        """Extract features for role recommendation."""

        try:
            # Resource diversity
            resource_count = len(user_profile.typical_resources)

            # Access frequency patterns
            total_access = sum(user_profile.access_frequency.values())
            avg_access_freq = total_access / max(resource_count, 1)

            # Time patterns
            work_hour_count = sum(
                1 for hour in user_profile.preferred_hours if 9 <= hour <= 17
            )

            # Activity level indicators
            admin_resource_count = sum(
                1 for res in user_profile.typical_resources if "admin" in res.lower()
            )
            read_access_ratio = 0.7  # Placeholder - would calculate from actual data

            features = [
                min(resource_count / 50.0, 1.0),  # Resource diversity
                min(avg_access_freq / 100.0, 1.0),  # Access frequency
                work_hour_count / 9.0,  # Work hours alignment
                min(admin_resource_count / 10.0, 1.0),  # Admin resource access
                read_access_ratio,  # Read vs write ratio
                len(user_profile.preferred_hours) / 24.0,  # Time flexibility
                min(len(user_profile.risk_indicators) / 5.0, 1.0),  # Risk indicators
            ]

            return features

        except Exception as e:
            logger.error(f"Error extracting role features: {e}")
            return None

    def _generate_role_reasoning(
        self, role: str, user_profile: UserAccessProfile
    ) -> str:
        """Generate reasoning for role recommendation."""

        reasoning_map = {
            "viewer": "Based on read-heavy access patterns and limited resource diversity",
            "contributor": "Based on moderate activity level and mixed read/write patterns",
            "editor": "Based on high activity level and diverse resource access",
            "admin": "Based on administrative resource access and extensive permissions usage",
            "owner": "Based on comprehensive system usage and high-level access patterns",
        }

        base_reasoning = reasoning_map.get(role, "Based on access pattern analysis")

        # Add specific factors
        factors = []
        if len(user_profile.typical_resources) > 20:
            factors.append("high resource diversity")
        if len(user_profile.preferred_hours) > 12:
            factors.append("flexible time patterns")
        if any("admin" in res.lower() for res in user_profile.typical_resources):
            factors.append("administrative access history")

        if factors:
            return f"{base_reasoning}; Additional factors: {', '.join(factors)}"

        return base_reasoning


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_policy_engine():
        """Test the Intelligent Policy Engine functionality."""

        # Initialize policy engine
        engine = IntelligentPolicyEngine()

        # Create test access request
        test_request = AccessRequest(
            user_id="test_user_123",
            resource="/api/admin/users",
            action="read",
            context={"department": "IT", "clearance_level": "standard"},
            timestamp=datetime.utcnow(),
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            session_id="session_123",
        )

        # Evaluate the request
        decision = await engine.evaluate_access_request(test_request)

        print(f"Access Decision: {decision.decision.value}")
        print(f"Confidence: {decision.confidence_score:.2f}")
        print(f"Reasoning: {decision.reasoning}")
        print(f"Risk Factors: {decision.risk_factors}")

        if decision.additional_requirements:
            print(f"Additional Requirements: {decision.additional_requirements}")

        # Generate role recommendations
        recommendations = await engine.generate_role_recommendations("test_user_123")

        print("\nRole Recommendations:")
        for rec in recommendations:
            print(f"- {rec['role']}: {rec['confidence']:.2f} confidence")
            print(f"  Reasoning: {rec['reasoning']}")

    # Run test
    asyncio.run(test_policy_engine())
