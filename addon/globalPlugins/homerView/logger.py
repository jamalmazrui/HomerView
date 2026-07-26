"""Extensive per-session logging for HomerView.

The log is rewritten from empty each time the add-on loads, which in practice
means once per NVDA session. The previous session's log is kept alongside it as
HomerView.previous.log, because an add-on defect that forces an NVDA restart
would otherwise destroy the very log needed to diagnose it.

The preferred location is C:\\HomerView\\HomerView.log, for ease of access during
development. That folder is created by an installer that requires administrator
rights, so a standard user may not be able to write there. When the preferred
folder cannot be written, the log falls back to the local application data
folder, and the header records which location was used.

Logging is deliberately verbose. Beyond ordinary tracing it records the raw
values behind decisions that are not yet settled, such as which NVDA property
carries a document address and which attribute identifies a main landmark, so
that the log can answer those questions from a real session.
"""

import logging
import os
import sys
from pathlib import Path

logFileName = "HomerView.log"
logFolderPreferred = r"C:\HomerView"
logLevel = logging.DEBUG
maximumPayloadCharacters = 1200
previousLogFileName = "HomerView.previous.log"

bUsingPreferredFolder = False
homerLog = logging.getLogger("homerView")
pathLogFile = None


def abbreviate(vValue, iMaximum=maximumPayloadCharacters):
    """Shorten a value for logging, noting the original length when cut."""
    sText = vValue if isinstance(vValue, str) else repr(vValue)
    if len(sText) <= iMaximum:
        return sText
    return f"{sText[:iMaximum]}... [{len(sText)} characters total]"


def chooseLogFolder():
    """Return the first writable candidate folder, or None."""
    global bUsingPreferredFolder
    lCandidates = [
        Path(logFolderPreferred),
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HomerView",
    ]
    for iIndex, pathCandidate in enumerate(lCandidates):
        try:
            pathCandidate.mkdir(parents=True, exist_ok=True)
            pathProbe = pathCandidate / logFileName
            with open(pathProbe, "a", encoding="utf-8"):
                pass
            bUsingPreferredFolder = iIndex == 0
            return pathCandidate
        except OSError:
            continue
    return None


def readAddonVersion():
    """Read the version from the add-on manifest beside this package."""
    try:
        pathManifest = Path(__file__).resolve().parents[2] / "manifest.ini"
        for sLine in pathManifest.read_text(encoding="utf-8-sig").splitlines():
            sLine = sLine.strip()
            if sLine.startswith("version"):
                return sLine.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "unknown"


def startSession(sAddonVersion=""):
    """Open a fresh log for this session and write the header block."""
    global pathLogFile
    pathFolder = chooseLogFolder()
    if not pathFolder:
        return None
    pathLogFile = pathFolder / logFileName
    sAddonVersion = sAddonVersion or readAddonVersion()
    pathPrevious = pathFolder / previousLogFileName
    try:
        if pathLogFile.exists():
            if pathPrevious.exists():
                pathPrevious.unlink()
            pathLogFile.replace(pathPrevious)
    except OSError:
        pass
    for handlerExisting in list(homerLog.handlers):
        try:
            handlerExisting.close()
        except Exception:
            pass
        homerLog.removeHandler(handlerExisting)
    handler = logging.FileHandler(pathLogFile, mode="w", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(threadName)-17s  %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    homerLog.addHandler(handler)
    homerLog.setLevel(logLevel)
    homerLog.propagate = False
    writeHeader(sAddonVersion)
    return pathLogFile


def writeHeader(sAddonVersion):
    logSection("Session started")
    homerLog.info(f"HomerView add-on version: {sAddonVersion}")
    homerLog.info(f"Log file: {pathLogFile}")
    if not bUsingPreferredFolder:
        homerLog.warning(
            f"{logFolderPreferred} could not be written, so the log fell back to the "
            "local application data folder. This usually means the installation "
            "folder belongs to an administrator."
        )
    try:
        import buildVersion

        homerLog.info(f"NVDA version: {buildVersion.version}")
        homerLog.info(f"NVDA API version: {buildVersion.version_year}.{buildVersion.version_major}")
    except Exception:
        homerLog.info("NVDA version: unavailable")
    homerLog.info(f"Python: {sys.version.splitlines()[0]}")
    homerLog.info(f"Executable: {sys.executable}")
    homerLog.info(f"Windows: {sys.getwindowsversion() if hasattr(sys, 'getwindowsversion') else 'unavailable'}")
    homerLog.info(f"Log level: {logging.getLevelName(logLevel)}")
    homerLog.info(f"Maximum logged payload: {maximumPayloadCharacters} characters")


def describeThread():
    """Return the current thread's name and whether it is NVDA's main thread."""
    import threading

    thread = threading.current_thread()
    bMain = thread is threading.main_thread()
    return thread.name, bMain


def logThreadContext(sWhere, bExpectMain=True):
    """Record which thread a step is running on, and complain if it is wrong.

    Speech, braille and dialogs must happen on NVDA's main thread, and anything
    touching the network must not. Recording the thread at each step turns a
    vague report of sluggishness into a specific line in the log.
    """
    sName, bMain = describeThread()
    if bExpectMain and not bMain:
        homerLog.warning(
            f"{sWhere} ran on {sName}, not NVDA's main thread. Speech and dialogs "
            "from here are unsafe."
        )
    elif not bExpectMain and bMain:
        homerLog.warning(
            f"{sWhere} ran on NVDA's main thread. Anything slow here will stall speech."
        )
    else:
        homerLog.debug(f"{sWhere} on {sName}")
    return bMain


def logSection(sTitle):
    homerLog.info("=" * 78)
    homerLog.info(sTitle)
    homerLog.info("=" * 78)


def logError(sMessage):
    """Record a failure with its traceback, and mirror it into NVDA's own log."""
    homerLog.exception(sMessage)
    try:
        from logHandler import log

        log.debugWarning(f"HomerView: {sMessage}", exc_info=True)
    except Exception:
        pass


def stopSession():
    logSection("Session ended")
    for handlerExisting in list(homerLog.handlers):
        try:
            handlerExisting.close()
        except Exception:
            pass
        homerLog.removeHandler(handlerExisting)


# The session opens as soon as this module is first imported, which happens
# before any other HomerView module can log anything.
startSession()
