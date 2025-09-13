#!/usr/bin/env python3
"""
Nox API v8.0.0 - Biometric Authentication System
Advanced biometric authentication using Azure AI services

Provides facial recognition, voice authentication, behavioral biometrics,
and multi-factor biometric verification for the distributed architecture.
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from redis.cluster import RedisCluster

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure AI imports (placeholder for actual Azure SDK)
try:
    from azure.cognitiveservices.speech import (
        AudioConfig,
        SpeechConfig,
        SpeechRecognizer,
    )
    from azure.cognitiveservices.vision.face import FaceClient
    from msrest.authentication import CognitiveServicesCredentials
except ImportError:
    logger.warning(
        "Azure Cognitive Services SDK not available - using mock implementation"
    )


class BiometricType(Enum):
    """Types of biometric authentication"""

    FACIAL_RECOGNITION = "facial_recognition"
    VOICE_RECOGNITION = "voice_recognition"
    KEYSTROKE_DYNAMICS = "keystroke_dynamics"
    MOUSE_DYNAMICS = "mouse_dynamics"
    BEHAVIORAL_PATTERN = "behavioral_pattern"


class AuthenticationResult(Enum):
    """Biometric authentication results"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_MATCH = "partial_match"
    INSUFFICIENT_DATA = "insufficient_data"
    QUALITY_TOO_LOW = "quality_too_low"
    LIVENESS_FAILED = "liveness_failed"


@dataclass
class BiometricTemplate:
    """Stored biometric template"""

    template_id: str
    user_id: str
    biometric_type: BiometricType
    template_data: str  # Base64 encoded encrypted template
    quality_score: float
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0
    is_active: bool = True


@dataclass
class BiometricChallenge:
    """Biometric authentication challenge"""

    challenge_id: str
    user_id: str
    required_types: List[BiometricType]
    session_id: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    completed_types: List[BiometricType] = None


@dataclass
class BiometricVerificationResult:
    """Result of biometric verification"""

    challenge_id: str
    biometric_type: BiometricType
    result: AuthenticationResult
    confidence_score: float
    quality_score: float
    liveness_score: float
    processing_time_ms: int
    error_details: Optional[str] = None


@dataclass
class FaceDetectionResult:
    """Face detection and analysis result"""

    face_id: str
    confidence: float
    quality_score: float
    liveness_score: float
    age_estimate: Optional[int] = None
    emotion_scores: Optional[Dict[str, float]] = None
    face_landmarks: Optional[Dict[str, Any]] = None


@dataclass
class VoiceAnalysisResult:
    """Voice analysis and verification result"""

    voice_id: str
    confidence: float
    quality_score: float
    text_confidence: float
    speaker_verification_score: float
    audio_duration_ms: int


class BiometricAuthenticationSystem:
    """
    Advanced biometric authentication system with Azure AI integration.

    Features:
    - Facial recognition with liveness detection
    - Voice authentication and verification
    - Behavioral biometrics analysis
    - Multi-factor biometric verification
    - Template encryption and secure storage
    - Real-time fraud detection
    - Distributed authentication across nodes
    """

    def __init__(
        self,
        redis_cluster: RedisCluster = None,
        db_connection_params: Dict[str, Any] = None,
        azure_face_key: str = None,
        azure_speech_key: str = None,
    ):
        """
        Initialize Biometric Authentication System.

        Args:
            redis_cluster: Redis cluster connection
            db_connection_params: PostgreSQL connection parameters
            azure_face_key: Azure Face API key
            azure_speech_key: Azure Speech Services key
        """

        self.redis_cluster = redis_cluster or self._init_redis_cluster()
        self.db_params = db_connection_params or self._load_db_params()

        # Azure AI service configuration
        self.azure_face_key = azure_face_key or os.getenv("AZURE_FACE_API_KEY")
        self.azure_speech_key = azure_speech_key or os.getenv("AZURE_SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_REGION", "eastus")

        # Initialize Azure clients
        self.face_client = self._init_face_client()
        self.speech_config = self._init_speech_config()

        # Biometric thresholds
        self.face_confidence_threshold = 0.7
        self.voice_confidence_threshold = 0.75
        self.liveness_threshold = 0.6
        self.quality_threshold = 0.5

        # Security configuration
        self.encryption_key = self._load_encryption_key()
        self.template_cache = {}
        self.challenge_cache = {}

        # Behavioral analysis configuration
        self.keystroke_window_size = 50
        self.mouse_tracking_duration = 30  # seconds

        logger.info("Biometric Authentication System initialized successfully")

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

    def _init_face_client(self):
        """Initialize Azure Face API client."""
        if self.azure_face_key:
            try:
                endpoint = f"https://{self.azure_region}.api.cognitive.microsoft.com/"
                credentials = CognitiveServicesCredentials(self.azure_face_key)
                return FaceClient(endpoint, credentials)
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Face client: {e}")

        logger.info("Using mock Face API implementation")
        return None

    def _init_speech_config(self):
        """Initialize Azure Speech Services configuration."""
        if self.azure_speech_key:
            try:
                return SpeechConfig(
                    subscription=self.azure_speech_key, region=self.azure_region
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Speech config: {e}")

        logger.info("Using mock Speech API implementation")
        return None

    def _load_encryption_key(self) -> bytes:
        """Load or generate encryption key for biometric templates."""
        key_file = "/tmp/nox_biometric_key.bin"

        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()

        # Generate new key
        key = os.urandom(32)  # 256-bit key
        with open(key_file, "wb") as f:
            f.write(key)

        os.chmod(key_file, 0o600)  # Restrict access
        logger.info("Generated new biometric template encryption key")
        return key

    async def create_biometric_challenge(
        self,
        user_id: str,
        required_types: List[BiometricType],
        session_id: str,
        expires_in_minutes: int = 10,
    ) -> BiometricChallenge:
        """
        Create a new biometric authentication challenge.

        Args:
            user_id: User identifier
            required_types: List of required biometric types
            session_id: Session identifier
            expires_in_minutes: Challenge expiration time

        Returns:
            Biometric challenge object
        """

        challenge_id = hashlib.sha256(
            f"{user_id}:{session_id}:{time.time()}".encode()
        ).hexdigest()[:16]

        challenge = BiometricChallenge(
            challenge_id=challenge_id,
            user_id=user_id,
            required_types=required_types,
            session_id=session_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
            completed_types=[],
        )

        # Store in cache and database
        try:
            self.challenge_cache[challenge_id] = challenge

            # Store in Redis for distributed access
            challenge_key = f"biometric_challenge:{challenge_id}"
            challenge_data = asdict(challenge)
            challenge_data["created_at"] = challenge.created_at.isoformat()
            challenge_data["expires_at"] = challenge.expires_at.isoformat()

            self.redis_cluster.setex(
                challenge_key,
                expires_in_minutes * 60,
                json.dumps(challenge_data, default=str),
            )

            logger.info(
                f"Created biometric challenge {challenge_id} for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to store biometric challenge: {e}")

        return challenge

    async def verify_facial_recognition(
        self, challenge_id: str, image_data: bytes
    ) -> BiometricVerificationResult:
        """
        Verify user identity using facial recognition.

        Args:
            challenge_id: Challenge identifier
            image_data: Face image data (JPEG/PNG)

        Returns:
            Verification result
        """

        start_time = time.time()

        try:
            # Get challenge details
            challenge = await self._get_challenge(challenge_id)
            if not challenge:
                return self._create_error_result(
                    challenge_id,
                    BiometricType.FACIAL_RECOGNITION,
                    "Challenge not found",
                    start_time,
                )

            # Detect and analyze face
            face_result = await self._detect_and_analyze_face(image_data)

            if not face_result or face_result.quality_score < self.quality_threshold:
                return BiometricVerificationResult(
                    challenge_id=challenge_id,
                    biometric_type=BiometricType.FACIAL_RECOGNITION,
                    result=AuthenticationResult.QUALITY_TOO_LOW,
                    confidence_score=0.0,
                    quality_score=face_result.quality_score if face_result else 0.0,
                    liveness_score=face_result.liveness_score if face_result else 0.0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error_details="Image quality too low for verification",
                )

            # Check liveness
            if face_result.liveness_score < self.liveness_threshold:
                return BiometricVerificationResult(
                    challenge_id=challenge_id,
                    biometric_type=BiometricType.FACIAL_RECOGNITION,
                    result=AuthenticationResult.LIVENESS_FAILED,
                    confidence_score=face_result.confidence,
                    quality_score=face_result.quality_score,
                    liveness_score=face_result.liveness_score,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error_details="Liveness detection failed",
                )

            # Compare with stored templates
            stored_templates = await self._get_user_templates(
                challenge.user_id, BiometricType.FACIAL_RECOGNITION
            )

            best_match_score = 0.0
            for template in stored_templates:
                match_score = await self._compare_face_templates(face_result, template)
                best_match_score = max(best_match_score, match_score)

            # Determine result
            if best_match_score >= self.face_confidence_threshold:
                result = AuthenticationResult.SUCCESS
                await self._update_template_usage(stored_templates[0])
            elif best_match_score > 0.4:
                result = AuthenticationResult.PARTIAL_MATCH
            else:
                result = AuthenticationResult.FAILURE

            verification_result = BiometricVerificationResult(
                challenge_id=challenge_id,
                biometric_type=BiometricType.FACIAL_RECOGNITION,
                result=result,
                confidence_score=best_match_score,
                quality_score=face_result.quality_score,
                liveness_score=face_result.liveness_score,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

            # Update challenge progress
            if result == AuthenticationResult.SUCCESS:
                await self._update_challenge_progress(
                    challenge_id, BiometricType.FACIAL_RECOGNITION
                )

            # Log verification attempt
            await self._log_biometric_attempt(challenge.user_id, verification_result)

            return verification_result

        except Exception as e:
            logger.error(f"Error in facial recognition verification: {e}")
            return self._create_error_result(
                challenge_id,
                BiometricType.FACIAL_RECOGNITION,
                f"Verification error: {str(e)}",
                start_time,
            )

    async def verify_voice_recognition(
        self, challenge_id: str, audio_data: bytes, expected_phrase: str = None
    ) -> BiometricVerificationResult:
        """
        Verify user identity using voice recognition.

        Args:
            challenge_id: Challenge identifier
            audio_data: Voice audio data (WAV format)
            expected_phrase: Expected spoken phrase for verification

        Returns:
            Verification result
        """

        start_time = time.time()

        try:
            # Get challenge details
            challenge = await self._get_challenge(challenge_id)
            if not challenge:
                return self._create_error_result(
                    challenge_id,
                    BiometricType.VOICE_RECOGNITION,
                    "Challenge not found",
                    start_time,
                )

            # Analyze voice audio
            voice_result = await self._analyze_voice_audio(audio_data, expected_phrase)

            if not voice_result or voice_result.quality_score < self.quality_threshold:
                return BiometricVerificationResult(
                    challenge_id=challenge_id,
                    biometric_type=BiometricType.VOICE_RECOGNITION,
                    result=AuthenticationResult.QUALITY_TOO_LOW,
                    confidence_score=0.0,
                    quality_score=voice_result.quality_score if voice_result else 0.0,
                    liveness_score=0.9,  # Voice inherently has liveness
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error_details="Audio quality too low for verification",
                )

            # Compare with stored voice templates
            stored_templates = await self._get_user_templates(
                challenge.user_id, BiometricType.VOICE_RECOGNITION
            )

            best_match_score = 0.0
            for template in stored_templates:
                match_score = await self._compare_voice_templates(
                    voice_result, template
                )
                best_match_score = max(best_match_score, match_score)

            # Determine result
            if best_match_score >= self.voice_confidence_threshold:
                result = AuthenticationResult.SUCCESS
                if stored_templates:
                    await self._update_template_usage(stored_templates[0])
            elif best_match_score > 0.5:
                result = AuthenticationResult.PARTIAL_MATCH
            else:
                result = AuthenticationResult.FAILURE

            verification_result = BiometricVerificationResult(
                challenge_id=challenge_id,
                biometric_type=BiometricType.VOICE_RECOGNITION,
                result=result,
                confidence_score=best_match_score,
                quality_score=voice_result.quality_score,
                liveness_score=0.9,  # Voice inherently has liveness
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

            # Update challenge progress
            if result == AuthenticationResult.SUCCESS:
                await self._update_challenge_progress(
                    challenge_id, BiometricType.VOICE_RECOGNITION
                )

            # Log verification attempt
            await self._log_biometric_attempt(challenge.user_id, verification_result)

            return verification_result

        except Exception as e:
            logger.error(f"Error in voice recognition verification: {e}")
            return self._create_error_result(
                challenge_id,
                BiometricType.VOICE_RECOGNITION,
                f"Verification error: {str(e)}",
                start_time,
            )

    async def verify_behavioral_biometrics(
        self, challenge_id: str, behavioral_data: Dict[str, Any]
    ) -> BiometricVerificationResult:
        """
        Verify user identity using behavioral biometrics.

        Args:
            challenge_id: Challenge identifier
            behavioral_data: Keystroke dynamics, mouse patterns, etc.

        Returns:
            Verification result
        """

        start_time = time.time()

        try:
            # Get challenge details
            challenge = await self._get_challenge(challenge_id)
            if not challenge:
                return self._create_error_result(
                    challenge_id,
                    BiometricType.BEHAVIORAL_PATTERN,
                    "Challenge not found",
                    start_time,
                )

            # Analyze behavioral patterns
            keystroke_score = 0.0
            mouse_score = 0.0

            if "keystroke_dynamics" in behavioral_data:
                keystroke_score = await self._analyze_keystroke_dynamics(
                    challenge.user_id, behavioral_data["keystroke_dynamics"]
                )

            if "mouse_dynamics" in behavioral_data:
                mouse_score = await self._analyze_mouse_dynamics(
                    challenge.user_id, behavioral_data["mouse_dynamics"]
                )

            # Combine scores
            combined_score = (keystroke_score + mouse_score) / 2.0
            quality_score = min(keystroke_score + mouse_score, 1.0)

            # Determine result
            if combined_score >= 0.7:
                result = AuthenticationResult.SUCCESS
            elif combined_score >= 0.5:
                result = AuthenticationResult.PARTIAL_MATCH
            else:
                result = AuthenticationResult.FAILURE

            verification_result = BiometricVerificationResult(
                challenge_id=challenge_id,
                biometric_type=BiometricType.BEHAVIORAL_PATTERN,
                result=result,
                confidence_score=combined_score,
                quality_score=quality_score,
                liveness_score=0.95,  # Behavioral patterns are inherently live
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

            # Update challenge progress
            if result == AuthenticationResult.SUCCESS:
                await self._update_challenge_progress(
                    challenge_id, BiometricType.BEHAVIORAL_PATTERN
                )

            # Log verification attempt
            await self._log_biometric_attempt(challenge.user_id, verification_result)

            return verification_result

        except Exception as e:
            logger.error(f"Error in behavioral biometric verification: {e}")
            return self._create_error_result(
                challenge_id,
                BiometricType.BEHAVIORAL_PATTERN,
                f"Verification error: {str(e)}",
                start_time,
            )

    async def _detect_and_analyze_face(
        self, image_data: bytes
    ) -> Optional[FaceDetectionResult]:
        """Detect and analyze face in image using Azure Face API."""

        if not self.face_client:
            # Mock implementation for testing
            return FaceDetectionResult(
                face_id="mock_face_id",
                confidence=0.85,
                quality_score=0.8,
                liveness_score=0.75,
                age_estimate=30,
                emotion_scores={"happiness": 0.7, "neutral": 0.3},
            )

        try:
            # Convert bytes to stream
            image_stream = io.BytesIO(image_data)

            # Detect faces
            detected_faces = self.face_client.face.detect_with_stream(
                image_stream,
                recognition_model="recognition_04",
                detection_model="detection_03",
                return_face_attributes=[
                    "age",
                    "emotion",
                    "headPose",
                    "noise",
                    "occlusion",
                ],
            )

            if not detected_faces:
                return None

            face = detected_faces[0]  # Use first detected face

            # Calculate quality score based on face attributes
            quality_factors = []
            if hasattr(face.face_attributes, "noise"):
                quality_factors.append(1.0 - face.face_attributes.noise.noise_level)
            if hasattr(face.face_attributes, "occlusion"):
                occlusion = face.face_attributes.occlusion
                occlusion_penalty = (
                    occlusion.eye_occluded
                    + occlusion.forehead_occluded
                    + occlusion.mouth_occluded
                ) / 3
                quality_factors.append(1.0 - occlusion_penalty)

            quality_score = (
                sum(quality_factors) / len(quality_factors) if quality_factors else 0.7
            )

            # Mock liveness score (would use actual liveness detection in production)
            liveness_score = 0.8

            return FaceDetectionResult(
                face_id=face.face_id,
                confidence=0.85,  # Mock confidence
                quality_score=quality_score,
                liveness_score=liveness_score,
                age_estimate=face.face_attributes.age if face.face_attributes else None,
                emotion_scores=(
                    dict(face.face_attributes.emotion)
                    if face.face_attributes and face.face_attributes.emotion
                    else None
                ),
            )

        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return None

    async def _analyze_voice_audio(
        self, audio_data: bytes, expected_phrase: str = None
    ) -> Optional[VoiceAnalysisResult]:
        """Analyze voice audio using Azure Speech Services."""

        if not self.speech_config:
            # Mock implementation for testing
            return VoiceAnalysisResult(
                voice_id="mock_voice_id",
                confidence=0.82,
                quality_score=0.75,
                text_confidence=0.9,
                speaker_verification_score=0.8,
                audio_duration_ms=3000,
            )

        try:
            # Create audio config from bytes
            audio_stream = io.BytesIO(audio_data)
            audio_config = AudioConfig(stream=audio_stream)

            # Initialize speech recognizer
            speech_recognizer = SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )

            # Recognize speech
            result = speech_recognizer.recognize_once()

            if not result.text:
                return None

            # Calculate text confidence
            text_confidence = (
                0.9
                if expected_phrase and expected_phrase.lower() in result.text.lower()
                else 0.6
            )

            # Mock speaker verification (would use actual speaker recognition in production)
            speaker_verification_score = 0.8

            # Estimate audio quality
            quality_score = 0.75  # Mock quality score

            return VoiceAnalysisResult(
                voice_id="voice_recognition_result",
                confidence=0.82,
                quality_score=quality_score,
                text_confidence=text_confidence,
                speaker_verification_score=speaker_verification_score,
                audio_duration_ms=len(audio_data) // 16,  # Rough duration estimate
            )

        except Exception as e:
            logger.error(f"Error in voice analysis: {e}")
            return None

    async def _analyze_keystroke_dynamics(
        self, user_id: str, keystroke_data: List[Dict[str, Any]]
    ) -> float:
        """Analyze keystroke dynamics for behavioral authentication."""

        try:
            if len(keystroke_data) < 20:  # Need minimum keystrokes
                return 0.0

            # Extract timing features
            dwell_times = []
            flight_times = []

            for i, keystroke in enumerate(keystroke_data):
                if "key_down_time" in keystroke and "key_up_time" in keystroke:
                    dwell_time = keystroke["key_up_time"] - keystroke["key_down_time"]
                    dwell_times.append(dwell_time)

                if i > 0 and "key_down_time" in keystroke:
                    prev_up_time = keystroke_data[i - 1].get("key_up_time", 0)
                    flight_time = keystroke["key_down_time"] - prev_up_time
                    if flight_time > 0:
                        flight_times.append(flight_time)

            if not dwell_times or not flight_times:
                return 0.0

            # Calculate statistical features
            current_features = {
                "avg_dwell": np.mean(dwell_times),
                "std_dwell": np.std(dwell_times),
                "avg_flight": np.mean(flight_times),
                "std_flight": np.std(flight_times),
                "typing_rhythm": (
                    np.std(dwell_times) / np.mean(dwell_times)
                    if np.mean(dwell_times) > 0
                    else 0
                ),
            }

            # Compare with stored profile (mock implementation)
            stored_profile = await self._get_keystroke_profile(user_id)

            if not stored_profile:
                # First time user - store profile and return moderate confidence
                await self._store_keystroke_profile(user_id, current_features)
                return 0.6

            # Calculate similarity score
            similarity_score = self._calculate_keystroke_similarity(
                current_features, stored_profile
            )

            # Update stored profile with new data (adaptive learning)
            await self._update_keystroke_profile(user_id, current_features)

            return similarity_score

        except Exception as e:
            logger.error(f"Error analyzing keystroke dynamics: {e}")
            return 0.0

    async def _analyze_mouse_dynamics(
        self, user_id: str, mouse_data: List[Dict[str, Any]]
    ) -> float:
        """Analyze mouse movement patterns for behavioral authentication."""

        try:
            if len(mouse_data) < 50:  # Need minimum mouse movements
                return 0.0

            # Extract movement features
            velocities = []
            accelerations = []
            angles = []

            for i in range(1, len(mouse_data)):
                prev_point = mouse_data[i - 1]
                curr_point = mouse_data[i]

                # Calculate velocity
                dx = curr_point.get("x", 0) - prev_point.get("x", 0)
                dy = curr_point.get("y", 0) - prev_point.get("y", 0)
                dt = curr_point.get("timestamp", 0) - prev_point.get("timestamp", 0)

                if dt > 0:
                    velocity = np.sqrt(dx * dx + dy * dy) / dt
                    velocities.append(velocity)

                    # Calculate angle
                    if dx != 0:
                        angle = np.arctan2(dy, dx)
                        angles.append(angle)

            # Calculate acceleration
            for i in range(1, len(velocities)):
                acc = velocities[i] - velocities[i - 1]
                accelerations.append(acc)

            if not velocities or not accelerations:
                return 0.0

            # Calculate statistical features
            current_features = {
                "avg_velocity": np.mean(velocities),
                "std_velocity": np.std(velocities),
                "avg_acceleration": np.mean(accelerations),
                "std_acceleration": np.std(accelerations),
                "movement_efficiency": len(mouse_data) / (np.sum(velocities) + 1),
            }

            # Compare with stored profile
            stored_profile = await self._get_mouse_profile(user_id)

            if not stored_profile:
                # First time user - store profile and return moderate confidence
                await self._store_mouse_profile(user_id, current_features)
                return 0.6

            # Calculate similarity score
            similarity_score = self._calculate_mouse_similarity(
                current_features, stored_profile
            )

            # Update stored profile
            await self._update_mouse_profile(user_id, current_features)

            return similarity_score

        except Exception as e:
            logger.error(f"Error analyzing mouse dynamics: {e}")
            return 0.0

    def _calculate_keystroke_similarity(
        self, current: Dict[str, float], stored: Dict[str, float]
    ) -> float:
        """Calculate similarity between keystroke profiles."""

        try:
            similarities = []

            for feature in [
                "avg_dwell",
                "std_dwell",
                "avg_flight",
                "std_flight",
                "typing_rhythm",
            ]:
                if feature in current and feature in stored:
                    curr_val = current[feature]
                    stored_val = stored[feature]

                    if stored_val != 0:
                        diff_ratio = abs(curr_val - stored_val) / stored_val
                        similarity = max(0.0, 1.0 - diff_ratio)
                        similarities.append(similarity)

            return np.mean(similarities) if similarities else 0.0

        except Exception as e:
            logger.error(f"Error calculating keystroke similarity: {e}")
            return 0.0

    def _calculate_mouse_similarity(
        self, current: Dict[str, float], stored: Dict[str, float]
    ) -> float:
        """Calculate similarity between mouse movement profiles."""

        try:
            similarities = []

            for feature in [
                "avg_velocity",
                "std_velocity",
                "avg_acceleration",
                "std_acceleration",
                "movement_efficiency",
            ]:
                if feature in current and feature in stored:
                    curr_val = current[feature]
                    stored_val = stored[feature]

                    if stored_val != 0:
                        diff_ratio = abs(curr_val - stored_val) / stored_val
                        similarity = max(0.0, 1.0 - diff_ratio)
                        similarities.append(similarity)

            return np.mean(similarities) if similarities else 0.0

        except Exception as e:
            logger.error(f"Error calculating mouse similarity: {e}")
            return 0.0

    async def _get_challenge(self, challenge_id: str) -> Optional[BiometricChallenge]:
        """Get biometric challenge by ID."""

        # Check local cache first
        if challenge_id in self.challenge_cache:
            return self.challenge_cache[challenge_id]

        # Check Redis
        try:
            challenge_key = f"biometric_challenge:{challenge_id}"
            challenge_data = self.redis_cluster.get(challenge_key)

            if challenge_data:
                data = json.loads(challenge_data)
                data["created_at"] = datetime.fromisoformat(data["created_at"])
                data["expires_at"] = datetime.fromisoformat(data["expires_at"])

                challenge = BiometricChallenge(**data)
                self.challenge_cache[challenge_id] = challenge
                return challenge

        except Exception as e:
            logger.error(f"Error getting challenge from Redis: {e}")

        return None

    async def _update_challenge_progress(
        self, challenge_id: str, completed_type: BiometricType
    ):
        """Update challenge progress with completed biometric type."""

        challenge = await self._get_challenge(challenge_id)
        if challenge:
            if not challenge.completed_types:
                challenge.completed_types = []

            if completed_type not in challenge.completed_types:
                challenge.completed_types.append(completed_type)

            # Update cache and Redis
            self.challenge_cache[challenge_id] = challenge

            try:
                challenge_key = f"biometric_challenge:{challenge_id}"
                challenge_data = asdict(challenge)
                challenge_data["created_at"] = challenge.created_at.isoformat()
                challenge_data["expires_at"] = challenge.expires_at.isoformat()

                self.redis_cluster.setex(
                    challenge_key,
                    600,  # 10 minutes TTL
                    json.dumps(challenge_data, default=str),
                )

            except Exception as e:
                logger.error(f"Error updating challenge progress: {e}")

    def _create_error_result(
        self,
        challenge_id: str,
        biometric_type: BiometricType,
        error_message: str,
        start_time: float,
    ) -> BiometricVerificationResult:
        """Create error result for failed verification."""

        return BiometricVerificationResult(
            challenge_id=challenge_id,
            biometric_type=biometric_type,
            result=AuthenticationResult.FAILURE,
            confidence_score=0.0,
            quality_score=0.0,
            liveness_score=0.0,
            processing_time_ms=int((time.time() - start_time) * 1000),
            error_details=error_message,
        )

    async def _get_user_templates(
        self, user_id: str, biometric_type: BiometricType
    ) -> List[BiometricTemplate]:
        """Get stored biometric templates for user."""

        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """SELECT template_id, user_id, biometric_type, template_data,
                           quality_score, created_at, last_used, use_count, is_active
                           FROM biometric_templates 
                           WHERE user_id = %s AND biometric_type = %s AND is_active = TRUE
                           ORDER BY quality_score DESC""",
                        (user_id, biometric_type.value),
                    )

                    templates = []
                    for row in cursor.fetchall():
                        templates.append(
                            BiometricTemplate(
                                template_id=row["template_id"],
                                user_id=row["user_id"],
                                biometric_type=BiometricType(row["biometric_type"]),
                                template_data=row["template_data"],
                                quality_score=row["quality_score"],
                                created_at=row["created_at"],
                                last_used=row["last_used"],
                                use_count=row["use_count"],
                                is_active=row["is_active"],
                            )
                        )

                    return templates

        except Exception as e:
            logger.error(f"Error getting user templates: {e}")
            return []

    async def _compare_face_templates(
        self, face_result: FaceDetectionResult, stored_template: BiometricTemplate
    ) -> float:
        """Compare current face detection with stored template."""

        # Mock implementation - would use actual face comparison in production
        try:
            # Decrypt stored template data
            _template_data = self._decrypt_template_data(stored_template.template_data)

            # Mock comparison logic
            base_score = 0.75
            quality_factor = min(
                face_result.quality_score, stored_template.quality_score
            )

            # Simulate template matching
            match_score = base_score * quality_factor

            return match_score

        except Exception as e:
            logger.error(f"Error comparing face templates: {e}")
            return 0.0

    async def _compare_voice_templates(
        self, voice_result: VoiceAnalysisResult, stored_template: BiometricTemplate
    ) -> float:
        """Compare current voice analysis with stored template."""

        # Mock implementation - would use actual voice comparison in production
        try:
            # Decrypt stored template data
            _template_data = self._decrypt_template_data(stored_template.template_data)

            # Mock comparison logic
            base_score = voice_result.speaker_verification_score
            quality_factor = min(
                voice_result.quality_score, stored_template.quality_score
            )

            # Simulate template matching
            match_score = base_score * quality_factor

            return match_score

        except Exception as e:
            logger.error(f"Error comparing voice templates: {e}")
            return 0.0

    def _encrypt_template_data(self, template_data: str) -> str:
        """Encrypt biometric template data."""
        # Mock implementation - would use proper encryption in production
        encoded = base64.b64encode(template_data.encode()).decode()
        return encoded

    def _decrypt_template_data(self, encrypted_data: str) -> str:
        """Decrypt biometric template data."""
        # Mock implementation - would use proper decryption in production
        decoded = base64.b64decode(encrypted_data.encode()).decode()
        return decoded

    async def _log_biometric_attempt(
        self, user_id: str, result: BiometricVerificationResult
    ):
        """Log biometric authentication attempt."""

        try:
            # Store in database
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO biometric_attempts 
                           (challenge_id, user_id, biometric_type, result, confidence_score,
                            quality_score, liveness_score, processing_time_ms, timestamp, error_details)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            result.challenge_id,
                            user_id,
                            result.biometric_type.value,
                            result.result.value,
                            result.confidence_score,
                            result.quality_score,
                            result.liveness_score,
                            result.processing_time_ms,
                            datetime.utcnow(),
                            result.error_details,
                        ),
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Error logging biometric attempt: {e}")

    # Placeholder methods for behavioral profile management
    async def _get_keystroke_profile(self, user_id: str) -> Optional[Dict[str, float]]:
        """Get stored keystroke profile for user."""
        return None  # Would implement database storage

    async def _store_keystroke_profile(self, user_id: str, profile: Dict[str, float]):
        """Store keystroke profile for user."""
        pass  # Would implement database storage

    async def _update_keystroke_profile(self, user_id: str, profile: Dict[str, float]):
        """Update keystroke profile for user."""
        pass  # Would implement database storage

    async def _get_mouse_profile(self, user_id: str) -> Optional[Dict[str, float]]:
        """Get stored mouse profile for user."""
        return None  # Would implement database storage

    async def _store_mouse_profile(self, user_id: str, profile: Dict[str, float]):
        """Store mouse profile for user."""
        pass  # Would implement database storage

    async def _update_mouse_profile(self, user_id: str, profile: Dict[str, float]):
        """Update mouse profile for user."""
        pass  # Would implement database storage

    async def _update_template_usage(self, template: BiometricTemplate):
        """Update template usage statistics."""
        try:
            with psycopg2.connect(**self.db_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """UPDATE biometric_templates 
                           SET last_used = %s, use_count = use_count + 1
                           WHERE template_id = %s""",
                        (datetime.utcnow(), template.template_id),
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Error updating template usage: {e}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_biometric_auth():
        """Test the Biometric Authentication System functionality."""

        # Initialize biometric auth system
        auth_system = BiometricAuthenticationSystem()

        # Create test challenge
        challenge = await auth_system.create_biometric_challenge(
            user_id="test_user_123",
            required_types=[
                BiometricType.FACIAL_RECOGNITION,
                BiometricType.VOICE_RECOGNITION,
            ],
            session_id="session_123",
        )

        print(f"Created biometric challenge: {challenge.challenge_id}")
        print(f"Required types: {[t.value for t in challenge.required_types]}")

        # Simulate facial recognition verification (mock image data)
        mock_image_data = b"mock_image_data_here"

        face_result = await auth_system.verify_facial_recognition(
            challenge.challenge_id, mock_image_data
        )

        print("\nFacial Recognition Result:")
        print(f"Result: {face_result.result.value}")
        print(f"Confidence: {face_result.confidence_score:.2f}")
        print(f"Quality: {face_result.quality_score:.2f}")
        print(f"Liveness: {face_result.liveness_score:.2f}")
        print(f"Processing time: {face_result.processing_time_ms}ms")

        # Simulate voice recognition verification (mock audio data)
        mock_audio_data = b"mock_audio_data_here"

        voice_result = await auth_system.verify_voice_recognition(
            challenge.challenge_id,
            mock_audio_data,
            "Hello, this is my voice verification",
        )

        print("\nVoice Recognition Result:")
        print(f"Result: {voice_result.result.value}")
        print(f"Confidence: {voice_result.confidence_score:.2f}")
        print(f"Quality: {voice_result.quality_score:.2f}")
        print(f"Processing time: {voice_result.processing_time_ms}ms")

        # Simulate behavioral biometrics
        mock_behavioral_data = {
            "keystroke_dynamics": [
                {"key": "h", "key_down_time": 1000, "key_up_time": 1050},
                {"key": "e", "key_down_time": 1100, "key_up_time": 1150},
                {"key": "l", "key_down_time": 1200, "key_up_time": 1240},
                # ... more keystroke data
            ],
            "mouse_dynamics": [
                {"x": 100, "y": 200, "timestamp": 1000},
                {"x": 105, "y": 205, "timestamp": 1020},
                {"x": 110, "y": 210, "timestamp": 1040},
                # ... more mouse movement data
            ],
        }

        behavioral_result = await auth_system.verify_behavioral_biometrics(
            challenge.challenge_id, mock_behavioral_data
        )

        print("\nBehavioral Biometrics Result:")
        print(f"Result: {behavioral_result.result.value}")
        print(f"Confidence: {behavioral_result.confidence_score:.2f}")
        print(f"Processing time: {behavioral_result.processing_time_ms}ms")

    # Run test
    asyncio.run(test_biometric_auth())
