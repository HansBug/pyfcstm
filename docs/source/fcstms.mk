PLANTUMLCLI ?= $(shell which plantumlcli)
PYFCSTM     ?= $(shell which pyfcstm)

SOURCE ?= .
FCSTMS := $(shell find ${SOURCE} -name *.fcstm)
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
