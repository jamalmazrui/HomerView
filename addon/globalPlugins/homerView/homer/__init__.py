"""The Homer toolkit for NVDA add-ons.

This is the Python counterpart of the C# Homer namespace: a set of modules that
several programs need, kept in one place so a fix reaches all of them.

Three rules make it shareable, and they are the whole design.

Nothing here imports NVDA at module level. Where an NVDA facility is needed, it
is imported inside the function that needs it and falls back when absent. That
keeps every module importable and testable in a plain Python interpreter, which
is how the tests run and how the same code can serve a program that is not an
add-on at all.

Nothing here depends on anything outside the standard library, except wx, which
NVDA's own interface is built on and so is always present.

Nothing here knows about the program using it. No module reads a HomerView path,
a HomerView setting, or a HomerView constant.

**How another add-on uses this.** Copy the homer folder into your add-on and
import from it relatively:

    from .homer import lbc, web

NVDA has no dependency manager for add-ons, and that is the reason for copying
rather than sharing one installed copy. A library add-on that put itself on
sys.path would work until load order changed, or until a user removed it without
knowing three other add-ons depended on it, and NVDA's add-on store has no way
to declare that dependency or prevent the removal. Copying costs a re-copy when
a fix lands; sharing costs silent breakage in someone else's add-on. The C#
Homer modules make the same trade for the same reason: "to reuse elsewhere, copy
this file as-is."

Because no module imports NVDA, the same folder also works in a standalone
program, which is what makes it worth publishing on its own.

Modules:

    inix    Order preserving ini and inix configuration files.
    lbc     Layout by Code: accessible dialogs built in code.
    say     One way to announce text, whatever is listening.
    version Comparing and checking versions against a GitHub release.
    web     Dependency free HTTP with browser-like behaviour.

**What Lbc gives every dialog.** These are the same conveniences the C#
Lbc provides, and they exist because a person who cannot see the dialog needs
to be told things a sighted user can simply look at.

    Control+Enter    accept the dialog from any control, including a
                     multi-line field or a list, which swallow plain Enter
    Shift+F1         speak the tip for the control that has focus
    Control+A        select all, and say so
    Control+Shift+A  clear the selection, and say so
    Control+C        copy the current line, or the current list item
    Alt+C            append the same to the clipboard
    Control+J        find a substring in a list, not case sensitive
    Control+Shift+J  the same, backwards
    F3, Shift+F3     repeat that search without being asked again
    F4               open a pick list, where the field was given one

OK and Cancel never carry a mnemonic, because Windows already gives Cancel to
Escape and OK to Enter, and spending two accelerators on them takes letters a
field could use.
"""

toolkitVersion = "1.0.0"

__all__ = ["inix", "lbc", "say", "version", "web"]

# --- A shared Homer folder, when one exists -------------------------------
#
# The copy above is the one that ships. This lets a machine that also has a
# shared Homer folder use modules from it that were never vendored, without
# any add-on depending on that folder existing.
#
# Two locations are looked for, in order:
#
#   The NVDA developer scratchpad, at %APPDATA%\nvda\scratchpad\homer. This
#   is NVDA's own supported place for code a developer maintains outside an
#   add-on. It is off by default and has to be enabled under Advanced
#   settings, and NVDA states plainly that it is for development rather than
#   for distribution, which is exactly the right shape for a single machine
#   holding the authoritative copy.
#
#   A Homer program folder, beside the other Homer tools, for an installation
#   that keeps shared assets in Program Files.
#
# Vendored modules win by default: a shared folder can add modules but cannot
# silently replace one an add-on shipped and tested against. Set
# bPreferSharedFolder to True on a development machine to reverse that and
# make the shared folder authoritative.

import os

bPreferSharedFolder = False

def _nvdaConfigFolder():
    """Walk up from this file to NVDA's configuration folder.

    ...\\nvda\\addons\\<addon>\\globalPlugins\\<package>\\homer\\__init__.py,
    so five levels up is the nvda folder. Any add-on can reach the same shared
    folder by the same walk, which is what makes one copy serve several.
    """
    try:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
    except Exception:
        return ""


lSharedFolderNames = [
    os.path.join(_nvdaConfigFolder(), "Homer", "python", "homer"),
    os.path.join(_nvdaConfigFolder(), "scratchpad", "homer"),
    os.path.join(os.environ.get("APPDATA", ""), "nvda", "scratchpad", "homer"),
    os.path.join(os.environ.get("PROGRAMFILES", ""), "Homer", "python", "homer"),
]


def sharedFolders():
    """Return the shared Homer folders that actually exist."""
    return [s for s in lSharedFolderNames if s and os.path.isdir(s)]


def _extendSearchPath():
    for sFolder in sharedFolders():
        if sFolder in __path__:
            continue
        if bPreferSharedFolder:
            __path__.insert(0, sFolder)
        else:
            __path__.append(sFolder)


_extendSearchPath()
