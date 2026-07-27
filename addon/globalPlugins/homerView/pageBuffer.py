"""Browse-mode commands that exist only inside HomerView Edge documents.

The two commands live on the tree interceptor rather than on the global plugin,
and that placement is deliberate. A single letter bound globally would intercept
that letter in every edit box in Windows, and a single defect in the guard would
leave the user unable to type it at all. Tree interceptors already distinguish
browse mode from focus mode, so the letter Q is safe there and nowhere else.

Two routes are provided for attaching the commands, because the preferred one
depends on an NVDA implementation detail that has not yet been observed working.

The preferred route composes a class in front of NVDA's own browse mode class.
Commands attached that way appear in the Input Gestures dialog and the user can
reassign them. It relies on NVDA turning the overlay's _get_treeInterceptorClass
into a real property, which is why HomerViewDocument now derives from
AutoPropertyObject rather than being a plain class.

The fallback route binds the same two functions onto the tree interceptor
instance. It always works, but the commands do not appear in Input Gestures.
The log records which route was taken, so the fallback can be removed once the
preferred one is confirmed.

Logging here is unusually detailed on purpose. Two questions remain open, namely
which NVDA property carries the document address and which attribute identifies
the main landmark. Every candidate is logged with its raw value, so one real
session answers both.
"""

import re
import threading
import time

import addonHandler
import api
import speech
import textInfos
import ui
from baseObject import AutoPropertyObject
from scriptHandler import getLastScriptRepeatCount, script, willSayAllResume

from . import alternateMenu
from . import clipboardTools
from . import find
from . import homerCommands
from . import homerText
from . import speechControl
from . import lbc as lbcModule
from .history import history
from .logger import abbreviate, homerLog, logError, logSection
from .service import service

addonHandler.initTranslation()

dComposedClasses = {}
lAddressProperties = ("documentConstantIdentifier", "documentURL")
mainLandmarkName = "main"
maximumLoggedLandmarks = 40

# Gestures for the two browse mode commands, gathered here so they are easy to
# change in one place.
#
# The letter Q was the obvious choice, because JAWS uses it for the main region.
# In NVDA, Q is already block quote navigation, and taking it would cost a
# command the user has rather than adding one. NVDA's browse mode also spends
# most of the alphabet: D is landmark, P is paragraph, H heading, K link, F form
# field, B button, T table, L list, I list item, G graphic, E edit field, X
# check box, R radio button, C combo box, S separator, M frame, N block of
# links, O embedded object, A annotation, U and V link states, W spelling error.
#
# J is unassigned and carries a usable mnemonic, jump to main. A modifier based
# alternative is bound as well, so the command still works if J turns out to be
# taken by another add-on or a future NVDA release. The alternative uses the
# same letter, because NVDA+Alt+M is its own command for interacting with
# mathematical content.
# The Homer interface keys, as settled by FxMax and IEMax for virtual mode.
# They live on the browse mode class, so they exist only inside HomerView pages
# and cannot shadow anything in Edge, in other browsers, or in Windows.
dHomerGestures = {
    "kb:alt+f8": "readAll",
    # Scroll Lock, because nothing else wants it: not Edge, not NVDA, not
    # Windows since about 1981. One large isolated key that both starts and
    # stops continuous reading.
    "kb:scrolllock": "toggleSayAll",
    # The Homer grave accent family, as EdSharp arranges it. Punctuation moves
    # to Control+Alt+Grave because HomerView does not use NVDA's modifier for
    # page commands; the other four are unchanged. None of the five is used by
    # Edge, by NVDA, or by Windows.
    "kb:control+alt+`": "togglePunctuation",
    "kb:control+`": "speakFaster",
    "kb:control+shift+`": "speakSlower",
    "kb:alt+`": "speakLouder",
    "kb:alt+shift+`": "speakSofter",
    "kb:shift+`": "reportSpeechSettings",
    "kb:control+f8": "copyAll",
    "kb:control+c": "copyLineOrSelection",
    "kb:alt+c": "copyAppend",
    "kb:alt+m": "pageInformation",
    # Q for query. NVDA uses plain Q for block quotes, and Alt+Q is free in
    # Edge, in NVDA and in Windows.
    "kb:alt+q": "webUtilities",
    # Homer puts a window list on F4. Microsoft Edge uses F4 to select the
    # address bar, but Control+L and Alt+D both do that too, so this takes the
    # least used of three ways to do one thing and loses nothing.
    "kb:f4": "chooseTab",
    "kb:shift+f4": "sayTabs",
    # Control+F4 is deliberately absent. Microsoft Edge already closes the
    # current tab with it, which is exactly what it should do, so the family
    # has a gap on purpose rather than by oversight.
    "kb:control+shift+f4": "closeOtherTabs",
    "kb:alt+downarrow": "nextSentence",
    "kb:alt+uparrow": "priorSentence",
    "kb:control+downarrow": "nextParagraph",
    "kb:control+uparrow": "priorParagraph",
    "kb:alt+k": "runAccessibilityCheck",
    "kb:alt+v": "actOnPage",
    "kb:shift+j": "proxyMainContent",
    "kb:y": "explorePage",
    # The two things JAWS reaches and NVDA does not. Z is the last letter NVDA
    # leaves unassigned, and both commands belong to one key family so there is
    # one thing to remember rather than two.
    "kb:z": "nextSameType",
    "kb:shift+z": "priorSameType",
    "kb:alt+z": "nextDifferentType",
    "kb:alt+shift+z": "priorDifferentType",
    "kb:alt+i": "runIbmChecker",
    "kb:control+f": "findText",
    "kb:control+shift+f": "findTextBackwards",
    "kb:control+f3": "findByPattern",
    "kb:control+o": "openOtherFormat",
    "kb:alt+w": "findWordAtCursor",
    "kb:alt+shift+w": "findWordAtCursorBackwards",
    "kb:f1": "showHelp",
    "kb:alt+f1": "showAbout",
    "kb:control+f11": "elevateVersion",
    "kb:shift+f1": "showHistory",
    "kb:control+shift+f3": "findByPatternBackwards",
    "kb:f3": "findAgain",
    "kb:shift+f3": "findAgainBackwards",
    "kb:NVDA+f5": "listFormFields",
    "kb:NVDA+f6": "listHeadings",
    "kb:NVDA+shift+f7": "listLinks",
    "kb:NVDA+alt+l": "listAnyElements",
    "kb:alt+y": "sayYield",
    "kb:alt+shift+y": "sayYieldStructure",
    # JAWS reports progress through a page on Alt+Delete. NVDA's own equivalent
    # is NVDA+Delete, which reports the position of the review cursor including
    # the percentage through the document. Both spellings of Delete are bound,
    # because the keypad's Delete is a different key identifier and a user who
    # reaches for one will not think to try the other.
    "kb:alt+delete": "sayPosition",
    "kb:alt+numpadDelete": "sayPosition",
    "kb:shift+space": "saySelected",
    "kb:shift+backspace": "sayChunk",
    "kb:alt+r": "sayRest",
    "kb:control+space": "selectChunk",
    "kb:f8": "startSelection",
    "kb:shift+f8": "completeSelection",
    "kb:alt+shift+f8": "goToSelectionStart",
    "kb:alt+u": "urlReference",
    "kb:alt+p": "pageUrls",
    "kb:alt+n": "pageName",
    "kb:alt+;": "sayTime",
    "kb:control+g": "goToPercent",
    "kb:alt+g": "goToPercentAgain",
    "kb:alt+'": "quoteClipboard",
    "kb:alt+shift+'": "clearClipboard",
    "kb:control+'": "saveClipboard",
    "kb:control+shift+'": "appendClipboard",
    # The Alternate Menu is deliberately not bound here. It is on NVDA+Alt+F10
    # alone, which works everywhere, because a command whose whole purpose is
    # to find other commands must never be one of the things that sometimes
    # does nothing. See the note in __init__.py.
    "kb:alt+shift+h": "hotkeySummary",
}

# How a key is written when a person is going to read it.
#
# Two conventions, both deliberate.
#
# Modifiers are listed alphabetically: Alt, Control, NVDA, Shift, Windows. That
# is arbitrary in itself, and that is the point. Any fixed order would do; what
# matters is that the same combination always reads the same way, so two lists
# of keys can be compared without normalising them first, and a reader hears
# Alt+Control+Shift in that order every time rather than in whatever order the
# author happened to type.
#
# Key names follow Freedom Scientific's, as JAWS writes them, even though these
# keys are being bound in NVDA. A blind Windows user has read JAWS key names for
# thirty years, and DownArrow, Accent and SemiColon are what they expect to
# hear. NVDA's own gesture identifiers stay as NVDA writes them, because those
# are what the binding needs; only what is shown to a person changes.
#
# Developer.md carries the full translation between the two.
dModifierNames = {
    "alt": "Alt", "control": "Control", "nvda": "NVDA", "shift": "Shift",
    "windows": "Windows",
}

dKeyNames = {
    "`": "Accent", "'": "Apostrophe", "\\": "BackSlash", ",": "Comma",
    "-": "Dash", "=": "Equals", "[": "LeftBracket", ".": "Period",
    "]": "RightBracket", "/": "Slash", ";": "SemiColon",
    "backspace": "Backspace", "capslock": "CapsLock", "delete": "Delete",
    "downarrow": "DownArrow", "end": "End", "enter": "Enter",
    "escape": "Escape", "home": "Home", "insert": "Insert",
    "leftarrow": "LeftArrow", "numlock": "NumLock",
    "numpaddelete": "NumPadDelete", "numpadenter": "NumPadEnter",
    "pagedown": "PageDown", "pageup": "PageUp", "printscreen": "PrintScreen",
    "rightarrow": "RightArrow", "scrolllock": "ScrollLock", "space": "Space",
    "tab": "Tab", "uparrow": "UpArrow",
}


def readableName(sName):
    """Turn a script name into words a person would read in a menu.

    The menu shows commands, not identifiers, so listFormFields has to become
    List form fields before anyone sees it. Two names are spelled out rather
    than derived, because splitting them on capitals gives the wrong words.
    """
    dSpecial = {
        "moveToMainContent": "Jump to Main Content",
        "proxyMainContent": "Jump to Probable Main Content",
    }
    if sName in dSpecial:
        return dSpecial[sName]
    sSpaced = re.sub(r"(?<!^)(?=[A-Z])", " ", str(sName or ""))
    return sSpaced[:1].upper() + sSpaced[1:].lower() if sSpaced else ""


def describeGesture(sGesture):
    """Write a gesture the way a JAWS user reads keys.

    Modifiers alphabetically, then the key, with Freedom Scientific's spelling.
    """
    lParts = sGesture[3:].split("+")
    lModifiers = sorted(
        dModifierNames[s.lower()] for s in lParts[:-1] if s.lower() in dModifierNames)
    sKey = lParts[-1]
    sKey = dKeyNames.get(sKey, dKeyNames.get(sKey.lower()))
    if sKey is None:
        sKey = lParts[-1]
        if len(sKey) == 1:
            sKey = sKey.upper()
        elif sKey.lower().startswith("f") and sKey[1:].isdigit():
            sKey = "F" + sKey[1:]
        elif sKey.lower().startswith("numpad"):
            sKey = "NumPad" + sKey[6:].capitalize()
        else:
            sKey = sKey.capitalize()
    return "+".join(lModifiers + [sKey])


dHomerNames = {sName: describeGesture(sGesture) for sGesture, sName in dHomerGestures.items()}

# NVDA's own report commands speak the value and nothing else: NVDA+T says the
# title, not "Title, ...", and NVDA+F12 says the time, not "Time, ...". There is
# no verbosity setting that adds a label, because labelling is not NVDA's
# pattern. JAWS does label, which is why the absence is noticeable to anyone
# coming from it.
#
# HomerView follows NVDA by default. Set this to True to hear a label first.
bSpeakCommandLabels = False

pageScopeName = "In a HomerView page"

sMainContentAlternateGesture = "kb:NVDA+alt+j"
sMainContentGesture = "kb:j"
sPageAddressGesture = "kb:alt+a"


def resolveDocumentAddress(treeInterceptor):
    """Return the document address from NVDA alone, or an empty string.

    A real session showed documentConstantIdentifier and documentURL both
    carrying the address for a Chromium document, while the root object's value
    was empty, so that third candidate has been dropped. The first is tried
    first; the second remains as insurance against an NVDA change. Keeping this
    on the NVDA side avoids a protocol round trip in the common case.
    """
    lCandidates = []
    for sProperty in lAddressProperties:
        try:
            sValue = getattr(treeInterceptor, sProperty, None)
            homerLog.debug(f"Address candidate {sProperty}: {abbreviate(sValue, 300)}")
            lCandidates.append((sProperty, str(sValue or "")))
        except Exception as exception:
            homerLog.debug(f"Address candidate {sProperty} raised: {exception}")
            lCandidates.append((sProperty, ""))
    for sProperty, sCandidate in lCandidates:
        sCandidate = sCandidate.strip()
        if "://" in sCandidate or sCandidate.startswith("about:"):
            homerLog.debug(f"Address resolved from {sProperty}")
            return sCandidate
    homerLog.warning("No NVDA property yielded a usable address; the fallback will be used")
    return ""


def describeLandmarkItem(item):
    """Return a dictionary of every attribute that might identify a landmark."""
    dDescription = {}
    try:
        obj = item.obj
    except Exception as exception:
        obj = None
        dDescription["objError"] = str(exception)
    for sName, vValue in (
        ("label", getattr(item, "label", None)),
        ("landmark", getattr(obj, "landmark", None)),
        ("roleText", getattr(obj, "roleText", None)),
        ("role", getattr(obj, "role", None)),
        ("name", getattr(obj, "name", None)),
    ):
        try:
            dDescription[sName] = str(vValue) if vValue is not None else None
        except Exception:
            dDescription[sName] = "unreadable"
    return dDescription


def isMainLandmark(item):
    """Decide whether a landmark quick navigation item is the main content.

    A real session showed the object's landmark attribute holding exactly
    "main", so that is the test. The item label is kept as a cheap second
    check, since it also read "main" for the same landmark.
    """
    try:
        obj = item.obj
    except Exception:
        obj = None
    if (getattr(obj, "landmark", "") or "").lower() == mainLandmarkName:
        return True
    return (getattr(item, "label", "") or "").strip().lower() == mainLandmarkName


# The command bodies live at module level so that both attachment routes run
# exactly the same code.

def speakAddress(sAddress, iRepeat):
    """Speak, spell, or copy the address, following NVDA's report conventions.

    NVDA's own report commands, such as report title on NVDA+T, speak once,
    spell on a second press, and copy to the clipboard on a third. Matching that
    means the new command behaves the way the rest of NVDA already taught you.
    """
    if iRepeat == 0:
        # Translators: Spoken label before the web address, when labels are on.
        ui.message(homerCommands.withLabel(_("Address"), sAddress))
        return
    if iRepeat == 1:
        homerLog.debug("Second press: spelling the address")
        speech.speakSpelling(sAddress)
        return
    homerLog.debug("Third press: copying the address to the clipboard")
    try:
        api.copyToClip(sAddress, notify=True)
    except TypeError:
        # Older signatures take no notify argument.
        api.copyToClip(sAddress)
        # Translators: Reported after copying the web address to the clipboard.
        ui.message(_("Copied to clipboard"))
    except Exception:
        logError("Copying the address to the clipboard failed")
        # Translators: Reported when the address could not be copied.
        ui.message(_("The web address could not be copied"))


def reportPageAddress(treeInterceptor):
    logSection("Command: report the page address")
    nStarted = time.monotonic()
    iRepeat = getLastScriptRepeatCount()
    sAddress = resolveDocumentAddress(treeInterceptor)
    if sAddress:
        homerLog.info(
            f"Address from NVDA in {time.monotonic() - nStarted:.3f} seconds, repeat {iRepeat}: "
            f"{abbreviate(sAddress, 300)}"
        )
        if iRepeat == 0:
            sTitle = ""
            try:
                sTitle = (getattr(treeInterceptor.rootNVDAObject, "name", "") or "").strip()
            except Exception:
                sTitle = ""
            history.record("pageViewed", sTitle, sAddress)
        speakAddress(sAddress, iRepeat)
        return
    if not service.isConnected():
        homerLog.warning("Address fallback unavailable because HomerView is not connected")
        # Translators: Reported when the address cannot be determined.
        ui.message(_("The web address is unavailable"))
        return
    homerLog.info("Address falling back to the DevTools Protocol on the worker thread")

    def onSuccess(sUrl):
        homerLog.info(f"Address from the DevTools Protocol: {abbreviate(sUrl, 300)}")
        if sUrl:
            speakAddress(sUrl, iRepeat)
        else:
            ui.message(_("The web address is unavailable"))

    def onError(exception):
        homerLog.error(f"Address fallback failed: {exception}")
        ui.message(_("The web address is unavailable"))

    service.submit("activePageUrl", service.taskActivePageUrl, onSuccess, onError)


def reportQuickNavItem(item, gesture):
    """Report an item and move to it, exactly as NVDA's quick navigation does.

    Two details are copied deliberately. NVDA reports before moving, because
    moving can change the focus and mutate the document, invalidating an
    offset-based position. And a line is read rather than the whole element;
    without that, arriving at a main landmark would read the entire page.
    """
    if not gesture or not willSayAllResume(gesture):
        item.report(readUnit=textInfos.UNIT_LINE)
    else:
        homerLog.debug("Report suppressed so that say all can resume")
    item.moveTo()


def moveToMainContent(treeInterceptor, gesture=None):
    """Move to the main landmark, or leave the cursor exactly where it is.

    NVDA's quick navigation keys do not move on failure, and they announce it
    with a short lowercase message. Both are matched here. Nothing is offered
    as a substitute destination: a navigation command that lands somewhere
    other than where it was asked to go is worse than one that reports nothing
    was found.
    """
    logSection("Command: move to the main content")
    nStarted = time.monotonic()
    iSeen = 0
    try:
        infoStart = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        for item in treeInterceptor._iterNodesByType("landmark", "next", infoStart):
            iSeen += 1
            if iSeen <= maximumLoggedLandmarks:
                homerLog.debug(f"Landmark {iSeen}: {describeLandmarkItem(item)}")
            if isMainLandmark(item):
                homerLog.info(
                    f"Main landmark matched at position {iSeen} after "
                    f"{time.monotonic() - nStarted:.3f} seconds"
                )
                reportQuickNavItem(item, gesture)
                return
    except NotImplementedError:
        homerLog.warning("This document does not implement landmark navigation")
        # Translators: Message when a quick navigation command is not supported
        # in the current document. This wording matches NVDA's own message.
        ui.message(_("Not supported in this document"))
        return
    except Exception:
        logError("Moving to the main landmark raised")
        # Translators: Reported when main content navigation fails.
        ui.message(_("HomerView could not move to the main content"))
        return
    homerLog.info(f"No main landmark among {iSeen} landmarks; the cursor has not moved")
    # Translators: Message when a page has no main landmark. The lowercase
    # wording matches NVDA's own quick navigation messages, such as
    # "no next heading".
    ui.message(_("no main landmark"))


class HomerViewBuffer:
    """Mixin composed in front of the ordinary browse-mode class."""

    __gestures = dict(
        dHomerGestures,
        **{
            sMainContentAlternateGesture: "moveToMainContent",
            sMainContentGesture: "moveToMainContent",
            sPageAddressGesture: "reportPageAddress",
        },
    )

    @script(
        # Translators: Input help mode message for the report page address command.
        description=_(
            "Reports the web address of the current HomerView page. "
            "Pressing twice spells it, and pressing three times copies it to the clipboard"
        ),
        category="HomerView",
        speakOnDemand=True,
    )
    def script_reportPageAddress(self, gesture):
        self.runSafely("reportPageAddress", lambda: reportPageAddress(self))

    @script(
        # Translators: Input help mode message for the move to main content command.
        description=_("Jump to Main Content: moves to the page's main content landmark"),
        category="HomerView",
    )
    def script_moveToMainContent(self, gesture):
        self.runSafely("moveToMainContent", lambda: moveToMainContent(self, gesture))

    def runSafely(self, sName, functionCommand, *lArguments):
        """Run a command so that a fault is reported rather than swallowed.

        NVDA catches an exception raised inside a script and writes it to its
        own log, which means a command can fail in complete silence: nothing is
        spoken, nothing appears in HomerView's log, and the key looks dead. For
        a program that has to be trusted by people who cannot see a stack
        trace, silence is the worst possible failure.
        """
        try:
            return functionCommand(*lArguments)
        except Exception as exception:
            logError(f"The command {sName} failed")
            ui.message(
                # Translators: Reported when a command fails. The placeholders
                # are the command name and the kind of fault.
                _("{name} failed: {reason}. The log has the detail.").format(
                    name=readableName(sName), reason=type(exception).__name__
                )
            )
            return None

    def getScript(self, gesture):
        """Resolve a key to a command, recording every attempt.

        This is the diagnostic that distinguishes the two ways a key can appear
        to do nothing. If a key does not appear here at all, Windows or Edge
        consumed it before NVDA saw it, and no binding on our side can help. If
        it appears with no command, the key reached us and our binding is what
        is wrong. Without this line the two look identical from outside.
        """
        functionScript = super().getScript(gesture)
        try:
            lIdentifiers = list(getattr(gesture, "normalizedIdentifiers", None) or [])
            sName = getattr(functionScript, "__name__", "") if functionScript else ""
            bMine = sName.startswith("script_") and hasattr(HomerViewBuffer, sName)
            # A key that resolves to a HomerView command is worth finding
            # without a debug filter; everything else stays at debug level so
            # the file remains readable.
            sMessage = (
                f"Key in a HomerView page: {lIdentifiers} -> "
                f"{sName or 'no command'}{' (HomerView)' if bMine else ''} "
                f"on {threading.current_thread().name}"
            )
            if bMine:
                homerLog.info(sMessage)
            else:
                homerLog.debug(sMessage)
        except Exception:
            pass
        return functionScript

    # --- The Homer interface -------------------------------------------------
    # Each script is a thin wrapper so that the command bodies stay in
    # homerCommands, where they can be read as a set.

    def _homer(self, sName, sDescription):
        """Return a menu entry for one of this class's commands.

        The scripts are named script_<name>, and an earlier version of this
        method looked for homer_<name>, which does not exist. Every call raised
        AttributeError before the first entry was built, so the Alternate Menu
        appeared to do nothing at all while the key resolved correctly. The
        lookup is now checked rather than assumed.
        """
        functionScript = getattr(self, "script_" + sName, None)
        if not functionScript:
            homerLog.warning(f"No script exists for the page command {sName}")
            return None
        return alternateMenu.CommandEntry(
            readableName(sName), dHomerNames.get(sName, ""), sDescription,
            lambda f=functionScript: f(None), pageScopeName,
        )

    @script(
        description=_("Starts reading continuously, or stops if it is already reading"),
        category="HomerView",
    )
    def script_toggleSayAll(self, gesture):
        self.runSafely("toggleSayAll", lambda: homerCommands.toggleSayAll(self))

    @script(
        description=_("Switches punctuation between all and none"),
        category="HomerView",
    )
    def script_togglePunctuation(self, gesture):
        self.runSafely("togglePunctuation", speechControl.togglePunctuation)

    @script(description=_("Speaks faster"), category="HomerView")
    def script_speakFaster(self, gesture):
        self.runSafely("speakFaster", lambda: speechControl.adjustRate(True))

    @script(description=_("Speaks slower"), category="HomerView")
    def script_speakSlower(self, gesture):
        self.runSafely("speakSlower", lambda: speechControl.adjustRate(False))

    @script(description=_("Speaks louder"), category="HomerView")
    def script_speakLouder(self, gesture):
        self.runSafely("speakLouder", lambda: speechControl.adjustVolume(True))

    @script(description=_("Speaks more softly"), category="HomerView")
    def script_speakSofter(self, gesture):
        self.runSafely("speakSofter", lambda: speechControl.adjustVolume(False))

    @script(
        description=_("Reports the punctuation level, the rate and the volume"),
        category="HomerView",
        speakOnDemand=True,
    )
    def script_reportSpeechSettings(self, gesture):
        from . import output

        self.runSafely(
            "reportSpeechSettings",
            lambda: output.lines(_("Speech settings"), speechControl.reportSpeechSettings()))

    @script(description=_("Reads the whole page without moving the cursor"), category="HomerView")
    def script_readAll(self, gesture):
        self.runSafely("readAll", lambda: homerCommands.readAll(self))

    @script(description=_("Copies the whole page to the clipboard"), category="HomerView")
    def script_copyAll(self, gesture):
        self.runSafely("copyAll", lambda: homerCommands.copyAll(self))

    @script(description=_("Copies the selection, or the current line when nothing is selected"), category="HomerView")
    def script_copyLineOrSelection(self, gesture):
        self.runSafely("copyLineOrSelection", lambda: homerCommands.copyLineOrSelection(self))

    @script(description=_("Appends the selection, or the current line, to the clipboard"), category="HomerView")
    def script_copyAppend(self, gesture):
        self.runSafely("copyAppend", lambda: homerCommands.copyAppend(self))

    @script(
        description=_("Reports what the page says about itself: author, publisher, date, licence"),
        category="HomerView",
        speakOnDemand=True,
    )
    def script_pageInformation(self, gesture):
        self.runSafely("pageInformation", lambda: homerCommands.pageInformation(self))

    @script(description=_("Says how many characters, words and lines the page or selection holds"), category="HomerView", speakOnDemand=True)
    def script_sayYield(self, gesture):
        self.runSafely("sayYield", lambda: homerCommands.sayYield(self))

    @script(description=_("Says how many links, headings, landmarks, tables, frames and fields the page holds"), category="HomerView", speakOnDemand=True)
    def script_sayYieldStructure(self, gesture):
        self.runSafely("sayYieldStructure", lambda: homerCommands.sayYieldStructure(self))

    @script(description=_("Says the line, column and percentage position of the cursor"), category="HomerView", speakOnDemand=True)
    def script_sayPosition(self, gesture):
        self.runSafely("sayPosition", lambda: homerCommands.sayPosition(self))

    @script(description=_("Says the selected text, and spells it when pressed twice"), category="HomerView", speakOnDemand=True)
    def script_saySelected(self, gesture):
        self.runSafely("saySelected", lambda: homerCommands.saySelected(self))

    @script(description=_("Says the run of non-blank characters at the cursor, and spells it when pressed twice"), category="HomerView", speakOnDemand=True)
    def script_sayChunk(self, gesture):
        self.runSafely("sayChunk", lambda: homerCommands.sayChunk(self))

    @script(description=_("Reads the rest of the page from the cursor, without moving it"), category="HomerView")
    def script_sayRest(self, gesture):
        self.runSafely("sayRest", lambda: homerCommands.sayRest(self))

    @script(description=_("Selects the run of non-blank characters at the cursor"), category="HomerView")
    def script_selectChunk(self, gesture):
        self.runSafely("selectChunk", lambda: homerCommands.selectChunk(self))

    @script(description=_("Marks where a selection should begin, so Shift need not be held"), category="HomerView")
    def script_startSelection(self, gesture):
        self.runSafely("startSelection", lambda: homerCommands.startSelection(self))

    @script(description=_("Selects from the marked start to the cursor"), category="HomerView")
    def script_completeSelection(self, gesture):
        self.runSafely("completeSelection", lambda: homerCommands.completeSelection(self))

    @script(description=_("Returns to the marked start of the selection"), category="HomerView")
    def script_goToSelectionStart(self, gesture):
        self.runSafely("goToSelectionStart", lambda: homerCommands.goToSelectionStart(self))

    @script(description=_("Says where the link at the cursor would go, and copies it when pressed twice"), category="HomerView", speakOnDemand=True)
    def script_urlReference(self, gesture):
        self.runSafely("urlReference", lambda: homerCommands.urlReference(self))

    @script(description=_("Copies every link address on the page to the clipboard"), category="HomerView")
    def script_pageUrls(self, gesture):
        self.runSafely("pageUrls", lambda: homerCommands.pageUrls(self))

    @script(description=_("Says the name of the page, and spells it when pressed twice"), category="HomerView", speakOnDemand=True)
    def script_pageName(self, gesture):
        self.runSafely("pageName", lambda: homerCommands.pageName(self))

    @script(description=_("Says the time, and the date when pressed twice"), category="HomerView", speakOnDemand=True)
    def script_sayTime(self, gesture):
        self.runSafely("sayTime", lambda: homerCommands.sayTime())

    @script(description=_("Moves to a percentage point through the page"), category="HomerView")
    def script_goToPercent(self, gesture):
        # Deferred, so NVDA has finished the script before the dialog opens.
        lbcModule.afterScript(self._goToPercentNow)

    def _goToPercentNow(self):
        tValue = askForPercent(homerCommands.lastPercent(self))
        if tValue is None:
            return
        iNumber, bRelative = tValue
        if bRelative:
            iCurrent = homerText.caretPosition(self)[2]
            iNumber = max(0, min(100, iCurrent + iNumber))
            homerLog.info(f"Relative move from {iCurrent} percent to {iNumber} percent")
        homerCommands.goToPercent(self, iNumber)

    @script(description=_("Moves to the percentage point used last time"), category="HomerView")
    def script_goToPercentAgain(self, gesture):
        iPercent = homerCommands.lastPercent(self)
        if iPercent is None:
            # Translators: Reported when no percentage has been used yet.
            ui.message(_("No percentage has been set yet"))
            return
        homerCommands.goToPercent(self, iPercent)

    @script(description=_("Says the clipboard text, and spells it when pressed twice"), category="HomerView", speakOnDemand=True)
    def script_quoteClipboard(self, gesture):
        self.runSafely("quoteClipboard", lambda: clipboardTools.sayClipboard())

    @script(description=_("Clears the clipboard"), category="HomerView")
    def script_clearClipboard(self, gesture):
        self.runSafely("clearClipboard", lambda: clipboardTools.clearClipboard())

    @script(description=_("Saves the clipboard to a text file, proposing a name"), category="HomerView")
    def script_saveClipboard(self, gesture):
        self.runSafely("saveClipboard", lambda: clipboardTools.exportClipboard(False))

    @script(description=_("Appends the clipboard to a text file"), category="HomerView")
    def script_appendClipboard(self, gesture):
        self.runSafely("appendClipboard", lambda: clipboardTools.exportClipboard(True))

    @script(description=_("Shows every HomerView command and its key as a document"), category="HomerView")
    def script_hotkeySummary(self, gesture):
        self.runSafely("hotkeySummary", lambda: alternateMenu.showHotkeySummary(self.buildCommandEntries()))

    @script(
        description=_("Acts on the page by describing what you want, such as click sign in"),
        category="HomerView",
    )
    def script_actOnPage(self, gesture):
        self.runSafely("actOnPage", lambda: homerCommands.actOnPage())

    @script(
        description=_("Tests the page with the IBM Equal Access engine, alongside axe-core"),
        category="HomerView",
    )
    def script_runIbmChecker(self, gesture):
        self.runSafely("runIbmChecker", lambda: homerCommands.runIbmChecker())

    @script(
        description=_("Jump to Probable Main Content: finds it when the page declares none"),
        category="HomerView",
    )
    def script_proxyMainContent(self, gesture):
        self.runSafely("proxyMainContent", lambda: homerCommands.moveToProxyMainContent(self, gesture))

    @script(
        description=_("Moves to the next element of the same kind as this one"),
        category="HomerView",
    )
    def script_nextSameType(self, gesture):
        self.runSafely("nextSameType",
                       lambda: homerCommands.moveByTypeRelation(self, True, True))

    @script(
        description=_("Moves to the previous element of the same kind as this one"),
        category="HomerView",
    )
    def script_priorSameType(self, gesture):
        self.runSafely("priorSameType",
                       lambda: homerCommands.moveByTypeRelation(self, True, False))

    @script(
        description=_("Moves to the next element of a different kind"),
        category="HomerView",
    )
    def script_nextDifferentType(self, gesture):
        self.runSafely("nextDifferentType",
                       lambda: homerCommands.moveByTypeRelation(self, False, True))

    @script(
        description=_("Moves to the previous element of a different kind"),
        category="HomerView",
    )
    def script_priorDifferentType(self, gesture):
        self.runSafely("priorDifferentType",
                       lambda: homerCommands.moveByTypeRelation(self, False, False))

    @script(
        description=_("Looks something up using free web services that need no account"),
        category="HomerView",
    )
    def script_webUtilities(self, gesture):
        self.runSafely("webUtilities", homerCommands.webUtilities)

    @script(
        description=_("Lists the HomerView tabs and switches to the one you choose"),
        category="HomerView",
    )
    def script_chooseTab(self, gesture):
        self.runSafely("chooseTab", homerCommands.chooseTab)

    @script(
        description=_("Says the names of the open HomerView tabs"),
        category="HomerView",
        speakOnDemand=True,
    )
    def script_sayTabs(self, gesture):
        self.runSafely("sayTabs", homerCommands.sayTabs)

    @script(
        description=_("Closes every HomerView tab but this one and the first"),
        category="HomerView",
    )
    def script_closeOtherTabs(self, gesture):
        self.runSafely("closeOtherTabs", homerCommands.closeOtherTabs)

    @script(description=_("Summarises the structure of this page"), category="HomerView")
    def script_explorePage(self, gesture):
        self.runSafely("explorePage", lambda: homerCommands.explorePageFromBuffer())

    @script(description=_("Moves to the next sentence and reads it"), category="HomerView")
    def script_nextSentence(self, gesture):
        self.runSafely("nextSentence", lambda: homerCommands.moveBySentence(self, True))

    @script(description=_("Moves to the previous sentence and reads it"), category="HomerView")
    def script_priorSentence(self, gesture):
        self.runSafely("priorSentence", lambda: homerCommands.moveBySentence(self, False))

    @script(description=_("Moves to the next paragraph and reads it"), category="HomerView")
    def script_nextParagraph(self, gesture):
        self.runSafely("nextParagraph", lambda: homerCommands.moveByParagraph(self, True))

    @script(description=_("Moves to the previous paragraph and reads it"), category="HomerView")
    def script_priorParagraph(self, gesture):
        self.runSafely("priorParagraph", lambda: homerCommands.moveByParagraph(self, False))

    @script(
        description=_("Tests this page for accessibility, asking which engine to use"),
        category="HomerView",
    )
    def script_runAccessibilityCheck(self, gesture):
        self.runSafely("runAccessibilityCheck", homerCommands.runAccessibilityCheck)

    @script(
        description=_("Finds text in the page, not case sensitive"),
        category="HomerView",
    )
    def script_findText(self, gesture):
        self.runSafely("findText", lambda: homerCommands.askAndFind(self, False, False))

    @script(
        description=_("Finds text backwards in the page, not case sensitive"),
        category="HomerView",
    )
    def script_findTextBackwards(self, gesture):
        self.runSafely("findTextBackwards", lambda: homerCommands.askAndFind(self, True, False))

    @script(
        description=_("Finds a regular expression in the page"),
        category="HomerView",
    )
    def script_findByPattern(self, gesture):
        self.runSafely("findByPattern", lambda: homerCommands.askAndFind(self, False, True))

    @script(
        description=_("Finds a regular expression backwards in the page"),
        category="HomerView",
    )
    def script_findByPatternBackwards(self, gesture):
        self.runSafely("findByPatternBackwards", lambda: homerCommands.askAndFind(self, True, True))

    @script(description=_("Finds the next occurrence of the word at the cursor"), category="HomerView")
    def script_findWordAtCursor(self, gesture):
        self.runSafely("findWordAtCursor", lambda: homerCommands.findWordAtCursor(self, False))

    @script(description=_("Finds the previous occurrence of the word at the cursor"), category="HomerView")
    def script_findWordAtCursorBackwards(self, gesture):
        self.runSafely("findWordAtCursorBackwards", lambda: homerCommands.findWordAtCursor(self, True))

    @script(
        description=_("Opens a document of any popular format, or a web address"),
        category="HomerView",
    )
    def script_openOtherFormat(self, gesture):
        self.runSafely("openOtherFormat", lambda: homerCommands.openDocument())

    @script(
        description=_("Checks for a newer HomerView and installs it"),
        category="HomerView",
    )
    def script_elevateVersion(self, gesture):
        self.runSafely("elevateVersion", homerCommands.elevateVersion)

    @script(description=_("Shows the HomerView user guide"), category="HomerView")
    def script_showHelp(self, gesture):
        self.runSafely("showHelp", lambda: homerCommands.showDocument("help"))

    @script(description=_("Shows what HomerView is, and where it keeps its files"), category="HomerView")
    def script_showAbout(self, gesture):
        self.runSafely("showAbout", lambda: homerCommands.showDocument("about"))

    @script(description=_("Shows the history of changes to HomerView"), category="HomerView")
    def script_showHistory(self, gesture):
        self.runSafely("showHistory", lambda: homerCommands.showDocument("history"))

    @script(description=_("Repeats the last find, forwards"), category="HomerView")
    def script_findAgain(self, gesture):
        self.runSafely("findAgain", lambda: find.repeatFind(self, False))

    @script(description=_("Repeats the last find, backwards"), category="HomerView")
    def script_findAgainBackwards(self, gesture):
        self.runSafely("findAgainBackwards", lambda: find.repeatFind(self, True))

    @script(
        description=_(
            "Lists any kind of element on the page, including kinds NVDA's own "
            "Elements List does not offer"
        ),
        category="HomerView",
    )
    def script_listAnyElements(self, gesture):
        self.runSafely("listAnyElements", lambda: homerCommands.chooseElementList(self))

    @script(description=_("Lists the headings on the page, like the JAWS heading list"), category="HomerView")
    def script_listHeadings(self, gesture):
        self.runSafely("listHeadings", lambda: homerCommands.listElements(self, "heading", _("Headings")))

    @script(description=_("Lists the links on the page, like the JAWS link list"), category="HomerView")
    def script_listLinks(self, gesture):
        self.runSafely("listLinks", lambda: homerCommands.listElements(self, "link", _("Links")))

    @script(description=_("Lists the form fields on the page, like the JAWS form field list"), category="HomerView")
    def script_listFormFields(self, gesture):
        self.runSafely("listFormFields", lambda: homerCommands.listElements(self, "formField", _("Form fields")))

    def _hasSelection(self):
        try:
            info = self.makeTextInfo(textInfos.POSITION_SELECTION)
            return bool((info.text or "").strip())
        except Exception:
            return False

    def buildCommandEntries(self):
        """Every command available right now, page commands and global ones."""
        lEntries = self._buildPageEntries()
        try:
            lEntries.extend(service.buildGlobalCommandEntries())
        except Exception:
            logError("The global commands could not be listed")
        iPage = sum(1 for entry in lEntries if entry.sScope == pageScopeName)
        homerLog.info(
            f"Alternate menu built with {len(lEntries)} commands: "
            f"{iPage} for this page, {len(lEntries) - iPage} available anywhere"
        )
        return lEntries

    def _buildPageEntries(self):
        lEntries = [
            self._homer("toggleSayAll", _("Start reading continuously, or stop reading")),
            self._homer("togglePunctuation", _("Switch punctuation between all and none")),
            self._homer("speakFaster", _("Speak faster")),
            self._homer("speakSlower", _("Speak slower")),
            self._homer("speakLouder", _("Speak louder")),
            self._homer("speakSofter", _("Speak more softly")),
            self._homer("reportSpeechSettings", _("Report the punctuation level, rate and volume")),
            self._homer("readAll", _("Read the whole page without moving the cursor")),
            self._homer("copyAll", _("Copy the whole page to the clipboard")),
            self._homer("copyLineOrSelection", _("Copy the selection, or the current line when nothing is selected")),
            self._homer("copyAppend", _("Append the selection, or the current line, to the clipboard")),
            self._homer("pageInformation", _("Report what the page says about itself")),
            self._homer("actOnPage", _("Act on the page by describing what you want")),
            self._homer("proxyMainContent", _("Jump to Probable Main Content, when the page declares none")),

            self._homer("runAccessibilityCheck", _("Test this page for accessibility, choosing the engine")),
            self._homer("nextSentence", _("Move to the next sentence and read it")),
            self._homer("priorSentence", _("Move to the previous sentence and read it")),
            self._homer("nextParagraph", _("Move to the next paragraph and read it")),
            self._homer("priorParagraph", _("Move to the previous paragraph and read it")),
            self._homer("runIbmChecker", _("Test the page with the IBM Equal Access engine")),
            self._homer("findText", _("Find text, not case sensitive")),
            self._homer("findTextBackwards", _("Find text backwards, not case sensitive")),
            self._homer("findByPattern", _("Find a regular expression")),
            self._homer("findByPatternBackwards", _("Find a regular expression backwards")),
            self._homer("findAgain", _("Repeat the last find")),
            self._homer("findAgainBackwards", _("Repeat the last find, backwards")),
            self._homer("listHeadings", _("List the headings on the page")),
            self._homer("listLinks", _("List the links on the page")),
            self._homer("listFormFields", _("List the form fields on the page")),
            self._homer("listAnyElements", _("List any kind of element on the page")),
            self._homer("findWordAtCursor", _("Find the next occurrence of the word at the cursor")),
            self._homer("findWordAtCursorBackwards", _("Find the previous occurrence of the word at the cursor")),
            self._homer("openOtherFormat", _("Open a document of any popular format")),
            self._homer("elevateVersion", _("Check for a newer HomerView and install it")),
            self._homer("showHelp", _("Show the HomerView user guide")),
            self._homer("showAbout", _("Show what HomerView is and where it keeps its files")),
            self._homer("showHistory", _("Show the history of changes to HomerView")),
            self._homer("sayYield", _("Say how many characters, words and lines there are")),
            self._homer("sayYieldStructure", _("Say how many links, headings, landmarks, tables, frames and fields there are")),
            self._homer("sayPosition", _("Say the line, column and percentage position of the cursor")),
            self._homer("saySelected", _("Say the selected text")),
            self._homer("sayChunk", _("Say the run of non-blank characters at the cursor")),
            self._homer("sayRest", _("Read the rest of the page from the cursor")),
            self._homer("selectChunk", _("Select the run of non-blank characters at the cursor")),
            self._homer("startSelection", _("Mark where a selection should begin")),
            self._homer("completeSelection", _("Select from the marked start to the cursor")),
            self._homer("goToSelectionStart", _("Return to the marked start of the selection")),
            self._homer("urlReference", _("Say where the link at the cursor would go")),
            self._homer("pageUrls", _("Copy every link address on the page to the clipboard")),
            self._homer("pageName", _("Say the name of the page")),
            self._homer("sayTime", _("Say the time, and the date when pressed twice")),
            self._homer("goToPercent", _("Move to a percentage point through the page")),
            self._homer("goToPercentAgain", _("Move to the percentage point used last time")),
            self._homer("quoteClipboard", _("Say the clipboard text")),
            self._homer("clearClipboard", _("Clear the clipboard")),
            self._homer("saveClipboard", _("Save the clipboard to a text file")),
            self._homer("appendClipboard", _("Append the clipboard to a text file")),
            self._homer("hotkeySummary", _("Show every HomerView command as a document")),
            alternateMenu.CommandEntry(
                _("Report the page address"), "NVDA+A",
                _("Say the web address, spell it when pressed twice, copy it when pressed three times"),
                lambda: reportPageAddress(self), pageScopeName),
            alternateMenu.CommandEntry(
                _("Jump to Main Content"), "J",
                _("Jump to the page's main content landmark"),
                lambda: moveToMainContent(self), pageScopeName),
        ]
        # Commands that need something this page does not have are left out.
        # Copying the selection when there is none, or completing a selection
        # that was never started, are choices a reader should not be offered.
        bSelection = self._hasSelection()
        bSelecting = bool(homerCommands.dSelectionStart.get(id(self)))
        # A menu entry carries its readable name, not its script name, so the
        # comparison has to be made in the same language.
        lSkip = []
        if not bSelection:
            lSkip.extend(["saySelected", "goToSelectionStart"])
        if not bSelecting:
            lSkip.append("completeSelection")
        setSkip = {readableName(s) for s in lSkip}
        lAll = [entry for entry in lEntries if entry]




def askForPercent(iPrevious):
    """Ask how far through the page to move, and return a number or None."""
    import wx

    import gui

    gui.mainFrame.prePopup()
    try:
        dialog = wx.TextEntryDialog(
            gui.mainFrame,
            # Translators: Prompt for the Go to Percent command.
            _("Percentage through the page:"),
            # Translators: Title of the Go to Percent dialog.
            _("HomerView go to percent"),
            value=str(iPrevious) if iPrevious is not None else "50",
        )
        iResult = dialog.ShowModal()
        sValue = dialog.GetValue()
        dialog.Destroy()
    finally:
        gui.mainFrame.postPopup()
    if iResult != wx.ID_OK:
        return None
    return parsePercent(sValue)


def parsePercent(sValue):
    """Read 40, 40%, +10 or -10 and say which kind it is.

    A plain number means go to that point. A signed number means move that far
    from where you are, which is what a reader wants far more often: knowing
    you are two thirds through and wanting a little further is common, and
    working out that this means 72 is not.

    Returns a pair of the number and whether it is relative, or None.
    """
    sValue = str(sValue or "").strip().rstrip("%").strip()
    if not sValue:
        return None
    bRelative = sValue[0] in "+-"
    try:
        iNumber = int(sValue)
    except ValueError:
        # Translators: Reported when a percentage could not be understood.
        ui.message(_("Type a percentage such as 40, or a change such as plus 10"))
        return None
    if bRelative:
        return (max(-100, min(100, iNumber)), True)
    return (max(0, min(100, iNumber)), False)


def bindFallbackGestures(treeInterceptor):
    """Attach the commands to a tree interceptor that missed the overlay.

    Used when a document was already open, or was still being built, when
    HomerView connected, so the overlay class was never inserted and the
    composed class never took effect.

    Two things have to happen and an earlier version only did one of them.

    The instance's class is replaced with the composed class, because NVDA's
    bindGesture resolves a script name against the object's CLASS: a method
    placed on the instance is invisible to it. That part worked.

    Then every gesture has to be bound explicitly, because the initialiser that
    would have read the class's gesture table has already run. The earlier
    version bound only the three commands this function was first written for,
    so a page that took the fallback route got three of forty-four commands and
    the rest did nothing at all. A log line reporting three gestures bound where
    a working page reported forty-six is what gave it away.
    """
    classComposed = composeBufferClass(type(treeInterceptor))
    if not issubclass(classComposed, HomerViewBuffer):
        homerLog.error("The composed class is not a HomerView class; commands cannot be bound")
        return
    treeInterceptor.__class__ = classComposed
    homerLog.info(f"Fallback route: class swapped to {classComposed.__name__}")

    lBindings = list(dHomerGestures.items()) + [
        (sPageAddressGesture, "reportPageAddress"),
        (sMainContentGesture, "moveToMainContent"),
        (sMainContentAlternateGesture, "moveToMainContent"),
    ]
    iBound = 0
    for sGesture, sScript in lBindings:
        try:
            treeInterceptor.bindGesture(sGesture, sScript)
            iBound += 1
        except Exception as exception:
            homerLog.error(f"Fallback route: {sGesture} could not be bound to {sScript}: {exception}")
    homerLog.info(f"Fallback route: {iBound} of {len(lBindings)} gestures bound")


def composeBufferClass(classBase):
    """Return the HomerView browse-mode class for a given NVDA buffer class."""
    classComposed = dComposedClasses.get(classBase)
    if not classComposed:
        classComposed = type(
            "HomerView" + classBase.__name__,
            (HomerViewBuffer, classBase),
            {},
        )
        dComposedClasses[classBase] = classComposed
        homerLog.info(
            f"Composed browse mode class {classComposed.__name__} from {classBase.__name__}; "
            f"method resolution order is {[cls.__name__ for cls in classComposed.__mro__]}"
        )
    return classComposed


class HomerViewDocument(AutoPropertyObject):
    """Overlay class inserted in front of HomerView Edge document objects.

    Deriving from AutoPropertyObject matters. NVDA generates properties from
    _get_ methods through that class's metaclass, and a plain class would leave
    the method below as dead code while the base attribute stayed in force.
    """

    def _get_treeInterceptorClass(self):
        classBase = super().treeInterceptorClass
        homerLog.info(f"Tree interceptor class requested; NVDA supplied {classBase}")
        if not classBase:
            homerLog.warning("NVDA supplied no tree interceptor class, so no commands will be added")
            return classBase
        return composeBufferClass(classBase)
