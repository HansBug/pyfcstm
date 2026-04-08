# Makefile for FCSTM VSCode Extension
# This file provides commands for building and maintaining the extension

.PHONY: all parser clean install build package verify-p0.2 verify-p0.3 verify-p0.4 verify-p0.5 verify-p0.6 verify-p1.b verify-import-editor-support verify-semantic-editor-support verify test-e2e help syntaxes icons jsfcstm-install jsfcstm-build jsfcstm-pack

# ANTLR configuration
ANTLR_VERSION := 4.9.3
ANTLR_JAR := ../../antlr-$(ANTLR_VERSION).jar
GRAMMAR_LEXER_FILE := ../../pyfcstm/dsl/grammar/GrammarLexer.g4
GRAMMAR_PARSER_FILE := ../../pyfcstm/dsl/grammar/GrammarParser.g4
PARSER_OUTPUT_DIR := ./parser

# TextMate grammar configuration
SYNTAXES_DIR := ./syntaxes
TEXTMATE_SRC := ../fcstm.tmLanguage.json
TEXTMATE_DST := $(SYNTAXES_DIR)/fcstm.tmLanguage.json

# Node/npm configuration
NPM := npm
TSC := npx tsc
ROOT_DIR := ../..
JSFCSTM_DIR := ../jsfcstm

help:
	@echo "FCSTM VSCode Extension Build Commands"
	@echo "======================================"
	@echo ""
	@echo "  make install      - Install npm dependencies"
	@echo "  make jsfcstm-install - Install jsfcstm local package dependencies"
	@echo "  make jsfcstm-build - Build the local jsfcstm package"
	@echo "  make jsfcstm-pack  - Create the local jsfcstm tarball consumed by the extension"
	@echo "  make syntaxes     - Copy TextMate grammar from editors/"
	@echo "  make parser       - Generate legacy local parser artifacts from ANTLR grammar"
	@echo "  make build        - Build extension with esbuild (production, all-in-one)"
	@echo "  make build-dev    - Build extension (development mode with sourcemaps)"
	@echo "  make build-tsc    - Compile TypeScript only (for verification scripts)"
	@echo "  make verify-p0.2  - Verify P0.2 parser integration (32 tests)"
	@echo "  make verify-p0.3  - Verify P0.3 syntax diagnostics (35 tests)"
	@echo "  make verify-p0.4  - Verify P0.4 document symbols (35 tests)"
	@echo "  make verify-p0.5  - Verify P0.5 completion support (30 tests)"
	@echo "  make verify-p0.6  - Verify P0.6 hover documentation (35 tests)"
	@echo "  make verify-p1.b  - Verify P1.B language configuration reinforcement"
	@echo "  make verify-import-editor-support - Verify import-aware editor support"
	@echo "  make verify-semantic-editor-support - Verify scope/event/import semantic editor behavior"
	@echo "  make test-e2e     - Run end-to-end bundle verification (20 tests)"
	@echo "  make verify       - Run all verification tests"
	@echo "  make package      - Build VSIX package (runs all prerequisites)"
	@echo "  make clean        - Remove generated files"
	@echo "  make all          - Install deps, copy syntaxes, and build"
	@echo "  make icons        - Generate the packaged extension marketplace icon"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Java (for ANTLR)"
	@echo "  - Node.js and npm"
	@echo "  - ANTLR jar at $(ANTLR_JAR)"
	@echo ""

all: build

jsfcstm-install:
	@echo "Installing jsfcstm local package dependencies..."
	$(MAKE) -C $(JSFCSTM_DIR) install

jsfcstm-build:
	@echo "Building jsfcstm local package..."
	$(MAKE) -C $(JSFCSTM_DIR) build

jsfcstm-pack:
	@echo "Packing jsfcstm local package for extension consumption..."
	$(MAKE) -C $(JSFCSTM_DIR) pack

icons:
	@echo "Generating VSCode extension icon..."
	$(MAKE) -C $(ROOT_DIR) app_icons

install: jsfcstm-install jsfcstm-build jsfcstm-pack
	@echo "Installing npm dependencies..."
	@echo "Using package-lock-free install for the local jsfcstm tarball because each fresh npm pack can change tarball integrity."
	$(NPM) install --force --package-lock=false
	$(NPM) install --force --package-lock=false ../jsfcstm/jsfcstm.tgz

syntaxes: $(TEXTMATE_DST)

$(TEXTMATE_DST): $(TEXTMATE_SRC)
	@echo "Copying TextMate grammar..."
	@mkdir -p $(SYNTAXES_DIR)
	cp $(TEXTMATE_SRC) $(TEXTMATE_DST)
	@echo "TextMate grammar copied to $(TEXTMATE_DST)"

parser: $(ANTLR_JAR) $(GRAMMAR_LEXER_FILE) $(GRAMMAR_PARSER_FILE)
	@echo "Generating JavaScript parser from ANTLR grammar..."
	@echo "Using the canonical GrammarLexer.g4 + GrammarParser.g4 shared across Python and VSCode."
	@mkdir -p $(PARSER_OUTPUT_DIR)
	@find $(PARSER_OUTPUT_DIR) -mindepth 1 ! -name 'README.md' ! -name 'package.json' -exec rm -rf {} +
	java -jar $(ANTLR_JAR) -Dlanguage=JavaScript \
		-o $(PARSER_OUTPUT_DIR) \
		-Xexact-output-dir \
		-no-listener \
		$(GRAMMAR_LEXER_FILE) \
		$(GRAMMAR_PARSER_FILE)
	@echo "Parser generated successfully in $(PARSER_OUTPUT_DIR)/"
	@echo ""
	@echo "Generated files:"
	@ls -1 $(PARSER_OUTPUT_DIR)/*.js 2>/dev/null || echo "  (none yet - check for errors above)"

build: install icons syntaxes
	@echo "Building extension with esbuild..."
	node esbuild.config.js --production
	@echo "Build complete. Output in ./dist/"

build-dev: install icons syntaxes
	@echo "Building extension (development mode)..."
	node esbuild.config.js
	@echo "Development build complete. Output in ./dist/"

# Legacy TypeScript compilation (for verification scripts)
build-tsc: install syntaxes
	@echo "Compiling TypeScript (for verification scripts)..."
	$(TSC) -p ./
	@echo "TypeScript compilation complete. Output in ./out/"

verify-p0.2: build-tsc
	@echo "Running P0.2 verification script..."
	node ./scripts/verify-p0.2.js
	@echo ""

verify-p0.3: build-tsc
	@echo "Running P0.3 verification script..."
	node ./scripts/verify-p0.3.js
	@echo ""

verify-p0.4: build-tsc
	@echo "Running P0.4 verification script..."
	node ./scripts/verify-p0.4.js
	@echo ""

verify-p0.5: build-tsc
	@echo "Running P0.5 verification script..."
	node ./scripts/verify-p0.5.js
	@echo ""

verify-p0.6: build-tsc
	@echo "Running P0.6 verification script..."
	node ./scripts/verify-p0.6.js
	@echo ""

verify-p1.b:
	@echo "Running P1.B verification script..."
	node ./scripts/verify-p1.b.js
	@echo ""

verify-import-editor-support: build-tsc
	@echo "Running import editor support verification script..."
	node ./scripts/verify-import-editor-support.js
	@echo ""

verify-semantic-editor-support: build-tsc
	@echo "Running semantic editor support verification script..."
	node ./scripts/verify-semantic-editor-support.js
	@echo ""

test-e2e: build
	@echo "Running end-to-end bundle verification..."
	node ./scripts/test-e2e.js
	@echo ""

verify: verify-p0.2 verify-p0.3 verify-p0.4 verify-p0.5 verify-p0.6 verify-p1.b verify-import-editor-support verify-semantic-editor-support test-e2e
	@echo "All verification tests passed!"

package: all
	@echo "Building VSIX package..."
	@echo "Note: VSIX packaging keeps normal npm dependency traversal"
	@mkdir -p ./build
	$(NPM) run package
	@echo "Package built successfully in ./build/"
	@echo ""
	@echo "Verifying package contents..."
	@unzip -l ./build/*.vsix | grep -q "dist/extension.js" && echo "✓ Bundled extension.js included" || echo "✗ WARNING: extension.js not found in package!"
	@unzip -l ./build/*.vsix | grep -q "dist/server.js" && echo "✓ Bundled server.js included" || (echo "✗ Bundled server.js missing from package!" && exit 1)
	@unzip -l ./build/*.vsix | grep -q "resources/icon.png" && echo "✓ Extension icon included in package" || (echo "✗ Extension icon missing from package!" && exit 1)
	@echo "Package size:"
	@ls -lh ./build/*.vsix | awk '{print "  " $$9 ": " $$5}'

clean:
	@echo "Cleaning generated files..."
	@find $(PARSER_OUTPUT_DIR) -mindepth 1 ! -name 'README.md' ! -name 'package.json' -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(SYNTAXES_DIR)
	rm -rf ./out
	rm -rf ./dist
	rm -rf ./node_modules
	rm -rf ./build
	rm -f ./*.vsix
	$(MAKE) -C $(JSFCSTM_DIR) clean
	@echo "Clean complete."

# Check if ANTLR jar exists
$(ANTLR_JAR):
	@echo "ANTLR jar not found at $(ANTLR_JAR), downloading it from the project root..."
	$(MAKE) -C $(ROOT_DIR) antlr-$(ANTLR_VERSION).jar
