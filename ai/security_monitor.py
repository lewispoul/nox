#!/usr/bin/env python3
"""
Nox API v8.0.0 - AI-Powered Security Monitor
Real-time threat detection and behavioral analysis using machine learning

Provides intelligent security monitoring with anomaly detection,
behavioral analysis, and automated threat response across the
distributed multi-node architecture.
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

import joblib
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

# Redis and database imports
from redis.cluster import RedisCluster
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Security threat severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BehaviorType(Enum):
    """Types of user behavior patterns"""

    LOGIN_PATTERN = "login_pattern"
    ACCESS_PATTERN = "access_pattern"
    GEOGRAPHIC_PATTERN = "geographic_pattern"
    DEVICE_PATTERN = "device_pattern"
    TEMPORAL_PATTERN = "temporal_pattern"


@dataclass
class SecurityEvent:
    """Security event data structure"""

    user_id: str
    event_type: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    location: Optional[Dict[str, Any]] = None
    device_fingerprint: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class ThreatDetection:
    """Threat detection result"""

    threat_id: str
    user_id: str
    threat_type: str
    severity: ThreatLevel
    confidence_score: float
    detection_details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False


@dataclass
class BehaviorProfile:
    """User behavior profile for ML analysis"""

    user_id: str
    behavior_type: BehaviorType
    feature_vector: List[float]
    risk_score: float
    last_updated: datetime
    pattern_confidence: float


class AISecurityMonitor:
    """
    AI-powered security monitoring system for Nox API.

    Features:
    - Real-time behavioral analysis and anomaly detection
    - Machine learning-based threat identification
    - Geographic and temporal pattern analysis
    - Automated threat response and alerting
    - Integration with distributed Redis Cluster and PostgreSQL
    """

    def __init__(
        self,
        redis_cluster: RedisCluster = None,
        db_connection_params: Dict[str, Any] = None,
    ):
        """
        Initialize AI Security Monitor.

        Args:
            redis_cluster: Redis cluster connection for real-time data
            db_connection_params: PostgreSQL connection parameters
        """

        self.redis_cluster = redis_cluster or self._init_redis_cluster()
        self.db_params = db_connection_params or self._load_db_params()

        # ML Models for different types of analysis
        self.models = {}
        self.scalers = {}
        self.model_versions = {}

        # Behavior analysis configuration
        self.behavior_window_hours = 24  # Analysis window
        self.anomaly_threshold = -0.5  # Isolation Forest threshold
        self.risk_score_threshold = 0.7  # Risk score alert threshold

        # Initialize ML models
        self._initialize_models()

        # Cache for user behavior profiles
        self.behavior_cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL

        logger.info("AI Security Monitor initialized successfully")

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
        """Initialize and load ML models for security analysis."""

        # Initialize different models for different behavior types
        behavior_types = [
            BehaviorType.LOGIN_PATTERN,
            BehaviorType.ACCESS_PATTERN,
            BehaviorType.GEOGRAPHIC_PATTERN,
            BehaviorType.TEMPORAL_PATTERN,
        ]

        for behavior_type in behavior_types:
            # Create Isolation Forest model for anomaly detection
            model = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_estimators=100,
            )

            # Create scaler for feature normalization
            scaler = StandardScaler()

            # Try to load existing trained models
            model_path = f"/tmp/nox_ai_model_{behavior_type.value}.pkl"
            scaler_path = f"/tmp/nox_ai_scaler_{behavior_type.value}.pkl"

            try:
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    model = joblib.load(model_path)
                    scaler = joblib.load(scaler_path)
                    logger.info(f"Loaded existing model for {behavior_type.value}")
                else:
                    # Initialize with dummy data for cold start
                    dummy_data = np.random.rand(100, 10)  # 100 samples, 10 features
                    scaler.fit(dummy_data)
                    scaled_data = scaler.transform(dummy_data)
                    model.fit(scaled_data)
                    logger.info(f"Initialized new model for {behavior_type.value}")

            except Exception as e:
                logger.warning(f"Failed to load model for {behavior_type.value}: {e}")
                # Fallback to new model initialization
                dummy_data = np.random.rand(100, 10)
                scaler.fit(dummy_data)
                scaled_data = scaler.transform(dummy_data)
                model.fit(scaled_data)

            self.models[behavior_type] = model
            self.scalers[behavior_type] = scaler
            self.model_versions[behavior_type] = "1.0.0"

        logger.info(f"Initialized {len(self.models)} ML models for security monitoring")

    async def process_security_event(
        self, event: SecurityEvent
    ) -> List[ThreatDetection]:
        """
        Process a security event and detect potential threats.

        Args:
            event: Security event to analyze

        Returns:
            List of detected threats
        """

        threats = []

        try:
            # Store event for historical analysis
            await self._store_security_event(event)

            # Get user behavior profile
            behavior_profile = await self._get_user_behavior_profile(event.user_id)

            # Analyze different aspects of the event
            login_threat = await self._analyze_login_behavior(event, behavior_profile)
            if login_threat:
                threats.append(login_threat)

            access_threat = await self._analyze_access_patterns(event, behavior_profile)
            if access_threat:
                threats.append(access_threat)

            geo_threat = await self._analyze_geographic_anomaly(event, behavior_profile)
            if geo_threat:
                threats.append(geo_threat)

            temporal_threat = await self._analyze_temporal_patterns(
                event, behavior_profile
            )
            if temporal_threat:
                threats.append(temporal_threat)

            # Update user behavior profile
            await self._update_behavior_profile(event, behavior_profile)

            # Store detected threats
            for threat in threats:
                await self._store_threat_detection(threat)
                await self._trigger_automated_response(threat)

            return threats

        except Exception as e:
            logger.error(f"Error processing security event: {e}")
            return []

    async def _analyze_login_behavior(
        self, event: SecurityEvent, behavior_profile: Dict[str, Any]
    ) -> Optional[ThreatDetection]:
        """Analyze login behavior patterns for anomalies."""

        try:
            # Extract login behavior features
            features = await self._extract_login_features(event, behavior_profile)

            if not features:
                return None

            # Scale features
            model = self.models[BehaviorType.LOGIN_PATTERN]
            scaler = self.scalers[BehaviorType.LOGIN_PATTERN]

            scaled_features = scaler.transform([features])

            # Predict anomaly
            anomaly_score = model.decision_function(scaled_features)[0]
            is_anomaly = model.predict(scaled_features)[0] == -1

            if is_anomaly and anomaly_score < self.anomaly_threshold:
                # Calculate threat severity based on anomaly score
                severity = self._calculate_threat_severity(anomaly_score)
                confidence = min(abs(anomaly_score) * 2, 1.0)

                return ThreatDetection(
                    threat_id=f"login_anomaly_{int(time.time())}_{event.user_id}",
                    user_id=event.user_id,
                    threat_type="login_anomaly",
                    severity=severity,
                    confidence_score=confidence,
                    detection_details={
                        "anomaly_score": anomaly_score,
                        "features": dict(
                            zip(self._get_login_feature_names(), features)
                        ),
                        "event_timestamp": event.timestamp.isoformat(),
                        "ip_address": event.ip_address,
                    },
                    timestamp=datetime.utcnow(),
                )

            return None

        except Exception as e:
            logger.error(f"Error analyzing login behavior: {e}")
            return None

    async def _extract_login_features(
        self, event: SecurityEvent, behavior_profile: Dict[str, Any]
    ) -> Optional[List[float]]:
        """Extract numerical features for login behavior analysis."""

        try:
            # Time-based features
            hour_of_day = event.timestamp.hour
            day_of_week = event.timestamp.weekday()

            # Historical behavior features
            avg_login_hour = behavior_profile.get("avg_login_hour", 12)
            login_frequency = behavior_profile.get("login_frequency", 1)

            # IP address features (simplified)
            ip_parts = event.ip_address.split(".")
            ip_numeric = sum(
                int(part) * (256 ** (3 - i)) for i, part in enumerate(ip_parts)
            )
            ip_class = int(ip_parts[0]) // 64  # Rough IP class categorization

            # User agent features (simplified)
            ua_length = len(event.user_agent)
            ua_hash = hash(event.user_agent) % 10000

            # Device fingerprint features
            device_hash = 0
            if event.device_fingerprint:
                device_hash = hash(event.device_fingerprint) % 10000

            features = [
                hour_of_day / 24.0,  # Normalized hour
                day_of_week / 7.0,  # Normalized day of week
                abs(hour_of_day - avg_login_hour) / 24.0,  # Hour deviation
                min(login_frequency / 100.0, 1.0),  # Login frequency
                ip_class / 4.0,  # IP class
                (ip_numeric % 65536) / 65536.0,  # IP variation
                ua_length / 500.0,  # User agent length
                (ua_hash % 1000) / 1000.0,  # User agent variation
                (device_hash % 1000) / 1000.0,  # Device variation
                1.0 if event.session_id else 0.0,  # Has session
            ]

            return features

        except Exception as e:
            logger.error(f"Error extracting login features: {e}")
            return None

    def _get_login_feature_names(self) -> List[str]:
        """Get names of login behavior features."""
        return [
            "hour_normalized",
            "day_normalized",
            "hour_deviation",
            "login_frequency",
            "ip_class",
            "ip_variation",
            "ua_length",
            "ua_variation",
            "device_variation",
            "has_session",
        ]

    async def _analyze_access_patterns(
        self, event: SecurityEvent, behavior_profile: Dict[str, Any]
    ) -> Optional[ThreatDetection]:
        """Analyze access patterns for suspicious activity."""

        # Implement access pattern analysis
        # This would analyze API endpoints, request frequency, etc.

        return None  # Placeholder implementation

    async def _analyze_geographic_anomaly(
        self, event: SecurityEvent, behavior_profile: Dict[str, Any]
    ) -> Optional[ThreatDetection]:
        """Analyze geographic location for impossible travel or suspicious locations."""

        # Implement geographic anomaly detection
        # This would check for impossible travel times, suspicious countries, etc.

        return None  # Placeholder implementation

    async def _analyze_temporal_patterns(
        self, event: SecurityEvent, behavior_profile: Dict[str, Any]
    ) -> Optional[ThreatDetection]:
        """Analyze temporal patterns for unusual timing."""

        # Implement temporal pattern analysis
        # This would check for off-hours access, burst activity, etc.

        return None  # Placeholder implementation

    def _calculate_threat_severity(self, anomaly_score: float) -> ThreatLevel:
        """Calculate threat severity based on anomaly score."""

        if anomaly_score < -0.8:
            return ThreatLevel.CRITICAL
        elif anomaly_score < -0.6:
            return ThreatLevel.HIGH
        elif anomaly_score < -0.4:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    async def _get_user_behavior_profile(self, user_id: str) -> Dict[str, Any]:
        """Get or create user behavior profile."""

        # Check cache first
        cache_key = f"behavior_profile:{user_id}"

        try:
            cached_profile = self.redis_cluster.get(cache_key)
            if cached_profile:
                return json.loads(cached_profile)
        except Exception as e:
            logger.warning(f"Cache access failed: {e}")

        # Query database for behavior profile
        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM user_behavior_profiles WHERE user_id = %s",
                        (user_id,),
                    )

                    result = cursor.fetchone()
                    if result:
                        profile = dict(result)
                        # Cache the profile
                        try:
                            self.redis_cluster.setex(
                                cache_key,
                                self.cache_ttl,
                                json.dumps(profile, default=str),
                            )
                        except Exception as e:
                            logger.warning(f"Cache storage failed: {e}")

                        return profile

        except Exception as e:
            logger.error(f"Database query failed: {e}")

        # Return default profile for new users
        return {
            "user_id": user_id,
            "avg_login_hour": 12,
            "login_frequency": 1,
            "typical_locations": [],
            "device_fingerprints": [],
            "risk_score": 0.0,
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def _update_behavior_profile(
        self, event: SecurityEvent, current_profile: Dict[str, Any]
    ):
        """Update user behavior profile based on new event."""

        # Update profile with new event data
        # This would implement incremental learning and profile updates

        pass  # Placeholder implementation

    async def _store_security_event(self, event: SecurityEvent):
        """Store security event for historical analysis."""

        try:
            # Store in Redis for real-time access
            event_key = f"security_event:{event.user_id}:{int(time.time())}"
            event_data = asdict(event)
            event_data["timestamp"] = event.timestamp.isoformat()

            self.redis_cluster.setex(
                event_key, 86400, json.dumps(event_data, default=str)  # 24 hours TTL
            )

            # Also store in database for long-term analysis
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO security_events 
                           (user_id, event_type, timestamp, ip_address, user_agent, 
                            location, device_fingerprint, session_id, additional_data)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            event.user_id,
                            event.event_type,
                            event.timestamp,
                            event.ip_address,
                            event.user_agent,
                            json.dumps(event.location) if event.location else None,
                            event.device_fingerprint,
                            event.session_id,
                            (
                                json.dumps(event.additional_data)
                                if event.additional_data
                                else None
                            ),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Failed to store security event: {e}")

    async def _store_threat_detection(self, threat: ThreatDetection):
        """Store threat detection result."""

        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO threat_detections 
                           (id, user_id, threat_type, severity_level, 
                            detection_details, confidence_score, resolved, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            threat.threat_id,
                            threat.user_id,
                            threat.threat_type,
                            threat.severity.value,
                            json.dumps(threat.detection_details),
                            threat.confidence_score,
                            threat.resolved,
                            threat.timestamp,
                        ),
                    )
                    conn.commit()

            # Store in Redis for real-time access
            threat_key = f"threat:{threat.threat_id}"
            threat_data = asdict(threat)
            threat_data["timestamp"] = threat.timestamp.isoformat()
            threat_data["severity"] = threat.severity.value

            self.redis_cluster.setex(
                threat_key, 86400, json.dumps(threat_data, default=str)  # 24 hours TTL
            )

        except Exception as e:
            logger.error(f"Failed to store threat detection: {e}")

    async def _trigger_automated_response(self, threat: ThreatDetection):
        """Trigger automated response based on threat severity."""

        try:
            # High and critical threats trigger immediate alerts
            if threat.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                await self._send_security_alert(threat)

            # Critical threats may trigger account lockdown
            if threat.severity == ThreatLevel.CRITICAL:
                await self._initiate_account_protection(threat)

            logger.info(f"Automated response triggered for threat {threat.threat_id}")

        except Exception as e:
            logger.error(f"Failed to trigger automated response: {e}")

    async def _send_security_alert(self, threat: ThreatDetection):
        """Send security alert for high-priority threats."""

        # This would integrate with alerting systems (email, SMS, Slack, etc.)
        logger.warning(
            f"SECURITY ALERT: {threat.threat_type} detected for user {threat.user_id} "
            f"with {threat.severity.value} severity (confidence: {threat.confidence_score:.2f})"
        )

    async def _initiate_account_protection(self, threat: ThreatDetection):
        """Initiate protective measures for critical threats."""

        # This would implement account protection measures like:
        # - Requiring additional authentication
        # - Temporary account suspension
        # - Forcing password reset
        # - Notifying security team

        logger.critical(
            f"Account protection initiated for user {threat.user_id} due to {threat.threat_type}"
        )

    async def get_user_risk_assessment(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk assessment for a user."""

        try:
            # Get recent threat detections
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """SELECT * FROM threat_detections 
                           WHERE user_id = %s 
                           AND created_at > %s 
                           ORDER BY created_at DESC LIMIT 10""",
                        (user_id, datetime.utcnow() - timedelta(days=7)),
                    )

                    recent_threats = [dict(row) for row in cursor.fetchall()]

            # Calculate overall risk score
            risk_score = self._calculate_user_risk_score(recent_threats)

            # Get behavior profile
            behavior_profile = await self._get_user_behavior_profile(user_id)

            return {
                "user_id": user_id,
                "overall_risk_score": risk_score,
                "recent_threats": recent_threats,
                "behavior_profile": behavior_profile,
                "assessment_timestamp": datetime.utcnow().isoformat(),
                "recommendations": self._generate_security_recommendations(
                    risk_score, recent_threats
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get user risk assessment: {e}")
            return {"user_id": user_id, "error": str(e)}

    def _calculate_user_risk_score(self, recent_threats: List[Dict[str, Any]]) -> float:
        """Calculate overall risk score based on recent threats."""

        if not recent_threats:
            return 0.0

        # Weight threats by severity and recency
        severity_weights = {"low": 0.1, "medium": 0.3, "high": 0.7, "critical": 1.0}

        total_score = 0.0
        for threat in recent_threats:
            severity_weight = severity_weights.get(
                threat.get("severity_level", "low"), 0.1
            )
            confidence = threat.get("confidence_score", 0.5)

            # Apply time decay (newer threats have more weight)
            threat_age_days = (datetime.utcnow() - threat["created_at"]).days
            time_decay = max(0.1, 1.0 - (threat_age_days / 7.0))  # 7-day decay

            threat_score = severity_weight * confidence * time_decay
            total_score += threat_score

        # Normalize to 0-1 range
        return min(total_score / len(recent_threats), 1.0)

    def _generate_security_recommendations(
        self, risk_score: float, recent_threats: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate security recommendations based on risk assessment."""

        recommendations = []

        if risk_score > 0.8:
            recommendations.append(
                "Consider requiring additional authentication factors"
            )
            recommendations.append("Review recent login locations and devices")
            recommendations.append("Enable real-time security alerts")

        if risk_score > 0.5:
            recommendations.append("Update password if not changed recently")
            recommendations.append("Review authorized applications and permissions")

        if recent_threats:
            recommendations.append("Monitor account activity closely")
            recommendations.append("Consider enabling stricter access controls")

        return recommendations


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_ai_security_monitor():
        """Test the AI Security Monitor functionality."""

        # Initialize security monitor
        monitor = AISecurityMonitor()

        # Create test security event
        test_event = SecurityEvent(
            user_id="test_user_123",
            event_type="login",
            timestamp=datetime.utcnow(),
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            location={"country": "US", "city": "San Francisco"},
            device_fingerprint="test_device_fp_123",
            session_id="session_123",
        )

        # Process the event
        threats = await monitor.process_security_event(test_event)

        print(f"Detected {len(threats)} threats:")
        for threat in threats:
            print(f"- {threat.threat_type}: {threat.severity.value} severity")

        # Get risk assessment
        risk_assessment = await monitor.get_user_risk_assessment("test_user_123")
        print(f"User risk score: {risk_assessment.get('overall_risk_score', 0.0):.2f}")

    # Run test
    asyncio.run(test_ai_security_monitor())
