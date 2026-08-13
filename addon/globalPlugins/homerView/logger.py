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
# The log lives with the user's local application data, not in the program
# folder. A program folder is written once by an installer with administrator
# rights and read thereafter; a program that writes there at run time either
# demands administrator rights forever or has its writes redirected somewhere
# the user cannot find. Windows has been moving away from that redirection for
# years, and the folder is per-machine anyway, so two users of one computer
# would share a log.
#
# Local rather than roaming, because a log is specific to this machine and can
# grow. A roaming profile is copied at every sign in and sign out, and putting
# a log in it makes that slower for no benefit.
logFolderName = "HomerView"
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
        Path(os.environ.get("LOCALAPPDATA", "")) / logFolderName if os.environ.get("LOCALAPPDATA") else None,
        Path.home() / logFolderName,
    ]
    lCandidates = [p for p in lCandidates if p]
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


bAppendWithinTheHour = True
maximumAppendMinutes = 60


def shouldAppend(pathLogFile):
    """Continue the existing log when this looks like the same sitting.

    Restarting NVDA to install a build, or reconnecting to a browser left
    running, is a continuation of what the user was doing rather than a new
    session. Splitting the log there loses the context that makes the second
    half readable. An hour is a generous line between one sitting and the next.
    """
    import time as timeModule

    if not bAppendWithinTheHour:
        return False
    try:
        nAge = (timeModule.time() - pathLogFile.stat().st_mtime) / 60
    except OSError:
        return False
    return nAge <= maximumAppendMinutes


def flushLog():
    """Push everything buffered to disk, so a copy of the log is complete.

    Without this, the last few lines are still in the handler's buffer and the
    copy someone opens is missing exactly the lines they wanted to read.
    """
    for handler in list(homerLog.handlers):
        try:
            handler.flush()
        except Exception:
            pass


def buildRedactions():
    """The strings to take out of the log, longest first.

    A log is only worth sharing if sharing it is safe, and the thing that makes
    it unsafe is not anything HomerView chooses to write: it is the user's own
    name, which Windows puts in the middle of every path. C:\\Users\\Someone
    appears dozens of times in an ordinary session without anybody deciding it
    should.

    So the name is replaced with the variable that stands for it. The log still
    says where a file was, which is what a reader needs, without saying whose
    computer it was on.

    Longest first, because the profile path contains the user name, and
    replacing the shorter one first would leave the longer one half done.
    """
    import os

    lPairs = []
    for sVariable in ("LOCALAPPDATA", "APPDATA", "TEMP", "USERPROFILE"):
        sValue = os.environ.get(sVariable, "")
        if sValue and len(sValue) > 3:
            lPairs.append((sValue, f"%{sVariable}%"))
    sUser = os.environ.get("USERNAME", "")
    if sUser and len(sUser) > 2:
        lPairs.append((sUser, "%USERNAME%"))
    sComputer = os.environ.get("COMPUTERNAME", "")
    if sComputer and len(sComputer) > 2:
        lPairs.append((sComputer, "%COMPUTERNAME%"))
    lPairs.sort(key=lambda t2: -len(t2[0]))
    return lPairs


lRedactions = []


def redact(sText):
    """Replace the user's own names with what they stand for."""
    global lRedactions
    if not lRedactions:
        lRedactions = buildRedactions()
    sResult = str(sText)
    for sFrom, sTo in lRedactions:
        if sFrom in sResult:
            sResult = sResult.replace(sFrom, sTo)
        sLower = sFrom.lower()
        if sLower != sFrom and sLower in sResult:
            sResult = sResult.replace(sLower, sTo)
    return sResult


class RedactingFormatter(logging.Formatter):
    """Take the user's name out of every line, whoever wrote it.

    Done here rather than at each call, because there are several hundred
    places that log a path and one of them would be forgotten. A rule applied
    at the last moment before writing cannot be bypassed by a caller who did
    not know about it.
    """

    def format(self, record):
        return redact(super().format(record))


class SessionFileHandler(logging.FileHandler):
    """Write one line at a time, with a byte order mark and Windows breaks.

    Three things Windows text tools expect and Python does not do by default.

    The byte order mark tells Notepad and EdSharp that the file is UTF-8, so a
    log with an accented character in a page title opens as that character
    rather than as two wrong ones. It is written once, when the file is
    created, and never again.

    CRLF is what every Windows editor treats as a line break. Without it the
    whole log is one enormous line in some of them.

    And each line is flushed as it is written. A buffered log loses its last
    few lines exactly when something has gone wrong, which is when those lines
    are the ones worth having.
    """

    def __init__(self, pathFile, mode="w", encoding="utf-8"):
        bNew = mode == "w" or not pathFile.exists() or pathFile.stat().st_size == 0
        super().__init__(pathFile, mode=mode, encoding=encoding, delay=False)
        self.terminator = "\r\n"
        if bNew:
            try:
                self.stream.write("\ufeff")
                self.stream.flush()
            except Exception:
                pass

    def emit(self, record):
        super().emit(record)
        try:
            self.flush()
        except Exception:
            pass


def sessionLogName():
    """A name that says which session this was.

    One file per session, named for when it started, rather than one file
    overwritten each time. A user who reports something an hour later still
    has the log from when it happened, and a log that is being read is not the
    log being written to.
    """
    import datetime

    return f"HomerView{datetime.datetime.now():%Y%m%d-%H%M%S}.log"


def pruneOldLogs(pathFolder, iKeep=30):
    """Keep the recent logs and remove the rest.

    One file per session accumulates, and nobody wants a folder of nine hundred
    of them. Thirty is enough to reach back through a few weeks of ordinary use
    and small enough that the folder stays readable.
    """
    try:
        lLogs = sorted(pathFolder.glob("HomerView*.log"),
                       key=lambda p2: p2.stat().st_mtime, reverse=True)
        for pathOld in lLogs[iKeep:]:
            try:
                pathOld.unlink()
            except OSError:
                pass
        return len(lLogs) - iKeep if len(lLogs) > iKeep else 0
    except OSError:
        return 0


def startSession(sAddonVersion=""):
    """Open a fresh log for this session and write the header block."""
    global pathLogFile
    pathFolder = chooseLogFolder()
    if not pathFolder:
        return None
    # A logs folder inside HomerView's own, so the folder a user opens is not
    # a wall of log files with the settings and the database among them.
    pathFolder = pathFolder / "logs"
    try:
        pathFolder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    pathLogFile = pathFolder / sessionLogName()
    sAddonVersion = sAddonVersion or readAddonVersion()
    # No rolling any more. Each session has its own file, named for when it
    # began, so nothing has to be moved aside and an older log is never lost to
    # make room for a newer one.
    iRemoved = pruneOldLogs(pathFolder)
    bContinuing = False
    for handlerExisting in list(homerLog.handlers):
        try:
            handlerExisting.close()
        except Exception:
            pass
        homerLog.removeHandler(handlerExisting)
    handler = SessionFileHandler(pathLogFile, mode="w", encoding="utf-8")
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s  %(levelname)-7s  %(threadName)-17s  %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    homerLog.addHandler(handler)
    homerLog.setLevel(logLevel)
    homerLog.propagate = False
    writeHeader(sAddonVersion)
    if iRemoved:
        homerLog.info(f"Removed {iRemoved} old session logs, keeping the most recent 30")
    return pathLogFile


def writeHeader(sAddonVersion):
    logSection("Session started")
    homerLog.info(f"HomerView add-on version: {sAddonVersion}")
    homerLog.info(f"Log file: {pathLogFile}")
    if not bUsingPreferredFolder:
        homerLog.warning(
            "The local application data folder could not be written, so the log fell "
            "back to the user's home folder."
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
    try:
        import config

        homerLog.info(
            "NVDA keyboard layout: "
            f"{config.conf['keyboard']['keyboardLayout']}")
    except Exception:
        pass
    logSection("What this log holds")
    homerLog.info(
        "This log is for you. HomerView never sends it anywhere; Control+Shift+L "
        "puts it on the clipboard so that you can choose to attach it to an email."
    )
    homerLog.info(
        "Your user name and computer name are replaced with the variables that "
        "stand for them, so a path reads %USERPROFILE% rather than naming you."
    )
    homerLog.info(
        "It does record the addresses and titles of pages opened in HomerView, "
        "and text you searched for, because a fault usually cannot be explained "
        "without them. Read it before sending it if that matters for what you "
        "were doing."
    )


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
