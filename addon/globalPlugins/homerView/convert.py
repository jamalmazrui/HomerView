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
from .logger import abbreviate, homerLog, logError, logSection

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
    "mhtml": "The page and everything it uses, in one file, as Edge saves it",
    "htm": "Web page, keeping headings, lists and tables",
    "md": "Markdown, plain text with structure preserved as punctuation",
    "txt": "Plain text, no structure",
    "dom.htm": "The markup after script has run, not what the server sent",
    "pdf": "The page as it would print, fixed layout, one file",
    "png": "Image of the whole page, as a sighted reader sees it",
    "json": "The accessibility tree, with the reasons any node was ignored",
    "docx": "A Word document, made from the page by pandoc",
}


# Which tool converts what, best first. Nothing is bundled: each is looked for,
# and a format with no tool present says which one to install.
#
# 2htm comes last for everything it is not alone in handling, because it drives
# Microsoft Office through COM and therefore needs Office installed and of the
# same bitness. The others need nothing but themselves.
dConverterChain = {
    "doc": ["libreOffice", "2htm"],
    "docx": ["libreOffice", "pandoc", "2htm"],
    "epub": ["pandoc", "calibre"],
    "md": ["pandoc", "2htm"],
    "odp": ["libreOffice"],
    "ods": ["libreOffice"],
    "odt": ["libreOffice", "pandoc"],
    "pdf": ["2htm", "libreOffice"],
    "ppt": ["libreOffice", "2htm"],
    "pptx": ["libreOffice", "2htm"],
    "rtf": ["libreOffice", "pandoc", "2htm"],
    "xls": ["libreOffice", "2htm"],
    "xlsx": ["libreOffice", "2htm"],
    "csv": ["libreOffice", "2htm"],
}

officeConfigurationKey = r"SOFTWARE\Microsoft\Office\ClickToRun\Configuration"


class ConversionError(Exception):
    pass


def hasOfficeCom():
    """Say whether 2htm's conversions can work, and why not when they cannot.

    2htm drives Microsoft Word, Excel and PowerPoint through COM, so it needs
    Office installed. Reporting this before running it turns a silent failure
    into a sentence the user can act on.
    """
    bWord = False
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CurVer"):
            bWord = True
    except OSError:
        bWord = False
    sPlatform = ""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, officeConfigurationKey) as key:
            sPlatform = winreg.QueryValueEx(key, "Platform")[0]
    except OSError:
        sPlatform = ""
    homerLog.info(f"Office COM: Word registered={bWord}, platform={sPlatform or 'unknown'}")
    if not bWord:
        return False, (
            "This format is converted by 2htm, which works through Microsoft Office. "
            "Office does not appear to be installed on this computer, so the conversion "
            "cannot be done. Installing LibreOffice, which needs no Office and is free, "
            "would let HomerView open this format instead."
        )
    if sPlatform and sPlatform.lower() != "x64":
        return False, (
            f"Microsoft Office is installed but reports itself as {sPlatform}, while 2htm "
            "needs the 64 bit edition. A 64 bit Office, or LibreOffice, would let HomerView "
            "open this format."
        )
    return True, ""


def findLibreOffice():
    """soffice.exe converts every office format and needs no Office installed."""
    pathShared = paths.findSharedFile("soffice.exe")
    if pathShared:
        return pathShared
    for sVariable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        sRoot = os.environ.get(sVariable, "")
        if not sRoot:
            continue
        for sFolder in ("LibreOffice", "LibreOffice 26", "LibreOffice 25"):
            pathCandidate = Path(sRoot) / sFolder / "program" / "soffice.exe"
            try:
                if pathCandidate.is_file():
                    homerLog.info(f"LibreOffice found at {pathCandidate}")
                    return pathCandidate
            except OSError:
                continue
    homerLog.debug("LibreOffice was not found")
    return None


def findCalibre():
    """ebook-convert.exe is calibre's converter, good for ebook formats."""
    pathShared = paths.findSharedFile("ebook-convert.exe")
    if pathShared:
        return pathShared
    for sVariable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        sRoot = os.environ.get(sVariable, "")
        if sRoot:
            pathCandidate = Path(sRoot) / "Calibre2" / "ebook-convert.exe"
            try:
                if pathCandidate.is_file():
                    homerLog.info(f"Calibre found at {pathCandidate}")
                    return pathCandidate
            except OSError:
                continue
    for sFolder in os.environ.get("PATH", "").split(os.pathsep):
        try:
            pathCandidate = Path(sFolder) / "ebook-convert.exe"
            if pathCandidate.is_file():
                return pathCandidate
        except OSError:
            continue
    homerLog.debug("Calibre was not found")
    return None


def runConverter(lArguments, pathTarget, sTool):
    homerLog.info(f"Running {sTool}: {lArguments}")
    try:
        completed = subprocess.run(
            lArguments, capture_output=True, text=True,
            timeout=conversionTimeoutSeconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise ConversionError(f"{sTool} took too long and was stopped")
    homerLog.info(f"{sTool} exit code {completed.returncode}")
    if completed.stdout:
        homerLog.debug(f"{sTool} said: {abbreviate(completed.stdout, 600)}")
    if completed.stderr:
        homerLog.warning(f"{sTool} reported: {abbreviate(completed.stderr, 600)}")
    return pathTarget.is_file()


def convertWithLibreOffice(pathSource, pathFolder):
    pathExecutable = findLibreOffice()
    if not pathExecutable:
        return None
    pathTarget = pathFolder / f"{pathSource.stem}.html"
    lArguments = [
        str(pathExecutable), "--headless", "--norestore", "--convert-to", "html",
        "--outdir", str(pathFolder), str(pathSource),
    ]
    if runConverter(lArguments, pathTarget, "LibreOffice"):
        # This project writes .htm rather than .html.
        pathFinal = pathFolder / f"{pathSource.stem}.htm"
        try:
            if pathFinal.exists():
                pathFinal.unlink()
            pathTarget.rename(pathFinal)
        except OSError:
            pathFinal = pathTarget
        homerLog.info(f"LibreOffice wrote {pathFinal}")
        return pathFinal
    return None


def convertWithCalibre(pathSource, pathFolder):
    pathExecutable = findCalibre()
    if not pathExecutable:
        return None
    pathTarget = pathFolder / f"{pathSource.stem}.htmlz"
    if runConverter([str(pathExecutable), str(pathSource), str(pathTarget)], pathTarget, "Calibre"):
        homerLog.info(f"Calibre wrote {pathTarget}")
        return pathTarget
    return None


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
        # Everything else goes straight to the browser, which is what the
        # native Control+O does with it. Images, audio, video, JSON, source
        # files and anything Edge renders open exactly as they would have;
        # anything it cannot render, it offers to download, also as before.
        # This is what makes taking Control+O honest: nothing that worked
        # before stops working.
        homerLog.info(
            f"{pathSource.suffix or 'This file'} has no converter, so it is opened "
            "in the browser as the native command would"
        )
        return pathSource, False

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
