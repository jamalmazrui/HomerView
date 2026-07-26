"""Where a report goes: a real page by default, the browseable window otherwise.

NVDA's browseable message is the obvious place to put a report and the wrong
one for most of them. It is a dead end. Control+S does nothing, because it is
not a browser. None of HomerView's own commands reach it, so a report cannot be
searched with Control+F, read with Alt+F8, saved with Control+F12, or scanned
for its main content. And focus does not reliably land at the top, so the reader
has to go looking for output they just asked for.

A temporary web page opened in the HomerView window has none of those problems.
It is an ordinary document: every HomerView command works on it, the browser's
own Control+S works, it can be kept, printed, or sent, and NVDA announces it the
way it announces any page, with the cursor at the beginning.

So a page is the default. The browseable window remains for the case where
there is no browser to put a page in, which is mainly before HomerView Edge has
been launched, and for anyone who prefers it.

Set bPreferTemporaryPage to False to use the browseable window throughout.
"""

import re

import addonHandler
import ui

from . import paths
from .logger import homerLog, logError

addonHandler.initTranslation()

bPreferTemporaryPage = True

pageStyle = """
body { font-family: Segoe UI, Arial, sans-serif; line-height: 1.5; margin: 0 auto;
       max-width: 60em; padding: 1em; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #999; padding: 0.3em 0.5em; text-align: left; }
pre { background: #f4f4f4; overflow-x: auto; padding: 1em; white-space: pre-wrap; }
code { background: #f4f4f4; padding: 0 0.2em; }
"""


def safeName(sName):
    sName = re.sub(r'[\\/*?:"<>|]', "_", str(sName or "Report"))
    return " ".join(sName.split())[:60] or "Report"


def wrapDocument(sHtml, sTitle):
    """Make a fragment into a document a browser and a reader can both use."""
    if sHtml.lstrip().lower().startswith("<!doctype"):
        return sHtml
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{sTitle}</title>\n"
        f"<style>{pageStyle}</style>\n"
        "</head>\n<body>\n<main>\n"
        + sHtml
        + "\n</main>\n</body>\n</html>\n"
    )


def showBrowseable(sHtml, sTitle):
    """The fallback. Kept because it works with no browser running."""
    try:
        ui.browseableMessage(sHtml, sTitle, True)
    except TypeError:
        ui.browseableMessage(sHtml, title=sTitle, isHtml=True)
    return "browseable"


def info(sTitle, sMessage):
    """Short facts, in a box Control+C can copy whole.

    Three shapes, three jobs. Speech for something heard once and discarded. A
    message box for a short set of facts worth copying. A page for anything
    long enough to search, save, or send. Using the wrong one wastes the
    reader's time in a different way each time.
    """
    from .homer import lbc

    homerLog.info(f"Information: {sTitle}")
    lbc.afterScript(lbc.dialogInfo, sTitle, sMessage)


def show(sHtml, sTitle, sFileName=""):
    """Put a report where the reader can actually work with it.

    Returns which route was taken, so the log records it and a reader who
    expected a tab and got a window can see why.
    """
    from .service import service

    if not bPreferTemporaryPage:
        homerLog.info(f"Report {sTitle}: browseable window, by preference")
        return showBrowseable(sHtml, sTitle)
    if not service.isConnected():
        homerLog.info(f"Report {sTitle}: browseable window, because Edge is not running")
        return showBrowseable(sHtml, sTitle)
    try:
        pathTarget = paths.getTempFolder() / f"{safeName(sFileName or sTitle)}.htm"
        # UTF-8 with a byte order mark and Windows line endings, as every other
        # document this project writes.
        pathTarget.write_text(wrapDocument(sHtml, sTitle), encoding="utf-8-sig", newline="\r\n")
        homerLog.info(f"Report {sTitle}: wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
        service.openReportPage(pathTarget.as_uri())
        return "page"
    except Exception:
        logError(f"Report {sTitle} could not be opened as a page; using the window instead")
        return showBrowseable(sHtml, sTitle)
