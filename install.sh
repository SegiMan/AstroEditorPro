#!/usr/bin/env bash
set -euo pipefail

APP_NAME="AstroEditorPro"
APP_ID="astroeditorpro.desktop"

INSTALL_DIR="${ASTROEDITORPRO_INSTALL_DIR:-$HOME/.local/share/astroeditorpro}"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/astroeditorpro"

DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/$APP_ID"

ICON_BASE="$HOME/.local/share/icons/hicolor"
ICON_APP_DIR="$ICON_BASE/512x512/apps"
ICON_MIME_DIR="$ICON_BASE/512x512/mimetypes"
ICON_APP_FILE="$ICON_APP_DIR/astroeditorpro.png"
ICON_MIME_FILE="$ICON_MIME_DIR/application-x-astroeditorpro.png"

MIME_DIR="$HOME/.local/share/mime"
MIME_PACKAGES_DIR="$MIME_DIR/packages"
MIME_XML="$MIME_PACKAGES_DIR/astroeditorpro-aep.xml"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install_system_dependencies() {
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "apt-get not found; skipping optional system spellcheck setup."
        return 0
    fi
    echo "Installing/checking base system support for spellcheck and desktop integration..."
    sudo apt-get update || echo "WARNING: apt-get update failed; continuing with existing package lists."
    sudo apt-get install -y shared-mime-info desktop-file-utils xdg-utils hunspell || true
    echo
    echo "Language dictionaries can be installed later from inside AstroEditorPro:"
    echo "  Preferences → Spellcheck languages..."
    echo
}


mkdir -p "$BIN_DIR"

is_python314() {
    "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)
PY
}

find_python314() {
    for py in python3.14 "$HOME/.local/bin/python3.14"; do
        if command -v "$py" >/dev/null 2>&1 && is_python314 "$py"; then
            command -v "$py"
            return 0
        fi
    done

    # uv-managed Python locations are not always on PATH.
    if command -v uv >/dev/null 2>&1; then
        local uv_py
        uv_py="$(uv python find 3.14 2>/dev/null || true)"
        if [[ -n "$uv_py" && -x "$uv_py" ]] && is_python314 "$uv_py"; then
            echo "$uv_py"
            return 0
        fi
    fi

    return 1
}

install_python314_with_apt_if_available() {
    if ! command -v apt-cache >/dev/null 2>&1 || ! command -v apt-get >/dev/null 2>&1; then
        return 1
    fi

    echo "Checking whether Python 3.14 is available through apt..."
    sudo apt-get update

    if apt-cache show python3.14 >/dev/null 2>&1; then
        echo "Installing Python 3.14 through apt..."
        sudo apt-get install -y python3.14 python3.14-venv python3.14-dev python3-pip
        return 0
    fi

    echo "python3.14 is not available in the currently configured apt repositories."
    return 1
}

install_uv_if_needed() {
    if command -v uv >/dev/null 2>&1; then
        return 0
    fi

    echo "Installing uv locally because Python 3.14 is not available through apt..."
    echo "This downloads uv from Astral's official installer."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # uv installer usually places uv in ~/.local/bin.
    export PATH="$HOME/.local/bin:$PATH"

    if ! command -v uv >/dev/null 2>&1; then
        echo "ERROR: uv was installed but is not available on PATH."
        echo "Try opening a new terminal, or run:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        exit 1
    fi
}

install_python314_with_uv() {
    install_uv_if_needed
    echo "Installing user-local managed Python 3.14 with uv..."
    uv python install 3.14
}

ensure_python314() {
    local py
    py="$(find_python314 || true)"
    if [[ -n "$py" ]]; then
        echo "$py"
        return 0
    fi

    echo "Python 3.14 not found. Installing it now..."

    if install_python314_with_apt_if_available; then
        py="$(find_python314 || true)"
        if [[ -n "$py" ]]; then
            echo "$py"
            return 0
        fi
        echo "apt reported success, but python3.14 still could not be verified."
    fi

    install_python314_with_uv

    py="$(find_python314 || true)"
    if [[ -n "$py" ]]; then
        echo "$py"
        return 0
    fi

    echo "ERROR: Python 3.14 installation failed or could not be verified."
    exit 1
}

install_system_dependencies

PYTHON314="$(ensure_python314 | tail -n 1)"

if [[ -z "$PYTHON314" || ! -x "$PYTHON314" ]]; then
    echo "ERROR: Python 3.14 path is invalid: $PYTHON314"
    exit 1
fi

if ! is_python314 "$PYTHON314"; then
    echo "ERROR: Selected interpreter is not Python 3.14:"
    "$PYTHON314" --version || true
    exit 1
fi

echo "Verified Python 3.14:"
"$PYTHON314" --version
echo "Python path:"
echo "  $PYTHON314"
echo
echo "Installing AstroEditorPro to:"
echo "  $INSTALL_DIR"

mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/tmp/autosave" "$INSTALL_DIR/tmp/backup" "$INSTALL_DIR/tmp/embedded_images"
mkdir -p "$DESKTOP_DIR" "$ICON_APP_DIR" "$ICON_MIME_DIR" "$MIME_PACKAGES_DIR"

cp "$REPO_DIR/astroeditorpro/AstroEditorPro.py" "$INSTALL_DIR/AstroEditorPro.py"
cp "$REPO_DIR/astroeditorpro/shortcuts.conf" "$INSTALL_DIR/shortcuts.conf"

if [[ -f "$REPO_DIR/assets/AstroEditorIcon.png" ]]; then
    cp "$REPO_DIR/assets/AstroEditorIcon.png" "$INSTALL_DIR/AstroEditorIcon.png"
    cp "$REPO_DIR/assets/AstroEditorIcon.png" "$ICON_APP_FILE"
    cp "$REPO_DIR/assets/AstroEditorIcon.png" "$ICON_MIME_FILE"
else
    echo "WARNING: assets/AstroEditorIcon.png not found. App will install with generic icon."
fi

# Recreate venv unless it is already Python 3.14.
if [[ -x "$INSTALL_DIR/.venv/bin/python" ]]; then
    if ! is_python314 "$INSTALL_DIR/.venv/bin/python"; then
        echo "Existing venv is not Python 3.14. Removing it."
        rm -rf "$INSTALL_DIR/.venv"
    fi
fi

echo "Creating/verifying virtual environment..."
if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
    if command -v uv >/dev/null 2>&1; then
        uv venv --python "$PYTHON314" "$INSTALL_DIR/.venv"
    else
        "$PYTHON314" -m venv "$INSTALL_DIR/.venv"
    fi
fi

if ! is_python314 "$INSTALL_DIR/.venv/bin/python"; then
    echo "ERROR: Created venv is not Python 3.14."
    "$INSTALL_DIR/.venv/bin/python" --version || true
    exit 1
fi

echo "Verified venv Python:"
"$INSTALL_DIR/.venv/bin/python" --version

# Install Python package dependencies.
#
# uv-managed Python/venv can be created without pip inside the environment.
# In that case, use `uv pip` to install into the venv directly.
if "$INSTALL_DIR/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
    "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
    "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$REPO_DIR/requirements.txt"
else
    echo "pip is not available inside the venv; using uv pip instead."
    if ! command -v uv >/dev/null 2>&1; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if ! command -v uv >/dev/null 2>&1; then
        echo "ERROR: pip is missing and uv is not available."
        exit 1
    fi
    uv pip install --python "$INSTALL_DIR/.venv/bin/python" pip setuptools wheel
    uv pip install --python "$INSTALL_DIR/.venv/bin/python" -r "$REPO_DIR/requirements.txt"
fi

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
export ASTROEDITORPRO_HOME="$INSTALL_DIR"
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/AstroEditorPro.py" "\$@"
EOF
chmod +x "$WRAPPER"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AstroEditorPro
GenericName=Text Editor
Comment=Tabbed rich text editor with notes, highlights, images, spellcheck, workspaces and autosave
Exec=$WRAPPER %F
Icon=astroeditorpro
Terminal=false
Categories=Utility;TextEditor;Office;Development;
MimeType=application/x-astroeditorpro;text/plain;text/x-python;text/x-c;text/x-c++;text/x-java;text/x-shellscript;text/markdown;text/html;text/css;text/csv;application/json;application/xml;application/x-yaml;
StartupNotify=true
StartupWMClass=astroeditorpro
DBusActivatable=false
EOF
chmod +x "$DESKTOP_FILE"

cat > "$MIME_XML" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-astroeditorpro">
    <comment>AstroEditorPro self-contained document</comment>
    <glob pattern="*.aep"/>
    <glob pattern="*.AEP"/>
  </mime-type>
</mime-info>
EOF

command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$MIME_DIR" || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" || true

if [[ -f "$INSTALL_DIR/AstroEditorIcon.png" ]] && command -v xdg-icon-resource >/dev/null 2>&1; then
    xdg-icon-resource install --context apps --size 512 "$INSTALL_DIR/AstroEditorIcon.png" astroeditorpro || true
    xdg-icon-resource install --context mimetypes --size 512 "$INSTALL_DIR/AstroEditorIcon.png" application-x-astroeditorpro || true
fi

xdg-mime default "$APP_ID" application/x-astroeditorpro || true
xdg-mime default "$APP_ID" text/plain || true
xdg-mime default "$APP_ID" text/x-python || true
xdg-mime default "$APP_ID" text/markdown || true
xdg-mime default "$APP_ID" text/html || true
xdg-mime default "$APP_ID" text/css || true
xdg-mime default "$APP_ID" text/csv || true
xdg-mime default "$APP_ID" application/json || true
xdg-mime default "$APP_ID" application/xml || true
xdg-mime default "$APP_ID" application/x-yaml || true

if command -v gsettings >/dev/null 2>&1; then
python3 - <<'PY'
import ast, subprocess
app_id = "astroeditorpro.desktop"
try:
    raw = subprocess.check_output(["gsettings", "get", "org.gnome.shell", "favorite-apps"], text=True).strip()
    apps = ast.literal_eval(raw)
    if app_id not in apps:
        apps.append(app_id)
        value = "[" + ", ".join(repr(x) for x in apps) + "]"
        subprocess.run(["gsettings", "set", "org.gnome.shell", "favorite-apps", value], check=False)
except Exception as exc:
    print(f"Could not update GNOME favorites: {exc}")
PY
fi

echo
echo "AstroEditorPro installed successfully with Python 3.14."
echo
echo "Run from terminal:"
echo "  astroeditorpro"
echo
echo "Verify:"
echo "  ~/.local/share/astroeditorpro/.venv/bin/python --version"
echo "  grep -E 'Name=|Exec=|Icon=|StartupWMClass=' ~/.local/share/applications/astroeditorpro.desktop"
echo
echo "If icons do not refresh immediately:"
echo "  nautilus -q"
echo "or log out and back in."
