# You can set these variables from the command line, and also
# from the environment for the first two.
PROJ_DIR           ?= ${CURDIR}
SPHINXOPTS         ?=
SPHINXBUILD        ?= $(shell which sphinx-build)
SPHINXMULTIVERSION ?= $(shell which sphinx-multiversion)
PYTHON             ?= $(shell which python)
SOURCEDIR          ?= ${PROJ_DIR}/source
BUILDDIR           ?= ${PROJ_DIR}/build
PDFBUILDDIR        ?= ${BUILDDIR}/pdf
PDFCHECKER         ?= $(abspath ${PROJ_DIR}/../tools/check_docs_pdf.py)

# Minimal makefile for Sphinx documentation
ALL_MK := ${SOURCEDIR}/all.mk
ALL    := $(MAKE) -f "${ALL_MK}" SOURCE=${SOURCEDIR}

BMS    := $(shell find ${SOURCEDIR} -name 'benchmark_*.dat.*')

.EXPORT_ALL_VARIABLES:

NO_CONTENTS_BUILD = true

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
# Put it first so that "make" without argument is like "make help".
.PHONY: help contents _acceptance_contents build html pdf pdf_en pdf_zh _pdf_en _pdf_zh _acceptance_pdf prod clean sourcedir builddir Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

contents:
	@$(ALL) build
_acceptance_contents:
	@$(MAKE) -f "$(SOURCEDIR)/fcstms.mk" SOURCE="$(SOURCEDIR)/acceptance" build
	@$(MAKE) -f "$(SOURCEDIR)/demos.mk" SOURCE="$(SOURCEDIR)/acceptance" build
	@$(MAKE) -f "$(SOURCEDIR)/graphviz.mk" SOURCE="$(SOURCEDIR)/acceptance" build
build: html
html: contents
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@touch "$(BUILDDIR)/html/.nojekyll"
pdf: _acceptance_contents
	@$(MAKE) _pdf_zh
pdf_en: contents
	@$(MAKE) _pdf_en
pdf_zh: _acceptance_contents
	@$(MAKE) _pdf_zh
_pdf_en:
	@rm -rf "$(PDFBUILDDIR)/en"
	@mkdir -p "$(PDFBUILDDIR)/en"
	@start="$$(date +%s)"; \
		log="$(PDFBUILDDIR)/en/build.log"; \
		if ! NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=en $(SPHINXBUILD) -M latexpdf "$(SOURCEDIR)" "$(PDFBUILDDIR)/en" $(SPHINXOPTS) $(O) > "$$log" 2>&1; then \
			cat "$$log"; \
			exit 1; \
		fi; \
		cat "$$log"; \
		duration="$$(($$(date +%s) - $$start))"; \
		printf '%s\n' "$$duration" > "$(PDFBUILDDIR)/en/duration-seconds.txt"; \
		printf 'English PDF build duration: %s seconds\n' "$$duration"
	@$(PYTHON) "$(PDFCHECKER)" --language en --build-root "$(PDFBUILDDIR)/en"
_acceptance_pdf:
	@rm -rf "$(PDFBUILDDIR)/zh"
	@mkdir -p "$(PDFBUILDDIR)/zh"
	@start="$$(date +%s)"; \
		log="$(PDFBUILDDIR)/zh/build.log"; \
		if ! NO_CONTENTS_BUILD=1 PYFCSTM_ACCEPTANCE_PDF=1 READTHEDOCS_LANGUAGE=zh $(SPHINXBUILD) -M latexpdf "$(SOURCEDIR)" "$(PDFBUILDDIR)/zh" $(SPHINXOPTS) $(O) > "$$log" 2>&1; then \
			cat "$$log"; \
			exit 1; \
		fi; \
		cat "$$log"; \
		duration="$$(($$(date +%s) - $$start))"; \
		printf '%s\n' "$$duration" > "$(PDFBUILDDIR)/zh/duration-seconds.txt"; \
		printf 'Acceptance Chinese PDF build duration: %s seconds\n' "$$duration"
	@$(PYTHON) "$(PDFCHECKER)" --language zh --build-root "$(PDFBUILDDIR)/zh"
_pdf_zh:
	@$(MAKE) _acceptance_pdf
prod:
	@NO_CONTENTS_BUILD='' $(SPHINXMULTIVERSION) "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)
	@cp main_page.html "$(BUILDDIR)/html/index.html"
	@touch "$(BUILDDIR)/html/.nojekyll"

doc_clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	@$(ALL) clean
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

sourcedir:
	@echo $(shell readlink -f ${SOURCEDIR})
builddir:
	@echo $(shell readlink -f ${BUILDDIR}/html)

cleanplt:
	$(ALL) cleanplt
