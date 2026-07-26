"""Small accessible dialogs for HomerView.

Both OK and Cancel are left without a mnemonic on purpose. Windows already
gives Cancel to Escape and OK to Enter, so assigning them letters spends two
accelerators that a field or another button could use.
"""

import wx

import addonHandler
import gui

addonHandler.initTranslation()

dialogWidth = 520


class ExtensionsDialog(wx.Dialog):
    """Ask which file extensions to download."""

    def __init__(self, sPrompt, sExtensions):
        # Translators: Title of the dialog asking which files to download.
        super().__init__(gui.mainFrame, title=_("HomerView download"))
        boxOuter = wx.BoxSizer(wx.VERTICAL)
        # Translators: Label of the field listing file extensions to download.
        labelPrompt = wx.StaticText(self, label=sPrompt)
        labelPrompt.Wrap(dialogWidth)
        boxOuter.Add(labelPrompt, 0, wx.ALL, 10)
        # Translators: Label of the editable list of file extensions.
        self.labelExtensions = wx.StaticText(self, label=_("File extensions to download:"))
        boxOuter.Add(self.labelExtensions, 0, wx.LEFT | wx.RIGHT, 10)
        self.textExtensions = wx.TextCtrl(self, value=sExtensions, size=(dialogWidth, -1))
        boxOuter.Add(self.textExtensions, 0, wx.EXPAND | wx.ALL, 10)
        boxButtons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        boxOuter.Add(boxButtons, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(boxOuter)
        self.textExtensions.SetFocus()
        self.textExtensions.SetSelection(-1, -1)


def askForExtensions(sPrompt, sExtensions):
    """Show the dialog and return the text entered, or None if cancelled."""
    gui.mainFrame.prePopup()
    try:
        dialog = ExtensionsDialog(sPrompt, sExtensions)
        iResult = dialog.ShowModal()
        sValue = dialog.textExtensions.GetValue()
        dialog.Destroy()
    finally:
        gui.mainFrame.postPopup()
    return sValue if iResult == wx.ID_OK else None
