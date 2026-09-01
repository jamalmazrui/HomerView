"""Choosing which Chromium browser HomerView drives.

A dialog rather than a picklist, because choosing a browser is not choosing a
command. Three things have to be said about each candidate and a one line
picker cannot say them: what it is called, where it is, and whether it has
been proved to work here.

THE TEST IS THE POINT OF THE DIALOG. Any list of browsers is a guess about
what is Chromium and what is not, and the guess is wrong in both directions:
a fork can have remote debugging removed, and a browser nobody has heard of
can have it. So Test starts the candidate on a throwaway profile, watches for
the file it writes when it opens a debugging port, and closes it again. That
takes a few seconds and it answers the question for this machine rather than
in general.

WHAT CHANGING IT COSTS, said before it is changed rather than after. On JAWS
the keys are bound inside the browser's own key map, named after that
browser, so a new browser means those files have to be written again for it
and the old ones removed. The dialog says so and offers to do it.
"""

import os, subprocess
from pathlib import Path

import wx

import addonHandler
import gui

from . import browsers
from .logger import homerLog, logError

addonHandler.initTranslation()

dialogWidth = 620


class BrowserDialog(wx.Dialog):
    """Pick a browser, with room to say why one is a better answer."""

    def __init__(self, lFound, sCurrentPath):
        # Translators: Title of the dialog for choosing HomerView's browser.
        super().__init__(gui.mainFrame, title=_("HomerView browser"))
        self.lFound = lFound
        boxOuter = wx.BoxSizer(wx.VERTICAL)

        # Translators: Introduction in the browser dialog.
        labelPrompt = wx.StaticText(self, label=_(
            "HomerView drives the browser through the Chrome DevTools Protocol, "
            "so any Chromium browser will do. Choose one, and use Test if you "
            "are not sure it will work."))
        labelPrompt.Wrap(dialogWidth)
        boxOuter.Add(labelPrompt, 0, wx.ALL, 10)

        # Translators: Label of the list of browsers found on this computer.
        self.labelList = wx.StaticText(self, label=_("&Browsers found on this computer:"))
        boxOuter.Add(self.labelList, 0, wx.LEFT | wx.RIGHT, 10)
        self.listBrowsers = wx.ListBox(
            self, choices=[self._describe(d) for d in lFound],
            size=(dialogWidth, 200), style=wx.LB_SINGLE)
        boxOuter.Add(self.listBrowsers, 1, wx.EXPAND | wx.ALL, 10)

        boxButtons = wx.BoxSizer(wx.HORIZONTAL)
        # Translators: Button that tests whether a browser can be driven.
        self.buttonTest = wx.Button(self, label=_("&Test this browser"))
        self.buttonTest.Bind(wx.EVT_BUTTON, self.onTest)
        boxButtons.Add(self.buttonTest, 0, wx.RIGHT, 10)
        boxOuter.Add(boxButtons, 0, wx.LEFT | wx.RIGHT, 10)

        boxOuter.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(boxOuter)

        # Opened on the browser in use, so the commonest answer -- looking to
        # see what is set -- needs no reading of the list at all.
        iSelected = 0
        for iIndex, dBrowser in enumerate(lFound):
            if sCurrentPath and dBrowser["path"].lower() == sCurrentPath.lower():
                iSelected = iIndex
        if lFound:
            self.listBrowsers.SetSelection(iSelected)
        self.listBrowsers.SetFocus()

    def _describe(self, dBrowser):
        """One line per browser: what it is, and where it came from."""
        return "%s  --  %s  (%s)" % (dBrowser["name"], dBrowser["path"], dBrowser["how"])

    def chosen(self):
        iIndex = self.listBrowsers.GetSelection()
        if iIndex < 0 or iIndex >= len(self.lFound):
            return None
        return self.lFound[iIndex]

    def onTest(self, event):
        """Start the selected browser, watch for a debugging port, close it."""
        dBrowser = self.chosen()
        if not dBrowser:
            return
        from . import paths

        pathTest = Path(paths.getDataFolder()) / "BrowserTest"
        self.buttonTest.Disable()
        # Translators: Reported while a browser is being tested.
        self.labelList.SetLabel(_("Testing {name}, which takes a few seconds...").format(
            name=dBrowser["name"]))
        wx.Yield()
        try:
            bWorks, sWhy = browsers.canBeDriven(dBrowser["path"], pathTest)
        except Exception:
            logError("Testing the browser raised")
            bWorks, sWhy = False, _("the test could not be run")
        self.buttonTest.Enable()
        # Translators: Label of the list of browsers found on this computer.
        self.labelList.SetLabel(_("&Browsers found on this computer:"))
        if bWorks:
            # Translators: Reported when a browser passed the test.
            sMessage = _("{name} can be driven: {why}.").format(
                name=dBrowser["name"], why=sWhy)
        else:
            # Translators: Reported when a browser failed the test.
            sMessage = _("{name} cannot be used: {why}.").format(
                name=dBrowser["name"], why=sWhy)
        gui.messageBox(sMessage, _("HomerView browser test"), wx.OK | wx.ICON_INFORMATION)
        self.listBrowsers.SetFocus()


def rewriteJawsKeys(sBrowserPath):
    """Bind the JAWS keys inside the new browser instead of the old one.

    JAWS names an application script set after the executable, so the keys
    HomerView binds live in a file called after whichever browser was chosen.
    Change the browser and those files are for the wrong program: the new one
    has no HomerView keys and the old one still has all of them.

    chainJawsScripts does the whole of it, including removing the previous
    browser's files, and it needs no administrator rights because JAWS
    settings belong to the user. It is given the browser explicitly rather
    than left to read the file this function has just written, since a value
    read back is one more thing that can be wrong.

    Silent when JAWS is not installed. Nothing is missing in that case.
    """
    from . import paths

    pathScript = paths.findSharedFile("chainJawsScripts.cmd")
    if not pathScript:
        homerLog.info("chainJawsScripts is not installed here, so there are no JAWS keys to rewrite")
        return False, ""
    lCommand = [str(pathScript), "-sBrowserExe", os.path.basename(sBrowserPath)]
    homerLog.info(f"Rewriting the JAWS keys: {lCommand}")
    try:
        oResult = subprocess.run(
            lCommand, capture_output=True, text=True, timeout=180,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as exception:
        logError(f"chainJawsScripts could not be run: {exception}")
        return False, str(exception)
    homerLog.info(f"chainJawsScripts finished with exit code {oResult.returncode}")
    for sLine in (oResult.stdout or "").splitlines()[-20:]:
        homerLog.debug(f"  {sLine}")
    return oResult.returncode == 0, (oResult.stdout or "").strip()


def chooseBrowser():
    """Show the dialog, remember the answer, and rebind the JAWS keys."""
    gui.mainFrame.prePopup()
    try:
        lFound = browsers.findBrowsers()
        _sName, sCurrent = browsers.chosenBrowser()
        if not lFound:
            gui.messageBox(
                # Translators: Reported when no browser could be found.
                _("No Chromium browser could be found on this computer. HomerView "
                  "needs Microsoft Edge, Google Chrome, Brave, Vivaldi or another "
                  "browser built on Chromium."),
                _("HomerView browser"), wx.OK | wx.ICON_WARNING)
            return
        dialog = BrowserDialog(lFound, sCurrent)
        iResult = dialog.ShowModal()
        dBrowser = dialog.chosen()
        dialog.Destroy()
    finally:
        gui.mainFrame.postPopup()
    if iResult != wx.ID_OK or not dBrowser:
        homerLog.info("The browser was not changed")
        return
    if sCurrent and dBrowser["path"].lower() == sCurrent.lower():
        homerLog.info("The same browser was chosen, so nothing is changed")
        gui.messageBox(
            # Translators: Reported when the browser chosen is the one already in use.
            _("{name} is already the browser HomerView uses.").format(name=dBrowser["name"]),
            _("HomerView browser"), wx.OK | wx.ICON_INFORMATION)
        return

    browsers.rememberBrowser(dBrowser["name"], dBrowser["path"])
    bJaws, _sOutput = rewriteJawsKeys(dBrowser["path"])

    # SAID PLAINLY, BECAUSE NEITHER CHANGE TAKES EFFECT WHERE THE READER IS
    # STANDING. A browser already open is still the old one until it is closed,
    # and JAWS reads its key maps when it loads them.
    lLines = [
        # Translators: Reported after the browser has been changed.
        _("HomerView will now use {name}.").format(name=dBrowser["name"]),
        "",
        # Translators: Told to the user after changing the browser.
        _("Close the HomerView browser window if one is open, then press "
          "Alt+Control+Shift+H to start the new one."),
    ]
    if bJaws:
        lLines.append("")
        # Translators: Told to the user when the JAWS keys have been rewritten.
        lLines.append(_("The JAWS keys have been bound inside {name}. Restart JAWS "
                        "for them to take effect.").format(name=dBrowser["name"]))
    gui.messageBox("\n".join(lLines), _("HomerView browser"), wx.OK | wx.ICON_INFORMATION)
