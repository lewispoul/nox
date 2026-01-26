"""
Tests for version_matcher module.

Tests the intelligent version matching functionality including:
- Exact version matching
- Partial version matching  
- Fuzzy matching for typos
- Helpful error messages with suggestions
"""

import pytest
from api.utils.version_matcher import VersionMatcher, match_python_version, VersionMatch


# Standard Python versions available in most environments
AVAILABLE_VERSIONS = ["3.9.23", "3.10.18", "3.11.13", "3.12.11", "3.13.7"]


class TestVersionMatcher:
    """Test suite for VersionMatcher class."""
    
    def test_exact_version_match(self):
        """Test exact version string matching."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("3.11.13")
        
        assert result.found
        assert result.exact_match == "3.11.13"
        assert result.error_message is None
    
    def test_partial_version_match_major_minor(self):
        """Test matching with major.minor (e.g., '3.11' matches '3.11.13')."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("3.11")
        
        assert result.found
        assert result.exact_match == "3.11.13"
        assert result.error_message is None
    
    def test_partial_version_match_major_only(self):
        """Test matching with major version only (e.g., '3' matches latest 3.x)."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("3")
        
        assert result.found
        # Should match the latest 3.x version
        assert result.exact_match == "3.13.7"
    
    def test_typo_3_1_for_3_11(self):
        """Test the specific bug case: '3.1' when '3.11' was intended."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("3.1")
        
        # Should NOT find exact match
        assert not result.found
        assert result.exact_match is None
        
        # Should provide suggestions
        assert len(result.suggestions) > 0
        # Should suggest 3.11 and 3.10 as they are closest
        assert "3.11.13" in result.suggestions or "3.10.18" in result.suggestions
        
        # Should have helpful error message
        assert "3.1" in result.error_message
        assert "not found" in result.error_message
        assert "Available versions:" in result.error_message
    
    def test_typo_3_1_provides_correct_error_message(self):
        """Test that the error message format matches expected output."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS, arch="x64")
        result = matcher.find_match("3.1")
        
        # Check error message format
        expected_start = "Version 3.1 with arch x64 not found"
        assert result.error_message.startswith(expected_start)
        
        # Check all available versions are listed
        for version in AVAILABLE_VERSIONS:
            assert version in result.error_message
            assert "(x64)" in result.error_message
    
    def test_nonexistent_version_provides_suggestions(self):
        """Test that searching for non-existent version provides suggestions."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("3.8")
        
        assert not result.found
        assert len(result.suggestions) > 0
        # Should suggest 3.9 as closest
        assert "3.9.23" in result.suggestions
    
    def test_future_version_provides_suggestions(self):
        """Test that searching for future version provides suggestions."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("3.14")
        
        assert not result.found
        assert len(result.suggestions) > 0
        # Should suggest 3.13 as closest
        assert "3.13.7" in result.suggestions
    
    def test_multiple_partial_matches(self):
        """Test that partial match returns latest version."""
        versions = ["3.11.1", "3.11.10", "3.11.13"]
        matcher = VersionMatcher(versions)
        result = matcher.find_match("3.11")
        
        assert result.found
        # Should return the latest 3.11.x
        assert result.exact_match == "3.11.13"
    
    def test_empty_version_string(self):
        """Test handling of empty version string."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("")
        
        assert not result.found
        assert "cannot be empty" in result.error_message
    
    def test_invalid_version_format(self):
        """Test handling of invalid version format."""
        matcher = VersionMatcher(AVAILABLE_VERSIONS)
        result = matcher.find_match("abc")
        
        # Should not crash, should provide suggestions
        assert not result.found
        assert len(result.suggestions) > 0
    
    def test_version_with_suffix(self):
        """Test handling of versions with suffixes like rc, alpha, etc."""
        versions = ["3.11.1", "3.12.0rc1", "3.12.1"]
        matcher = VersionMatcher(versions)
        
        # Should be able to parse and match
        result = matcher.find_match("3.12")
        assert result.found
        # Should prefer stable version over rc
        assert result.exact_match in ["3.12.1", "3.12.0rc1"]
    
    def test_architecture_in_error_message(self):
        """Test that architecture is correctly included in error messages."""
        for arch in ["x64", "x86", "arm64"]:
            matcher = VersionMatcher(AVAILABLE_VERSIONS, arch=arch)
            result = matcher.find_match("3.1")
            
            assert f"arch {arch}" in result.error_message
            assert f"({arch})" in result.error_message


class TestMatchPythonVersionConvenience:
    """Test suite for the convenience function match_python_version."""
    
    def test_convenience_function_exact_match(self):
        """Test convenience function with exact match."""
        result = match_python_version("3.11.13", AVAILABLE_VERSIONS)
        
        assert result.found
        assert result.exact_match == "3.11.13"
    
    def test_convenience_function_typo(self):
        """Test convenience function with typo case."""
        result = match_python_version("3.1", AVAILABLE_VERSIONS)
        
        assert not result.found
        assert len(result.suggestions) > 0
        assert "3.1" in result.error_message
    
    def test_convenience_function_custom_arch(self):
        """Test convenience function with custom architecture."""
        result = match_python_version("3.1", AVAILABLE_VERSIONS, arch="arm64")
        
        assert "arm64" in result.error_message


class TestVersionMatchDataclass:
    """Test suite for VersionMatch dataclass."""
    
    def test_version_match_found_property(self):
        """Test the found property of VersionMatch."""
        match_found = VersionMatch(requested="3.11", exact_match="3.11.13")
        assert match_found.found
        
        match_not_found = VersionMatch(requested="3.1", suggestions=["3.11.13"])
        assert not match_not_found.found
    
    def test_version_match_default_suggestions(self):
        """Test that suggestions defaults to empty list."""
        match = VersionMatch(requested="3.11")
        assert match.suggestions == []


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_available_versions(self):
        """Test behavior with no available versions."""
        matcher = VersionMatcher([])
        result = matcher.find_match("3.11")
        
        assert not result.found
        assert result.suggestions == []
    
    def test_single_available_version(self):
        """Test with only one available version."""
        matcher = VersionMatcher(["3.11.13"])
        
        # Exact match
        result = matcher.find_match("3.11.13")
        assert result.found
        
        # Non-match should suggest the only version
        result = matcher.find_match("3.10")
        assert not result.found
        assert "3.11.13" in result.suggestions
    
    def test_very_long_version_string(self):
        """Test handling of unusually long version strings."""
        versions = ["3.11.13.1.2.3"]
        matcher = VersionMatcher(versions)
        result = matcher.find_match("3.11")
        
        assert result.found
        assert result.exact_match == "3.11.13.1.2.3"
    
    def test_empty_available_versions(self):
        """Test behavior with no available versions."""
        matcher = VersionMatcher([])
        result = matcher.find_match("3.11")
        
        assert not result.found
        assert result.suggestions == []
    
    def test_single_available_version(self):
        """Test with only one available version."""
        matcher = VersionMatcher(["3.11.13"])
        
        # Exact match
        result = matcher.find_match("3.11.13")
        assert result.found
        
        # Non-match should suggest the only version
        result = matcher.find_match("3.10")
        assert not result.found
        assert "3.11.13" in result.suggestions
    
    def test_very_long_version_string(self):
        """Test handling of unusually long version strings."""
        versions = ["3.11.13.1.2.3"]
        matcher = VersionMatcher(versions)
        result = matcher.find_match("3.11")
        
        assert result.found
        assert result.exact_match == "3.11.13.1.2.3"
