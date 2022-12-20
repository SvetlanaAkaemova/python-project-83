dev:
	poetry run flask --app page_analyzer:app run

install:
	poetry install

test:
	poetry run pytest

test-coverage:
	poetry run pytest --cov=page_analyzer tests/ --cov-report xml

lint:
	poetry run flake8 page_analyzer

selfcheck:
	poetry check

check: selfcheck test lint

build:
	poetry build

PORT ?= 8000
start:
	poetry run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

.PHONY: install test lint selfcheck check build
