"""List the people, places, organisations and dates a page mentions.

The engine is compromise, a rule-based English parser that carries no model and
makes no network call once fetched. It arrives the same way axe-core does:
fetched from a content delivery network, cached for the session, and injected as
source text through Runtime.evaluate, which runs in the page's own context
through the debugger so a content security policy never applies.

IT GUESSES, AND THE REPORT SAYS SO. A rule-based tagger will call a company a
person and will miss a name it has not seen before. Presented as fact that would
be worse than useless. Presented as a starting point it is a way of reading a
page that no screen reader offers: every name in a long report, every date on a
page of deadlines, in a list you can move through.

Tags rather than methods (#Person+ rather than .people()) because the tag names
have been stable across compromise's major versions and the method set has not.
"""

import urllib.request
from datetime import datetime

from .logger import abbreviate, homerLog, logSection
from . import paths

namesFileName = "Names.htm"
nlpFetchTimeoutSeconds = 30.0
nlpRunTimeoutSeconds = 60.0
# jsdelivr first: unpkg answered 404 for this exact path on 15 August 2026 while
# jsdelivr served it, so the order reflects what was observed rather than habit.
lNlpCdnUrls = [
    "https://cdn.jsdelivr.net/npm/compromise@14/builds/compromise.min.js",
    "https://unpkg.com/compromise@latest/builds/compromise.min.js",
    "https://unpkg.com/compromise@14/builds/compromise.min.js",
]
# The page's text is capped: this is a parser running inside the page, and a
# very long document would hold the browser for seconds.
maximumCharacters = 200000
lGroups = [
    ("#Person+", "People"),
    ("#Place+", "Places"),
    ("#Organization+", "Organisations"),
    ("#Date+", "Dates"),
    ("#Money+", "Amounts of money"),
    ("#Percent+", "Percentages"),
]

dCachedScript = {}


class NamesError(Exception):
    """Raised when the page cannot be read for names."""


def fetchText(sUrl):
    """Fetch one url as text."""
    oRequest = urllib.request.Request(sUrl, headers={"User-Agent": "HomerView"})
    with urllib.request.urlopen(oRequest, timeout=nlpFetchTimeoutSeconds) as oResponse:
        return oResponse.read().decode("utf-8", "replace")


def getNlpScript():
    """Return the compromise source, fetching it once per session."""
    if dCachedScript.get("source"):
        homerLog.debug(f"Reusing the compromise source from {dCachedScript.get('url')}")
        return dCachedScript["source"], dCachedScript["url"]
    lFailures = []
    for sUrl in lNlpCdnUrls:
        homerLog.info(f"Fetching compromise from {sUrl}")
        try:
            sSource = fetchText(sUrl)
        except Exception as exception:
            homerLog.warning(f"Could not fetch compromise from {sUrl}: {exception}")
            lFailures.append(f"{sUrl}: {exception}")
            continue
        dCachedScript["source"] = sSource
        dCachedScript["url"] = sUrl
        homerLog.info(f"Fetched compromise, {len(sSource)} characters, from {sUrl}")
        return sSource, sUrl
    raise NamesError("The language engine could not be downloaded. " + "; ".join(lFailures))


def buildExpression():
    """The reducer that runs in the page and returns one line per group."""
    sTags = ", ".join(f'"{sTag}"' for sTag, _sHeading in lGroups)
    return (
        "(() => {"
        f" const sText = (document.body ? document.body.innerText : '').slice(0, {maximumCharacters});"
        " if (!sText.trim()) return '';"
        " const oDoc = nlp(sText);"
        " const gather = (sTag) => {"
        "   const lSeen = [];"
        "   for (const sOne of oDoc.match(sTag).out('array')) {"
        "     const sClean = String(sOne).replace(/\\s+/g, ' ').trim()"
        "       .replace(/^[^\\w(]+|[^\\w)]+$/g, '');"
        "     if (sClean.length < 2 || sClean.length > 80) continue;"
        "     if (lSeen.indexOf(sClean) < 0) lSeen.push(sClean);"
        "     if (lSeen.length > 300) break;"
        "   }"
        "   return lSeen.join('\\u0001');"
        " };"
        f" return [{sTags}].map(gather).join('\\u0002');"
        "})()"
    )


def escapeHtml(sValue):
    return (
        str(sValue)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def buildHtml(sPageTitle, sPageUrl, lFound):
    """The report, which says on its own first page that it guesses."""
    lOut = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>Names on {escapeHtml(sPageTitle)}</title>",
        "</head>",
        "<body>",
        "<h1>What this page mentions</h1>",
        "<ul>",
        f"<li>Page: {escapeHtml(sPageTitle)}</li>",
        f'<li>Address: <a href="{escapeHtml(sPageUrl)}">{escapeHtml(sPageUrl)}</a></li>',
        f"<li>Read: {datetime.now().strftime('%Y-%m-%d %H:%M')}</li>",
        "</ul>",
        "<p>These were found by a rule-based language engine reading the page's "
        "text. It guesses. Expect a company called a person now and then, and "
        "expect it to miss a name it has not seen before. It is a starting point "
        "rather than an index.</p>",
    ]
    for (_sTag, sHeading), lItems in zip(lGroups, lFound):
        if not lItems:
            continue
        lOut.append(f"<h2>{sHeading} ({len(lItems)})</h2>")
        lOut.append("<ul>")
        lOut += [f"<li>{escapeHtml(sItem)}</li>" for sItem in lItems]
        lOut.append("</ul>")
    lOut += ["</body>", "</html>", ""]
    return "\r\n".join(lOut)


def listNames(cdpSession):
    """Read the focused page for names, save Names.htm, and say what was found."""
    logSection("Command: list names")
    sSource, sSourceUrl = getNlpScript()
    dTarget, sSessionId = cdpSession.findActivePageSession()
    sPageUrl = dTarget.get("url", "")
    sPageTitle = dTarget.get("title", "") or sPageUrl
    homerLog.info(f"Reading {abbreviate(sPageTitle, 120)} for names")

    cdpSession.evaluate(sSessionId, sSource)
    if not cdpSession.evaluate(sSessionId, "Boolean(window.nlp)"):
        raise NamesError("The language engine did not load into the page")

    sFound = cdpSession.evaluate(sSessionId, buildExpression(), nlpRunTimeoutSeconds)
    if not sFound:
        raise NamesError("This page has no text to read")

    lFound = []
    for sGroup in str(sFound).split("\u0002"):
        lFound.append([s for s in sGroup.split("\u0001") if s] if sGroup else [])
    iTotal = sum(len(l) for l in lFound)
    if iTotal == 0:
        raise NamesError("No names, places or dates were found on this page")
    homerLog.info(
        "Found "
        + ", ".join(
            f"{len(lItems)} {sHeading.lower()}"
            for (_sTag, sHeading), lItems in zip(lGroups, lFound)
            if lItems
        )
    )

    pathFolder = paths.pageFolder(sPageTitle)
    pathNames = pathFolder / namesFileName
    pathNames.write_text(
        buildHtml(sPageTitle, sPageUrl, lFound), encoding="utf-8"
    )
    homerLog.info(f"Saved {pathNames}, {pathNames.stat().st_size} bytes")

    return {
        "counts": {
            sHeading: len(lItems)
            for (_sTag, sHeading), lItems in zip(lGroups, lFound)
            if lItems
        },
        "folder": str(pathFolder),
        "path": str(pathNames),
        "pageTitle": sPageTitle,
        "pageUrl": sPageUrl,
        "sourceUrl": sSourceUrl,
        "total": iTotal,
    }
