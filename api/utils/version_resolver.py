"""
Example integration of the version matcher for Python version resolution.

This module demonstrates how the version matcher can be integrated into
systems that need to resolve Python versions, such as:
- GitHub Actions workflows
- CI/CD pipelines
- Python version managers
- Environment setup scripts
"""

from typing import Any, Dict, List, Optional, Union
from api.utils.version_matcher import VersionMatcher


class PythonVersionResolver:
    """
    Resolves Python versions for execution environments.
    
    This class provides a practical example of how to integrate the
    version matcher into a system that needs to select Python versions.
    """
    
    def __init__(self, available_versions: Optional[Dict[str, str]] = None):
        """
        Initialize the resolver.
        
        Args:
            available_versions: Dict mapping version strings to installation paths.
                               If None, uses default system versions.
        """
        self.available_versions = available_versions or self._detect_system_versions()
    
    def _detect_system_versions(self) -> Dict[str, str]:
        """
        Detect available Python versions on the system.
        
        In a real implementation, this would scan for installed Python versions.
        For this example, we use a simulated set of versions.
        
        Returns:
            Dict mapping version strings to paths
        """
        # Simulated available versions (would be detected in real implementation)
        return {
            "3.9.23": "/usr/bin/python3.9",
            "3.10.18": "/usr/bin/python3.10",
            "3.11.13": "/usr/bin/python3.11",
            "3.12.11": "/usr/bin/python3.12",
            "3.13.7": "/usr/bin/python3.13",
        }
    
    def resolve_version(self, requested_version: str, arch: str = "x64") -> Dict[str, Any]:
        """
        Resolve a requested Python version to an available installation.
        
        Args:
            requested_version: The version string to resolve (e.g., "3.11", "3.1")
            arch: The target architecture
            
        Returns:
            Dict with resolution results including:
                - success: bool indicating if resolution succeeded
                - version: The resolved version string (if successful)
                - path: The path to the Python executable (if successful)
                - error: Error message (if unsuccessful)
                - suggestions: List of suggested versions (if unsuccessful)
        """
        matcher = VersionMatcher(list(self.available_versions.keys()), arch=arch)
        result = matcher.find_match(requested_version)
        
        if result.found:
            resolved_version = result.exact_match
            return {
                "success": True,
                "requested": requested_version,
                "resolved": resolved_version,
                "path": self.available_versions[resolved_version],
                "message": f"Successfully resolved {requested_version} to {resolved_version}"
            }
        else:
            return {
                "success": False,
                "requested": requested_version,
                "error": result.error_message,
                "suggestions": result.suggestions,
                "suggestion_paths": {v: self.available_versions[v] for v in result.suggestions}
            }


def setup_python_environment(requested_version: str) -> bool:
    """
    Example function showing how to use the resolver in a setup script.
    
    Args:
        requested_version: The Python version to set up
        
    Returns:
        True if setup succeeded, False otherwise
    """
    resolver = PythonVersionResolver()
    result = resolver.resolve_version(requested_version)
    
    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"  Python executable: {result['path']}")
        return True
    else:
        print(f"✗ Failed to resolve Python version '{requested_version}'")
        print(f"\n{result['error']}")
        
        if result["suggestions"]:
            print(f"\n💡 Did you mean one of these?")
            for i, suggestion in enumerate(result["suggestions"], 1):
                path = result["suggestion_paths"][suggestion]
                print(f"   {i}. {suggestion} (available at {path})")
        
        return False


def main():
    """Demonstrate the integration with various test cases."""
    print("=" * 70)
    print("Python Version Resolver - Integration Example")
    print("=" * 70)
    
    test_cases = [
        "3.11",      # Should work - partial match
        "3.11.13",   # Should work - exact match
        "3.1",       # The problematic typo case
        "3.8",       # Too old
        "3.14",      # Too new
    ]
    
    for version in test_cases:
        print(f"\n{'-' * 70}")
        print(f"Attempting to set up Python {version}")
        print(f"{'-' * 70}")
        success = setup_python_environment(version)
        print()
    
    print("=" * 70)


if __name__ == "__main__":
    main()
