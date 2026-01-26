# Python Version Matcher

A robust utility for matching and resolving Python versions with intelligent error handling and suggestions.

## Problem Statement

When users request a Python version like "3.1" (a common typo for "3.11"), traditional string matching can fail to provide helpful feedback. This utility solves the problem by:

1. **Proper semantic version parsing** - Understands version numbers correctly
2. **Fuzzy matching** - Suggests similar versions when exact match fails
3. **Helpful error messages** - Provides clear guidance with available options
4. **Partial matching** - Allows specifying just "3.11" to get "3.11.13"

## The "3.1" Problem

The issue that motivated this utility:

```
Error: Version 3.1 with arch x64 not found
Available versions: 3.10.18 (x64) 3.11.13 (x64) 3.12.11 (x64) 3.13.7 (x64) 3.9.23 (x64)
```

This happens when someone types "3.1" instead of "3.11" or "3.10". The version matcher handles this gracefully by:
- Detecting that "3.1" isn't available
- Calculating version similarity
- Suggesting the closest matches (3.10, 3.11, etc.)

## Installation

The version matcher is part of the NOX API utilities:

```python
from api.utils.version_matcher import match_python_version, VersionMatcher
```

No external dependencies required - uses only Python standard library.

## Usage

### Basic Usage

```python
from api.utils.version_matcher import match_python_version

available = ["3.9.23", "3.10.18", "3.11.13", "3.12.11", "3.13.7"]
result = match_python_version("3.1", available)

if result.found:
    print(f"Match: {result.exact_match}")
else:
    print(result.error_message)
    print(f"Suggestions: {', '.join(result.suggestions)}")
```

### Advanced Usage

```python
from api.utils.version_matcher import VersionMatcher

matcher = VersionMatcher(available_versions=["3.11.13", "3.12.11"], arch="x64")

# Exact match
result = matcher.find_match("3.11.13")
assert result.found

# Partial match (major.minor)
result = matcher.find_match("3.11")
assert result.exact_match == "3.11.13"

# Typo with suggestions
result = matcher.find_match("3.1")
assert not result.found
assert len(result.suggestions) > 0
```

## Features

### 1. Exact Version Matching

```python
result = match_python_version("3.11.13", ["3.11.13", "3.12.11"])
# result.exact_match == "3.11.13"
```

### 2. Partial Version Matching

```python
result = match_python_version("3.11", ["3.11.1", "3.11.13"])
# result.exact_match == "3.11.13" (latest 3.11.x)
```

### 3. Fuzzy Matching with Suggestions

```python
result = match_python_version("3.1", ["3.9.23", "3.10.18", "3.11.13"])
# result.found == False
# result.suggestions == ["3.9.23", "3.10.18", "3.11.13"]
```

### 4. Architecture Support

```python
result = match_python_version("3.1", available, arch="arm64")
# Error message includes "arch arm64"
```

## API Reference

### `match_python_version(requested_version, available_versions, arch="x64")`

Convenience function for quick version matching.

**Parameters:**
- `requested_version` (str): The version to find (e.g., "3.11", "3.1")
- `available_versions` (List[str]): List of available version strings
- `arch` (str): Architecture string (default: "x64")

**Returns:** `VersionMatch` object

### `VersionMatcher`

Main class for version matching operations.

**Methods:**
- `__init__(available_versions, arch="x64")`: Initialize with available versions
- `find_match(requested_version)`: Find a matching version

### `VersionMatch`

Result dataclass containing:
- `requested` (str): The requested version string
- `exact_match` (Optional[str]): Matched version if found
- `suggestions` (List[str]): Suggested similar versions
- `error_message` (Optional[str]): Error message if not found
- `found` (bool property): True if exact match exists

## Examples

### Example 1: GitHub Actions Setup

```python
from api.utils.version_resolver import PythonVersionResolver

resolver = PythonVersionResolver()
result = resolver.resolve_version("3.11")

if result["success"]:
    python_path = result["path"]
    # Use python_path for execution
else:
    print(result["error"])
    print(f"Try: {result['suggestions'][0]}")
```

### Example 2: CI/CD Pipeline

```python
from api.utils.version_matcher import VersionMatcher

def setup_python(requested: str, available: list) -> str:
    """Setup Python version, raising helpful error if not found."""
    matcher = VersionMatcher(available)
    result = matcher.find_match(requested)
    
    if result.found:
        return result.exact_match
    
    # Provide helpful error
    error = f"{result.error_message}\n\n"
    if result.suggestions:
        error += f"Did you mean: {result.suggestions[0]}?"
    raise ValueError(error)
```

### Example 3: Interactive Version Selection

```python
from api.utils.version_matcher import match_python_version

requested = input("Enter Python version: ")
available = ["3.9.23", "3.10.18", "3.11.13", "3.12.11"]

result = match_python_version(requested, available)

if result.found:
    print(f"Using Python {result.exact_match}")
else:
    print(f"Version {requested} not found.")
    if result.suggestions:
        print("Available alternatives:")
        for i, version in enumerate(result.suggestions, 1):
            print(f"  {i}. {version}")
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_version_matcher.py -v
```

Test coverage includes:
- Exact and partial matching
- Typo handling (the "3.1" case)
- Edge cases (empty versions, invalid formats)
- Version distance calculations
- Suggestion ordering
- Architecture handling

## Demo Scripts

### 1. Basic Demo

```bash
python scripts/demo_version_matcher.py
```

Shows basic version matching with various test cases.

### 2. Integration Demo

```bash
python api/utils/version_resolver.py
```

Shows practical integration in a version resolution system.

## Design Decisions

### Why Not Use String Prefix Matching?

Traditional approaches might use:
```python
if version_string.startswith("3.1"):  # WRONG!
    # This matches 3.10, 3.11, 3.12, 3.13 but NOT 3.1
```

Our approach uses proper version parsing:
```python
requested = (3, 1)  # Parse to tuple
available = (3, 11, 13)  # Parse to tuple
# Now we can properly compare and calculate distances
```

### Why Calculate Version Distance?

When suggesting alternatives, we calculate semantic distance:
- "3.1" is closer to "3.10" than to "3.13"
- "3.8" is closest to "3.9"
- Major version differences are weighted more than minor differences

### Why Support Partial Versions?

Users often specify "3.11" when they mean "any 3.11.x". The matcher:
1. Checks if requested is a prefix of available
2. Returns the latest matching version
3. Allows flexible version specifications

## Contributing

When adding new features:
1. Add tests to `tests/test_version_matcher.py`
2. Update this README
3. Ensure all existing tests pass
4. Consider edge cases

## License

Part of the NOX API project.

## Related

- `api/utils/version_resolver.py` - Integration example
- `tests/test_version_matcher.py` - Test suite
- `scripts/demo_version_matcher.py` - Demonstration script
