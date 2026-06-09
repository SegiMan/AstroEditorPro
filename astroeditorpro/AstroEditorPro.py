import os
from pathlib import Path

APP_HOME = Path(os.environ.get("ASTROEDITORPRO_HOME", str(Path.home() / ".local/share/astroeditorpro"))).expanduser()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AstroEditor Qt

A tabbed rich-text editor using PySide6/Qt.

Install dependency once:
    python3 -m pip install PySide6

Run:
    python3 astro_editor_qt.py

In PyCharm:
    - Open this file
    - Make sure the interpreter has PySide6 installed
    - Run the file directly
"""

# ============================================================
# USER-EDITABLE PATHS
# ============================================================
TEMP_DATA_DIR = str(APP_HOME / "tmp")
FONTS_DIR = "/usr/share/fonts"
SHORTCUTS_FILE = str(APP_HOME / "shortcuts.conf")

# Spellcheck uses system Hunspell dictionaries, usually installed in /usr/share/hunspell.
# Required files for the default setup:
#   /usr/share/hunspell/en_GB.dic + en_GB.aff
#   /usr/share/hunspell/hr_HR.dic + hr_HR.aff
SPELLCHECK_DICTIONARY_DIR = "/usr/share/hunspell"
SPELLCHECK_LANGUAGES = ["en_GB", "hr_HR"]
SPELLCHECK_USER_DICTIONARY = str(APP_HOME / "user_dictionary.txt")

# Common Hunspell packages on Debian/Ubuntu. Installed dictionaries are also
# discovered dynamically from SPELLCHECK_DICTIONARY_DIR, so this list is only
# used for friendly names and install buttons.
COMMON_HUNSPELL_LANGUAGES = {
    "en_GB": ("English (UK)", "hunspell-en-gb"),
    "en_US": ("English (US)", "hunspell-en-us"),
    "hr_HR": ("Croatian", "hunspell-hr"),
    "de_DE": ("German", "hunspell-de-de"),
    "fr_FR": ("French", "hunspell-fr"),
    "es_ES": ("Spanish", "hunspell-es"),
    "it_IT": ("Italian", "hunspell-it"),
    "pt_PT": ("Portuguese (Portugal)", "hunspell-pt-pt"),
    "pt_BR": ("Portuguese (Brazil)", "hunspell-pt-br"),
    "nl_NL": ("Dutch", "hunspell-nl"),
    "pl_PL": ("Polish", "hunspell-pl"),
    "cs_CZ": ("Czech", "hunspell-cs"),
    "sk_SK": ("Slovak", "hunspell-sk"),
    "sl_SI": ("Slovenian", "hunspell-sl"),
    "sr": ("Serbian", "hunspell-sr"),
    "ru_RU": ("Russian", "hunspell-ru"),
    "uk_UA": ("Ukrainian", "hunspell-uk"),
    "hu_HU": ("Hungarian", "hunspell-hu"),
    "ro_RO": ("Romanian", "hunspell-ro"),
    "el_GR": ("Greek", "hunspell-el"),
    "tr_TR": ("Turkish", "hunspell-tr"),
    "sv_SE": ("Swedish", "hunspell-sv"),
    "da_DK": ("Danish", "hunspell-da"),
    "fi_FI": ("Finnish", "hunspell-fi"),
    "nb_NO": ("Norwegian Bokmål", "hunspell-no"),
    "nn_NO": ("Norwegian Nynorsk", "hunspell-no"),
}

# ============================================================

import json
import base64
import os
import mimetypes
import re
import sys
import time
import subprocess
import shutil
import fcntl
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QEvent, QPoint, QRect, QSaveFile, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
    QPen,
    QTextCharFormat,
    QTextCursor,
    QTextImageFormat,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QDockWidget,
    QFontComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QTextBrowser,
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
)


APP_NAME = "AstroEditorPro Qt"
APP_VERSION = "pro_v10_async_session_restore"
APP_ICON_PATH = str(APP_HOME / "AstroEditorIcon.png")
APP_DESKTOP_ID = "astroeditorpro"
APP_DISPLAY_NAME = "AstroEditorPro"
AUTOSAVE_DELAY_MS = 3000
STATE_FILE = "pro_state.json"
PREFS_FILE = "pro_preferences.json"
RECENT_FILE = "pro_recent_files.json"
COPY_STORAGE_FILE = "pro_copy_storage.json"

# Restore the safer explicit view state, but do not restore Qt's opaque
# binary QMainWindow state blob by default. A corrupted/old window_state
# can crash Qt before Python can catch it, especially after upgrades or shutdowns.
RESTORE_QT_BINARY_WINDOW_STATE = False
MAX_RESTORED_TABS = 30
MAX_AUTOSAVE_FILE_BYTES = 50 * 1024 * 1024

# Startup/session-restore hardening.
# Last tabs remain a core feature, but they are restored after the first window
# is visible and in small batches so the GUI event loop stays responsive.
SESSION_RESTORE_BATCH_SIZE = 1
SESSION_RESTORE_BATCH_DELAY_MS = 30
MAX_STARTUP_AUTOSAVE_FILE_BYTES = 50 * 1024 * 1024
MAX_SPELLCHECK_CHARS = 60000
SPELLCHECK_DELAY_MS = 1600

DEFAULT_SHORTCUTS = {
    "bold": "Ctrl+B",
    "italic": "Ctrl+I",
    "underline": "Ctrl+U",
    "copy": "Ctrl+C",
    "paste": "Ctrl+V",
    "store_copy_block": "Ctrl+Shift+C",
    "paste_copy_block": "Ctrl+Shift+V",
    "select_all": "Ctrl+A",
    "new_tab": "Ctrl+T",
    "new_window": "Ctrl+N",
    "save": "Ctrl+S",
    "save_as_copy_close": "Ctrl+Shift+S",
    "open": "Ctrl+O",
    "find": "Ctrl+F",
    "find_replace": "Ctrl+H",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Shift+Z",
    "indent_lines": "Tab",
    "outdent_lines": "Shift+Tab",
    "close_tab": "Ctrl+W",
    "save_as_copy_close": "Ctrl+Shift+S",
    "toggle_split_view": "Ctrl+Alt+V",
    "open_workspace": "Ctrl+Alt+O",
    "export_document": "Ctrl+Alt+E",
    "insert_clipboard_image": "Ctrl+Alt+I",
    "clear_multi_selection": "Esc",
    "bookmark_A": "Alt+A",
    "bookmark_B": "Alt+B",
    "bookmark_C": "Alt+C",
    "bookmark_D": "Alt+D",
    "bookmark_E": "Alt+E",
    "bookmark_F": "Alt+F",
    "bookmark_G": "Alt+G",
    "bookmark_H": "Alt+H",
    "bookmark_I": "Alt+I",
    "bookmark_J": "Alt+J",
    "bookmark_K": "Alt+K",
    "bookmark_L": "Alt+L",
    "bookmark_M": "Alt+M",
    "bookmark_N": "Alt+N",
    "bookmark_O": "Alt+O",
    "bookmark_P": "Alt+P",
    "bookmark_Q": "Alt+Q",
    "bookmark_R": "Alt+R",
    "bookmark_S": "Alt+S",
    "bookmark_T": "Alt+T",
    "bookmark_U": "Alt+U",
    "bookmark_V": "Alt+V",
    "bookmark_W": "Alt+W",
    "bookmark_X": "Alt+X",
    "bookmark_Y": "Alt+Y",
    "bookmark_Z": "Alt+Z",
}

SHORTCUT_COMMENTS = {
    "bold": "Toggle bold formatting on the selected text or current typing style.",
    "italic": "Toggle italic formatting on the selected text or current typing style.",
    "underline": "Toggle underline formatting on the selected text or current typing style.",
    "copy": "Copy selected text.",
    "paste": "Paste from clipboard.",
    "store_copy_block": "Store selected text in the copy-storage list.",
    "paste_copy_block": "Open copy-storage dropdown and paste the selected stored text.",
    "select_all": "Select all text in the current tab.",
    "new_tab": "Open a new blank tab.",
    "new_window": "Open another editor window.",
    "save": "Save the current tab. Empty documents are not saved.",
    "save_as_copy_close": "Save current file as a separate file elsewhere and close the original tab.",
    "open": "Open any readable text-based file, regardless of extension.",
    "find": "Open the find bar.",
    "find_replace": "Open the find and replace bar.",
    "undo": "Undo the previous save/autosave snapshot.",
    "redo": "Redo the next save/autosave snapshot.",
    "indent_lines": "Indent selected/current line by 4 spaces.",
    "outdent_lines": "Remove one 4-space/tab indent from selected/current line.",
    "close_tab": "Close the current tab.",
    "save_as_copy_close": "Save current file as a separate file elsewhere and close the original tab.",
    "toggle_split_view": "Toggle editable split view on/off.",
    "open_workspace": "Open a workspace folder.",
    "export_document": "Export the current document.",
    "insert_clipboard_image": "Insert an image currently stored in the clipboard.",
    "clear_multi_selection": "Clear stored AstroEditorPro multi-selections.",
    "bookmark_A": "Jump to bookmark A.",
    "bookmark_B": "Jump to bookmark B.",
    "bookmark_C": "Jump to bookmark C.",
    "bookmark_D": "Jump to bookmark D.",
    "bookmark_E": "Jump to bookmark E.",
    "bookmark_F": "Jump to bookmark F.",
    "bookmark_G": "Jump to bookmark G.",
    "bookmark_H": "Jump to bookmark H.",
    "bookmark_I": "Jump to bookmark I.",
    "bookmark_J": "Jump to bookmark J.",
    "bookmark_K": "Jump to bookmark K.",
    "bookmark_L": "Jump to bookmark L.",
    "bookmark_M": "Jump to bookmark M.",
    "bookmark_N": "Jump to bookmark N.",
    "bookmark_O": "Jump to bookmark O.",
    "bookmark_P": "Jump to bookmark P.",
    "bookmark_Q": "Jump to bookmark Q.",
    "bookmark_R": "Jump to bookmark R.",
    "bookmark_S": "Jump to bookmark S.",
    "bookmark_T": "Jump to bookmark T.",
    "bookmark_U": "Jump to bookmark U.",
    "bookmark_V": "Jump to bookmark V.",
    "bookmark_W": "Jump to bookmark W.",
    "bookmark_X": "Jump to bookmark X.",
    "bookmark_Y": "Jump to bookmark Y.",
    "bookmark_Z": "Jump to bookmark Z.",
}


def ensure_dirs() -> Path:
    base = Path(TEMP_DATA_DIR).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    (base / "autosave").mkdir(exist_ok=True)
    (base / "backup").mkdir(exist_ok=True)
    (base / "embedded_images").mkdir(exist_ok=True)
    return base


BASE_DIR = ensure_dirs()


def autosave_dir() -> Path:
    return BASE_DIR / "autosave"


def backup_dir() -> Path:
    d = BASE_DIR / "backup"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_autosave_file(path) -> bool:
    """Return True for AstroEditor internal autosave/recovery files."""
    if not path:
        return False
    try:
        p = Path(path).expanduser().resolve()
        auto = autosave_dir().expanduser().resolve()
        if auto in p.parents and (p.name.endswith(".aep") or p.name.endswith(".astroeditor_qt.json")):
            return True
    except Exception:
        pass

    try:
        p = Path(path)
        return p.name.startswith("autosave_") and (p.name.endswith(".aep") or p.name.endswith(".astroeditor_qt.json"))
    except Exception:
        return False


def is_rich_document_file(path) -> bool:
    """AstroEditorPro rich document formats.

    .aep is the current compact extension.
    .astroeditor_qt.json is kept readable as a legacy format.
    """
    if not path:
        return False
    try:
        name = Path(path).name.lower()
    except Exception:
        name = str(path).lower()
    return name.endswith(".aep") or name.endswith(".astroeditor_qt.json")


def safe_document_path(path):
    """Document paths should never point at internal autosave files.

    If an autosave file is opened/recovered, it should remain a recovery source,
    not become the normal user file path. This prevents autosave-of-autosave
    chains and protects annotation metadata from being written into confusing
    nested files.
    """
    if not path or is_autosave_file(path):
        return None
    return str(path)


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    saver = QSaveFile(str(path))
    if saver.open(QSaveFile.WriteOnly):
        saver.write(payload.encode("utf-8"))
        saver.commit()


def write_default_shortcuts(path: str):
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AstroEditor Qt keyboard shortcuts",
        "#",
        "# Edit values after '=' and save this file.",
        "# Changes are reloaded automatically while AstroEditor is running.",
        "# Use Qt-style shortcuts, e.g. Ctrl+B, Ctrl+Shift+S, Alt+F, F5.",
        "",
    ]
    for action, shortcut in DEFAULT_SHORTCUTS.items():
        lines.append(f"# {SHORTCUT_COMMENTS[action]}")
        lines.append(f"{action} = {shortcut}")
        lines.append("")
    p.write_text("\n".join(lines), encoding="utf-8")


def parse_shortcuts(path: str):
    p = Path(path).expanduser()
    if not p.exists():
        write_default_shortcuts(str(p))

    shortcuts = DEFAULT_SHORTCUTS.copy()
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in shortcuts and value:
            shortcuts[key] = value
    return shortcuts


def looks_binary(raw: bytes) -> bool:
    if b"\x00" in raw[:8192]:
        return True
    if not raw:
        return False
    sample = raw[:8192]
    control = sum(1 for b in sample if b < 32 and b not in b"\n\r\t\b\f")
    return control / max(1, len(sample)) > 0.20


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    if looks_binary(raw):
        raise UnicodeError("This looks like a binary file, not a text file.")

    errors = []
    for enc in ("utf-8", "utf-8-sig", "cp1250", "iso-8859-2", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError as exc:
            errors.append(f"{enc}: {exc}")
    raise UnicodeError("Could not decode as text:\n" + "\n".join(errors))


def meaningful_text(editor: QTextEdit) -> str:
    return editor.toPlainText().strip()


def block_preview(text: str, max_words: int = 5) -> str:
    words = re.findall(r"\S+", text.strip())
    if not words:
        return "(empty)"
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "..."


def normalize_block_text(text: str) -> str:
    # Preserve selected text, but normalize Qt paragraph separators and line endings.
    return (
        text.replace("\u2029", "\n")
            .replace("\u2028", "\n")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
    )




class NoteHoverPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #fff7c2;
                color: #000000;
                border: 1px solid #777;
                border-radius: 4px;
            }
            QLabel {
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(420)
        layout.addWidget(self.label)

    def show_note(self, text, global_pos):
        self.label.setText(text)
        self.adjustSize()
        self.move(global_pos + QPoint(18, 18))
        self.show()
        self.raise_()


class RichTextEdit(QTextEdit):
    def __init__(self, tab):
        super().__init__()
        self.tab = tab
        self.zoom_percent = 100
        self.note_popup = NoteHoverPopup(self)
        self._last_hover_note_id = None
        self.setMouseTracking(True)

    def keyPressEvent(self, event):
        # Clear AstroEditorPro emulated multi/column selections when user
        # cancels or navigates away, matching normal selection expectations.
        if event.key() == Qt.Key_Escape:
            if getattr(self.tab, "multi_selections", None):
                self.tab.clear_multi_selections()
                event.accept()
                return

        # Clear stored multi-selections only for explicit horizontal cursor
        # movement, as requested. Other keys, including formatting shortcuts,
        # should leave the stored ranges visible.
        if event.key() in (Qt.Key_Left, Qt.Key_Right):
            if getattr(self.tab, "multi_selections", None):
                self.tab.clear_multi_selections()

        # Handle undo/redo here before QTextEdit consumes Ctrl+Z/Ctrl+Shift+Z.
        # This keeps the snapshot undo system working for text, highlights,
        # notes, images, and formatting together.
        if event.matches(QKeySequence.Undo):
            self.tab.main.undo_action()
            event.accept()
            return
        if event.matches(QKeySequence.Redo) or (event.key() == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier)):
            self.tab.main.redo_action()
            event.accept()
            return

        # Coding convenience: indent/outdent whole selected/current lines.
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
            self.tab.indent_selected_lines(4)
            event.accept()
            return
        if event.key() == Qt.Key_Backtab or (event.key() == Qt.Key_Tab and (event.modifiers() & Qt.ShiftModifier)):
            self.tab.outdent_selected_lines(4)
            event.accept()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.tab.set_zoom(self.zoom_percent + 10)
            elif delta < 0:
                self.tab.set_zoom(self.zoom_percent - 10)
            event.accept()
            return
        super().wheelEvent(event)

    def insert_image_from_path(self, path: str):
        fmt = QTextImageFormat()
        fmt.setName(path)
        cursor = self.textCursor()
        cursor.insertImage(fmt)
        self.setTextCursor(cursor)

    def insertFromMimeData(self, source):
        # Paste copied images from outside the app.
        # The image is stored in TEMP_DATA_DIR/embedded_images and inserted
        # by local path, so it survives autosave/reopen as long as that data
        # directory remains present.
        if source.hasImage():
            try:
                image = source.imageData()
                path = save_clipboard_image(image)
                self.insert_image_from_path(path)
                self.tab.on_text_changed()
                return
            except Exception as exc:
                self.tab.main.status(f"Image paste failed: {exc}")

        # Also handle copied image files from a file manager.
        if source.hasUrls():
            for url in source.urls():
                local = url.toLocalFile()
                if local and Path(local).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
                    self.insert_image_from_path(local)
                    self.tab.on_text_changed()
                    return

        super().insertFromMimeData(source)

    def annotation_at_position(self, pos: int, kind=None):
        matches = []
        for ann in self.tab.doc.annotations:
            if kind is not None and ann.get("kind") != kind:
                continue
            if int(ann.get("start", -1)) <= pos < int(ann.get("end", -1)):
                matches.append(ann)
        if not matches:
            return None
        matches.sort(key=lambda a: (int(a.get("end", 0)) - int(a.get("start", 0))))
        return matches[0]

    def mousePressEvent(self, event):
        # Ctrl+Shift drag: approximate column/rectangular selection.
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier):
            cursor = self.textCursor()
            if cursor.hasSelection():
                self.tab.add_multi_selection(cursor.selectionStart(), cursor.selectionEnd())
                cursor.clearSelection()
                self.setTextCursor(cursor)
            self.tab.column_selecting = True
            self.tab.column_start = event.position().toPoint()
            self.tab.column_end = self.tab.column_start
            event.accept()
            return

        # Ctrl + start another selection:
        # if the editor currently has a normal selection, convert/toggle it
        # into AstroEditorPro's stored multi-selection first, just like a file
        # explorer keeps the old selected item when Ctrl-selecting another.
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            cursor = self.textCursor()
            if cursor.hasSelection():
                self.tab.add_multi_selection(cursor.selectionStart(), cursor.selectionEnd())
                cursor.clearSelection()
                self.setTextCursor(cursor)

        # A normal click clears emulated multi-selections.
        if event.button() == Qt.LeftButton and not (event.modifiers() & Qt.ControlModifier):
            if getattr(self.tab, "multi_selections", None):
                self.tab.clear_multi_selections()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self.tab, "column_selecting", False):
            self.tab.column_end = event.position().toPoint()
            self.tab.finalize_column_selection()
            self.tab.column_selecting = False
            event.accept()
            return

        super().mouseReleaseEvent(event)

        if event.button() == Qt.LeftButton and (QApplication.keyboardModifiers() & Qt.ControlModifier) and self.textCursor().hasSelection():
            self.tab.add_multi_selection_from_cursor()
            event.accept()
            return

        if event.button() == Qt.LeftButton and self.tab.main.current_annotation_mode == "highlight":
            cursor = self.textCursor()
            if cursor.hasSelection():
                self.tab.main.add_highlight_from_current_selection()
                event.accept()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()

        highlight = self.annotation_at_position(pos, kind="highlight")
        note = self.annotation_at_position(pos, kind="note")
        miss = self.tab.misspelling_at_position(pos) if hasattr(self.tab, "misspelling_at_position") else None

        menu.addSeparator()
        add_bm = menu.addAction("Add bookmark for this line")
        add_bm.triggered.connect(lambda checked=False, p=pos: self.tab.main.add_bookmark_at_cursor_or_position(p))

        if highlight or note or miss:
            menu.addSeparator()

        if miss:
            word = miss.get("word", "")
            suggestions = self.tab.main.spellchecker.suggestions(word)
            if suggestions:
                suggestions_menu = menu.addMenu(f"Spelling suggestions for '{word}'")
                for suggestion in suggestions:
                    act = suggestions_menu.addAction(suggestion)
                    act.triggered.connect(
                        lambda checked=False, replacement=suggestion, start=miss.get("start"), end=miss.get("end"):
                            self.tab.main.replace_misspelled_word(start, end, replacement)
                    )
            else:
                no_suggestions = menu.addAction(f"No suggestions for '{word}'")
                no_suggestions.setEnabled(False)

            add_word_act = menu.addAction(f"Add '{word}' to user dictionary")
            add_word_act.triggered.connect(lambda checked=False, w=word: self.tab.main.add_word_to_user_dictionary(w))

        if highlight:
            text = self.tab.annotation_text(highlight).strip()
            act = menu.addAction(f"Delete highlight: {block_preview(text)}")
            act.triggered.connect(lambda checked=False, ann_id=highlight.get("id"): self.tab.main.delete_annotation(ann_id))

        if note:
            act = menu.addAction(f"Delete note: {block_preview(note.get('note', ''))}")
            act.triggered.connect(lambda checked=False, ann_id=note.get("id"): self.tab.main.delete_annotation(ann_id))

        menu.exec(event.globalPos())

    def mouseMoveEvent(self, event):
        if getattr(self.tab, "column_selecting", False):
            self.tab.column_end = event.position().toPoint()
            self.tab.update_column_selection_preview()
            event.accept()
            return

        cursor = self.cursorForPosition(event.pos())
        note = self.annotation_at_position(cursor.position(), kind="note")

        if note:
            note_id = note.get("id")
            text = note.get("note", "")
            if text:
                self.setToolTip(text)
                if note_id != self._last_hover_note_id or not self.note_popup.isVisible():
                    self.note_popup.show_note(text, event.globalPosition().toPoint())
                else:
                    self.note_popup.move(event.globalPosition().toPoint() + QPoint(18, 18))
                self._last_hover_note_id = note_id
        else:
            self.setToolTip("")
            self._last_hover_note_id = None
            self.note_popup.hide()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.note_popup.hide()
        self._last_hover_note_id = None
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        note = self.annotation_at_position(cursor.position(), kind="note")
        if note:
            self.tab.main.show_notes_sidebar()
            self.tab.main.select_annotation_in_sidebar(note.get("id"))
            event.accept()
            return

        doc = self.document()
        for pos in (cursor.position() - 1, cursor.position(), cursor.position() + 1):
            if pos < 0 or pos >= doc.characterCount():
                continue
            probe = QTextCursor(doc)
            probe.setPosition(pos)
            probe.setPosition(pos + 1, QTextCursor.KeepAnchor)
            if probe.charFormat().isImageFormat():
                self.setTextCursor(probe)
                self.tab.main.refresh_image_size_controls()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)



def save_clipboard_image(image) -> str:
    """Save a pasted clipboard image and return its local file path."""
    out_dir = BASE_DIR / "embedded_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"pasted_image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}.png"
    path = out_dir / filename
    if not image.save(str(path), "PNG"):
        raise RuntimeError("Could not save clipboard image.")
    return str(path)



def unique_embedded_image_path(prefix="image", suffix=".png") -> str:
    out_dir = BASE_DIR / "embedded_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}{suffix}"
    return str(out_dir / filename)


def load_image_from_document_name(name: str) -> QImage:
    if name.startswith("file://"):
        name = name[7:]
    image = QImage(name)
    if image.isNull():
        raise RuntimeError(f"Could not load image: {name}")
    return image


def save_qimage(image: QImage, prefix="edited_image") -> str:
    path = unique_embedded_image_path(prefix=prefix, suffix=".png")
    if not image.save(path, "PNG"):
        raise RuntimeError("Could not save edited image.")
    return path


def iter_html_image_sources(html: str):
    """Return image sources from QTextEdit HTML."""
    if not html:
        return []
    sources = []
    pattern = r"""<img[^>]+src=["']([^"']+)["']"""
    for match in re.finditer(pattern, html, flags=re.IGNORECASE):
        src = match.group(1)
        if src and src not in sources:
            sources.append(src)
    return sources


def image_source_to_local_path(src: str):
    if not src or src.startswith("data:"):
        return None
    if src.startswith("file://"):
        src = src[7:]
    try:
        p = Path(src).expanduser()
        if p.exists() and p.is_file():
            return p
    except Exception:
        pass
    return None


def collect_embedded_images_from_html(html: str):
    """Collect local images referenced by HTML into base64 blobs."""
    images = {}
    for src in iter_html_image_sources(html):
        p = image_source_to_local_path(src)
        if not p:
            continue
        try:
            raw = p.read_bytes()
            mime = mimetypes.guess_type(str(p))[0] or "image/png"
            images[src] = {
                "name": p.name,
                "mime": mime,
                "data": base64.b64encode(raw).decode("ascii"),
            }
        except Exception as exc:
            print(f"AstroEditorPro could not embed image {src}: {exc}", flush=True)
    return images


def restore_embedded_images_to_cache(images: dict):
    """Restore base64 embedded images to local cache and return src remapping."""
    if not images:
        return {}
    out_dir = BASE_DIR / "embedded_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    remap = {}
    for old_src, item in images.items():
        try:
            name = item.get("name") or "embedded_image.png"
            suffix = Path(name).suffix or ".png"
            out_path = Path(unique_embedded_image_path(prefix="restored_embedded_image", suffix=suffix))
            raw = base64.b64decode(item.get("data", ""))
            out_path.write_bytes(raw)
            remap[old_src] = str(out_path)
        except Exception as exc:
            print(f"AstroEditorPro could not restore embedded image {old_src}: {exc}", flush=True)
    return remap


def remap_html_image_sources(html: str, remap: dict):
    if not html or not remap:
        return html
    for old, new in remap.items():
        html = html.replace(old, new)
    return html




def cleanup_embedded_image_cache():
    """Remove temporary extracted/pasted image cache on process exit.

    Documents saved as .aep are self-contained, so these files can be restored
    from the document on next open.
    """
    try:
        folder = BASE_DIR / "embedded_images"
        if folder.exists():
            for item in folder.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as exc:
                    print(f"AstroEditorPro could not remove cached image {item}: {exc}", flush=True)
    except Exception as exc:
        print(f"AstroEditorPro image cache cleanup failed: {exc}", flush=True)


class SpellCheckerManager:
    """Hunspell/spylls spellchecker wrapper with user-selected languages."""

    WORD_RE = re.compile(r"[A-Za-zÀ-žĆćČčĐđŠšŽž]+(?:[-'][A-Za-zÀ-žĆćČčĐđŠšŽž]+)*", re.UNICODE)

    def __init__(self, selected_languages=None):
        self.enabled = False
        self.dictionaries = []
        self.user_words = set()
        # Do not load Hunspell dictionaries during startup. Load lazily when needed.
        self.selected_languages = list(selected_languages or [])
        self.load_user_dictionary()

    @staticmethod
    def dictionary_base_dir():
        return Path(SPELLCHECK_DICTIONARY_DIR).expanduser()

    @classmethod
    def installed_language_codes(cls):
        base = cls.dictionary_base_dir()
        if not base.exists():
            return []
        codes = []
        for aff in base.glob("*.aff"):
            code = aff.stem
            if (base / f"{code}.dic").exists():
                codes.append(code)
        return sorted(set(codes), key=lambda c: language_display_name(c).lower())

    @classmethod
    def has_dictionary(cls, lang):
        base = cls.dictionary_base_dir()
        return (base / f"{lang}.aff").exists() and (base / f"{lang}.dic").exists()

    def load_user_dictionary(self):
        path = Path(SPELLCHECK_USER_DICTIONARY).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        try:
            self.user_words = {
                line.strip().lower()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            }
        except Exception:
            self.user_words = set()

    def save_user_dictionary(self):
        path = Path(SPELLCHECK_USER_DICTIONARY).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(sorted(self.user_words)) + ("\n" if self.user_words else ""), encoding="utf-8")

    def load_dictionaries(self, languages=None):
        self.dictionaries = []
        self.selected_languages = list(languages or [])
        try:
            from spylls.hunspell import Dictionary
        except Exception:
            return

        base = Path(SPELLCHECK_DICTIONARY_DIR).expanduser()
        for lang in self.selected_languages:
            aff = base / f"{lang}.aff"
            dic = base / f"{lang}.dic"
            if aff.exists() and dic.exists():
                try:
                    self.dictionaries.append((lang, Dictionary.from_files(str(base / lang))))
                except Exception as exc:
                    print(f"Could not load Hunspell dictionary {lang}: {exc}", flush=True)

    def reload(self, languages=None):
        self.load_user_dictionary()
        self.load_dictionaries(languages if languages is not None else self.selected_languages)

    def available(self):
        return bool(self.dictionaries)

    def is_user_word(self, word):
        w = word.strip().lower()
        return w in self.user_words

    def add_user_word(self, word):
        w = word.strip().lower()
        if not w:
            return
        self.user_words.add(w)
        self.save_user_dictionary()

    def check_word(self, word):
        if not word or self.is_user_word(word):
            return True
        if any(ch.isdigit() for ch in word) or len(word) <= 1:
            return True
        for _lang, dictionary in self.dictionaries:
            try:
                if dictionary.lookup(word):
                    return True
            except Exception:
                pass
        return False

    def suggestions(self, word, limit=8):
        seen = []
        for _lang, dictionary in self.dictionaries:
            try:
                for suggestion in dictionary.suggest(word):
                    if suggestion not in seen:
                        seen.append(suggestion)
                    if len(seen) >= limit:
                        return seen
            except Exception:
                pass
        return seen

    def misspellings(self, text):
        if not self.enabled or not self.available():
            return []
        out = []
        for match in self.WORD_RE.finditer(text):
            word = match.group(0)
            if not self.check_word(word):
                out.append({
                    "word": word,
                    "start": match.start(),
                    "end": match.end(),
                    "suggestions": self.suggestions(word),
                })
        return out


def language_display_name(code):
    if code in COMMON_HUNSPELL_LANGUAGES:
        return COMMON_HUNSPELL_LANGUAGES[code][0]
    return code.replace("_", "-")


def language_package_name(code):
    if code in COMMON_HUNSPELL_LANGUAGES:
        return COMMON_HUNSPELL_LANGUAGES[code][1]
    return "hunspell-" + code.split("_")[0].lower()



@dataclass
class DocumentInfo:
    path: str | None = None
    autosave_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    dirty: bool = False
    title: str = "Untitled"
    annotations: list = field(default_factory=list)
    bookmarks: list = field(default_factory=list)


    def __post_init__(self):
        # Defensive normalization. If a generated/broken version ever lets
        # dataclasses.field objects reach runtime, convert them to safe values.
        from dataclasses import Field
        if isinstance(self.annotations, Field) or self.annotations is None:
            self.annotations = []
        if isinstance(self.bookmarks, Field) or self.bookmarks is None:
            self.bookmarks = []
        if isinstance(self.path, Field):
            self.path = None
        if isinstance(self.autosave_path, Field):
            self.autosave_path = None
        if isinstance(self.title, Field) or not self.title:
            self.title = "Untitled"


class LineNumberArea(QWidget):
    def __init__(self, tab):
        super().__init__(tab)
        self.tab = tab
        self.setMinimumWidth(44)

    def sizeHint(self):
        return QSize(self.tab.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.tab.paint_line_numbers(event)


class EditorTab(QWidget):
    def __init__(self, main, doc=None):
        super().__init__()
        self.main = main
        self.doc = doc or DocumentInfo()
        # Runtime guard against older/broken generated DocumentInfo objects
        # where dataclasses.field leaked into annotations/bookmarks.
        from dataclasses import Field
        if isinstance(getattr(self.doc, "annotations", None), Field) or self.doc.annotations is None:
            self.doc.annotations = []
        if isinstance(getattr(self.doc, "bookmarks", None), Field) or self.doc.bookmarks is None:
            self.doc.bookmarks = []

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.autosave)

        # Used for real visual zoom. When zoomed away from 100%, this stores
        # the document's unzoomed HTML so repeated wheel steps do not compound
        # formatting errors.
        self._zoom_base_html = None
        self._applying_zoom = False
        self.misspellings = []
        self.multi_selections = []
        self.column_selecting = False
        self.column_start = None
        self.column_end = None
        self.spellcheck_timer = QTimer(self)
        self.spellcheck_timer.setSingleShot(True)
        self.spellcheck_timer.timeout.connect(self.run_spellcheck)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        editor_row = QHBoxLayout()
        editor_row.setContentsMargins(0, 0, 0, 0)
        editor_row.setSpacing(0)
        outer_layout.addLayout(editor_row)

        self.editor = RichTextEdit(self)
        self.editor.setAcceptRichText(True)

        self.line_number_area = LineNumberArea(self)
        editor_row.addWidget(self.line_number_area)
        editor_row.addWidget(self.editor)

        self.apply_wrap_mode()
        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.cursorPositionChanged.connect(self.main.update_format_buttons)

        self.editor.verticalScrollBar().valueChanged.connect(lambda _v: self.line_number_area.update())
        self.editor.document().blockCountChanged.connect(lambda _n: self.update_line_number_area_width())
        self.editor.cursorPositionChanged.connect(lambda: self.line_number_area.update())
        self.editor.viewport().installEventFilter(self)

        self.update_line_number_area_width()
        self.apply_preferences()

    def eventFilter(self, obj, event):
        if obj is self.editor.viewport() and event.type() in (
            QEvent.Paint,
            QEvent.Resize,
            QEvent.Wheel,
            QEvent.MouseButtonRelease,
            QEvent.KeyRelease,
        ):
            self.line_number_area.update()
        return super().eventFilter(obj, event)

    def schedule_spellcheck(self):
        if self.main.prefs.get("spellcheck_enabled", False):
            if self.editor.document().characterCount() > MAX_SPELLCHECK_CHARS:
                self.misspellings = []
                self.apply_annotations()
                self.main.status("Spellcheck skipped for a large document.")
                return
            self.spellcheck_timer.start(SPELLCHECK_DELAY_MS)
        else:
            self.spellcheck_timer.stop()
            if self.misspellings:
                self.misspellings = []
                self.apply_annotations()

    def run_spellcheck(self):
        if not self.main.prefs.get("spellcheck_enabled", False):
            self.misspellings = []
            self.apply_annotations()
            return

        text = self.editor.toPlainText()
        if len(text) > MAX_SPELLCHECK_CHARS:
            self.misspellings = []
            self.apply_annotations()
            self.main.status("Spellcheck skipped for a large document.")
            return

        langs = self.main.current_spellcheck_languages() if hasattr(self.main, "current_spellcheck_languages") else []
        langs = [l for l in langs if l]
        if not langs:
            self.misspellings = []
            self.apply_annotations()
            self.editor.viewport().update()
            return

        try:
            self.main.ensure_spellchecker_loaded(langs)
            old_dicts = self.main.spellchecker.dictionaries
            self.main.spellchecker.dictionaries = [(l, d) for (l, d) in old_dicts if l in langs]
            self.misspellings = self.main.spellchecker.misspellings(text)
            self.main.spellchecker.dictionaries = old_dicts
        except Exception as exc:
            print(f"AstroEditor spellcheck failed: {exc}", flush=True)
            self.misspellings = []

        self.apply_annotations()
        self.editor.viewport().update()

    def misspelling_at_position(self, pos):
        for miss in self.misspellings:
            if int(miss.get("start", -1)) <= pos < int(miss.get("end", -1)):
                return miss
        return None

    def line_number_area_width(self):
        if not self.main.prefs.get("show_line_numbers", True):
            return 0
        digits = len(str(max(1, self.editor.document().blockCount())))
        space = 16 + self.editor.fontMetrics().horizontalAdvance("9") * digits
        return max(44, space)

    def update_line_number_area_width(self):
        enabled = self.main.prefs.get("show_line_numbers", True)
        self.line_number_area.setVisible(enabled)
        self.line_number_area.setFixedWidth(self.line_number_area_width() if enabled else 0)
        self.line_number_area.update()

    def paint_line_numbers(self, event):
        if not self.main.prefs.get("show_line_numbers", True):
            return

        painter = QPainter(self.line_number_area)
        try:
            bg = QColor(self.main.prefs.get("background", "#000000"))
            fg = QColor(self.main.prefs.get("line_number_color", "#888888"))
            painter.fillRect(event.rect(), bg.darker(115))
            painter.setPen(fg)
            painter.setFont(self.editor.font())

            # QTextEdit does not have contentOffset(); that belongs to
            # QPlainTextEdit. For QTextEdit, document layout coordinates are
            # converted to viewport coordinates by subtracting the scrollbar
            # values.
            doc_layout = self.editor.document().documentLayout()
            vscroll = self.editor.verticalScrollBar().value()
            hscroll = self.editor.horizontalScrollBar().value()

            block = self.editor.document().firstBlock()
            block_number = 1

            while block.isValid():
                block_rect = doc_layout.blockBoundingRect(block)
                top = int(block_rect.top() - vscroll)
                bottom = int(block_rect.bottom() - vscroll)

                if bottom >= event.rect().top() and top <= event.rect().bottom():
                    bookmark_blocks = set()
                    for bm in getattr(self.doc, "bookmarks", []):
                        try:
                            b = self.editor.document().findBlock(int(bm.get("position", -1)))
                            if b.isValid():
                                bookmark_blocks.add(b.blockNumber() + 1)
                        except Exception:
                            pass

                    if block_number in bookmark_blocks:
                        painter.fillRect(
                            0,
                            top,
                            self.line_number_area.width(),
                            self.editor.fontMetrics().height(),
                            QColor("#8a7300"),
                        )
                        painter.setPen(QColor("#ffffff"))
                    else:
                        painter.setPen(fg)

                    painter.drawText(
                        0,
                        top,
                        self.line_number_area.width() - 6 - hscroll * 0,
                        self.editor.fontMetrics().height(),
                        Qt.AlignRight,
                        str(block_number),
                    )

                block = block.next()
                block_number += 1
        finally:
            painter.end()

    def annotation_text(self, ann):
        cursor = QTextCursor(self.editor.document())
        max_pos = max(0, self.editor.document().characterCount() - 1)
        start = max(0, min(int(ann.get("start", 0)), max_pos))
        end = max(start, min(int(ann.get("end", start)), max_pos))
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        return cursor.selectedText().replace("\u2029", "\n").replace("\u2028", "\n")

    def normalize_multi_selection(self, start, end):
        start, end = int(start), int(end)
        if end < start:
            start, end = end, start
        if end == start:
            return None
        max_pos = max(0, self.editor.document().characterCount() - 1)
        start = max(0, min(start, max_pos))
        end = max(start, min(end, max_pos))
        return (start, end)

    def ranges_overlap(self, a, b):
        return max(a[0], b[0]) < min(a[1], b[1])

    def add_multi_selection(self, start, end):
        rng = self.normalize_multi_selection(start, end)
        if not rng:
            return

        # File-explorer-like toggle behavior:
        # selecting an already stored range, or a range overlapping it,
        # removes the existing stored range instead of adding another one.
        removed = False
        kept = []
        for existing in self.multi_selections:
            if self.ranges_overlap(existing, rng):
                removed = True
                continue
            kept.append(existing)

        if removed:
            self.multi_selections = kept
            self.status_text = "Removed multi-selection."
        else:
            kept.append(rng)
            self.multi_selections = sorted(kept, key=lambda r: (r[0], r[1]))
            self.status_text = f"Added multi-selection #{len(self.multi_selections)}."

        self.apply_annotations()
        self.editor.viewport().update()
        self.main.status(self.status_text)

    def add_multi_selection_from_cursor(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.add_multi_selection(cursor.selectionStart(), cursor.selectionEnd())
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)

    def clear_multi_selections(self):
        self.multi_selections = []
        self.apply_annotations()
        self.editor.viewport().update()

    def update_column_selection_preview(self):
        self.apply_annotations()
        self.editor.viewport().update()

    def column_ranges_from_points(self, p1, p2):
        rect = QRect(p1, p2).normalized()
        doc = self.editor.document()
        top_cursor = self.editor.cursorForPosition(rect.topLeft())
        bottom_cursor = self.editor.cursorForPosition(rect.bottomRight())
        start_block = top_cursor.blockNumber()
        end_block = bottom_cursor.blockNumber()
        ranges = []
        for block_no in range(start_block, end_block + 1):
            block = doc.findBlockByNumber(block_no)
            if not block.isValid():
                continue
            block_cursor = QTextCursor(block)
            line_rect = self.editor.cursorRect(block_cursor)
            y = line_rect.center().y()
            left_cursor = self.editor.cursorForPosition(QPoint(rect.left(), y))
            right_cursor = self.editor.cursorForPosition(QPoint(rect.right(), y))
            if left_cursor.blockNumber() != block_no:
                left_cursor = QTextCursor(block)
            if right_cursor.blockNumber() != block_no:
                right_cursor = QTextCursor(block)
                right_cursor.movePosition(QTextCursor.EndOfBlock)
            rng = self.normalize_multi_selection(left_cursor.position(), right_cursor.position())
            if rng:
                ranges.append(rng)
        return ranges

    def finalize_column_selection(self):
        if self.column_start is None or self.column_end is None:
            return
        for rng in self.column_ranges_from_points(self.column_start, self.column_end):
            if rng not in self.multi_selections:
                self.multi_selections.append(rng)
        self.column_start = None
        self.column_end = None
        self.apply_annotations()
        self.editor.viewport().update()
        self.main.status(f"Added column selection with {len(self.multi_selections)} total range(s).")

    def merge_char_format_to_multi_selections(self, fmt):
        if not self.multi_selections:
            return False
        cursor = QTextCursor(self.editor.document())
        cursor.beginEditBlock()
        for start, end in list(self.multi_selections):
            c = QTextCursor(self.editor.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            c.mergeCharFormat(fmt)
        cursor.endEditBlock()

        # Keep the emulated multi-selection visible after formatting, so several
        # formatting actions can be applied in sequence, e.g. Ctrl+B then Ctrl+I.
        self.doc.dirty = True
        self.main.refresh_tab_title(self)
        self.apply_annotations()
        self.editor.viewport().update()
        self.autosave_timer.start(AUTOSAVE_DELAY_MS)
        return True

    def apply_annotations(self):
        selections = []

        for ann in self.doc.annotations:
            start = int(ann.get("start", 0))
            end = int(ann.get("end", 0))
            if end <= start:
                continue
            max_pos = max(0, self.editor.document().characterCount() - 1)
            start = max(0, min(start, max_pos))
            end = max(start, min(end, max_pos))

            cursor = QTextCursor(self.editor.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            fmt = QTextCharFormat()

            if ann.get("kind") == "highlight":
                color = QColor(ann.get("color", "#ffff00"))
                color.setAlpha(120)
                fmt.setBackground(color)
            elif ann.get("kind") == "note":
                fmt.setUnderlineStyle(QTextCharFormat.DashUnderline)
                fmt.setUnderlineColor(QColor(ann.get("color", "#00a0ff")))

            selection.format = fmt
            selections.append(selection)

        # AstroEditorPro emulated multi-selections.
        for start, end in getattr(self, "multi_selections", []):
            cursor = QTextCursor(self.editor.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#3355aa"))
            selection.format = fmt
            selections.append(selection)

        # Ctrl+Shift column selection preview.
        if getattr(self, "column_selecting", False) and self.column_start is not None and self.column_end is not None:
            for start, end in self.column_ranges_from_points(self.column_start, self.column_end):
                cursor = QTextCursor(self.editor.document())
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#553388"))
                selection.format = fmt
                selections.append(selection)

        if self.main.prefs.get("spellcheck_enabled", False):
            for miss in self.misspellings:
                start = int(miss.get("start", 0))
                end = int(miss.get("end", 0))
                if end <= start:
                    continue
                max_pos = max(0, self.editor.document().characterCount() - 1)
                start = max(0, min(start, max_pos))
                end = max(start, min(end, max_pos))

                cursor = QTextCursor(self.editor.document())
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)

                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                fmt = QTextCharFormat()
                fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
                fmt.setUnderlineColor(QColor("#ff3333"))
                selection.format = fmt
                selections.append(selection)

        self.editor.setExtraSelections(selections)

    def selected_line_range(self):
        cursor = self.editor.textCursor()
        doc = self.editor.document()

        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()

            # If the selection ends at the very start of a block, do not include
            # that following block.
            end_cursor = QTextCursor(doc)
            end_cursor.setPosition(end)
            if end > start and end_cursor.positionInBlock() == 0:
                end -= 1
        else:
            start = cursor.position()
            end = cursor.position()

        start_cursor = QTextCursor(doc)
        start_cursor.setPosition(max(0, start))
        end_cursor = QTextCursor(doc)
        end_cursor.setPosition(max(0, end))

        start_block = start_cursor.blockNumber()
        end_block = end_cursor.blockNumber()
        return start_block, end_block

    def indent_selected_lines(self, spaces=4):
        doc = self.editor.document()
        start_block, end_block = self.selected_line_range()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        for block_number in range(start_block, end_block + 1):
            block = doc.findBlockByNumber(block_number)
            if not block.isValid():
                continue
            cursor.setPosition(block.position())
            cursor.insertText(" " * spaces)
        cursor.endEditBlock()
        self.on_text_changed()

    def outdent_selected_lines(self, spaces=4):
        doc = self.editor.document()
        start_block, end_block = self.selected_line_range()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        for block_number in range(start_block, end_block + 1):
            block = doc.findBlockByNumber(block_number)
            if not block.isValid():
                continue

            text = block.text()
            remove_count = 0

            if text.startswith("\t"):
                remove_count = 1
            else:
                leading_spaces = len(text) - len(text.lstrip(" "))
                remove_count = min(spaces, leading_spaces)

            if remove_count > 0:
                cursor.setPosition(block.position())
                cursor.setPosition(block.position() + remove_count, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()

        cursor.endEditBlock()
        self.on_text_changed()

    def is_empty(self) -> bool:
        return meaningful_text(self.editor) == ""

    def tab_name(self) -> str:
        if self.doc.path:
            base = Path(self.doc.path).name
        else:
            base = self.doc.title
        return ("*" if self.doc.dirty else "") + base

    def set_plain_text(self, text: str):
        self.editor.blockSignals(True)
        self.editor.zoom_percent = 100
        self._zoom_base_html = None
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.doc.dirty = False
        self.apply_annotations()
        self.schedule_spellcheck()

    def set_html(self, html: str):
        self.editor.blockSignals(True)
        self.editor.zoom_percent = 100
        self._zoom_base_html = None
        self.editor.setHtml(html)
        self.editor.blockSignals(False)
        self.doc.dirty = False
        self.apply_annotations()
        self.schedule_spellcheck()

    def html_payload(self):
        # If the document is visually zoomed, save the original unzoomed HTML,
        # not the temporarily scaled display HTML.
        html = self._zoom_base_html if (self.editor.zoom_percent != 100 and self._zoom_base_html is not None) else self.editor.toHtml()
        embedded_images = collect_embedded_images_from_html(html)
        return {
            "format": "astroeditor-qt-html-v2-self-contained",
            "html": html,
            "plain": self.editor.toPlainText(),
            "annotations": self.doc.annotations,
            "bookmarks": getattr(self.doc, "bookmarks", []),
            "embedded_images": embedded_images,
        }

    def on_text_changed(self):
        if self._applying_zoom:
            return
        self._zoom_base_html = None
        self.doc.dirty = True

        if not getattr(self.main, "_restoring_snapshot", False):
            self.main.validate_annotations_after_text_change(self)

        self.main.refresh_tab_title(self)
        self.apply_annotations()
        self.update_line_number_area_width()
        self.line_number_area.update()
        self.editor.viewport().update()
        self.main.refresh_annotation_sidebars()
        self.schedule_spellcheck()
        if hasattr(self.main, 'schedule_outline_refresh'):
            self.main.schedule_outline_refresh()
            self.main.refresh_bookmarks_sidebar()
            self.main.refresh_split_view()
        self.autosave_timer.start(AUTOSAVE_DELAY_MS)

    def autosave(self) -> bool:
        if self.is_empty():
            self.main.status("Autosave skipped: empty tab.")
            return False

        if not self.doc.autosave_path:
            filename = f"autosave_{self.doc.created_at}_{int(time.time())}.aep"
            self.doc.autosave_path = str(BASE_DIR / "autosave" / filename)

        try:
            payload = {
                "document": {
                    "path": safe_document_path(self.doc.path),
                    "title": self.doc.title,
                    "created_at": self.doc.created_at,
                    "autosave_path": self.doc.autosave_path,
                },
                "content": self.html_payload(),
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            save_json(Path(self.doc.autosave_path), payload)

            # If saved to a normal user file, autosave there too.
            # Empty content is never written.
            # Internal autosave/recovery files are never treated as normal
            # document paths, preventing autosave-of-autosave chains.
            if self.doc.path and not is_autosave_file(self.doc.path):
                p = Path(self.doc.path)
                if is_rich_document_file(p):
                    save_json(p, self.html_payload())
                elif p.suffix.lower() in {".html", ".htm"}:
                    p.write_text(self.editor.toHtml(), encoding="utf-8")
                else:
                    p.write_text(self.editor.toPlainText(), encoding="utf-8")
                self.doc.dirty = False
                self.main.refresh_tab_title(self)

            self.main.commit_snapshot_boundary(self, "autosave")
            self.main.status("Autosaved.")
            return True
        except Exception as exc:
            self.main.status(f"Autosave failed: {exc}")
            return False

    def has_rich_metadata(self) -> bool:
        html = self.editor.toHtml()
        # QTextEdit HTML always differs from plain text, so the strongest
        # signal is metadata/images. Formatting itself is also preserved if
        # the user chooses .aep.
        return bool(
            self.doc.annotations
            or getattr(self.doc, "bookmarks", [])
            or collect_embedded_images_from_html(html)
        )

    def save(self) -> bool:
        if self.is_empty():
            QMessageBox.information(self, "Empty file not saved", "This tab is empty, so it was not saved.")
            return False

        if not self.doc.path or is_autosave_file(self.doc.path):
            # Recovery/autosave documents should be explicitly saved by the
            # user to a normal file path, not written back into the internal
            # autosave area.
            return self.save_as(force_rich=True)

        p = Path(self.doc.path)

        if not is_rich_document_file(p) and self.has_rich_metadata():
            answer = QMessageBox.question(
                self,
                "Save self-contained document?",
                "This document contains annotations, bookmarks or embedded images.\n\n"
                "To preserve everything in one file, save it as a self-contained "
                ".aep document instead?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                return self.save_as(force_rich=True)

        try:
            if is_rich_document_file(p):
                save_json(p, self.html_payload())
            elif p.suffix.lower() in {".html", ".htm"}:
                p.write_text(self.editor.toHtml(), encoding="utf-8")
            else:
                p.write_text(self.editor.toPlainText(), encoding="utf-8")

            self.doc.dirty = False
            self.main.add_recent(str(p))
            self.main.refresh_tab_title(self)
            self.main.commit_snapshot_boundary(self, "save")
            self.main.status(f"Saved: {p}")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False

    def save_as(self, force_rich=False) -> bool:
        if self.is_empty():
            QMessageBox.information(self, "Empty file not saved", "This tab is empty, so it was not saved.")
            return False

        default_name = Path(self.doc.title or "Untitled").stem + ".aep" if force_rich else ""
        start_path = str(Path(self.main.last_folder()) / default_name) if default_name else self.main.last_folder()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save file as",
            start_path,
            "AstroEditorPro self-contained file (*.aep);;Plain text (*.txt);;HTML file (*.html);;All files (*)",
        )
        if not path:
            return False
        if force_rich and not is_rich_document_file(path):
            path += ".aep"
        self.main.remember_folder_from_path(path)
        self.doc.path = safe_document_path(path)
        self.doc.title = Path(path).name
        return self.save()

    def apply_wrap_mode(self):
        if self.main.prefs.get("word_wrap", True):
            self.editor.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QTextEdit.NoWrap)

    def zoom_text(self, step: int):
        self.set_zoom(self.editor.zoom_percent + step * 10)

    def set_zoom(self, percent: int):
        percent = max(20, min(500, int(percent)))
        if percent == self.editor.zoom_percent:
            return

        old_dirty = self.doc.dirty
        old_cursor_pos = self.editor.textCursor().position()
        old_scroll = self.editor.verticalScrollBar().value()

        # Capture the unzoomed document before the first zoom step.
        if self.editor.zoom_percent == 100 or self._zoom_base_html is None:
            self._zoom_base_html = self.editor.toHtml()

        self.editor.zoom_percent = percent
        self._apply_document_zoom()

        # Restore cursor/scroll as closely as possible.
        cursor = self.editor.textCursor()
        cursor.setPosition(min(old_cursor_pos, len(self.editor.toPlainText())))
        self.editor.setTextCursor(cursor)
        self.editor.verticalScrollBar().setValue(old_scroll)

        self.doc.dirty = old_dirty
        self.apply_annotations()
        self.editor.viewport().update()
        self.main.refresh_tab_title(self)
        self.main.update_zoom_display()
        self.main.refresh_annotation_sidebars()
        self.main.status(f"Zoom: {percent}%")

    def _apply_document_zoom(self):
        """Scale the whole QTextDocument by changing actual char-format sizes.

        This works where QTextEdit.zoomIn()/zoomOut() and stylesheet font-size
        can fail because rich HTML often has explicit span-level font sizes.
        """
        if self._zoom_base_html is None:
            return

        self._applying_zoom = True
        self.editor.blockSignals(True)
        try:
            self.editor.setHtml(self._zoom_base_html)

            factor = self.editor.zoom_percent / 100.0
            default_size = float(self.main.prefs.get("font_size", 12))

            cursor = QTextCursor(self.editor.document())
            cursor.beginEditBlock()

            block = self.editor.document().firstBlock()
            while block.isValid():
                it = block.begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if fragment.isValid() and fragment.length() > 0:
                        fmt = QTextCharFormat(fragment.charFormat())
                        original_size = fmt.fontPointSize()
                        if original_size <= 0:
                            original_size = default_size
                        fmt.setFontPointSize(max(1.0, original_size * factor))

                        c = QTextCursor(self.editor.document())
                        c.setPosition(fragment.position())
                        c.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                        c.mergeCharFormat(fmt)
                    it += 1
                block = block.next()

            cursor.endEditBlock()
        finally:
            self.editor.blockSignals(False)
            self._applying_zoom = False
            self.editor.viewport().update()

    def zoom_text(self, step: int):
        self.set_zoom(self.editor.zoom_percent + step * 10)

    def apply_preferences(self):
        prefs = self.main.prefs
        base_font = QFont(prefs.get("font_family", "DejaVu Sans Mono"), int(prefs.get("font_size", 12)))
        self.editor.setFont(base_font)
        self.apply_wrap_mode()

        bg = prefs.get("background", "#000000")
        fg = prefs.get("foreground", "#ffffff")
        selection = prefs.get("selection", "#555555")

        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                color: {fg};
                selection-background-color: {selection};
                padding: 6px;
            }}
        """)

        self.update_line_number_area_width()

        if self.editor.zoom_percent != 100 and self._zoom_base_html is not None:
            self._apply_document_zoom()
        self.apply_annotations()
        self.editor.viewport().update()
        self.line_number_area.update()



class ExportDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("Export")
        self.resize(420, 220)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose what to export:"))

        self.kind = QComboBox()
        self.kind.addItems([
            "Plain text",
            "HTML",
            "AstroEditorPro AEP",
            "Highlighted text only",
            "Sticky notes only",
            "Highlights + notes report",
        ])
        layout.addWidget(self.kind)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Export...")
        buttons.accepted.connect(self.do_export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def do_export(self):
        tab = self.main.current_tab()
        if not tab:
            return

        kind = self.kind.currentText()
        suffix = ".txt"
        filters = "Text file (*.txt);;All files (*)"
        if kind == "HTML":
            suffix = ".html"
            filters = "HTML file (*.html);;All files (*)"
        elif kind == "AstroEditorPro AEP":
            suffix = ".aep"
            filters = "AstroEditorPro self-contained file (*.aep);;All files (*)"

        path, _ = QFileDialog.getSaveFileName(self, "Export", str(Path.home() / ("export" + suffix)), filters)
        if not path:
            return

        p = Path(path)
        try:
            if kind == "Plain text":
                p.write_text(tab.editor.toPlainText(), encoding="utf-8")
            elif kind == "HTML":
                p.write_text(tab.editor.toHtml(), encoding="utf-8")
            elif kind == "AstroEditorPro AEP":
                save_json(p, tab.html_payload())
            elif kind == "Highlighted text only":
                texts = [tab.annotation_text(a).strip() for a in tab.doc.annotations if a.get("kind") == "highlight"]
                p.write_text("\n\n".join(t for t in texts if t), encoding="utf-8")
            elif kind == "Sticky notes only":
                notes = []
                for ann in tab.doc.annotations:
                    if ann.get("kind") == "note":
                        marked = tab.annotation_text(ann).strip()
                        notes.append(f"{marked}\n{ann.get('note','')}".strip())
                p.write_text("\n\n".join(notes), encoding="utf-8")
            else:
                lines = []
                for ann in tab.doc.annotations:
                    if ann.get("kind") == "highlight":
                        lines.append("[HIGHLIGHT]\n" + tab.annotation_text(ann).strip())
                    elif ann.get("kind") == "note":
                        lines.append("[NOTE]\nText: " + tab.annotation_text(ann).strip() + "\nNote: " + ann.get("note", ""))
                p.write_text("\n\n".join(lines), encoding="utf-8")

            self.main.status(f"Exported: {p}")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))


class SpellcheckLanguagesDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("Spellcheck languages")
        self.resize(650, 620)
        self.checkboxes = {}

        root = QVBoxLayout(self)
        intro = QLabel(
            "Select any number of Hunspell dictionaries for spellcheck. "
            "User-added words in the custom dictionary are always accepted first."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.user_dict_label = QLabel()
        self.user_dict_label.setWordWrap(True)
        root.addWidget(self.user_dict_label)

        user_row = QHBoxLayout()
        open_user_dict = QPushButton("Open custom dictionary")
        reload_user_dict = QPushButton("Reload custom dictionary")
        user_row.addWidget(open_user_dict)
        user_row.addWidget(reload_user_dict)
        root.addLayout(user_row)
        open_user_dict.clicked.connect(self.open_custom_dictionary)
        reload_user_dict.clicked.connect(self.reload_custom_dictionary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid = QGridLayout(container)
        scroll.setWidget(container)
        root.addWidget(scroll)

        self.populate_language_grid()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.refresh_user_dict_label()

    def all_language_codes(self):
        installed = set(SpellCheckerManager.installed_language_codes())
        common = set(COMMON_HUNSPELL_LANGUAGES.keys())
        selected = set(self.main.prefs.get("spellcheck_languages", SPELLCHECK_LANGUAGES))
        return sorted(installed | common | selected, key=lambda c: language_display_name(c).lower())

    def populate_language_grid(self):
        selected = set(self.main.prefs.get("spellcheck_languages", SPELLCHECK_LANGUAGES))
        row = 0
        self.grid.addWidget(QLabel("<b>Use</b>"), row, 0)
        self.grid.addWidget(QLabel("<b>Language</b>"), row, 1)
        self.grid.addWidget(QLabel("<b>Status</b>"), row, 2)
        self.grid.addWidget(QLabel("<b>Action</b>"), row, 3)
        row += 1

        for code in self.all_language_codes():
            installed = SpellCheckerManager.has_dictionary(code)
            checkbox = QCheckBox()
            checkbox.setChecked(code in selected and installed)
            checkbox.toggled.connect(lambda checked, lang=code: self.language_toggled(lang, checked))
            name = QLabel(f"{language_display_name(code)} <span style='color:#888'>({code})</span>")
            status = QLabel("Installed" if installed else "Missing")
            status.setStyleSheet("color: #70c070;" if installed else "color: #d0a030;")
            install_btn = QPushButton("Install..." if not installed else "Reinstall...")
            install_btn.clicked.connect(lambda checked=False, lang=code: self.install_language(lang))
            self.grid.addWidget(checkbox, row, 0)
            self.grid.addWidget(name, row, 1)
            self.grid.addWidget(status, row, 2)
            self.grid.addWidget(install_btn, row, 3)
            self.checkboxes[code] = checkbox
            row += 1

    def language_toggled(self, lang, checked):
        if not checked or SpellCheckerManager.has_dictionary(lang):
            return

        box = self.checkboxes.get(lang)
        if box:
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)

        answer = QMessageBox.question(
            self,
            "Dictionary missing",
            f"No Hunspell dictionary was found for {language_display_name(lang)} ({lang}).\n\n"
            f"Try to install package '{language_package_name(lang)}' now?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes and self.install_language(lang):
            box = self.checkboxes.get(lang)
            if box and SpellCheckerManager.has_dictionary(lang):
                box.blockSignals(True)
                box.setChecked(True)
                box.blockSignals(False)

    def terminal_command(self):
        for term in [
            ["x-terminal-emulator", "-e"],
            ["gnome-terminal", "--"],
            ["konsole", "-e"],
            ["xfce4-terminal", "-e"],
            ["mate-terminal", "-e"],
        ]:
            if shutil.which(term[0]):
                return term
        return None

    def install_language(self, lang):
        package = language_package_name(lang)
        command = f"sudo apt-get update; sudo apt-get install -y hunspell {package}; echo; read -p 'Press Enter to return to AstroEditorPro...'"
        term = self.terminal_command()
        if term:
            try:
                subprocess.run(term + ["bash", "-lc", command], check=False)
            except Exception as exc:
                QMessageBox.critical(self, "Install failed", str(exc))
                return False
        else:
            QMessageBox.information(
                self,
                "Manual install needed",
                "No terminal emulator was found.\n\n"
                f"Run this manually:\n\nsudo apt-get install hunspell {package}"
            )
            return False

        self.main.spellchecker.reload(self.main.prefs.get("spellcheck_languages", []))
        if SpellCheckerManager.has_dictionary(lang):
            QMessageBox.information(self, "Dictionary installed", f"{language_display_name(lang)} dictionary is now available.")
            return True

        QMessageBox.warning(
            self,
            "Dictionary still missing",
            f"The dictionary for {language_display_name(lang)} was not found after installation.\n\n"
            f"Expected files in {SPELLCHECK_DICTIONARY_DIR}:\n{lang}.aff\n{lang}.dic"
        )
        return False

    def refresh_user_dict_label(self):
        path = Path(SPELLCHECK_USER_DICTIONARY).expanduser()
        count = len(self.main.spellchecker.user_words)
        self.user_dict_label.setText(f"Custom dictionary: {path}\nWords stored: {count}")

    def open_custom_dictionary(self):
        path = Path(SPELLCHECK_USER_DICTIONARY).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        self.main.open_file(str(path))
        self.accept()

    def reload_custom_dictionary(self):
        self.main.spellchecker.load_user_dictionary()
        self.refresh_user_dict_label()
        self.main.apply_spellcheck_preference()

    def apply(self):
        selected = []
        for code, box in self.checkboxes.items():
            if box.isChecked() and SpellCheckerManager.has_dictionary(code):
                selected.append(code)
        self.main.prefs["spellcheck_languages"] = selected
        if selected:
            self.main.prefs["spellcheck_enabled"] = True
        self.main.save_preferences()
        self.main.spellchecker.reload(selected)
        self.main.apply_spellcheck_preference()
        self.accept()


class PreferencesDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("Preferences")
        self.resize(650, 440)

        self.bg = QColor(main.prefs.get("background", "#000000"))
        self.fg = QColor(main.prefs.get("foreground", "#ffffff"))
        self.sel = QColor(main.prefs.get("selection", "#555555"))

        root = QVBoxLayout(self)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font:"))
        self.font_box = QFontComboBox()
        self.font_box.setCurrentFont(QFont(main.prefs.get("font_family", "DejaVu Sans Mono")))
        font_row.addWidget(self.font_box)

        font_row.addWidget(QLabel("Size:"))
        self.size_box = QSpinBox()
        self.size_box.setRange(6, 96)
        self.size_box.setValue(int(main.prefs.get("font_size", 12)))
        font_row.addWidget(self.size_box)
        root.addLayout(font_row)

        self.wrap_checkbox = QCheckBox("Enable text wrapping")
        self.wrap_checkbox.setChecked(bool(main.prefs.get("word_wrap", True)))
        root.addWidget(self.wrap_checkbox)

        self.line_numbers_checkbox = QCheckBox("Show line numbers")
        self.line_numbers_checkbox.setChecked(bool(main.prefs.get("show_line_numbers", True)))
        root.addWidget(self.line_numbers_checkbox)

        self.spellcheck_checkbox = QCheckBox("Enable spellcheck")
        self.spellcheck_checkbox.setChecked(bool(main.prefs.get("spellcheck_enabled", False)))
        root.addWidget(self.spellcheck_checkbox)

        spell_row = QHBoxLayout()
        self.spell_lang_label = QLabel(self.language_summary())
        self.spell_lang_label.setWordWrap(True)
        self.spell_lang_btn = QPushButton("Spellcheck languages...")
        spell_row.addWidget(self.spell_lang_label, 1)
        spell_row.addWidget(self.spell_lang_btn)
        root.addLayout(spell_row)
        self.spell_lang_btn.clicked.connect(self.open_spellcheck_languages)

        colour_row = QHBoxLayout()
        self.bg_btn = QPushButton("Background...")
        self.fg_btn = QPushButton("Text colour...")
        self.sel_btn = QPushButton("Selection colour...")
        colour_row.addWidget(self.bg_btn)
        colour_row.addWidget(self.fg_btn)
        colour_row.addWidget(self.sel_btn)
        root.addLayout(colour_row)

        self.bg_btn.clicked.connect(lambda: self.pick_colour("bg"))
        self.fg_btn.clicked.connect(lambda: self.pick_colour("fg"))
        self.sel_btn.clicked.connect(lambda: self.pick_colour("sel"))

        self.preview = QTextEdit()
        self.preview.setPlainText("The quick brown fox jumps over the lazy dog.\n0123456789 ČĆŽŠĐ čćžšđ")
        root.addWidget(self.preview)

        info = QLabel(f"Fonts folder path set in code:\n{FONTS_DIR}")
        info.setWordWrap(True)
        root.addWidget(info)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.font_box.currentFontChanged.connect(self.update_preview)
        self.size_box.valueChanged.connect(self.update_preview)
        self.update_preview()

    def language_summary(self):
        selected = self.main.prefs.get("spellcheck_languages", SPELLCHECK_LANGUAGES)
        if not selected:
            return "Spellcheck languages: none selected"
        names = [language_display_name(code) for code in selected]
        return "Spellcheck languages: " + ", ".join(names)

    def open_spellcheck_languages(self):
        dlg = SpellcheckLanguagesDialog(self.main)
        dlg.exec()
        self.spell_lang_label.setText(self.language_summary())

    def pick_colour(self, which):
        current = {"bg": self.bg, "fg": self.fg, "sel": self.sel}[which]
        dlg = QColorDialog(current, self)
        dlg.setOption(QColorDialog.ShowAlphaChannel, False)
        dlg.setWindowTitle("Choose colour")
        if dlg.exec():
            chosen = dlg.selectedColor()
            if chosen.isValid():
                if which == "bg":
                    self.bg = chosen
                elif which == "fg":
                    self.fg = chosen
                else:
                    self.sel = chosen
                self.update_preview()

    def update_preview(self):
        font = self.font_box.currentFont()
        font.setPointSize(self.size_box.value())
        self.preview.setFont(font)
        self.preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.bg.name()};
                color: {self.fg.name()};
                selection-background-color: {self.sel.name()};
            }}
        """)

    def apply(self):
        self.main.prefs["font_family"] = self.font_box.currentFont().family()
        self.main.prefs["font_size"] = self.size_box.value()
        self.main.prefs["background"] = self.bg.name()
        self.main.prefs["foreground"] = self.fg.name()
        self.main.prefs["selection"] = self.sel.name()
        self.main.prefs["word_wrap"] = self.wrap_checkbox.isChecked()
        self.main.prefs["show_line_numbers"] = self.line_numbers_checkbox.isChecked()
        self.main.prefs["spellcheck_enabled"] = self.spellcheck_checkbox.isChecked()
        self.main.save_preferences()
        self.main.apply_preferences()
        self.main.apply_spellcheck_preference()
        self.accept()


class FindBar(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        layout.addWidget(QLabel("Find:"))
        self.find_text = QLineEdit()
        layout.addWidget(self.find_text)

        self.next_btn = QPushButton("Next")
        layout.addWidget(self.next_btn)

        layout.addWidget(QLabel("Replace:"))
        self.replace_text = QLineEdit()
        layout.addWidget(self.replace_text)

        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")
        self.close_btn = QPushButton("Close")
        layout.addWidget(self.replace_btn)
        layout.addWidget(self.replace_all_btn)
        layout.addWidget(self.close_btn)

        self.next_btn.clicked.connect(self.find_next)
        self.find_text.returnPressed.connect(self.find_next)
        self.replace_btn.clicked.connect(self.replace_one)
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.close_btn.clicked.connect(self.hide)

        self.hide()

    def show_find(self, replace=False):
        self.show()
        if replace:
            self.replace_text.setFocus()
        else:
            self.find_text.setFocus()

    def current_editor(self):
        tab = self.main.current_tab()
        return tab.editor if tab else None

    def find_next(self):
        editor = self.current_editor()
        needle = self.find_text.text()
        if not editor or not needle:
            return
        if not editor.find(needle):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)
            editor.find(needle)

    def replace_one(self):
        editor = self.current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replace_text.text())
        self.find_next()

    def replace_all(self):
        editor = self.current_editor()
        needle = self.find_text.text()
        repl = self.replace_text.text()
        if not editor or not needle:
            return

        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)

        count = 0
        while editor.find(needle):
            c = editor.textCursor()
            c.insertText(repl)
            count += 1

        cursor.endEditBlock()
        self.main.status(f"Replaced {count} occurrence(s).")




class CropImageDialog(QDialog):
    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop image")
        self.original = image
        self.result_image = None

        self._dragging = False
        self._start_pos = QPoint()
        self._end_pos = QPoint()
        self.crop_rect = None

        layout = QVBoxLayout(self)

        info = QLabel("Press, drag, and release once to draw the crop rectangle. Then click Crop.")
        layout.addWidget(info)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setMouseTracking(True)
        self.image_label.setMinimumSize(self.pixmap.size())

        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.image_label)

        self.image_label.mousePressEvent = self.mouse_press
        self.image_label.mouseMoveEvent = self.mouse_move
        self.image_label.mouseReleaseEvent = self.mouse_release

        layout.addWidget(self.image_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Crop")
        buttons.accepted.connect(self.crop)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clamp_to_pixmap(self, point):
        x = max(0, min(point.x(), self.pixmap.width() - 1))
        y = max(0, min(point.y(), self.pixmap.height() - 1))
        return QPoint(x, y)

    def _rect_from_points(self, p1, p2):
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        return self.pixmap.rect().intersected(
            QRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        )

    def mouse_press(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = True
        self._start_pos = self._clamp_to_pixmap(event.position().toPoint())
        self._end_pos = self._start_pos
        self.crop_rect = None
        self.rubber_band.setGeometry(self._start_pos.x(), self._start_pos.y(), 0, 0)
        self.rubber_band.show()
        event.accept()

    def mouse_move(self, event):
        if not self._dragging:
            return
        self._end_pos = self._clamp_to_pixmap(event.position().toPoint())
        rect = self._rect_from_points(self._start_pos, self._end_pos)
        self.rubber_band.setGeometry(rect)
        event.accept()

    def mouse_release(self, event):
        if event.button() != Qt.LeftButton or not self._dragging:
            return
        self._dragging = False
        self._end_pos = self._clamp_to_pixmap(event.position().toPoint())
        self.crop_rect = self._rect_from_points(self._start_pos, self._end_pos)
        self.rubber_band.setGeometry(self.crop_rect)
        self.rubber_band.show()
        event.accept()

    def crop(self):
        if not self.crop_rect or self.crop_rect.width() < 2 or self.crop_rect.height() < 2:
            QMessageBox.information(self, "No crop selected", "Press, drag, and release to draw a crop rectangle first.")
            return

        rect = self.crop_rect.intersected(self.pixmap.rect())
        if rect.isEmpty():
            QMessageBox.information(self, "Invalid crop", "The crop rectangle is outside the image.")
            return

        self.result_crop_rect = rect
        self.result_image = self.original.copy(rect)
        self.accept()


class CopyStoragePopup(QFrame):
    def __init__(self, main):
        super().__init__(main, Qt.Popup)
        self.main = main
        self.setFrameShape(QFrame.StyledPanel)
        self.setWindowTitle("Copy Storage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(360)
        self.list_widget.setMaximumHeight(260)
        self.list_widget.itemActivated.connect(self.paste_current)
        layout.addWidget(self.list_widget)

        hint = QLabel("↑/↓ to choose, Enter to paste, Esc to close")
        hint.setStyleSheet("color: #777; padding: 2px;")
        layout.addWidget(hint)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.paste_current()
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def populate(self):
        self.list_widget.clear()

        clear_item = QListWidgetItem("Clear copy storage")
        clear_item.setData(Qt.UserRole, "__CLEAR_COPY_STORAGE__")
        clear_item.setToolTip("Remove all stored copy blocks.")
        self.list_widget.addItem(clear_item)

        for i, entry in enumerate(self.main.copy_storage):
            preview = block_preview(entry.get("text", ""))
            item = QListWidgetItem(f"{i + 1}. {preview}")
            item.setData(Qt.UserRole, entry.get("text", ""))
            tooltip = entry.get("text", "")
            if len(tooltip) > 1000:
                tooltip = tooltip[:1000] + "..."
            item.setToolTip(tooltip)
            self.list_widget.addItem(item)

        # Clear storage stays at the top, but keyboard selection starts on
        # the first saved copy block below it.
        if self.list_widget.count() > 1:
            self.list_widget.setCurrentRow(1)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def open_near_cursor(self):
        self.populate()
        if not self.main.copy_storage:
            self.main.status("Copy storage is empty.")
            # Still show the popup with the clear command hidden? No: there
            # is nothing useful to clear or paste.
            return

        tab = self.main.current_tab()
        if tab:
            rect = tab.editor.cursorRect()
            global_pos = tab.editor.mapToGlobal(rect.bottomLeft())
        else:
            global_pos = self.main.mapToGlobal(self.main.rect().center())

        self.move(global_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        self.list_widget.setFocus()

    def paste_current(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        value = item.data(Qt.UserRole)
        if value == "__CLEAR_COPY_STORAGE__":
            self.main.clear_copy_storage()
            self.hide()
            return
        self.main.insert_copy_block(value)
        self.hide()


class ShortcutsEditor(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(720, 520)

        layout = QVBoxLayout(self)
        info = QLabel(
            "Edit the shortcuts file below. Save and close to apply changes.\n"
            "Examples: Ctrl+B, Ctrl+Shift+S, Alt+F, F5."
        )
        layout.addWidget(info)

        self.editor = QPlainTextEdit()
        self.path = Path(SHORTCUTS_FILE).expanduser()
        if not self.path.exists():
            write_default_shortcuts(str(self.path))
        self.editor.setPlainText(self.path.read_text(encoding="utf-8"))
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Save).clicked.connect(self.save)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self.main.reload_shortcuts()
        self.main.status("Shortcuts saved and applied.")
        self.accept()


class MainWindow(QMainWindow):
    @staticmethod
    def normalize_startup_path_static(raw_path):
        if raw_path is None:
            return None
        raw = str(raw_path).strip()
        if not raw:
            return None
        if raw.startswith("file://"):
            from urllib.parse import unquote, urlparse
            raw = unquote(urlparse(raw).path)

        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        try:
            return p.resolve()
        except Exception:
            return p

    def __init__(self, startup_files=None, restore_session=True):
        super().__init__()

        self.restore_session = restore_session
        self.window_id = f"{os.getpid()}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setProperty("desktopFileName", APP_DESKTOP_ID)

        icon_path = Path(APP_ICON_PATH)
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.startup_files = []
        for raw in (startup_files or []):
            p = self.normalize_startup_path_static(raw)
            if p is not None:
                self.startup_files.append(str(p))

        if self.startup_files:
            print(f"AstroEditor normalized startup files: {self.startup_files}", flush=True)
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1100, 760)

        self.prefs_path = BASE_DIR / PREFS_FILE
        self.state_path = BASE_DIR / STATE_FILE
        self.recent_path = BASE_DIR / RECENT_FILE
        self.copy_storage_path = BASE_DIR / COPY_STORAGE_FILE
        self.copy_storage = load_json(self.copy_storage_path, [])

        self.prefs = load_json(self.prefs_path, {
            "background": "#000000",
            "foreground": "#ffffff",
            "selection": "#555555",
            "line_number_color": "#888888",
            "font_family": "DejaVu Sans Mono",
            "font_size": 12,
            "word_wrap": True,
            "show_line_numbers": True,
            "spellcheck_enabled": False,
            "spellcheck_languages": SPELLCHECK_LANGUAGES,
            "last_file_folder": str(Path.home()),
        })

        self.spellchecker = SpellCheckerManager([])
        self.spellchecker.enabled = False

        self.shortcuts_path = Path(SHORTCUTS_FILE).expanduser()
        self.shortcuts = parse_shortcuts(str(self.shortcuts_path))
        self.shortcut_actions = {}
        self._updating_toolbar = False
        self.current_annotation_mode = "text"

        # Snapshot undo/redo.
        # A snapshot is committed on every save/autosave boundary. Ctrl+Z
        # restores the previous snapshot, so text + highlights + notes always
        # move together as one coherent document state.
        self.snapshot_undo_stack = []
        self.snapshot_redo_stack = []
        self._restoring_snapshot = False

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(lambda _i: (self.update_format_buttons(), self.refresh_annotation_sidebars(), self.refresh_outline(), self.refresh_bookmarks_sidebar(), self.refresh_split_view()))

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.tabs)

        self.find_bar = FindBar(self)
        wrapper_layout.addWidget(self.find_bar)
        self.setCentralWidget(wrapper)

        self.copy_popup = CopyStoragePopup(self)

        self.statusBar().showMessage("Ready.")

        self.create_pro_panels()
        self.create_actions_and_menu()
        self.load_state_or_new()
        self.reload_shortcuts()

        self.shortcut_watcher = QFileSystemWatcher(self)
        if self.shortcuts_path.exists():
            self.shortcut_watcher.addPath(str(self.shortcuts_path))
        self.shortcut_watcher.fileChanged.connect(lambda _p: self.reload_shortcuts())

    def save_copy_storage(self):
        # Keep newest first, avoid duplicates, and prevent unbounded growth.
        cleaned = []
        seen = set()
        for entry in self.copy_storage:
            text = normalize_block_text(entry.get("text", ""))
            if not text.strip() or text in seen:
                continue
            seen.add(text)
            cleaned.append({
                "text": text,
                "created_at": entry.get("created_at") or datetime.now().isoformat(timespec="seconds"),
            })
        self.copy_storage = cleaned[:200]
        save_json(self.copy_storage_path, self.copy_storage)

    def clear_copy_storage(self):
        if not self.copy_storage:
            self.status("Copy storage is already empty.")
            return

        answer = QMessageBox.question(
            self,
            "Clear copy storage",
            "Clear all stored copy blocks?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.copy_storage = []
        self.save_copy_storage()
        self.status("Copy storage cleared.")

    def store_selected_copy_block(self):
        tab = self.current_tab()
        if not tab:
            return
        cursor = tab.editor.textCursor()
        if not cursor.hasSelection():
            self.status("Select text first to store it in copy storage.")
            return

        text = normalize_block_text(cursor.selectedText())
        if not text.strip():
            self.status("Empty selection was not stored.")
            return

        # Newest first. If already present, move it to the top.
        self.copy_storage = [entry for entry in self.copy_storage if entry.get("text") != text]
        self.copy_storage.insert(0, {
            "text": text,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        self.save_copy_storage()
        self.status(f"Stored copy block: {block_preview(text)}")

    def open_copy_storage_popup(self):
        self.copy_popup.open_near_cursor()

    def insert_copy_block(self, text: str):
        tab = self.current_tab()
        if not tab:
            return
        text = normalize_block_text(text or "")
        cursor = tab.editor.textCursor()
        cursor.insertText(text)
        tab.editor.setTextCursor(cursor)
        tab.doc.dirty = True
        self.refresh_tab_title(tab)
        tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
        self.status(f"Pasted copy block: {block_preview(text)}")


    def selected_image_format_and_cursor(self):
        tab = self.current_tab()
        if not tab:
            return None, None

        cursor = tab.editor.textCursor()
        doc = tab.editor.document()

        def cursor_for_image_at(pos):
            if pos < 0 or pos >= doc.characterCount():
                return None, None

            # QTextEdit embedded images live as one object-replacement
            # character. The image format is most reliably found by selecting
            # that one character and inspecting the selection format.
            c = QTextCursor(doc)
            c.setPosition(pos)
            c.setPosition(pos + 1, QTextCursor.KeepAnchor)
            fmt = c.charFormat()
            if fmt.isImageFormat():
                delete_cursor = QTextCursor(doc)
                delete_cursor.setPosition(pos)
                return QTextImageFormat(fmt), delete_cursor

            # Fallback: sometimes charFormat() is visible one position after
            # the object depending on cursor placement.
            c2 = QTextCursor(doc)
            c2.setPosition(pos)
            fmt2 = c2.charFormat()
            if fmt2.isImageFormat():
                delete_cursor = QTextCursor(doc)
                delete_cursor.setPosition(pos)
                return QTextImageFormat(fmt2), delete_cursor

            return None, None

        # Case 1: selected image object.
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            for pos in range(start, end):
                fmt, del_cursor = cursor_for_image_at(pos)
                if fmt is not None:
                    return fmt, del_cursor

        # Case 2: cursor is directly adjacent to an image.
        positions = [
            cursor.position() - 1,
            cursor.position(),
            cursor.position() + 1,
            cursor.position() - 2,
            cursor.position() + 2,
        ]
        for pos in positions:
            fmt, del_cursor = cursor_for_image_at(pos)
            if fmt is not None:
                return fmt, del_cursor

        return None, None

    def image_display_size(self, fmt: QTextImageFormat):
        image = load_image_from_document_name(fmt.name())
        width = int(fmt.width()) if fmt.width() > 0 else image.width()
        height = int(fmt.height()) if fmt.height() > 0 else image.height()
        return width, height, image.width(), image.height()

    def refresh_image_size_controls(self):
        if getattr(self, "_updating_image_size_controls", False):
            return

        fmt, _cursor = self.selected_image_format_and_cursor()
        self._updating_image_size_controls = True
        try:
            if fmt is None:
                self.image_width_spin.setSpecialValueText("auto")
                self.image_height_spin.setSpecialValueText("auto")
                self.image_width_spin.setValue(0)
                self.image_height_spin.setValue(0)
                self._current_image_aspect = None
                return

            width, height, _natural_w, _natural_h = self.image_display_size(fmt)
            self._current_image_aspect = width / height if height else None
            self.image_width_spin.setSpecialValueText("")
            self.image_height_spin.setSpecialValueText("")
            self.image_width_spin.setValue(width)
            self.image_height_spin.setValue(height)
        except Exception:
            self._current_image_aspect = None
        finally:
            self._updating_image_size_controls = False

    def image_width_changed(self, value):
        if getattr(self, "_updating_image_size_controls", False):
            return
        if not getattr(self, "_lock_image_aspect", True):
            return
        aspect = getattr(self, "_current_image_aspect", None)
        if not aspect or value <= 0:
            return
        self._updating_image_size_controls = True
        try:
            self.image_height_spin.setValue(max(1, int(round(value / aspect))))
        finally:
            self._updating_image_size_controls = False

    def image_height_changed(self, value):
        if getattr(self, "_updating_image_size_controls", False):
            return
        if not getattr(self, "_lock_image_aspect", True):
            return
        aspect = getattr(self, "_current_image_aspect", None)
        if not aspect or value <= 0:
            return
        self._updating_image_size_controls = True
        try:
            self.image_width_spin.setValue(max(1, int(round(value * aspect))))
        finally:
            self._updating_image_size_controls = False

    def replace_selected_image(self, image_path: str, width=None, height=None):
        tab = self.current_tab()
        if not tab:
            return

        old_fmt, cursor = self.selected_image_format_and_cursor()
        if old_fmt is None or cursor is None:
            self.status("Select an image first.")
            return

        doc = tab.editor.document()
        insert_pos = cursor.position()

        new_fmt = QTextImageFormat()
        new_fmt.setName(image_path)
        if width and width > 0:
            new_fmt.setWidth(width)
        if height and height > 0:
            new_fmt.setHeight(height)

        cursor.beginEditBlock()

        # Force deletion of exactly one embedded image object. This is more
        # reliable than removeSelectedText(), which may leave the image object
        # behind depending on how QTextEdit reports the selection.
        cursor.setPosition(insert_pos)
        cursor.deleteChar()

        # Insert the replacement at precisely the same document position.
        cursor.setPosition(insert_pos)
        cursor.insertImage(new_fmt)

        cursor.endEditBlock()

        # Select the newly inserted image object and leave the cursor after it
        # when the user next types/clicks.
        new_cursor = QTextCursor(doc)
        new_cursor.setPosition(insert_pos)
        new_cursor.setPosition(insert_pos + 1, QTextCursor.KeepAnchor)
        tab.editor.setTextCursor(new_cursor)

        tab.doc.dirty = True
        self.refresh_tab_title(tab)
        tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
        self.refresh_image_size_controls()
        self.status("Image updated.")

    def rotate_selected_image(self, degrees: int):
        fmt, cursor = self.selected_image_format_and_cursor()
        if fmt is None:
            self.status("Select an image first.")
            return

        try:
            display_w, display_h, _natural_w, _natural_h = self.image_display_size(fmt)
            image = load_image_from_document_name(fmt.name())
            transform = QTransform().rotate(degrees)
            rotated = image.transformed(transform, Qt.SmoothTransformation)
            path = save_qimage(rotated, prefix="rotated_image")

            # For 90° rotations, swap displayed width/height so the visual size
            # follows the rotated image instead of stretching it.
            if abs(degrees) % 180 == 90:
                self.replace_selected_image(path, width=display_h, height=display_w)
            else:
                self.replace_selected_image(path, width=display_w, height=display_h)

            self.status(f"Image rotated {degrees}°.")
        except Exception as exc:
            QMessageBox.critical(self, "Image rotation failed", str(exc))

    def crop_selected_image(self):
        fmt, cursor = self.selected_image_format_and_cursor()
        if fmt is None:
            self.status("Select an image first.")
            return

        try:
            display_w, display_h, natural_w, natural_h = self.image_display_size(fmt)
            image = load_image_from_document_name(fmt.name())
            dlg = CropImageDialog(image, self)
            if dlg.exec() and dlg.result_image is not None:
                path = save_qimage(dlg.result_image, prefix="cropped_image")

                rect = getattr(dlg, "result_crop_rect", None)
                if rect is not None and natural_w > 0 and natural_h > 0:
                    # Preserve the scale the user was seeing before cropping.
                    # Example: if a 2000 px image is displayed as 500 px wide,
                    # a 1000 px crop should display as 250 px wide.
                    new_w = max(1, int(round(display_w * rect.width() / natural_w)))
                    new_h = max(1, int(round(display_h * rect.height() / natural_h)))
                else:
                    new_w = dlg.result_image.width()
                    new_h = dlg.result_image.height()

                self.replace_selected_image(path, width=new_w, height=new_h)
                self.status(f"Image cropped to displayed size {new_w} × {new_h}.")
        except Exception as exc:
            QMessageBox.critical(self, "Image crop failed", str(exc))

    def set_selected_image_size(self):
        fmt, cursor = self.selected_image_format_and_cursor()
        if fmt is None:
            self.status("Select an image first.")
            return

        try:
            image = load_image_from_document_name(fmt.name())
            current_w = int(fmt.width()) if fmt.width() > 0 else image.width()
            current_h = int(fmt.height()) if fmt.height() > 0 else image.height()
            w = self.image_width_spin.value()
            h = self.image_height_spin.value()
            if w <= 0:
                w = current_w
            if h <= 0:
                h = current_h
            self.replace_selected_image(fmt.name(), width=w, height=h)
            self.refresh_image_size_controls()
            self.status(f"Image size set to {w} × {h}.")
        except Exception as exc:
            QMessageBox.critical(self, "Image resize failed", str(exc))

    def scale_selected_image(self):
        fmt, cursor = self.selected_image_format_and_cursor()
        if fmt is None:
            self.status("Select an image first.")
            return

        try:
            image = load_image_from_document_name(fmt.name())
            current_w = int(fmt.width()) if fmt.width() > 0 else image.width()
            current_h = int(fmt.height()) if fmt.height() > 0 else image.height()
            scale = self.image_scale_spin.value() / 100.0
            new_w = max(1, int(round(current_w * scale)))
            new_h = max(1, int(round(current_h * scale)))
            self.replace_selected_image(fmt.name(), width=new_w, height=new_h)
            self.refresh_image_size_controls()
            self.status(f"Image scaled to {new_w} × {new_h}.")
        except Exception as exc:
            QMessageBox.critical(self, "Image scale failed", str(exc))


    def document_snapshot(self, tab):
        if not tab:
            return None

        html = tab._zoom_base_html if (
            getattr(tab.editor, "zoom_percent", 100) != 100
            and getattr(tab, "_zoom_base_html", None) is not None
        ) else tab.editor.toHtml()

        cursor = tab.editor.textCursor()
        return {
            "tab": tab,
            "html": html,
            "plain": tab.editor.toPlainText(),
            "annotations": [dict(a) for a in tab.doc.annotations],
            "cursor_position": cursor.position(),
            "zoom_percent": getattr(tab.editor, "zoom_percent", 100),
        }

    def snapshots_equal(self, a, b):
        if not a or not b:
            return False
        return (
            a.get("plain") == b.get("plain")
            and a.get("html") == b.get("html")
            and a.get("annotations") == b.get("annotations")
        )

    def commit_snapshot_boundary(self, tab, reason="autosave"):
        if getattr(self, "_restoring_snapshot", False):
            return
        snap = self.document_snapshot(tab)
        if snap is None:
            return

        if not self.snapshot_undo_stack:
            self.snapshot_undo_stack.append(snap)
            return

        if self.snapshots_equal(self.snapshot_undo_stack[-1], snap):
            return

        self.snapshot_undo_stack.append(snap)
        self.snapshot_redo_stack.clear()
        if len(self.snapshot_undo_stack) > 200:
            self.snapshot_undo_stack.pop(0)

    def restore_snapshot(self, snap):
        if not snap:
            return
        tab = snap.get("tab")
        if not tab:
            return

        self._restoring_snapshot = True
        try:
            tab.editor.blockSignals(True)
            tab.editor.setHtml(snap.get("html", ""))
            tab.editor.zoom_percent = int(snap.get("zoom_percent", 100))
            tab._zoom_base_html = None
            tab.editor.blockSignals(False)

            tab.doc.annotations = [dict(a) for a in snap.get("annotations", [])]
            tab.doc.dirty = True

            cursor = tab.editor.textCursor()
            pos = max(0, min(int(snap.get("cursor_position", 0)), tab.editor.document().characterCount() - 1))
            cursor.setPosition(pos)
            tab.editor.setTextCursor(cursor)

            tab.apply_annotations()
            tab.editor.viewport().update()
            self.refresh_tab_title(tab)
            self.refresh_annotation_sidebars()
            tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
            self.tabs.setCurrentWidget(tab)
        finally:
            self._restoring_snapshot = False

    def undo_action(self):
        tab = self.current_tab()
        if not tab:
            return

        current = self.document_snapshot(tab)

        # Ensure current unsaved state exists as the top boundary before moving back.
        if current and (not self.snapshot_undo_stack or not self.snapshots_equal(self.snapshot_undo_stack[-1], current)):
            self.snapshot_undo_stack.append(current)

        if len(self.snapshot_undo_stack) <= 1:
            self.status("Nothing to undo.")
            return

        current_top = self.snapshot_undo_stack.pop()
        self.snapshot_redo_stack.append(current_top)
        previous = self.snapshot_undo_stack[-1]
        self.restore_snapshot(previous)
        self.status("Restored previous autosave/save step.")

    def redo_action(self):
        if not self.snapshot_redo_stack:
            self.status("Nothing to redo.")
            return

        snap = self.snapshot_redo_stack.pop()
        self.snapshot_undo_stack.append(snap)
        self.restore_snapshot(snap)
        self.status("Restored next autosave/save step.")

    def validate_annotations_after_text_change(self, tab):
        """Remove or move annotations whose underlying marked text changed.

        If the exact annotated text still exists at the saved range, keep it.
        If it moved because text before it changed, relocate it to the nearest
        matching occurrence. If the exact text no longer exists, remove the
        annotation.
        """
        if not tab or not getattr(tab.doc, "annotations", None):
            return

        plain = tab.editor.toPlainText()
        changed = False
        kept = []

        for ann in tab.doc.annotations:
            expected = ann.get("text")
            if not expected:
                # Older annotations may lack stored text; initialize it from
                # their current range rather than deleting immediately.
                expected = tab.annotation_text(ann)
                ann["text"] = expected

            if not expected:
                changed = True
                continue

            start = int(ann.get("start", 0))
            end = int(ann.get("end", start))

            if 0 <= start <= end <= len(plain) and plain[start:end] == expected:
                kept.append(ann)
                continue

            # Try to relocate the same text, choosing the occurrence nearest
            # to the old start position. This avoids deleting annotations just
            # because text was inserted/removed before them.
            positions = []
            search_from = 0
            while True:
                found = plain.find(expected, search_from)
                if found == -1:
                    break
                positions.append(found)
                search_from = found + max(1, len(expected))

            if positions:
                nearest = min(positions, key=lambda p: abs(p - start))
                ann["start"] = nearest
                ann["end"] = nearest + len(expected)
                kept.append(ann)
                changed = True
            else:
                changed = True

        if changed:
            tab.doc.annotations = kept
            tab.apply_annotations()
            tab.editor.viewport().update()
            self.refresh_annotation_sidebars()

    def add_word_to_user_dictionary(self, word):
        self.spellchecker.add_user_word(word)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab):
                tab.run_spellcheck()
        self.status(f"Added '{word}' to user dictionary.")

    def replace_misspelled_word(self, start, end, replacement):
        tab = self.current_tab()
        if not tab:
            return
        cursor = QTextCursor(tab.editor.document())
        cursor.setPosition(int(start))
        cursor.setPosition(int(end), QTextCursor.KeepAnchor)
        cursor.insertText(replacement)
        tab.editor.setTextCursor(cursor)
        tab.on_text_changed()
        tab.run_spellcheck()
        self.status(f"Replaced with '{replacement}'.")

    def ensure_spellchecker_loaded(self, selected_languages):
        selected_languages = list(selected_languages or [])
        current = list(getattr(self.spellchecker, "selected_languages", []) or [])
        have = [lang for lang, _dict in getattr(self.spellchecker, "dictionaries", [])]
        if selected_languages != current or sorted(have) != sorted(selected_languages):
            self.spellchecker.reload(selected_languages)

    def apply_spellcheck_preference(self):
        selected_languages = list(self.prefs.get("spellcheck_languages", SPELLCHECK_LANGUAGES) or [])
        enabled = bool(self.prefs.get("spellcheck_enabled", False)) and bool(selected_languages)
        self.spellchecker.enabled = enabled

        if enabled:
            QTimer.singleShot(300, lambda: self.ensure_spellchecker_loaded(selected_languages))
        else:
            self.spellchecker.dictionaries = []
            self.spellchecker.selected_languages = []

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab):
                if enabled:
                    tab.schedule_spellcheck()
                else:
                    tab.spellcheck_timer.stop()
                    tab.misspellings = []
                    tab.apply_annotations()
                    tab.editor.viewport().update()

    def _new_annotation_id(self):
        return f"ann_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    def selected_text_range(self):
        tab = self.current_tab()
        if not tab:
            return None
        cursor = tab.editor.textCursor()
        if not cursor.hasSelection():
            return None
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        if end <= start:
            return None
        return start, end

    def set_annotation_mode(self, mode: str):
        self.current_annotation_mode = mode
        if hasattr(self, "act_text_mode"):
            self.act_text_mode.setChecked(mode == "text")
        if hasattr(self, "act_highlight_mode"):
            self.act_highlight_mode.setChecked(mode == "highlight")

        if mode == "highlight":
            self.notes_toolbar.setStyleSheet("QToolBar { border: 2px solid #d6b800; background: #fff8bf; }")
            self.status("Highlight mode: drag-select text to highlight it.")
        else:
            self.notes_toolbar.setStyleSheet("")
            self.status("Text editing mode.")

    def add_highlight_from_current_selection(self):
        tab = self.current_tab()
        rng = self.selected_text_range()
        if not tab or not rng:
            return

        start, end = rng
        selected_text = tab.annotation_text({"start": start, "end": end}).strip()
        if not selected_text:
            return

        ann = {
            "id": self._new_annotation_id(),
            "kind": "highlight",
            "label": block_preview(selected_text),
            "start": start,
            "end": end,
            "text": selected_text,
            "color": self.highlight_color.name(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        tab.doc.annotations.append(ann)
        tab.doc.dirty = True
        tab.apply_annotations()
        tab.editor.viewport().update()
        self.refresh_tab_title(tab)
        self.refresh_annotation_sidebars()
        tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
        self.status(f"Highlighted: {block_preview(selected_text)}")

    def choose_highlight_color(self):
        colour = QColorDialog.getColor(self.highlight_color, self, "Choose highlighter colour")
        if colour.isValid():
            self.highlight_color = colour
            self.update_highlight_colour_button()

    def update_highlight_colour_button(self):
        self.highlight_colour_btn.setText(f"Highlighter {self.highlight_color.name()}")
        self.highlight_colour_btn.setStyleSheet(
            f"QPushButton {{ background-color: {self.highlight_color.name()}; color: #000; padding: 3px; }}"
        )

    def choose_note_color(self):
        colour = QColorDialog.getColor(self.note_color, self, "Choose sticky note underline colour")
        if colour.isValid():
            self.note_color = colour
            self.update_note_colour_button()

    def update_note_colour_button(self):
        self.note_colour_btn.setText(f"Note colour {self.note_color.name()}")
        self.note_colour_btn.setStyleSheet(
            f"QPushButton {{ border-bottom: 4px dashed {self.note_color.name()}; padding: 3px; }}"
        )

    def add_note_from_selection(self):
        tab = self.current_tab()
        if not tab:
            return

        cursor = tab.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)
            if not cursor.hasSelection():
                self.status("Select a word or place the cursor inside a word first.")
                return
            tab.editor.setTextCursor(cursor)

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        if end <= start:
            self.status("Select text first, then click Add note.")
            return

        note_text, ok = QInputDialog.getMultiLineText(self, "Add sticky note", "Note:")
        if not ok or not note_text.strip():
            return

        selected_text = tab.annotation_text({"start": start, "end": end}).strip()
        ann = {
            "id": self._new_annotation_id(),
            "kind": "note",
            "label": block_preview(selected_text) if selected_text else "Note",
            "start": start,
            "end": end,
            "text": selected_text,
            "color": self.note_color.name(),
            "note": note_text.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        tab.doc.annotations.append(ann)
        tab.doc.dirty = True
        tab.apply_annotations()
        tab.editor.viewport().update()
        self.refresh_tab_title(tab)
        self.refresh_annotation_sidebars()
        tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
        self.status(f"Added note: {block_preview(note_text)}.")

    def delete_annotation(self, ann_id):
        tab = self.current_tab()
        if not tab:
            return

        existing = next((a for a in tab.doc.annotations if a.get("id") == ann_id), None)
        if existing is None:
            return

        tab.doc.annotations = [a for a in tab.doc.annotations if a.get("id") != ann_id]

        tab.doc.dirty = True
        tab.apply_annotations()
        self.refresh_tab_title(tab)
        self.refresh_annotation_sidebars()
        tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
        self.status("Annotation deleted.")

    def go_to_annotation(self, ann_id):
        tab = self.current_tab()
        if not tab:
            return
        ann = next((a for a in tab.doc.annotations if a.get("id") == ann_id), None)
        if not ann:
            return
        cursor = QTextCursor(tab.editor.document())
        start = int(ann.get("start", 0))
        end = int(ann.get("end", start))
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        tab.editor.setTextCursor(cursor)
        tab.editor.ensureCursorVisible()

    def select_annotation_in_sidebar(self, ann_id):
        for widget in (getattr(self, "highlight_list", None), getattr(self, "note_list", None)):
            if widget is None:
                continue
            for i in range(widget.count()):
                item = widget.item(i)
                if item.data(Qt.UserRole) == ann_id:
                    widget.setCurrentRow(i)
                    return

    def refresh_annotation_sidebars(self):
        if not hasattr(self, "highlight_list"):
            return

        self.highlight_list.clear()
        self.note_list.clear()

        tab = self.current_tab()
        if not tab:
            return

        for ann in tab.doc.annotations:
            if ann.get("kind") == "highlight":
                text = tab.annotation_text(ann).strip()
                item = QListWidgetItem(block_preview(text) if text else "(empty highlight)")
                item.setData(Qt.UserRole, ann.get("id"))
                item.setToolTip(text)
                self.highlight_list.addItem(item)
            elif ann.get("kind") == "note":
                text = ann.get("note", "").strip()
                item = QListWidgetItem(block_preview(text) if text else "(empty note)")
                item.setData(Qt.UserRole, ann.get("id"))
                item.setToolTip(text)
                self.note_list.addItem(item)

    def copy_all_highlighted_text(self):
        tab = self.current_tab()
        if not tab:
            return

        pieces = []
        for ann in tab.doc.annotations:
            if ann.get("kind") == "highlight":
                text = tab.annotation_text(ann).strip()
                if text:
                    pieces.append(text)

        if not pieces:
            self.status("No highlighted text to copy.")
            return

        QApplication.clipboard().setText("\n\n".join(pieces))
        self.status(f"Copied {len(pieces)} highlighted piece(s).")

    def show_notes_sidebar(self):
        if hasattr(self, "notes_dock"):
            self.notes_dock.show()
            self.notes_dock.raise_()

    # ============================================================
    # AstroEditorPro features
    # ============================================================
    def create_pro_panels(self):
        self.create_outline_dock()
        self.create_bookmarks_dock()
        self.create_workspace_dock()
        self.outline_timer = QTimer(self)
        self.outline_timer.setSingleShot(True)
        self.outline_timer.timeout.connect(self.refresh_outline)
        self.bookmark_actions = []

    def create_outline_dock(self):
        self.outline_dock = QDockWidget("Document outline", self)
        self.outline_dock.setObjectName("DocumentOutlineDock")
        self.outline_tree = QTreeWidget()
        self.outline_tree.setHeaderLabels(["Outline"])
        self.outline_tree.itemActivated.connect(self.jump_to_outline_item)
        self.outline_dock.setWidget(self.outline_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.outline_dock)
        self.outline_dock.hide()

    def create_bookmarks_dock(self):
        self.bookmarks_dock = QDockWidget("Bookmarks", self)
        self.bookmarks_dock.setObjectName("BookmarksDock")
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.itemActivated.connect(self.jump_to_bookmark_item)
        self.bookmarks_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookmarks_list.customContextMenuRequested.connect(self.bookmark_context_menu)
        self.bookmarks_dock.setWidget(self.bookmarks_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bookmarks_dock)
        self.bookmarks_dock.hide()

    def create_workspace_dock(self):
        self.workspace_dock = QDockWidget("Workspace", self)
        self.workspace_dock.setObjectName("WorkspaceDock")
        box = QWidget()
        layout = QVBoxLayout(box)
        self.workspace_root_label = QLabel("No folder opened")
        self.workspace_open_btn = QPushButton("Open folder...")
        self.workspace_tree = QTreeWidget()
        self.workspace_tree.setHeaderLabels(["Files"])
        layout.addWidget(self.workspace_root_label)
        layout.addWidget(self.workspace_open_btn)
        layout.addWidget(self.workspace_tree)
        self.workspace_open_btn.clicked.connect(self.open_workspace_folder)
        self.workspace_tree.itemActivated.connect(self.open_workspace_item)
        self.workspace_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.workspace_tree.customContextMenuRequested.connect(self.workspace_context_menu)
        self.workspace_dock.setWidget(box)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.workspace_dock)
        self.workspace_dock.hide()
        self.workspace_root = None

    def schedule_outline_refresh(self):
        if hasattr(self, "outline_timer") and hasattr(self, "outline_dock") and self.outline_dock.isVisible():
            self.outline_timer.start(1200)

    def refresh_outline(self):
        if not hasattr(self, "outline_tree"):
            return
        if hasattr(self, "outline_dock") and not self.outline_dock.isVisible():
            return
        tab = self.current_tab()
        self.outline_tree.clear()
        if not tab:
            return

        heading_re = re.compile(r"^\s*((#{1,6})\s+(.+)|(\d+(?:\.\d+)*)[.)]\s+(.+)|={2,}\s*(.+?)\s*={2,})\s*$")
        block = tab.editor.document().firstBlock()
        while block.isValid():
            line = block.text()
            m = heading_re.match(line)
            if m:
                title = m.group(3) or m.group(5) or m.group(6) or line.strip()
                item = QTreeWidgetItem([title.strip()])
                item.setData(0, Qt.UserRole, block.position())
                self.outline_tree.addTopLevelItem(item)
            block = block.next()

    def jump_to_outline_item(self, item, column=0):
        tab = self.current_tab()
        if not tab:
            return
        pos = int(item.data(0, Qt.UserRole) or 0)
        cursor = tab.editor.textCursor()
        cursor.setPosition(pos)
        tab.editor.setTextCursor(cursor)
        tab.editor.setFocus()

    def current_tab_bookmarks(self):
        tab = self.current_tab()
        if not tab:
            return []
        if not hasattr(tab.doc, "bookmarks"):
            tab.doc.bookmarks = []
        return tab.doc.bookmarks

    def add_bookmark_at_cursor_or_position(self, pos=None):
        tab = self.current_tab()
        if not tab:
            return
        cursor = tab.editor.textCursor()
        if pos is not None:
            cursor.setPosition(pos)
        block = cursor.block()
        line_no = block.blockNumber() + 1
        start = block.position()
        preview = block.text().strip() or f"Line {line_no}"
        bms = self.current_tab_bookmarks()
        for bm in bms:
            if int(bm.get("position", -1)) == start:
                self.status("Bookmark already exists on this line.")
                return
        bms.append({"position": start, "line": line_no, "preview": preview})
        bms.sort(key=lambda b: int(b.get("position", 0)))
        tab.doc.dirty = True
        self.refresh_bookmarks_sidebar()
        self.refresh_tab_title(tab)
        self.status(f"Bookmarked line {line_no}.")

    def refresh_bookmarks_sidebar(self):
        if not hasattr(self, "bookmarks_list"):
            return
        self.bookmarks_list.clear()
        bms = self.current_tab_bookmarks()
        for i, bm in enumerate(bms):
            name = chr(ord("A") + i) if i < 26 else f"{i+1}"
            item = QListWidgetItem(f"{name}. line {bm.get('line', '?')}: {bm.get('preview','')}")
            item.setData(Qt.UserRole, i)
            self.bookmarks_list.addItem(item)

    def jump_to_bookmark_index(self, index):
        tab = self.current_tab()
        bms = self.current_tab_bookmarks()
        if not tab or index < 0 or index >= len(bms):
            return
        bm = bms[index]
        pos = int(bm.get("position", 0))
        cursor = tab.editor.textCursor()
        cursor.setPosition(min(pos, tab.editor.document().characterCount() - 1))
        tab.editor.setTextCursor(cursor)
        tab.editor.setFocus()
        self.status(f"Jumped to bookmark {chr(ord('A') + index) if index < 26 else index + 1}.")

    def bookmark_context_menu(self, pos):
        item = self.bookmarks_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        remove = menu.addAction("Remove bookmark")
        jump = menu.addAction("Jump to bookmark")
        action = menu.exec(self.bookmarks_list.viewport().mapToGlobal(pos))
        idx = int(item.data(Qt.UserRole))
        if action == remove:
            bms = self.current_tab_bookmarks()
            if 0 <= idx < len(bms):
                bms.pop(idx)
                tab = self.current_tab()
                if tab:
                    tab.doc.dirty = True
                    self.refresh_tab_title(tab)
                self.refresh_bookmarks_sidebar()
        elif action == jump:
            self.jump_to_bookmark_index(idx)

    def jump_to_bookmark_item(self, item):
        self.jump_to_bookmark_index(int(item.data(Qt.UserRole)))

    def clear_current_multi_selection(self):
        tab = self.current_tab()
        if tab:
            tab.clear_multi_selections()

    def toggle_split_view(self):
        if getattr(self, "splitter_mode", False):
            self.disable_split_view()
        else:
            self.enable_split_view()

    def enable_split_view(self):
        if getattr(self, "splitter_mode", False):
            return

        old = self.centralWidget()
        self._normal_central_widget = old
        self.splitter = QSplitter(Qt.Horizontal)
        old.setParent(None)
        self.splitter.addWidget(old)

        self.split_edit_tabs = QTabWidget()
        self.split_syncing = False
        self.split_clone_for_left = {}
        self.left_for_split_clone = {}

        for i in range(self.tabs.count()):
            src_tab = self.tabs.widget(i)
            clone_doc = DocumentInfo(
                path=src_tab.doc.path,
                autosave_path=src_tab.doc.autosave_path,
                title=src_tab.doc.title,
                annotations=[dict(a) for a in src_tab.doc.annotations],
                bookmarks=[dict(b) for b in getattr(src_tab.doc, "bookmarks", [])],
            )
            clone = EditorTab(self, clone_doc)
            clone.set_html(src_tab.editor.toHtml())
            self.split_edit_tabs.addTab(clone, self.tabs.tabText(i))

            self.split_clone_for_left[src_tab] = clone
            self.left_for_split_clone[clone] = src_tab

            src_tab.editor.textChanged.connect(lambda t=src_tab: self.sync_split_from_left(t))
            clone.editor.textChanged.connect(lambda t=clone: self.sync_split_from_right(t))

        self.tabs.currentChanged.connect(self.sync_split_tab_index_from_left)
        self.split_edit_tabs.currentChanged.connect(self.sync_left_tab_index_from_split)

        self.splitter.addWidget(self.split_edit_tabs)
        self.setCentralWidget(self.splitter)
        self.splitter_mode = True
        self.status("Editable split view enabled and synchronized.")

    def sync_split_tab_index_from_left(self, index):
        if getattr(self, "splitter_mode", False) and hasattr(self, "split_edit_tabs"):
            if 0 <= index < self.split_edit_tabs.count() and self.split_edit_tabs.currentIndex() != index:
                self.split_edit_tabs.setCurrentIndex(index)

    def sync_left_tab_index_from_split(self, index):
        if getattr(self, "splitter_mode", False):
            if 0 <= index < self.tabs.count() and self.tabs.currentIndex() != index:
                self.tabs.setCurrentIndex(index)

    def capture_tab_view_state(self, tab):
        if not tab:
            return {}
        editor = tab.editor
        cursor = editor.textCursor()
        return {
            "cursor": cursor.position(),
            "vscroll": editor.verticalScrollBar().value(),
            "hscroll": editor.horizontalScrollBar().value(),
        }

    def restore_tab_view_state(self, tab, state):
        if not tab or not state:
            return
        editor = tab.editor
        max_pos = max(0, editor.document().characterCount() - 1)
        cursor = editor.textCursor()
        cursor.setPosition(min(int(state.get("cursor", 0)), max_pos))
        editor.setTextCursor(cursor)
        editor.verticalScrollBar().setValue(min(int(state.get("vscroll", 0)), editor.verticalScrollBar().maximum()))
        editor.horizontalScrollBar().setValue(min(int(state.get("hscroll", 0)), editor.horizontalScrollBar().maximum()))

    def copy_tab_content_and_metadata(self, source, target):
        if not source or not target:
            return
        src_state = self.capture_tab_view_state(source)
        tgt_state = self.capture_tab_view_state(target)

        target.editor.blockSignals(True)
        try:
            target.editor.setHtml(source.editor.toHtml())
        finally:
            target.editor.blockSignals(False)

        target.doc.annotations = [dict(a) for a in source.doc.annotations]
        target.doc.bookmarks = [dict(b) for b in getattr(source.doc, "bookmarks", [])]
        target.doc.dirty = source.doc.dirty
        target.apply_annotations()
        self.restore_tab_view_state(target, tgt_state)
        self.restore_tab_view_state(source, src_state)

    def sync_split_from_left(self, left_tab):
        if not getattr(self, "splitter_mode", False) or getattr(self, "split_syncing", False):
            return
        right_tab = self.split_clone_for_left.get(left_tab)
        if not right_tab:
            return
        self.split_syncing = True
        try:
            self.copy_tab_content_and_metadata(left_tab, right_tab)
            self.refresh_bookmarks_sidebar()
            self.refresh_outline()
        finally:
            self.split_syncing = False

    def sync_split_from_right(self, right_tab):
        if not getattr(self, "splitter_mode", False) or getattr(self, "split_syncing", False):
            return
        left_tab = self.left_for_split_clone.get(right_tab)
        if not left_tab:
            return
        self.split_syncing = True
        try:
            self.copy_tab_content_and_metadata(right_tab, left_tab)
            left_tab.on_text_changed()
            self.refresh_tab_title(left_tab)
            self.refresh_bookmarks_sidebar()
            self.refresh_outline()
        finally:
            self.split_syncing = False


    def disable_split_view(self):
        if not getattr(self, "splitter_mode", False):
            return

        # Push any active right-side edits back to the left before closing split view.
        try:
            if hasattr(self, "split_edit_tabs"):
                idx = self.split_edit_tabs.currentIndex()
                if 0 <= idx < self.split_edit_tabs.count():
                    right_tab = self.split_edit_tabs.widget(idx)
                    self.sync_split_from_right(right_tab)
        except Exception:
            pass

        self.splitter.setParent(None)
        self.setCentralWidget(self._normal_central_widget)
        self.splitter_mode = False
        self.split_clone_for_left = {}
        self.left_for_split_clone = {}
        self.status("Split view disabled.")


    def refresh_split_view(self):
        # Split view is synchronized by textChanged signals in both directions.
        return


    def open_spellcheck_languages_dialog(self):
        dlg = SpellcheckLanguagesDialog(self)
        dlg.exec()

    def set_spellcheck_mode(self, mode):
        self.prefs["spellcheck_mode"] = mode
        self.save_preferences()
        self.apply_spellcheck_preference()
        self.status(f"Spellcheck mode: {mode}")

    def current_spellcheck_languages(self):
        return list(self.prefs.get("spellcheck_languages", SPELLCHECK_LANGUAGES))


    def clean_selected_or_all_text(self, operation):
        tab = self.current_tab()
        if not tab:
            return
        cursor = tab.editor.textCursor()
        whole = not cursor.hasSelection()
        text = cursor.selectedText().replace("\u2029", "\n") if not whole else tab.editor.toPlainText()

        if operation == "trim_trailing":
            text = "\n".join(line.rstrip() for line in text.splitlines())
        elif operation == "tabs_to_spaces":
            text = text.replace("\t", "    ")
        elif operation == "double_spaces":
            text = re.sub(r"[ ]{2,}", " ", text)
        elif operation == "remove_empty":
            text = "\n".join(line for line in text.splitlines() if line.strip())
        elif operation == "sort_lines":
            text = "\n".join(sorted(text.splitlines()))
        elif operation == "dedupe_lines":
            seen, out = set(), []
            for line in text.splitlines():
                if line not in seen:
                    seen.add(line)
                    out.append(line)
            text = "\n".join(out)
        elif operation == "join_wrapped":
            paragraphs = re.split(r"\n\s*\n", text)
            text = "\n\n".join(" ".join(p.splitlines()) for p in paragraphs)
        else:
            return

        if whole:
            tab.editor.setPlainText(text)
        else:
            cursor.insertText(text)
        tab.on_text_changed()

    def align_selected_table(self):
        tab = self.current_tab()
        if not tab:
            return
        cursor = tab.editor.textCursor()
        if not cursor.hasSelection():
            self.status("Select a table-like block first.")
            return
        text = cursor.selectedText().replace("\u2029", "\n")
        lines = text.splitlines()
        rows = []
        for line in lines:
            if "\t" in line:
                cells = [c.strip() for c in line.split("\t")]
            elif "," in line:
                cells = [c.strip() for c in line.split(",")]
            else:
                cells = re.split(r"\s{2,}|\s+", line.strip())
            rows.append(cells)
        if not rows:
            return
        cols = max(len(r) for r in rows)
        widths = [0] * cols
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        out = []
        for row in rows:
            padded = []
            for i in range(cols):
                cell = row[i] if i < len(row) else ""
                padded.append(cell.ljust(widths[i]))
            out.append("  ".join(padded).rstrip())
        cursor.insertText("\n".join(out))
        tab.on_text_changed()

    def open_workspace_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open workspace folder", self.last_folder())
        if folder:
            self.remember_folder_from_path(folder)
            self.load_workspace(folder)

    def load_workspace(self, folder):
        self.workspace_root = Path(folder)
        self.workspace_root_label.setText(str(self.workspace_root))
        self.workspace_tree.clear()
        root_item = QTreeWidgetItem([self.workspace_root.name])
        root_item.setData(0, Qt.UserRole, str(self.workspace_root))
        self.workspace_tree.addTopLevelItem(root_item)
        self.populate_workspace_item(root_item, self.workspace_root, depth=0)
        root_item.setExpanded(True)

    def populate_workspace_item(self, parent_item, folder, depth=0):
        if depth > 3:
            return
        try:
            entries = sorted(Path(folder).iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception:
            return
        for path in entries[:500]:
            if path.name.startswith("."):
                continue
            item = QTreeWidgetItem([path.name])
            item.setData(0, Qt.UserRole, str(path))
            parent_item.addChild(item)
            if path.is_dir():
                self.populate_workspace_item(item, path, depth + 1)

    def workspace_context_menu(self, pos):
        item = self.workspace_tree.itemAt(pos)
        if not item:
            return
        path = Path(item.data(0, Qt.UserRole))
        menu = QMenu(self)
        remove_view = menu.addAction("Remove from workspace view")
        open_file_action = None
        if path.is_file():
            open_file_action = menu.addAction("Open file")
        action = menu.exec(self.workspace_tree.viewport().mapToGlobal(pos))
        if action == remove_view:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                idx = self.workspace_tree.indexOfTopLevelItem(item)
                self.workspace_tree.takeTopLevelItem(idx)
        elif open_file_action is not None and action == open_file_action:
            self.open_file(str(path))

    def open_workspace_item(self, item, column=0):
        path = Path(item.data(0, Qt.UserRole))
        if path.is_file():
            self.open_file(str(path))

    def paste_clipboard_image_into_current_tab(self, label="screenshot"):
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            self.status("No image found in clipboard.")
            return False
        try:
            out = save_clipboard_image(image)
            tab = self.current_tab()
            if tab:
                tab.editor.insert_image_from_path(out)
                tab.on_text_changed()
                self.status(f"Inserted {label} from clipboard.")
                return True
        except Exception as exc:
            QMessageBox.critical(self, "Clipboard image paste failed", str(exc))
        return False



    def export_current_document(self):
        dlg = ExportDialog(self)
        dlg.exec()

    def create_actions_and_menu(self):
        menu = self.menuBar().addMenu("Menu")
        view_menu = self.menuBar().addMenu("View")

        self.act_preferences = QAction("Preferences", self)
        self.act_preferences.triggered.connect(self.open_preferences)
        menu.addAction(self.act_preferences)

        menu.addSeparator()

        self.act_new_window = QAction("New Window", self)
        self.act_new_window.triggered.connect(self.new_window)
        menu.addAction(self.act_new_window)

        self.act_new_tab = QAction("New Tab", self)
        self.act_new_tab.triggered.connect(self.new_tab)
        menu.addAction(self.act_new_tab)

        self.act_open = QAction("Open...", self)
        self.act_open.triggered.connect(self.open_file)
        menu.addAction(self.act_open)

        self.act_save = QAction("Save", self)
        self.act_save.triggered.connect(self.save_current)
        menu.addAction(self.act_save)

        self.recent_menu = menu.addMenu("Recent Files")
        self.refresh_recent_menu()

        menu.addSeparator()

        self.act_find = QAction("Find", self)
        self.act_find.triggered.connect(lambda: self.find_bar.show_find(False))
        menu.addAction(self.act_find)

        self.act_replace = QAction("Find and Replace", self)
        self.act_replace.triggered.connect(lambda: self.find_bar.show_find(True))
        menu.addAction(self.act_replace)

        menu.addSeparator()

        self.act_store_copy_block = QAction("Store Selection in Copy Storage", self)
        self.act_store_copy_block.triggered.connect(self.store_selected_copy_block)
        menu.addAction(self.act_store_copy_block)

        self.act_paste_copy_block = QAction("Paste from Copy Storage", self)
        self.act_paste_copy_block.triggered.connect(self.open_copy_storage_popup)
        menu.addAction(self.act_paste_copy_block)

        menu.addSeparator()

        self.act_shortcuts = QAction("Keyboard Shortcuts", self)
        self.act_shortcuts.triggered.connect(self.open_shortcuts_editor)
        menu.addAction(self.act_shortcuts)

        self.act_close_tab = QAction("Close Tab", self)
        self.act_close_tab.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        menu.addAction(self.act_close_tab)

        toolbar = QToolBar("Text formatting")
        toolbar.setObjectName("TextFormattingToolbar")
        toolbar.setMovable(False)
        self.text_toolbar = toolbar
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.act_bold = QAction("B", self)
        self.act_bold.setCheckable(True)
        self.act_bold.triggered.connect(self.toggle_bold)
        toolbar.addAction(self.act_bold)

        self.act_italic = QAction("I", self)
        self.act_italic.setCheckable(True)
        self.act_italic.triggered.connect(self.toggle_italic)
        toolbar.addAction(self.act_italic)

        self.act_underline = QAction("U", self)
        self.act_underline.setCheckable(True)
        self.act_underline.triggered.connect(self.toggle_underline)
        toolbar.addAction(self.act_underline)

        toolbar.addSeparator()

        self.font_combo = QFontComboBox()
        self.font_combo.setToolTip("Apply font to selected text or future typing")
        self.font_combo.setMaximumWidth(260)
        self.font_combo.currentFontChanged.connect(self.apply_selected_font)
        toolbar.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setToolTip("Apply text size to selected text or future typing")
        self.size_combo.setEditable(True)
        self.size_combo.setMaximumWidth(80)
        for size in [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72]:
            self.size_combo.addItem(str(size))
        self.size_combo.setCurrentText(str(self.prefs.get("font_size", 12)))
        self.size_combo.currentTextChanged.connect(self.apply_selected_font_size)
        toolbar.addWidget(self.size_combo)

        self.text_colour_btn = QPushButton("Text colour")
        self.text_colour_btn.setToolTip("Apply colour to selected text or future typing")
        self.text_colour_btn.clicked.connect(self.choose_text_colour)
        toolbar.addWidget(self.text_colour_btn)

        self.zoom_label = QLabel("Zoom: 100%")
        self.zoom_label.setMinimumWidth(90)
        toolbar.addWidget(self.zoom_label)

        self.image_toolbar = QToolBar("Image editing")
        self.image_toolbar.setObjectName("ImageEditingToolbar")
        self.image_toolbar.setMovable(False)
        self.addToolBarBreak(Qt.TopToolBarArea)
        self.addToolBar(Qt.TopToolBarArea, self.image_toolbar)

        self.act_rotate_ccw = QAction("⟲ Rotate left", self)
        self.act_rotate_ccw.triggered.connect(lambda: self.rotate_selected_image(-90))
        self.image_toolbar.addAction(self.act_rotate_ccw)

        self.act_rotate_cw = QAction("⟳ Rotate right", self)
        self.act_rotate_cw.triggered.connect(lambda: self.rotate_selected_image(90))
        self.image_toolbar.addAction(self.act_rotate_cw)

        self.act_crop_image = QAction("Crop", self)
        self.act_crop_image.triggered.connect(self.crop_selected_image)
        self.image_toolbar.addAction(self.act_crop_image)

        self.image_toolbar.addSeparator()

        self.image_toolbar.addWidget(QLabel("W:"))
        self._updating_image_size_controls = False
        self._current_image_aspect = None
        self._lock_image_aspect = True

        self.image_width_spin = QSpinBox()
        self.image_width_spin.setRange(0, 20000)
        self.image_width_spin.setSpecialValueText("auto")
        self.image_width_spin.setMaximumWidth(90)
        self.image_width_spin.valueChanged.connect(self.image_width_changed)
        self.image_toolbar.addWidget(self.image_width_spin)

        self.image_toolbar.addWidget(QLabel("H:"))
        self.image_height_spin = QSpinBox()
        self.image_height_spin.setRange(0, 20000)
        self.image_height_spin.setSpecialValueText("auto")
        self.image_height_spin.setMaximumWidth(90)
        self.image_height_spin.valueChanged.connect(self.image_height_changed)
        self.image_toolbar.addWidget(self.image_height_spin)

        self.lock_aspect_checkbox = QCheckBox("Keep ratio")
        self.lock_aspect_checkbox.setChecked(True)
        self.lock_aspect_checkbox.toggled.connect(lambda checked: setattr(self, "_lock_image_aspect", checked))
        self.image_toolbar.addWidget(self.lock_aspect_checkbox)

        self.act_apply_image_size = QAction("Set size", self)
        self.act_apply_image_size.triggered.connect(self.set_selected_image_size)
        self.image_toolbar.addAction(self.act_apply_image_size)

        self.image_toolbar.addSeparator()

        self.image_toolbar.addWidget(QLabel("Scale %:"))
        self.image_scale_spin = QSpinBox()
        self.image_scale_spin.setRange(1, 1000)
        self.image_scale_spin.setValue(50)
        self.image_scale_spin.setMaximumWidth(80)
        self.image_toolbar.addWidget(self.image_scale_spin)

        self.act_scale_image = QAction("Scale", self)
        self.act_scale_image.triggered.connect(self.scale_selected_image)
        self.image_toolbar.addAction(self.act_scale_image)

        self.act_view_text_toolbar = QAction("Text formatting toolbar", self)
        self.act_view_text_toolbar.setCheckable(True)
        self.act_view_text_toolbar.setChecked(True)
        self.act_view_text_toolbar.toggled.connect(lambda visible: (self.text_toolbar.setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_text_toolbar)

        self.act_view_image_toolbar = QAction("Image editing toolbar", self)
        self.act_view_image_toolbar.setCheckable(True)
        self.act_view_image_toolbar.setChecked(True)
        self.act_view_image_toolbar.toggled.connect(lambda visible: (self.image_toolbar.setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_image_toolbar)

        self.act_view_statusbar = QAction("Status bar", self)
        self.act_view_statusbar.setCheckable(True)
        self.act_view_statusbar.setChecked(True)
        self.act_view_statusbar.toggled.connect(lambda visible: (self.statusBar().setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_statusbar)

        self.notes_toolbar = QToolBar("Notes and annotations")
        self.notes_toolbar.setObjectName("NotesAnnotationsToolbar")
        self.notes_toolbar.setMovable(False)
        self.addToolBarBreak(Qt.TopToolBarArea)
        self.addToolBar(Qt.TopToolBarArea, self.notes_toolbar)

        self.annotation_mode_group = QActionGroup(self)
        self.annotation_mode_group.setExclusive(True)

        self.act_text_mode = QAction("Text mode", self)
        self.act_text_mode.setCheckable(True)
        self.act_text_mode.setChecked(True)
        self.act_text_mode.triggered.connect(lambda: self.set_annotation_mode("text"))
        self.annotation_mode_group.addAction(self.act_text_mode)
        self.notes_toolbar.addAction(self.act_text_mode)

        self.act_highlight_mode = QAction("Highlight mode", self)
        self.act_highlight_mode.setCheckable(True)
        self.act_highlight_mode.triggered.connect(lambda: self.set_annotation_mode("highlight"))
        self.annotation_mode_group.addAction(self.act_highlight_mode)
        self.notes_toolbar.addAction(self.act_highlight_mode)

        self.highlight_color = QColor("#ffff00")
        self.highlight_colour_btn = QPushButton()
        self.highlight_colour_btn.clicked.connect(self.choose_highlight_color)
        self.notes_toolbar.addWidget(self.highlight_colour_btn)
        self.update_highlight_colour_button()

        self.note_color = QColor("#00a0ff")
        self.note_colour_btn = QPushButton()
        self.note_colour_btn.clicked.connect(self.choose_note_color)
        self.notes_toolbar.addWidget(self.note_colour_btn)
        self.update_note_colour_button()

        self.act_add_note = QAction("Add note to selection", self)
        self.act_add_note.triggered.connect(self.add_note_from_selection)
        self.notes_toolbar.addAction(self.act_add_note)

        self.act_view_notes_toolbar = QAction("Notes toolbar", self)
        self.act_view_notes_toolbar.setCheckable(True)
        self.act_view_notes_toolbar.setChecked(True)
        self.act_view_notes_toolbar.toggled.connect(lambda visible: (self.notes_toolbar.setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_notes_toolbar)

        self.highlights_dock = QDockWidget("Highlights", self)
        self.highlights_dock.setObjectName("HighlightsDock")
        self.highlights_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        highlights_widget = QWidget()
        highlights_layout = QVBoxLayout(highlights_widget)
        self.highlight_list = QListWidget()
        self.highlight_list.itemDoubleClicked.connect(lambda item: self.go_to_annotation(item.data(Qt.UserRole)))
        highlights_layout.addWidget(self.highlight_list)
        copy_highlights_btn = QPushButton("Copy all highlighted text")
        copy_highlights_btn.clicked.connect(self.copy_all_highlighted_text)
        highlights_layout.addWidget(copy_highlights_btn)
        self.highlights_dock.setWidget(highlights_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.highlights_dock)

        self.notes_dock = QDockWidget("Sticky notes", self)
        self.notes_dock.setObjectName("StickyNotesDock")
        self.notes_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)
        self.note_list = QListWidget()
        self.note_list.itemDoubleClicked.connect(lambda item: self.go_to_annotation(item.data(Qt.UserRole)))
        notes_layout.addWidget(self.note_list)
        self.notes_dock.setWidget(notes_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.notes_dock)

        self.act_view_highlights_sidebar = QAction("Highlights sidebar", self)
        self.act_view_highlights_sidebar.setCheckable(True)
        self.act_view_highlights_sidebar.setChecked(True)
        self.act_view_highlights_sidebar.toggled.connect(lambda visible: (self.highlights_dock.setVisible(visible), self.schedule_save_state()))
        self.highlights_dock.visibilityChanged.connect(lambda visible: (self.act_view_highlights_sidebar.setChecked(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_highlights_sidebar)

        self.act_view_notes_sidebar = QAction("Sticky notes sidebar", self)
        self.act_view_notes_sidebar.setCheckable(True)
        self.act_view_notes_sidebar.setChecked(True)
        self.act_view_notes_sidebar.toggled.connect(lambda visible: (self.notes_dock.setVisible(visible), self.schedule_save_state()))
        self.notes_dock.visibilityChanged.connect(lambda visible: (self.act_view_notes_sidebar.setChecked(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_notes_sidebar)

        self.refresh_annotation_sidebars()

        # AstroEditorPro menus
        view_menu.addSeparator()
        self.act_view_outline_sidebar = QAction("Document outline sidebar", self, checkable=True)
        self.act_view_outline_sidebar.toggled.connect(lambda visible: (self.outline_dock.setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_outline_sidebar)

        self.act_view_bookmarks_sidebar = QAction("Bookmarks sidebar", self, checkable=True)
        self.act_view_bookmarks_sidebar.toggled.connect(lambda visible: (self.bookmarks_dock.setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_bookmarks_sidebar)

        self.act_view_workspace_sidebar = QAction("Workspace sidebar", self, checkable=True)
        self.act_view_workspace_sidebar.toggled.connect(lambda visible: (self.workspace_dock.setVisible(visible), self.schedule_save_state()))
        view_menu.addAction(self.act_view_workspace_sidebar)

        self.outline_dock.visibilityChanged.connect(lambda visible: self.act_view_outline_sidebar.setChecked(visible))
        self.bookmarks_dock.visibilityChanged.connect(lambda visible: self.act_view_bookmarks_sidebar.setChecked(visible))
        self.workspace_dock.visibilityChanged.connect(lambda visible: self.act_view_workspace_sidebar.setChecked(visible))

        tools_menu = self.menuBar().addMenu("Tools")

        paste_screen_act = QAction("Insert image from clipboard", self)
        paste_screen_act.triggered.connect(lambda: self.paste_clipboard_image_into_current_tab("clipboard image"))
        tools_menu.addAction(paste_screen_act)

        split_act = QAction("Toggle split view", self)
        split_act.triggered.connect(self.toggle_split_view)
        tools_menu.addAction(split_act)

        workspace_act = QAction("Open workspace folder...", self)
        workspace_act.triggered.connect(self.open_workspace_folder)
        tools_menu.addAction(workspace_act)

        tools_menu.addSeparator()
        clean_menu = tools_menu.addMenu("Clean text")
        for label, op in [
            ("Trim trailing whitespace", "trim_trailing"),
            ("Convert tabs to spaces", "tabs_to_spaces"),
            ("Remove repeated spaces", "double_spaces"),
            ("Remove empty lines", "remove_empty"),
            ("Sort selected lines", "sort_lines"),
            ("Deduplicate selected lines", "dedupe_lines"),
            ("Join wrapped lines into paragraphs", "join_wrapped"),
        ]:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, op=op: self.clean_selected_or_all_text(op))
            clean_menu.addAction(act)

        table_align_act = QAction("Align selected table columns", self)
        table_align_act.triggered.connect(self.align_selected_table)
        tools_menu.addAction(table_align_act)

        spell_lang_act = QAction("Spellcheck languages...", self)
        spell_lang_act.triggered.connect(self.open_spellcheck_languages_dialog)
        tools_menu.addAction(spell_lang_act)

        export_menu = self.menuBar().addMenu("Export")
        export_act = QAction("Export current document...", self)
        export_act.triggered.connect(self.export_current_document)
        export_menu.addAction(export_act)


    def action_mapping(self):
        return {
            "bold": self.act_bold,
            "italic": self.act_italic,
            "underline": self.act_underline,
            "copy": QAction(self),
            "paste": QAction(self),
            "select_all": QAction(self),
            "new_tab": self.act_new_tab,
            "new_window": self.act_new_window,
            "save": self.act_save,
            "open": self.act_open,
            "find": self.act_find,
            "find_replace": self.act_replace,
        }

    def reload_shortcuts(self):
        self.shortcuts = parse_shortcuts(str(self.shortcuts_path))

        # Clear old dynamic shortcuts/actions.
        for action in self.shortcut_actions.values():
            self.removeAction(action)
        self.shortcut_actions = {}

        def add_shortcut(name, callback):
            act = QAction(self)
            act.setShortcut(QKeySequence(self.shortcuts.get(name, DEFAULT_SHORTCUTS[name])))
            act.triggered.connect(callback)
            self.addAction(act)
            self.shortcut_actions[name] = act

        add_shortcut("bold", self.toggle_bold)
        add_shortcut("italic", self.toggle_italic)
        add_shortcut("underline", self.toggle_underline)
        add_shortcut("copy", lambda: self.current_tab().editor.copy() if self.current_tab() else None)
        add_shortcut("paste", lambda: self.current_tab().editor.paste() if self.current_tab() else None)
        add_shortcut("store_copy_block", self.store_selected_copy_block)
        add_shortcut("paste_copy_block", self.open_copy_storage_popup)
        add_shortcut("select_all", lambda: self.current_tab().editor.selectAll() if self.current_tab() else None)
        add_shortcut("new_tab", self.new_tab)
        add_shortcut("new_window", self.new_window)
        add_shortcut("save", self.save_current)
        add_shortcut("open", self.open_file)
        add_shortcut("find", lambda: self.find_bar.show_find(False))
        add_shortcut("find_replace", lambda: self.find_bar.show_find(True))
        add_shortcut("undo", self.undo_action)
        add_shortcut("redo", self.redo_action)
        add_shortcut("indent_lines", lambda: self.current_tab().indent_selected_lines(4) if self.current_tab() else None)
        add_shortcut("outdent_lines", lambda: self.current_tab().outdent_selected_lines(4) if self.current_tab() else None)
        add_shortcut("close_tab", lambda: self.close_tab(self.tabs.currentIndex()))
        add_shortcut("save_as_copy_close", self.save_as_copy_and_close_original)
        add_shortcut("toggle_split_view", self.toggle_split_view)
        add_shortcut("open_workspace", self.open_workspace_folder)
        add_shortcut("export_document", self.export_current_document)
        add_shortcut("insert_clipboard_image", lambda: self.paste_clipboard_image_into_current_tab("clipboard image"))
        add_shortcut("clear_multi_selection", self.clear_current_multi_selection)
        for i in range(26):
            letter = chr(ord("A") + i)
            add_shortcut(f"bookmark_{letter}", lambda checked=False, idx=i: self.jump_to_bookmark_index(idx))

        if self.shortcuts_path.exists() and str(self.shortcuts_path) not in self.shortcut_watcher.files() if hasattr(self, "shortcut_watcher") else False:
            self.shortcut_watcher.addPath(str(self.shortcuts_path))

        self.status("Shortcuts loaded.")

    def current_tab(self) -> EditorTab | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, EditorTab) else None

    def normalize_startup_path(self, raw_path):
        """Resolve paths passed by the OS/file manager or command line.

        File managers normally pass absolute paths, but terminal tests often
        pass relative paths such as "shortcuts.conf". Those must be resolved
        against the current working directory, not against the app directory.
        """
        if raw_path is None:
            return None

        raw = str(raw_path).strip()
        if not raw:
            return None

        # Handle file:// URLs defensively, though .desktop %F normally passes paths.
        if raw.startswith("file://"):
            from urllib.parse import unquote, urlparse
            raw = unquote(urlparse(raw).path)

        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p

        try:
            return p.resolve()
        except Exception:
            return p

    def tab_for_path(self, path):
        if not path:
            return None
        wanted = str(Path(path).resolve())
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab) and tab.doc.path:
                try:
                    if str(Path(tab.doc.path).resolve()) == wanted:
                        return tab
                except Exception:
                    if str(tab.doc.path) == str(path):
                        return tab
        return None

    def move_tab_to_front(self, tab, front_index=0):
        idx = self.tabs.indexOf(tab)
        if idx < 0:
            return
        self.tabs.tabBar().moveTab(idx, front_index)
        self.tabs.setCurrentWidget(tab)

    def open_startup_files_in_front(self):
        startup_files = getattr(self, "startup_files", None) or []
        if not startup_files:
            return False

        print(f"AstroEditor startup files: {startup_files}", flush=True)

        opened_any = False
        insert_at = 0
        failures = []

        for raw_path in startup_files:
            try:
                p = self.normalize_startup_path(raw_path)
                print(f"AstroEditor opening startup path: {p}", flush=True)

                if p is None or not p.exists():
                    failures.append(f"Not found: {p}")
                    continue

                existing = self.tab_for_path(str(p))
                if existing is not None:
                    self.move_tab_to_front(existing, insert_at)
                    insert_at += 1
                    opened_any = True
                    continue

                tab = self.open_file(str(p))
                if tab is not None:
                    self.move_tab_to_front(tab, insert_at)
                    insert_at += 1
                    opened_any = True
                else:
                    failures.append(f"Could not open: {p}")
            except Exception as exc:
                failures.append(f"{raw_path}: {exc}")

        if opened_any:
            first = self.tabs.widget(0)
            if first is not None:
                self.tabs.setCurrentWidget(first)
            self.status("Opened command-line/Open-With file(s) in front.")
        elif failures:
            msg = "; ".join(failures[:3])
            print(f"AstroEditor startup open failures: {msg}", flush=True)
            self.status("Could not open startup file(s): " + msg)

        return opened_any

    def new_tab(self):
        tab = EditorTab(self)
        self.tabs.addTab(tab, tab.tab_name())
        self.tabs.setCurrentWidget(tab)
        tab.editor.setFocus()
        self.commit_snapshot_boundary(tab, "new_tab")
        return tab

    def refresh_tab_title(self, tab):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            self.tabs.setTabText(idx, tab.tab_name())

    def last_folder(self):
        folder = self.prefs.get("last_file_folder") or str(Path.home())
        return str(Path(folder)) if Path(folder).exists() else str(Path.home())

    def remember_folder_from_path(self, path):
        if not path:
            return
        try:
            p = Path(path)
            folder = p if p.is_dir() else p.parent
            if folder.exists():
                self.prefs["last_file_folder"] = str(folder)
                self.save_preferences()
        except Exception:
            pass

    def save_as_copy_and_close_original(self):
        tab = self.current_tab()
        if not tab or tab.is_empty():
            return
        needs_rich = tab.has_rich_metadata() if hasattr(tab, "has_rich_metadata") else True
        default_name = (Path(tab.doc.title or "Untitled").stem + ".aep") if needs_rich else ""
        start_path = str(Path(self.last_folder()) / default_name) if default_name else self.last_folder()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save a separate copy and close original",
            start_path,
            "AstroEditorPro self-contained file (*.aep);;Plain text (*.txt);;HTML file (*.html);;All files (*)",
        )
        if not path:
            return
        if needs_rich and not is_rich_document_file(path):
            path += ".aep"
        self.remember_folder_from_path(path)
        old_path = tab.doc.path
        old_title = tab.doc.title
        tab.doc.path = path
        tab.doc.title = Path(path).name
        ok = tab.save()
        if ok:
            self.close_tab(self.tabs.currentIndex())
            self.status(f"Saved copy and closed original: {path}")
        else:
            tab.doc.path = old_path
            tab.doc.title = old_title

    def load_rich_content_into_tab(self, tab, content):
        """Load AstroEditor rich content, restoring self-contained images."""
        html = content.get("html", "")
        embedded_images = content.get("embedded_images", {})
        remap = restore_embedded_images_to_cache(embedded_images)
        html = remap_html_image_sources(html, remap)
        tab.doc.annotations = content.get("annotations", [])
        tab.doc.bookmarks = content.get("bookmarks", [])
        tab.set_html(html)

    def open_file(self, path=None):
        if path is False:
            path = None
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open text-based file", str(Path.home()), "All files (*)")
        if not path:
            return None

        p = Path(path)
        try:
            p = p.expanduser().resolve()

            if is_autosave_file(p):
                data = load_json(p, {})
                content = data.get("content", data)
                doc = data.get("document", {})
                html = content.get("html", "")
                annotations = content.get("annotations", [])
                bookmarks = content.get("bookmarks", [])

                original_path = safe_document_path(doc.get("path"))
                title = Path(original_path).name if original_path else f"Recovered {p.name}"

                tab = EditorTab(
                    self,
                    DocumentInfo(
                        path=original_path,
                        title=title,
                        autosave_path=str(p),
                        annotations=annotations,
                        bookmarks=bookmarks,
                    ),
                )
                self.load_rich_content_into_tab(tab, content)

            elif is_rich_document_file(p):
                data = load_json(p, {})
                content = data.get("content", data)
                html = content.get("html", "")
                annotations = content.get("annotations", [])
                bookmarks = content.get("bookmarks", [])
                tab = EditorTab(self, DocumentInfo(path=safe_document_path(str(p)), title=p.name, annotations=annotations, bookmarks=bookmarks))
                tab.set_html(html)
            elif p.suffix.lower() in {".html", ".htm"}:
                html = read_text_file(p)
                tab = EditorTab(self, DocumentInfo(path=safe_document_path(str(p)), title=p.name))
                tab.set_html(html)
            else:
                text = read_text_file(p)
                tab = EditorTab(self, DocumentInfo(path=safe_document_path(str(p)), title=p.name))
                tab.set_plain_text(text)

            self.tabs.addTab(tab, tab.tab_name())
            self.tabs.setCurrentWidget(tab)
            self.remember_folder_from_path(str(p))
            self.add_recent(str(p))
            self.commit_snapshot_boundary(tab, "open")
            self.status(f"Opened: {p}")
            return tab
        except Exception as exc:
            QMessageBox.critical(self, "Could not open file", f"{p}\n\n{exc}")
            return None

    def open_autosave(self, autosave_path):
        try:
            data = load_json(Path(autosave_path), None)
            if not data:
                return False
            content = data.get("content", {})
            plain = content.get("plain", "")
            if plain.strip() == "":
                return False

            doc = data.get("document", {})
            tab = EditorTab(
                self,
                DocumentInfo(
                    path=safe_document_path(doc.get("path")),
                    autosave_path=autosave_path,
                    title=doc.get("title", "Recovered"),
                    dirty=True,
                    annotations=content.get("annotations", []),
                    bookmarks=content.get("bookmarks", []),
                ),
            )
            self.load_rich_content_into_tab(tab, content)
            tab.doc.dirty = True
            self.tabs.addTab(tab, tab.tab_name())
            self.commit_snapshot_boundary(tab, "recover")
            return True
        except Exception:
            return False

    def save_current(self):
        tab = self.current_tab()
        if tab:
            tab.save()

    def close_tab(self, index):
        if index < 0:
            return

        tab = self.tabs.widget(index)
        if isinstance(tab, EditorTab) and tab.doc.dirty and not tab.is_empty():
            ans = QMessageBox.question(
                self,
                "Unsaved changes",
                f"Save changes to {tab.tab_name().lstrip('*')}?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if ans == QMessageBox.Cancel:
                return
            if ans == QMessageBox.Yes and not tab.save():
                return
            if ans == QMessageBox.No:
                tab.autosave()

        self.tabs.removeTab(index)
        tab.deleteLater()

        if self.tabs.count() == 0:
            self.new_tab()

    def choose_text_colour(self):
        tab = self.current_tab()
        if not tab:
            return

        initial = tab.editor.textColor()
        if not initial.isValid():
            initial = QColor(self.prefs.get("foreground", "#ffffff"))

        colour = QColorDialog.getColor(initial, self, "Choose text colour")
        if not colour.isValid():
            return

        fmt = QTextCharFormat()
        fmt.setForeground(colour)
        self.toggle_char_format(fmt)
        self.update_text_colour_button(colour)

    def update_text_colour_button(self, colour=None):
        tab = self.current_tab()
        if colour is None and tab:
            colour = tab.editor.textColor()
        if colour is None or not colour.isValid():
            colour = QColor(self.prefs.get("foreground", "#ffffff"))

        fg = colour.name()
        self.text_colour_btn.setStyleSheet(
            f"QPushButton {{ border: 2px solid {fg}; padding: 3px; color: #ffffff; }}"
        )
        self.text_colour_btn.setText(f"Text colour {fg}")

    def update_zoom_display(self):
        tab = self.current_tab()
        percent = 100
        if tab and hasattr(tab.editor, "zoom_percent"):
            percent = tab.editor.zoom_percent
        self.zoom_label.setText(f"Zoom: {percent}%")

    def apply_selected_font(self, qfont):
        if self._updating_toolbar:
            return
        tab = self.current_tab()
        if not tab:
            return
        family = qfont.family()
        if not family:
            return
        fmt = QTextCharFormat()
        fmt.setFontFamily(family)
        self.toggle_char_format(fmt)

    def apply_selected_font_size(self, value):
        if self._updating_toolbar:
            return
        tab = self.current_tab()
        if not tab:
            return
        try:
            size = int(value)
        except ValueError:
            return
        if size < 6 or size > 96:
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.toggle_char_format(fmt)

    def toggle_char_format(self, fmt: QTextCharFormat):
        tab = self.current_tab()
        if not tab:
            return

        if getattr(tab, "multi_selections", None):
            if tab.merge_char_format_to_multi_selections(fmt):
                self.update_format_buttons()
                return

        cursor = tab.editor.textCursor()
        if not cursor.hasSelection():
            # Applies to future typing at cursor.
            tab.editor.mergeCurrentCharFormat(fmt)
        else:
            cursor.mergeCharFormat(fmt)
            tab.editor.mergeCurrentCharFormat(fmt)
        tab.doc.dirty = True
        self.refresh_tab_title(tab)
        tab.autosave_timer.start(AUTOSAVE_DELAY_MS)
        self.update_format_buttons()

    def toggle_bold(self):
        tab = self.current_tab()
        if not tab:
            return
        current = tab.editor.fontWeight()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Normal if current >= QFont.Bold else QFont.Bold)
        self.toggle_char_format(fmt)

    def toggle_italic(self):
        tab = self.current_tab()
        if not tab:
            return
        fmt = QTextCharFormat()
        fmt.setFontItalic(not tab.editor.fontItalic())
        self.toggle_char_format(fmt)

    def toggle_underline(self):
        tab = self.current_tab()
        if not tab:
            return
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not tab.editor.fontUnderline())
        self.toggle_char_format(fmt)

    def update_format_buttons(self):
        tab = self.current_tab()
        if not tab or self._updating_toolbar:
            return

        self._updating_toolbar = True
        try:
            self.act_bold.blockSignals(True)
            self.act_italic.blockSignals(True)
            self.act_underline.blockSignals(True)

            self.act_bold.setChecked(tab.editor.fontWeight() >= QFont.Bold)
            self.act_italic.setChecked(tab.editor.fontItalic())
            self.act_underline.setChecked(tab.editor.fontUnderline())

            cursor = tab.editor.textCursor()
            char_format = cursor.charFormat()

            # Avoid deprecated QTextCharFormat.fontFamily(); use the QFont object.
            qfont = char_format.font()
            family = qfont.family() or tab.editor.currentFont().family() or self.prefs.get("font_family", "DejaVu Sans Mono")

            size = char_format.fontPointSize()
            if size <= 0:
                size = qfont.pointSizeF()
            if size <= 0:
                size = tab.editor.currentFont().pointSizeF()
            if size <= 0:
                size = float(self.prefs.get("font_size", 12))

            self.font_combo.blockSignals(True)
            self.size_combo.blockSignals(True)
            self.font_combo.setCurrentFont(QFont(family))
            self.size_combo.setCurrentText(str(int(round(size))))

            colour = char_format.foreground().color()
            self.update_text_colour_button(colour)
            self.update_zoom_display()
            if hasattr(self, "image_width_spin"):
                self.refresh_image_size_controls()
        finally:
            self.font_combo.blockSignals(False)
            self.size_combo.blockSignals(False)
            self.act_bold.blockSignals(False)
            self.act_italic.blockSignals(False)
            self.act_underline.blockSignals(False)
            self._updating_toolbar = False

    def new_window(self):
        try:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--new-window-empty"])
        except Exception as exc:
            QMessageBox.critical(self, "Could not open new window", str(exc))

    def open_preferences(self):
        PreferencesDialog(self).exec()

    def open_shortcuts_editor(self):
        ShortcutsEditor(self).exec()

    def save_preferences(self):
        save_json(self.prefs_path, self.prefs)

    def apply_preferences(self):
        self._updating_toolbar = True
        try:
            self.size_combo.blockSignals(True)
            self.font_combo.blockSignals(True)
            self.size_combo.setCurrentText(str(int(self.prefs.get("font_size", 12))))
            self.font_combo.setCurrentFont(QFont(self.prefs.get("font_family", "DejaVu Sans Mono")))
        finally:
            self.size_combo.blockSignals(False)
            self.font_combo.blockSignals(False)
            self._updating_toolbar = False

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab):
                tab.apply_preferences()
        self.update_text_colour_button()
        self.update_zoom_display()
        if hasattr(self, "spellchecker"):
            self.apply_spellcheck_preference()

    def add_recent(self, path):
        recent = load_json(self.recent_path, [])
        path = str(Path(path))
        recent = [x for x in recent if x != path]
        recent.insert(0, path)
        recent = recent[:30]
        save_json(self.recent_path, recent)
        self.refresh_recent_menu()

    def refresh_recent_menu(self):
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        recent = load_json(self.recent_path, [])
        if not recent:
            empty = QAction("No recent files", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)
            return
        for p in recent:
            act = QAction(p, self)
            act.triggered.connect(lambda checked=False, path=p: self.open_file(path))
            self.recent_menu.addAction(act)

    def backup_state_file(self, reason="bad_state"):
        """Move the current state.json to backup so startup can continue safely."""
        try:
            if not self.state_path.exists():
                return None
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_reason = re.sub(r"[^A-Za-z0-9_-]+", "_", str(reason))[:40]
            out = backup_dir() / f"state_{safe_reason}_{stamp}.json"
            self.state_path.replace(out)
            print(f"AstroEditor moved unsafe state file to: {out}", flush=True)
            return out
        except Exception as exc:
            print(f"AstroEditor could not backup unsafe state file: {exc}", flush=True)
            return None

    def load_state_safely(self):
        """Load state.json with validation.

        The app should never require deleting the whole tmp folder to start.
        If state.json is malformed or refers only to invalid/missing autosaves,
        it is quarantined and a blank session is opened.
        """
        try:
            if not self.state_path.exists():
                return {}
            raw = self.state_path.read_text(encoding="utf-8")
            if not raw.strip():
                self.backup_state_file("empty")
                return {}
            state = json.loads(raw)
            if not isinstance(state, dict):
                self.backup_state_file("not_dict")
                return {}
            return self.sanitize_state_for_restore(state)
        except Exception as exc:
            print(f"AstroEditor state load failed: {exc}", flush=True)
            self.backup_state_file("json_error")
            return {}

    def sanitize_state_for_restore(self, state):
        """Remove duplicate/broken session entries before Qt widgets are created."""
        clean = dict(state or {})
        clean_tabs = []
        seen = set()

        for item in list(clean.get("tabs", [])):
            if not isinstance(item, dict):
                continue

            path = item.get("path")
            autosave = item.get("autosave_path")

            # Never allow an autosave file to be treated as a normal path.
            path = safe_document_path(path)

            autosave_ok = False
            if autosave:
                try:
                    ap = Path(autosave).expanduser()
                    if ap.exists() and ap.is_file() and ap.stat().st_size <= MAX_AUTOSAVE_FILE_BYTES:
                        # Test-load the JSON now. Bad autosaves are skipped.
                        data = load_json(ap, None)
                        content = data.get("content", data) if isinstance(data, dict) else {}
                        plain = content.get("plain", "") if isinstance(content, dict) else ""
                        html = content.get("html", "") if isinstance(content, dict) else ""
                        autosave_ok = bool(str(plain).strip() or str(html).strip())
                except Exception:
                    autosave_ok = False

            path_ok = False
            if path:
                try:
                    pp = Path(path).expanduser()
                    path_ok = pp.exists() and pp.is_file()
                except Exception:
                    path_ok = False

            if not autosave_ok and not path_ok:
                continue

            ident_source = path if path_ok else autosave
            try:
                ident = str(Path(ident_source).expanduser().resolve())
            except Exception:
                ident = str(ident_source)

            if ident in seen:
                continue
            seen.add(ident)

            fixed = dict(item)
            fixed["path"] = path if path_ok else None
            if not autosave_ok:
                fixed["autosave_path"] = None
            clean_tabs.append(fixed)

            if len(clean_tabs) >= MAX_RESTORED_TABS:
                print(f"AstroEditor restored tab list was limited to {MAX_RESTORED_TABS} tabs.", flush=True)
                break

        clean["tabs"] = clean_tabs

        # Keep visibility preferences, but do not trust binary QMainWindow state
        # unless explicitly enabled.
        if not RESTORE_QT_BINARY_WINDOW_STATE:
            clean.pop("window_state", None)

        return clean

    def state_tab_identity(self, item):
        path = item.get("path")
        autosave = item.get("autosave_path")

        if path:
            try:
                return ("path", str(Path(path).expanduser().resolve()))
            except Exception:
                return ("path", str(path))

        if autosave:
            try:
                return ("autosave", str(Path(autosave).expanduser().resolve()))
            except Exception:
                return ("autosave", str(autosave))

        return None

    def merge_tabs_for_state(self, existing_tabs, current_tabs):
        merged = []
        seen = set()
        for item in list(current_tabs or []) + list(existing_tabs or []):
            ident = self.state_tab_identity(item)
            if ident is None or ident in seen:
                continue
            seen.add(ident)
            merged.append(item)
        return merged[:MAX_RESTORED_TABS]

    def inject_startup_files_into_state(self, state):
        """Pretend command-line/Open-With files were part of the previous session.

        This is deliberately simple and robust:
        - normalize each passed path
        - remove any existing saved tab for the same path
        - insert the passed files at the front of state["tabs"]
        - let the normal session-restoration code open them

        Result:
        - clicked file becomes first tab
        - previous session remains after it
        - duplicate restored tabs for the same path are avoided
        """
        startup_files = getattr(self, "startup_files", None) or []
        if not startup_files:
            return state

        tabs = list(state.get("tabs", []))
        injected = []
        injected_paths = []

        for raw_path in startup_files:
            p = self.normalize_startup_path(raw_path)
            if p is None or not p.exists():
                print(f"AstroEditor startup file not found: {p}", flush=True)
                continue

            resolved = str(p)
            injected_paths.append(resolved)
            injected.append({
                "path": None if is_autosave_file(p) else resolved,
                "title": p.name,
                "autosave_path": resolved if is_autosave_file(p) else None,
                "injected_startup_file": True,
            })

        if not injected:
            print("AstroEditor: no valid startup files could be injected.", flush=True)
            return state

        self._injected_startup_paths = injected_paths

        def same_path(a, b):
            try:
                return str(Path(a).resolve()) == str(Path(b).resolve())
            except Exception:
                return str(a) == str(b)

        filtered_tabs = []
        for item in tabs:
            item_path = item.get("path")
            if item_path and any(same_path(item_path, p) for p in injected_paths):
                continue
            filtered_tabs.append(item)

        state["tabs"] = injected + filtered_tabs
        print(f"AstroEditor injected startup files into restored session: {injected_paths}", flush=True)
        return state

    def prepare_async_session_restore(self, state):
        """Prepare previous tabs for non-blocking restoration after the GUI is visible."""
        self._pending_session_restore_tabs = []
        self._session_restore_active = False

        for item in state.get("tabs", [])[:MAX_RESTORED_TABS]:
            if not isinstance(item, dict):
                continue
            autosave = item.get("autosave_path")
            path = item.get("path")
            candidate = autosave or path
            if not candidate:
                continue
            try:
                p = Path(candidate).expanduser()
                if not p.exists() or not p.is_file():
                    continue
                if p.stat().st_size > MAX_STARTUP_AUTOSAVE_FILE_BYTES:
                    print(f"AstroEditor skipped large startup restore file: {p}", flush=True)
                    continue
                self._pending_session_restore_tabs.append(item)
            except Exception as exc:
                print(f"AstroEditor skipped bad startup restore entry: {candidate}: {exc}", flush=True)

    def start_async_session_restore(self):
        """Restore saved tabs in small chunks so the visible GUI keeps responding."""
        pending = list(getattr(self, "_pending_session_restore_tabs", []) or [])
        if not pending:
            if self.tabs.count() == 0:
                self.new_tab()
            QTimer.singleShot(0, self.restore_saved_view_state)
            return

        self._session_restore_active = True
        self.status(f"Restoring previous session: 0/{len(pending)}")
        QTimer.singleShot(0, self.restore_next_session_batch)

    def restore_next_session_batch(self):
        pending = getattr(self, "_pending_session_restore_tabs", [])
        total = getattr(self, "_session_restore_total", None)
        if total is None:
            self._session_restore_total = len(pending)
            total = self._session_restore_total

        count = 0
        while pending and count < SESSION_RESTORE_BATCH_SIZE:
            item = pending.pop(0)
            try:
                autosave = item.get("autosave_path")
                path = item.get("path")

                if autosave and Path(autosave).exists():
                    self.open_autosave(autosave)
                elif path and Path(path).exists():
                    self.open_file(path)
            except Exception as exc:
                print(f"AstroEditor skipped one restored tab: {exc}", flush=True)
            count += 1

        restored = total - len(pending)
        self.status(f"Restoring previous session: {restored}/{total}")

        if pending:
            QTimer.singleShot(SESSION_RESTORE_BATCH_DELAY_MS, self.restore_next_session_batch)
            return

        self._session_restore_active = False

        # Remove temporary loading tab only after at least one real tab was restored.
        for i in reversed(range(self.tabs.count())):
            tab = self.tabs.widget(i)
            if getattr(tab, "_temporary_loading_tab", False) and self.tabs.count() > 1:
                self.tabs.removeTab(i)
                tab.deleteLater()

        if self.tabs.count() == 0:
            self.new_tab()

        QTimer.singleShot(0, self.restore_saved_view_state)
        self.status("Previous session restored.")

    def load_state_or_new(self):
        # Last-open-tabs restoration remains automatic, but it is now asynchronous:
        # the window appears first, then saved tabs are restored in small batches.
        state = self.load_state_safely()

        geometry_hex = state.get("geometry")
        if geometry_hex:
            try:
                self.restoreGeometry(bytes.fromhex(geometry_hex))
            except Exception as exc:
                print(f"AstroEditor ignored bad geometry state: {exc}", flush=True)

        self._pending_window_state_hex = state.get("window_state") if RESTORE_QT_BINARY_WINDOW_STATE else None
        self._pending_view_state = state.get("view_state", {})

        # Open explicit file-manager/command-line files immediately.
        if getattr(self, "startup_files", None):
            opened = False
            for raw_path in self.startup_files:
                try:
                    p = self.normalize_startup_path(raw_path)
                    if p is not None and p.exists():
                        if is_autosave_file(p):
                            opened = self.open_autosave(str(p)) or opened
                        else:
                            opened = bool(self.open_file(str(p))) or opened
                except Exception as exc:
                    print(f"AstroEditor skipped startup file {raw_path}: {exc}", flush=True)
            if not opened:
                self.new_tab()
            QTimer.singleShot(0, self.restore_saved_view_state)
            return

        self.prepare_async_session_restore(state)

        if getattr(self, "_pending_session_restore_tabs", None):
            loading_tab = self.new_tab()
            if loading_tab is not None:
                loading_tab._temporary_loading_tab = True
                loading_tab.editor.setPlainText("Restoring previous AstroEditorPro session...")
                loading_tab.editor.setReadOnly(True)
                idx = self.tabs.indexOf(loading_tab)
                if idx >= 0:
                    self.tabs.setTabText(idx, "Restoring session...")
            QTimer.singleShot(0, self.start_async_session_restore)
        else:
            self.new_tab()
            QTimer.singleShot(0, self.restore_saved_view_state)

    def schedule_save_state(self):
        # Save soon, after Qt has applied visibility/layout changes.
        QTimer.singleShot(0, self.save_state)

    def restore_saved_view_state(self):
        # First restore Qt's own dock/toolbar layout, then explicitly restore
        # visibility because QMainWindow::restoreState can override or ignore
        # visibility depending on platform/session timing.
        window_state_hex = getattr(self, "_pending_window_state_hex", None)
        if RESTORE_QT_BINARY_WINDOW_STATE and window_state_hex:
            try:
                self.restoreState(bytes.fromhex(window_state_hex))
            except Exception as exc:
                print(f"AstroEditor ignored bad Qt window_state: {exc}", flush=True)

        # Re-force rows after restoreState, because Qt may pack toolbars onto
        # the same row if the saved state was incomplete or came from an older
        # version.
        try:
            self.removeToolBarBreak(self.image_toolbar)
            self.removeToolBarBreak(self.notes_toolbar)
        except Exception:
            pass
        try:
            self.insertToolBarBreak(self.image_toolbar)
            self.insertToolBarBreak(self.notes_toolbar)
        except Exception:
            pass

        view_state = getattr(self, "_pending_view_state", {}) or {}

        mapping = {
            "text_toolbar": getattr(self, "text_toolbar", None),
            "image_toolbar": getattr(self, "image_toolbar", None),
            "notes_toolbar": getattr(self, "notes_toolbar", None),
            "highlights_dock": getattr(self, "highlights_dock", None),
            "notes_dock": getattr(self, "notes_dock", None),
            "statusBar": self.statusBar(),
        }

        for key, widget in mapping.items():
            if widget is None:
                continue
            if key in view_state:
                widget.setVisible(bool(view_state[key]))

        action_mapping = {
            "act_view_text_toolbar": "text_toolbar",
            "act_view_image_toolbar": "image_toolbar",
            "act_view_notes_toolbar": "notes_toolbar",
            "act_view_highlights_sidebar": "highlights_dock",
            "act_view_notes_sidebar": "notes_dock",
            "act_view_outline_sidebar": "outline_dock",
            "act_view_bookmarks_sidebar": "bookmarks_dock",
            "act_view_workspace_sidebar": "workspace_dock",
            "act_view_statusbar": "statusBar",
        }

        for action_name, key in action_mapping.items():
            action = getattr(self, action_name, None)
            widget = mapping.get(key)
            if action is not None and widget is not None:
                action.blockSignals(True)
                action.setChecked(widget.isVisible())
                action.blockSignals(False)

    def cleanup_unreferenced_autosaves(self, kept_tabs):
        """Delete old autosave files not referenced by current restored session.

        This keeps only the latest autosave file per open/restorable tab and
        removes older internal recovery files. Real user files are never touched.
        """
        keep = set()
        for item in kept_tabs or []:
            ap = item.get("autosave_path")
            if ap:
                try:
                    keep.add(str(Path(ap).expanduser().resolve()))
                except Exception:
                    keep.add(str(ap))

        auto = autosave_dir()
        if not auto.exists():
            return

        deleted = 0
        for p in list(auto.glob("*.aep")) + list(auto.glob("*.astroeditor_qt.json")):
            try:
                rp = str(p.resolve())
                if rp not in keep:
                    p.unlink()
                    deleted += 1
            except Exception as exc:
                print(f"AstroEditor could not delete old autosave {p}: {exc}", flush=True)

        if deleted:
            print(f"AstroEditor cleaned {deleted} old autosave file(s).", flush=True)

    def save_state(self):
        current_tabs = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if not isinstance(tab, EditorTab):
                continue
            if tab.is_empty():
                continue

            try:
                tab.autosave()
            except Exception as exc:
                print(f"AstroEditor skipped autosave during state save: {exc}", flush=True)

            if tab.doc.autosave_path:
                current_tabs.append({
                    "path": safe_document_path(tab.doc.path),
                    "title": tab.doc.title,
                    "autosave_path": tab.doc.autosave_path,
                    "window_id": getattr(self, "window_id", "single"),
                })

        view_state = {}
        for attr in [
            "text_toolbar",
            "image_toolbar",
            "notes_toolbar",
            "highlights_dock",
            "notes_dock",
            "outline_dock",
            "bookmarks_dock",
            "workspace_dock",
        ]:
            widget = getattr(self, attr, None)
            if widget is not None:
                view_state[attr] = widget.isVisible()
        view_state["statusBar"] = self.statusBar().isVisible()
        view_state["toolbars_separate_rows"] = True

        lock_path = BASE_DIR / "state.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        with lock_path.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                existing_state = load_json(self.state_path, {})
                existing_tabs = existing_state.get("tabs", []) if isinstance(existing_state, dict) else []

                # Remove older entries from this same window, keep other windows.
                window_id = getattr(self, "window_id", None)
                if window_id:
                    existing_tabs = [item for item in existing_tabs if item.get("window_id") != window_id]

                merged_tabs = self.merge_tabs_for_state(existing_tabs, current_tabs)

                new_state = {
                    "geometry": bytes(self.saveGeometry()).hex(),
                    # Store but do not rely on this by default.
                    "window_state": bytes(self.saveState()).hex(),
                    "view_state": view_state,
                    "tabs": merged_tabs,
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "app_version": APP_VERSION,
                }

                # Save the state first. Only after it is safely written do we
                # clean old autosave files. This avoids shutdown-time corruption
                # where autosaves are deleted before state.json is updated.
                save_json(self.state_path, new_state)
                self.cleanup_unreferenced_autosaves(merged_tabs)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def closeEvent(self, event):
        try:
            self.save_state()
        except Exception as exc:
            print(f"AstroEditor save_state during close failed: {exc}", flush=True)
        event.accept()

    def status(self, message):
        self.statusBar().showMessage(message, 5000)


def load_fonts_from_folder():
    folder = Path(FONTS_DIR).expanduser()
    if not folder.exists():
        return
    for ext in ("*.ttf", "*.otf", "*.ttc"):
        for p in folder.rglob(ext):
            QFontDatabase.addApplicationFont(str(p))


def main():
    Path(TEMP_DATA_DIR).expanduser().mkdir(parents=True, exist_ok=True)
    if not Path(SHORTCUTS_FILE).expanduser().exists():
        write_default_shortcuts(SHORTCUTS_FILE)

    app = QApplication(sys.argv)

    # Desktop integration:
    # - setDesktopFileName("astroeditor") must match ~/.local/share/applications/astroeditor.desktop
    # - this helps GNOME/Ubuntu Dock associate the running Qt window with the launcher
    #   instead of showing a generic "python3" gear icon.
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setDesktopFileName(APP_DESKTOP_ID)

    icon_path = Path(APP_ICON_PATH)
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    load_fonts_from_folder()

    # Preserve command-line file arguments. Relative paths are intentionally
    # left as strings here and resolved inside MainWindow against Path.cwd().
    args = sys.argv[1:]
    restore_session = "--new-window-empty" not in args
    startup_files = [arg for arg in args if arg != "--new-window-empty"]

    if startup_files:
        print(f"AstroEditor {APP_VERSION} received command-line/Open-With files: {startup_files}", flush=True)
        try:
            debug_path = Path(TEMP_DATA_DIR) / "startup_debug.log"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            with debug_path.open("a", encoding="utf-8") as f:
                f.write(datetime.now().isoformat(timespec="seconds") + " " + repr(startup_files) + "\n")
        except Exception:
            pass
    window = MainWindow(startup_files=startup_files, restore_session=restore_session)
    window.show()
    exit_code = app.exec()
    cleanup_embedded_image_cache()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
