#!/bin/sh
cd "$(dirname "$0")"

# The command line prints a Python traceback for this error; keep the lines that
# do not depend on where the checkout lives.
echo "\$ pyfcstm bmc -i spin.fcstm -q spin.fbmcq"
out="$(pyfcstm bmc -i spin.fcstm -q spin.fbmcq 2>&1; echo "exit=$?")"
printf '%s\n' "$out" | grep -E '^(Unexpected error|_BmcCliInternalError|exit=)'
