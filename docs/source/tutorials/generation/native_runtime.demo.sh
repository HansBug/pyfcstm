#!/bin/bash
set -e
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

model="simple_machine.fcstm"
cc_bin=${CC:-cc}
cxx_bin=${CXX:-c++}

echo "=== Toolchain snapshot ==="
printf 'os: '
uname -srm
if command -v "$cc_bin" >/dev/null 2>&1; then
    printf 'cc: '
    "$cc_bin" --version | head -1
else
    echo "cc: unavailable"
fi
if command -v "$cxx_bin" >/dev/null 2>&1; then
    printf 'c++: '
    "$cxx_bin" --version | head -1
else
    echo "c++: unavailable"
fi
if command -v cmake >/dev/null 2>&1; then
    printf 'cmake: '
    cmake --version | head -1
else
    echo "cmake: unavailable"
fi

run_c_demo() {
    template=$1
    driver=$2
    output="$workdir/$template"
    exe="$output/demo"
    echo ""
    echo "=== $template ==="
    pyfcstm generate -i "$model" --template "$template" -o "$output" --clear >/dev/null
    for path in "$output"/*; do
        echo "file: $(basename "$path")"
    done | sort
    cp "$driver" "$output/app.c"
    if ! command -v "$cc_bin" >/dev/null 2>&1; then
        echo "compile: skipped because cc is unavailable"
        return 0
    fi
    (
        cd "$output"
        "$cc_bin" -std=c99 -Wall -Wextra -pedantic -O2 machine.c app.c -lm -o "$exe"
        "$exe"
    )
}

run_cpp_demo() {
    template=$1
    driver=$2
    output="$workdir/$template"
    exe="$output/demo"
    echo ""
    echo "=== $template ==="
    pyfcstm generate -i "$model" --template "$template" -o "$output" --clear >/dev/null
    for path in "$output"/*; do
        echo "file: $(basename "$path")"
    done | sort
    cp "$driver" "$output/app.cpp"
    if ! command -v "$cc_bin" >/dev/null 2>&1 || ! command -v "$cxx_bin" >/dev/null 2>&1; then
        echo "compile: skipped because cc or c++ is unavailable"
        return 0
    fi
    (
        cd "$output"
        "$cc_bin" -std=c99 -Wall -Wextra -pedantic -O2 -c machine.c -o machine_c.o
        "$cxx_bin" -std=c++98 -Wall -Wextra -pedantic -O2 -c machine.cpp -o machine_cpp.o
        "$cxx_bin" -std=c++98 -Wall -Wextra -pedantic -O2 -c app.cpp -o app.o
        "$cxx_bin" machine_c.o machine_cpp.o app.o -lm -o "$exe"
        "$exe"
    )
}

run_c_demo c c_driver.c
run_c_demo c_poll c_poll_driver.c
run_cpp_demo cpp cpp_driver.cpp
run_cpp_demo cpp_poll cpp_poll_driver.cpp
