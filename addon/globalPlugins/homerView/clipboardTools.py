"""The Homer clipboard commands, on the apostrophe key.

The bindings are not invented here. FxMax and IEMax already settled them, and
following an existing standard is worth more than a fresh opinion:

    Alt+Apostrophe            Quote Clipboard, say the clipboard text
    Alt+Shift+Apostrophe      Clear Clipboard
    Control+Apostrophe        Export Clipboard to File
    Control+Shift+Apostrophe  Export Clipboard, appending to a file

FileDir uses Alt+Apostrophe and Alt+Shift+Apostrophe the same way, so the say
and clear keys are common to both the editor and the browser interfaces. Its
export sits on Alt+Shift+E because a file manager needs Control+Apostrophe for
something else; the browser packages are the closer precedent here, so their
Control+Apostrophe is what HomerView uses.

The proposed file name follows the same rule Homer used: a plain name first,
then a numbered variant when that name is taken, so repeated saves never
silently overwrite each other and never make the user think of a name.
"""

import wx
from pathlib import Path

import addonHandler
import api
import gui
import speech
import ui
from scriptHandler import getLastScriptRepeatCount

from . import paths
from .logger import abbreviate, homerLog, logError

addonHandler.initTranslation()

clipboardStem = "clipboard"
maximumNumberedNames = 100

sLastExportPath = ""


def getClipboardText():
    try:
        return api.getClipData() or ""
    except Exception:
        logError("The clipboard could not be read")
        return ""


def proposeFileName(pathFolder):
    """Return clipboard.txt, or clipboard-01.txt and so on when taken."""
    pathCandidate = pathFolder / f"{clipboardStem}.txt"
    if not pathCandidate.exists():
        return pathCandidate.name
    for iCount in range(1, maximumNumberedNames):
        pathCandidate = pathFolder / f"{clipboardStem}-{iCount:02d}.txt"
        if not pathCandidate.exists():
            return pathCandidate.name
    return f"{clipboardStem}-{maximumNumberedNames:02d}.txt"


def sayClipboard():
    """Say the clipboard text, spelling it when the key is repeated."""
    sText = getClipboardText()
    if not sText:
        # Translators: Reported when the clipboard holds no text.
        ui.message(_("The clipboard is empty"))
        return
    homerLog.info(f"Quote clipboard: {len(sText)} characters")
    if getLastScriptRepeatCount() == 0:
        speech.speakText(sText)
    else:
        speech.speakSpelling(sText)


def clearClipboard():
    try:
        api.copyToClip("")
    except Exception:
        logError("The clipboard could not be cleared")
        # Translators: Reported when clearing the clipboard failed.
        ui.message(_("The clipboard could not be cleared"))
        return
    homerLog.info("Clipboard cleared")
    # Translators: Reported after clearing the clipboard.
    ui.message(_("Clipboard cleared"))


def askForFile(bAppend):
    """Show a save dialog with a proposed name, and return the chosen path."""
    global sLastExportPath
    pathFolder = paths.getDownloadsFolder()
    sProposed = Path(sLastExportPath).name if (bAppend and sLastExportPath) else proposeFileName(pathFolder)
    sFolder = str(Path(sLastExportPath).parent) if sLastExportPath else str(pathFolder)
    gui.mainFrame.prePopup()
    try:
        dialog = wx.FileDialog(
            gui.mainFrame,
            # Translators: Title of the dialog for saving the clipboard.
            message=_("Append the clipboard to a text file") if bAppend
            # Translators: Title of the dialog for saving the clipboard.
            else _("Save the clipboard to a text file"),
            defaultDir=sFolder,
            defaultFile=sProposed,
            wildcard=_("Text files") + " (*.txt)|*.txt|" + _("All files") + " (*.*)|*.*",
            style=wx.FD_SAVE | (0 if bAppend else wx.FD_OVERWRITE_PROMPT),
        )
        iResult = dialog.ShowModal()
        sPath = dialog.GetPath()
        dialog.Destroy()
    finally:
        gui.mainFrame.postPopup()
    return sPath if iResult == wx.ID_OK else ""


def exportClipboard(bAppend):
    """Write the clipboard to a file, once the calling script has returned."""
    from .homer import lbc

    lbc.afterScript(_exportClipboardNow, bAppend)


def _exportClipboardNow(bAppend):
    """Write the clipboard to a file, replacing it or adding to the end."""
    global sLastExportPath
    sText = getClipboardText()
    if not sText:
        # Translators: Reported when the clipboard holds no text.
        ui.message(_("The clipboard is empty"))
        return
    sPath = askForFile(bAppend)
    if not sPath:
        homerLog.info("Clipboard export cancelled")
        return
    pathTarget = Path(sPath)
    try:
        if bAppend and pathTarget.exists():
            # A section break, as Homer uses, so the file stays navigable by
            # section in an editor rather than becoming one long run of text.
            sExisting = pathTarget.read_text(encoding="utf-8", errors="replace")
            sSeparator = "" if sExisting.endswith("\n") else "\n"
            sBody = f"{sExisting}{sSeparator}{'-' * 10}\n\f\n{sText}"
        else:
            sBody = sText
        pathTarget.write_text(sBody, encoding="utf-8", newline="\r\n")
    except Exception:
        logError(f"The clipboard could not be written to {sPath}")
        # Translators: Reported when saving the clipboard failed.
        ui.message(_("The clipboard could not be saved"))
        return
    sLastExportPath = str(pathTarget)
    homerLog.info(f"Clipboard {'appended to' if bAppend else 'saved to'} {pathTarget}")
    if bAppend:
        # Translators: Reported after appending the clipboard to a file.
        ui.message(_("Appended to {name}").format(name=pathTarget.name))
    else:
        # Translators: Reported after saving the clipboard to a file.
        ui.message(_("Saved as {name}").format(name=pathTarget.name))


def appendToClipboard(sText):
    """Add text to the clipboard rather than replacing what is there.

    Homer's rule: when the existing text does not end with a line break, one is
    inserted first, so appended pieces stay on separate lines.
    """
    sExisting = getClipboardText()
    if sExisting:
        sSeparator = "" if sExisting.endswith("\n") else "\n"
        sCombined = f"{sExisting}{sSeparator}{sText}"
    else:
        sCombined = sText
    try:
        api.copyToClip(sCombined)
    except Exception:
        logError("The clipboard could not be appended to")
        return False
    homerLog.info(f"Appended {len(sText)} characters, clipboard now {len(sCombined)}")
    homerLog.debug(f"Appended text: {abbreviate(sText, 200)}")
    return True
