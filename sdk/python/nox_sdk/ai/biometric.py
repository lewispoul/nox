#!/usr/bin/env python3
"""
Nox API Python SDK - AI Biometric Client
v8.0.0 Developer Experience Enhancement

AI-powered biometric authentication integration for advanced
user verification, behavioral biometrics, and adaptive authentication.
"""

import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BiometricType(Enum):
    """Biometric authentication types."""

    FINGERPRINT = "fingerprint"
    FACE = "face"
    VOICE = "voice"
    BEHAVIORAL = "behavioral"
    KEYSTROKE = "keystroke"
    MULTI_MODAL = "multi_modal"


class AuthenticationResult(Enum):
    """Authentication result types."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    REQUIRE_ADDITIONAL = "require_additional"
    SUSPICIOUS = "suspicious"


@dataclass
class BiometricTemplate:
    """Biometric template data."""

    template_id: str
    user_id: str
    biometric_type: BiometricType
    template_data: str  # Base64 encoded
    quality_score: float
    created_at: str
    expires_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BiometricChallenge:
    """Biometric authentication challenge."""

    challenge_id: str
    user_id: str
    challenge_type: BiometricType
    challenge_data: Optional[str] = None
    expires_at: str
    attempt_count: int = 0
    max_attempts: int = 3
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuthenticationResponse:
    """Biometric authentication response."""

    result: AuthenticationResult
    confidence_score: float
    matched_templates: List[str]
    processing_time_ms: float
    challenge_id: Optional[str] = None
    additional_requirements: Optional[List[str]] = None
    fraud_indicators: Optional[List[str]] = None


class BiometricClient:
    """
    AI Biometric client for advanced authentication and verification.

    Integrates with the AI Biometric Authentication system to provide:
    - Multi-modal biometric authentication
    - Behavioral biometrics analysis
    - Anti-spoofing and fraud detection
    - Adaptive authentication flows
    """

    def __init__(self, main_client):
        """
        Initialize biometric client.

        Args:
            main_client: Main NoxClient instance
        """
        self.client = main_client
        self.active_challenges: Dict[str, BiometricChallenge] = {}
        self.authentication_history: List[AuthenticationResponse] = []
        self.max_history_size = 100

        logger.info("AI Biometric client initialized")

    async def enroll_biometric(
        self,
        user_id: str,
        biometric_type: BiometricType,
        biometric_data: Union[str, bytes],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[BiometricTemplate]:
        """
        Enroll a biometric template for a user.

        Args:
            user_id: User identifier
            biometric_type: Type of biometric
            biometric_data: Raw biometric data
            metadata: Additional metadata

        Returns:
            Biometric template or None
        """

        try:
            # Encode biometric data if needed
            if isinstance(biometric_data, bytes):
                encoded_data = base64.b64encode(biometric_data).decode("utf-8")
            else:
                encoded_data = biometric_data

            enrollment_data = {
                "user_id": user_id,
                "biometric_type": biometric_type.value,
                "biometric_data": encoded_data,
                "metadata": metadata or {},
            }

            response = await self.client.post(
                "/api/ai/biometric/enroll", data=enrollment_data
            )

            if response.success and response.data:
                template = BiometricTemplate(
                    template_id=response.data["template_id"],
                    user_id=user_id,
                    biometric_type=biometric_type,
                    template_data=response.data["template_data"],
                    quality_score=response.data.get("quality_score", 0.0),
                    created_at=response.data.get(
                        "created_at", datetime.utcnow().isoformat()
                    ),
                    expires_at=response.data.get("expires_at"),
                    metadata=response.data.get("metadata"),
                )

                logger.info(f"Biometric enrolled: {template.template_id}")
                return template

            return None

        except Exception as e:
            logger.error(f"Biometric enrollment failed: {e}")
            return None

    async def authenticate_biometric(
        self,
        user_id: str,
        biometric_type: BiometricType,
        biometric_data: Union[str, bytes],
        challenge_id: Optional[str] = None,
    ) -> Optional[AuthenticationResponse]:
        """
        Authenticate using biometric data.

        Args:
            user_id: User identifier
            biometric_type: Type of biometric
            biometric_data: Raw biometric data for verification
            challenge_id: Optional challenge ID

        Returns:
            Authentication response or None
        """

        try:
            # Encode biometric data if needed
            if isinstance(biometric_data, bytes):
                encoded_data = base64.b64encode(biometric_data).decode("utf-8")
            else:
                encoded_data = biometric_data

            auth_data = {
                "user_id": user_id,
                "biometric_type": biometric_type.value,
                "biometric_data": encoded_data,
                "challenge_id": challenge_id,
            }

            response = await self.client.post(
                "/api/ai/biometric/authenticate", data=auth_data
            )

            if response.success and response.data:
                auth_response = AuthenticationResponse(
                    result=AuthenticationResult(response.data.get("result", "failure")),
                    confidence_score=response.data.get("confidence_score", 0.0),
                    matched_templates=response.data.get("matched_templates", []),
                    processing_time_ms=response.response_time_ms or 0.0,
                    challenge_id=response.data.get("challenge_id"),
                    additional_requirements=response.data.get(
                        "additional_requirements"
                    ),
                    fraud_indicators=response.data.get("fraud_indicators"),
                )

                # Add to history
                self._add_to_history(auth_response)

                # Update challenge if provided
                if challenge_id and challenge_id in self.active_challenges:
                    self.active_challenges[challenge_id].attempt_count += 1

                return auth_response

            return None

        except Exception as e:
            logger.error(f"Biometric authentication failed: {e}")
            return None

    async def create_authentication_challenge(
        self,
        user_id: str,
        challenge_type: BiometricType,
        expires_in: int = 300,
        max_attempts: int = 3,
    ) -> Optional[BiometricChallenge]:
        """
        Create a biometric authentication challenge.

        Args:
            user_id: User identifier
            challenge_type: Type of challenge
            expires_in: Expiration time in seconds
            max_attempts: Maximum attempts allowed

        Returns:
            Biometric challenge or None
        """

        try:
            challenge_data = {
                "user_id": user_id,
                "challenge_type": challenge_type.value,
                "expires_in": expires_in,
                "max_attempts": max_attempts,
            }

            response = await self.client.post(
                "/api/ai/biometric/challenge/create", data=challenge_data
            )

            if response.success and response.data:
                challenge = BiometricChallenge(
                    challenge_id=response.data["challenge_id"],
                    user_id=user_id,
                    challenge_type=challenge_type,
                    challenge_data=response.data.get("challenge_data"),
                    expires_at=response.data["expires_at"],
                    max_attempts=max_attempts,
                )

                # Store active challenge
                self.active_challenges[challenge.challenge_id] = challenge

                logger.info(f"Biometric challenge created: {challenge.challenge_id}")
                return challenge

            return None

        except Exception as e:
            logger.error(f"Failed to create biometric challenge: {e}")
            return None

    async def verify_challenge_response(
        self, challenge_id: str, biometric_data: Union[str, bytes]
    ) -> Optional[AuthenticationResponse]:
        """
        Verify response to a biometric challenge.

        Args:
            challenge_id: Challenge identifier
            biometric_data: Response biometric data

        Returns:
            Authentication response or None
        """

        if challenge_id not in self.active_challenges:
            logger.error(f"Unknown challenge: {challenge_id}")
            return None

        challenge = self.active_challenges[challenge_id]

        # Authenticate using the challenge
        return await self.authenticate_biometric(
            user_id=challenge.user_id,
            biometric_type=challenge.challenge_type,
            biometric_data=biometric_data,
            challenge_id=challenge_id,
        )

    async def get_user_templates(self, user_id: str) -> List[BiometricTemplate]:
        """
        Get all biometric templates for a user.

        Args:
            user_id: User identifier

        Returns:
            List of biometric templates
        """

        try:
            response = await self.client.get(f"/api/ai/biometric/templates/{user_id}")

            if response.success and response.data:
                templates = []
                for template_data in response.data.get("templates", []):
                    template = BiometricTemplate(
                        template_id=template_data["template_id"],
                        user_id=user_id,
                        biometric_type=BiometricType(template_data["biometric_type"]),
                        template_data=template_data["template_data"],
                        quality_score=template_data.get("quality_score", 0.0),
                        created_at=template_data.get("created_at", ""),
                        expires_at=template_data.get("expires_at"),
                        metadata=template_data.get("metadata"),
                    )
                    templates.append(template)

                return templates

            return []

        except Exception as e:
            logger.error(f"Failed to get user templates: {e}")
            return []

    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a biometric template.

        Args:
            template_id: Template identifier

        Returns:
            True if deletion successful
        """

        try:
            response = await self.client.delete(
                f"/api/ai/biometric/templates/{template_id}"
            )

            if response.success:
                logger.info(f"Biometric template deleted: {template_id}")
                return True

            logger.warning(f"Failed to delete template: {template_id}")
            return False

        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False

    async def analyze_behavioral_pattern(
        self, user_id: str, behavioral_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze behavioral biometric patterns.

        Args:
            user_id: User identifier
            behavioral_data: Behavioral data (keystroke, mouse, etc.)

        Returns:
            Behavioral analysis or None
        """

        try:
            analysis_data = {
                "user_id": user_id,
                "behavioral_data": behavioral_data,
                "analysis_type": "pattern_recognition",
            }

            response = await self.client.post(
                "/api/ai/biometric/behavioral/analyze", data=analysis_data
            )

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Behavioral pattern analysis failed: {e}")
            return None

    async def detect_liveness(
        self, biometric_type: BiometricType, biometric_data: Union[str, bytes]
    ) -> Optional[Dict[str, Any]]:
        """
        Perform liveness detection to prevent spoofing.

        Args:
            biometric_type: Type of biometric
            biometric_data: Biometric data to analyze

        Returns:
            Liveness analysis or None
        """

        try:
            # Encode data if needed
            if isinstance(biometric_data, bytes):
                encoded_data = base64.b64encode(biometric_data).decode("utf-8")
            else:
                encoded_data = biometric_data

            liveness_data = {
                "biometric_type": biometric_type.value,
                "biometric_data": encoded_data,
            }

            response = await self.client.post(
                "/api/ai/biometric/liveness", data=liveness_data
            )

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Liveness detection failed: {e}")
            return None

    async def get_fraud_analysis(
        self, user_id: str, time_range: str = "24h"
    ) -> Optional[Dict[str, Any]]:
        """
        Get fraud analysis for biometric authentications.

        Args:
            user_id: User identifier
            time_range: Analysis time range

        Returns:
            Fraud analysis or None
        """

        try:
            response = await self.client.get(
                f"/api/ai/biometric/fraud-analysis/{user_id}",
                params={"range": time_range},
            )

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to get fraud analysis: {e}")
            return None

    async def configure_biometric_settings(
        self, user_id: str, settings: Dict[str, Any]
    ) -> bool:
        """
        Configure biometric settings for a user.

        Args:
            user_id: User identifier
            settings: Biometric settings

        Returns:
            True if configuration successful
        """

        try:
            response = await self.client.put(
                f"/api/ai/biometric/settings/{user_id}", data=settings
            )

            if response.success:
                logger.info(f"Biometric settings configured for user: {user_id}")
                return True

            logger.warning(
                f"Failed to configure biometric settings for user: {user_id}"
            )
            return False

        except Exception as e:
            logger.error(f"Error configuring biometric settings: {e}")
            return False

    async def get_authentication_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get authentication statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Authentication statistics or None
        """

        try:
            response = await self.client.get(f"/api/ai/biometric/stats/{user_id}")

            if response.success:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Failed to get authentication stats: {e}")
            return None

    async def create_multi_modal_template(
        self, user_id: str, biometric_data_map: Dict[BiometricType, Union[str, bytes]]
    ) -> Optional[str]:
        """
        Create a multi-modal biometric template.

        Args:
            user_id: User identifier
            biometric_data_map: Map of biometric types to data

        Returns:
            Multi-modal template ID or None
        """

        try:
            # Prepare multi-modal data
            modal_data = {}
            for bio_type, data in biometric_data_map.items():
                if isinstance(data, bytes):
                    encoded_data = base64.b64encode(data).decode("utf-8")
                else:
                    encoded_data = data
                modal_data[bio_type.value] = encoded_data

            template_data = {"user_id": user_id, "biometric_data": modal_data}

            response = await self.client.post(
                "/api/ai/biometric/multi-modal/enroll", data=template_data
            )

            if response.success and response.data:
                template_id = response.data.get("template_id")
                logger.info(f"Multi-modal template created: {template_id}")
                return template_id

            return None

        except Exception as e:
            logger.error(f"Failed to create multi-modal template: {e}")
            return None

    def get_active_challenges(self) -> Dict[str, BiometricChallenge]:
        """Get active biometric challenges."""
        return self.active_challenges.copy()

    def clear_expired_challenges(self):
        """Clear expired challenges."""
        now = datetime.utcnow().isoformat()
        expired = [
            challenge_id
            for challenge_id, challenge in self.active_challenges.items()
            if challenge.expires_at <= now
        ]

        for challenge_id in expired:
            del self.active_challenges[challenge_id]
            logger.info(f"Cleared expired challenge: {challenge_id}")

    def _add_to_history(self, response: AuthenticationResponse):
        """Add authentication response to history."""
        self.authentication_history.append(response)

        # Maintain max history size
        if len(self.authentication_history) > self.max_history_size:
            self.authentication_history = self.authentication_history[
                -self.max_history_size :
            ]

    def get_authentication_history(self) -> List[AuthenticationResponse]:
        """Get authentication history."""
        return self.authentication_history.copy()

    def get_biometric_statistics(self) -> Dict[str, Any]:
        """Get biometric authentication statistics."""
        if not self.authentication_history:
            return {
                "total_authentications": 0,
                "success_rate": 0.0,
                "average_confidence": 0.0,
                "result_breakdown": {},
            }

        # Calculate statistics
        results = {}
        total_confidence = 0.0
        success_count = 0

        for auth in self.authentication_history:
            # Count results
            result = auth.result.value
            results[result] = results.get(result, 0) + 1

            # Sum confidence
            total_confidence += auth.confidence_score

            # Count successes
            if auth.result == AuthenticationResult.SUCCESS:
                success_count += 1

        return {
            "total_authentications": len(self.authentication_history),
            "success_rate": success_count / len(self.authentication_history),
            "average_confidence": total_confidence / len(self.authentication_history),
            "result_breakdown": results,
            "average_processing_time": sum(
                a.processing_time_ms for a in self.authentication_history
            )
            / len(self.authentication_history),
        }
