"""Extract the readable part of a page and save it as a plain HTML document.

This is the job mainly.py and mainer.py did, moved into the browser.

Those scripts fetched the raw markup and ran a readability library over it in
Python. Fetching raw markup is the weak point: on any page built by script, the
markup that arrives from the server is a shell, and the article the reader wants
does not exist in it. HomerView already has the live document through the
protocol, after script has run, so the extraction happens on what is actually on
screen.

The engine is Mozilla's Readability, the same algorithm behind Firefox's reader
view and behind the readability packages those scripts imported. It is fetched
from a content delivery network once per session and injected the way axe-core
is, so nothing has to be installed.

When the network is unavailable there is a small fallback that picks the main
landmark, then an article element, then whichever container holds the most
paragraph text. It is cruder, and the result says which method was used.
"""

import re
import urllib.request

from . import paths
from .logger import abbreviate, homerLog, logSection

extractTimeoutSeconds = 60.0
fetchTimeoutSeconds = 30.0
mainContentFileName = "MainContent.htm"
userAgent = "HomerView (+NVDA add-on)"

lReadabilityCdnUrls = [
    "https://cdn.jsdelivr.net/npm/@mozilla/readability@0.5.0/Readability.js",
    "https://unpkg.com/@mozilla/readability@0.5.0/Readability.js",
]

dCachedScript = {}

# Runs after Readability has been injected. The algorithm mutates the document
# it is given, so it is handed a clone and the live page is left alone.
readabilityScript = r"""(() => {
    if (typeof Readability === "undefined") return null;
    try {
        const documentClone = document.cloneNode(true);
        const dArticle = new Readability(documentClone).parse();
        if (!dArticle || !dArticle.content) return null;
        return {
            byline: dArticle.byline || "",
            content: dArticle.content,
            excerpt: dArticle.excerpt || "",
            length: dArticle.length || 0,
            method: "Readability",
            siteName: dArticle.siteName || "",
            title: dArticle.title || document.title || ""
        };
    } catch (error) {
        return null;
    }
})()"""

# Used only when Readability could not be fetched.
fallbackScript = r"""(() => {
    const textLength = el => (el.innerText || "").trim().length;
    const lCandidates = [];
    const elMain = document.querySelector("main, [role=main]");
    if (elMain) lCandidates.push(["main landmark", elMain]);
    const elArticle = document.querySelector("article");
    if (elArticle) lCandidates.push(["article element", elArticle]);
    let elBest = null;
    let iBest = 0;
    for (const elNode of Array.from(document.querySelectorAll("div, section"))) {
        const iParagraphs = elNode.querySelectorAll("p").length;
        if (iParagraphs < 3) continue;
        const iScore = textLength(elNode) + iParagraphs * 50;
        if (iScore > iBest) { iBest = iScore; elBest = elNode; }
    }
    if (elBest) lCandidates.push(["densest text container", elBest]);
    if (!lCandidates.length) return null;
    const [sMethod, elChosen] = lCandidates[0];
    return {
        byline: "",
        content: elChosen.innerHTML,
        excerpt: "",
        length: textLength(elChosen),
        method: sMethod,
        siteName: "",
        title: document.title || ""
    };
})()"""


class MainContentError(Exception):
    pass


def fetchText(sUrl):
    request = urllib.request.Request(sUrl, headers={"User-Agent": userAgent})
    with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
        return response.read().decode("utf-8")


def getReadabilityScript():
    """Return the Readability source, fetching it once per session."""
    if dCachedScript.get("source"):
        return dCachedScript["source"]
    for sUrl in lReadabilityCdnUrls:
        homerLog.info(f"Fetching Readability from {sUrl}")
        try:
            sSource = fetchText(sUrl)
        except Exception as exception:
            homerLog.warning(f"Could not fetch Readability from {sUrl}: {exception}")
            continue
        dCachedScript["source"] = sSource
        homerLog.info(f"Fetched Readability, {len(sSource)} characters")
        return sSource
    homerLog.warning("Readability could not be downloaded; the built-in fallback will be used")
    return ""


def escapeHtml(sValue):
    return (
        str(sValue or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def buildDocument(dArticle, sPageUrl):
    """Wrap the extracted fragment in a complete, plainly structured document."""
    sTitle = dArticle.get("title") or sPageUrl
    sContent = dArticle.get("content") or ""
    if not re.search(r"<\s*h1\b", sContent, re.IGNORECASE):
        sContent = f"<h1>{escapeHtml(sTitle)}</h1>\n{sContent}"
    lHeader = [f"<p>Source: <a href=\"{escapeHtml(sPageUrl)}\">{escapeHtml(sPageUrl)}</a></p>"]
    if dArticle.get("byline"):
        lHeader.append(f"<p>By {escapeHtml(dArticle['byline'])}</p>")
    if dArticle.get("siteName"):
        lHeader.append(f"<p>Site: {escapeHtml(dArticle['siteName'])}</p>")
    lHeader.append(
        f"<p>Extracted by HomerView using {escapeHtml(dArticle.get('method', 'unknown'))}, "
        f"{dArticle.get('length', 0)} characters.</p>"
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{escapeHtml(sTitle)}</title>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n" + "\n".join(lHeader) + "\n</header>\n"
        "<main>\n" + sContent + "\n</main>\n"
        "</body>\n"
        "</html>\n"
    )


def injectReadability(cdpSession, sSessionId):
    """Put Readability into the page, and say whether it arrived.

    Shared by the extract command and by whatever else needs to ask where the
    article is, so the two cannot disagree about it. The source is fetched once
    per session and cached, so a second caller costs only the injection.
    """
    sSource = getReadabilityScript()
    if not sSource:
        return False
    cdpSession.evaluate(sSessionId, sSource, extractTimeoutSeconds)
    bLoaded = bool(cdpSession.evaluate(sSessionId, 'typeof Readability !== "undefined"'))
    if not bLoaded:
        homerLog.warning("Readability did not load into the page")
    return bLoaded


def extractMainContent(cdpSession):
    """Extract the readable part of the focused page and save it."""
    logSection("Command: extract the main content")
    dTarget, sSessionId = cdpSession.findActivePageSession()
    sPageUrl = dTarget.get("url", "")
    sPageTitle = dTarget.get("title", "") or sPageUrl
    homerLog.info(f"Extracting from {abbreviate(sPageTitle, 120)} at {abbreviate(sPageUrl, 300)}")

    dArticle = None
    if injectReadability(cdpSession, sSessionId):
        dArticle = cdpSession.evaluate(sSessionId, readabilityScript, extractTimeoutSeconds)
        if dArticle:
            homerLog.info("Readability extracted the article")
        else:
            homerLog.info("Readability found no article; falling back to the built-in method")
    if not dArticle:
        dArticle = cdpSession.evaluate(sSessionId, fallbackScript, extractTimeoutSeconds)
        if dArticle:
            homerLog.info(f"Fallback extraction used the {dArticle.get('method')}")
    if not dArticle:
        raise MainContentError("No main content could be identified on this page")

    pathFolder = paths.getTempFolder()
    pathDocument = pathFolder / mainContentFileName
    # UTF-8 with a byte order mark and Windows line endings, matching the
    # convention for every other .htm file in this project.
    pathDocument.write_text(buildDocument(dArticle, sPageUrl), encoding="utf-8-sig", newline="\r\n")
    homerLog.info(f"Wrote {pathDocument}, {pathDocument.stat().st_size} bytes")

    return {
        "characters": dArticle.get("length", 0),
        "method": dArticle.get("method", "unknown"),
        "path": str(pathDocument),
        "pathUri": pathDocument.as_uri(),
        "title": dArticle.get("title") or sPageTitle,
    }
