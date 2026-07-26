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
from .logger import homerLog, logError, logSection

appPathsKey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
launchTimeoutSeconds = 25.0
pollIntervalSeconds = 0.25
portFileName = "DevToolsActivePort"
portProbeTimeoutSeconds = 0.4

# HomerView writes a small start page beside the log and opens that, rather than
# about:blank, which leaves NVDA with nothing to announce. Set startPageUrl to
# any address, such as "https://www.google.com/", to open that instead, or to
# "about:blank" for the older behaviour.
startPageFileName = "Start.html"
startPageUrl = ""

# Set this to True to let the HomerView profile be signed in and synchronised,
# so that bookmarks, passwords, and extensions arrive from a Microsoft account.
# The prompt suppression below still applies, so sign-in stays deliberate rather
# than automatic. The default is False, which is the isolated behaviour proven
# in urlFido and bookFido.
bAllowSignIn = False

# Applied on every launch. The disable-features list is best-effort: the
# Chromium entries are long standing, while Edge's implicit sign-in feature has
# been named differently across versions, so several spellings are passed. An
# unrecognised feature name is ignored rather than rejected, so listing extras
# is safe.
lArgumentsAlways = [
    "--disable-background-networking",
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
]

# Applied only when bAllowSignIn is False.
lArgumentsIsolated = [
    "--disable-sync",
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

    def activateWindow(self):
        """Bring a top level window of the HomerView browser to the front.

        The protocol can raise a tab within its own window, but it cannot make
        that window the foreground window of Windows, which is what the user
        actually needs when they were reading somewhere else a moment ago.
        """
        if not self.iProcessId:
            return False
        lHandles = []

        def collect(iHandle, iParameter):
            iOwner = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(iHandle, ctypes.byref(iOwner))
            if iOwner.value in self.setProcessIds and ctypes.windll.user32.IsWindowVisible(iHandle):
                iLength = ctypes.windll.user32.GetWindowTextLengthW(iHandle)
                if iLength > 0:
                    lHandles.append(iHandle)
            return True

        prototype = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        try:
            ctypes.windll.user32.EnumWindows(prototype(collect), 0)
        except Exception:
            logError("The browser windows could not be enumerated")
            return False
        homerLog.info(f"Found {len(lHandles)} visible HomerView browser windows")
        for iHandle in lHandles:
            try:
                ctypes.windll.user32.ShowWindow(iHandle, 9)  # SW_RESTORE
                bResult = bool(ctypes.windll.user32.SetForegroundWindow(iHandle))
                # Windows refuses foreground changes from a process that does
                # not already own the foreground, and the call can still report
                # success while only flashing the taskbar button. Asking which
                # window is actually in front is the only honest check.
                iForeground = ctypes.windll.user32.GetForegroundWindow()
                bReally = int(iForeground) == int(iHandle)
                homerLog.info(
                    f"Activated window {iHandle}: call returned {bResult}, "
                    f"foreground is now {iForeground}, actually in front: {bReally}"
                )
                if bReally:
                    return True
                homerLog.warning(
                    "Windows declined to bring the HomerView window to the front. "
                    "Its taskbar button may be flashing instead. Press Alt+Tab, or "
                    "NVDA+Alt+H again once another HomerView window has focus."
                )
            except Exception:
                logError(f"Window {iHandle} could not be activated")
        return False

    def resolveStartPage(self, sOverrideUrl=""):
        """Return the address the new window should open."""
        if sOverrideUrl:
            homerLog.info(f"Start page taken from the browser already running: {sOverrideUrl}")
            return sOverrideUrl
        if startPageUrl:
            homerLog.info(f"Start page overridden: {startPageUrl}")
            return startPageUrl
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
            "signin": {"allowed": bAllowSignIn, "allowed_on_next_startup": bAllowSignIn},
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
