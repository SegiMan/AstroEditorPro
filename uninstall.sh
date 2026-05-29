#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${ASTROEDITORPRO_INSTALL_DIR:-$HOME/.local/share/astroeditorpro}"
APP_ID="astroeditorpro.desktop"

rm -f "$HOME/.local/bin/astroeditorpro"
rm -f "$HOME/.local/share/applications/$APP_ID"
rm -f "$HOME/.local/share/icons/hicolor/512x512/apps/astroeditorpro.png"
rm -f "$HOME/.local/share/icons/hicolor/512x512/mimetypes/application-x-astroeditorpro.png"
rm -f "$HOME/.local/share/mime/packages/astroeditorpro-aep.xml"

command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$HOME/.local/share/mime" || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true

if command -v xdg-icon-resource >/dev/null 2>&1; then
    xdg-icon-resource uninstall --context apps --size 512 astroeditorpro || true
    xdg-icon-resource uninstall --context mimetypes --size 512 application-x-astroeditorpro || true
fi

if command -v gsettings >/dev/null 2>&1; then
python3 - <<'PY'
import ast, subprocess
app_id = "astroeditorpro.desktop"
try:
    raw = subprocess.check_output(["gsettings", "get", "org.gnome.shell", "favorite-apps"], text=True).strip()
    apps = ast.literal_eval(raw)
    if app_id in apps:
        apps = [x for x in apps if x != app_id]
        value = "[" + ", ".join(repr(x) for x in apps) + "]"
        subprocess.run(["gsettings", "set", "org.gnome.shell", "favorite-apps", value], check=False)
except Exception as exc:
    print(f"Could not update GNOME favorites: {exc}")
PY
fi

echo "Desktop integration removed."
read -r -p "Remove installed app data at $INSTALL_DIR too? [y/N] " answer
case "$answer" in
    [yY][eE][sS]|[yY])
        rm -rf "$INSTALL_DIR"
        echo "Removed $INSTALL_DIR"
        ;;
    *)
        echo "Kept $INSTALL_DIR"
        ;;
esac
