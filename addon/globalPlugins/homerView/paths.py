"""Where HomerView puts the files it makes.

Generated pages are working documents rather than records. They belong in the
temporary folder, which Windows and Storage Sense clear on their own, so a long
session does not slowly fill a program folder with old reports. The names inside
are stable rather than random, so a file can be found again while it still
exists.

Downloads belong wherever the user's downloads already go, which is a known
folder and not always under the profile.
"""

from urllib.parse import unquote
import os
import re
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


def getDataFolder():
    """Where this machine's HomerView data lives.

    Local application data, which is per user and per machine and is not copied
    between computers. Logs, the history database and anything else that grows
    or is meaningful only here.
    """
    sRoot = os.environ.get("LOCALAPPDATA", "")
    pathFolder = Path(sRoot) / "HomerView" if sRoot else Path.home() / "HomerView"
    try:
        pathFolder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return pathFolder


def getSettingsFolder():
    """Where this user's HomerView preferences live.

    Roaming application data, which follows the user to another computer in a
    domain. Preferences belong to the person rather than the machine, and they
    are small, which is what roaming requires.
    """
    sRoot = os.environ.get("APPDATA", "")
    pathFolder = Path(sRoot) / "HomerView" if sRoot else Path.home() / "HomerView"
    try:
        pathFolder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return pathFolder


def getTempFolder():
    """Return a HomerView folder inside the user's temporary folder."""
    pathFolder = Path(tempfile.gettempdir()) / tempFolderName
    pathFolder.mkdir(parents=True, exist_ok=True)
    return pathFolder


setReservedNames = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


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
    """Return where a file goes. It REPLACES whatever is already there.

    This used to number duplicates as the other Homer tools do -- name (2),
    name (3). HomerView deliberately does not any more. The folder is named
    after the page, so a second run on the same page re-fetches the same
    things, and a folder filling with numbered copies of one report is worse
    than a folder holding the current one. The name is kept for the callers.
    """
    return pathFolder / sName


def safeStem(sTitle, sFallback="report"):
    """A page title turned into a name Windows will accept.

    Ported from urlFido's folderNameFromTitle so that both halves of HomerView
    name a folder identically. Two rules matter and are easy to miss: a
    trailing dot or space is illegal at the end of a Windows name, and a
    reserved device name -- CON, PRN, AUX, NUL, COM1 to COM9, LPT1 to LPT9 --
    cannot be a file or folder at all.

    Percent escapes are undone first. "%20" is read aloud as "percent two
    zero", over and over, which is tedious with a screen reader. Three passes,
    because doubly-escaped names turn up on real sites.
    """
    sName = (sTitle or "").strip()
    for _iPass in range(3):
        if "%" not in sName:
            break
        try:
            sNext = unquote(sName)
        except Exception:
            break
        if sNext == sName:
            break
        sName = sNext
    sName = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", sName)
    sName = re.sub(r"\s+", " ", sName).strip().rstrip(". ")
    if sName.split(".")[0].upper() in setReservedNames:
        sName = "_" + sName
    sName = sName[:70].rstrip(". ")
    return sName or sFallback


def pageFolder(sPageTitle):
    """The one folder for this page, shared by everything the page produces.

    Downloads, both accessibility reports and the extracted article all live
    here, each under its own name -- Axe.htm, IBM.htm, Main.htm. The folder is
    KEPT between runs and each tool replaces its own files, because emptying a
    folder that also holds downloads destroys them.
    """
    pathFolder = getDownloadsFolder() / safeStem(sPageTitle)
    pathFolder.mkdir(parents=True, exist_ok=True)
    return pathFolder
