"""Support for Microsoft Edge's Copilot, and the one thing that constrains it.

The default profile is not available, and this is a hard limit rather than a
preference. Since Chrome 136 and the matching Edge release, the remote
debugging switches are ignored outright when the data directory is the
browser's default one. Launching HomerView against the default profile would
produce a browser with no protocol connection at all: no reports, no page
explorer, no downloads, none of it. The separate profile is what makes every
other command in HomerView possible.

What the separate profile costs is exactly what is being asked about here. It
starts with no sign-in, so Copilot has no account, sites ask you to log in, and
a download behind a login wall fails. The answer is not to give up the separate
profile but to sign that profile in: it is a real profile that happens to live
somewhere else, and once signed in it has an account, sessions, cookies,
bookmarks and Copilot, while still permitting the debugging connection.

So Copilot support means allowing sign-in, and nothing more than that. Every
switch that keeps the first launch quiet is kept: the sync dialog, the promos
and the automatic sign-in stay suppressed, so signing in remains something the
user chooses rather than something that happens to them.

Sending the shortcut needs the Windows keyboard rather than the protocol.
Control+Shift+Period is handled by the browser's own interface, not by the
page, so a key dispatched into a page through the Input domain never reaches
it. The window is brought to the front first and the keystroke sent through
the operating system, which is what a real key press does.
"""

import ctypes
import time

import addonHandler

from .logger import abbreviate, homerLog, logError, logSection

addonHandler.initTranslation()

keyEventKeyUp = 0x0002
virtualControl = 0x11
virtualPeriod = 0xBE
virtualShift = 0x10

# Long enough for the window to settle after being raised, short enough not to
# be noticed. Sending the keystroke into a window that is still arriving loses
# it, which looks exactly like the shortcut not working.
settleSeconds = 0.35


def sendCopilotShortcut():
    """Press Control+Shift+Period, as a person would."""
    logSection("Command: open Copilot")
    try:
        for iKey in (virtualControl, virtualShift):
            ctypes.windll.user32.keybd_event(iKey, 0, 0, 0)
        ctypes.windll.user32.keybd_event(virtualPeriod, 0, 0, 0)
        ctypes.windll.user32.keybd_event(virtualPeriod, 0, keyEventKeyUp, 0)
        for iKey in (virtualShift, virtualControl):
            ctypes.windll.user32.keybd_event(iKey, 0, keyEventKeyUp, 0)
        homerLog.info("Sent Control+Shift+Period to the foreground window")
        return True
    except Exception:
        logError("The Copilot shortcut could not be sent")
        return False


def describeReadiness(edgeManager):
    """Say whether this profile can use Copilot, and why not when it cannot."""
    from . import edge

    lNotes = []
    if not edge.bAllowSignIn:
        lNotes.append(
            "Sign-in is turned off for the HomerView profile, so Copilot has no account. "
            "Set bAllowSignIn to True in edge.py, delete the profile folder, and launch again."
        )
    if edge.bCopilotSupport:
        lNotes.append("Copilot support is on: background networking is left enabled.")
    else:
        lNotes.append(
            "Copilot support is off, so background networking is disabled and the sidebar "
            "may not load. Set bCopilotSupport to True in edge.py."
        )
    lNotes.append(f"Profile: {edgeManager.pathProfile}")
    homerLog.info(f"Copilot readiness: {lNotes}")
    return lNotes


def prepareContext(cdpSession):
    """Put the page's readable text on the clipboard for Copilot to receive.

    Copilot in the sidebar can see the page already, but a reader often wants
    to ask about a particular part, or about a page whose content arrived after
    Copilot looked. Having the text ready to paste costs nothing and covers
    both.
    """
    import api

    from . import mainContent

    dTarget, sSessionId = cdpSession.findActivePageSession()
    sText = ""
    try:
        sText = cdpSession.evaluate(
            sSessionId,
            "(() => { const el = document.querySelector('main, [role=main], article') "
            "|| document.body; return (el.innerText || '').trim().slice(0, 20000); })()",
            mainContent.extractTimeoutSeconds,
        ) or ""
    except Exception:
        logError("The page text could not be read for Copilot")
    sTitle = dTarget.get("title", "")
    sUrl = dTarget.get("url", "")
    homerLog.info(
        f"Copilot context: {len(sText)} characters from {abbreviate(sTitle, 100)} "
        f"at {abbreviate(sUrl, 200)}"
    )
    if sText:
        sPayload = f"{sTitle}\n{sUrl}\n\n{sText}"
        try:
            api.copyToClip(sPayload)
            homerLog.info(f"Placed {len(sPayload)} characters on the clipboard")
        except Exception:
            logError("The Copilot context could not be copied")
    return {"characters": len(sText), "title": sTitle, "url": sUrl}
