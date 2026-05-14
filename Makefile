.PHONY: help install dev backend frontend test lint clean train-tiny

help:
	@echo "Common commands:"
	@echo "  make install       Install backend + frontend deps"
	@echo "  make dev           Run backend (8765) and frontend (5173) together"
	@echo "  make backend       Run only the FastAPI backend"
	@echo "  make frontend      Run only the Vite frontend"
	@echo "  make train-tiny    Train the bundled TinyTokenizer model"
	@echo "  make lint          Lint backend (ruff) and frontend (tsc)"
	@echo "  make clean         Remove caches and build output"

install:
	@if [ ! -d venv ]; then /opt/homebrew/bin/python3.12 -m venv venv; fi
	. venv/bin/activate && pip install --upgrade pip && pip install -e .
	cd frontend && npm install

backend:
	. venv/bin/activate && python -m app.main

frontend:
	cd frontend && npm run dev

dev:
	@$(MAKE) -j 2 backend frontend

train-tiny:
	. venv/bin/activate && python -m tokenizer.cli "hello world" \
		--vocab-size 1024 \
		--save tokenizer/data/tok.json

lint:
	. venv/bin/activate && ruff check backend tokenizer
	cd frontend && npx tsc --noEmit -p tsconfig.app.json

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf frontend/dist frontend/.vite
