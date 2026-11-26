#!/bin/sh
set -eu
cd "$(dirname "$0")"

pyfcstm plantuml -i controller.fcstm
