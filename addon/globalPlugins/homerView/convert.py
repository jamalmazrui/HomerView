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
import time
import winreg
from pathlib import Path

from . import paths
from .logger import abbreviate, homerLog, logError, logSection

# HOW LONG TO WAIT FOR A CONVERTER, SCALED TO THE FILE.
#
# This was a flat five minutes, which is far past the point where a reader
# concludes the program has hung: they hear "Converting", then silence, and the
# silence is the whole problem. A flat short timeout is no better, since a large
# PDF genuinely takes a while.
#
# So it scales: a base, plus an allowance for each megabyte, with a ceiling. A
# 200 kilobyte document fails fast; a two megabyte PDF gets forty seconds;
# nothing waits past a minute. The same numbers as the JAWS side, so the two
# give up at the same moment on the same file.
conversionBaseSeconds = 18.0
conversionSecondsPerMegabyte = 11.0
conversionCeilingSeconds = 60.0


def conversionBudget(pathSource):
    """Seconds to allow this file, by its size."""
    try:
        iBytes = pathSource.stat().st_size
    except Exception:
        iBytes = 0
    nSeconds = conversionBaseSeconds + (iBytes // (1024 * 1024)) * conversionSecondsPerMegabyte
    return min(nSeconds, conversionCeilingSeconds)
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
            "cannot be done."
        )
    if sPlatform and sPlatform.lower() != "x64":
        return False, (
            f"Microsoft Office is installed but reports itself as {sPlatform}, while 2htm "
            "needs the 64 bit edition. A 64 bit Office would let HomerView open this format."
        )
    return True, ""


def writtenSince(pathTarget, nStarted):
    """Whether the file exists and was written at or after nStarted, a time.time() value: made by this attempt, not
    left by an earlier one. WHY (8 October 2026, from an audit by another AI): success was the target's existence alone,
    so a failed conversion of a document converted before "succeeded" by finding the old file."""
    try:
        return pathTarget.is_file() and pathTarget.stat().st_mtime >= nStarted - 2
    except OSError:
        return False


def runConverter(lArguments, pathTarget, sTool, nBudget=conversionCeilingSeconds):
    """Run a converter, bounded. The budget comes from the caller, which knows
    the source file; this function only sees the argument list."""
    homerLog.info(f"Running {sTool} with {nBudget:.0f} seconds: {lArguments}")
    nStarted = time.time()
    try:
        completed = subprocess.run(
            lArguments, capture_output=True, text=True,
            timeout=nBudget,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise ConversionError(f"{sTool} took too long and was stopped")
    homerLog.info(f"{sTool} exit code {completed.returncode}")
    if completed.stdout:
        homerLog.debug(f"{sTool} said: {abbreviate(completed.stdout, 600)}")
    if completed.stderr:
        homerLog.warning(f"{sTool} reported: {abbreviate(completed.stderr, 600)}")
    return completed.returncode == 0 and writtenSince(pathTarget, nStarted)


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


def needsConversion(pathSource):
    sExtension = pathSource.suffix.lstrip(".").lower()
    if sExtension in lNativeExtensions:
        return False
    return True


def isConvertible(pathSource):
    from .homer import conversion as kitConversion
    return kitConversion.canConvert(str(pathSource), "htm")


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

    # THROUGH THE HOMER KIT'S ONE CONVERSION (22 October 2026), as every Homer app converts: the kit's
    # conversion.py, carried in the homer package, picks the way from conversions.inix -- Pandoc, Office,
    # its own readers -- where HomerView ran 2htm.exe or Pandoc itself. A type the kit cannot convert is
    # opened in the browser, as before.
    from .homer import conversion as kitConversion
    sExtension = "txt" if bPlainText else "htm"
    if not kitConversion.canConvert(str(pathSource), sExtension):
        homerLog.info(
            f"{pathSource.suffix or 'This file'} has no conversion in the Homer kit, so it is opened "
            "in the browser as the native command would"
        )
        return pathSource, False
    # A FOLDER OF ITS OWN FOR EACH SOURCE (30 October 2026, from an audit by another AI). Every converted
    # document went to the temporary folder under its own stem, so A\report.docx and B\report.docx shared one
    # address: a tab showing the first could reload as the second, and the second's conversion deleted the first's
    # file first. Each source now has a folder named for its full path, so the address stays its own; the file
    # keeps the source's name, so the page title and the tab still read as the document. The old file is not
    # deleted first: the kit replaces it only with a whole new one.
    import hashlib
    sKey = hashlib.sha1(str(pathSource.resolve()).lower().encode("utf-8")).hexdigest()[:12]
    pathFolder = paths.getTempFolder() / sKey
    pathFolder.mkdir(parents=True, exist_ok=True)
    pathTarget = pathFolder / f"{pathSource.stem}.{sExtension}"
    logSection("Converting through the Homer kit")
    try:
        dDone = kitConversion.convert(str(pathSource), str(pathTarget))
    except Exception as oError:
        raise ConversionError(f"{pathSource.name} could not be converted: {oError}")
    if not pathTarget.is_file():
        raise ConversionError(f"{pathSource.name} could not be converted.")
    homerLog.info(f"Converted to {pathTarget} by {dDone.get('route', '?')}, {pathTarget.stat().st_size} bytes")
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
