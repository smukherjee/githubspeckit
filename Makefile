PYTHON := .venv/bin/python
PIP := .venv/bin/pip
ACTIVATE := . .venv/bin/activate

.PHONY: venv install dev test lint run health clean

venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements.txt || true

# Install dev dependencies from pyproject via uv export if desired later

dev: install
	$(PIP) install pytest pytest-asyncio

test: dev
	$(PYTHON) -m pytest -q

run: dev
	$(PYTHON) -c "from adapters.api.app import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8000)"

health: dev
	curl -s http://localhost:8000/v1/health | jq .

clean:
	rm -rf .venv
	find . -name __pycache__ -prune -exec rm -rf {} +
