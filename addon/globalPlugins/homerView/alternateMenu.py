"""One list of every command, presented two ways.

The Homer interface has two commands for finding other commands. The Alternate
Menu, Alt+F10, puts all of them in a single alphabetised list box, so a command
can be run without remembering its key. The Hotkey Summary, Alt+Shift+H, shows
the same set as a document that can be read and searched.

Both read from one table. A command that exists but is unbound still appears,
with its key shown as none, because a command nobody can find is no better than
one that does not exist.

The list box shows the name first and the key after it, so first-letter
navigation lands on the command name rather than on a modifier.
"""

import wx

import addonHandler

from . import output
import gui
import ui

from .logger import homerLog

addonHandler.initTranslation()

dialogHeight = 460
dialogWidth = 620


class CommandEntry:
    def __init__(self, sName, sGesture, sDescription, functionAction, sScope):
        self.functionAction = functionAction
        self.sDescription = sDescription
        self.sGesture = sGesture
        self.sName = sName
        self.sScope = sScope

    @property
    def sLabel(self):
        # Translators: Shown in the command list when a command has no key.
        sGesture = self.sGesture or _("none")
        return f"{self.sName}, {sGesture}"


class AlternateMenuDialog(wx.Dialog):
    """A single alphabetised list of commands, run with Enter."""

    def __init__(self, lEntries):
        # Translators: Title of the dialog listing all HomerView commands.
        super().__init__(gui.mainFrame, title=_("HomerView commands"))
        self.lEntries = lEntries
        boxOuter = wx.BoxSizer(wx.VERTICAL)
        # Translators: Label of the list of commands.
        labelList = wx.StaticText(self, label=_("Command, and key:"))
        boxOuter.Add(labelList, 0, wx.ALL, 10)
        self.listCommands = wx.ListBox(
            self,
            choices=[entry.sLabel for entry in lEntries],
            size=(dialogWidth, dialogHeight - 160),
        )
        boxOuter.Add(self.listCommands, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.labelDescription = wx.StaticText(self, label="", size=(dialogWidth, 48))
        boxOuter.Add(self.labelDescription, 0, wx.ALL, 10)
        boxButtons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        boxOuter.Add(boxButtons, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(boxOuter)
        if lEntries:
            self.listCommands.SetSelection(0)
            self._showDescription(0)
        self.listCommands.Bind(wx.EVT_LISTBOX, self._onSelect)
        self.listCommands.Bind(wx.EVT_LISTBOX_DCLICK, lambda event: self.EndModal(wx.ID_OK))
        self.listCommands.SetFocus()

    def _onSelect(self, event):
        self._showDescription(event.GetSelection())

    def _showDescription(self, iIndex):
        if 0 <= iIndex < len(self.lEntries):
            self.labelDescription.SetLabel(self.lEntries[iIndex].sDescription)


def showAlternateMenu(lEntries):
    """Show the menu after the current script returns, then run the choice.

    Showing it during the script left NVDA believing focus was still in the
    page: a real session recorded arrow keys resolving to the page's own line
    navigation while the menu sat open and silent.
    """
    wx.CallAfter(_showAlternateMenu, lEntries)


def _showAlternateMenu(lEntries):
    # The command that opened this menu has no business being in it.
    lEntries = [e for e in lEntries if "alternate menu" not in e.sName.lower()]
    lSorted = sorted(lEntries, key=lambda entry: entry.sName.lower())
    homerLog.info(f"Alternate menu: {len(lSorted)} commands")
    gui.mainFrame.prePopup()
    try:
        dialog = AlternateMenuDialog(lSorted)
        iResult = dialog.ShowModal()
        iSelection = dialog.listCommands.GetSelection()
        dialog.Destroy()
    finally:
        gui.mainFrame.postPopup()
    if iResult != wx.ID_OK or iSelection < 0:
        homerLog.info("Alternate menu cancelled")
        return
    entry = lSorted[iSelection]
    homerLog.info(f"Alternate menu chose: {entry.sName}")
    # Wait for focus to finish returning to the page before running anything.
    #
    # Closing the dialog hands focus back to the document, and NVDA announces
    # that document as it arrives. A command run in that instant speaks into
    # the announcement and is cut off by it: the log shows the command ran and
    # produced its answer, and the user heard nothing. Letting the transition
    # finish first is the whole fix, and it costs a fraction of a second.
    wx.CallLater(settleMilliseconds, runChosenCommand, entry)


settleMilliseconds = 350


def runChosenCommand(entry):
    homerLog.info(f"Running {entry.sName} now that focus has settled")
    try:
        entry.functionAction()
    except Exception as exception:
        homerLog.exception(f"The command {entry.sName} failed from the menu")
        # A generic apology tells the user nothing and tells a bug report even
        # less. Naming the command and the fault means one spoken sentence is
        # enough to act on.
        # Translators: Reported when a command run from the menu failed. The
        # placeholders are the command name and the fault.
        ui.message(
            _("{name} failed: {reason}. The log has the detail.").format(
                name=entry.sName, reason=type(exception).__name__
            )
        )


def buildSummaryHtml(lEntries):
    """Return the same set as a document, grouped by where each command works."""
    import html

    def escape(sValue):
        return html.escape(str(sValue or ""), quote=True)

    dGroups = {}
    for entry in lEntries:
        dGroups.setdefault(entry.sScope, []).append(entry)
    lParts = ["<h1>HomerView commands</h1>"]
    lParts.append(
        "<p>Every command below also appears in NVDA's Input Gestures dialog under the "
        "HomerView category, where its key can be changed. Commands shown with no key "
        "have none assigned and can be run from the Alternate Menu on Alt+F10.</p>"
    )
    for sScope in sorted(dGroups):
        lParts.append(f"<h2>{escape(sScope)}</h2>")
        lParts.append("<table>")
        lParts.append("<thead><tr><th>Command</th><th>Key</th><th>What it does</th></tr></thead>")
        lParts.append("<tbody>")
        for entry in sorted(dGroups[sScope], key=lambda e: e.sName.lower()):
            lParts.append(
                f"<tr><td>{escape(entry.sName)}</td>"
                f"<td>{escape(entry.sGesture or 'none')}</td>"
                f"<td>{escape(entry.sDescription)}</td></tr>"
            )
        lParts.append("</tbody></table>")
    return "\n".join(lParts)


def showHotkeySummary(lEntries):
    from .homer import lbc

    lbc.afterScript(_showHotkeySummaryNow, lEntries)


def _showHotkeySummaryNow(lEntries):
    wx.CallAfter(_showHotkeySummary, lEntries)


def _showHotkeySummary(lEntries):
    sHtml = buildSummaryHtml(lEntries)
    # Translators: Title of the window listing all HomerView commands.
    sTitle = _("HomerView commands")
    output.show(sHtml, sTitle)
