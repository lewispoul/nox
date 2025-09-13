#!/usr/bin/env python3
"""
🔧 NOX API v8.0.0 - Environment Verification Script
===================================================

Comprehensive validation script for all scientific computing dependencies
and environment requirements before staging deployment.

Usage: python3 scripts/verify_env.py
"""

import importlib
import os
import subprocess
import sys
from typing import Optional


class EnvironmentValidator:
    def __init__(self):
        self.results = {}
        self.errors = []
        self.warnings = []

    def log_result(self, component: str, status: bool, message: str = ""):
        """Log validation result for a component"""
        self.results[component] = {"status": status, "message": message}

        if not status:
            self.errors.append(f"❌ {component}: {message}")
        else:
            print(f"✅ {component}: OK {message}")

    def validate_python_version(self) -> bool:
        """Validate Python version compatibility"""
        version = sys.version_info
        required_major, required_minor = 3, 8

        if version.major >= required_major and version.minor >= required_minor:
            self.log_result(
                "Python Version",
                True,
                f"({version.major}.{version.minor}.{version.micro})",
            )
            return True
        else:
            self.log_result(
                "Python Version",
                False,
                f"Requires Python {required_major}.{required_minor}+, got {version.major}.{version.minor}.{version.micro}",
            )
            return False

    def validate_package_import(
        self, package_name: str, import_name: Optional[str] = None
    ) -> bool:
        """Validate that a package can be imported successfully"""
        import_name = import_name or package_name

        try:
            module = importlib.import_module(import_name)
            version = getattr(module, "__version__", "Unknown")
            self.log_result(package_name, True, f"version {version}")
            return True
        except ImportError as e:
            self.log_result(package_name, False, str(e))
            return False
        except (AttributeError, RuntimeError) as e:
            # Catch specific exceptions that might occur during import
            self.log_result(package_name, False, f"Unexpected error: {str(e)}")
            return False

    def validate_rdkit(self) -> bool:
        """Special validation for RDKit with basic functionality test"""
        try:
            from rdkit import Chem  # type: ignore
            from rdkit.Chem import rdMolDescriptors  # type: ignore

            # Test basic molecule creation and descriptor calculation
            mol = Chem.MolFromSmiles("CCO")
            if mol is None:
                raise ValueError("Failed to create molecule from SMILES")

            mw = rdMolDescriptors.CalcExactMolWt(mol)
            if not isinstance(mw, float) or mw <= 0:
                raise ValueError("Failed to calculate molecular weight")

            self.log_result(
                "RDKit", True, f"Functional test passed (MW calculation: {mw:.2f})"
            )
            return True

        except ImportError as e:
            self.log_result("RDKit", False, f"Import error: {str(e)}")
            return False
        except (ValueError, RuntimeError) as e:
            self.log_result("RDKit", False, f"Functionality test failed: {str(e)}")
            return False

    def validate_psi4(self) -> bool:
        """Validate Psi4 quantum chemistry package"""
        try:
            import psi4  # type: ignore

            # Test basic Psi4 functionality
            psi4.core.clean_options()

            # Check if we can set basic options
            psi4.set_memory("100 MB")
            psi4.set_num_threads(1)

            version = psi4.__version__
            self.log_result("Psi4", True, f"version {version} - basic setup OK")
            return True

        except ImportError as e:
            self.log_result("Psi4", False, f"Import error: {str(e)}")
            return False
        except (AttributeError, RuntimeError) as e:
            self.log_result("Psi4", False, f"Setup error: {str(e)}")
            return False

    def validate_cantera(self) -> bool:
        """Validate Cantera chemical kinetics library"""
        try:
            import cantera as ct  # type: ignore

            # Test basic Cantera functionality
            gas = ct.Solution("gri30.yaml")
            if gas is None:
                raise ValueError("Failed to load GRI-Mech 3.0 mechanism")

            # Test setting state
            gas.TPX = 300, 101325, "CH4:1, O2:2, N2:7.52"

            self.log_result(
                "Cantera", True, f"version {ct.__version__} - GRI-Mech loaded OK"
            )
            return True

        except ImportError as e:
            self.log_result("Cantera", False, f"Import error: {str(e)}")
            return False
        except (ValueError, RuntimeError, FileNotFoundError) as e:
            self.log_result("Cantera", False, f"Functionality test failed: {str(e)}")
            return False

    def validate_xtb_wrapper(self) -> bool:
        """Validate XTB wrapper accessibility"""
        try:
            # Try to find XTB executable
            result = subprocess.run(
                ["which", "xtb"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                xtb_path = result.stdout.strip()

                # Test XTB version
                version_result = subprocess.run(
                    [xtb_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                if version_result.returncode == 0:
                    # Note: version_output kept for debugging but not used in production
                    self.log_result("XTB", True, f"executable found at {xtb_path}")
                    return True
                else:
                    self.log_result(
                        "XTB", False, "Executable found but version check failed"
                    )
                    return False
            else:
                self.log_result("XTB", False, "Executable not found in PATH")
                return False

        except subprocess.TimeoutExpired:
            self.log_result("XTB", False, "Command timeout - possible system issue")
            return False
        except (OSError, ValueError) as e:
            self.log_result("XTB", False, f"Validation error: {str(e)}")
            return False

    def validate_standard_packages(self) -> int:
        """Validate standard scientific Python packages"""
        packages = {
            "numpy": "numpy",
            "scipy": "scipy",
            "pandas": "pandas",
            "matplotlib": "matplotlib",
            "requests": "requests",
            "flask": "flask",
            "sqlalchemy": "sqlalchemy",
            "redis": "redis",
            "psycopg2": "psycopg2",
            "celery": "celery",
            "pytest": "pytest",
        }

        success_count = 0
        for package, import_name in packages.items():
            if self.validate_package_import(package, import_name):
                success_count += 1

        return success_count

    def validate_environment_variables(self) -> bool:
        """Validate critical environment variables"""
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GITHUB_CLIENT_ID",
            "GITHUB_CLIENT_SECRET",
            "MICROSOFT_CLIENT_ID",
            "MICROSOFT_CLIENT_SECRET",
            "SECRET_KEY",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.log_result(
                "Environment Variables", False, f"Missing: {', '.join(missing_vars)}"
            )
            return False
        else:
            self.log_result(
                "Environment Variables",
                True,
                f"All {len(required_vars)} required variables set",
            )
            return True

    def validate_file_permissions(self) -> bool:
        """Validate file system permissions for critical directories"""
        critical_paths = [
            "/tmp",
            "/home/lppoulin/nox-api-src",
            "/home/lppoulin/nox-api-src/logs",
            "/home/lppoulin/nox-api-src/data",
        ]

        permission_issues = []
        for path in critical_paths:
            if not os.path.exists(path):
                if path.endswith(("logs", "data")):
                    # Create if it's a project subdirectory
                    try:
                        os.makedirs(path, exist_ok=True)
                        continue
                    except (OSError, PermissionError):
                        permission_issues.append(f"{path} (cannot create)")
                        continue
                else:
                    permission_issues.append(f"{path} (does not exist)")
                    continue

            if not os.access(path, os.R_OK | os.W_OK):
                permission_issues.append(f"{path} (insufficient permissions)")

        if permission_issues:
            self.log_result(
                "File Permissions", False, f"Issues: {', '.join(permission_issues)}"
            )
            return False
        else:
            self.log_result("File Permissions", True, "All paths accessible")
            return True

    def run_full_validation(self) -> bool:
        """Run complete environment validation"""
        print("🔍 NOX API v8.0.0 Environment Validation")
        print("=" * 50)

        # Core validation steps
        validation_steps = [
            ("Python Version", self.validate_python_version),
            ("Standard Packages", lambda: self.validate_standard_packages() >= 8),
            ("RDKit", self.validate_rdkit),
            ("Psi4", self.validate_psi4),
            ("Cantera", self.validate_cantera),
            ("XTB Wrapper", self.validate_xtb_wrapper),
            ("Environment Variables", self.validate_environment_variables),
            ("File Permissions", self.validate_file_permissions),
        ]

        passed = 0
        total = len(validation_steps)

        for step_name, validation_func in validation_steps:
            try:
                if validation_func():
                    passed += 1
            except (ImportError, OSError, RuntimeError) as e:
                self.log_result(step_name, False, f"Validation error: {str(e)}")

        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")

        # Determine overall success
        critical_failures = [
            result
            for component, result in self.results.items()
            if not result["status"]
            and component
            in ["Python Version", "RDKit", "Psi4", "Environment Variables"]
        ]

        if critical_failures:
            print(
                "\n🚨 CRITICAL FAILURES DETECTED - Environment NOT ready for staging!"
            )
            return False
        elif passed >= total * 0.8:  # 80% success rate required
            print("\n✅ Environment validation PASSED - Ready for staging deployment!")
            return True
        else:
            print(
                "\n⚠️  Environment validation PARTIAL - Review failures before proceeding"
            )
            return False


def main():
    """Main validation entry point"""
    validator = EnvironmentValidator()

    try:
        success = validator.run_full_validation()
        exit_code = 0 if success else 1

        print(f"\n🏁 Validation completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(130)
    except (ImportError, OSError, RuntimeError, SystemExit) as e:
        if isinstance(e, SystemExit):
            raise  # Let SystemExit propagate normally
        print(f"\n💥 Unexpected validation error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
