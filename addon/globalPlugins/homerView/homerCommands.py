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
import controlTypes
import textInfos
import ui
from scriptHandler import getLastScriptRepeatCount

from . import clipboardTools
from . import homerText
from . import linkTarget
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

    from . import settings

    if settings.getFlag("speakCommandLabels",
                        getattr(pageBuffer, "bSpeakCommandLabels", False)) and sLabel:
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


def sayYieldPattern(treeInterceptor):
    """Count how often a regular expression matches, as EdSharp's Yield does.

    Plain Yield answers how much text there is. This answers how much of a
    particular thing there is, which is the question a reader actually has when
    they want to know whether a page is worth reading: how many times is this
    name mentioned, how many dollar amounts are there, how many dates.

    Counting is not searching. Control+F3 moves to the next match one at a
    time, which answers "where is it"; this answers "how many", and on a long
    page those are different questions with different keys.

    The pattern is shared with the search commands, so a pattern just used to
    search can be counted without retyping it, and the other way round.
    """
    lbc.afterScript(_sayYieldPatternNow, treeInterceptor)


def _sayYieldPatternNow(treeInterceptor):
    import re as reModule

    from . import output
    from . import settings

    sText, bSelected = homerText.textOrAll(treeInterceptor)
    if not sText:
        # Translators: Reported when there is no text to count in.
        ui.message(_("There is no text here"))
        return

    sPrevious = find.restorePattern()
    sPattern = lbc.dialogInput(
        # Translators: Title of the dialog counting pattern matches.
        _("Yield with pattern"),
        # Translators: Label of the field for a regular expression to count.
        _("&Regular expression to count:"),
        sPrevious,
    )
    if sPattern is None or not sPattern.strip():
        homerLog.info("Yield with pattern cancelled")
        return

    try:
        expression = reModule.compile(sPattern, reModule.IGNORECASE | reModule.MULTILINE)
    except reModule.error as exception:
        homerLog.warning(f"The pattern would not compile: {exception}")
        lbc.dialogInfo(
            # Translators: Title of the message about a bad pattern.
            _("Yield with pattern"),
            # Translators: Shown when a regular expression is not valid.
            _("That is not a valid regular expression.\n\n{reason}").format(reason=exception))
        return

    find.dLastFind["pattern"] = sPattern
    find.rememberPattern()
    settings.setRecent("findPattern", sPattern)

    lMatches = list(expression.finditer(sText))
    # The lines a match falls on, so a reader learns whether ten matches are
    # spread through the page or crowded into one paragraph.
    setLines = set()
    for match in lMatches:
        setLines.add(sText.count("\n", 0, match.start()) + 1)
    lSamples = []
    for match in lMatches[:5]:
        sSample = " ".join((match.group(0) or "").split())
        if sSample:
            lSamples.append(sSample[:80])

    homerLog.info(
        f"Yield with pattern {abbreviate(sPattern, 80)}: {len(lMatches)} matches "
        f"on {len(setLines)} lines, selected={bSelected}")

    lLines = [
        # Translators: First line of the pattern yield. The placeholder is the
        # expression that was counted.
        _("Pattern: {pattern}").format(pattern=sPattern),
        _("In the selection") if bSelected else _("In the whole page"),
        "",
    ]
    if not lMatches:
        # Translators: Shown when a pattern matched nothing.
        lLines.append(_("No matches."))
    else:
        # Translators: How many times a pattern matched.
        lLines.append(_("{count} matches").format(count=len(lMatches)))
        # Translators: How many lines the matches fall on.
        lLines.append(_("on {count} lines").format(count=len(setLines)))
        if lSamples:
            lLines.append("")
            # Translators: Heading above example matches.
            lLines.append(_("First matches:"))
            for sSample in lSamples:
                lLines.append("  " + sSample)
            if len(lMatches) > len(lSamples):
                # Translators: Shown when more matched than are listed.
                lLines.append(_("  and {count} more").format(
                    count=len(lMatches) - len(lSamples)))
    output.lines(_("Yield with pattern"), lLines)


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


def describeLinkTarget(treeInterceptor):
    """Ask where the link at the cursor goes, and what is there.

    Alt+U gives the address, which is what a sighted reader sees on hover. This
    is what they work out from it: whether it is a page or a file, how big,
    whether it still exists, whether it ends up somewhere other than it claims,
    and for a page, what it is about and how long.
    """
    from .service import service

    obj = linkAtCursor(treeInterceptor)
    sUrl = (getattr(obj, "value", "") or "") if obj else ""
    if not sUrl:
        # Translators: Reported when the cursor is not on a link.
        ui.message(_("No link here"))
        return
    if not sUrl.lower().startswith("http"):
        # Translators: Reported for a link that does not go to a web address.
        ui.message(_("That link does not go to a web address"))
        return
    sText = ""
    try:
        sText = (getattr(obj, "name", "") or "").strip()
    except Exception:
        sText = ""
    homerLog.info(f"Describing the target of {abbreviate(sUrl, 200)}")
    # Translators: Reported while a link target is asked about.
    ui.message(_("Asking where that goes"))
    # On the worker, because this is a network request and NVDA speaks from the
    # main thread.
    service.submit(
        "describeLinkTarget",
        lambda: {"lines": linkTarget.describeLink(sUrl, sText), "url": sUrl},
        _showLinkTarget,
        lambda exception: ui.message(str(exception)))


def _showLinkTarget(dResult):
    from . import output

    # Translators: Title of the box describing where a link goes.
    output.lines(_("Where that link goes"), dResult.get("lines") or [])


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


# Which kind of search was used last, and which way it ran. Held here rather
# than on the buffer, because the buffer is replaced whenever a page reloads
# and a reader does not expect a reload to forget what they were looking for.
dLastFind = {"backwards": False, "kind": ""}


def rememberFindKind(sKind, bBackwards):
    dLastFind["backwards"] = bool(bBackwards)
    dLastFind["kind"] = sKind
    homerLog.debug(f"Last search: {sKind}, {'backwards' if bBackwards else 'forwards'}")


def lastFindKind():
    """Return the kind of the last search and its direction.

    Defaults to NVDA's, because that is the one a reader reaches for first and
    the one F3 should repeat if somehow neither has run.
    """
    return dLastFind.get("kind") or "nvda", bool(dLastFind.get("backwards"))


def repeatFind(treeInterceptor, bBackwards):
    """Repeat the last regular expression search."""
    find.repeatFind(treeInterceptor, bBackwards)


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
    confused.

    Two ways of guessing, in order. The browser is asked first, because it can
    weigh every part of the page against every other: the element with the most
    text and the fewest links is what an article looks like and what navigation
    does not. If that answers, its opening words are found in NVDA's own buffer
    and the cursor goes there.

    The old rule follows when it does not: the first heading past the banner
    and navigation, then the first heading at all. That was right often enough
    to be useful and wrong in the two places it mattered most, on a page whose
    article opens with a paragraph rather than a heading, and on a page whose
    navigation has headings of its own.

    Whichever answers, the reader is told which, so being taken somewhere
    inferred is never mistaken for being taken somewhere declared.
    """
    from .service import service

    if service.isConnected():
        # Translators: Reported while the main content is looked for.
        ui.message(_("Looking for the main content"))
        service.submit(
            "findMainContent", service.taskFindMainContent,
            lambda dFound: _proxyByScoring(treeInterceptor, dFound, gesture),
            lambda exception: _proxyByHeading(treeInterceptor, gesture))
        return
    _proxyByHeading(treeInterceptor, gesture)


def _proxyByScoring(treeInterceptor, dFound, gesture=None):
    """Move to the opening words the browser reported, using NVDA's own search.

    Text is the bridge. Chromium can name the DOM node holding the main
    content, and NVDA's buffer has no notion of a DOM node, so mapping one to
    the other would mean maintaining a correspondence that breaks whenever the
    page changes. The opening words exist on both sides already.
    """
    sOpening = (dFound or {}).get("opening", "")
    if not sOpening:
        homerLog.info("The browser found nothing to score, so the heading rule runs")
        _proxyByHeading(treeInterceptor, gesture)
        return
    homerLog.info(f"Looking in the buffer for {abbreviate(sOpening, 120)}")
    try:
        infoStart = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        # Progressively shorter, because the buffer's punctuation and the
        # page's need not agree and the first few words are enough to be
        # unique on almost any page.
        lWords = sOpening.split()
        for iCount in (len(lWords), 8, 5, 3):
            if iCount > len(lWords):
                continue
            sNeedle = " ".join(lWords[:iCount])
            info = infoStart.copy()
            if info.find(sNeedle, caseSensitive=False):
                info.updateCaret()
                info.collapse()
                info.expand(textInfos.UNIT_LINE)
                homerLog.info(
                    f"Moved to the main content, matched on {iCount} words "
                    f"({dFound.get('how')}, {dFound.get('tag', '')})")
                # Translators: Reported when the main content was inferred by
                # weighing the page rather than declared by it.
                ui.message(_("Main content, by weighing the page"))
                speech.speakTextInfo(info, reason=controlTypes.OutputReason.CARET)
                return
    except Exception:
        logError("The opening words could not be found in the buffer")
    homerLog.info("The opening words were not in the buffer, so the heading rule runs")
    _proxyByHeading(treeInterceptor, gesture)


def _proxyByHeading(treeInterceptor, gesture=None):
    """The older rule, kept as the fallback.

    The first heading inside an article, then the first heading after the
    banner and navigation, then the first heading at all. Used when the browser
    cannot be asked, or when what it reported could not be found in the buffer.

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

    from .service import service

    # Translators: Reported while the version check runs.
    ui.message(_("Checking for a newer version"))
    # On the worker, not here. wx.CallAfter defers the call, but it defers it
    # onto the main thread, which is the one NVDA speaks from; a slow or
    # unreachable server would hold speech for as long as the request took.
    # The dialogs that follow are put back on the main thread, which is where
    # they belong.
    service.submit(
        "checkForUpdate", elevate.checkForUpdate, _elevateChecked,
        lambda exception: lbc.dialogInfo(_("Elevate version"), str(exception)))


def _elevateChecked(dCheck):
    from . import elevate
    from . import lbc

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

    from .service import service

    # Translators: Reported while the add-on downloads.
    ui.message(_("Downloading"))
    # Also on the worker. This one matters more: it is a file of some size over
    # a connection that may be slow.
    service.submit(
        "installAddon", elevate.installAddon, _elevateInstalled,
        lambda exception: lbc.dialogInfo(
            _("Elevate version"),
            _("The download failed.\n\n{reason}\n\nYou can download it directly from "
              "{url}").format(reason=exception, url=elevate.latestPageUrl)))


def _elevateInstalled(dResult):
    from . import elevate
    from . import lbc

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


# NVDA can move to every kind of thing JAWS can, with two exceptions. JAWS has
# S for the next element of the same kind as the one you are on, and D for the
# next element of a different kind. Neither depends on knowing what kind you are
# on, which is what makes them useful: on a page of unfamiliar shape they let a
# reader move by structure without first working out what the structure is.
#
# Everything else JAWS reaches, NVDA reaches, sometimes under another name. Its
# divider is NVDA's separator on S; its edit box is NVDA's edit field on E; its
# main region has no NVDA key, which is why HomerView added J and Shift+J.
lNodeTypes = [
    "heading", "link", "landmark", "table", "list", "listItem", "graphic",
    "button", "formField", "edit", "checkBox", "radioButton", "comboBox",
    "blockQuote", "separator", "frame", "embeddedObject",
]


def typeAtCursor(treeInterceptor):
    """Say which kind of thing the cursor is on, if any.

    Asked by looking for the nearest preceding node of each kind and taking
    whichever starts latest, because NVDA offers no direct answer and this is
    the reading that matches what a user would call "the thing I am on".
    """
    try:
        infoCaret = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
    except Exception:
        return ""
    sBest, iBest = "", -1
    for sType in lNodeTypes:
        try:
            for item in treeInterceptor._iterNodesByType(sType, "previous", infoCaret):
                iStart = getattr(getattr(item, "textInfo", None), "_startOffset", None)
                if iStart is None:
                    sBest = sBest or sType
                else:
                    if iStart > iBest:
                        iBest, sBest = iStart, sType
                break
        except Exception:
            continue
    return sBest


def moveByTypeRelation(treeInterceptor, bSame, bForward):
    """Move to the next thing of the same kind as this one, or a different kind.

    With nothing identifiable at the cursor, the same-kind command has no
    question to answer and says so rather than guessing.
    """
    sCurrent = typeAtCursor(treeInterceptor)
    homerLog.info(f"Type at the cursor: {sCurrent or 'nothing identifiable'}")
    if bSame and not sCurrent:
        # Translators: Reported when the cursor is not on a recognisable element.
        ui.message(_("Not on anything to match"))
        return
    sDirection = "next" if bForward else "previous"
    try:
        infoCaret = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
    except Exception:
        return
    lCandidates = []
    for sType in lNodeTypes:
        if bSame and sType != sCurrent:
            continue
        if not bSame and sType == sCurrent:
            continue
        try:
            for item in treeInterceptor._iterNodesByType(sType, sDirection, infoCaret):
                lCandidates.append((item, sType))
                break
        except Exception:
            continue
    if not lCandidates:
        # Translators: Reported when no matching element was found.
        ui.message(_("No more of the same kind") if bSame else _("No other kind of element"))
        return
    # The nearest one in the direction of travel, which is what "next" means.
    def sortKey(tCandidate):
        iOffset = getattr(getattr(tCandidate[0], "textInfo", None), "_startOffset", 0) or 0
        return iOffset if bForward else -iOffset
    lCandidates.sort(key=sortKey)
    item, sType = lCandidates[0]
    homerLog.info(f"Moving to the {sDirection} {sType}")
    from . import pageBuffer

    pageBuffer.reportQuickNavItem(item, None)


def webUtilities():
    """Offer the web lookups, ask for what the chosen one needs, and run it."""
    from . import lbc

    lbc.afterScript(_webUtilitiesNow)


def _webUtilitiesNow():
    from . import lbc
    from . import settings
    from . import webUtilities
    from .service import service
    import wx

    lLabels = [sName for sName, _lFields, _f in webUtilities.lUtilities]
    sPrevious = settings.getRecent("webUtility", "")
    iStart = lLabels.index(sPrevious) if sPrevious in lLabels else 0
    sChoice = lbc.dialogChoose(
        # Translators: Title of the web utilities dialog.
        _("Look something up"),
        # Translators: Prompt above the list of web lookups.
        _("These use free services that need no account. Control+J searches this list."),
        lLabels, iStart)
    if not sChoice:
        homerLog.info("Web utility cancelled")
        return
    settings.setRecent("webUtility", sChoice)
    iIndex = lLabels.index(sChoice)
    sName, lFields, _functionLookup = webUtilities.lUtilities[iIndex]

    # A dialog built from what the lookup actually asks for, one field each,
    # rather than one box the user has to pack several values into.
    dialog = lbc.Dialog(sTitle=sName)
    for sField, sLabel, sDefault, lLookup in lFields:
        sRemembered = settings.getRecent(f"web.{iIndex}.{sField}", sDefault)
        dialog.addInputBox(
            sLabel, sRemembered, sName=sField,
            sTip=_("F4 offers the usual values") if lLookup else "",
            lLookup=lLookup)
        dialog.addBand()
    dResults = dialog.complete(["OK", "Cancel"], 0)
    if dResults.get("result") != wx.ID_OK:
        homerLog.info("Web utility cancelled at the fields")
        return

    dValues = {}
    for sField, _sLabel, _sDefault, _lLookup in lFields:
        sValue = str(dResults.get(sField, "")).strip()
        dValues[sField] = sValue
        settings.setRecent(f"web.{iIndex}.{sField}", sValue)
    if lFields and not dValues.get(lFields[0][0]):
        # Translators: Reported when the first field of a lookup was left empty.
        ui.message(_("Nothing was entered to look up"))
        return

    # Translators: Reported while a web lookup runs.
    ui.message(_("Looking that up"))
    service.submit(
        "webUtility",
        lambda: webUtilities.runUtility(iIndex, dValues),
        showWebUtilityResult,
        lambda exception: ui.message(str(exception)))


def showWebUtilityResult(dResult):
    """Short answers to a box, longer ones to a page with real structure."""
    from . import output

    lSections = dResult.get("sections") or []
    iLines = sum(len(lLines) for _sHeading, lLines in lSections)
    sName = dResult.get("name", "")

    # A message box can be read at a glance and copied whole with Control+C,
    # which suits a definition or an exchange rate. Beyond about a screenful it
    # stops being readable that way, and a page is better: it has headings to
    # move by, it can be searched with Control+F, and it can be saved.
    if iLines <= 14 and len(lSections) <= 1:
        output.lines(sName, lSections[0][1] if lSections else [])
        return

    import html as htmlModule

    lParts = [f"<h1>{htmlModule.escape(sName)}</h1>"]
    dValues = dResult.get("values") or {}
    if dValues:
        lParts.append("<p>" + htmlModule.escape(
            ", ".join(f"{k}: {v}" for k, v in dValues.items() if v)) + "</p>")
    for sHeading, lLines in lSections:
        if sHeading:
            lParts.append(f"<h2>{htmlModule.escape(sHeading)}</h2>")
        # Blank lines separate one result from the next, so each becomes an
        # item rather than the whole thing becoming one long list.
        lItem = []
        lParts.append("<ul>")
        for sLine in lLines:
            if str(sLine).strip():
                lItem.append(htmlModule.escape(str(sLine)))
            elif lItem:
                lParts.append("<li>" + "<br>".join(lItem) + "</li>")
                lItem = []
        if lItem:
            lParts.append("<li>" + "<br>".join(lItem) + "</li>")
        lParts.append("</ul>")
    output.show("\n".join(lParts), sName, sName)


def chooseTab():
    """Offer the HomerView tabs and switch to whichever is chosen."""
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    service.submit("gatherTabs", service.taskGatherTabs, _offerTabs,
                   lambda exception: ui.message(str(exception)))


def _offerTabs(dGathered):
    from . import lbc

    lTabs = dGathered.get("tabs") or []
    if not lTabs:
        # Translators: Reported when no HomerView tabs were found.
        ui.message(_("No HomerView tabs are open"))
        return
    if len(lTabs) == 1:
        # Translators: Reported when only one tab is open. The placeholder is
        # the name of that tab.
        ui.message(_("Only one tab: {name}").format(name=lTabs[0]["title"] or lTabs[0]["url"]))
        return
    lbc.afterScript(_pickTab, lTabs)


def _pickTab(lTabs):
    from . import lbc
    from .service import service

    iStart = next((i for i, d in enumerate(lTabs) if d["current"]), 0)
    sChoice = lbc.dialogChoose(
        # Translators: Title of the dialog listing HomerView tabs.
        _("HomerView tabs"),
        # Translators: Prompt above the list of tabs. The placeholder is a count.
        _("{count} tabs. Choose one to switch to it.").format(count=len(lTabs)),
        [d["label"] for d in lTabs], iStart)
    if not sChoice:
        homerLog.info("Tab list cancelled")
        return
    for dTab in lTabs:
        if dTab["label"] == sChoice:
            service.submit(
                "activateTab", service.makeActivateTabTask(dTab["targetId"]),
                lambda vResult: None, lambda exception: ui.message(str(exception)))
            return


def sayTabs():
    """Say the names of the open tabs, without opening anything."""
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    service.submit("gatherTabs", service.taskGatherTabs, _speakTabs,
                   lambda exception: ui.message(str(exception)))


def _speakTabs(dGathered):
    """Say the titles, leaving the keyboard where it is.

    Deliberately spoken rather than shown in a box. A box would take focus and
    need dismissing, and the question this answers is only what is open; the
    reader is in the middle of something and wants to stay there. F4 is the
    command for when they want to act on the answer.
    """
    lTabs = dGathered.get("tabs") or []
    if not lTabs:
        # Translators: Reported when no HomerView tabs are open.
        ui.message(_("No HomerView tabs are open"))
        return
    homerLog.info(f"Saying {len(lTabs)} tab titles")
    # Translators: Spoken before the list of tab titles. The placeholder is a count.
    ui.message(_("{count} tabs").format(count=len(lTabs)))
    for dTab in lTabs:
        speech.speakText(dTab["label"])


def closeOtherTabs():
    """Close every tab but the current one and the one the browser opened with."""
    from .service import service

    if not service.isConnected():
        # Translators: Reported when HomerView has no connection.
        ui.message(_("HomerView is not connected"))
        return
    service.submit("closeOtherTabs", service.taskCloseOtherTabs, _reportClosed,
                   lambda exception: ui.message(str(exception)))


def _reportClosed(dResult):
    iClosed = dResult.get("closed", 0)
    if not iClosed:
        # Translators: Reported when there was nothing to close.
        ui.message(_("Nothing to close"))
        return
    # Translators: Reported after closing tabs. The placeholder is a count.
    ui.message(_("Closed {count} tabs").format(count=iClosed))


def lastPercent(treeInterceptor):
    return dLastPercent.get(id(treeInterceptor))
