SHELL := powershell.exe
.SHELLFLAGS := -Command

# Basic variables
PYTHON := python
PIP := pip
VENV := .venv
VENV_BIN := $(VENV)\Scripts
PYTHONPATH := $(CURDIR)

.PHONY: test deps bump-major bump-minor bump-patch publish env pack mix


pack:
	repomix

mix:
	make pack

deps:
	& $(VENV_BIN)\python -m pip install -r requirements.txt

test:
	& $(VENV_BIN)\python test_igc_parser.py

clean:
	if (Test-Path dist) { Remove-Item -Recurse -Force dist }
	if (Test-Path build) { Remove-Item -Recurse -Force build }
	Remove-Item -Force *.egg-info -ErrorAction SilentlyContinue

build:
	& $(VENV_BIN)\python -m build

bump-major: test
	& $(VENV_BIN)\bumpversion major

bump-minor: test
	& $(VENV_BIN)\bumpversion minor

bump-patch: test
	& $(VENV_BIN)\bumpversion patch

publish:
	& $(VENV_BIN)\python -m twine upload dist/*

env:
	if (-not (Test-Path $(VENV))) { \
		$(PYTHON) -m venv $(VENV); \
		& $(VENV_BIN)\Activate.ps1; \
		Write-Host "Virtual environment created and activated."; \
	} else { \
		& $(VENV_BIN)\Activate.ps1; \
		Write-Host "Virtual environment activated."; \
	}