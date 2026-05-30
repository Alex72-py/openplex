#!/data/data/com.termux/files/usr/bin/bash
# OpenPlex installer for Termux
# Also works on regular Linux

set -e

echo ""
echo "  ◆ OpenPlex Installer ◆"
echo "  AI Search Engine for Termux"
echo ""

# Detect environment
if [ -d "/data/data/com.termux" ]; then
    ENV="termux"
    PREFIX="/data/data/com.termux/files/usr"
    INSTALL_DIR="$HOME/openplex"
    BIN_DIR="$PREFIX/bin"
    PIP="pip"
    PYTHON="python"
else
    ENV="linux"
    PREFIX="/usr/local"
    INSTALL_DIR="$HOME/openplex"
    BIN_DIR="$HOME/.local/bin"
    PIP="pip3"
    PYTHON="python3"
    mkdir -p "$BIN_DIR"
fi

echo "  Environment: $ENV"
echo "  Install dir: $INSTALL_DIR"
echo ""

# Check Python
if ! command -v $PYTHON &> /dev/null; then
    echo "  ✗ Python not found!"
    if [ "$ENV" = "termux" ]; then
        echo "  Run: pkg install python"
    else
        echo "  Run: sudo apt install python3"
    fi
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2)
echo "  ✓ Python $PYTHON_VERSION"

# Install rich (only required dependency)
echo "  Installing dependencies..."
$PIP install rich --quiet 2>/dev/null || $PIP install rich --user --quiet 2>/dev/null || {
    echo "  ! Could not install 'rich'. OpenPlex will work without it (plain text mode)."
}

# Copy files
if [ -d "$INSTALL_DIR" ]; then
    echo "  Updating existing installation..."
    rm -rf "$INSTALL_DIR/src"
fi

# If running from the repo directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/openplex.py" "$INSTALL_DIR/"
fi

# Create launcher script
cat > "$BIN_DIR/openplex" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
$PYTHON openplex.py "\$@"
EOF

chmod +x "$BIN_DIR/openplex"
chmod +x "$INSTALL_DIR/openplex.py"

echo ""
echo "  ✓ OpenPlex installed successfully!"
echo ""
echo "  Usage:"
echo "    openplex          — Start OpenPlex"
echo ""
echo "  First run will ask for your NVIDIA NIM API key."
echo "  Get one free at: https://build.nvidia.com"
echo ""

# Check if BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "  Note: Add $BIN_DIR to your PATH:"
    echo "    echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc"
    echo ""
fi
