.PHONY: docs test unittest resource antlr antlr_build build package clean docs_auto todos_auto tests_auto rst_auto vscode vscode_clean vscode_install vscode_uninstall logos logos_clean app_icons app_icons_clean help tpl tpl_clean templates_package

PYTHON := $(shell which python)

PROJ_DIR      := .
DOC_DIR       := ${PROJ_DIR}/docs
BUILD_DIR     := ${PROJ_DIR}/build
DIST_DIR      := ${PROJ_DIR}/dist
TEST_DIR      := ${PROJ_DIR}/test
TESTFILE_DIR  := ${TEST_DIR}/testfile
DATASET_DIR   := ${TESTFILE_DIR}/dataset
SRC_DIR       := ${PROJ_DIR}/pyfcstm
TEMPLATES_DIR := ${PROJ_DIR}/templates
RESOURCE_DIR  := ${PROJ_DIR}/resource
LOGOS_DIR     := ${PROJ_DIR}/logos

RANGE_DIR      ?= .
RANGE_TEST_DIR := ${TEST_DIR}/${RANGE_DIR}
RANGE_SRC_DIR  := ${SRC_DIR}/${RANGE_DIR}
RANGE_SRC_DIR_TEST := ${TEST_DIR}/${RANGE_DIR}

COV_TYPES ?= xml term-missing

# LLM-based documentation generation options
AUTO_OPTIONS ?= --param max_tokens=400000 --no-ignore-module pyfcstm --no-ignore-module hbutils --model-name gpt-5.2-codex

# RST documentation generation variables
PYTHON_CODE_DIR   := ${SRC_DIR}
RST_DOC_DIR       := ${DOC_DIR}/source/api_doc
PYTHON_CODE_FILES := $(shell find ${PYTHON_CODE_DIR} -name "*.py" ! -name "__*.py" 2>/dev/null)
RST_DOC_FILES     := $(patsubst ${PYTHON_CODE_DIR}/%.py,${RST_DOC_DIR}/%.rst,${PYTHON_CODE_FILES})
PYTHON_NONM_FILES := $(shell find ${PYTHON_CODE_DIR} -name "__init__.py" 2>/dev/null)
RST_NONM_FILES    := $(foreach file,${PYTHON_NONM_FILES},$(patsubst %/__init__.py,%/index.rst,$(patsubst ${PYTHON_CODE_DIR}/%,${RST_DOC_DIR}/%,$(patsubst ${PYTHON_CODE_DIR}/__init__.py,${RST_DOC_DIR}/index.rst,${file}))))

ANTLR_VERSION ?= 4.9.3
ANTLR_GRAMMAR_DIR  := ${SRC_DIR}/dsl/grammar
ANTLR_GRAMMAR_FILE := ${ANTLR_GRAMMAR_DIR}/Grammar.g4

# VSCode extension variables
VSCODE_EXT_DIR := ${PROJ_DIR}/editors/vscode
APP_ICON_DIR := ${BUILD_DIR}/icons
APP_ICON_SOURCE := ${LOGOS_DIR}/logo.png
PYINSTALLER_ICON_ICO := ${APP_ICON_DIR}/pyfcstm.ico
PYINSTALLER_ICON_ICNS := ${APP_ICON_DIR}/pyfcstm.icns
PYINSTALLER_BUNDLE_ICON := ${APP_ICON_DIR}/pyfcstm.png
PYINSTALLER_BIN := ${DIST_DIR}/pyfcstm$(if ${IS_WIN},.exe,)
VSCODE_ICON := ${VSCODE_EXT_DIR}/resources/icon.png
APP_ICON_STAMP := ${APP_ICON_DIR}/.stamp

# Sample test generation related variables
MODEL_TEST_DIR   := ${TEST_DIR}/model
SAMPLE_CODES_DIR := ${TESTFILE_DIR}/sample_codes
SAMPLE_DSL_FILES := $(shell find ${SAMPLE_CODES_DIR} -name "*.fcstm" 2>/dev/null)
SAMPLE_TEST_FILES := $(patsubst ${SAMPLE_CODES_DIR}/%.fcstm,${MODEL_TEST_DIR}/test_sample_%.py,${SAMPLE_DSL_FILES})
SAMPLE_NEG_CODES_DIR := ${TESTFILE_DIR}/sample_neg_codes
SAMPLE_NEG_DSL_FILES := $(shell find ${SAMPLE_NEG_CODES_DIR} -name "*.fcstm" 2>/dev/null)
SAMPLE_NEG_TEST_FILES := $(patsubst ${SAMPLE_NEG_CODES_DIR}/%.fcstm,${MODEL_TEST_DIR}/test_sample_neg_%.py,${SAMPLE_NEG_DSL_FILES})

MODEL_SOURCE_FILES := \
	${SRC_DIR}/dsl/grammar/Grammar.g4 \
	${SRC_DIR}/dsl/listener.py \
	${SRC_DIR}/dsl/node.py \
	${SRC_DIR}/model/model.py \
	${SRC_DIR}/model/expr.py

# Help target
help:
	@echo "pyfcstm Build System"
	@echo "===================="
	@echo ""
	@echo "Building and Packaging:"
	@echo "  make package      - Build Python package (sdist and wheel)"
	@echo "  make build        - Build standalone executable with PyInstaller"
	@echo "  make clean        - Remove build artifacts"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests (alias for unittest)"
	@echo "  make unittest     - Run unit tests with pytest"
	@echo "                      Options: RANGE_DIR=<dir> COV_TYPES='xml term-missing'"
	@echo "                               MIN_COVERAGE=<percent> WORKERS=<n>"
	@echo "  make test_cli     - Test CLI executable"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs         - Build documentation (auto-detects language)"
	@echo "  make docs_en      - Build English documentation"
	@echo "  make docs_zh      - Build Chinese documentation"
	@echo "  make pdocs        - Build production documentation with versioning"
	@echo "  make rst_auto     - Generate RST documentation from Python source"
	@echo "                      Options: RANGE_DIR=<dir>"
	@echo ""
	@echo "LLM-Based Documentation (requires hbllmutils):"
	@echo "  make docs_auto    - Generate Python docstrings"
	@echo "  make todos_auto   - Complete TODO comments"
	@echo "  make tests_auto   - Generate unit tests"
	@echo "                      Options: RANGE_DIR=<dir> AUTO_OPTIONS='...'"
	@echo ""
	@echo "ANTLR Grammar:"
	@echo "  make antlr        - Download ANTLR jar and setup (requires Java)"
	@echo "  make antlr_build  - Regenerate parser from Grammar.g4"
	@echo ""
	@echo "Built-in Templates:"
	@echo "  make tpl          - Package repository templates into pyfcstm/template zip assets"
	@echo "  make tpl_clean    - Remove packaged template zip assets and index"
	@echo "  make templates_package - Alias of 'make tpl'"
	@echo ""
	@echo "Sample Tests:"
	@echo "  make sample       - Generate test files from sample DSL files"
	@echo "  make sample_clean - Remove generated sample tests"
	@echo ""
	@echo "VSCode Extension:"
	@echo "  make vscode          - Build VSCode extension package"
	@echo "  make vscode_clean    - Clean VSCode extension build artifacts"
	@echo "  make vscode_install  - Build and install VSCode extension via 'code' CLI"
	@echo "  make vscode_uninstall - Uninstall VSCode extension via 'code' CLI"
	@echo "  make app_icons       - Generate PyInstaller and VSCode application icons"
	@echo "  make app_icons_clean - Remove generated application icons"
	@echo ""
	@echo "Logos:"
	@echo "  make logos        - Generate PNG logos from SVG sources"
	@echo "  make logos_clean  - Remove generated PNG logos"
	@echo ""
	@echo "Common Variables:"
	@echo "  RANGE_DIR=<dir>   - Target specific directory (default: .)"
	@echo "  COV_TYPES=<types> - Coverage report types (default: xml term-missing)"
	@echo "  MIN_COVERAGE=<n>  - Minimum coverage percentage"
	@echo "  WORKERS=<n>       - Number of parallel test workers"
	@echo "  AUTO_OPTIONS=...  - LLM generation options"
	@echo ""

package: tpl
	$(PYTHON) -m build --sdist --wheel --outdir ${DIST_DIR}
build: tpl ${APP_ICON_STAMP}
	$(PYTHON) -m tools.generate_spec -o pyfcstm.spec --icon-dir ${APP_ICON_DIR}
	pyinstaller pyfcstm.spec
	@echo "Verifying bundled PyInstaller icon asset..."
	@pyi-archive_viewer -l ${PYINSTALLER_BIN} | grep -q "pyfcstm.png" && echo "✓ Bundled icon asset included in PyInstaller executable" || (echo "✗ Bundled icon asset missing from PyInstaller executable" && exit 1)

test_cli:
	python -m tools.test_cli dist/pyfcstm \
		--test-dsl docs/source/tutorials/cli/simple_machine.fcstm \
		--template-dir test/testfile/template_1
clean:
	rm -rf ${DIST_DIR} ${BUILD_DIR} *.egg-info
	rm -rf build dist pyfcstm.spec
	rm -f ${VSCODE_ICON}
	@rmdir --ignore-fail-on-non-empty ${VSCODE_EXT_DIR}/resources 2>/dev/null || true

test: unittest

unittest: tpl
	UNITTEST=1 \
		pytest "${RANGE_TEST_DIR}" \
		-sv -m unittest \
		--junitxml=junit.xml -o junit_family=legacy \
		$(shell for type in ${COV_TYPES}; do echo "--cov-report=$$type"; done) \
		--cov="${RANGE_SRC_DIR}" \
		$(if ${MIN_COVERAGE},--cov-fail-under=${MIN_COVERAGE},) \
		$(if ${WORKERS},-n ${WORKERS},)

docs:
	$(MAKE) -C "${DOC_DIR}" build
docs_en:
	READTHEDOCS_LANGUAGE=en $(MAKE) -C "${DOC_DIR}" build
docs_zh:
	READTHEDOCS_LANGUAGE=zh-cn $(MAKE) -C "${DOC_DIR}" build
pdocs:
	$(MAKE) -C "${DOC_DIR}" prod

tpl:
	$(PYTHON) -m tools.package_templates --source ${TEMPLATES_DIR} --output ${SRC_DIR}/template

templates_package: tpl

tpl_clean:
	rm -f ${SRC_DIR}/template/*.zip ${SRC_DIR}/template/index.json

# LLM-based documentation generation targets
docs_auto:
	python -m hbllmutils code pydoc -i "${RANGE_SRC_DIR}" ${AUTO_OPTIONS}
todos_auto:
	python -m hbllmutils code todo -i "${RANGE_SRC_DIR}" ${AUTO_OPTIONS}
tests_auto:
	python -m hbllmutils code unittest -i "${RANGE_SRC_DIR}" -o "${RANGE_SRC_DIR_TEST}" ${AUTO_OPTIONS}

# RST documentation generation targets
rst_auto: ${RST_DOC_FILES} ${RST_NONM_FILES} auto_rst_top_index.py
	python auto_rst_top_index.py -i ${PYTHON_CODE_DIR} -o ${DOC_DIR}/source

${RST_DOC_DIR}/%.rst: ${PYTHON_CODE_DIR}/%.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	python auto_rst.py -i $< -o $@

${RST_DOC_DIR}/%/index.rst: ${PYTHON_CODE_DIR}/%/__init__.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	python auto_rst.py -i $< -o $@

${RST_DOC_DIR}/index.rst: ${PYTHON_CODE_DIR}/__init__.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	python auto_rst.py -i $< -o $@

antlr-${ANTLR_VERSION}.jar:
	wget -O $@ https://www.antlr.org/download/antlr-${ANTLR_VERSION}-complete.jar

antlr: antlr-${ANTLR_VERSION}.jar
	$(PYTHON) antlr_req.py -v ${ANTLR_VERSION}
	pip install -r requirements.txt

antlr_build:
	java -jar antlr-${ANTLR_VERSION}.jar -Dlanguage=Python3 ${ANTLR_GRAMMAR_FILE}
	ruff format ${ANTLR_GRAMMAR_DIR}

# Generate sample test files
sample: ${SAMPLE_TEST_FILES} ${SAMPLE_NEG_TEST_FILES}

${MODEL_TEST_DIR}/test_sample_%.py: ${SAMPLE_CODES_DIR}/%.fcstm sample_test_generator.py ${MODEL_SOURCE_FILES}
	@mkdir -p ${MODEL_TEST_DIR}
	UNITTEST=1 $(PYTHON) sample_test_generator.py -i $< -o $@
	ruff format $@

${MODEL_TEST_DIR}/test_sample_neg_%.py: ${SAMPLE_NEG_CODES_DIR}/%.fcstm sample_test_neg_generator.py ${MODEL_SOURCE_FILES}
	@mkdir -p ${MODEL_TEST_DIR}
	UNITTEST=1 $(PYTHON) sample_test_neg_generator.py -i $< -o $@
	ruff format $@

sample_clean:
	rm -rf ${SAMPLE_TEST_FILES}
	rm -rf ${SAMPLE_NEG_TEST_FILES}

# VSCode extension build targets
vscode:
	@echo "Building VSCode extension..."
	$(MAKE) -C ${VSCODE_EXT_DIR} package
	@echo "VSCode extension built successfully at ${VSCODE_EXT_DIR}/build/"

vscode_clean:
	$(MAKE) -C ${VSCODE_EXT_DIR} clean
	$(MAKE) app_icons_clean

vscode_install: vscode
	@echo "Installing VSCode extension..."
	code --install-extension $(shell ls ${VSCODE_EXT_DIR}/build/*.vsix | tail -1)
	@echo "VSCode extension installed successfully."

vscode_uninstall:
	@echo "Uninstalling VSCode extension..."
	code --uninstall-extension hansbug.fcstm-language-support
	@echo "VSCode extension uninstalled successfully."

app_icons: ${APP_ICON_STAMP}

${APP_ICON_STAMP}: ${APP_ICON_SOURCE} tools/generate_app_icons.py
	@mkdir -p ${APP_ICON_DIR}
	$(PYTHON) tools/generate_app_icons.py \
		--input $< \
		--pyinstaller-ico ${PYINSTALLER_ICON_ICO} \
		--pyinstaller-icns ${PYINSTALLER_ICON_ICNS} \
		--pyinstaller-png ${PYINSTALLER_BUNDLE_ICON} \
		--vscode-png ${VSCODE_ICON}
	@touch $@

app_icons_clean:
	rm -rf ${APP_ICON_DIR}
	rm -f ${VSCODE_ICON}
	@rmdir --ignore-fail-on-non-empty ${VSCODE_EXT_DIR}/resources 2>/dev/null || true

# Logo generation targets
LOGO_SVG_FILES := ${LOGOS_DIR}/logo.svg ${LOGOS_DIR}/logo_banner.svg
LOGO_PNG_FILES := ${LOGOS_DIR}/logo.png ${LOGOS_DIR}/logo_banner.png

logos: ${LOGO_PNG_FILES}

${LOGOS_DIR}/%.png: ${LOGOS_DIR}/%.svg tools/svg2png.py
	@echo "Converting $< to $@..."
	$(PYTHON) tools/svg2png.py -i $< -o $@

logos_clean:
	@echo "Cleaning generated logo PNG files..."
	rm -f ${LOGO_PNG_FILES}
