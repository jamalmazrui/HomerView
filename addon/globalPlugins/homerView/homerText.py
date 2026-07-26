"""Reading the virtual buffer the way the Homer interface expects.

Every Homer query command needs one of a small number of text ranges: all of
the document, the rest of it from the cursor, the current selection, the current
line, or the chunk at the cursor. NVDA supplies all of these through TextInfo
objects on the tree interceptor, so this module is the one place that knows how
to ask for each, and the commands stay short.

A chunk is Homer's own unit and NVDA has no equivalent. It is a run of
non-blank characters, which is usually more than a word: word movement stops at
punctuation, so a url or a file path is several words but one chunk. That is
exactly the unit a reader wants when checking an address on a page.
"""

import textInfos

from .logger import homerLog

maximumSpokenCharacters = 100000


def allText(treeInterceptor):
    """Return the whole document as text."""
    info = treeInterceptor.makeTextInfo(textInfos.POSITION_ALL)
    return info.text or ""


def restText(treeInterceptor):
    """Return the text from the cursor to the end of the document."""
    infoCaret = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
    infoAll = treeInterceptor.makeTextInfo(textInfos.POSITION_ALL)
    infoRest = infoCaret.copy()
    infoRest.setEndPoint(infoAll, "endToEnd")
    return infoRest.text or ""


def selectedText(treeInterceptor):
    """Return the selected text, or an empty string when nothing is selected."""
    try:
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_SELECTION)
    except Exception:
        return ""
    return info.text or ""


def lineText(treeInterceptor):
    """Return the line at the cursor."""
    info = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
    info.expand(textInfos.UNIT_LINE)
    return info.text or ""


def chunkText(treeInterceptor):
    """Return the run of non-blank characters at the cursor.

    Homer's chunk is wider than a word because word movement stops at
    punctuation. A web address is one chunk and several words, and the chunk is
    what a reader actually wants to hear or copy.
    """
    sLine = lineText(treeInterceptor)
    if not sLine:
        return ""
    iOffset = 0
    try:
        infoCaret = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        infoLine = infoCaret.copy()
        infoLine.expand(textInfos.UNIT_LINE)
        infoStart = infoLine.copy()
        infoStart.setEndPoint(infoCaret, "endToStart")
        iOffset = len(infoStart.text or "")
    except Exception:
        iOffset = 0
    iOffset = max(0, min(iOffset, len(sLine) - 1))
    if sLine[iOffset].isspace():
        return ""
    iStart = iOffset
    while iStart > 0 and not sLine[iStart - 1].isspace():
        iStart -= 1
    iEnd = iOffset
    while iEnd < len(sLine) - 1 and not sLine[iEnd + 1].isspace():
        iEnd += 1
    return sLine[iStart:iEnd + 1]


def textOrAll(treeInterceptor):
    """Selected text when there is a selection, otherwise the whole document.

    This is the Homer convention for commands that act on a range: a selection
    means the user has already said what they meant, and its absence means all
    of it.
    """
    sSelected = selectedText(treeInterceptor)
    if sSelected:
        return sSelected, True
    return allText(treeInterceptor), False


def countYield(sText):
    """Return characters, words, and lines, as Homer's Yield command reports."""
    iCharacters = len(sText)
    iWords = len(sText.split())
    iLines = len(sText.splitlines()) or (1 if sText else 0)
    return iCharacters, iWords, iLines


def caretPosition(treeInterceptor):
    """Return line number, column, and percentage through the document."""
    try:
        infoAll = treeInterceptor.makeTextInfo(textInfos.POSITION_ALL)
        infoCaret = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        infoBefore = infoAll.copy()
        infoBefore.setEndPoint(infoCaret, "endToStart")
        sBefore = infoBefore.text or ""
        sAll = infoAll.text or ""
        iLine = sBefore.count("\n") + 1
        iColumn = len(sBefore) - (sBefore.rfind("\n") + 1) + 1
        iPercent = round(len(sBefore) * 100 / len(sAll)) if sAll else 0
        return iLine, iColumn, iPercent
    except Exception:
        homerLog.debug("Caret position could not be measured", exc_info=True)
        return 0, 0, 0


def moveToPercent(treeInterceptor, iPercent):
    """Move the browse cursor to a percentage point through the document."""
    infoAll = treeInterceptor.makeTextInfo(textInfos.POSITION_ALL)
    sAll = infoAll.text or ""
    if not sAll:
        return False
    iTarget = max(0, min(len(sAll) - 1, int(len(sAll) * iPercent / 100)))
    info = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
    info.move(textInfos.UNIT_CHARACTER, iTarget)
    info.updateCaret()
    info.expand(textInfos.UNIT_LINE)
    return info
