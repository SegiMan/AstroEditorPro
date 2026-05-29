# AstroEditorPro v9 spellcheck language manager

New spellcheck behavior:

- Preferences now contains **Spellcheck languages...**
- Tools now contains **Spellcheck languages...**
- Users can tick any number of installed Hunspell dictionaries.
- Missing dictionaries show as missing and can be installed from inside the app.
- Trying to enable a missing language asks whether to install its Hunspell package.
- Installation opens a terminal and runs `sudo apt-get install`.
- The custom dictionary is visible, reloadable, and can be opened from the dialog.
- User-added words from the spellcheck right-click menu are saved in the custom dictionary.

Custom dictionary path in installed public builds:

```text
~/.local/share/astroeditorpro/user_dictionary.txt
```


Run `bash install.sh` to install/update from this repository.
