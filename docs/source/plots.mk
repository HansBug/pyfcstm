PYTHON := $(shell which python)

SOURCE ?= .

# Every ``X.plot.py`` draws the figure ``X.plot.py.svg`` that a page includes.
PYTHON_PLOTS        := $(shell find ${SOURCE} -name *.plot.py)
PYTHON_PLOT_RESULTS := $(addsuffix .py.svg, $(basename ${PYTHON_PLOTS}))

%.plot.py.svg: %.plot.py
	cd "$(shell dirname $(shell readlink -f $<))" && \
		PYTHONPATH="$(shell dirname $(shell readlink -f $<)):${PYTHONPATH}" \
		$(PYTHON) "$(shell readlink -f $<)" -o "$(shell readlink -f $@)"

build: ${PYTHON_PLOT_RESULTS}

all: build

clean:
	rm -rf $(shell find ${SOURCE} -name *.plot.py.svg)
