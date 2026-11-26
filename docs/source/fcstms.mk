PLANTUMLCLI ?= $(shell which plantumlcli)
PYFCSTM     ?= $(shell which pyfcstm)

SOURCE ?= .
# A model is drawn only when some page names its picture, such as
# ``controller.fcstm.puml.svg``. A model that is only the input of a command in a
# page needs no picture, so none is generated or committed for it.
FCSTMS := $(shell find ${SOURCE} -name '*.fcstm' | while read model; do \
	grep -rqF "$$(basename "$$model").puml." ${SOURCE} --include='*.rst' --include='*.inc' && echo "$$model"; \
	done)
PUMLS  := $(addsuffix .fcstm.puml, $(basename ${FCSTMS}))
PNGS   := $(addsuffix .puml.png, $(basename ${PUMLS}))
SVGS   := $(addsuffix .puml.svg, $(basename ${PUMLS}))

# Pattern-specific rules for different detail levels
%.full.fcstm.puml: %.full.fcstm
	$(PYFCSTM) plantuml -i "$(shell readlink -f $<)" -o "$(shell readlink -f $@)" --level full

%.minimal.fcstm.puml: %.minimal.fcstm
	$(PYFCSTM) plantuml -i "$(shell readlink -f $<)" -o "$(shell readlink -f $@)" --level minimal

# Default rule for normal detail level
%.fcstm.puml: %.fcstm
	$(PYFCSTM) plantuml -i "$(shell readlink -f $<)" -o "$(shell readlink -f $@)" --level normal

%.fcstm.puml.png: %.fcstm.puml
	$(PLANTUMLCLI) -t png -o "$(shell readlink -f $@)" "$(shell readlink -f $<)"

%.fcstm.puml.svg: %.fcstm.puml
	$(PLANTUMLCLI) -t svg -o "$(shell readlink -f $@)" "$(shell readlink -f $<)"

build: ${PUMLS} ${SVGS} ${PNGS}

all: build

clean:
	rm -rf \
		$(shell find ${SOURCE} -name *.fcstm.puml) \
		$(shell find ${SOURCE} -name *.fcstm.puml.svg) \
		$(shell find ${SOURCE} -name *.fcstm.puml.png) \
