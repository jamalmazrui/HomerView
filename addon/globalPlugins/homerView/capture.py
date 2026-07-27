"""Save the current page as an image, a document, a tree, or its markup.

Four things the protocol can produce that a browser's own Save command cannot,
and each answers a different question.

An image is what a sighted colleague sees. When a reader reports a problem and
is asked "what does it look like", this is the answer, and it can be attached
to an email without describing anything.

A PDF is the page as it would print: one file, fixed layout, readable by
anything, and accepted by every system that will not take a web page.

The accessibility tree is the page as assistive technology receives it, with
each node's role, name, and the reasons any node was ignored. That last part is
the one nothing else provides, and it is why an element visible on screen can
be missing from the reading order.

The markup is the document after script has run, which is not what the server
sent and not what View Source shows.

Both the image and the PDF arrive as encoded text over the protocol and are
decoded here, so a failure to decode is reported rather than written to disk as
a broken file.
"""

import base64
import json

from .logger import abbreviate, homerLog, logSection

captureTimeoutSeconds = 120.0

# The whole page rather than the visible part. A screenshot of what happens to
# be scrolled into view answers a narrower question than the one being asked.
dScreenshotOptions = {"format": "png", "captureBeyondViewport": True}

dPdfOptions = {
    "printBackground": True,
    "preferCSSPageSize": True,
}


class CaptureError(Exception):
    pass


def decodeToFile(sData, pathTarget, sWhat):
    if not sData:
        raise CaptureError(f"The browser returned no {sWhat}")
    try:
        bBytes = base64.b64decode(sData)
    except Exception:
        raise CaptureError(f"The {sWhat} could not be decoded")
    pathTarget.write_bytes(bBytes)
    homerLog.info(f"Wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget


def saveImage(cdpSession, sSessionId, pathTarget):
    logSection("Capture: page image")
    dResult = cdpSession.call(
        "Page.captureScreenshot", dScreenshotOptions, sSessionId, captureTimeoutSeconds
    )
    return decodeToFile(dResult.get("data", ""), pathTarget, "image")


def savePdf(cdpSession, sSessionId, pathTarget):
    logSection("Capture: page as PDF")
    dResult = cdpSession.call(
        "Page.printToPDF", dPdfOptions, sSessionId, captureTimeoutSeconds
    )
    return decodeToFile(dResult.get("data", ""), pathTarget, "PDF")


def saveAccessibilityTree(cdpSession, sSessionId, pathTarget):
    """Save the page as assistive technology receives it.

    Every node carries its role, its name, and when it was left out of the tree,
    the reasons why. Nothing else HomerView can produce answers the question of
    why something on screen is absent from the reading order.
    """
    logSection("Capture: accessibility tree")
    try:
        cdpSession.call("Accessibility.enable", {}, sSessionId)
    except Exception:
        homerLog.debug("The accessibility domain was already enabled")
    dResult = cdpSession.call(
        "Accessibility.getFullAXTree", {}, sSessionId, captureTimeoutSeconds
    )
    lNodes = dResult.get("nodes") or []
    iIgnored = sum(1 for d in lNodes if d.get("ignored"))
    homerLog.info(f"Accessibility tree: {len(lNodes)} nodes, {iIgnored} of them ignored")
    pathTarget.write_text(json.dumps(dResult, indent=2), encoding="utf-8")
    homerLog.info(f"Wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget


def saveMarkup(cdpSession, sSessionId, pathTarget):
    """Save the document after script has run, not the markup the server sent."""
    logSection("Capture: page markup")
    sHtml = cdpSession.evaluate(
        sSessionId, "document.documentElement.outerHTML", captureTimeoutSeconds
    ) or ""
    if not sHtml:
        raise CaptureError("The page markup could not be read")
    if not sHtml.lstrip().lower().startswith("<!doctype"):
        sHtml = "<!doctype html>\n" + sHtml
    pathTarget.write_text(sHtml, encoding="utf-8-sig", newline="\r\n")
    homerLog.info(f"Wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget


def saveArchive(cdpSession, sSessionId, pathTarget):
    """Save the page and everything it uses as one file.

    This is what Microsoft Edge's own Save Page As produces by default, and
    having it is what makes taking Control+S honest: the format a user already
    relied on is still there, alongside the six HomerView adds.
    """
    logSection("Capture: page archive")
    dResult = cdpSession.call(
        "Page.captureSnapshot", {"format": "mhtml"}, sSessionId, captureTimeoutSeconds)
    sData = dResult.get("data", "")
    if not sData:
        raise CaptureError("The browser returned no archive")
    pathTarget.write_text(sData, encoding="utf-8", newline="")
    homerLog.info(f"Wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget


dCaptures = {
    "mhtml": (saveArchive, "The page and everything it uses, in one file, as Edge saves it"),
    "png": (saveImage, "Image of the whole page, as a sighted reader sees it"),
    "pdf": (savePdf, "The page as it would print, fixed layout, one file"),
    "json": (saveAccessibilityTree, "The accessibility tree, with the reasons any node was ignored"),
    "dom.htm": (saveMarkup, "The markup after script has run, not what the server sent"),
}


def capture(cdpSession, sFormat, pathTarget):
    dTarget, sSessionId = cdpSession.findActivePageSession()
    homerLog.info(
        f"Capturing {sFormat} from {abbreviate(dTarget.get('title', ''), 100)} "
        f"at {abbreviate(dTarget.get('url', ''), 200)}"
    )
    functionCapture = dCaptures[sFormat][0]
    return functionCapture(cdpSession, sSessionId, pathTarget)
