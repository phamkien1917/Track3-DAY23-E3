.PHONY: install test lint typecheck run-scenarios grade-local graph-diagram inspect-history clean

install:
	pip install -e '.[dev,sqlite]'

test:
	pytest

lint:
	ruff check src tests

typecheck:
	mypy src

run-scenarios:
	python -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json

grade-local:
	python -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json

graph-diagram:
	python -m langgraph_agent_lab.cli export-diagram --output outputs/graph.mmd

inspect-history:
	python -m langgraph_agent_lab.cli inspect-history --config configs/lab.yaml --thread-id thread-S01_simple --output outputs/state_history.json

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build *.egg-info outputs/*.json
