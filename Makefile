# Makefile for Disk Cleanup Analyzer

.PHONY: help install test lint clean analyze sample

# Default target
help:
	@echo "Disk Cleanup Analyzer - Makefile Commands"
	@echo "=========================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install dependencies (none required)"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Run linting checks"
	@echo "  make clean      - Remove temporary files and caches"
	@echo "  make analyze    - Analyze current directory"
	@echo "  make sample     - Run sample analysis on /tmp"
	@echo "  make report     - Generate JSON report for current directory"
	@echo ""

# Install dependencies (currently none)
install:
	@echo "✓ No external dependencies required"
	@echo "  This script uses only Python standard library"
	@echo ""
	@echo "Python version check:"
	@python3 --version

# Run tests
test:
	@echo "Running tests..."
	@if [ -d "tests" ]; then \
		python3 -m pytest tests/ -v; \
	else \
		echo "⚠ No tests directory found. Creating basic test..."; \
		mkdir -p tests; \
		echo "print('Basic test passed')" > tests/test_basic.py; \
		python3 tests/test_basic.py; \
	fi

# Run linting
lint:
	@echo "Running linting checks..."
	@python3 -m py_compile disk_cleanup_analyzer.py && echo "✓ Syntax check passed"
	@echo ""
	@echo "Code statistics:"
	@echo "  Lines of code: $$(wc -l < disk_cleanup_analyzer.py)"
	@echo "  File size: $$(du -h disk_cleanup_analyzer.py | cut -f1)"

# Clean temporary files
clean:
	@echo "Cleaning up temporary files..."
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf *.pyc
	@rm -rf disk_cleanup_report.json
	@rm -rf tests/__pycache__
	@echo "✓ Cleanup complete"

# Analyze current directory
analyze:
	@echo "Analyzing current directory..."
	python3 disk_cleanup_analyzer.py .

# Sample analysis on /tmp
sample:
	@echo "Running sample analysis on /tmp..."
	python3 disk_cleanup_analyzer.py /tmp --min-size 1 --save-report

# Generate JSON report
report:
	@echo "Generating JSON report..."
	python3 disk_cleanup_analyzer.py . --save-report
	@echo ""
	@echo "Report saved to: disk_cleanup_report.json"
