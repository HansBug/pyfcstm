.PHONY: all help install build test coverage pack clean

NPM := npm

help:
	@echo "jsfcstm Build Commands"
	@echo "====================="
	@echo ""
	@echo "  make install  - Install npm dependencies"
	@echo "  make build    - Generate parser artifacts under src/dsl/grammar/ and build dist/"
	@echo "  make test     - Run package unit tests with coverage reporting"
	@echo "  make coverage - Alias of make test"
	@echo "  make pack     - Build and create both npm tarball outputs and jsfcstm.tgz for local repo consumers"
	@echo "  make clean    - Remove generated files"
	@echo "  make all      - Install, build, and test"

all: install build test

install:
	@echo "Installing jsfcstm dependencies..."
	$(NPM) install

build:
	@echo "Building jsfcstm..."
	$(NPM) run build

test:
	@echo "Running jsfcstm unit tests with coverage..."
	$(NPM) test

coverage: test

pack: build
	@echo "Packing jsfcstm..."
	$(NPM) run pack:local

clean:
	@echo "Cleaning jsfcstm..."
	rm -rf dist
	rm -rf src/dsl/grammar
	rm -rf parser
	rm -rf coverage
	rm -rf node_modules
	rm -f ./*.tgz
	rm -f ./jsfcstm.tgz
	rm -f tsconfig.tsbuildinfo
