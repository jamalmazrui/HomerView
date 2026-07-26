"""Layout by Code: accessible dialogs built in code rather than in a designer.

This is a Python 3 rewrite of the original pyLbc for wxPython, intended to stand
on its own as a library and to work unchanged inside an NVDA add-on. Four
changes were needed to get there.

The dependency on win32api is gone. It was used for one thing, reading a value
from an ini file, which the standard library's configparser does properly. An
NVDA add-on cannot rely on pywin32 being present, and a library that needs it
excludes every embedded interpreter that does not ship it.

Names follow Camel Type: lowerCamelCase methods, Hungarian prefixes on typed
variables. The original PascalCase came from a VBScript lineage that no longer
applies.

The dialog no longer creates or exits a wx.App of its own when one already
exists. Inside NVDA one always does, and taking over the application object of a
running screen reader would be a serious thing to do by accident.

Finally, the parent window is resolved rather than assumed. Inside NVDA that
means NVDA's own main frame, together with the prePopup and postPopup calls
that let NVDA track a dialog properly; outside it, whatever top window exists.

The accessibility rules from the original are kept and are the reason this
exists at all:

    OK and Cancel never carry a mnemonic. Windows already gives Cancel to
    Escape and OK to Enter, so spending two accelerators on them takes letters
    a field or another button could use.

    Control+Enter submits from any control. Plain Enter is swallowed by controls
    that handle it themselves, such as a multi-line edit or a list, so a user
    who is deep in a form has no reliable way out. This is the original's own
    innovation and it is preserved exactly.

    A label placed beside a text control is not automatically that control's
    accessible name. The label text is therefore copied into AccessibleName, and
    this is load bearing rather than redundant. Buttons and check boxes are
    unaffected, because their text belongs to the control itself.
"""

import configparser
import os
from collections import OrderedDict

import wx

borderPad = 2
buttonWidth = 100
defaultEditHeight = 200
defaultEditWidth = 260
defaultInputWidth = 260
defaultListHeight = 140
defaultListWidth = 260
horizontalDividerPad = 14
horizontalLabelPad = 6
verticalDividerPad = 14
verticalRelatedPad = 8

lNoMnemonicLabels = ["ok", "cancel"]


def stripMnemonic(sLabel):
    """Return a label without its ampersand marker."""
    return str(sLabel or "").replace("&", "")


def fixLabel(sLabel):
    """Keep OK and Cancel free of a mnemonic, however they were written."""
    sPlain = stripMnemonic(sLabel)
    if sPlain.strip().lower() in lNoMnemonicLabels:
        return sPlain
    return sLabel


def getHostParent():
    """Return the window a dialog should belong to.

    Inside NVDA that is NVDA's own main frame. Elsewhere it is whatever top
    window the application has, or nothing.
    """
    try:
        import gui

        return gui.mainFrame
    except Exception:
        pass
    app = wx.GetApp()
    return app.GetTopWindow() if app else None


def showLater(functionShow):
    """Show a dialog after the current script has finished, never during it.

    This is not a nicety. A screen reader script runs on the same thread that
    processes the screen reader's own events. Calling ShowModal inside a script
    opens a nested event loop while the screen reader is still waiting for that
    script to return, so the focus change into the dialog is never processed.
    The dialog appears, accepts Enter, and is completely silent, because as far
    as the screen reader is concerned focus never left the page underneath: a
    real session showed arrow keys still moving the browse cursor of the page
    behind the open dialog.

    Deferring with CallAfter lets the script return first. The screen reader
    then processes the focus change normally and the dialog speaks.
    """
    wx.CallAfter(functionShow)


def afterScript(functionCallable, *lArguments):
    """Run something once the current screen reader script has finished.

    A modal dialog opened from inside a script is a trap. The script has not
    returned, so NVDA is still executing it and has not processed the focus
    change to the dialog. The window appears and works, because wx has its own
    event loop, but NVDA never learns it exists: nothing is announced, and every
    keystroke is still routed to whatever had focus before, which is why arrow
    keys go on moving through the web page underneath.

    Deferring to the main loop lets the script return first. NVDA then sees the
    dialog appear as an ordinary foreground change, announces it, and routes
    keys to it. NVDA provides runScriptModalDialog for the same reason; this is
    the same idea in a form that keeps the dialog functions synchronous.
    """
    try:
        wx.CallAfter(functionCallable, *lArguments)
        return True
    except Exception:
        functionCallable(*lArguments)
        return False


def beforeDialog():
    """Tell NVDA a dialog is opening, when running inside it."""
    try:
        import gui

        gui.mainFrame.prePopup()
        return True
    except Exception:
        return False


def afterDialog(bNotified):
    if not bNotified:
        return
    try:
        import gui

        gui.mainFrame.postPopup()
    except Exception:
        pass


def readIniValue(sPath, sSection, sName, sDefault=""):
    """Read one value from an ini file, without pywin32."""
    try:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(sPath, encoding="utf-8-sig")
        return parser.get(sSection, sName, fallback=sDefault)
    except Exception:
        return sDefault


def writeIniValue(sPath, sSection, sName, sValue):
    try:
        parser = configparser.ConfigParser(interpolation=None)
        if os.path.isfile(sPath):
            parser.read(sPath, encoding="utf-8-sig")
        if not parser.has_section(sSection):
            parser.add_section(sSection)
        parser.set(sSection, sName, str(sValue))
        with open(sPath, "w", encoding="utf-8") as fFile:
            parser.write(fFile)
        return True
    except Exception:
        return False


class Dialog(wx.Dialog):
    """A dialog assembled a band at a time, top to bottom.

    A band is one horizontal row. Controls added after addBand share that row;
    calling addBand again starts the next one. That is the whole layout model,
    and it is enough for the forms this kind of program needs.
    """

    def __init__(self, parent=None, sTitle="Dialog", bResizable=True):
        iStyle = wx.DEFAULT_DIALOG_STYLE | (wx.RESIZE_BORDER if bResizable else 0)
        super().__init__(parent=parent or getHostParent(), title=sTitle, style=iStyle)
        self.dControls = OrderedDict()
        self.dResults = {}
        self.functionHandler = None
        self.iBand = 0
        self.lSizers = [wx.BoxSizer(wx.VERTICAL)]
        self.lSizers[0].Add(wx.Size(1, verticalDividerPad))
        self.SetName(f"Dialog {sTitle}")
        self.addBand()
        self._bindSubmitKeys()

    # --- Layout ---------------------------------------------------------

    def addBand(self):
        if self.iBand > 0:
            self.lSizers[self.iBand].Add(wx.Size(horizontalLabelPad, 1))
            self.lSizers[0].Add(self.lSizers[self.iBand], 0, wx.GROW)
        self.lSizers[0].Add(wx.Size(1, verticalRelatedPad))
        self.lSizers.append(wx.BoxSizer(wx.HORIZONTAL))
        self.iBand += 1
        self.lSizers[self.iBand].Add(wx.Size(horizontalDividerPad, 1))

    def _place(self, control, iProportion=0):
        self.lSizers[self.iBand].Add(control, iProportion, wx.ALIGN_CENTER_VERTICAL | wx.ALL, borderPad)
        return control

    def _remember(self, sName, control):
        self.dControls[sName or control.GetName()] = control
        return control

    # --- Controls -------------------------------------------------------

    def addStaticText(self, sLabel="", sName=""):
        label = wx.StaticText(self, label=sLabel)
        return self._remember(sName or stripMnemonic(sLabel), self._place(label))

    def addButton(self, sLabel="", bDefault=False, sName=""):
        sLabel = fixLabel(sLabel)
        sPlain = stripMnemonic(sLabel).strip().lower()
        iId = wx.ID_OK if sPlain == "ok" else (wx.ID_CANCEL if sPlain == "cancel" else wx.ID_ANY)
        button = wx.Button(self, id=iId, label=sLabel)
        if bDefault:
            button.SetDefault()
        button.Bind(wx.EVT_BUTTON, self._onButton)
        return self._remember(sName or stripMnemonic(sLabel), self._place(button))

    def addButtonBand(self, lLabels=None, iDefault=0, functionHandler=None):
        self.functionHandler = functionHandler
        self.addBand()
        for iIndex, sLabel in enumerate(lLabels or ["OK", "Cancel"]):
            self.addButton(sLabel, bDefault=(iIndex == iDefault))

    def addCheckBox(self, sLabel="", bValue=False, sName=""):
        checkBox = wx.CheckBox(self, label=sLabel)
        checkBox.SetValue(bool(bValue))
        return self._remember(sName or stripMnemonic(sLabel), self._place(checkBox))

    def addInputBox(self, sLabel="", sValue="", sName="", iWidth=defaultInputWidth):
        """A labelled single line field.

        The label is copied into the field's accessible name. A label placed
        beside a text control is not automatically announced as that control's
        name, so removing this line silently makes the field anonymous.
        """
        if sLabel:
            self._place(wx.StaticText(self, label=sLabel))
        textCtrl = wx.TextCtrl(self, value=str(sValue), size=(iWidth, -1))
        if sLabel:
            textCtrl.SetName(stripMnemonic(sLabel))
            try:
                textCtrl.GetAccessible().SetName(stripMnemonic(sLabel))
            except Exception:
                pass
        return self._remember(sName or stripMnemonic(sLabel), self._place(textCtrl, 1))

    def addMemo(self, sLabel="", sValue="", bReadOnly=False, sName="",
                iWidth=defaultEditWidth, iHeight=defaultEditHeight):
        if sLabel:
            self.addStaticText(sLabel)
            self.addBand()
        iStyle = wx.TE_MULTILINE | (wx.TE_READONLY if bReadOnly else 0)
        textCtrl = wx.TextCtrl(self, value=str(sValue), size=(iWidth, iHeight), style=iStyle)
        if sLabel:
            textCtrl.SetName(stripMnemonic(sLabel))
        return self._remember(sName or stripMnemonic(sLabel), self._place(textCtrl, 1))

    def addListBox(self, sLabel="", lNames=None, iSelection=0, sName="",
                   iWidth=defaultListWidth, iHeight=defaultListHeight):
        if sLabel:
            self.addStaticText(sLabel)
            self.addBand()
        listBox = wx.ListBox(self, choices=list(lNames or []), size=(iWidth, iHeight))
        if lNames:
            listBox.SetSelection(max(0, min(iSelection, len(lNames) - 1)))
        if sLabel:
            listBox.SetName(stripMnemonic(sLabel))
        return self._remember(sName or stripMnemonic(sLabel), self._place(listBox, 1))

    def addChoice(self, sLabel="", lNames=None, iSelection=0, sName=""):
        if sLabel:
            self._place(wx.StaticText(self, label=sLabel))
        choice = wx.Choice(self, choices=list(lNames or []))
        if lNames:
            choice.SetSelection(max(0, min(iSelection, len(lNames) - 1)))
        if sLabel:
            choice.SetName(stripMnemonic(sLabel))
        return self._remember(sName or stripMnemonic(sLabel), self._place(choice, 1))

    # --- Behaviour ------------------------------------------------------

    def _bindSubmitKeys(self):
        """Control+Enter submits from anywhere in the dialog.

        Plain Enter is consumed by controls that handle it themselves, so a
        user inside a multi-line field or a list has no reliable way to accept
        the dialog. An accelerator reaches the dialog whatever has focus.
        """
        iSubmitId = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda event: self._submit(), id=iSubmitId)
        self.SetAcceleratorTable(
            wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, iSubmitId)])
        )

    def _submit(self):
        self.collect()
        self.EndModal(wx.ID_OK)

    def _onButton(self, event):
        button = event.GetEventObject()
        self.collect()
        self.dResults["button"] = stripMnemonic(button.GetLabel())
        if self.functionHandler:
            try:
                if self.functionHandler(self, button) is False:
                    return
            except Exception:
                pass
        iId = button.GetId()
        if iId in (wx.ID_OK, wx.ID_CANCEL):
            self.EndModal(iId)
        else:
            self.EndModal(wx.ID_OK)

    def collect(self):
        """Copy every control's value into the results dictionary."""
        for sName, control in self.dControls.items():
            try:
                if isinstance(control, wx.ListBox):
                    self.dResults[sName] = control.GetStringSelection()
                elif isinstance(control, wx.Choice):
                    self.dResults[sName] = control.GetStringSelection()
                elif isinstance(control, (wx.CheckBox,)):
                    self.dResults[sName] = control.GetValue()
                elif isinstance(control, wx.TextCtrl):
                    self.dResults[sName] = control.GetValue()
            except Exception:
                continue
        return self.dResults

    def complete(self, lButtons=None, iDefault=0, functionHandler=None):
        """Finish layout, show the dialog, and return the result."""
        if lButtons is not False:
            self.addButtonBand(lButtons or ["OK", "Cancel"], iDefault, functionHandler)
        self.lSizers[0].Add(self.lSizers[self.iBand], 0, wx.GROW)
        self.lSizers[0].Add(wx.Size(1, verticalDividerPad))
        self.SetSizerAndFit(self.lSizers[0])
        self.CenterOnScreen()
        for control in self.dControls.values():
            if isinstance(control, (wx.TextCtrl, wx.ListBox, wx.Choice)):
                control.SetFocus()
                break
        bNotified = beforeDialog()
        try:
            iResult = self.ShowModal()
        finally:
            afterDialog(bNotified)
        self.dResults["result"] = iResult
        dResults = dict(self.dResults)
        self.Destroy()
        return dResults


# --- One call conveniences ------------------------------------------------


def dialogInput(sTitle="Input", sLabel="", sValue="", functionDone=None):
    """Ask for one line of text.

    Pass functionDone from inside a screen reader script: the dialog is then
    shown after the script returns and the answer arrives at the callback.
    Without it the call is synchronous, which is safe only outside a script.
    """

    def build():
        dialog = Dialog(sTitle=sTitle)
        dialog.addInputBox(sLabel or "Value:", sValue, sName="value")
        dResults = dialog.complete()
        return dResults.get("value") if dResults.get("result") == wx.ID_OK else None

    if functionDone:
        showLater(lambda: functionDone(build()))
        return None
    return build()


def dialogChoose(sTitle="Choose", sMessage="", lNames=None, iSelection=0, functionDone=None):
    """Offer a list, synchronously or through a callback. See dialogInput."""

    def build():
        dialog = Dialog(sTitle=sTitle)
        if sMessage:
            dialog.addStaticText(sMessage)
            dialog.addBand()
        dialog.addListBox("Choices:", lNames or [], iSelection, sName="choice")
        dResults = dialog.complete()
        return dResults.get("choice") if dResults.get("result") == wx.ID_OK else None

    if functionDone:
        showLater(lambda: functionDone(build()))
        return None
    return build()


def dialogConfirm(sTitle="Confirm", sMessage="", bDefaultYes=True):
    """Ask a yes or no question. Returns True, False, or None if cancelled."""
    dialog = Dialog(sTitle=sTitle, bResizable=False)
    dialog.addStaticText(sMessage)
    dResults = dialog.complete(["&Yes", "&No", "Cancel"], 0 if bDefaultYes else 1)
    if dResults.get("result") != wx.ID_OK:
        return None
    sButton = (dResults.get("button") or "").strip().lower()
    return True if sButton == "yes" else (False if sButton == "no" else None)


def dialogInfo(sTitle="Information", sMessage=""):
    """Show short information in a standard Windows message box.

    This is not the same as dialogShow and the difference is the point.
    Windows message boxes support Control+C, which copies the whole of the box
    including its title, and every user of Windows already knows that. A custom
    dialog with a read only edit box does not: it needs Control+A first, and it
    is one more window whose shape has to be learned.

    So short facts go here, and anything long enough to want searching or
    keeping goes to a page in the browser instead. A version number does not
    deserve a tab; a scan report does not deserve a message box.
    """
    bNotified = beforeDialog()
    try:
        wx.MessageBox(
            str(sMessage), str(sTitle), style=wx.OK | wx.ICON_INFORMATION,
            parent=getHostParent(),
        )
    finally:
        afterDialog(bNotified)
    return True


def dialogShow(sTitle="Message", sMessage=""):
    """Show text that can be read and copied, rather than only heard."""
    dialog = Dialog(sTitle=sTitle)
    dialog.addMemo("Message:", sMessage, bReadOnly=True, sName="message")
    dialog.complete(["OK"], 0)


def dialogOpenFile(sTitle="Open", sValue="", sWildcard="All files (*.*)|*.*", functionDone=None):
    iStyle = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    if functionDone:
        showLater(lambda: functionDone(_fileDialog(sTitle, sValue, sWildcard, iStyle)))
        return None
    return _fileDialog(sTitle, sValue, sWildcard, iStyle)


def dialogSaveFile(sTitle="Save", sValue="", sWildcard="All files (*.*)|*.*", functionDone=None):
    iStyle = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    if functionDone:
        showLater(lambda: functionDone(_fileDialog(sTitle, sValue, sWildcard, iStyle)))
        return None
    return _fileDialog(sTitle, sValue, sWildcard, iStyle)


def _fileDialog(sTitle, sValue, sWildcard, iStyle):
    bNotified = beforeDialog()
    try:
        dialog = wx.FileDialog(
            getHostParent(),
            message=sTitle,
            defaultDir=os.path.dirname(sValue) if sValue else "",
            defaultFile=os.path.basename(sValue) if sValue else "",
            wildcard=sWildcard,
            style=iStyle,
        )
        iResult = dialog.ShowModal()
        sPath = dialog.GetPath()
        dialog.Destroy()
    finally:
        afterDialog(bNotified)
    return sPath if iResult == wx.ID_OK else None
