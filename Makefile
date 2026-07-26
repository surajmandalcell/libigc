ifeq ($(OS),Windows_NT)
    RMDIR := rmdir /s /q
else
    RMDIR := rm -rf
endif

.PHONY: test lint format deps clean build bump-major bump-minor bump-patch publish pack mix

TEST_PUBLISHED_OUTPUT := testpublishedoutput


deps:
	uv sync --all-extras

test: lint
	uv run pytest

# Check formatting and lint rules without touching anything. This is what CI
# and the release targets run.
lint: deps
	uv run ruff format --check .
	uv run ruff check .

# Apply the formatter and every autofixable lint rule.
format: deps
	uv run ruff format .
	uv run ruff check --fix .

clean:
	-$(RMDIR) dist
	-$(RMDIR) build
	-$(RMDIR) src/libigc.egg-info
	-$(RMDIR) $(TEST_PUBLISHED_OUTPUT)

build: clean test
	uv build

# `$(ARGS)` allows passwing additional arguments to the command.
# For testing during development, you can run `make bump-major ARGS="--allow-dirty"`
bump-major: test
	uv run bump-my-version bump major $(ARGS)

bump-minor: test
	uv run bump-my-version bump minor $(ARGS)

bump-patch: test
	uv run bump-my-version bump patch $(ARGS)

publish: build
	uv run twine upload dist/* --verbose $(ARGS)

# Publish to Test PyPI (https://test.pypi.org/) for testing purposes.
test-publish: build
	uv run twine upload -r testpypi dist/* --verbose $(ARGS)

# Run example script against the package published to Test PyPI, rather than
# against this checkout. --no-project keeps the local sources off sys.path and
# --with pulls libigc from the index.
# --index-strategy unsafe-best-match
# We need to force it to look for other dependencies from the regular pypi server.
# We save the output to a directory, and delete it afterwards if successful.
test-testpypi-artifact:
	uv run \
	  --no-cache \
	  --no-project \
	  --with libigc \
	  --index https://test.pypi.org/simple/ \
	  --verbose \
	  --index-strategy unsafe-best-match \
	  examples/libigc_demo.py \
	  tests/testfiles/napret.igc \
	  tests/testfiles/napret.lkt \
	  -o $(TEST_PUBLISHED_OUTPUT)
	-$(RMDIR) $(TEST_PUBLISHED_OUTPUT)

pack:
	repomix

mix: pack
