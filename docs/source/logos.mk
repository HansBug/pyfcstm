SOURCE ?= .
PROJ_DIR := $(shell readlink -f ${SOURCE}/../..)
LOGOS_SRC_DIR := ${PROJ_DIR}/logos
LOGOS_DST_DIR := ${SOURCE}/_static/logos

.PHONY: build clean

build:
	@mkdir -p ${LOGOS_DST_DIR}
	@cp ${LOGOS_SRC_DIR}/logo.svg ${LOGOS_DST_DIR}/logo.svg
	@cp ${LOGOS_SRC_DIR}/logo.png ${LOGOS_DST_DIR}/logo.png
	@cp ${LOGOS_SRC_DIR}/logo_banner.svg ${LOGOS_DST_DIR}/logo_banner.svg
	@cp ${LOGOS_SRC_DIR}/logo_banner.png ${LOGOS_DST_DIR}/logo_banner.png
	@echo "Logos copied to ${LOGOS_DST_DIR}"

clean:
	@rm -rf ${LOGOS_DST_DIR}
	@echo "Logos cleaned from ${LOGOS_DST_DIR}"
