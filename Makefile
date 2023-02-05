all: start db-create schema-load

schema-load:
	psql python-project-83 < database.sql

db-create:
	createdb python-project-83

db-reset:
	dropdb python-project-83 || true
	createdb python-project-83

connect:
	psql -d python-project-83

dev:
	poetry run flask --app page_analyzer:app --debug run

install:
	poetry install

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
