ifeq ($(OS),Windows_NT)
    RMDIR := rmdir /s /q
else
    RMDIR := rm -rf
endif

.PHONY: test deps clean build bump-major bump-minor bump-patch publish pack mix

TEST_PUBLISHED_OUTPUT := testpublishedoutput


deps:
	uv sync --all-extras

test: deps
	uv run pytest

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

# Run example script with the package published to Test PyPI
# --index-strategy unsafe-best-match
# We need to force it to look for other dependencies from the regular pypi server.
# We save the output to a directory, and delete it afterwards if successful.
test-testpypi-artifact:
	uv run \
	  --no-cache \
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
