"""
Version matching utility for Python versions.

This module provides intelligent version matching that:
- Properly parses semantic versions
- Provides fuzzy matching for common typos
- Suggests similar versions when exact match not found
- Handles the "3.1" vs "3.10/3.11" confusion

Example:
    >>> matcher = VersionMatcher(["3.9.23", "3.10.18", "3.11.13", "3.12.11", "3.13.7"])
    >>> result = matcher.find_match("3.1")
    >>> if not result.exact_match:
    ...     print(f"Suggestions: {result.suggestions}")
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import re


@dataclass
class VersionMatch:
    """Result of a version matching operation."""
    
    requested: str
    exact_match: Optional[str] = None
    suggestions: List[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
    
    @property
    def found(self) -> bool:
        """Returns True if an exact match was found."""
        return self.exact_match is not None


class VersionMatcher:
    """
    Intelligent version matcher for Python versions.
    
    Handles common version matching scenarios including:
    - Exact version matching (3.11.13 → 3.11.13)
    - Partial version matching (3.11 → 3.11.13)
    - Fuzzy matching for typos (3.1 → suggests 3.10, 3.11)
    """
    
    def __init__(self, available_versions: List[str], arch: str = "x64"):
        """
        Initialize the version matcher.
        
        Args:
            available_versions: List of available version strings (e.g., ["3.11.13", "3.12.11"])
            arch: Architecture string (default: "x64")
        """
        self.available_versions = available_versions
        self.arch = arch
        # Parse and sort versions
        self.parsed_versions = [self._parse_version(v) for v in available_versions]
    
    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """
        Parse a version string into a tuple of integers.
        
        Args:
            version_str: Version string like "3.11.13"
            
        Returns:
            Tuple of integers like (3, 11, 13)
        """
        # Remove any non-numeric suffixes (e.g., "3.11rc1" -> "3.11")
        cleaned = re.match(r'^(\d+(?:\.\d+)*)', version_str)
        if not cleaned:
            return (0,)
        
        parts = cleaned.group(1).split('.')
        return tuple(int(p) for p in parts)
    
    def _version_distance(self, v1: Tuple[int, ...], v2: Tuple[int, ...]) -> float:
        """
        Calculate a distance metric between two version tuples.
        Lower distance means more similar versions.
        
        Args:
            v1: First version tuple
            v2: Second version tuple
            
        Returns:
            Distance value (lower is closer)
        """
        # Pad versions to same length
        max_len = max(len(v1), len(v2))
        v1_padded = v1 + (0,) * (max_len - len(v1))
        v2_padded = v2 + (0,) * (max_len - len(v2))
        
        # Weight earlier components more heavily (major > minor > patch)
        weights = [100, 10, 1] + [0.1] * (max_len - 3)
        distance = sum(w * abs(a - b) for w, a, b in zip(weights, v1_padded, v2_padded))
        return distance
    
    def find_match(self, requested_version: str) -> VersionMatch:
        """
        Find a matching version for the requested version string.
        
        Args:
            requested_version: The version string to find (e.g., "3.1", "3.11", "3.11.13")
            
        Returns:
            VersionMatch object with results
        """
        if not requested_version:
            return VersionMatch(
                requested=requested_version,
                error_message="Version string cannot be empty"
            )
        
        requested_parsed = self._parse_version(requested_version)
        
        # Try exact match first
        for available in self.available_versions:
            available_parsed = self._parse_version(available)
            if available_parsed == requested_parsed:
                return VersionMatch(
                    requested=requested_version,
                    exact_match=available
                )
        
        # Try prefix matching (e.g., "3.11" matches "3.11.13")
        matches = []
        for available in self.available_versions:
            available_parsed = self._parse_version(available)
            # Check if requested is a prefix of available
            if len(requested_parsed) <= len(available_parsed):
                if available_parsed[:len(requested_parsed)] == requested_parsed:
                    matches.append(available)
        
        if matches:
            # Return the latest version among matches
            latest = max(matches, key=lambda v: self._parse_version(v))
            return VersionMatch(
                requested=requested_version,
                exact_match=latest
            )
        
        # No match found - provide suggestions
        # Calculate distances to all available versions
        distances = [
            (available, self._version_distance(requested_parsed, self._parse_version(available)))
            for available in self.available_versions
        ]
        
        # Sort by distance and take top 3 suggestions
        distances.sort(key=lambda x: x[1])
        suggestions = [v for v, _ in distances[:3]]
        
        # Build error message
        available_str = " ".join([f"{v} ({self.arch})" for v in self.available_versions])
        error_msg = f"Version {requested_version} with arch {self.arch} not found. Available versions: {available_str}"
        
        return VersionMatch(
            requested=requested_version,
            suggestions=suggestions,
            error_message=error_msg
        )


def match_python_version(
    requested_version: str,
    available_versions: List[str],
    arch: str = "x64"
) -> VersionMatch:
    """
    Convenience function to match a Python version.
    
    Args:
        requested_version: The version to find (e.g., "3.1", "3.11")
        available_versions: List of available versions
        arch: Architecture (default: "x64")
        
    Returns:
        VersionMatch object with results
        
    Example:
        >>> result = match_python_version("3.1", ["3.9.23", "3.10.18", "3.11.13"])
        >>> if not result.found:
        ...     print(result.error_message)
        ...     print(f"Did you mean: {result.suggestions[0]}?")
    """
    matcher = VersionMatcher(available_versions, arch)
    return matcher.find_match(requested_version)
