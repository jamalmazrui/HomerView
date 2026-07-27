"""Choosing among HomerView's own tabs, and closing the ones you are done with.

Homer puts a pick list of the program's windows on F4, and the same idea serves
here: a reader who has run a report, extracted an article and opened a document
has four tabs and no easy way to say which is which. Control+Tab cycles blind,
and the browser's own tab list is a strip of buttons rather than a list.

Only HomerView's own tabs are offered. A page target belonging to another
process is not ours to switch to or close.

Closing keeps the tab being read, and only that one. Keeping it is enough: the
browser exits when its last tab closes, so one surviving tab keeps the process,
the debugging port and every HomerView command alive. Pressing NVDA+Alt+H again
is never needed.

An earlier version also kept the oldest tab, on the reasoning that it was a
safer margin. It was not worth it. The command says it closes everything but
the current tab, and a command that quietly leaves an extra window behind is
worse than one that does what it says.

The one case still guarded is no tab reporting itself as current, which can
happen for a moment after a page loads. Then the oldest is kept instead, since
closing everything on a guess would end the session.
"""

import addonHandler

from .logger import abbreviate, homerLog, logSection

addonHandler.initTranslation()


def listPageTargets(cdpSession):
    """Return the browser's own page tabs, oldest first.

    The protocol lists targets in creation order, which is what makes the first
    one the tab the browser opened with.
    """
    dResult = cdpSession.call("Target.getTargets")
    lTargets = [
        dTarget for dTarget in (dResult.get("targetInfos") or [])
        if dTarget.get("type") == "page"
        and not str(dTarget.get("url", "")).startswith(("devtools://", "edge://"))
    ]
    homerLog.info(f"HomerView has {len(lTargets)} page tabs open")
    return lTargets


def describeTarget(dTarget, bCurrent=False):
    """A line naming one tab, as a reader would want to hear it."""
    sTitle = str(dTarget.get("title", "")).strip()
    sUrl = str(dTarget.get("url", "")).strip()
    if not sTitle:
        sTitle = sUrl or _("untitled")
    # The address is worth having when two tabs share a title, which happens
    # with generated reports, but not when it merely repeats the title.
    if sUrl and sUrl not in sTitle and not sUrl.startswith("file:"):
        from urllib.parse import urlparse

        sHost = urlparse(sUrl).netloc
        if sHost and sHost not in sTitle:
            sTitle = f"{sTitle} ({sHost})"
    return _("{title}, current") .format(title=sTitle) if bCurrent else sTitle


def gatherTabs(cdpSession):
    """Every HomerView tab, with the current one marked."""
    logSection("Command: list the tabs")
    lTargets = listPageTargets(cdpSession)
    sCurrentId = ""
    try:
        dCurrent, _sSessionId = cdpSession.findActivePageSession()
        sCurrentId = dCurrent.get("targetId", "")
    except Exception:
        homerLog.debug("No tab reported itself as focused")
    lTabs = []
    for iIndex, dTarget in enumerate(lTargets):
        bCurrent = dTarget.get("targetId") == sCurrentId
        lTabs.append({
            "current": bCurrent,
            "index": iIndex,
            "label": describeTarget(dTarget, bCurrent),
            "targetId": dTarget.get("targetId", ""),
            "title": str(dTarget.get("title", "")),
            "url": str(dTarget.get("url", "")),
        })
        homerLog.debug(f"  tab {iIndex}: {abbreviate(lTabs[-1]['label'], 120)}")
    return {"current": sCurrentId, "tabs": lTabs}


def activateTab(cdpSession, sTargetId):
    logSection("Command: activate a tab")
    cdpSession.call("Target.activateTarget", {"targetId": sTargetId})
    homerLog.info(f"Activated tab {sTargetId}")
    return True


def closeOtherTabs(cdpSession):
    """Close every tab but the one being read.

    One surviving tab is all the browser needs to stay running, so full
    HomerView function is preserved and NVDA+Alt+H is not needed again.
    """
    logSection("Command: close the other tabs")
    dGathered = gatherTabs(cdpSession)
    lTabs = dGathered["tabs"]
    if len(lTabs) <= 1:
        homerLog.info("Only one tab is open, so nothing was closed")
        return {"closed": 0, "kept": len(lTabs), "reason": "only one tab"}

    setKeep = set()
    for dTab in lTabs:
        if dTab["current"]:
            setKeep.add(dTab["targetId"])
    if not setKeep:
        # Nothing reported itself as current, so the oldest stands in. Closing
        # everything on a guess would end the session.
        setKeep.add(lTabs[0]["targetId"])
        homerLog.warning("No tab reported itself as current, so the oldest is kept instead")

    iClosed = 0
    for dTab in lTabs:
        if dTab["targetId"] in setKeep:
            continue
        try:
            cdpSession.call("Target.closeTarget", {"targetId": dTab["targetId"]})
            iClosed += 1
            homerLog.info(f"Closed {abbreviate(dTab['label'], 100)}")
        except Exception as exception:
            homerLog.warning(f"A tab could not be closed: {exception}")
    homerLog.info(f"Closed {iClosed} tabs, kept {len(setKeep)}")
    return {"closed": iClosed, "kept": len(setKeep), "reason": ""}
