"""The Homer interface, adapted from an editor to a browser.

The Homer editor interface is documented in Editor.txt of HomerKit, and its
browser adaptations in FxMax.txt and IEMax.txt. Those packages already worked
out which editor commands make sense in a read-only browser and what they should
be bound to, so this module follows them rather than reinventing the scheme.

Three principles carry across from the original and are worth stating, because
they explain choices that would otherwise look arbitrary.

A command with no selection assumes the obvious thing. Copy with nothing
selected copies the current line. Yield with nothing selected counts the whole
document. The user is not made to select something first to say what they
plainly meant.

Shift means append rather than replace. Copy Append adds to the clipboard
instead of overwriting it, and the clipboard export has an appending twin. This
is one keyboard pattern rather than a set of unrelated ones.

Repeating a key spells what it just said. Read All, Say Selected, Say Chunk and
Quote Clipboard all follow this, so a heard address or code can be checked
character by character without a second command.

The chunk is Homer's own unit: a run of non-blank characters, wider than a word
because word movement stops at punctuation. A url is one chunk and several
words, which is why Homer added it.
"""

import time

import addonHandler

from . import output
import api
import speech
import textInfos
import ui
from scriptHandler import getLastScriptRepeatCount

from . import clipboardTools
from . import homerText
from .logger import abbreviate, homerLog, logError, logSection

addonHandler.initTranslation()

maximumSpokenUrls = 200

dActContext = {}
dLastScript = {}
dSelectionStart = {}
dLastPercent = {}


def withLabel(sLabel, sText):
    """Prefix a label when the user has asked for one."""
    from . import pageBuffer

    if getattr(pageBuffer, "bSpeakCommandLabels", False) and sLabel:
        return f"{sLabel}, {sText}"
    return sText


def sayOrSpell(sText, sEmptyMessage):
    """Say text, or spell it when the same key was just pressed."""
    if not sText:
        ui.message(sEmptyMessage)
        return
    if getLastScriptRepeatCount() == 0:
        speech.speakText(sText)
    else:
        speech.speakSpelling(sText)


def readAll(treeInterceptor):
    """Say the whole page without moving the browse cursor."""
    logSection("Homer: read all")
    sText = homerText.allText(treeInterceptor)
    homerLog.info(f"Read all: {len(sText)} characters")
    # Translators: Reported when the page has no text.
    sayOrSpell(sText, _("The page is empty"))


def copyAll(treeInterceptor):
    """Copy the whole page to the clipboard."""
    sText = homerText.allText(treeInterceptor)
    if not sText:
        # Translators: Reported when the page has no text.
        ui.message(_("The page is empty"))
        return
    api.copyToClip(sText)
    iCharacters, iWords, iLines = homerText.countYield(sText)
    homerLog.info(f"Copy all: {iCharacters} characters")
    # Translators: Reported after copying the whole page.
    ui.message(_("Copied {characters} characters").format(characters=iCharacters))


def copyAppend(treeInterceptor):
    """Append the selection, or the current line, to the clipboard.

    The same rule as Control+C, with Shift meaning append rather than replace,
    which is the one keyboard pattern Homer uses throughout.
    """
    sText = homerText.selectedText(treeInterceptor) or homerText.lineText(treeInterceptor)
    if not sText.strip():
        # Translators: Reported when there is nothing to copy.
        ui.message(_("Nothing to copy"))
        return
    if clipboardTools.appendToClipboard(sText.rstrip("\r\n")):
        # Translators: Reported after appending to the clipboard.
        ui.message(_("Appended {characters} characters").format(characters=len(sText)))


def copyLineOrSelection(treeInterceptor):
    """Copy the selection, or the current line when nothing is selected.

    This is the Homer rule that a command with no selection assumes the obvious
    thing. Pressing Control+C on a line you are reading should copy that line,
    not silently do nothing because you had not selected it first.

    The selection is copied as plain text rather than handed back to the
    browser. Re-sending the keystroke would risk NVDA processing it again, and
    every other Homer clipboard command here is text based, so a mixture would
    be the surprising choice.
    """
    sSelected = homerText.selectedText(treeInterceptor)
    if sSelected:
        api.copyToClip(sSelected)
        homerLog.info(f"Copy: {len(sSelected)} selected characters")
        # Translators: Reported after copying the selected text.
        ui.message(_("Copied {characters} characters").format(characters=len(sSelected)))
        return
    sLine = homerText.lineText(treeInterceptor).rstrip("\r\n")
    if not sLine.strip():
        # Translators: Reported when there is nothing to copy.
        ui.message(_("Nothing to copy"))
        return
    api.copyToClip(sLine)
    homerLog.info(f"Copy: current line, {len(sLine)} characters")
    # Translators: Reported after copying the current line.
    ui.message(_("Line copied"))


def sayYield(treeInterceptor):
    """Say how much text there is, in the selection or the whole page."""
    sText, bSelected = homerText.textOrAll(treeInterceptor)
    iCharacters, iWords, iLines = homerText.countYield(sText)
    homerLog.info(f"Yield: {iCharacters} characters, {iWords} words, {iLines} lines, selected={bSelected}")
    from . import output

    output.lines(
        # Translators: Title of the box reporting how much text there is.
        _("Selected text") if bSelected else _("Page text"),
        [
            _("{count} characters").format(count=iCharacters),
            _("{count} words").format(count=iWords),
            _("{count} lines").format(count=iLines),
        ],
    )


def countNodes(treeInterceptor, sType):
    try:
        infoStart = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        return sum(1 for _item in treeInterceptor._iterNodesByType(sType, "next", infoStart))
    except Exception:
        return 0


def sayYieldStructure(treeInterceptor):
    """Say how the page is built, rather than how long it is."""
    dCounts = {
        "links": countNodes(treeInterceptor, "link"),
        "headings": countNodes(treeInterceptor, "heading"),
        "landmarks": countNodes(treeInterceptor, "landmark"),
        "tables": countNodes(treeInterceptor, "table"),
        "frames": countNodes(treeInterceptor, "frame"),
        "form fields": countNodes(treeInterceptor, "formField"),
    }
    from . import output

    homerLog.info(f"Yield structure: {dCounts}")
    output.lines(
        # Translators: Title of the box reporting what a page is built from.
        _("What this page holds"),
        [f"{iCount} {sName}" for sName, iCount in dCounts.items() if iCount],
    )


def sayPosition(treeInterceptor):
    """Say where the browse cursor is, as Homer's Address command does."""
    iLine, iColumn, iPercent = homerText.caretPosition(treeInterceptor)
    homerLog.info(f"Position: line {iLine}, column {iColumn}, {iPercent} percent")
    # A position is a phrase, so it stays spoken: a box for three words would
    # cost a keystroke and buy nothing.
    # NVDA's own position command leads with the percentage, which is the part
    # a reader actually wants; the line and column follow for precision.
    # Translators: Reported for the cursor position within the page.
    ui.message(
        _("{percent} percent, line {line}, column {column}").format(
            column=iColumn, line=iLine, percent=iPercent
        )
    )


def saySelected(treeInterceptor):
    sText = homerText.selectedText(treeInterceptor)
    homerLog.info(f"Say selected: {len(sText)} characters")
    # Translators: Reported when nothing is selected.
    sayOrSpell(sText, _("No selection"))


def sayChunk(treeInterceptor):
    sText = homerText.chunkText(treeInterceptor)
    homerLog.info(f"Say chunk: {abbreviate(sText, 120)}")
    # Translators: Reported when the cursor is not on a chunk of text.
    sayOrSpell(sText, _("No chunk here"))


def sayRest(treeInterceptor):
    """Say the rest of the page from the cursor, without moving it."""
    sText = homerText.restText(treeInterceptor)
    homerLog.info(f"Say rest: {len(sText)} characters")
    # Translators: Reported when the cursor is at the end of the page.
    sayOrSpell(sText, _("Nothing after the cursor"))


def selectChunk(treeInterceptor):
    """Select the run of non-blank characters at the cursor."""
    sChunk = homerText.chunkText(treeInterceptor)
    if not sChunk:
        # Translators: Reported when the cursor is not on a chunk of text.
        ui.message(_("No chunk here"))
        return
    try:
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        info.expand(textInfos.UNIT_LINE)
        sLine = info.text or ""
        iStart = sLine.find(sChunk)
        if iStart < 0:
            raise ValueError("the chunk was not found on the line")
        infoLine = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        infoLine.expand(textInfos.UNIT_LINE)
        infoChunk = infoLine.copy()
        infoChunk.collapse()
        infoChunk.move(textInfos.UNIT_CHARACTER, iStart)
        infoChunk.move(textInfos.UNIT_CHARACTER, len(sChunk), "end")
        infoChunk.updateSelection()
        homerLog.info(f"Selected chunk of {len(sChunk)} characters")
        # Translators: Reported after selecting a chunk of text.
        ui.message(_("Selected {characters} characters").format(characters=len(sChunk)))
    except Exception:
        logError("The chunk could not be selected")
        speech.speakText(sChunk)


def startSelection(treeInterceptor):
    """Mark where a selection should begin, so Shift need not be held."""
    try:
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        dSelectionStart[id(treeInterceptor)] = info.copy()
        iLine, iColumn, iPercent = homerText.caretPosition(treeInterceptor)
        homerLog.info(f"Selection start marked at line {iLine}, column {iColumn}")
        # Translators: Reported after marking the start of a selection.
        ui.message(_("Selection start, line {line}").format(line=iLine))
    except Exception:
        logError("The selection start could not be marked")


def completeSelection(treeInterceptor):
    """Select from the marked start to the cursor."""
    infoStart = dSelectionStart.get(id(treeInterceptor))
    if not infoStart:
        # Translators: Reported when no selection start has been marked.
        ui.message(_("Press F8 first to mark the start"))
        return
    try:
        infoEnd = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        infoRange = infoStart.copy()
        infoRange.setEndPoint(infoEnd, "endToEnd")
        infoRange.updateSelection()
        sText = infoRange.text or ""
        homerLog.info(f"Selection completed: {len(sText)} characters")
        # Translators: Reported after completing a selection.
        ui.message(_("Selected {characters} characters").format(characters=len(sText)))
    except Exception:
        logError("The selection could not be completed")
        # Translators: Reported when a selection could not be made.
        ui.message(_("The selection could not be made"))


def goToSelectionStart(treeInterceptor):
    infoStart = dSelectionStart.get(id(treeInterceptor))
    if not infoStart:
        # Translators: Reported when no selection start has been marked.
        ui.message(_("Press F8 first to mark the start"))
        return
    infoStart.updateCaret()
    infoLine = infoStart.copy()
    infoLine.expand(textInfos.UNIT_LINE)
    speech.speakText(infoLine.text or "")


def linkAtCursor(treeInterceptor):
    """Return the NVDA object for the link at the cursor, or None."""
    try:
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        obj = info.NVDAObjectAtStart
    except Exception:
        return None
    for _iStep in range(6):
        if not obj:
            return None
        sRole = str(getattr(obj, "role", "")).lower()
        if "link" in sRole:
            return obj
        obj = getattr(obj, "parent", None)
    return None


def urlReference(treeInterceptor):
    """Say where the link at the cursor would go."""
    obj = linkAtCursor(treeInterceptor)
    sUrl = (getattr(obj, "value", "") or "") if obj else ""
    homerLog.info(f"Url reference: {abbreviate(sUrl, 300)}")
    if not sUrl:
        # Translators: Reported when the cursor is not on a link.
        ui.message(_("No link here"))
        return
    if getLastScriptRepeatCount() == 0:
        ui.message(sUrl)
    else:
        api.copyToClip(sUrl)
        # Translators: Reported after copying a link address.
        ui.message(_("Link address copied"))


def pageUrls(treeInterceptor):
    """Collect every link address on the page onto the clipboard."""
    lUrls = []
    try:
        infoStart = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        for item in treeInterceptor._iterNodesByType("link", "next", infoStart):
            sUrl = (getattr(getattr(item, "obj", None), "value", "") or "").strip()
            if sUrl and sUrl not in lUrls:
                lUrls.append(sUrl)
            if len(lUrls) >= maximumSpokenUrls:
                break
    except Exception:
        logError("The page addresses could not be collected")
    if not lUrls:
        # Translators: Reported when the page has no links.
        ui.message(_("No link addresses were found"))
        return
    api.copyToClip("\r\n".join(lUrls))
    homerLog.info(f"Page urls: {len(lUrls)} collected to the clipboard")
    # Translators: Reported after collecting the page's link addresses.
    ui.message(_("{count} addresses copied").format(count=len(lUrls)))


def pageName(treeInterceptor):
    """Say the page name, which is the title without the browser's suffix."""
    sName = ""
    try:
        sName = (getattr(treeInterceptor.rootNVDAObject, "name", "") or "").strip()
    except Exception:
        sName = ""
    if not sName:
        obj = api.getForegroundObject()
        sName = (getattr(obj, "name", "") or "").split(" - ")[0].strip()
    homerLog.info(f"Page name: {abbreviate(sName, 200)}")
    # Translators: Reported when the page has no name.
    sayOrSpell(sName, _("The page has no name"))


def sayTime():
    """Say the time, and the date when the key is repeated."""
    if getLastScriptRepeatCount() == 0:
        ui.message(time.strftime("%I:%M %p").lstrip("0"))
    else:
        ui.message(time.strftime("%A, %d %B %Y"))


def goToPercent(treeInterceptor, iPercent):
    info = homerText.moveToPercent(treeInterceptor, iPercent)
    if not info:
        # Translators: Reported when the page has no text.
        ui.message(_("The page is empty"))
        return
    dLastPercent[id(treeInterceptor)] = iPercent
    homerLog.info(f"Moved to {iPercent} percent")
    speech.speakText(info.text or "")


def pageInformation(treeInterceptor):
    """Show what the page declares about itself, in a readable window."""
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    # Translators: Reported while the page information is gathered.
    ui.message(_("Reading the page information"))
    service.submit(
        "pageInformation",
        service.taskPageInformation,
        showPageInformation,
        lambda exception: ui.message(str(exception)),
    )


def showPageInformation(dSummary):
    lFields = dSummary.get("fields") or []
    homerLog.info(f"Page information ready: {len(lFields)} fields")
    sTitle = _("Page information")
    output.show(dSummary.get("html", ""), sTitle)


def askAndFind(treeInterceptor, bBackwards, bRegex=True):
    from . import lbc

    lbc.afterScript(_askAndFindNow, treeInterceptor, bBackwards, bRegex)


def _askAndFindNow(treeInterceptor, bBackwards, bRegex=True):
    """Ask for a pattern and search for it.

    Regular expressions are the default here because the command is bound to
    Control+F3 for that purpose. Plain text still works: anything without
    regular expression punctuation means itself.
    """
    from . import find
    from . import lbc

    def onAnswer(sPattern):
        if sPattern is None or not sPattern.strip():
            homerLog.info("Find cancelled")
            return
        find.findInBuffer(treeInterceptor, sPattern, bRegex, bBackwards)

    lbc.dialogInput(
        # Translators: Title of the find dialog.
        _("Find backwards") if bBackwards else _("Find"),
        # Translators: Label of the find field.
        _("Text or regular expression:"),
        find.dLastFind.get("pattern", ""),
        functionDone=onAnswer,
    )


# JAWS lists elements with Insert+Control plus the same letter as its quick
# navigation key, which is a memorable rule. It cannot be copied here: NVDA
# spends almost the whole of NVDA+Control+letter on its settings dialogs, so
# mirroring the pattern would break a dozen NVDA commands to gain a dozen
# HomerView ones. One command that asks which kind costs a single extra
# keystroke and breaks nothing.
#
# The types NVDA's own Elements List cannot offer are marked, because those are
# the ones this actually adds.
lElementTypes = [
    ("heading", "Headings", False),
    ("link", "Links", False),
    ("formField", "Form fields", False),
    ("button", "Buttons", False),
    ("landmark", "Landmarks", False),
    ("table", "Tables", True),
    ("list", "Lists", True),
    ("listItem", "List items", True),
    ("graphic", "Graphics", True),
    ("checkBox", "Check boxes", True),
    ("radioButton", "Radio buttons", True),
    ("comboBox", "Combo boxes", True),
    ("edit", "Edit fields", True),
    ("blockQuote", "Block quotes", True),
    ("frame", "Frames", True),
    ("separator", "Separators", True),
    ("annotation", "Annotations", True),
    ("embeddedObject", "Embedded objects", True),
]


def chooseElementList(treeInterceptor):
    """Ask which kind of element to list, then list it."""
    from . import lbc

    lbc.afterScript(_chooseElementListNow, treeInterceptor)


def _chooseElementListNow(treeInterceptor):
    from . import lbc

    logSection("Command: list elements")
    lLabels = []
    for sType, sTitle, bBeyondNvda in lElementTypes:
        iCount = countNodes(treeInterceptor, sType)
        if not iCount:
            continue
        # Translators: An entry in the element list chooser. The placeholders
        # are the kind of element and how many the page holds.
        sLabel = _("{name}: {count}").format(count=iCount, name=sTitle)
        lLabels.append((sLabel, sType, sTitle))
    homerLog.info(f"Element kinds present on this page: {len(lLabels)}")
    if not lLabels:
        # Translators: Reported when a page holds none of the listable kinds.
        ui.message(_("This page has nothing to list"))
        return
    sChoice = lbc.dialogChoose(
        # Translators: Title of the dialog choosing which elements to list.
        _("List elements"),
        # Translators: Prompt above the list of element kinds.
        _("Choose what to list. The number is how many this page holds."),
        [sLabel for sLabel, _sType, _sTitle in lLabels],
    )
    if not sChoice:
        homerLog.info("Element list cancelled")
        return
    for sLabel, sType, sTitle in lLabels:
        if sLabel == sChoice:
            _listElementsNow(treeInterceptor, sType, sTitle)
            return


def listElements(treeInterceptor, sType, sTitle):
    from . import lbc

    lbc.afterScript(_listElementsNow, treeInterceptor, sType, sTitle)


def _listElementsNow(treeInterceptor, sType, sTitle):
    """Offer the page's headings, links or form fields as a list.

    This is what JAWS gives on Insert+F5, Insert+F6 and Insert+F7. NVDA has one
    combined Elements List on NVDA+F7, which is more capable but needs a radio
    button chosen first. A reader who wants the links wants them now.
    """
    from . import lbc

    logSection(f"Command: list {sType}")
    lItems = []
    try:
        infoStart = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        for item in treeInterceptor._iterNodesByType(sType, "next", infoStart):
            sLabel = (getattr(item, "label", "") or "").strip()
            if sLabel:
                lItems.append((sLabel, item))
    except NotImplementedError:
        # Translators: Message when a quick navigation command is not supported.
        ui.message(_("Not supported in this document"))
        return
    except Exception:
        logError(f"The {sType} list could not be built")
        # Translators: Reported when a list of elements could not be built.
        ui.message(_("That list could not be built"))
        return

    homerLog.info(f"{sTitle}: {len(lItems)} found")
    if not lItems:
        # Translators: Reported when a page has none of the requested elements.
        ui.message(_("No {name} were found").format(name=sTitle.lower()))
        return

    def onChoice(sChoice):
        if not sChoice:
            homerLog.info(f"{sTitle} list cancelled")
            return
        for sLabel, item in lItems:
            if sLabel == sChoice:
                homerLog.info(f"Moving to {abbreviate(sLabel, 120)}")
                try:
                    item.report(readUnit=textInfos.UNIT_LINE)
                except Exception:
                    pass
                item.moveTo()
                return

    lbc.dialogChoose(
        sTitle,
        # Translators: Prompt above a list of page elements.
        _("{count} found. Choose one to move there.").format(count=len(lItems)),
        [sLabel for sLabel, _item in lItems],
        functionDone=onChoice,
    )


def findWordAtCursor(treeInterceptor, bBackwards):
    """Search for the next occurrence of the word under the cursor.

    Homer's Word Find. Nothing has to be typed, which is the point: having
    heard a term, you want the next place it appears, not a dialog.
    """
    from . import find

    # A selection says what the word is more precisely than the cursor can, so
    # when there is one it wins.
    sWord = homerText.selectedText(treeInterceptor).strip()
    if not sWord:
        sWord = homerText.chunkText(treeInterceptor).strip(".,;:!?()[]{}\"'")
    if not sWord:
        # Translators: Reported when the cursor is not on a word.
        ui.message(_("No word here"))
        return
    homerLog.info(f"Word find: {abbreviate(sWord, 80)}")
    find.findInBuffer(treeInterceptor, sWord, False, bBackwards)


def openDocument():
    """Open a file of any popular format, or a web address.

    Bound to Control+O as well as Control+F10. Edge's own Control+O opens a
    file the browser can already read; this opens those and every format 2htm
    converts, so nothing is lost and a great deal is gained. That is the test
    for taking a key that already does something.
    """
    from .service import service

    service.runOpenDocumentCommand()


def showDocument(sWhich):
    """Show the user guide, the About text, or the history of changes."""
    from . import documents

    documents.show(sWhich)


def actOnPage():
    from . import lbc

    lbc.afterScript(_actOnPageNow)


def describeScript(sScript):
    """Say what running this script would do, without doing any of it.

    A script that acts on a page is worth checking before it runs. Test reads
    each line the way the runner will, and reports the verb, the target and the
    value it found, so a mistyped instruction is caught before it clicks
    something.
    """
    from . import act

    lLines = [s.strip() for s in str(sScript or "").splitlines()]
    lLines = [s for s in lLines if s and not s.startswith("#")]
    if not lLines:
        return _("There is nothing to run yet.")
    lParts = [_("{count} instructions would run, in this order:").format(count=len(lLines))]
    for iIndex, sLine in enumerate(lLines, 1):
        sVerb, sTarget, sValue = act.parsePhrase(sLine)
        if not sTarget:
            lParts.append(
                _("{index}. {line} — no target named, so the script would stop here").format(
                    index=iIndex, line=sLine))
            break
        if sValue:
            lParts.append(_("{index}. {verb} \"{value}\" into whatever best matches \"{target}\"").format(
                index=iIndex, target=sTarget, value=sValue, verb=sVerb))
        else:
            lParts.append(_("{index}. {verb} whatever best matches \"{target}\"").format(
                index=iIndex, target=sTarget, verb=sVerb))
    lParts.append("")
    lParts.append(_("Each instruction acts on the closest match by role and name. "
                    "The script stops at the first line that matches nothing."))
    return "\n".join(lParts)


def scriptHelpText():
    """What can be written in a script."""
    return "\n".join([
        _("Write one instruction a line. A line beginning with a hash is a comment."),
        "",
        _("What you can do:"),
        _("  click, press, open, follow, select, choose — activate something"),
        _("  type, enter, fill — put text into a field, as in: type Jamal into search"),
        _("  check, tick, uncheck, untick — set a check box"),
        _("  focus — move to something without activating it"),
        _("  read — say the text of something"),
        "",
        _("Naming what to act on:"),
        _("  Use the words you would hear. Click sign in. Type London into city."),
        _("  You may name the kind as well: the search field, the Download link."),
        _("  Naming a kind makes matches of that kind more likely to win, "
          "rather than ruling others out."),
        "",
        _("Example:"),
        _("  # sign in, then search"),
        _("  click sign in"),
        _("  type me@example.org into email"),
        _("  click submit"),
        "",
        _("This is HomerView's own matching, not a language model. Nothing about "
          "the page leaves your computer."),
    ])


def _actOnPageNow():
    """Ask what to do, find what could be meant, and do it."""
    from . import act
    from . import lbc
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    def onPhrase(sPhrase):
        if not sPhrase or not sPhrase.strip():
            homerLog.info("Act cancelled")
            return
        homerLog.info(f"Act phrase: {abbreviate(sPhrase, 200)}")
        # Translators: Reported while the page's controls are examined.
        ui.message(_("Looking for that"))
        service.submit(
            "surveyPage",
            service.taskSurveyPage,
            lambda tSurvey: chooseAndAct(tSurvey, sPhrase),
            lambda exception: ui.message(str(exception)),
        )

    lbc.dialogInput(
        # Translators: Title of the act on page dialog.
        _("Act on the page"),
        # Translators: Label of the field describing an action.
        _("What would you like to do? For example, click sign in:"),
        "",
        functionDone=onPhrase,
    )


def chooseAndAct(tSurvey, sPhrase):
    """Offer what matched, then carry out the chosen action."""
    from . import act
    from . import lbc
    from .service import service

    lSurvey, sSessionId = tSurvey
    sVerb, sTarget, sValue = act.parsePhrase(sPhrase)
    dActContext.clear()
    dActContext.update({"sessionId": sSessionId, "value": sValue, "verb": sVerb})
    homerLog.info(f"Parsed as verb={sVerb} target={sTarget!r} value={sValue!r}")
    if not sTarget:
        # Translators: Reported when a phrase names no target.
        ui.message(_("Say what to act on, such as click sign in"))
        return
    lScored = act.findCandidates(lSurvey, sTarget)
    homerLog.info(f"{len(lScored)} candidates; best score {lScored[0][0] if lScored else 0}")
    for iScore, dCandidate in lScored:
        homerLog.debug(f"  {iScore:3d} {act.describeCandidate(dCandidate)}")
    if not lScored:
        # Translators: Reported when nothing on the page matched.
        ui.message(_("Nothing on this page matches that"))
        return

    dChosen = None
    if len(lScored) == 1 or lScored[0][0] >= act.strongScore:
        dChosen = lScored[0][1]
        homerLog.info("One clear match, acting without asking")
    else:
        lLabels = [act.describeCandidate(d) for _iScore, d in lScored]
        def onChoice(sChoice):
            if not sChoice:
                homerLog.info("Act cancelled at the choice")
                return
            for sLabel, (_iScore, dCandidate) in zip(lLabels, lScored):
                if sLabel == sChoice:
                    runAction(dCandidate)
                    return

        lbc.dialogChoose(
            # Translators: Title of the dialog choosing what to act on.
            _("Which one?"),
            # Translators: Prompt above the list of matching controls.
            _("{count} things could match. Choose one.").format(count=len(lLabels)),
            lLabels,
            functionDone=onChoice,
        )
        return
    if dChosen:
        runAction(dChosen)


def runAction(dChosen, sSessionId=None, sVerb="click", sValue=""):
    """Carry out one chosen action on the worker thread."""
    from .service import service

    dContext = dActContext
    sSessionId = sSessionId or dContext.get("sessionId")
    sVerb = dContext.get("verb", sVerb)
    sValue = dContext.get("value", sValue)
    # Translators: Reported just before an action is carried out.
    ui.message(_("{verb} {name}").format(name=dChosen.get("name", ""), verb=sVerb))
    service.submit(
        "actOnPage",
        service.makeActTask(sSessionId, dChosen, sVerb, sValue),
        reportActed,
        lambda exception: ui.message(str(exception)),
    )


def reportActed(dSummary):
    homerLog.info(f"Acted: {dSummary}")
    sResult = str(dSummary.get("result", ""))
    if dSummary.get("verb") == "read" and sResult:
        speech.speakText(sResult)
        return
    # Translators: Reported after an action on the page.
    ui.message(_("Done"))


def runAccessibilityCheck():
    """Ask which engine to use, then run it.

    Two engines disagree usefully. axe checks WCAG. The IBM ruleset checks a
    superset that also covers EN 301 549 and Section 508, and it separates a
    recommendation from a failure. Offering both under one key means a reader
    chooses what they need rather than remembering two keys, and leaves room
    for a third engine without another binding.
    """
    from . import lbc
    from . import settings

    lChoices = [
        _("Deque axe-core, with a report and how to reach the publisher"),
        _("IBM Equal Access, saving JSON, CSV, a spreadsheet and a web page"),
        _("Both, one after the other"),
    ]
    sPrevious = settings.getRecent("accessibilityEngine", lChoices[0])
    iStart = lChoices.index(sPrevious) if sPrevious in lChoices else 0
    sChoice = lbc.dialogChoose(
        # Translators: Title of the dialog choosing an accessibility engine.
        _("Test this page for accessibility"),
        # Translators: Prompt above the list of accessibility engines.
        _("Which engine should test this page?"),
        lChoices, iStart)
    if not sChoice:
        homerLog.info("Accessibility check cancelled")
        return
    settings.setRecent("accessibilityEngine", sChoice)
    homerLog.info(f"Accessibility engine chosen: {sChoice}")
    if sChoice == lChoices[0]:
        runAxeReport()
    elif sChoice == lChoices[1]:
        runIbmChecker()
    else:
        runAxeReport()
        runIbmChecker()


def runAxeReport():
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    # Translators: Reported while the accessibility test runs.
    ui.message(_("Testing the page and looking for reporting channels"))
    service.submit("accessibilityReport", service.taskAccessibilityReport,
                   showAxeReport, lambda exception: ui.message(str(exception)))


def showAxeReport(dSummary):
    from . import output

    dCounts = dSummary.get("counts", {})
    output.lines(
        # Translators: Title of the box reporting an accessibility scan.
        _("Accessibility report"),
        [
            _("{count} violations").format(count=dCounts.get("violations", 0)),
            _("{count} needing review").format(count=dCounts.get("incomplete", 0)),
            _("Saved to {path}").format(path=dSummary.get("reportPath", "")),
        ],
    )


def runIbmChecker():
    """Run the IBM Equal Access engine and show its report."""
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    # Translators: Reported while the IBM engine runs.
    ui.message(_("Testing the page with the IBM engine"))
    service.submit("runAce", service.taskRunAce, showIbmReport,
                   lambda exception: ui.message(str(exception)))


def showIbmReport(dSummary):
    from . import ace

    dCounts = dSummary.get("counts", {})
    homerLog.info(f"IBM report ready: {dCounts}")
    sTitle = _("IBM Equal Access report")
    output.show(ace.buildReportHtml(dSummary), sTitle)
    dExported = dSummary.get("exported", {}) or {}
    lWritten = sorted((dExported.get("written") or {}).keys())
    if lWritten:
        # Translators: Reported after the reports are saved. The placeholders
        # are a list of formats and the folder they went to.
        ui.message(
            _("Saved as {formats} in {folder}").format(
                folder=dExported.get("folder", ""), formats=", ".join(lWritten)
            )
        )
    # Translators: Reported after the IBM engine finishes.
    ui.message(
        _("{violations} violations, {review} needing review, {advice} recommendations").format(
            advice=dCounts.get("recommendation", 0),
            review=dCounts.get("needs review", 0),
            violations=dCounts.get("violation", 0),
        )
    )


def moveToProxyMainContent(treeInterceptor, gesture=None):
    """Reach the main content of a page that never declared any.

    About half the web defines no main landmark, and J correctly refuses to
    guess. This is the deliberate guess, on its own key, so the two are never
    confused: the first heading inside an article, then the first heading after
    the banner and navigation, then the first heading at all.

    Each attempt says which rule found the destination, so the reader knows
    they were taken somewhere inferred rather than somewhere declared.
    """
    from . import pageBuffer

    logSection("Command: proxy to the main content")
    try:
        infoStart = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        lLandmarks = []
        for item in treeInterceptor._iterNodesByType("landmark", "next", infoStart):
            lLandmarks.append(item)
            if pageBuffer.isMainLandmark(item):
                homerLog.info("A main landmark exists after all; using it")
                pageBuffer.reportQuickNavItem(item, gesture)
                return
        # No main landmark. Move past the banner and navigation, then take the
        # first heading, which on a page without landmarks is the article title.
        infoAfterFurniture = infoStart
        for item in lLandmarks:
            sRole = (getattr(getattr(item, "obj", None), "landmark", "") or "").lower()
            if sRole in ("banner", "navigation", "search"):
                try:
                    infoAfterFurniture = item.textInfo.copy()
                except Exception:
                    pass
        for item in treeInterceptor._iterNodesByType("heading", "next", infoAfterFurniture):
            homerLog.info(f"Proxy main content: first heading past the page furniture")
            # Translators: Reported when main content was inferred, not declared.
            ui.message(_("No main landmark. First heading after the navigation."))
            pageBuffer.reportQuickNavItem(item, gesture)
            return
        for item in treeInterceptor._iterNodesByType("heading", "next", infoStart):
            homerLog.info("Proxy main content: first heading on the page")
            # Translators: Reported when main content was inferred, not declared.
            ui.message(_("No main landmark. First heading."))
            pageBuffer.reportQuickNavItem(item, gesture)
            return
    except NotImplementedError:
        # Translators: Message when a quick navigation command is not supported.
        ui.message(_("Not supported in this document"))
        return
    except Exception:
        logError("The proxy main content could not be found")
        # Translators: Reported when main content could not be inferred.
        ui.message(_("HomerView could not find anything that looks like main content"))
        return
    homerLog.info("Proxy main content: nothing to move to")
    # Translators: Reported when a page has no headings or landmarks at all.
    ui.message(_("no main content and no headings"))


def explorePageFromBuffer():
    """The page explorer, reachable by a single letter inside a page."""
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    # Translators: Reported while the page is summarised.
    ui.message(_("Exploring the page"))
    service.submit("explorePage", service.taskExplorePage, showExploreResult,
                   lambda exception: ui.message(str(exception)))


def showExploreResult(dSummary):
    from . import output

    output.show(dSummary.get("html", ""), _("Page explorer"))


def submitForm():
    """Submit the form containing the focused field, from any field.

    This is the Lbc convenience carried onto the web. In a dialog, plain Enter
    is swallowed by controls that handle it themselves, so Lbc added
    Control+Enter as the one key that always accepts. A web form has the same
    problem: Enter submits from a text field but not from a text area, a list,
    or a checkbox, and a form whose submit button sits at the end of a long
    page is a long way to tab.

    The submission has to be a real one. requestSubmit is used rather than
    submit, because submit bypasses both the form's own validation and its
    submit event, which means a page that checks its fields in script would
    never see the attempt. requestSubmit behaves exactly as pressing the submit
    button does, including refusing to send an incomplete form and showing the
    same message the user would have seen.
    """
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    logSection("Command: submit the form")
    service.submit("submitForm", service.taskSubmitForm, reportSubmitted,
                   lambda exception: ui.message(str(exception)))


def reportSubmitted(dResult):
    sOutcome = (dResult or {}).get("outcome", "")
    homerLog.info(f"Submit form: {dResult}")
    if sOutcome == "submitted":
        # Translators: Reported after a form is submitted.
        ui.message(_("Form submitted"))
    elif sOutcome == "invalid":
        # Translators: Reported when the browser refused an incomplete form.
        ui.message(_("The form is incomplete. The browser is showing what is missing."))
    elif sOutcome == "noForm":
        # Translators: Reported when the focus is not inside a form.
        ui.message(_("The cursor is not in a form"))
    else:
        # Translators: Reported when a form could not be submitted.
        ui.message(_("That form could not be submitted"))


def moveByUnit(treeInterceptor, sUnit, bForward, sWhatNone):
    """Move the browse cursor by a unit and read where it landed.

    NVDA leaves the cursor where it was when a movement finds nothing, and so
    does this. The keys are EdSharp's, which NVDA leaves unassigned in browse
    mode, so nothing is displaced.
    """
    try:
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        iMoved = info.move(sUnit, 1 if bForward else -1)
        if not iMoved:
            ui.message(sWhatNone)
            return
        info.updateCaret()
        info.expand(sUnit)
        sText = (info.text or "").strip()
        homerLog.info(f"Moved by {sUnit}: {abbreviate(sText, 120)}")
        speech.speakText(sText or sWhatNone)
    except Exception:
        logError(f"Moving by {sUnit} failed")
        # Translators: Reported when a movement command failed.
        ui.message(_("That movement is not supported here"))


def moveBySentence(treeInterceptor, bForward):
    moveByUnit(
        treeInterceptor,
        textInfos.UNIT_SENTENCE,
        bForward,
        # Translators: Reported at the first or last sentence.
        _("No next sentence") if bForward else _("No previous sentence"),
    )


def moveByParagraph(treeInterceptor, bForward):
    moveByUnit(
        treeInterceptor,
        textInfos.UNIT_PARAGRAPH,
        bForward,
        # Translators: Reported at the first or last paragraph.
        _("No next paragraph") if bForward else _("No previous paragraph"),
    )


def elevateVersion():
    """Check for a newer HomerView and install it."""
    from . import lbc

    lbc.afterScript(_elevateVersionNow)


def _elevateVersionNow():
    from . import elevate
    from . import lbc
    from . import output
    from .service import service

    # Translators: Reported while the version check runs.
    ui.message(_("Checking for a newer version"))
    try:
        dCheck = elevate.checkForUpdate()
    except Exception as exception:
        lbc.dialogInfo(_("Elevate version"), str(exception))
        return

    sInstalled, sLatest = dCheck["installed"], dCheck["latest"]
    iComparison = dCheck["comparison"]

    if iComparison < 0:
        # The developer's own machine, and not a fault.
        lbc.dialogInfo(
            _("Elevate version"),
            _("HomerView is running a newer version than the latest public release.\n\n"
              "Installed: {installed}\nPublished: {latest}\n\nNo change offered.").format(
                installed=sInstalled, latest=sLatest))
        return

    if iComparison == 0:
        sQuestion = _(
            "HomerView is already up to date.\n\n"
            "Installed: {installed}\nPublished: {latest}\n\n"
            "Install this version again anyway? That repairs an installation that did "
            "not take.").format(installed=sInstalled, latest=sLatest)
    else:
        sQuestion = _(
            "A newer HomerView is available.\n\n"
            "Installed: {installed}\nAvailable: {latest}\n\n"
            "Download it and hand it to NVDA now? NVDA will ask you to confirm, and "
            "will restart afterwards.").format(installed=sInstalled, latest=sLatest)
    if lbc.dialogConfirm(_("Elevate version"), sQuestion) is not True:
        homerLog.info("Elevate version declined")
        return

    # Translators: Reported while the add-on downloads.
    ui.message(_("Downloading"))
    try:
        dResult = elevate.installAddon()
    except Exception as exception:
        lbc.dialogInfo(
            _("Elevate version"),
            _("The download failed.\n\n{reason}\n\nYou can download it directly from "
              "{url}").format(reason=exception, url=elevate.latestPageUrl))
        return

    if dResult.get("opened"):
        lbc.dialogInfo(
            _("Elevate version"),
            _("The add-on has been handed to NVDA. Confirm the installation when NVDA "
              "asks, and let it restart.\n\nThe program files, the documentation and the "
              "converters are updated separately by the installer at {url}").format(
                url=elevate.latestPageUrl))
    else:
        lbc.dialogInfo(
            _("Elevate version"),
            _("The add-on downloaded but could not be opened. Run this file yourself:\n\n"
              "{path}").format(path=dResult.get("path", "")))


def toggleSayAll(treeInterceptor):
    """Start reading continuously, or stop if it is already reading.

    Scroll Lock is chosen because it is a key nobody is using. Windows gave it
    a meaning in 1981 and almost nothing has honoured it since; Microsoft Edge
    does not use it, NVDA does not bind it, and no browse mode command touches
    it. It is also large, isolated, and unlikely to be pressed by accident,
    which is what a start and stop key should be.

    One key doing both is the point. NVDA's own arrangement is NVDA+DownArrow
    to begin and Control to stop, which is two keys and a modifier for what is
    really one idea: read, and stop reading. This is the friendlier form.

    This does not replace Read All on Alt+F8. That says the whole page as one
    utterance and leaves the cursor alone, which is Homer's meaning. Say All
    moves the cursor as it goes, so a reader can stop and be where they
    stopped. Both are worth having and they are not the same thing.
    """
    from speech import sayAll as sayAllModule

    bReading = False
    try:
        bReading = bool(sayAllModule.SayAllHandler.isRunning())
    except Exception:
        # Older builds do not offer the query. Cancelling when nothing is
        # reading is harmless, so the uncertain case is treated as reading.
        bReading = bool(speech.getState().speechMode) if hasattr(speech, "getState") else False

    if bReading:
        homerLog.info("Say all: stopping")
        try:
            sayAllModule.SayAllHandler.stop()
        except Exception:
            speech.cancelSpeech()
        return

    homerLog.info("Say all: starting from the cursor")
    try:
        sayAllModule.SayAllHandler.readText(sayAllModule.CURSOR.CARET)
    except Exception:
        logError("Say all could not be started")
        # Translators: Reported when continuous reading could not start.
        ui.message(_("Continuous reading is not available here"))


def lastPercent(treeInterceptor):
    return dLastPercent.get(id(treeInterceptor))
