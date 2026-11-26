#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

pyfcstm plantuml -i controller.fcstm
