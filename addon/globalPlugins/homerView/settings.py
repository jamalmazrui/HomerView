"""HomerView.inix: preferences and the values last typed.

Kept in the roaming application data folder, beside NVDA's own configuration,
because a preference belongs with the user rather than with the installation.
It survives reinstalling, and it does not need administrator rights to write.

The inix format is used rather than JSON because a person may want to read and
edit this by hand, and inix keeps their comments, their blank lines and their
ordering when HomerView writes a value back. A configuration someone has edited
should come back as they left it.

Values last typed are stored alongside the settings on purpose. Retyping a
percentage, a search pattern or a script that was almost right is exactly the
sort of small friction that makes a program tiring to use.
"""

import os
from pathlib import Path

from .homer import inix
from .logger import abbreviate, homerLog, logError

settingsFileName = "HomerView.inix"

# Written on first run, so the file explains itself to anyone who opens it.
defaultText = """; HomerView settings
;
; Edit freely. Comments, blank lines and ordering are preserved when HomerView
; writes a value back, so anything you add here stays where you put it.

[Preferences]
; Say a label before a reported value, as JAWS does. NVDA's own report commands
; speak the value alone, so this is off by default.
speakCommandLabels=False
; Reopen the page the browser last had open, rather than the start page.
reopenLastPage=True
; Show reports as a page in the browser rather than in NVDA's message window.
preferTemporaryPage=True

[Recent]
; Values last typed. HomerView maintains these; there is no need to edit them.
"""


def getSettingsPath():
    from . import paths

    return paths.getSettingsFolder() / settingsFileName


def ensureSettings():
    pathSettings = getSettingsPath()
    if not pathSettings.is_file():
        try:
            pathSettings.write_text(defaultText, encoding="utf-8-sig", newline="\r\n")
            homerLog.info(f"Wrote a fresh settings file at {pathSettings}")
        except OSError:
            logError(f"The settings file could not be created at {pathSettings}")
    return pathSettings


def getValue(sSection, sKey, sDefault=""):
    sValue = inix.getValue(str(ensureSettings()), sSection, sKey, sDefault)
    homerLog.debug(f"Setting {sSection}.{sKey} is {abbreviate(sValue, 120)}")
    return sValue


def setValue(sSection, sKey, sValue):
    bWritten = inix.setValue(str(ensureSettings()), sSection, sKey, sValue)
    homerLog.debug(f"Setting {sSection}.{sKey} set to {abbreviate(str(sValue), 120)}")
    return bWritten


def getFlag(sKey, bDefault=False):
    sValue = getValue("Preferences", sKey, "True" if bDefault else "False")
    return str(sValue).strip().lower() in ("true", "yes", "1", "on")


def getRecent(sKey, sDefault=""):
    return getValue("Recent", sKey, sDefault)


def setRecent(sKey, sValue):
    return setValue("Recent", sKey, str(sValue))
