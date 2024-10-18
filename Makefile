.PHONY: test deps bump-major bump-minor bump-patch publish env

PYTHON := python3
PIP := pip
VENV := venv
VENV_BIN := $(VENV)/bin
PYTHONPATH := $(shell pwd)

deps:
	$(VENV_BIN)/python3 -m pip install -r requirements.txt

test:
	PYTHONPATH=$(PYTHONPATH) $(VENV_BIN)/python3 -m unittest discover tests

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

build:
	$(VENV_BIN)/python -m build

bump-major: test
	$(VENV_BIN)/bumpversion major

bump-minor: test
	$(VENV_BIN)/bumpversion minor

bump-patch: test
	$(VENV_BIN)/bumpversion patch

publish:
	$(VENV_BIN)/python -m twine upload dist/*

env:
	@if [ ! -d "$(VENV)" ]; then \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created."; \
	fi
	@echo "Creating venv.sh for easy activation"
	@echo "source $(VENV_BIN)/activate" > venv.sh
	@chmod +x venv.sh
	@echo "To activate the virtual environment in the current shell, run:"
	@echo "source venv.sh"
	# Copy the activation command to the clipboard
	@if [ "$(shell uname)" = "Linux" ]; then \
		if grep -qi microsoft /proc/version; then \
			echo "source venv.sh" | clip.exe; \
			echo "Activation command copied to clipboard for WSL."; \
		else \
			echo "source venv.sh" | xclip -selection clipboard; \
			echo "Activation command copied to clipboard."; \
		fi \
	elif [ "$(shell uname)" = "Darwin" ]; then \
		echo "source venv.sh" | pbcopy; \
		echo "Activation command copied to clipboard."; \
	fi