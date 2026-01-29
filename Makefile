# ---- NOX API XTB Dev Workflow ----
PYTHONPATH := $(shell pwd)
APP := api.main:app
HOST := 127.0.0.1
PORT := 8000

LOG_DIR := .logs
RUN_DIR := .run
API_PID := $(RUN_DIR)/api.pid

# ---- helpers ----
_init:
	@mkdir -p $(LOG_DIR) $(RUN_DIR)

# ---- API (new dev workflow) ----
api-start: _init
	@echo "Starting API on $(HOST):$(PORT)…"
	@(PYTHONPATH=$(PYTHONPATH) uvicorn $(APP) --host $(HOST) --port $(PORT) --reload \
		> $(LOG_DIR)/api.log 2>&1 & echo $$! > $(API_PID))
	@echo "API PID: $$(cat $(API_PID))  (logs: $(LOG_DIR)/api.log)"

api-stop:
	@if [ -f $(API_PID) ]; then \
		echo "Stopping API PID $$(cat $(API_PID))"; \
		kill $$(cat $(API_PID)) || true; \
		rm -f $(API_PID); \
	else echo "API not running"; fi

api-logs:
	@tail -f $(LOG_DIR)/api.log

# ---- tests ----
test:
	@PYTHONPATH=$(PYTHONPATH) pytest -q

.PHONY: test-e2e
test-e2e:
	@PYTHONPATH=$(PYTHONPATH) pytest tests/e2e -q

# ---- Legacy XTB targets (preserved) ----
.PHONY: run worker redis help clean status logs install harden caddy-lan caddy-public nginx-public repair repair-v2 validate demo logs install-logs debug api-start api-stop api-logs _init

run:  ## Run API server on port 8080 (legacy)
	PYTHONPATH=. python -m uvicorn api.main:app --reload --port 8080
	PYTHONPATH=. python -m uvicorn api.main:app --reload --port 8080

worker:  ## Run Dramatiq worker for background jobs
	python -m dramatiq api.routes.jobs --processes 1 --threads 1

legacy-test:  ## Run pytest test suite (legacy)
	PYTHONPATH=. python -m pytest -q

redis:  ## Start Redis server in daemon mode
	@echo "Starting Redis server..."
	@if command -v redis-server >/dev/null 2>&1; then \
		redis-server --daemonize yes; \
		echo "Redis started as daemon"; \
	else \
		echo "Redis not installed locally, starting with Docker..."; \
		docker compose -f docker-compose.xtb.yml up -d redis; \
	fi

# Legacy targets preserved
.PHONY: help install harden caddy-lan caddy-public nginx-public repair repair-v2 validate demo logs install-logs debug

# Configuration
SCRIPT_DIR = scripts
DEPLOY_DIR = deploy
TESTS_DIR = tests

help:  ## Display available commands
	@echo "Makefile Nox API XTB - Available commands:"
	@echo ""
	@echo "🚀 XTB Development:"
	@echo "  make run           # Start API server (port 8080)"
	@echo "  make worker        # Start Dramatiq worker"
	@echo "  make test          # Run pytest test suite"
	@echo "  make redis         # Start Redis daemon"
	@echo ""
	@echo "📊 System:"
	@echo "  make status        # Show service status"
	@echo "  make logs          # Show recent logs"  
	@echo "  make clean         # Clean temporary files"
	@echo ""
	@echo "⚙️  Legacy (for existing NOX infrastructure):"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v "XTB\|Display\|Start\|Run\|Show\|Clean" | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""
	@echo "💡 Quick start:"
	@echo "  Terminal 1: make redis && make run"
	@echo "  Terminal 2: make worker"
	@echo "  Terminal 3: make test"

status:  ## Show XTB API and service status
	@echo "=== XTB API Status ==="
	@echo "API Health: $$(curl -s http://127.0.0.1:8080/health 2>/dev/null | grep -o '"status":"ok"' | grep -o 'ok' || echo 'not available')"
	@echo "Redis: $$(redis-cli ping 2>/dev/null || echo 'not available')"
	@echo "XTB Binary: $$(which xtb 2>/dev/null || echo 'not found in PATH')"
	@if pgrep -f "uvicorn.*api.main" > /dev/null; then echo "API Server: running"; else echo "API Server: not running"; fi
	@if pgrep -f "dramatiq.*api.routes.jobs" > /dev/null; then echo "Dramatiq Worker: running"; else echo "Dramatiq Worker: not running"; fi

clean:  ## Clean temporary files and cache
	@echo "Cleaning temporary files..."
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.tmp" -delete 2>/dev/null || true
	@find . -name "test_*_output" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup completed"

logs:  ## Show recent logs
	@echo "=== Recent System Logs ==="
	@if [ -f "/var/log/nox-api/nox-api.log" ]; then \
		tail -20 /var/log/nox-api/nox-api.log; \
	else \
		echo "No XTB API specific logs found"; \
	fi

# Legacy NOX infrastructure targets (preserved for compatibility)
install:  ## Install/reinstall Nox API
	@echo "Installing Nox API..."
	@./scripts/install_nox.sh

repair:  ## Repair installation (legacy script removed; fallback guidance)
	@echo "Repairing Nox API..."
	@echo "Legacy repair script removed; use scripts/rollback.sh or reinstall if needed."

validate:  ## Validate installation
	@echo "Validating Nox API..."
	@./verify_env.sh

demo:  ## Run legacy demo tests
	@echo "Running legacy demo tests..."
	@if [ -f "/etc/default/nox-api" ]; then \
		export NOX_API_TOKEN=$$(sudo grep "^NOX_API_TOKEN=" /etc/default/nox-api | cut -d= -f2 | tr -d '"'); \
		export NOX_API_URL="http://localhost"; \
		cd clients && python3 tests_demo.py; \
	else \
		echo "❌ Error: Legacy configuration not found"; \
	fi

# Default target
.DEFAULT_GOAL := help
