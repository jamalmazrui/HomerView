"""Whose window is this? The one place HomerView decides, for every surface.

Before 18 October 2026 the answer was decided in two places that could
disagree. service.isHomerViewObject refused anything whose program was not
named msedge before it looked at a process id, so a page in HomerView's Chrome
was never recognized. __init__._focusIsHomerViewEdge compared process ids, but
fell back to the chosen browser's program NAME when none were known, so an
ordinary window of that browser could be taken for HomerView's. Both now ask
this module, which has three rules:

1. PROCESS IDENTITY DECIDES. A window is HomerView's when its process is one
   of the processes of the browser HomerView launched or attached to. The
   program's name never decides it: Chrome and Chromium share chrome.exe, and
   an ordinary Edge window is msedge.exe like HomerView's.

2. UNKNOWN IS NOT MINE. With no process known -- before launch, after the
   browser closed -- nothing is HomerView's, and every key keeps its normal
   browser and screen-reader meaning. Connect or Launch is offered by command,
   never by guessing.

3. ELIGIBLE IS NOT CONNECTED. Being a browser HomerView may be active in only
   makes a window worth probing for a connection. It authorizes no command.

A request that waits in the queue carries a TargetStamp: the session, window,
page and document generation it was made for. Before it acts, the stamp is
compared with what is current; a stale request is cancelled with a reason
instead of acting on a different page. (The stamp is defined and tested here;
the queue adopts it in stage 5 of the suite plan.)

This module imports nothing from NVDA, so scripts\\testIdentity.py can test
every rule on any machine, and the build does, every time.
"""

import os


def isManagedProcess(iProcessId, setProcessIds):
    """Rule 1 and rule 2: a known process of HomerView's browser, or not."""
    try:
        return bool(iProcessId) and bool(setProcessIds) and int(iProcessId) in setProcessIds
    except (TypeError, ValueError):
        return False


def isManagedObject(oObject, setProcessIds):
    """A document or control NVDA built: HomerView's when its process is."""
    return isManagedProcess(getattr(oObject, "processID", 0), setProcessIds)


def keyBelongsToHomerView(iFocusProcessId, setProcessIds):
    """Whether a browser key goes to HomerView. Same rule; no name fallback."""
    return isManagedProcess(iFocusProcessId, setProcessIds)


def appNameFromPath(sPath):
    """The program name NVDA gives a process: the file name, no extension, lower case."""
    if not sPath:
        return ""
    # Split on either slash, so a Windows path is read the same on any
    # machine the tests run on.
    sFile = sPath.replace("/", "\\").split("\\")[-1]
    return os.path.splitext(sFile)[0].lower()


def isEligibleApp(sFocusAppName, lsEligiblePaths):
    """Rule 3: worth probing for a connection; authorizes nothing."""
    sName = (sFocusAppName or "").lower()
    return bool(sName) and any(appNameFromPath(sPath) == sName for sPath in (lsEligiblePaths or []))


class TargetStamp:
    """What a queued request was made for. Compared again before it acts."""

    def __init__(self, sSessionId, iWindowHandle, sTargetId, iDocumentGeneration):
        self.sSessionId = sSessionId or ""
        self.iWindowHandle = iWindowHandle or 0
        self.sTargetId = sTargetId or ""
        self.iDocumentGeneration = iDocumentGeneration or 0

    def staleReason(self, oCurrent):
        """"" when the request may act; otherwise the reason it must not."""
        if oCurrent is None or not oCurrent.sSessionId:
            return "the browser is no longer connected"
        if oCurrent.sSessionId != self.sSessionId:
            return "the browser connection changed"
        if oCurrent.sTargetId != self.sTargetId:
            return "a different tab is in front now"
        if oCurrent.iDocumentGeneration != self.iDocumentGeneration:
            return "the page has changed since you asked"
        if self.iWindowHandle and oCurrent.iWindowHandle and oCurrent.iWindowHandle != self.iWindowHandle:
            return "a different window is in front now"
        return ""
