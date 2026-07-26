"""Open a document of any popular format by converting it to HTML first.

HomerView reads web pages very well, because a browser plus a screen reader is
already the most capable reading combination most people have. What it could not
do was open a Word file, a spreadsheet, a slide deck, or a PDF.

2htm closes that gap. It converts those formats to clean HTML using Microsoft's
own conversion engines, so the result keeps headings, lists, tables, and image
alternative text. HomerView runs it out of sight, writes the result to the
temporary folder, and opens that in the HomerView browser window, where every
HomerView command then works on it: heading navigation, the accessibility
report, the page explorer, Read All, Copy All, and the rest.

Where 2htm lives is a deliberate choice, and the answer is the HomerView
installation directory rather than the NVDA add-on folder.

An add-on folder is replaced wholesale whenever the add-on updates, so a half
megabyte binary would ride along with every update and every add-on backup.
Add-ons live under the roaming profile, which is user writable, and a growing
number of managed environments block execution from there outright. Program
Files is where Windows expects executables, is protected by its own permissions,
and is where 2htm's own installer already puts it. So HomerView looks for an
installed copy first and treats a bundled copy as the fallback, not the rule.
"""

import os
import subprocess
import winreg
from pathlib import Path

from . import paths
from .logger import abbreviate, homerLog, logSection

conversionTimeoutSeconds = 300.0
executableName = "2htm.exe"
pandocName = "pandoc.exe"

# Formats pandoc adds that 2htm does not cover. Pandoc is looked for, never
# bundled: it is well over a hundred megabytes, an add-on folder is replaced
# wholesale on every update, and it has its own installer that keeps itself
# current.
lPandocExtensions = [
    "adoc", "asciidoc", "dbk", "docbook", "fb2", "ipynb", "latex", "man",
    "mediawiki", "org", "rst", "tex", "textile", "wiki",
]
uninstallKey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

# Formats 2htm converts. Anything else is either opened directly by the browser
# or is not something this command can help with.
lConvertibleExtensions = [
    "csv", "doc", "docx", "epub", "md", "odp", "ods", "odt",
    "pdf", "ppt", "pptx", "rtf", "xls", "xlsx",
]

# Formats a browser already reads, which need no conversion at all.
lNativeExtensions = ["htm", "html", "mhtml", "svg", "txt", "xhtml", "xml"]

dSaveFormats = {
    "htm": "Web page, keeping headings, lists and tables",
    "md": "Markdown, plain text with structure preserved as punctuation",
    "txt": "Plain text, no structure",
}


class ConversionError(Exception):
    pass


def findExecutable():
    """Locate 2htm.exe: a shared Homer folder first, then an installed copy."""
    pathShared = paths.findSharedFile(executableName)
    if pathShared:
        homerLog.info(f"2htm found in a shared Homer folder at {pathShared}")
        return pathShared
    lCandidates = []
    for sVariable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        sRoot = os.environ.get(sVariable, "")
        if sRoot:
            lCandidates.append(Path(sRoot) / "HomerView" / executableName)
            lCandidates.append(Path(sRoot) / "2htm" / executableName)
    lCandidates.append(Path(r"C:\HomerView") / executableName)
    lCandidates.append(Path(r"C:\2htm") / executableName)
    # The add-on's own folder, last, for a portable install with no installer.
    lCandidates.append(Path(__file__).resolve().parents[2] / executableName)

    for pathCandidate in lCandidates:
        try:
            if pathCandidate.is_file():
                homerLog.info(f"2htm found at {pathCandidate}")
                return pathCandidate
        except OSError:
            continue
        homerLog.debug(f"2htm not at {pathCandidate}")

    pathRegistered = findRegisteredExecutable()
    if pathRegistered:
        return pathRegistered

    sPath = os.environ.get("PATH", "")
    for sFolder in sPath.split(os.pathsep):
        try:
            pathCandidate = Path(sFolder) / executableName
            if pathCandidate.is_file():
                homerLog.info(f"2htm found on the path at {pathCandidate}")
                return pathCandidate
        except OSError:
            continue
    homerLog.warning("2htm could not be found anywhere")
    return None


def findPandoc():
    """Locate pandoc: a bundled copy in a Homer program folder, or an installed one."""
    pathShared = paths.findSharedFile(pandocName)
    if pathShared:
        homerLog.info(f"Pandoc found in a shared Homer folder at {pathShared}")
        return pathShared
    lCandidates = []
    for sVariable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        sRoot = os.environ.get(sVariable, "")
        if sRoot:
            lCandidates.append(Path(sRoot) / "Pandoc" / pandocName)
            lCandidates.append(Path(sRoot) / "Homer" / pandocName)
    for pathCandidate in lCandidates:
        try:
            if pathCandidate.is_file():
                homerLog.info(f"Pandoc found at {pathCandidate}")
                return pathCandidate
        except OSError:
            continue
    for sFolder in os.environ.get("PATH", "").split(os.pathsep):
        try:
            pathCandidate = Path(sFolder) / pandocName
            if pathCandidate.is_file():
                homerLog.info(f"Pandoc found on the path at {pathCandidate}")
                return pathCandidate
        except OSError:
            continue
    homerLog.debug("Pandoc was not found; only the 2htm formats are available")
    return None


def convertWithPandoc(pathSource, pathFolder):
    """Convert a format pandoc knows and 2htm does not."""
    pathPandoc = findPandoc()
    if not pathPandoc:
        raise ConversionError(
            f"{pathSource.suffix} needs pandoc, which was not found. Install it from "
            "https://pandoc.org, or place pandoc.exe in the Homer program folder."
        )
    pathTarget = pathFolder / f"{pathSource.stem}.htm"
    lArguments = [
        str(pathPandoc), str(pathSource), "--standalone", "--to=html5",
        f"--metadata=title:{pathSource.stem}", "-o", str(pathTarget),
    ]
    homerLog.info(f"Running: {lArguments}")
    completed = subprocess.run(
        lArguments, capture_output=True, text=True,
        timeout=conversionTimeoutSeconds,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.stderr:
        homerLog.warning(f"Pandoc reported: {abbreviate(completed.stderr, 800)}")
    if not pathTarget.is_file():
        raise ConversionError(f"{pathSource.name} could not be converted by pandoc")
    homerLog.info(f"Pandoc wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget


def findRegisteredExecutable():
    """Look for an install location recorded by 2htm's own installer."""
    for iHive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(iHive, uninstallKey) as keyRoot:
                iCount = winreg.QueryInfoKey(keyRoot)[0]
                for iIndex in range(iCount):
                    sSubKey = winreg.EnumKey(keyRoot, iIndex)
                    if "2htm" not in sSubKey.lower():
                        continue
                    with winreg.OpenKey(keyRoot, sSubKey) as key:
                        sLocation = winreg.QueryValueEx(key, "InstallLocation")[0]
                    pathCandidate = Path(sLocation) / executableName
                    if pathCandidate.is_file():
                        homerLog.info(f"2htm found through the registry at {pathCandidate}")
                        return pathCandidate
        except OSError:
            continue
        except Exception:
            continue
    return None


def needsConversion(pathSource):
    sExtension = pathSource.suffix.lstrip(".").lower()
    if sExtension in lNativeExtensions:
        return False
    return True


def isConvertible(pathSource):
    sExtension = pathSource.suffix.lstrip(".").lower()
    return sExtension in lConvertibleExtensions


def convertToHtml(sSourcePath, bPlainText=False):
    """Convert a document and return the path of the file to open.

    The output keeps the source's root name and gains a .htm extension, and it
    goes to the temporary folder, which Windows clears on its own, because a
    converted copy is a way of reading something rather than a document in its
    own right.
    """
    logSection("Command: open another format")
    pathSource = Path(sSourcePath)
    if not pathSource.is_file():
        raise ConversionError(f"{pathSource.name} could not be found")

    if not needsConversion(pathSource):
        homerLog.info(f"{pathSource.name} needs no conversion; the browser reads it directly")
        return pathSource, False

    sExtension = pathSource.suffix.lstrip(".").lower()
    if sExtension in lPandocExtensions:
        logSection("Converting with pandoc")
        return convertWithPandoc(pathSource, paths.getTempFolder()), True

    if not isConvertible(pathSource):
        raise ConversionError(
            f"{pathSource.suffix or 'This file'} is not a format 2htm converts. "
            f"It handles {', '.join(lConvertibleExtensions)}."
        )

    pathExecutable = findExecutable()
    if not pathExecutable:
        raise ConversionError(
            "2htm was not found. Install it from https://github.com/JamalMazrui/2htm, "
            "or place 2htm.exe in the HomerView installation folder."
        )

    pathFolder = paths.getTempFolder()
    sExtension = "txt" if bPlainText else "htm"
    pathTarget = pathFolder / f"{pathSource.stem}.{sExtension}"
    try:
        if pathTarget.exists():
            pathTarget.unlink()
    except OSError:
        pass

    lArguments = [str(pathExecutable), str(pathSource), "-o", str(pathFolder), "-f"]
    if bPlainText:
        lArguments.append("-p")
    homerLog.info(f"Running: {lArguments}")
    try:
        completed = subprocess.run(
            lArguments,
            capture_output=True,
            text=True,
            timeout=conversionTimeoutSeconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise ConversionError(f"Converting {pathSource.name} took too long and was stopped")
    homerLog.info(f"2htm exit code {completed.returncode}")
    if completed.stdout:
        homerLog.debug(f"2htm said: {abbreviate(completed.stdout, 800)}")
    if completed.stderr:
        homerLog.warning(f"2htm reported: {abbreviate(completed.stderr, 800)}")

    if not pathTarget.is_file():
        raise ConversionError(
            f"{pathSource.name} could not be converted. "
            "Office documents need the matching Office program installed."
        )
    homerLog.info(f"Converted to {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget, True


def buildOpenWildcard():
    lAll = sorted(set(lConvertibleExtensions + lNativeExtensions + lPandocExtensions))
    sAll = ";".join(f"*.{s}" for s in lAll)
    sDocuments = ";".join(f"*.{s}" for s in sorted(lConvertibleExtensions))
    return (
        f"Readable files ({sAll})|{sAll}|"
        f"Documents ({sDocuments})|{sDocuments}|"
        "All files (*.*)|*.*"
    )
