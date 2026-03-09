#!/bin/bash
# Wrapper script to test CLI with python -m pyfcstm

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR"

# Create a temporary wrapper script
WRAPPER=$(mktemp)
cat > "$WRAPPER" << 'EOF'
#!/bin/bash
exec python -m pyfcstm "$@"
EOF
chmod +x "$WRAPPER"

# Run the test with the wrapper
python tools/test_cli.py "$WRAPPER" --test-dsl test/testfile/sample_codes/dlc6_simplest.fcstm

# Clean up
rm -f "$WRAPPER"
