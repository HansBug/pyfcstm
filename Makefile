.PHONY: docs docs_en docs_zh docs_pdf docs_pdf_en docs_pdf_zh test unittest template_unittest resource antlr antlr_build fcstm_antlr_build fbmcq_antlr_build build build_info build_info_cli package clean rst_auto sha256 jsfcstm jsfcstm_clean vscode vscode_clean vscode_install vscode_uninstall logos logos_clean app_icons app_icons_clean help tpl tpl_clean templates_package template_packaging_check template_source_install_check docs_terminology_check release_pipeline_identity_check test_boundary_check resource_ownership_check semantics_boundary_check semantics_check c_kernel_alignment_check deprecation_check fixture_corpus_check inspect_structure_parity_check public_payload_contract_check api_doc_toctree_check bmc_docs_check bmc_benchmark_check bmc_benchmark bmc_solving_benchmark_check bmc_solving_benchmark build_assets build_assets_clean diagram_assets_check diagram_rendering_check diagram_browser_check diagram_contract_check diagram_data_check diagram_options_check diagram_csp_check diagram_parity_check diagram_reference_check diagram_export_limits_check diagram_headless_check diagram_notebooks_check diagram_browser_headless_check diagram_engine_floor diagram_provenance_check diagram_viewer_gate_check diagram_webview_expander_check diagram_assets_verify diagram_package_check diagram_corpus diagram_viewer_option_flow_check doctest docs_doctest bmc_construction_check

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
SHA256_SOURCE_FILES := \
	${SRC_DIR}/llm/fcstm_grammar_guide.md \
	${SRC_DIR}/llm/fbmcq_language_guide.md
SHA256_FILES := $(addsuffix .sha256,${SHA256_SOURCE_FILES})

RANGE_DIR      ?= .
RANGE_TEST_DIR := ${TEST_DIR}/${RANGE_DIR}
RANGE_SRC_DIR  := ${SRC_DIR}/${RANGE_DIR}

# Frozen custom-backend reference bundle used by the required parity gate.
# It is intentionally external to the source tree and must be restored by the
# maintainer/CI workflow before ``diagram_assets_verify`` is run.
DIAGRAM_REFERENCE ?=

COV_TYPES ?= xml term-missing

# BMC infeasibility benchmark: measured repetitions and discarded warmups.
BMC_BENCHMARK_REPETITIONS ?= 5
BMC_BENCHMARK_WARMUPS     ?= 1

# RST documentation generation variables
PYTHON_CODE_DIR   := ${SRC_DIR}
RST_DOC_DIR       := ${DOC_DIR}/source/api_doc
PYTHON_CODE_FILES := $(filter-out ${SRC_DIR}/config/build_info.py,$(shell find ${PYTHON_CODE_DIR} -name "*.py" ! -name "__*.py" 2>/dev/null))
RST_DOC_FILES     := $(patsubst ${PYTHON_CODE_DIR}/%.py,${RST_DOC_DIR}/%.rst,${PYTHON_CODE_FILES})
PYTHON_NONM_FILES := $(shell find ${PYTHON_CODE_DIR} -name "__init__.py" 2>/dev/null)
RST_NONM_FILES    := $(foreach file,${PYTHON_NONM_FILES},$(patsubst %/__init__.py,%/index.rst,$(patsubst ${PYTHON_CODE_DIR}/%,${RST_DOC_DIR}/%,$(patsubst ${PYTHON_CODE_DIR}/__init__.py,${RST_DOC_DIR}/index.rst,${file}))))

ANTLR_VERSION ?= 4.9.3
ANTLR_GRAMMAR_DIR  := ${SRC_DIR}/dsl/grammar
ANTLR_LEXER_GRAMMAR_FILE := ${ANTLR_GRAMMAR_DIR}/GrammarLexer.g4
ANTLR_PARSER_GRAMMAR_FILE := ${ANTLR_GRAMMAR_DIR}/GrammarParser.g4
BMC_ANTLR_GRAMMAR_DIR  := ${SRC_DIR}/bmc/grammar
BMC_ANTLR_LEXER_GRAMMAR_FILE := ${BMC_ANTLR_GRAMMAR_DIR}/BmcQueryLexer.g4
BMC_ANTLR_PARSER_GRAMMAR_FILE := ${BMC_ANTLR_GRAMMAR_DIR}/BmcQueryParser.g4

# VSCode extension variables
VSCODE_EXT_DIR := ${PROJ_DIR}/editors/vscode
JSFCSTM_DIR := ${PROJ_DIR}/editors/jsfcstm
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
SAMPLE_DSL_ENTRY_DIRS := $(shell find ${SAMPLE_CODES_DIR} -mindepth 1 -type f -name "main.fcstm" -printf '%h\n' 2>/dev/null)
SAMPLE_FLAT_DSL_FILES := $(filter-out $(foreach dir,${SAMPLE_DSL_ENTRY_DIRS},${dir}/%),${SAMPLE_DSL_FILES})
SAMPLE_TEST_FILES := \
	$(patsubst ${SAMPLE_CODES_DIR}/%.fcstm,${MODEL_TEST_DIR}/test_sample_%.py,${SAMPLE_FLAT_DSL_FILES}) \
	$(patsubst ${SAMPLE_CODES_DIR}/%,${MODEL_TEST_DIR}/test_sample_%.py,${SAMPLE_DSL_ENTRY_DIRS})
SAMPLE_NEG_CODES_DIR := ${TESTFILE_DIR}/sample_neg_codes
SAMPLE_NEG_DSL_FILES := $(shell find ${SAMPLE_NEG_CODES_DIR} -name "*.fcstm" 2>/dev/null)
SAMPLE_NEG_TEST_FILES := $(patsubst ${SAMPLE_NEG_CODES_DIR}/%.fcstm,${MODEL_TEST_DIR}/test_sample_neg_%.py,${SAMPLE_NEG_DSL_FILES})

MODEL_SOURCE_FILES := \
	${SRC_DIR}/dsl/grammar/GrammarLexer.g4 \
	${SRC_DIR}/dsl/grammar/GrammarParser.g4 \
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
	@echo "  make build_info   - Generate build identity for a package or CLI build"
	@echo "  make build_assets - Build ignored Python diagram JS/WASM/font assets"
	@echo "  make diagram_assets_check - Build and validate diagram assets and ignore rules"
	@echo "  make diagram_browser_check - Run representative offline Chrome export gate"
	@echo "  make diagram_contract_check - Verify the public snapshot and portable data contract"
	@echo "  make diagram_data_check - Verify parsed, imported and programmatic data parity"
	@echo "  make diagram_options_check - Verify option and view-state mapping parity"
	@echo "  make diagram_csp_check - Verify the standalone HTML policy and embedded resources"
	@echo "  make diagram_export_limits_check - Compare export size limits across both export paths"
	@echo "  make diagram_headless_check - Exercise synchronous SVG/PNG/PDF export over the canonical corpus"
	@echo "  make diagram_notebooks_check - Check the notebook representation is stored, round-tripped and self-contained"
	@echo "  make diagram_browser_headless_check - Require the browser download and the synchronous export to agree"
	@echo "  make diagram_assets_verify - Run provenance, runtime, contract, and visual asset gates"
	@echo "  make diagram_parity_check DIAGRAM_REFERENCE=/abs/path/reference.json"
	@echo "  make diagram_reference_check - Verify reference archive retry behavior"
	@echo "  make diagram_corpus - Rebuild checked-in DiagramData rendering oracles"
	@echo "  make build_assets_clean - Remove generated diagram assets"
	@echo "  make clean        - Remove build artifacts"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests (alias for unittest)"
	@echo "  make unittest     - Run unit tests with pytest"
	@echo "  make template_unittest - Run selected built-in template pytest suites"
	@echo "                      Options: RANGE_DIR=<dir> COV_TYPES='xml term-missing'"
	@echo "                               MIN_COVERAGE=<percent> WORKERS=<n>"
	@echo "  make test_cli     - Test CLI executable"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs         - Build documentation (auto-detects language)"
	@echo "  make docs_en      - Build English documentation"
	@echo "  make docs_zh      - Build Chinese documentation"
	@echo "  make docs_pdf     - Build and validate English and Chinese PDFs"
	@echo "  make docs_pdf_en  - Build and validate the English PDF"
	@echo "  make docs_pdf_zh  - Build and validate the Chinese PDF"
	@echo "  make pdocs        - Build production documentation with versioning"
	@echo "  make rst_auto     - Generate RST documentation from Python source"
	@echo "                      Options: RANGE_DIR=<dir>"
	@echo "  make docs_terminology_check - Check Chinese documentation terminology"
	@echo "  make release_pipeline_identity_check - Check that Release Test and release run the same pipeline"
	@echo "  make sha256       - Update generated SHA-256 sidecar files"
	@echo ""
	@echo "ANTLR Grammar:"
	@echo "  make antlr        - Download ANTLR jar and setup (requires Java)"
	@echo "  make antlr_build - Regenerate both FCSTM and FBMCQ lexer/parser files"
	@echo "  make fcstm_antlr_build - Regenerate FCSTM lexer/parser from Grammar*.g4"
	@echo "  make fbmcq_antlr_build - Regenerate FBMCQ lexer/parser from BmcQuery*.g4"
	@echo ""
	@echo "Built-in Templates:"
	@echo "  make tpl          - Package repository templates into pyfcstm/template zip assets"
	@echo "  make tpl_clean    - Remove packaged template zip assets and index"
	@echo "  make templates_package - Alias of 'make tpl'"
	@echo "  make template_packaging_check - Validate repository template packaging contracts"
	@echo "  make template_source_install_check - Validate source-install template extraction"
	@echo "  make test_boundary_check - Validate pytest test-boundary rules"
	@echo "  make resource_ownership_check - Report handlers opened while holding a resource"
	@echo "  make semantics_boundary_check - Reject operator semantics defined outside the operator catalog"
	@echo "  make semantics_check - Compare runnable and Z3 operator semantics, and BMC runtime safety with simulation"
	@echo "  make c_kernel_alignment_check - Compare the generated c / c_poll runtimes with the simulator on random region models"
	@echo "  make deprecation_check - Audit versioned deprecations against the current version"
	@echo "  make inspect_structure_parity_check - Check Python/jsfcstm structure-statistics fixtures"
	@echo "  make public_payload_contract_check - Reject version markers in public inspect/BMC payloads"
	@echo "  make fixture_corpus_check - Validate the shared semantic fixture corpus contract"
	@echo "  make doctest      - Run the docstring example gate (separate from unittest)"
	@echo "                      Options: DOCTEST_SCOPE=pyfcstm/bmc DOCTEST_ARGS='-q'"
	@echo "  make docs_doctest - Run the examples written in the documentation pages (separate from doctest)"
	@echo "                      Options: DOCS_DOCTEST_SCOPE=docs/source/tutorials/regions DOCS_DOCTEST_ARGS='-q'"
	@echo "  make api_doc_toctree_check - Validate generated API documentation toctrees"
	@echo "  make bmc_docs_check - Validate the BMC documentation contracts"
	@echo "  make bmc_benchmark_check - Validate the BMC infeasibility benchmark corpus"
	@echo "  make bmc_construction_check - Compare BMC construction modes and solver contexts on the benchmark corpus"
	@echo "  make bmc_benchmark - Measure explanation cost across baseline/none/formal/proof"
	@echo "  make bmc_solving_benchmark_check - Validate the BMC solving benchmark corpus, thresholds and saved runs"
	@echo "  make bmc_solving_benchmark - Measure BMC solving cost across the option arms"
	@echo ""
	@echo "Sample Tests:"
	@echo "  make sample       - Generate test files from sample DSL files"
	@echo "  make sample_clean - Remove generated sample tests"
	@echo ""
	@echo "VSCode Extension:"
	@echo "  make jsfcstm         - Install, build, test, and pack the jsfcstm npm package"
	@echo "  make jsfcstm_clean   - Clean jsfcstm npm package artifacts"
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
	@echo ""

package: build_assets diagram_assets_check build_info
	rm -rf ${BUILD_DIR}
	rm -f ${DIST_DIR}/*.whl ${DIST_DIR}/*.tar.gz
	$(PYTHON) -m build --sdist --wheel --outdir ${DIST_DIR}
	$(PYTHON) tools/check_diagram_package.py --check
	$(PYTHON) tools/check_diagram_package.py --dist-dir ${DIST_DIR}
build_info: build_assets diagram_assets_check tpl
	$(PYTHON) -m tools.write_build_info

build_info_cli: ${APP_ICON_STAMP} build_info

build: build_assets diagram_assets_check build_info_cli
	$(PYTHON) -m tools.generate_spec -o pyfcstm.spec --icon-dir ${APP_ICON_DIR}
	pyinstaller pyfcstm.spec
	@echo "Verifying bundled PyInstaller icon asset..."
	@pyi-archive_viewer -l ${PYINSTALLER_BIN} | grep -q "pyfcstm.png" && echo "✓ Bundled icon asset included in PyInstaller executable" || (echo "✗ Bundled icon asset missing from PyInstaller executable" && exit 1)

test_cli:
	python -m tools.test_cli dist/pyfcstm \
		--test-dsl docs/source/tutorials/cli/simple_machine.fcstm \
		--template-dir test/testfile/template_1
clean:
	$(MAKE) build_assets_clean
	rm -rf ${DIST_DIR} ${BUILD_DIR} *.egg-info
	rm -rf build dist pyfcstm.spec
	rm -f ${SRC_DIR}/config/build_info.py
	rm -f ${VSCODE_ICON}
	@rmdir --ignore-fail-on-non-empty ${VSCODE_EXT_DIR}/resources 2>/dev/null || true

test: unittest

unittest: build_assets diagram_assets_check tpl
	UNITTEST=1 \
		pytest "${RANGE_TEST_DIR}" \
		-sv -m unittest \
		--junitxml=junit.xml -o junit_family=legacy \
		$(shell for type in ${COV_TYPES}; do echo "--cov-report=$$type"; done) \
		--cov="${RANGE_SRC_DIR}" \
		$(if ${MIN_COVERAGE},--cov-fail-under=${MIN_COVERAGE},) \
		$(if ${WORKERS},-n ${WORKERS},)

template_unittest: build_assets diagram_assets_check tpl
	UNITTEST=1 $(PYTHON) tools/run_template_suites.py --no-package $(TEMPLATE_UNITTEST_ARGS)

docs:
	$(MAKE) -C "${DOC_DIR}" build
docs_en:
	READTHEDOCS_LANGUAGE=en $(MAKE) -C "${DOC_DIR}" build
docs_zh:
	READTHEDOCS_LANGUAGE=zh-cn $(MAKE) -C "${DOC_DIR}" build
docs_pdf:
	$(MAKE) -C "${DOC_DIR}" pdf
docs_pdf_en:
	$(MAKE) -C "${DOC_DIR}" pdf_en
docs_pdf_zh:
	$(MAKE) -C "${DOC_DIR}" pdf_zh
pdocs:
	$(MAKE) -C "${DOC_DIR}" prod

tpl:
	$(PYTHON) -m tools.package_templates --source ${TEMPLATES_DIR} --output ${SRC_DIR}/template

templates_package: tpl

tpl_clean:
	rm -f ${SRC_DIR}/template/*.zip ${SRC_DIR}/template/index.json

build_assets:
	$(PYTHON) tools/build_diagram_assets.py

build_assets_clean:
	$(PYTHON) tools/build_diagram_assets.py --clean

diagram_assets_check: build_assets
	$(PYTHON) tools/build_diagram_assets.py --check
	$(PYTHON) tools/check_diagram_assets.py

diagram_browser_check: build_assets
	@if test -n "$(DIAGRAM_HTML)"; then \
		node tools/diagram_assets/check_viewer_browser.js "$(DIAGRAM_HTML)" "$(DIAGRAM_SCREENSHOT)"; \
	else \
		$(PYTHON) tools/check_diagram_browser_exports.py --all-cases --formats svg,png,pdf --pdf-require-zero-images --pdf-page-size-match --pdf-rerender; \
	fi

diagram_contract_check: build_assets
	$(PYTHON) tools/check_diagram_contract.py

diagram_data_check: build_assets
	$(PYTHON) tools/check_diagram_data_parity.py

diagram_options_check: build_assets
	$(PYTHON) tools/check_diagram_options_parity.py

diagram_csp_check: build_assets
	$(PYTHON) tools/check_diagram_csp.py --check
	$(PYTHON) tools/check_diagram_csp.py \
		--require-default-none --require-connect-none --require-worker-none \
		--require-script-hashes --require-style-hashes --require-style-nonce \
		--require-wasm-unsafe-eval --forbid-unsafe-eval \
		--require-no-fallback-directives \
		--require-font-data --require-img-data-blob \
		--forbid-eval --forbid-new-function --zero-network \
		--require-embedded-fonts 5 --require-fonts-ready

diagram_docstring_check: build_assets
	$(PYTHON) tools/check_diagram_docstring_examples.py --check
	$(PYTHON) tools/check_diagram_docstring_examples.py

diagram_rendering_check: build_assets
	$(PYTHON) tools/check_diagram_rendering.py --check
	$(PYTHON) tools/check_diagram_rendering.py \
		--corpus tools/diagram_assets/corpus/canonical-arrows.json \
		--expected-layouts 15 --expected-arrows 130 \
		--expected-directions right=32,down=78,left=5,up=15 --check-cjk
	$(PYTHON) tools/check_diagram_rendering.py \
		--corpus tools/diagram_assets/corpus/shared-layouts.json \
		--expected-layouts 20 --expected-arrows 176 \
		--expected-groups LR=10,TB=10

diagram_parity_check: build_assets
	@test -n "$(DIAGRAM_REFERENCE)" || (echo "DIAGRAM_REFERENCE is required; restore the frozen custom reference bundle and run make DIAGRAM_REFERENCE=/abs/path/reference.json diagram_assets_verify" >&2; exit 2)
	@test -f "$(DIAGRAM_REFERENCE)" || (echo "DIAGRAM_REFERENCE is not a file: $(DIAGRAM_REFERENCE)" >&2; exit 2)
	$(PYTHON) tools/check_diagram_rendering.py \
		--corpus tools/diagram_assets/corpus/canonical-arrows.json \
		--corpus tools/diagram_assets/corpus/shared-layouts.json \
		--expected-layouts 35 --expected-arrows 306 \
		--expected-directions right=107,down=153,left=18,up=28 \
		--compare-reference "$(DIAGRAM_REFERENCE)" --check-expanded-id-only \
		--check-cjk --check-memory

diagram_corpus: jsfcstm
	node tools/diagram_assets/generate_corpus.js

diagram_engine_floor: build_assets
	$(PYTHON) tools/check_diagram_engine_floor.py --all-cases --check-timeout-reset

diagram_provenance_check:
	$(PYTHON) tools/check_diagram_provenance.py

diagram_browser_headless_check: build_assets
	$(PYTHON) tools/check_diagram_browser_headless.py --check
	$(PYTHON) tools/check_diagram_browser_headless.py --all-cases --formats svg,png,pdf

diagram_notebooks_check: build_assets
	$(PYTHON) tools/check_diagram_notebooks.py --check
	$(PYTHON) tools/check_diagram_notebooks.py

diagram_headless_check: build_assets
	$(PYTHON) tools/check_diagram_headless.py --check
	$(PYTHON) tools/check_diagram_headless.py \
		--all-cases --formats svg,png,pdf --repeat 3 \
		--png-scales 1,2,4 --pdf-require-zero-images --pdf-page-size-match

diagram_export_limits_check:
	$(PYTHON) tools/check_diagram_export_limits.py --check
	$(PYTHON) tools/check_diagram_export_limits.py

diagram_reference_check:
	$(PYTHON) tools/fetch_diagram_reference.py --check

diagram_assets_verify: diagram_assets_check diagram_docstring_check diagram_rendering_check diagram_contract_check diagram_data_check diagram_options_check diagram_csp_check diagram_export_limits_check diagram_parity_check diagram_engine_floor diagram_provenance_check diagram_reference_check diagram_viewer_gate_check diagram_viewer_option_flow_check

diagram_viewer_gate_check:
	node tools/diagram_assets/check_viewer_browser.js --check

# Needs build_assets for the same reason the gates above it do, though for a
# narrower part of it: the check bundles the webview's own source with esbuild,
# and esbuild arrives through the `npm ci` that `build_assets` runs. Declaring
# it matters because make walks prerequisites left to right -- listed without
# this line the check ran before anything had installed, and a clean checkout
# failed on `Cannot find module 'esbuild'` rather than on anything it tests.
diagram_viewer_option_flow_check: build_assets
	node tools/check_viewer_option_flow.js

# Depends on build_assets like the other diagram gates: the renderer's assets are
# build products rather than tracked sources, and both halves of this check need
# them -- one to produce the canonical document, the other to expand it.
diagram_webview_expander_check: build_assets
	$(PYTHON) tools/check_diagram_webview_expander.py --check
	cd editors/vscode && npm run compile:tsc
	$(PYTHON) tools/check_diagram_webview_expander.py

diagram_package_check: package

template_packaging_check:
	$(PYTHON) tools/check_template_packaging.py

template_source_install_check:
	$(PYTHON) tools/check_template_source_install.py

docs_terminology_check:
	$(PYTHON) tools/check_docs_terminology.py --self-check
	$(PYTHON) tools/check_docs_terminology.py --check

# release.yml (publish: true) and release_test.yml (publish: false) must both be
# a thin call of release_pipeline.yml, whose only mode-dependent steps are the
# publishing steps of publish_release and the rehearsal upload that replaces them.
define RELEASE_PIPELINE_IDENTITY_PY
import copy
import sys

import yaml

WORKFLOWS = ".github/workflows/"
PIPELINE = "./.github/workflows/release_pipeline.yml"
MODE_LEAKS = ("github.event", "github.ref", "github.sha", "GITHUB_REF", "GITHUB_SHA")


def load(name):
    with open(WORKFLOWS + name, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def dump(value):
    return yaml.safe_dump(value, sort_keys=True)


def check_entry(name, workflow, publish):
    problems = []
    jobs = workflow["jobs"]
    callers = [key for key, job in jobs.items() if "uses" in job]
    others = [key for key in jobs if key not in callers]
    if len(callers) != 1 or len(others) != 1:
        return ["{}: expected one job that names the release and one that calls the pipeline, got {}".format(name, sorted(jobs))]
    caller, resolver = jobs[callers[0]], jobs[others[0]]
    if caller["uses"] != PIPELINE:
        problems.append("{}: calls {} instead of {}".format(name, caller["uses"], PIPELINE))
    arguments = caller.get("with") or {}
    if set(arguments) != {"tag", "commit", "publish"} or arguments.get("publish") is not publish:
        problems.append("{}: must pass only tag, commit and publish: {}".format(name, publish))
    if set(resolver.get("outputs") or {}) != {"tag", "commit"}:
        problems.append("{}: job {} must output only tag and commit".format(name, others[0]))
    for step in resolver.get("steps") or []:
        if "uses" in step and not step["uses"].startswith("actions/checkout@"):
            problems.append("{}: job {} may only check out and compute names, not use {}".format(name, others[0], step["uses"]))
        for word in ("make ", "pip ", "gh ", "upload", "publish"):
            if word in step.get("run", ""):
                problems.append("{}: job {} runs {!r}; release work belongs in the pipeline".format(name, others[0], word.strip()))
    return problems


def check_pipeline(pipeline, text):
    problems = []
    triggers = pipeline.get(True, pipeline.get("on"))
    if set(triggers) != {"workflow_call"}:
        problems.append("release_pipeline.yml: must only be callable, not triggered: {}".format(sorted(triggers)))
    for leak in MODE_LEAKS:
        if leak in text:
            problems.append("release_pipeline.yml: refers to {}; release and rehearsal may only differ through inputs.publish".format(leak))
    publish_steps, rehearsal_steps = [], []
    for job_name, job in pipeline["jobs"].items():
        if "inputs.publish" in dump({key: value for key, value in job.items() if key != "steps"}):
            problems.append("release_pipeline.yml: job {} depends on inputs.publish".format(job_name))
        conditional_seen = False
        for step in job.get("steps") or []:
            condition = str(step.get("if", ""))
            if "inputs.publish" in dump({key: value for key, value in step.items() if key != "if"}):
                problems.append("release_pipeline.yml: step {!r} uses inputs.publish outside its condition".format(step.get("name")))
            if "inputs.publish" not in condition:
                if conditional_seen:
                    problems.append("release_pipeline.yml: shared step {!r} runs after a publishing step".format(step.get("name")))
                continue
            conditional_seen = True
            if job_name != "publish_release":
                problems.append("release_pipeline.yml: step {!r} of job {} depends on inputs.publish".format(step.get("name"), job_name))
            normalized = condition.replace(" ", "")
            if normalized.endswith("{{inputs.publish}}"):
                publish_steps.append(step)
            elif normalized.endswith("{{!inputs.publish}}"):
                rehearsal_steps.append(step)
            else:
                problems.append("release_pipeline.yml: step {!r} has condition {!r}".format(step.get("name"), condition))
    if len(publish_steps) != 3:
        problems.append("release_pipeline.yml: expected 3 publishing steps, got {}".format(len(publish_steps)))
    for step in publish_steps:
        if "uses" in step:
            if not step["uses"].startswith("pypa/gh-action-pypi-publish@") or (step.get("with") or {}).get("packages-dir") != "pypi-dist":
                problems.append("release_pipeline.yml: publishing step {!r} may only upload pypi-dist to PyPI".format(step.get("name")))
            continue
        for line in step.get("run", "").splitlines():
            line = line.strip()
            if line and not line.startswith(("set -euo pipefail", "gh release ", 'test "$$(gh release ')):
                problems.append("release_pipeline.yml: publishing step {!r} runs {!r}; only gh release commands may differ".format(step.get("name"), line))
    if not any("gh release upload" in step.get("run", "") and "release-assets/*" in step.get("run", "") for step in publish_steps):
        problems.append("release_pipeline.yml: no publishing step uploads release-assets/*")
    if len(rehearsal_steps) != 1:
        problems.append("release_pipeline.yml: expected 1 rehearsal step, got {}".format(len(rehearsal_steps)))
    for step in rehearsal_steps:
        if not step.get("uses", "").startswith("actions/upload-artifact@") or (step.get("with") or {}).get("path") != "release-assets/*":
            problems.append("release_pipeline.yml: the rehearsal step must upload release-assets/* as an artifact")
    return problems


def find_problems(release, release_test, pipeline, pipeline_text):
    return (
        check_entry("release.yml", release, True)
        + check_entry("release_test.yml", release_test, False)
        + check_pipeline(pipeline, pipeline_text)
    )


def self_check(release, release_test, pipeline, text):
    assert find_problems(release, release_test, pipeline, text) == [], find_problems(release, release_test, pipeline, text)

    def expect(fragment, release=release, release_test=release_test, pipeline=pipeline, text=text):
        found = find_problems(release, release_test, pipeline, text)
        assert any(fragment in item for item in found), (fragment, found)

    mutated = copy.deepcopy(release_test)
    mutated["jobs"]["extra"] = {"runs-on": "ubuntu-22.04", "steps": [{"run": "true"}]}
    expect("release_test.yml: expected one job", release_test=mutated)
    mutated = copy.deepcopy(release_test)
    next(job for job in mutated["jobs"].values() if "uses" in job)["with"]["publish"] = True
    expect("release_test.yml: must pass only", release_test=mutated)
    mutated = copy.deepcopy(release)
    next(job for job in mutated["jobs"].values() if "uses" not in job)["steps"].append({"run": "make package"})
    expect("release.yml: job", release=mutated)
    mutated = copy.deepcopy(pipeline)
    mutated["jobs"]["package_stage"]["steps"][0]["if"] = "$${{ inputs.publish }}"
    expect("of job package_stage depends on inputs.publish", pipeline=mutated)
    mutated = copy.deepcopy(pipeline)
    mutated["jobs"]["publish_release"]["steps"] = [s for s in mutated["jobs"]["publish_release"]["steps"] if "!inputs.publish" not in str(s.get("if", ""))]
    expect("expected 1 rehearsal step", pipeline=mutated)
    mutated = copy.deepcopy(pipeline)
    step = next(s for s in mutated["jobs"]["publish_release"]["steps"] if "gh release upload" in s.get("run", ""))
    step["run"] += "\nmake package\n"
    expect("only gh release commands may differ", pipeline=mutated)
    mutated = copy.deepcopy(pipeline)
    mutated["jobs"]["publish_release"]["steps"].append({"name": "late", "run": "true"})
    expect("runs after a publishing step", pipeline=mutated)
    expect("refers to github.event", text=text + "\n# $${{ github.event_name }}\n")


def main():
    release, release_test = load("release.yml"), load("release_test.yml")
    pipeline = load("release_pipeline.yml")
    with open(WORKFLOWS + "release_pipeline.yml", encoding="utf-8") as stream:
        text = stream.read()
    problems = find_problems(release, release_test, pipeline, text)
    for item in problems:
        print("ERROR:", item)
    if problems:
        sys.exit(1)
    # Prove the check can fail: each mutation below is a drift it must report.
    self_check(release, release_test, pipeline, text)
    print("release pipeline identity: release.yml and release_test.yml run the same release_pipeline.yml; only its publishing steps differ")


main()
endef
export RELEASE_PIPELINE_IDENTITY_PY

release_pipeline_identity_check:
	$(PYTHON) -c "$$RELEASE_PIPELINE_IDENTITY_PY"

test_boundary_check:
	$(PYTHON) tools/check_test_boundary.py

resource_ownership_check:
	$(PYTHON) tools/check_resource_ownership.py --check
	$(PYTHON) tools/check_resource_ownership.py

semantics_boundary_check:
	$(PYTHON) tools/check_semantics_boundary.py --selfcheck
	$(PYTHON) tools/check_semantics_boundary.py --check

semantics_check:
	$(PYTHON) tools/check_semantics_alignment.py --check

c_kernel_alignment_check:
	$(PYTHON) tools/check_c_kernel_alignment.py --check

deprecation_check:
	$(PYTHON) tools/check_deprecations.py --self-check --check

inspect_structure_parity_check:
	$(PYTHON) tools/check_structure_statistics_parity.py

public_payload_contract_check:
	$(PYTHON) tools/check_public_payload_contract.py

# Shared semantic-fixture corpus contract, including the per-operator coverage
# rule. Kept out of pytest per the test-boundary policy: it validates fixture
# inventory, not production behaviour.
fixture_corpus_check:
	$(PYTHON) tools/inventory_simulate_semantics.py --check

DOCTEST_SCOPE ?= ${SRC_DIR}
DOCTEST_FLAGS ?= ELLIPSIS IGNORE_EXCEPTION_DETAIL DONT_ACCEPT_TRUE_FOR_1

doctest: build_assets
	$(PYTHON) -m pytest "${DOCTEST_SCOPE}" \
		--doctest-modules \
		-p tools.doctest_plugin \
		-o doctest_optionflags="${DOCTEST_FLAGS}" \
		$(DOCTEST_ARGS)

# The examples written in the documentation pages: ``testcode`` / ``testoutput``
# scripts and ``console`` terminal records, run by docs/source/conftest.py. This
# is a different gate from ``doctest`` above, which runs the ``>>>`` examples in
# the docstrings of the package.
DOCS_DOCTEST_SCOPE ?= ${DOC_DIR}/source

docs_doctest: build_assets
	$(PYTHON) -m pytest "${DOCS_DOCTEST_SCOPE}" $(DOCS_DOCTEST_ARGS)

api_doc_toctree_check:
	$(PYTHON) tools/check_api_doc_toctree.py --self-check
	$(PYTHON) tools/check_api_doc_toctree.py --check

bmc_docs_check:
	$(PYTHON) tools/check_bmc_docs.py --check

bmc_benchmark_check:
	$(PYTHON) tools/run_bmc_infeasibility_benchmark.py --check

bmc_benchmark: bmc_benchmark_check
	$(PYTHON) tools/run_bmc_infeasibility_benchmark.py --run \
		--repetitions ${BMC_BENCHMARK_REPETITIONS} --warmups ${BMC_BENCHMARK_WARMUPS}

BMC_CONSTRUCTION_ARGS ?= --bounds 2,3,5,9

bmc_construction_check:
	$(PYTHON) tools/check_bmc_construction.py --check ${BMC_CONSTRUCTION_ARGS}

bmc_solving_benchmark_check:
	$(PYTHON) tools/run_bmc_solving_benchmark.py --check
	$(PYTHON) tools/run_bmc_solving_benchmark.py --self-test

bmc_solving_benchmark: bmc_solving_benchmark_check
	$(PYTHON) tools/run_bmc_solving_benchmark.py --run \
		--repetitions ${BMC_BENCHMARK_REPETITIONS} --warmups ${BMC_BENCHMARK_WARMUPS}


# RST documentation generation targets
rst_auto: ${RST_DOC_FILES} ${RST_NONM_FILES} auto_rst_top_index.py
	python auto_rst_top_index.py -i ${PYTHON_CODE_DIR} -o ${DOC_DIR}/source

sha256: ${SHA256_FILES}

%.sha256: % Makefile
	$(PYTHON) -c "from pathlib import Path; import hashlib; source = Path('$<'); target = Path('$@'); text = source.read_text(encoding='utf-8').replace('\r\n', '\n').replace('\r', '\n'); target.write_text(hashlib.sha256(text.encode('utf-8')).hexdigest() + '  ' + source.name + '\n', encoding='utf-8')"

${RST_DOC_DIR}/%.rst: ${PYTHON_CODE_DIR}/%.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	python auto_rst.py -i $< -o $@

# A package index carries the toctree that auto_rst.py builds by listing the
# package directory, so it goes stale when a module or subpackage appears or is
# edited beside it -- not only when __init__.py itself changes.  The wildcards
# need the stem, which is why they are deferred to the second expansion; without
# them a new module gets its own generated page while the toctree keeps the shape
# it had before, and Sphinx reports the page as included in no toctree.
#
# A *deleted* module is outside what prerequisites can express: a file that no
# longer exists cannot make anything out of date.  That half of the invariant is
# checked instead of built -- make api_doc_toctree_check compares each toctree
# against the directory and reports an entry with no module behind it.
.SECONDEXPANSION:

${RST_DOC_DIR}/%/index.rst: ${PYTHON_CODE_DIR}/%/__init__.py $$(wildcard ${PYTHON_CODE_DIR}/$$*/*.py) $$(wildcard ${PYTHON_CODE_DIR}/$$*/*/__init__.py) auto_rst.py Makefile
	@mkdir -p $(dir $@)
	python auto_rst.py -i $< -o $@

${RST_DOC_DIR}/index.rst: ${PYTHON_CODE_DIR}/__init__.py $(wildcard ${PYTHON_CODE_DIR}/*.py) $(wildcard ${PYTHON_CODE_DIR}/*/__init__.py) auto_rst.py Makefile
	@mkdir -p $(dir $@)
	python auto_rst.py -i $< -o $@

antlr-${ANTLR_VERSION}.jar:
	wget -O $@ https://www.antlr.org/download/antlr-${ANTLR_VERSION}-complete.jar

antlr: antlr-${ANTLR_VERSION}.jar
	$(PYTHON) antlr_req.py -v ${ANTLR_VERSION}
	pip install -r requirements.txt

antlr_build: fcstm_antlr_build fbmcq_antlr_build

# The `ruff format` calls in this target and in the sample-generation targets
# below reformat generated Python that is committed -- the grammars are also
# shipped, the sample tests only run in the matrix, which includes 3.7. Either
# way the output must parse at this project's 3.7 floor, which is what
# ruff.toml's target-version = "py37" keeps it at: without it the formatter can
# emit a parenthesised multi-item `with`, a SyntaxError on 3.7 and 3.8.
fcstm_antlr_build: antlr
	java -jar antlr-${ANTLR_VERSION}.jar -Dlanguage=Python3 -Xexact-output-dir -o ${ANTLR_GRAMMAR_DIR} \
		${ANTLR_LEXER_GRAMMAR_FILE} ${ANTLR_PARSER_GRAMMAR_FILE}
	ruff format ${ANTLR_GRAMMAR_DIR}

fbmcq_antlr_build: antlr
	java -jar antlr-${ANTLR_VERSION}.jar -Dlanguage=Python3 -Xexact-output-dir -o ${BMC_ANTLR_GRAMMAR_DIR} \
		${BMC_ANTLR_LEXER_GRAMMAR_FILE} ${BMC_ANTLR_PARSER_GRAMMAR_FILE}
	ruff format ${BMC_ANTLR_GRAMMAR_DIR}

# Generate sample test files. The `ruff format` calls below are covered by the
# 3.7 floor note above the ANTLR targets.
sample: ${SAMPLE_TEST_FILES} ${SAMPLE_NEG_TEST_FILES}

${MODEL_TEST_DIR}/test_sample_%.py: ${SAMPLE_CODES_DIR}/%.fcstm sample_test_generator.py ${MODEL_SOURCE_FILES}
	@mkdir -p ${MODEL_TEST_DIR}
	UNITTEST=1 $(PYTHON) sample_test_generator.py -i $< -o $@
	ruff format $@

${MODEL_TEST_DIR}/test_sample_%.py: ${SAMPLE_CODES_DIR}/% ${SAMPLE_CODES_DIR}/%/main.fcstm sample_test_generator.py ${MODEL_SOURCE_FILES}
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

# jsfcstm build targets
jsfcstm:
	$(MAKE) -C ${JSFCSTM_DIR} all pack

jsfcstm_clean:
	$(MAKE) -C ${JSFCSTM_DIR} clean

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
