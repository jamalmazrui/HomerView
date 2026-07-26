"""Where HomerView puts the files it makes.

Generated pages are working documents rather than records. They belong in the
temporary folder, which Windows and Storage Sense clear on their own, so a long
session does not slowly fill a program folder with old reports. The names inside
are stable rather than random, so a file can be found again while it still
exists.

Downloads belong wherever the user's downloads already go, which is a known
folder and not always under the profile.
"""

import os
import tempfile
import winreg
from pathlib import Path

downloadsGuid = "{374DE290-123F-4565-9164-39C4925E467B}"
shellFoldersKey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
tempFolderName = "HomerView"


def sharedHomerFolders():
    """Every place a shared Homer folder may live, most specific first.

    Two kinds of thing want different homes and the difference matters.

    Python modules can live under the user profile. This add-on sits at
    ...\\nvda\\addons\\homerView\\globalPlugins\\homerView, so walking four
    levels up reaches NVDA's own configuration folder, and a Homer folder
    beside addons and scratchpad is reachable from any add-on by the same walk.
    NVDA does not scan that folder, so nothing there is mistaken for an add-on,
    and it survives add-on updates and removals.

    Executables should not live there. The user profile roams, and a growing
    number of managed environments refuse to execute anything from it. Program
    Files is where a binary belongs, which is why the program folders are
    searched as well and are where a bundled pandoc should be installed.
    """
    lFolders = []
    try:
        pathAddon = Path(__file__).resolve()
        # homerView.py -> homerView -> globalPlugins -> homerView -> addons -> nvda
        pathNvda = pathAddon.parents[4]
        lFolders.append(pathNvda / "Homer")
        lFolders.append(pathNvda / "scratchpad" / "homer")
    except Exception:
        pass
    for sVariable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        sRoot = os.environ.get(sVariable, "")
        if sRoot:
            lFolders.append(Path(sRoot) / "Homer")
            lFolders.append(Path(sRoot) / "HomerView")
    return [p for p in lFolders if p.is_dir()]


def findSharedFile(sName):
    """Return the first shared Homer folder holding a named file."""
    for pathFolder in sharedHomerFolders():
        pathCandidate = pathFolder / sName
        try:
            if pathCandidate.is_file():
                return pathCandidate
        except OSError:
            continue
    return None


def getTempFolder():
    """Return a HomerView folder inside the user's temporary folder."""
    pathFolder = Path(tempfile.gettempdir()) / tempFolderName
    pathFolder.mkdir(parents=True, exist_ok=True)
    return pathFolder


def getDownloadsFolder():
    """Return the user's downloads folder, however it has been redirected."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, shellFoldersKey) as key:
            sPath = winreg.QueryValueEx(key, downloadsGuid)[0]
        pathFolder = Path(os.path.expandvars(sPath))
        if pathFolder.is_dir():
            return pathFolder
    except OSError:
        pass
    pathFolder = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"
    pathFolder.mkdir(parents=True, exist_ok=True)
    return pathFolder


def uniquePath(pathFolder, sName):
    """Return a path that does not yet exist, numbering duplicates as Windows does."""
    pathCandidate = pathFolder / sName
    if not pathCandidate.exists():
        return pathCandidate
    sStem = pathCandidate.stem
    sSuffix = pathCandidate.suffix
    for iCount in range(2, 1000):
        pathCandidate = pathFolder / f"{sStem} ({iCount}){sSuffix}"
        if not pathCandidate.exists():
            return pathCandidate
    return pathFolder / f"{sStem} ({os.getpid()}){sSuffix}"
