#!/usr/bin/env python3
"""
Nox API Python SDK - AI Security Client
v8.0.0 Developer Experience Enhancement

AI-powered security features integration for threat detection,
behavioral analysis, and intelligent security monitoring.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Security event for analysis."""

    event_type: str
    timestamp: str
    method: Optional[str] = None
    endpoint: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class ThreatAssessment:
    """Threat assessment result from AI analysis."""

    threat_level: str  # low, medium, high, critical
    confidence_score: float
    threat_indicators: List[str]
    recommended_actions: List[str]
    analysis_time_ms: float


class SecurityClient:
    """
    AI Security client for threat detection and behavioral analysis.

    Integrates with the AI Security Monitor to provide:
    - Real-time threat detection
    - Behavioral pattern analysis
    - Security event monitoring
    - Intelligent threat response recommendations
    """

    def __init__(self, main_client):
        """
        Initialize security client.

        Args:
            main_client: Main NoxClient instance
        """
        self.client = main_client
        self.threat_history: List[ThreatAssessment] = []
        self.max_history_size = 100

        logger.info("AI Security client initialized")

    async def analyze_security_event(
        self, event_data: Dict[str, Any]
    ) -> Optional[ThreatAssessment]:
        """
        Analyze a security event for threats.

        Args:
            event_data: Security event data

        Returns:
            Threat assessment or None if analysis fails
        """

        try:
            # Create security event
            security_event = SecurityEvent(
                event_type=event_data.get("event_type", "api_call"),
                timestamp=event_data.get("timestamp", datetime.utcnow().isoformat()),
                method=event_data.get("method"),
                endpoint=event_data.get("endpoint"),
                status_code=event_data.get("status_code"),
                response_time=event_data.get("response_time"),
                user_agent=event_data.get("user_agent"),
                ip_address=event_data.get("ip_address"),
                additional_context=event_data.get("context", {}),
            )

            # Send to AI security monitor
            response = await self.client.post(
                "/api/ai/security/analyze", data=asdict(security_event)
            )

            if response.success and response.data:
                threat_assessment = ThreatAssessment(
                    threat_level=response.data.get("threat_level", "low"),
                    confidence_score=response.data.get("confidence_score", 0.0),
                    threat_indicators=response.data.get("threat_indicators", []),
                    recommended_actions=response.data.get("recommended_actions", []),
                    analysis_time_ms=response.response_time_ms or 0.0,
                )

                # Add to history
                self._add_to_history(threat_assessment)

                return threat_assessment

            return None

        except Exception as e:
            logger.error(f"Security event analysis failed: {e}")
            return None

    async def analyze_api_call(
        self, call_data: Dict[str, Any]
    ) -> Optional[ThreatAssessment]:
        """
        Analyze an API call for security threats.

        Args:
            call_data: API call data

        Returns:
            Threat assessment or None
        """

        # Enhance call data with security context
        enhanced_data = {
            **call_data,
            "event_type": "api_call",
            "analysis_type": "real_time",
        }

        return await self.analyze_security_event(enhanced_data)

    async def get_user_behavior_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user behavioral profile from AI system.

        Args:
            user_id: User identifier

        Returns:
            Behavioral profile or None
        """

        try:
            response = await self.client.get(f"/api/ai/security/profile/{user_id}")

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to get user behavior profile: {e}")
            return None

    async def report_suspicious_activity(
        self, activity_data: Dict[str, Any], severity: str = "medium"
    ) -> bool:
        """
        Report suspicious activity for AI analysis.

        Args:
            activity_data: Suspicious activity data
            severity: Activity severity (low, medium, high, critical)

        Returns:
            True if report submitted successfully
        """

        try:
            report_data = {
                "activity": activity_data,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
                "reporter": "sdk_client",
            }

            response = await self.client.post(
                "/api/ai/security/report", data=report_data
            )

            if response.success:
                logger.info("Suspicious activity reported successfully")
                return True

            logger.warning("Failed to report suspicious activity")
            return False

        except Exception as e:
            logger.error(f"Error reporting suspicious activity: {e}")
            return False

    async def get_threat_intelligence(self) -> Optional[Dict[str, Any]]:
        """
        Get current threat intelligence from AI system.

        Returns:
            Threat intelligence data or None
        """

        try:
            response = await self.client.get("/api/ai/security/intelligence")

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to get threat intelligence: {e}")
            return None

    async def check_ip_reputation(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """
        Check IP address reputation using AI analysis.

        Args:
            ip_address: IP address to check

        Returns:
            IP reputation data or None
        """

        try:
            response = await self.client.get(
                "/api/ai/security/ip-reputation", params={"ip": ip_address}
            )

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to check IP reputation: {e}")
            return None

    async def start_behavioral_monitoring(
        self, user_id: str, monitoring_duration: int = 3600
    ) -> Optional[str]:
        """
        Start behavioral monitoring session for a user.

        Args:
            user_id: User to monitor
            monitoring_duration: Duration in seconds

        Returns:
            Monitoring session ID or None
        """

        try:
            monitoring_data = {
                "user_id": user_id,
                "duration": monitoring_duration,
                "monitoring_type": "behavioral_analysis",
            }

            response = await self.client.post(
                "/api/ai/security/monitor/start", data=monitoring_data
            )

            if response.success and response.data:
                session_id = response.data.get("session_id")
                logger.info(f"Behavioral monitoring started: {session_id}")
                return session_id

            return None

        except Exception as e:
            logger.error(f"Failed to start behavioral monitoring: {e}")
            return None

    async def stop_behavioral_monitoring(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Stop behavioral monitoring session and get results.

        Args:
            session_id: Monitoring session ID

        Returns:
            Monitoring results or None
        """

        try:
            response = await self.client.post(
                f"/api/ai/security/monitor/stop/{session_id}"
            )

            if response.success:
                logger.info(f"Behavioral monitoring stopped: {session_id}")
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to stop behavioral monitoring: {e}")
            return None

    async def get_security_recommendations(
        self, user_id: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get AI-powered security recommendations for a user.

        Args:
            user_id: User identifier
            context: Additional context for recommendations

        Returns:
            List of security recommendations
        """

        try:
            request_data = {"user_id": user_id, "context": context or {}}

            response = await self.client.post(
                "/api/ai/security/recommendations", data=request_data
            )

            if response.success and response.data:
                return response.data.get("recommendations", [])

            return []

        except Exception as e:
            logger.error(f"Failed to get security recommendations: {e}")
            return []

    def _add_to_history(self, assessment: ThreatAssessment):
        """Add threat assessment to history."""
        self.threat_history.append(assessment)

        # Maintain max history size
        if len(self.threat_history) > self.max_history_size:
            self.threat_history = self.threat_history[-self.max_history_size :]

    def get_threat_history(self) -> List[ThreatAssessment]:
        """Get threat assessment history."""
        return self.threat_history.copy()

    def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat statistics from history."""
        if not self.threat_history:
            return {
                "total_assessments": 0,
                "threat_levels": {},
                "average_confidence": 0.0,
                "common_indicators": [],
            }

        # Calculate statistics
        threat_levels = {}
        total_confidence = 0.0
        all_indicators = []

        for assessment in self.threat_history:
            # Count threat levels
            level = assessment.threat_level
            threat_levels[level] = threat_levels.get(level, 0) + 1

            # Sum confidence scores
            total_confidence += assessment.confidence_score

            # Collect indicators
            all_indicators.extend(assessment.threat_indicators)

        # Find most common indicators
        from collections import Counter

        indicator_counts = Counter(all_indicators)
        common_indicators = [item for item, count in indicator_counts.most_common(5)]

        return {
            "total_assessments": len(self.threat_history),
            "threat_levels": threat_levels,
            "average_confidence": total_confidence / len(self.threat_history),
            "common_indicators": common_indicators,
            "average_analysis_time": sum(
                a.analysis_time_ms for a in self.threat_history
            )
            / len(self.threat_history),
        }

    async def configure_security_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Configure AI security settings.

        Args:
            settings: Security configuration settings

        Returns:
            True if configuration successful
        """

        try:
            response = await self.client.put("/api/ai/security/settings", data=settings)

            if response.success:
                logger.info("Security settings configured successfully")
                return True

            logger.warning("Failed to configure security settings")
            return False

        except Exception as e:
            logger.error(f"Error configuring security settings: {e}")
            return False

    async def get_security_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get AI security system metrics.

        Returns:
            Security metrics or None
        """

        try:
            response = await self.client.get("/api/ai/security/metrics")

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return None
