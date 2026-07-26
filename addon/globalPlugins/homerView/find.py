"""Finding text in a page, plainly or by regular expression.

EdSharp's model is followed exactly: a find command asks for the pattern, and
F3 or Shift+F3 afterwards repeats whatever the last find was, regular or
regular expression, forwards or backwards. The user does not have to remember
which kind of search they started.

Python's re module does the work. The alternative, VBScript's RegExp through
COM, would mean a COM round trip per search and a dialect nobody writes any
more; re is in the standard library, is faster, and is the dialect people
actually know.

Searching happens over the browse mode buffer's own text rather than over the
page markup, so a match is a place the browse cursor can be put. Matching the
markup would find things the reader cannot reach.
"""

import re

import addonHandler
import textInfos
import ui

from .logger import abbreviate, homerLog, logSection

addonHandler.initTranslation()

maximumReportedMatch = 120

dLastFind = {
    "pattern": "",
    "regex": False,
    "caseSensitive": False,
}


def buildPattern(sPattern, bRegex, bCaseSensitive):
    """Return a compiled pattern, or raise re.error with a usable message."""
    iFlags = 0 if bCaseSensitive else re.IGNORECASE
    if not bRegex:
        sPattern = re.escape(sPattern)
    return re.compile(sPattern, iFlags)


def findInBuffer(treeInterceptor, sPattern, bRegex, bBackwards, bCaseSensitive=False):
    """Move the browse cursor to the next or previous match.

    NVDA's own quick navigation leaves the cursor alone when it finds nothing,
    and so does this. A search that silently moves you somewhere unrelated is
    worse than one that says it found nothing.
    """
    logSection(f"Command: find {'backwards ' if bBackwards else ''}{'by pattern' if bRegex else ''}")
    try:
        pattern = buildPattern(sPattern, bRegex, bCaseSensitive)
    except re.error as exception:
        homerLog.warning(f"Bad pattern {abbreviate(sPattern, 120)}: {exception}")
        # Translators: Reported when a regular expression cannot be understood.
        ui.message(_("That pattern is not valid: {reason}").format(reason=exception))
        return False

    infoAll = treeInterceptor.makeTextInfo(textInfos.POSITION_ALL)
    sAll = infoAll.text or ""
    if not sAll:
        # Translators: Reported when the page has no text.
        ui.message(_("The page is empty"))
        return False

    iCaret = 0
    try:
        infoCaret = treeInterceptor.makeTextInfo(textInfos.POSITION_CARET)
        infoBefore = infoAll.copy()
        infoBefore.setEndPoint(infoCaret, "endToStart")
        iCaret = len(infoBefore.text or "")
    except Exception:
        iCaret = 0

    match = None
    if bBackwards:
        for candidate in pattern.finditer(sAll):
            if candidate.start() >= iCaret:
                break
            match = candidate
        if not match:
            # Wrap to the end, which is what every editor does.
            lAll = list(pattern.finditer(sAll))
            match = lAll[-1] if lAll else None
            if match:
                homerLog.info("Search wrapped to the end of the page")
    else:
        match = pattern.search(sAll, iCaret + 1)
        if not match:
            match = pattern.search(sAll)
            if match:
                homerLog.info("Search wrapped to the start of the page")

    if not match:
        homerLog.info(f"No match for {abbreviate(sPattern, 120)}")
        # Translators: Reported when a search finds nothing.
        ui.message(_("Not found"))
        return False

    dLastFind.update(
        {"pattern": sPattern, "regex": bRegex, "caseSensitive": bCaseSensitive}
    )
    try:
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        info.move(textInfos.UNIT_CHARACTER, match.start())
        info.updateCaret()
        infoLine = info.copy()
        infoLine.expand(textInfos.UNIT_LINE)
        homerLog.info(
            f"Matched at character {match.start()}: {abbreviate(match.group(0), 120)}"
        )
        ui.message(infoLine.text or match.group(0)[:maximumReportedMatch])
        return True
    except Exception:
        homerLog.exception("The cursor could not be moved to the match")
        # Translators: Reported when a match was found but could not be reached.
        ui.message(_("Found, but the cursor could not be moved there"))
        return False


def repeatFind(treeInterceptor, bBackwards):
    """Repeat the last search, whichever kind it was."""
    if not dLastFind.get("pattern"):
        # Translators: Reported when there is no earlier search to repeat.
        ui.message(_("Press Control+F3 first to search"))
        return False
    return findInBuffer(
        treeInterceptor,
        dLastFind["pattern"],
        dLastFind["regex"],
        bBackwards,
        dLastFind["caseSensitive"],
    )


def describeLastFind():
    if not dLastFind.get("pattern"):
        return ""
    sKind = "pattern" if dLastFind["regex"] else "text"
    return f"{sKind}: {dLastFind['pattern']}"
