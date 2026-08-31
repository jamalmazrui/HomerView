"""Which browser HomerView drives, and finding the ones installed here.

HomerView started as an Edge program and is not one any more. Everything it
does travels over the Chrome DevTools Protocol, which every Chromium browser
speaks, so Chrome, Brave, Vivaldi and Edge are the same program as far as this
code is concerned. The only thing that differs is which executable to start.

WHY THE LIST BELOW IS NOT THE ANSWER ON ITS OWN

A list of names and folders goes stale. So the list is only a way of asking
Windows a better question: App Paths, which is where a program registers where
it lives; and StartMenuInternet, which is where a browser registers that it is
a browser. StartMenuInternet is enumerable, so it finds browsers this file has
never heard of, and that is the point of including it.

AND THE REAL TEST IS NOT A NAME AT ALL

Whether a browser can be driven is not decided by what it is called. It is
decided by whether it publishes a DevToolsActivePort file when started with a
debugging port on a profile of its own. `canBeDriven` starts the candidate,
watches for that file, and closes it again. One run answers the question for
that machine, which beats any list of what is supposed to be Chromium.

Firefox is deliberately absent. It speaks its own protocol and a CDP bridge
for it was retired, so it would fail the test rather than mislead anyone --
but there is no reason to make somebody discover that by trying.

THE ONE PLACE THE CHOICE IS KEPT is HomerView.inix, in the roaming
application data folder, as two values in [Preferences]:

    browser=Google Chrome
    browserPath=C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe

The path is what launches. The name is for saying out loud. The JAWS side
reads the same file, and derives the executable name from browserPath rather
than keeping its own copy, so the two cannot disagree about which browser is
in use.

THIS TABLE IS DUPLICATED IN HomerView.cs, because the JAWS side has no Python
and the NVDA side must not depend on the program being installed beside it.
checkHomerViewQuality compares the two, since nothing else would notice them
drifting apart.
"""

import os, subprocess, time, winreg
from pathlib import Path

from .logger import homerLog, logError

# name, executable, and the folders it is usually installed into, relative to
# Program Files, Program Files (x86) and Local Application Data.
lKnownBrowsers = [
    ("Microsoft Edge", "msedge.exe", ["Microsoft/Edge/Application"]),
    ("Google Chrome", "chrome.exe", ["Google/Chrome/Application"]),
    ("Brave", "brave.exe", ["BraveSoftware/Brave-Browser/Application"]),
    ("Vivaldi", "vivaldi.exe", ["Vivaldi/Application"]),
    ("Opera", "opera.exe", ["Opera", "Programs/Opera"]),
    ("Chromium", "chrome.exe", ["Chromium/Application"]),
]

c_sDefaultBrowser = "Microsoft Edge"
c_sPortFileName = "DevToolsActivePort"
c_sStartMenuKey = r"SOFTWARE\Clients\StartMenuInternet"
c_iDriveTestSeconds = 15
lRootVariables = ["PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"]


def appPathsExecutable(sExe):
    """Where Windows says a program lives, or an empty string.

    App Paths is checked under both hives, because a browser installed for one
    user registers under HKEY_CURRENT_USER and a machine-wide one under
    HKEY_LOCAL_MACHINE, and a person may have either.
    """
    sKey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + sExe
    for iHive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(iHive, sKey) as key:
                sPath = winreg.QueryValueEx(key, "")[0]
        except OSError:
            continue
        pathFound = Path(str(sPath).strip('"'))
        if pathFound.is_file():
            return str(pathFound)
    return ""


def folderExecutable(sExe, lFolders):
    """The first of the usual installation folders that actually holds it."""
    for sVariable in lRootVariables:
        sRoot = os.environ.get(sVariable, "")
        if not sRoot:
            continue
        for sFolder in lFolders:
            pathTry = Path(sRoot).joinpath(*sFolder.split("/")) / sExe
            if pathTry.is_file():
                return str(pathTry)
    return ""


def startMenuBrowsers():
    """Browsers that have registered themselves with Windows as browsers.

    This is the half that finds what the table does not know about. The
    command is stored as a command line, so the executable has to be taken out
    of it, quotes and arguments and all.
    """
    lFound = []
    for iHive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(iHive, c_sStartMenuKey) as keyRoot:
                iIndex = 0
                while True:
                    try:
                        sClient = winreg.EnumKey(keyRoot, iIndex)
                    except OSError:
                        break
                    iIndex += 1
                    try:
                        with winreg.OpenKey(
                                keyRoot, sClient + r"\shell\open\command") as keyCommand:
                            sCommand = winreg.QueryValueEx(keyCommand, "")[0]
                    except OSError:
                        continue
                    sPath = str(sCommand).strip()
                    if sPath.startswith('"'):
                        sPath = sPath[1:].split('"', 1)[0]
                    else:
                        sPath = sPath.split(" ")[0]
                    if Path(sPath).is_file():
                        lFound.append((sClient, sPath))
        except OSError:
            continue
    return lFound


def findBrowsers():
    """Every browser worth offering, newest lookup first, without duplicates.

    Returns a list of dictionaries with a name, a path, and how it was found,
    because how it was found is the first thing worth knowing when the answer
    looks wrong.
    """
    lFound = []
    setPaths = set()

    def add(sName, sPath, sHow):
        if not sPath:
            return
        sKey = sPath.lower()
        if sKey in setPaths:
            return
        setPaths.add(sKey)
        lFound.append({"name": sName, "path": sPath, "how": sHow})
        homerLog.debug(f"Browser found: {sName} at {sPath} ({sHow})")

    for sName, sExe, lFolders in lKnownBrowsers:
        add(sName, appPathsExecutable(sExe), "registered in App Paths")
        add(sName, folderExecutable(sExe, lFolders), "in its usual folder")

    # Anything Windows knows is a browser and this file does not. Named after
    # its registry client name, which is what the user would recognise.
    for sClient, sPath in startMenuBrowsers():
        add(sClient, sPath, "registered as a browser with Windows")

    homerLog.info(f"{len(lFound)} browser(s) found")
    return lFound


def canBeDriven(sPath, pathProfile):
    """Whether this browser publishes a debugging port, tested rather than assumed.

    The whole of HomerView travels over the DevTools protocol, and a browser
    that will not open a port for it cannot be used at all. Asking the browser
    is the only honest way to know: the name proves nothing, since a Chromium
    fork may have the feature removed and an unfamiliar name may have it.

    The browser is started on a profile of its own and closed again. Since
    Chromium 136 the debugging switches are ignored on the default profile, so
    a test on the user's own profile would fail for a browser that works.
    """
    pathProfile = Path(pathProfile)
    pathPort = pathProfile / c_sPortFileName
    try:
        pathProfile.mkdir(parents=True, exist_ok=True)
        if pathPort.exists():
            pathPort.unlink()
    except OSError:
        logError("The test profile folder could not be prepared")
        return False, "the test profile folder could not be prepared"
    lArguments = [
        sPath,
        "--remote-debugging-port=0",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={pathProfile}",
        "--no-first-run",
        "--headless=new",
        "about:blank",
    ]
    homerLog.info(f"Testing whether {sPath} can be driven")
    try:
        process = subprocess.Popen(lArguments, close_fds=True)
    except OSError as exception:
        return False, f"it would not start ({exception})"
    nDeadline = time.monotonic() + c_iDriveTestSeconds
    bWorks = False
    while time.monotonic() < nDeadline:
        if pathPort.is_file():
            bWorks = True
            break
        time.sleep(0.25)
    try:
        process.terminate()
    except OSError:
        pass
    if bWorks:
        homerLog.info(f"{sPath} published a debugging port and can be driven")
        return True, "it opened a debugging port"
    homerLog.warning(f"{sPath} never published a debugging port")
    return False, "it never opened a debugging port, so HomerView cannot drive it"


def chosenBrowser():
    """The browser HomerView uses: its name and the path that launches it.

    Edge when nothing has been chosen, which is what every installation before
    the setting existed used, so an upgrade changes nothing for anybody.
    """
    from . import settings

    sName = settings.getValue("Preferences", "browser", "")
    sPath = settings.getValue("Preferences", "browserPath", "")
    if sPath and Path(sPath).is_file():
        return sName or Path(sPath).stem, sPath
    if sPath:
        homerLog.warning(f"The chosen browser is no longer at {sPath}")
    return c_sDefaultBrowser, ""


def rememberBrowser(sName, sPath):
    """Write the choice where both screen readers read it."""
    from . import settings

    settings.setValue("Preferences", "browser", sName)
    settings.setValue("Preferences", "browserPath", sPath)
    homerLog.info(f"The browser is now {sName} at {sPath}")
