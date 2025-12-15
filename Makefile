.PHONY: docs test unittest resource antlr antlr_build build package clean

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

RANGE_DIR      ?= .
RANGE_TEST_DIR := ${TEST_DIR}/${RANGE_DIR}
RANGE_SRC_DIR  := ${SRC_DIR}/${RANGE_DIR}

COV_TYPES ?= xml term-missing

ANTLR_VERSION ?= 4.9.3
ANTLR_GRAMMAR_DIR  := ${SRC_DIR}/dsl/grammar
ANTLR_GRAMMAR_FILE := ${ANTLR_GRAMMAR_DIR}/Grammar.g4

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

package:
	$(PYTHON) -m build --sdist --wheel --outdir ${DIST_DIR}
build:
	pyinstaller -D -F $(shell python -m tools.resources) -n pyfcstm -c pyfcstm_cli.py
clean:
	rm -rf ${DIST_DIR} ${BUILD_DIR} *.egg-info
	rm -rf build dist pyfcstm.spec

test: unittest

unittest:
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
pdocs:
	$(MAKE) -C "${DOC_DIR}" prod

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
