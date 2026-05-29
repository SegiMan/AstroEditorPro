# AstroEditorPro

AstroEditorPro is a Python/PySide6 rich-text editor for Linux. It combines ordinary text editing with features usually found across several different tools: tabs, autosave, rich formatting, annotations, sticky notes, bookmarks, images, spellcheck, workspaces, editable split view, and a self-contained `.aep` document format.

It is designed to be useful both as a general-purpose editor and as a more advanced note/review/writing tool.

---

## Features

### General editing

- Multiple tabs
- Session restore
- Autosave after inactivity
- Undo/redo using save/autosave snapshots
- Recently opened files
- Configurable shortcuts
- Configurable font, font size, colours, wrapping, line numbers
- Optional line-number column
- Text zoom with `Ctrl + mouse wheel`
- Indent/outdent selected lines with `Tab` and `Shift+Tab`

### Rich text

- Bold, italic, underline
- Per-selection font family
- Per-selection text size
- Per-selection text colour
- Pasted images
- Basic image editing:
  - rotate
  - crop
  - resize
  - scale by percentage
  - keep aspect ratio

### Annotations

- Highlight text without changing the text itself
- Choose highlight colour
- Sidebar listing all highlighted text
- Copy all highlighted text
- Sticky notes attached to text
- Note popup on hover
- Sidebar listing notes
- Right-click note/highlight removal

### Bookmarks and outline

- Right-click a line to add a bookmark
- Bookmarks are named alphabetically: `A`, `B`, `C`, ...
- Jump to bookmarks with editable shortcuts, defaulting to `Alt+A`, `Alt+B`, etc.
- Bookmark list sidebar
- Bookmark line highlighting in the line-number column
- Document outline sidebar for simple heading structures such as:
  - `# Heading`
  - `## Subheading`
  - `1. Section`
  - `=== Heading ===`

### Workspaces

- Open a folder as a workspace
- Browse files from a sidebar
- Open files directly from the workspace tree
- Remove files/folders from the workspace view through the context menu

### Split view

- Editable split view
- Edits on either side synchronize to the other side
- The editor tries to preserve scroll/cursor position after synchronization

### Spellcheck

- Hunspell-based spellcheck through `spylls`
- User-selectable spellcheck languages
- Multiple dictionaries can be enabled at the same time
- Missing dictionaries can be installed from inside the app
- Custom user dictionary
- Add words to the custom dictionary from the right-click spellcheck menu

### Tools and export

Tools include:

- Clean text tools
- Align selected table columns
- Insert image from clipboard
- Spellcheck language manager

Export options include:

- Plain text
- HTML
- AstroEditorPro rich document
- Highlighted text only
- Sticky notes only
- Highlights + notes report

---

## Self-contained `.aep` files

AstroEditorPro uses `.aep` as its main rich document format.

A `.aep` file stores everything in one file:

- rich HTML text
- plain text fallback
- highlights
- sticky notes
- bookmarks
- embedded images

This means you can move a `.aep` file to another folder or another computer without losing notes, highlights, or images.

Plain `.txt` and `.html` files are still supported, but they cannot preserve all AstroEditorPro metadata.

Use `.aep` whenever you want to preserve the full document state.

---

## Installation

The recommended installation method is the included installer script.

Clone the repository:

```bash
git clone https://github.com/SegiMan/AstroEditorPro.git
cd AstroEditorPro
```

Run the installer:

```bash
bash install.sh
```

The installer will:

1. Check for Python 3.14.
2. Install Python 3.14 if it is missing.
3. Create a virtual environment.
4. Install Python dependencies.
5. Install the app into your user directory.
6. Create a desktop launcher.
7. Register `.aep` files.
8. Install the app icon and `.aep` file icon.
9. Add AstroEditorPro to the app list/dock where possible.

After installation, launch AstroEditorPro from your app list or run:

```bash
astroeditorpro
```

---

## Installation location

AstroEditorPro is installed per-user, without modifying system application folders.

Default install location:

```text
~/.local/share/astroeditorpro
```

The installer also creates:

```text
~/.local/bin/astroeditorpro
~/.local/share/applications/astroeditorpro.desktop
~/.local/share/mime/packages/astroeditorpro-aep.xml
~/.local/share/icons/hicolor/512x512/apps/astroeditorpro.png
~/.local/share/icons/hicolor/512x512/mimetypes/application-x-astroeditorpro.png
```

---

## Dependencies

The installer handles Python dependencies automatically.

Python packages:

```text
PySide6
spylls
```

System tools used by the installer:

```text
shared-mime-info
desktop-file-utils
xdg-utils
hunspell
```

Spellcheck dictionaries are installed separately as needed from inside AstroEditorPro.

---

## Python 3.14

AstroEditorPro’s installer is designed to use Python 3.14.

If Python 3.14 is not available through your package manager, the installer can install a user-local Python 3.14 using `uv`.

The virtual environment used by AstroEditorPro is created only after Python 3.14 is verified.

---

## Spellcheck dictionaries

Open:

```text
Preferences → Spellcheck languages...
```

or:

```text
Tools → Spellcheck languages...
```

From there you can:

- select any number of installed dictionaries
- see which dictionaries are missing
- install missing dictionaries
- open the custom dictionary
- reload the custom dictionary

The custom dictionary is stored at:

```text
~/.local/share/astroeditorpro/user_dictionary.txt
```

Words added from the spellcheck context menu are saved there.

---

## Updating

To update from the GitHub repository:

```bash
cd AstroEditorPro
git pull
bash install.sh
```

The installer will update the installed application while preserving user data such as preferences, autosaves, and the custom dictionary.

---

## Uninstalling

Run:

```bash
bash uninstall.sh
```

The uninstaller removes desktop integration and asks whether to remove installed app data as well.

---

## Running from source for development

Create a development virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run with a local development data folder:

```bash
ASTROEDITORPRO_HOME="$PWD/dev_home" .venv/bin/python astroeditorpro/AstroEditorPro.py
```

---

## Keyboard shortcuts

Shortcuts are stored in:

```text
~/.local/share/astroeditorpro/shortcuts.conf
```

The default shortcut file is installed from:

```text
astroeditorpro/shortcuts.conf
```

Common defaults:

```text
Ctrl+B          bold
Ctrl+I          italic
Ctrl+U          underline
Ctrl+S          save
Ctrl+Shift+S    save as separate copy and close original
Ctrl+O          open file
Ctrl+T          new tab
Ctrl+W          close tab
Ctrl+Z          undo
Ctrl+Shift+Z    redo
Ctrl+F          find
Ctrl+H          find and replace
Ctrl+Alt+V      toggle split view
Ctrl+Alt+O      open workspace
Ctrl+Alt+E      export document
Ctrl+Alt+I      insert image from clipboard
Alt+A ... Alt+Z jump to bookmarks
```

Edit `shortcuts.conf` to customize shortcuts.

---

## Multi-selection

AstroEditorPro includes an emulated multi-selection system.

Use:

```text
Ctrl + drag/select
```

to add multiple separate selections.

Use:

```text
Ctrl + Shift + drag
```

for approximate column-style selection.

Formatting can be applied to all stored selections.

Stored multi-selections are cleared by:

```text
Esc
Left arrow
Right arrow
normal mouse click without Ctrl
```

Because this is implemented on top of `QTextEdit`, it may not behave exactly like native multi-cursor editing in a dedicated code editor.

---

## Opening files with AstroEditorPro

After installation, `.aep` files should open with AstroEditorPro.

Common text-like files are also registered for “Open With” support, including:

```text
.txt
.py
.md
.html
.css
.csv
.json
.xml
.yaml
```

If icons or file associations do not appear immediately, restart the file manager:

```bash
nautilus -q
```

or log out and back in.

---

## Troubleshooting

### The app shows a generic gear/python icon

Check the desktop entry:

```bash
grep -E "Name=|Exec=|Icon=|StartupWMClass=" ~/.local/share/applications/astroeditorpro.desktop
```

Expected:

```text
Name=AstroEditorPro
Icon=astroeditorpro
StartupWMClass=astroeditorpro
```

If an old gear icon is pinned, unpin it, launch AstroEditorPro from the app list, and pin the correct icon.

### `.aep` files do not have the correct icon

Check MIME detection:

```bash
xdg-mime query filetype example.aep
```

Expected:

```text
application/x-astroeditorpro
```

Then restart the file manager:

```bash
nautilus -q
```

### Spellcheck does not work

Open:

```text
Preferences → Spellcheck languages...
```

Make sure at least one dictionary is selected and installed.

The app expects Hunspell dictionaries in:

```text
/usr/share/hunspell
```

The custom dictionary is:

```text
~/.local/share/astroeditorpro/user_dictionary.txt
```

### Installer selected the wrong Python

The installer is intended to force Python 3.14. Verify:

```bash
~/.local/share/astroeditorpro/.venv/bin/python --version
```

Expected:

```text
Python 3.14.x
```

---

## Repository structure

```text
AstroEditorPro/
├── astroeditorpro/
│   ├── AstroEditorPro.py
│   └── shortcuts.conf
├── assets/
│   └── AstroEditorIcon.png
├── install.sh
├── uninstall.sh
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
└── snapcraft.yaml
```

---

## Snap package

A preliminary `snapcraft.yaml` is included, but the installer script is currently the recommended way to install AstroEditorPro.

Snap packaging for a PySide6 editor requires additional testing because of Qt libraries, Wayland/X11 integration, file access, Hunspell dictionaries, MIME registration, and desktop integration.

---

## License

This project is distributed under the license included in the repository.
