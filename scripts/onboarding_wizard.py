#!/usr/bin/env python3
"""
NOX Onboarding Wizard
Guides new contributors through environment setup, credentials, and first steps.
"""
import os
from pathlib import Path


def prompt(msg, default=None):
    val = input(f"{msg} " + (f"[{default}]" if default else "") + ": ")
    return val.strip() or default


def check_env_file():
    env_path = Path(__file__).parent.parent / ".env.production"
    if env_path.exists():
        print("✅ .env.production found.")
    else:
        print("❌ .env.production not found. Creating from template...")
        template = Path(__file__).parent.parent / ".env.production.example"
        if template.exists():
            os.system(f'cp "{template}" "{env_path}"')
            print("✅ .env.production created.")
        else:
            print("❌ Template not found. Please create .env.production manually.")


def main():
    print("=== NOX Onboarding Wizard ===")
    print("This tool will help you set up your environment for NOX development.")
    print("---")
    name = prompt("Enter your name")
    _email = prompt("Enter your email")
    print(f"Welcome, {name}!")
    print("Step 1: Checking environment file...")
    check_env_file()
    print("Step 2: Install dependencies (run: pip install -r requirements.txt)")
    print(
        "Step 3: Review docs/README.md and docs/deployment-guides/PRODUCTION_CREDENTIALS_GUIDE.md"
    )
    print("Step 4: Run health-check-production.sh to validate setup")
    print("Step 5: Start development with nox-api-src/")
    print("---")
    print("Onboarding complete! For help, see docs/README.md or ask your team lead.")


if __name__ == "__main__":
    main()
