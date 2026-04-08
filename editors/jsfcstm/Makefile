.PHONY: all help install build test coverage sample sample_clean pack clean

NPM := npm
PYTHON ?= python
REPO_ROOT := ../..
SAMPLE_GENERATOR := ./scripts/generate_model_sample_tests.py
SAMPLE_TEST_DIR := ./test/model-py-generated
SAMPLE_CODES_DIR := $(REPO_ROOT)/test/testfile/sample_codes
SAMPLE_DSL_FILES := $(shell find $(SAMPLE_CODES_DIR) -name "*.fcstm" 2>/dev/null)
SAMPLE_DSL_ENTRY_DIRS := $(shell find $(SAMPLE_CODES_DIR) -mindepth 1 -type f -name "main.fcstm" -printf '%h\n' 2>/dev/null)
SAMPLE_FLAT_DSL_FILES := $(filter-out $(foreach dir,$(SAMPLE_DSL_ENTRY_DIRS),$(dir)/%),$(SAMPLE_DSL_FILES))
SAMPLE_TEST_FILES := \
	$(patsubst $(SAMPLE_CODES_DIR)/%.fcstm,$(SAMPLE_TEST_DIR)/test_sample_%.test.ts,$(SAMPLE_FLAT_DSL_FILES)) \
	$(patsubst $(SAMPLE_CODES_DIR)/%,$(SAMPLE_TEST_DIR)/test_sample_%.test.ts,$(SAMPLE_DSL_ENTRY_DIRS))
PY_MODEL_SOURCE_FILES := \
	$(REPO_ROOT)/pyfcstm/dsl/grammar/GrammarLexer.g4 \
	$(REPO_ROOT)/pyfcstm/dsl/grammar/GrammarParser.g4 \
	$(REPO_ROOT)/pyfcstm/dsl/listener.py \
	$(REPO_ROOT)/pyfcstm/dsl/node.py \
	$(REPO_ROOT)/pyfcstm/model/model.py \
	$(REPO_ROOT)/pyfcstm/model/expr.py

help:
	@echo "jsfcstm Build Commands"
	@echo "====================="
	@echo ""
	@echo "  make install  - Install npm dependencies"
	@echo "  make build    - Generate parser artifacts under src/dsl/grammar/ and build dist/"
	@echo "  make test     - Run package unit tests with coverage reporting"
	@echo "  make coverage - Alias of make test"
	@echo "  make sample   - Generate pyfcstm-backed TS sample model tests per sample example"
	@echo "  make sample_clean - Remove generated TS sample model tests"
	@echo "  make pack     - Build and create both npm tarball outputs and jsfcstm.tgz for local repo consumers"
	@echo "  make clean    - Remove generated files"
	@echo "  make all      - Install, build, and test"

all: install build test

install:
	@echo "Installing jsfcstm dependencies..."
	$(NPM) install

build:
	@echo "Building jsfcstm..."
	$(NPM) run build

test:
	@echo "Running jsfcstm unit tests with coverage..."
	$(NPM) test

coverage: test

sample: $(SAMPLE_TEST_FILES)

$(SAMPLE_TEST_DIR)/test_sample_%.test.ts: $(SAMPLE_CODES_DIR)/%.fcstm $(SAMPLE_GENERATOR) $(PY_MODEL_SOURCE_FILES)
	@mkdir -p $(dir $@)
	$(PYTHON) $(SAMPLE_GENERATOR) -i $< -o $@

$(SAMPLE_TEST_DIR)/test_sample_%.test.ts: $(SAMPLE_CODES_DIR)/% $(SAMPLE_CODES_DIR)/%/main.fcstm $(SAMPLE_GENERATOR) $(PY_MODEL_SOURCE_FILES)
	@mkdir -p $(dir $@)
	$(PYTHON) $(SAMPLE_GENERATOR) -i $< -o $@

sample_clean:
	@echo "Removing generated jsfcstm sample tests..."
	find $(SAMPLE_TEST_DIR) -type f -name 'test_sample_*.test.ts' -delete
	find $(SAMPLE_TEST_DIR) -mindepth 1 -type d -empty -delete

pack: build
	@echo "Packing jsfcstm..."
	$(NPM) run pack:local

clean:
	@echo "Cleaning jsfcstm..."
	rm -rf dist
	rm -rf src/dsl/grammar
	rm -rf parser
	rm -rf coverage
	rm -rf node_modules
	rm -f ./*.tgz
	rm -f ./jsfcstm.tgz
	rm -f tsconfig.tsbuildinfo
