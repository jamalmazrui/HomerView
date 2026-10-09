r"""say.py -- part of the shared Homer toolkit.

ONE WAY TO ANNOUNCE TEXT, WHATEVER HAPPENS TO BE LISTENING.

THIS MODULE AND CSharp\Say.cs ARE THE SAME CLASS IN TWO LANGUAGES, as far as
Python can reach. Same order of channels, same rule of one utterance per part:

    1. Inside NVDA (an add-on): NVDA speaks directly, through ui.message.
    2. JAWS: the FreedomSci.JawsApi COM object's SayString, with flush off so
       it queues rather than interrupting. Detected first by JAWS's own window
       class, JFWUI2, so no COM object is made when JAWS is not running. The
       object is reached through pywin32 when it is installed, otherwise
       through pythonnet, which a WinForms Python program already has.
    3. NVDA from outside: nvdaControllerClient.dll through ctypes. The DLL is
       looked for beside the program, in the installed tree's exec folder and
       in a PyInstaller bundle. NVDA 2026.1 names it without a suffix; the
       older nvdaControllerClient64.dll is looked for too.
    4. Otherwise the text goes to the console, where a developer sees it.

WHAT IS NOT PORTED, said plainly: the UI Automation notification Say.cs raises
for Narrator. It needs a window of the program's own toolkit, and a Python
program may have wx, WinForms or none. A program that must reach Narrator does
so from its toolkit. Nothing here guesses.

ONE UTTERANCE PER PART (26 September 2026). A reader gives each string it is
handed its own phrase, with its own start and end, and that is what makes three
facts sound like three facts. So say("Column 3", "Row 12", "Paid") sends three
strings, one after another, with nothing inserted between them -- no pause, no
comma. A single string is still one utterance. Joining the parts with commas is
the thing not to do: a comma is a pause the synthesizer decides on, and it is
not always heard.

WHAT TO SAY. Only what the screen reader cannot know: never a dialog's title
or the name of the control with focus, which the reader says already. Report
what was actually done this session.

Nothing here raises. Saying something to nobody is not an error.
"""

import ctypes
import os
import sys

c_lsNvdaDllNames = ["nvdaControllerClient.dll", "nvdaControllerClient64.dll"]
c_sJawsProgId = "FreedomSci.JawsApi"
c_sJawsWindowClass = "JFWUI2"

bExtraSpeechEnabled = True
sLastPath = ""

_dllNvda = None
_bNvdaProbed = False
_oJaws = None


# --- the entry points -----------------------------------------------------------

def say(*vParts, bInterrupt=False):
    """Announce each part as its own utterance. Returns True when any was spoken.

    say("Saved") speaks one string. say("Column 3", "Row 12", "Paid") speaks
    three. A list or tuple passed as the only argument is taken as the parts.
    A final True interrupts what the reader is saying before the first part.
    """
    # A trailing True or False is the interrupt flag, as in say.say("Saved", True):
    # every caller written before parts existed passes it that way.
    if vParts and isinstance(vParts[-1], bool):
        bInterrupt = bInterrupt or vParts[-1]
        vParts = vParts[:-1]
    lParts = _parts(vParts)
    if not bExtraSpeechEnabled or not lParts: return False
    bAny = False
    for sPart in lParts:
        if sayForced(sPart, bInterrupt=bInterrupt and not bAny): bAny = True
    return bAny


def sayParts(lParts):
    """The same as say(*lParts), for a caller holding a list."""
    return say(*list(lParts or []))


def sayForced(sText, bInterrupt=False):
    """One utterance, past the extra-speech switch. True when a reader took it."""
    global sLastPath
    sText = str(sText or "")
    if not sText: return False
    if _sayNvdaInside(sText):
        sLastPath = "NVDA, from inside"
        return True
    if isJawsRunning() and _sayJaws(sText, bInterrupt):
        sLastPath = "JAWS COM"
        return True
    if isNvdaRunning() and _sayNvda(sText, bInterrupt):
        sLastPath = "NVDA controller client"
        return True
    sLastPath = "console"
    try: print(sText, file=sys.stderr)
    except Exception: pass
    return False


def spell(sText):
    """Announce text one character at a time."""
    if not sText: return False
    try:
        import speech
        speech.speakSpelling(str(sText))
        return True
    except Exception:
        return say(*list(str(sText)))


def browseable(sBody, sTitle="", bHtml=True):
    """Show text in a window that can be read like a document (inside NVDA)."""
    try:
        import ui
        try:
            ui.browseableMessage(sBody, sTitle, bHtml)
        except TypeError:
            ui.browseableMessage(sBody, title=sTitle, isHtml=bHtml)
        return True
    except Exception:
        return say(sBody)


def lastSpeechPath():
    """Which channel spoke last, for a diagnostic line in a log."""
    return sLastPath


# --- the channels -----------------------------------------------------------------

def _parts(vParts):
    if len(vParts) == 1 and isinstance(vParts[0], (list, tuple)): vParts = vParts[0]
    return [str(v) for v in vParts if v is not None and str(v) != ""]


def _sayNvdaInside(sText):
    """Inside NVDA itself, as an add-on. Never imports NVDA at module level."""
    if "nvda" not in os.path.basename(sys.executable or "").lower() and "ui" not in sys.modules: return False
    try:
        import ui
        ui.message(sText)
        return True
    except Exception:
        return False


def isJawsRunning():
    try:
        return bool(ctypes.windll.user32.FindWindowW(c_sJawsWindowClass, None))
    except Exception:
        return False


def _jawsObject():
    global _oJaws
    if _oJaws is not None: return _oJaws
    try:
        import win32com.client
        _oJaws = win32com.client.Dispatch(c_sJawsProgId)
        return _oJaws
    except Exception:
        pass
    try:
        import clr  # pythonnet
        from System import Activator, Type
        typeJaws = Type.GetTypeFromProgID(c_sJawsProgId)
        if typeJaws is None: return None
        _oJaws = (typeJaws, Activator.CreateInstance(typeJaws))
        return _oJaws
    except Exception:
        return None


def _sayJaws(sText, bInterrupt):
    global _oJaws
    oJaws = _jawsObject()
    if oJaws is None: return False
    try:
        if isinstance(oJaws, tuple):
            from System.Reflection import BindingFlags
            typeJaws, oInstance = oJaws
            typeJaws.InvokeMember("SayString", BindingFlags.InvokeMethod, None, oInstance, [sText, bool(bInterrupt)])
        else:
            oJaws.SayString(sText, bool(bInterrupt))
        return True
    except Exception:
        _oJaws = None
        return False


def _nvdaDllFolders():
    lsFolders = []
    try:
        sHere = os.path.dirname(os.path.abspath(sys.argv[0]))
        lsFolders.append(sHere)
        lsFolders.append(os.path.join(sHere, "exec"))
        if os.path.basename(sHere).lower() == "exec": lsFolders.append(os.path.dirname(sHere))
    except Exception:
        pass
    sBundle = getattr(sys, "_MEIPASS", "")
    if sBundle: lsFolders.append(sBundle)
    try: lsFolders.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception: pass
    return lsFolders


def isNvdaRunning():
    global _bNvdaProbed, _dllNvda
    if not _bNvdaProbed:
        _bNvdaProbed = True
        for sFolder in _nvdaDllFolders():
            for sName in c_lsNvdaDllNames:
                sPath = os.path.join(sFolder, sName)
                if not os.path.isfile(sPath): continue
                try:
                    _dllNvda = ctypes.WinDLL(sPath)
                    break
                except Exception:
                    _dllNvda = None
            if _dllNvda is not None: break
    if _dllNvda is None: return False
    try:
        return _dllNvda.nvdaController_testIfRunning() == 0
    except Exception:
        return False


def _sayNvda(sText, bInterrupt):
    if _dllNvda is None: return False
    try:
        if bInterrupt: _dllNvda.nvdaController_cancelSpeech()
        return _dllNvda.nvdaController_speakText(ctypes.c_wchar_p(sText)) == 0
    except Exception:
        return False
