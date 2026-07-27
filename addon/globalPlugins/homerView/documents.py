"""The Homer help trio: Help, About, and History of Changes.

Homer gives every program these three, on F1, Alt+F1 and Shift+F1, and the
consistency is the point: a user who knows one Homer program knows where to
find out about the next.

None of the three collides with anything in NVDA. F1 in Edge opens Microsoft's
own help site, which has nothing to say about HomerView, so replacing it inside
a HomerView page loses nothing and answers the question actually being asked.

Each is shown in NVDA's browseable message window, which can be read like a
document and searched, rather than spoken once and gone.
"""

import addonHandler

from . import output
import ui

from . import paths
from .logger import homerLog, logSection

addonHandler.initTranslation()

projectUrl = "https://github.com/JamalMazrui/HomerView"

# Each document ships as Markdown and as a web page. The web page is what gets
# opened, because it opens in the HomerView window where every HomerView command
# works on it, rather than in whichever program owns .md files.
lDocuments = [
    ("readMe", "README.htm", "README.md", "Quick start"),
    ("guide", "HomerView.htm", "HomerView.md", "User guide"),
    ("history", "History.htm", "History.md", "History of changes"),
    ("developer", "Developer.htm", "Developer.md", "Developer notes"),
]


def findInstalledDocument(sName):
    """Find a document beside the log, in the installation folder, or in the add-on."""
    import os
    from pathlib import Path

    from . import logger

    lFolders = []
    if logger.pathLogFile:
        lFolders.append(logger.pathLogFile.parent)
        lFolders.append(logger.pathLogFile.parent / "docs")
    for sVariable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        sRoot = os.environ.get(sVariable, "")
        if sRoot:
            lFolders.append(Path(sRoot) / "HomerView")
    lFolders.append(Path(__file__).resolve().parents[2])
    lFolders.append(Path(__file__).resolve().parents[2] / "doc" / "en")
    for pathFolder in lFolders:
        try:
            pathCandidate = pathFolder / sName
            if pathCandidate.is_file():
                homerLog.info(f"Document {sName} found at {pathCandidate}")
                return pathCandidate
        except OSError:
            continue
    homerLog.warning(f"Document {sName} was not found in {len(lFolders)} folders")
    return None


def openDocument(sKey):
    """Open one of the shipped documents in the HomerView window.

    Opening it as a file rather than handing it to the shell matters: the shell
    would give a .htm file to whichever browser is the default, which is not
    HomerView and may not even be Edge. Opening it through the protocol puts it
    in the HomerView window, where the reader has every HomerView command.
    """
    from .service import service

    for sName, sHtm, sMarkdown, sTitle in lDocuments:
        if sName != sKey:
            continue
        pathDocument = findInstalledDocument(sHtm) or findInstalledDocument(sMarkdown)
        if not pathDocument:
            # Translators: Reported when a shipped document could not be found.
            ui.message(_("{title} was not found. It is in the project at {url}").format(
                title=sTitle, url=projectUrl))
            return
        if not service.isConnected():
            # Translators: Reported when the browser is not running.
            ui.message(_("Press Alt+NVDA+H first, so the document opens in HomerView"))
            return
        homerLog.info(f"Opening {sTitle} at {pathDocument}")
        service.openReportPage(pathDocument.as_uri())
        # Translators: Reported when a document is opened.
        ui.message(_("{title} opened").format(title=sTitle))
        return


def readVersion():
    from . import logger

    return logger.readAddonVersion()


def buildAboutText():
    """About as plain lines, for a dialog rather than a page.

    Output has more than one right shape. A report is a document: long, worth
    keeping, worth searching, so a page in the browser is right. About is a
    short set of facts someone wants now and then closes, so a dialog is right.
    Putting the second in the first made a reader open a tab to learn a version
    number and then have to close it.
    """
    from . import convert
    from . import logger
    from . import paths as pathsModule
    from .history import history as historyStore
    from .service import service

    dStore = historyStore.describe()
    lLines = [
        f"HomerView {readVersion()}",
        "",
        "An NVDA add-on that drives its own instance of Microsoft Edge through the",
        "Chrome DevTools Protocol, so a browser and a document reader answer to the",
        "same commands.",
        "",
        "Files",
        f"  Session log: {logger.pathLogFile}",
        f"  Generated documents: {pathsModule.getTempFolder()}",
        f"  Downloads: {pathsModule.getDownloadsFolder()}",
        f"  History: {dStore.get('path', '')} ({dStore.get('backend', '')})",
        f"  Document converter: {convert.findExecutable() or 'not found'}",
        f"  Pandoc: {convert.findPandoc() or 'not found'}",
        "",
        "Connection",
    ]
    if service.isConnected():
        lLines.append(f"  Connected on port {service.iPort}")
        lLines.append(f"  Browser process: {sorted(service.setProcessIds)}")
    else:
        lLines.append("  Not connected. Press Alt+NVDA+H to start HomerView Edge.")
    lLines.extend(["", f"Project: {projectUrl}",
                   "Press Alt+F10 for every command, or Alt+Shift+H for the same list as a page."])
    return "\n".join(lLines)


def buildAbout():
    from . import convert
    from .history import history as historyStore
    from . import logger
    from .service import service

    pathExecutable = convert.findExecutable()
    dStore = historyStore.describe()
    lParts = [f"<h1>HomerView {escape(readVersion())}</h1>"]
    lParts.append(
        "<p>An NVDA add-on that drives its own instance of Microsoft Edge through the "
        "Chrome DevTools Protocol, so a screen reader user gets a browser and a document "
        "reader that answer to the same commands.</p>"
    )
    lParts.append("<h2>Where its files are</h2><ul>")
    lParts.append(f"<li>Session log: <code>{escape(logger.pathLogFile)}</code></li>")
    lParts.append(f"<li>Generated documents: <code>{escape(paths.getTempFolder())}</code></li>")
    lParts.append(f"<li>Downloads: <code>{escape(paths.getDownloadsFolder())}</code></li>")
    lParts.append(
        f"<li>History: <code>{escape(dStore.get('path', ''))}</code>, "
        f"using {escape(dStore.get('backend', ''))}</li>"
    )
    lParts.append(
        f"<li>Document converter: <code>{escape(pathExecutable or 'not found')}</code></li>"
    )
    lParts.append("</ul>")
    lParts.append("<h2>What it is connected to</h2><ul>")
    if service.isConnected():
        lParts.append(f"<li>Connected on port {service.iPort}</li>")
        lParts.append(f"<li>Browser process: {sorted(service.setProcessIds)}</li>")
    else:
        lParts.append("<li>Not connected. Press Alt+NVDA+H to start HomerView Edge.</li>")
    lParts.append("</ul>")
    lParts.append(
        f'<h2>More</h2><p><a href="{projectUrl}">{projectUrl}</a></p>'
        "<p>Press Alt+F10 for every command, or Alt+Shift+H for the same list as a document.</p>"
    )
    return "\n".join(lParts)


def escape(vValue):
    import html

    return html.escape(str(vValue if vValue is not None else ""), quote=True)


def findDocument(lNames):
    """Look for a document beside the log, then in the add-on's own folder."""
    from pathlib import Path

    from . import logger

    lFolders = []
    if logger.pathLogFile:
        lFolders.append(logger.pathLogFile.parent)
        lFolders.append(logger.pathLogFile.parent / "docs")
    lFolders.append(Path(__file__).resolve().parents[2])
    lFolders.append(Path(__file__).resolve().parents[2] / "doc" / "en")
    for pathFolder in lFolders:
        for sName in lNames:
            try:
                pathCandidate = pathFolder / sName
                if pathCandidate.is_file():
                    homerLog.info(f"Found {sName} at {pathCandidate}")
                    return pathCandidate
            except OSError:
                continue
    homerLog.warning(f"None of {lNames} could be found")
    return None


def renderMarkdown(sText):
    """A deliberately small Markdown rendering, enough for these documents."""
    lParts = []
    bList = False
    for sLine in sText.splitlines():
        sStripped = sLine.strip()
        if sStripped.startswith("#"):
            iLevel = min(6, len(sStripped) - len(sStripped.lstrip("#")))
            if bList:
                lParts.append("</ul>")
                bList = False
            lParts.append(f"<h{iLevel}>{escape(sStripped.lstrip('# ').strip())}</h{iLevel}>")
        elif sStripped.startswith(("- ", "* ")):
            if not bList:
                lParts.append("<ul>")
                bList = True
            lParts.append(f"<li>{escape(sStripped[2:])}</li>")
        elif not sStripped:
            if bList:
                lParts.append("</ul>")
                bList = False
        else:
            if bList:
                lParts.append("</ul>")
                bList = False
            lParts.append(f"<p>{escape(sStripped)}</p>")
    if bList:
        lParts.append("</ul>")
    return "\n".join(lParts)


def show(sWhich):
    logSection(f"Command: show {sWhich}")
    if sWhich == "about":
        from .homer import lbc

        # Translators: Title of the About dialog.
        lbc.dialogInfo(_("About HomerView"), buildAboutText())
        return
    elif sWhich == "history":
        pathDocument = findDocument(["History.md", "CHANGELOG.md"])
        sHtml = (
            renderMarkdown(pathDocument.read_text(encoding="utf-8-sig", errors="replace"))
            if pathDocument
            else "<h1>History of changes</h1><p>CHANGELOG.md was not found. "
                 f'It is in the project at <a href="{projectUrl}">{projectUrl}</a>.</p>'
        )
        # Translators: Title of the history of changes window.
        sTitle = _("HomerView history of changes")
    else:
        pathDocument = findDocument(["HomerView_User_Guide.md", "README.md"])
        sHtml = (
            renderMarkdown(pathDocument.read_text(encoding="utf-8-sig", errors="replace"))
            if pathDocument
            else "<h1>HomerView help</h1><p>The user guide was not found. Press Alt+F10 "
                 "for every command, or Alt+Shift+H for the same list as a document.</p>"
        )
        # Translators: Title of the help window.
        sTitle = _("HomerView help")
    import wx

    wx.CallAfter(_browseable, sHtml, sTitle)


def _browseable(sHtml, sTitle):
    output.show(sHtml, sTitle)
