#!/usr/bin/env python3
"""
Demonstration script for the version matcher utility.

This script shows how the version matcher handles the "3.1" typo case
and provides helpful suggestions.
"""

from api.utils.version_matcher import match_python_version

# Typical Python versions available in CI/CD environments
AVAILABLE_VERSIONS = ["3.9.23", "3.10.18", "3.11.13", "3.12.11", "3.13.7"]


def demo_version_matching():
    """Demonstrate version matching scenarios."""
    
    print("=" * 70)
    print("Python Version Matcher Demonstration")
    print("=" * 70)
    
    print(f"\nAvailable Python versions: {', '.join(AVAILABLE_VERSIONS)}")
    print()
    
    # Test cases
    test_cases = [
        ("3.11", "Partial match (major.minor)"),
        ("3.11.13", "Exact match"),
        ("3.1", "Typo case - should suggest 3.10 or 3.11"),
        ("3.8", "Version too old"),
        ("3.14", "Version too new"),
    ]
    
    for version_str, description in test_cases:
        print(f"\n{'-' * 70}")
        print(f"Test: {description}")
        print(f"Requested version: {version_str}")
        print(f"{'-' * 70}")
        
        result = match_python_version(version_str, AVAILABLE_VERSIONS)
        
        if result.found:
            print(f"✓ Match found: {result.exact_match}")
        else:
            print(f"✗ No exact match found")
            print(f"\nError message:")
            print(f"  {result.error_message}")
            if result.suggestions:
                print(f"\nSuggested versions:")
                for i, suggestion in enumerate(result.suggestions, 1):
                    print(f"  {i}. {suggestion}")
    
    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    demo_version_matching()
