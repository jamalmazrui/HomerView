"""Locate and launch the dedicated HomerView instance of Microsoft Edge.

Since Chrome 136 and the matching Edge release, remote debugging switches are
ignored against the browser's default data directory, so a separate profile is
not a preference but a requirement. The profile lives under LOCALAPPDATA rather
than the installation folder, because a standard user cannot write to a folder
installed with administrator rights.

Remote debugging uses port 0, letting Edge choose a free port and publish it in
the DevToolsActivePort file. That avoids collisions with other developer tools.

Edge signs a brand-new profile into the Windows account and immediately opens a
modal sync consent dialog. That dialog blocks the address bar, so the browser
appears frozen. The switches and seeded preferences below shut down implicit
sign-in, sync, and the promotional screens that accompany them. They are taken
from urlFido and bookFido, where the same problem was solved and the result has
been in daily use.
"""

import json
import ctypes
import os
import socket
import subprocess
import time
import winreg
from pathlib import Path

from . import logger
from . import startPage
from .logger import abbreviate, homerLog, logError, logSection

appPathsKey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
launchTimeoutSeconds = 25.0
pollIntervalSeconds = 0.25
portFileName = "DevToolsActivePort"
processFileName = "HomerView.pid"
portProbeTimeoutSeconds = 0.4

# HomerView writes a small start page beside the log and opens that, rather than
# about:blank, which leaves NVDA with nothing to announce. Set startPageUrl to
# any address, such as "https://www.google.com/", to open that instead, or to
# "about:blank" for the older behaviour.
# Reopen the page the profile last had open, rather than the start page. The
# profile is persistent, so its cookies and sessions come back with it.
bReopenLastPage = True

startPageFileName = "Start.htm"
startPageUrl = ""

# Set this to True to let the HomerView profile be signed in and synchronised,
# so that bookmarks, passwords, and extensions arrive from a Microsoft account.
# The prompt suppression below still applies, so sign-in stays deliberate rather
# than automatic. The default is False, which is the isolated behaviour proven
# in urlFido and bookFido.
bAllowSignIn = False

# Microsoft Edge's Copilot needs two things: an account, which means sign-in
# must be allowed, and the background networking its sidebar uses. Everything
# that keeps the first launch quiet is kept either way, so the sync dialog, the
# promotional screens and the automatic sign-in stay suppressed and signing in
# remains something chosen rather than something done to the user.
bCopilotSupport = True

# Google refuses to sign anyone in on a browser started with remote debugging.
# The message is that the browser or app may not be secure, and it is aimed at
# scripts driving a browser to take over accounts. HomerView is not that, but
# it is indistinguishable from the outside, because the same switch enables
# both.
#
# There is no way to have the debugging connection and sign in to Google in the
# same browser. The connection is what every HomerView command depends on, so
# it stays, and the sign-in has to happen elsewhere.
#
# What works is signing in to Edge itself rather than to the website. A profile
# signed in to a Microsoft account carries its cookies, and a Google session
# established in an ordinary Edge window before HomerView is launched is
# already present in the profile when HomerView opens it. So the order is: sign
# in first, in a browser without debugging, then launch HomerView, which finds
# you already signed in.
#
# This is documented rather than worked around, because a workaround that
# defeated the check would be exactly the thing the check exists to stop.
sGoogleSignInNote = (
    "Google will not sign anyone in on a browser started with remote debugging, "
    "which is what HomerView needs. Sign in to Google in an ordinary Edge window "
    "first, using the same profile, and HomerView will find the session already "
    "there when it launches."
)

# Applied on every launch. The disable-features list is best-effort: the
# Chromium entries are long standing, while Edge's implicit sign-in feature has
# been named differently across versions, so several spellings are passed. An
# unrecognised feature name is ignored rather than rejected, so listing extras
# is safe.
lArgumentsAlways = [
    "--disable-client-side-phishing-detection",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-features=msImplicitSignin,msEdgeImplicitSignin,EdgeAutoSignIn,"
    "SyncPromo,SigninPromo,PrivacySandboxSettings4,SearchEngineChoiceScreen",
    "--metrics-recording-only",
    "--no-default-browser-check",
    "--no-first-run",
    "--no-service-autorun",
    # Edge otherwise relaunches itself through a compatibility layer, which is
    # one of the ways the process we start disappears from under us.
    "--edge-skip-compat-layer-relaunch",
    # Do not advertise the browser as automated. Chromium sets a flag on the
    # page when remote debugging is on, and some sign-in pages read it and
    # refuse. Turning the flag off is honest here: this browser is not being
    # driven by a script, it is being driven by the person at the keyboard
    # through their screen reader, which is what the flag was meant to detect
    # and is not what it finds. It does not affect the debugging connection.
    "--disable-blink-features=AutomationControlled",
]

# Applied only when bAllowSignIn is False.
lArgumentsIsolated = [
    "--disable-sync",
]

# Dropped when Copilot support is on, because the sidebar needs it.
lArgumentsWithoutCopilot = [
    "--disable-background-networking",
]

dHiveNames = {
    winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
    winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
}


class EdgeError(Exception):
    pass


class EdgeManager:
    def __init__(self):
        self.bLauncherExited = False
        self.iProcessId = 0
        self.setProcessIds = set()
        self.pathProfile = (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HomerView" / "EdgeProfile"
        )
        self.process = None
        homerLog.info(f"Edge profile folder: {self.pathProfile}")

    @property
    def pathPortFile(self):
        return self.pathProfile / portFileName

    def findEdge(self):
        pathRegistered = self.findRegisteredEdge()
        if pathRegistered:
            homerLog.info(f"Edge located through App Paths: {pathRegistered}")
            return pathRegistered
        lCandidates = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]
        for pathCandidate in lCandidates:
            bFound = pathCandidate.is_file()
            homerLog.debug(f"Edge candidate {pathCandidate}: {'found' if bFound else 'absent'}")
            if bFound:
                homerLog.info(f"Edge located by path: {pathCandidate}")
                return pathCandidate
        homerLog.error("Edge could not be located by any method")
        raise EdgeError(
            "Microsoft Edge could not be found. Install Microsoft Edge or repair its Windows installation."
        )

    def findRegisteredEdge(self):
        for iHive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            sHive = dHiveNames.get(iHive, str(iHive))
            try:
                with winreg.OpenKey(iHive, appPathsKey) as key:
                    sPath = winreg.QueryValueEx(key, "")[0]
            except OSError as exception:
                homerLog.debug(f"Edge App Paths lookup in {sHive} failed: {exception}")
                continue
            pathEdge = Path(sPath.strip('"'))
            homerLog.debug(f"Edge App Paths value in {sHive}: {pathEdge}")
            if pathEdge.is_file():
                return pathEdge
        return None

    def recordBrowserProcess(self):
        """Remember which process this profile's browser is, for a later session.

        NVDA restarts often, and when it does, HomerView forgets everything it
        knew about a browser that is still sitting there. The process
        identifier is written into the profile folder, which is where a fact
        about that profile belongs, so a later session can find the window
        again without a protocol connection.
        """
        try:
            (self.pathProfile / processFileName).write_text(
                str(self.iProcessId), encoding="utf-8")
            homerLog.debug(f"Recorded browser process {self.iProcessId}")
        except OSError:
            logError("The browser process could not be recorded")

    def readBrowserProcess(self):
        try:
            sText = (self.pathProfile / processFileName).read_text(encoding="utf-8").strip()
            return int(sText) if sText.isdigit() else 0
        except (OSError, ValueError):
            return 0

    def findExistingWindows(self):
        """Return visible windows of this profile's browser, front-most first.

        EnumWindows walks in z order, so the first handle it offers is the one
        most recently in front. That is the window a user means when they ask
        for the one they were last using.

        The search uses the process identifiers this session knows, and falls
        back to the one recorded in the profile, which is what makes this work
        after NVDA has restarted and forgotten everything.
        """
        setProcessIds = set(self.setProcessIds)
        iRecorded = self.readBrowserProcess()
        if iRecorded:
            setProcessIds.add(iRecorded)
        if not setProcessIds:
            homerLog.debug("No browser process is known, so no window can be looked for")
            return []
        lHandles = []

        def collect(iHandle, iParameter):
            iOwner = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(iHandle, ctypes.byref(iOwner))
            if (iOwner.value in setProcessIds
                    and ctypes.windll.user32.IsWindowVisible(iHandle)
                    and ctypes.windll.user32.GetWindowTextLengthW(iHandle) > 0):
                lHandles.append(iHandle)
            return True

        prototype = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        try:
            ctypes.windll.user32.EnumWindows(prototype(collect), 0)
        except Exception:
            logError("The browser windows could not be enumerated")
            return []
        homerLog.info(
            f"Found {len(lHandles)} existing HomerView window(s) for process(es) "
            f"{sorted(setProcessIds)}"
        )
        return lHandles

    def activateHandle(self, iHandle):
        """Bring one window to the front and say whether Windows allowed it."""
        try:
            ctypes.windll.user32.ShowWindow(iHandle, 9)  # SW_RESTORE
            bResult = bool(ctypes.windll.user32.SetForegroundWindow(iHandle))
            iForeground = ctypes.windll.user32.GetForegroundWindow()
            bReally = int(iForeground) == int(iHandle)
            homerLog.info(
                f"Activated window {iHandle}: call returned {bResult}, "
                f"foreground is now {iForeground}, actually in front: {bReally}"
            )
            return bReally
        except Exception:
            logError(f"Window {iHandle} could not be activated")
            return False

    def activateWindow(self):
        """Bring a top level window of the HomerView browser to the front.

        The protocol can raise a tab within its own window, but it cannot make
        that window the foreground window of Windows, which is what the user
        actually needs when they were reading somewhere else a moment ago.
        """
        for iHandle in self.findExistingWindows():
            if self.activateHandle(iHandle):
                return True
        return False

    def readLastSession(self):
        """Return the address this profile had open when it last closed.

        The profile is persistent, so Edge has already recorded this in its own
        preferences. Reading it there is better than keeping a second copy that
        could disagree with the browser, and it means cookies, sessions and
        logins come back with the page rather than being reconstructed.
        """
        pathPreferences = self.pathProfile / "Default" / "Preferences"
        try:
            import json as jsonModule

            dPreferences = jsonModule.loads(
                pathPreferences.read_text(encoding="utf-8", errors="replace"))
        except Exception as exception:
            homerLog.debug(f"No previous session could be read: {exception}")
            return ""
        for lKeys in (
            ("session", "startup_urls"),
            ("browser", "last_known_urls"),
        ):
            vValue = dPreferences
            for sKey in lKeys:
                vValue = vValue.get(sKey, {}) if isinstance(vValue, dict) else {}
            if isinstance(vValue, list) and vValue:
                sUrl = str(vValue[0])
                if sUrl.startswith("http"):
                    homerLog.info(f"Previous session recorded {abbreviate(sUrl, 200)}")
                    return sUrl
        homerLog.info("The profile records no previous page")
        return ""

    def copyDocuments(self, pathFolder):
        """Put the shipped documents beside the start page.

        The start page links them with plain relative addresses, which only
        resolve if they sit in the same folder. Copying them there also means a
        link opens in this window rather than being handed to whichever browser
        owns .htm files, which is the whole point of listing them.
        """
        from . import documents

        iCopied = 0
        for _sKey, sHtm, _sMarkdown, _sTitle in documents.lDocuments:
            pathSource = documents.findInstalledDocument(sHtm)
            if not pathSource:
                continue
            pathTarget = pathFolder / sHtm
            try:
                if not pathTarget.is_file() or pathTarget.stat().st_mtime < pathSource.stat().st_mtime:
                    pathTarget.write_bytes(pathSource.read_bytes())
                    iCopied += 1
            except OSError:
                logError(f"{sHtm} could not be placed beside the start page")
        homerLog.info(f"Placed {iCopied} documents beside the start page")

    def resolveStartPage(self, sOverrideUrl=""):
        """Return the address the new window should open."""
        if sOverrideUrl:
            homerLog.info(f"Start page taken from the browser already running: {sOverrideUrl}")
            return sOverrideUrl
        if startPageUrl:
            homerLog.info(f"Start page overridden: {startPageUrl}")
            return startPageUrl
        if bReopenLastPage:
            sLast = self.readLastSession()
            if sLast:
                homerLog.info(f"Reopening the page this profile last had open: {abbreviate(sLast, 200)}")
                return sLast
        pathFolder = logger.pathLogFile.parent if logger.pathLogFile else self.pathProfile.parent
        pathStart = pathFolder / startPageFileName
        try:
            bCurrent = False
            if pathStart.exists():
                bCurrent = startPage.getVersionMarker() in pathStart.read_text(
                    encoding="utf-8", errors="ignore"
                )
            if not bCurrent:
                pathStart.write_text(startPage.getStartPageText(), encoding="utf-8")
                homerLog.info(f"Wrote the start page: {pathStart}")
            self.copyDocuments(pathFolder)
            return pathStart.as_uri()
        except Exception:
            logError("Could not write the start page, so about:blank is used instead")
            return "about:blank"

    def seedPreferences(self):
        """Write preferences before Edge first opens the profile.

        Belt and braces alongside the command line switches. Writing these means
        Edge never reaches the state in which it would offer to sign in or sync.
        This runs only when the profile folder is being created, so a profile the
        user has since configured is never overwritten.
        """
        dPreferences = {
            "browser": {"has_seen_welcome_page": True},
            "credentials_enable_service": False,
            "profile": {"exit_type": "Normal", "exited_cleanly": True},
            "session": {"restore_on_startup": 1},
            "signin": {"allowed": bAllowSignIn, "allowed_on_next_startup": bAllowSignIn},
            "edge_copilot": {"enabled": bCopilotSupport},
            "sync": {"has_setup_completed": False, "requested": False},
        }
        pathDefault = self.pathProfile / "Default"
        pathDefault.mkdir(parents=True, exist_ok=True)
        pathPreferences = pathDefault / "Preferences"
        pathPreferences.write_text(json.dumps(dPreferences), encoding="utf-8")
        homerLog.info(f"Seeded a fresh profile: {pathPreferences}")
        homerLog.debug(f"Seeded preferences: {dPreferences}")

    def readPort(self):
        try:
            sContent = self.pathPortFile.read_text(encoding="utf-8", errors="ignore")
        except OSError as exception:
            homerLog.debug(f"Port file unreadable: {exception}")
            return 0
        lLines = sContent.splitlines()
        homerLog.debug(f"Port file contains {len(lLines)} lines")
        sFirstLine = lLines[0].strip() if lLines else ""
        try:
            iPort = int(sFirstLine)
        except ValueError:
            homerLog.debug(f"Port file first line is not a number: {sFirstLine!r}")
            return 0
        homerLog.info(f"Remote debugging port from the port file: {iPort}")
        return iPort

    def isPortAlive(self, iPort):
        """Confirm something is listening before trusting the port file.

        The port file survives the browser that wrote it. Attempting a full
        protocol handshake against a dead port cost about two seconds on every
        launch before the operating system refused the connection; a short
        socket probe settles it in a fraction of that.
        """
        try:
            with socket.create_connection(("127.0.0.1", iPort), portProbeTimeoutSeconds):
                return True
        except OSError as exception:
            homerLog.info(f"Port {iPort} is not listening ({exception}); the port file is stale")
            return False

    def attach(self):
        """Return the port of an already-running HomerView Edge, or zero."""
        homerLog.info(f"Edge attach: reading {self.pathPortFile}")
        iPort = self.readPort()
        if not iPort:
            return 0
        if not self.isPortAlive(iPort):
            # Nothing is listening, so the file is left over from a browser that
            # has gone. Removing it saves probing the same dead port a second
            # time when the launch path repeats this check.
            try:
                self.pathPortFile.unlink()
                homerLog.debug("Removed the stale port file")
            except OSError:
                pass
            return 0
        return iPort

    def launch(self, sOverrideUrl=""):
        """Start HomerView Edge and return its remote debugging port."""
        logSection("Launching HomerView Edge")
        bNewProfile = not self.pathProfile.exists()
        self.pathProfile.mkdir(parents=True, exist_ok=True)
        if bNewProfile:
            homerLog.info("The profile folder did not exist, so it is being seeded")
            try:
                self.seedPreferences()
            except Exception:
                logError("Seeding the profile preferences failed; continuing with switches only")
        else:
            homerLog.info(
                "The profile folder already exists, so preferences are left alone. "
                "Delete it to get a freshly seeded profile."
            )
        try:
            self.pathPortFile.unlink()
            homerLog.debug("Stale port file removed")
        except OSError:
            homerLog.debug("No stale port file to remove")
        pathEdge = self.findEdge()
        lArguments = [str(pathEdge)]
        lArguments.extend(lArgumentsAlways)
        if not bAllowSignIn:
            lArguments.extend(lArgumentsIsolated)
        if not bCopilotSupport:
            lArguments.extend(lArgumentsWithoutCopilot)
        homerLog.info(
            f"Copilot support: {bCopilotSupport}. Background networking is "
            f"{'enabled' if bCopilotSupport else 'disabled'}, sign-in is "
            f"{'allowed' if bAllowSignIn else 'not allowed'}."
        )
        if bCopilotSupport and not bAllowSignIn:
            homerLog.warning(
                "Copilot support is on but sign-in is not allowed, so Copilot will have no "
                "account. Set bAllowSignIn to True and delete the profile folder to use it."
            )
        lArguments.extend([
            "--remote-debugging-port=0",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={self.pathProfile}",
            "--new-window",
            self.resolveStartPage(sOverrideUrl),
        ])
        homerLog.info(f"Sign-in and sync allowed: {bAllowSignIn}")
        homerLog.info(f"Edge command line: {lArguments}")
        self.process = subprocess.Popen(lArguments, close_fds=True)
        self.iProcessId = self.process.pid
        self.recordBrowserProcess()
        self.bLauncherExited = False
        homerLog.info(f"Edge started with process id {self.iProcessId}")
        # The process we start very often exits within a fraction of a second
        # after handing its work to another process, while a browser window is
        # opening perfectly well. Treating that exit as a failure aborts a
        # launch that was about to succeed, so only the port file is watched.
        nDeadline = time.monotonic() + launchTimeoutSeconds
        iAttempt = 0
        while time.monotonic() < nDeadline:
            iAttempt += 1
            iPort = self.readPort()
            if iPort:
                homerLog.info(
                    f"Edge ready after {iAttempt} polls and "
                    f"{launchTimeoutSeconds - (nDeadline - time.monotonic()):.1f} seconds"
                )
                return iPort
            iExit = self.process.poll()
            if iExit is not None and not self.bLauncherExited:
                self.bLauncherExited = True
                homerLog.info(
                    f"The process HomerView started exited with code {iExit}. Edge routinely "
                    "hands off to another process, so waiting for the port file continues."
                )
            time.sleep(pollIntervalSeconds)
        homerLog.error(f"Edge did not publish a port within {launchTimeoutSeconds} seconds")
        raise EdgeError(
            "HomerView Edge never published its remote debugging port. Close all Microsoft "
            "Edge windows and try again, or check whether enterprise policy has disabled "
            "remote debugging."
        )
