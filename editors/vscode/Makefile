# Makefile for FCSTM VSCode Extension
# This file provides commands for building and maintaining the extension

.PHONY: all parser clean install build package verify-p0.2 help

# ANTLR configuration
ANTLR_VERSION := 4.9.3
ANTLR_JAR := ../../antlr-$(ANTLR_VERSION).jar
GRAMMAR_FILE := ../../pyfcstm/dsl/grammar/Grammar.g4
PARSER_OUTPUT_DIR := ./parser

# Node/npm configuration
NPM := npm
TSC := npx tsc

help:
	@echo "FCSTM VSCode Extension Build Commands"
	@echo "======================================"
	@echo ""
	@echo "  make install    - Install npm dependencies"
	@echo "  make parser     - Generate JavaScript parser from ANTLR grammar"
	@echo "  make build      - Compile TypeScript to JavaScript"
	@echo "  make verify-p0.2 - Verify P0.2 parser integration"
	@echo "  make package    - Build VSIX package"
	@echo "  make clean      - Remove generated files"
	@echo "  make all        - Install deps, generate parser, and build"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Java (for ANTLR)"
	@echo "  - Node.js and npm"
	@echo "  - ANTLR jar at $(ANTLR_JAR)"
	@echo ""

all: install parser build

install:
	@echo "Installing npm dependencies..."
	$(NPM) install

parser: $(ANTLR_JAR) $(GRAMMAR_FILE)
	@echo "Generating JavaScript parser from ANTLR grammar..."
	@echo "Note: The grammar contains 'function' labels which conflict with JavaScript."
	@echo "      Generated parser will have these renamed to 'function_' automatically by ANTLR."
	@mkdir -p $(PARSER_OUTPUT_DIR)
	@find $(PARSER_OUTPUT_DIR) -mindepth 1 ! -name 'README.md' -exec rm -rf {} +
	java -jar $(ANTLR_JAR) -Dlanguage=JavaScript \
		-o $(PARSER_OUTPUT_DIR) \
		-Xexact-output-dir \
		-visitor \
		-no-listener \
		$(GRAMMAR_FILE)
	@echo "Parser generated successfully in $(PARSER_OUTPUT_DIR)/"
	@echo ""
	@echo "Generated files:"
	@ls -1 $(PARSER_OUTPUT_DIR)/*.js 2>/dev/null || echo "  (none yet - check for errors above)"

build:
	@echo "Compiling TypeScript..."
	$(TSC) -p ./
	@echo "Build complete. Output in ./out/"

verify-p0.2: build
	@echo "Running P0.2 verification script..."
	node ./scripts/verify-p0.2.js
	@echo "P0.2 verification completed successfully."

package: all
	@echo "Building VSIX package..."
	$(NPM) run package
	@echo "Package built successfully in ./build/"

clean:
	@echo "Cleaning generated files..."
	@find $(PARSER_OUTPUT_DIR) -mindepth 1 ! -name 'README.md' -exec rm -rf {} + 2>/dev/null || true
	rm -rf ./out
	rm -rf ./node_modules
	rm -rf ./build
	rm -f ./*.vsix
	@echo "Clean complete."

# Check if ANTLR jar exists
$(ANTLR_JAR):
	@echo "Error: ANTLR jar not found at $(ANTLR_JAR)"
	@echo "Please run 'make antlr' from the project root to download it."
	@exit 1
