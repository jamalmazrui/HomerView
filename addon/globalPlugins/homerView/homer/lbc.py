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


class ListSearch:
    """Find in a list box, as the C# Lbc does.

    A list of forty commands is faster to search than to walk, and a list box
    offers only first-letter jumping, which finds the wrong thing when several
    entries share a letter. Control+J asks for a substring and moves to the
    first match; F3 and Shift+F3 repeat it without asking again.

    The term is held on the class rather than the instance, so a search
    survives closing one dialog and opening another. Someone who has just
    searched for the same thing twice should not have to type it a third time.
    """

    sTerm = ""

    @staticmethod
    def items(listBox):
        try:
            return [listBox.GetString(i) for i in range(listBox.GetCount())]
        except Exception:
            return []

    @staticmethod
    def findFrom(listBox, iFrom, bForward, sNeedle):
        """Return the index of the next match, wrapping, or minus one."""
        lItems = ListSearch.items(listBox)
        if not lItems or not sNeedle:
            return -1
        sNeedle = sNeedle.lower()
        iCount = len(lItems)
        iStep = 1 if bForward else -1
        for iOffset in range(1, iCount + 1):
            iIndex = (iFrom + iStep * iOffset) % iCount
            if sNeedle in lItems[iIndex].lower():
                return iIndex
        return -1

    @staticmethod
    def moveTo(listBox, iIndex):
        listBox.SetSelection(iIndex)
        try:
            listBox.EnsureVisible(iIndex)
        except Exception:
            pass
        # A selection changed in code does not raise the event a screen reader
        # listens for, so the item is announced here.
        from . import say as sayModule

        sayModule.say(listBox.GetString(iIndex))

    @staticmethod
    def prompt(listBox, bForward=True):
        from . import say as sayModule

        sTerm = dialogInput(
            "Find backwards" if not bForward else "Find",
            "Find substring, not case sensitive:",
            ListSearch.sTerm,
        )
        if sTerm is None or not sTerm.strip():
            return
        ListSearch.sTerm = sTerm.strip()
        iFrom = listBox.GetSelection()
        iFound = ListSearch.findFrom(
            listBox, iFrom if iFrom >= 0 else -1, bForward, ListSearch.sTerm)
        if iFound < 0:
            sayModule.say("Not found")
            return
        ListSearch.moveTo(listBox, iFound)

    @staticmethod
    def again(listBox, bForward=True):
        from . import say as sayModule

        if not ListSearch.sTerm:
            sayModule.say("Press Control+J first to search")
            return
        iFrom = listBox.GetSelection()
        iFound = ListSearch.findFrom(
            listBox, iFrom if iFrom >= 0 else -1, bForward, ListSearch.sTerm)
        if iFound < 0:
            sayModule.say("Not found")
            return
        ListSearch.moveTo(listBox, iFound)

    @staticmethod
    def copyItem(listBox, bAppend):
        """Control+C copies the current item, Alt+C appends it.

        Every Lbc control answers the same chords, so a user does not have to
        remember which kind of control they are in.
        """
        from . import say as sayModule

        iIndex = listBox.GetSelection()
        if iIndex < 0:
            sayModule.say("No item")
            return
        sItem = listBox.GetString(iIndex)
        if bAppend:
            setClipboard(clipboardJoin(sItem))
            sayModule.say("Appended to clipboard")
        else:
            setClipboard(sItem)
            sayModule.say("Copied item")

    @staticmethod
    def bind(listBox):
        """Attach the find and copy chords to one list box."""
        def onKey(event):
            iKey = event.GetKeyCode()
            bControl, bShift = event.ControlDown(), event.ShiftDown()
            if bControl and iKey == ord("J"):
                ListSearch.prompt(listBox, not bShift)
            elif iKey == wx.WXK_F3:
                ListSearch.again(listBox, not bShift)
            elif bControl and iKey == ord("C"):
                ListSearch.copyItem(listBox, False)
            elif event.AltDown() and iKey == ord("C"):
                ListSearch.copyItem(listBox, True)
            else:
                event.Skip()
        listBox.Bind(wx.EVT_KEY_DOWN, onKey)
        return listBox


def setClipboard(sText):
    """Put text on the clipboard, through wx so no other library is needed."""
    try:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(str(sText)))
            finally:
                wx.TheClipboard.Close()
            return True
    except Exception:
        pass
    return False


def getClipboard():
    try:
        if wx.TheClipboard.Open():
            try:
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    return data.GetText()
            finally:
                wx.TheClipboard.Close()
    except Exception:
        pass
    return ""


def clipboardJoin(sText):
    """Append to what is already on the clipboard, on its own line."""
    sExisting = getClipboard()
    if not sExisting:
        return str(sText)
    sSeparator = "" if sExisting.endswith("\n") else "\r\n"
    return f"{sExisting}{sSeparator}{sText}"


class Dialog(wx.Dialog):
    """A dialog assembled a band at a time, top to bottom.

    A band is one horizontal row. Controls added after addBand share that row;
    calling addBand again starts the next one. That is the whole layout model,
    and it is enough for the forms this kind of program needs.
    """

    def __init__(self, parent=None, sTitle="Dialog", bResizable=True):
        iStyle = wx.DEFAULT_DIALOG_STYLE | (wx.RESIZE_BORDER if bResizable else 0)
        super().__init__(parent=parent or getHostParent(), title=sTitle, style=iStyle)
        self.controlInitialFocus = None
        self.dControls = OrderedDict()
        self.dLookups = {}
        self.dResults = {}
        self.dTips = {}
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

    # --- Control conveniences -------------------------------------------

    def bindTextChords(self, textCtrl, sTip="", lLookup=None):
        """Give a text control the chords every Lbc control answers.

        Control+A selects all and Control+Shift+A clears the selection, because
        a screen reader user cannot see what is selected and needs to be told.
        Control+C copies the current line and Alt+C appends it, matching the
        list box and the browser commands, so one habit serves everywhere.
        Shift+F1 speaks the tip for the control that has focus, which is where
        a hint belongs when there is no room for it on screen. F4 offers a pick
        list when one was supplied.
        """
        self.dTips[textCtrl] = sTip
        if lLookup:
            self.dLookups[textCtrl] = list(lLookup)

        def currentLine():
            sText = textCtrl.GetValue()
            if not textCtrl.IsMultiLine():
                return sText
            iPosition = textCtrl.GetInsertionPoint()
            iStart = sText.rfind("\n", 0, iPosition) + 1
            iEnd = sText.find("\n", iPosition)
            return sText[iStart:iEnd if iEnd >= 0 else len(sText)].rstrip("\r")

        def onKey(event):
            from . import say as sayModule

            iKey = event.GetKeyCode()
            bControl, bShift, bAlt = event.ControlDown(), event.ShiftDown(), event.AltDown()
            if bControl and bShift and iKey == ord("A"):
                textCtrl.SetSelection(textCtrl.GetInsertionPoint(), textCtrl.GetInsertionPoint())
                sayModule.say("Selection cleared")
            elif bControl and iKey == ord("A"):
                textCtrl.SetSelection(-1, -1)
                sayModule.say("Selected all")
            elif bControl and iKey == ord("C") and not textCtrl.GetStringSelection():
                setClipboard(currentLine())
                sayModule.say("Copied line")
            elif bAlt and iKey == ord("C"):
                sText = textCtrl.GetStringSelection() or currentLine()
                setClipboard(clipboardJoin(sText))
                sayModule.say("Appended to clipboard")
            elif bShift and iKey == wx.WXK_F1:
                sayModule.say(self.dTips.get(textCtrl) or "No tip for this field")
            elif iKey == wx.WXK_F4 and self.dLookups.get(textCtrl):
                sChoice = dialogChoose(
                    "Choose a value", "", sorted(self.dLookups[textCtrl], key=str.lower))
                if sChoice:
                    textCtrl.SetValue(sChoice)
            else:
                event.Skip()

        textCtrl.Bind(wx.EVT_KEY_DOWN, onKey)
        return textCtrl

    def findControl(self, sName):
        """Return a control by the name it was registered under."""
        return self.dControls.get(sName)

    def getValue(self, sName, vDefault=""):
        """Read one control's value without knowing what kind it is."""
        control = self.findControl(sName)
        if control is None:
            return vDefault
        for functionRead in (
            lambda: control.GetStringSelection(),
            lambda: control.GetValue(),
        ):
            try:
                return functionRead()
            except Exception:
                continue
        return vDefault

    def setValue(self, sName, vValue):
        control = self.findControl(sName)
        if control is None:
            return False
        try:
            if isinstance(control, (wx.ListBox, wx.Choice)):
                control.SetStringSelection(str(vValue))
            else:
                control.SetValue(vValue)
            return True
        except Exception:
            return False

    def setInitialFocus(self, sName):
        control = self.findControl(sName)
        if control is not None:
            self.controlInitialFocus = control
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

    def addInputBox(self, sLabel="", sValue="", sName="", iWidth=defaultInputWidth,
                    sTip="", lLookup=None):
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
        self.bindTextChords(textCtrl, sTip, lLookup)
        return self._remember(sName or stripMnemonic(sLabel), self._place(textCtrl, 1))

    def addMemo(self, sLabel="", sValue="", bReadOnly=False, sName="",
                iWidth=defaultEditWidth, iHeight=defaultEditHeight, sTip=""):
        if sLabel:
            self.addStaticText(sLabel)
            self.addBand()
        iStyle = wx.TE_MULTILINE | (wx.TE_READONLY if bReadOnly else 0)
        textCtrl = wx.TextCtrl(self, value=str(sValue), size=(iWidth, iHeight), style=iStyle)
        if sLabel:
            textCtrl.SetName(stripMnemonic(sLabel))
        self.bindTextChords(textCtrl, sTip)
        return self._remember(sName or stripMnemonic(sLabel), self._place(textCtrl, 1))

    def addListBox(self, sLabel="", lNames=None, iSelection=0, sName="",
                   iWidth=defaultListWidth, iHeight=defaultListHeight, sTip=""):
        if sLabel:
            self.addStaticText(sLabel)
            self.addBand()
        listBox = wx.ListBox(self, choices=list(lNames or []), size=(iWidth, iHeight))
        if lNames:
            listBox.SetSelection(max(0, min(iSelection, len(lNames) - 1)))
        if sLabel:
            listBox.SetName(stripMnemonic(sLabel))
        # Control+J and F3 to search, Control+C and Alt+C to copy.
        ListSearch.bind(listBox)
        self.dTips[listBox] = sTip
        return self._remember(sName or stripMnemonic(sLabel), self._place(listBox, 1))

    def addCheckListBox(self, sLabel="", lNames=None, lChecked=None, sName="",
                        iWidth=defaultListWidth, iHeight=defaultListHeight, sTip=""):
        """A list where several items can be chosen, each toggled with Space.

        This is the accessible way to offer multiple selection. A plain list
        box with extended selection reports its state poorly to a screen
        reader, because there is nothing on an item that says whether it is
        selected; a check box on each item says so directly.
        """
        if sLabel:
            self.addStaticText(sLabel)
            self.addBand()
        checkList = wx.CheckListBox(self, choices=list(lNames or []), size=(iWidth, iHeight))
        for iIndex in (lChecked or []):
            if 0 <= iIndex < checkList.GetCount():
                checkList.Check(iIndex, True)
        if lNames:
            checkList.SetSelection(0)
        if sLabel:
            checkList.SetName(stripMnemonic(sLabel))
        ListSearch.bind(checkList)
        self.dTips[checkList] = sTip
        return self._remember(sName or stripMnemonic(sLabel), self._place(checkList, 1))

    def addHistoryBox(self, sLabel="", lRecent=None, sValue="", sName="", sTip=""):
        """A field that remembers what was typed before.

        The same idea as the C# combo history box: the previous entries are
        there to be arrowed through, and anything else can still be typed.
        """
        if sLabel:
            self._place(wx.StaticText(self, label=sLabel))
        comboBox = wx.ComboBox(
            self, value=str(sValue), choices=list(lRecent or []), style=wx.CB_DROPDOWN)
        if sLabel:
            comboBox.SetName(stripMnemonic(sLabel))
        self.dTips[comboBox] = sTip
        return self._remember(sName or stripMnemonic(sLabel), self._place(comboBox, 1))

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

    def _bindHelpKey(self):
        """Shift+F1 speaks the tip for whatever has focus.

        A tip belongs where there is no room for it on screen, which for a
        screen reader user is everywhere. Reaching it from any control rather
        than only a text field means the habit is worth forming.
        """
        iTipId = wx.NewIdRef()

        def onTip(event):
            from . import say as sayModule

            control = self.FindFocus()
            sayModule.say(self.dTips.get(control) or "No tip for this control")

        self.Bind(wx.EVT_MENU, onTip, id=iTipId)
        return wx.AcceleratorEntry(wx.ACCEL_SHIFT, wx.WXK_F1, iTipId)

    def _bindSubmitKeys(self):
        """Control+Enter submits from anywhere in the dialog.

        Plain Enter is consumed by controls that handle it themselves, so a
        user inside a multi-line field or a list has no reliable way to accept
        the dialog. An accelerator reaches the dialog whatever has focus.
        """
        iSubmitId = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda event: self._submit(), id=iSubmitId)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, iSubmitId),
            self._bindHelpKey(),
        ]))

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
                if isinstance(control, wx.CheckListBox):
                    self.dResults[sName] = [
                        control.GetString(i) for i in range(control.GetCount())
                        if control.IsChecked(i)
                    ]
                elif isinstance(control, wx.ListBox):
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
        if self.controlInitialFocus is not None:
            self.controlInitialFocus.SetFocus()
        else:
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


def dialogText(sTitle="Text", sLabel="", sValue="", iWidth=560, iHeight=260):
    """Ask for several lines of text. Returns the text, or None if cancelled."""
    dialog = Dialog(sTitle=sTitle)
    dialog.addMemo(sLabel or "Text:", sValue, sName="text", iWidth=iWidth, iHeight=iHeight)
    dResults = dialog.complete()
    return dResults.get("text") if dResults.get("result") == wx.ID_OK else None


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
