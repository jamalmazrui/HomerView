"""Prove that all three ways of reaching the browser are actually working.

HomerView claims three separate channels, and each can fail independently and
silently. This command exercises all of them and reports what it found, so the
claim can be checked rather than believed.

    The browser's own window, through NVDA's object model and the Windows API.
    That is how the address bar, the tab strip and the toolbars are reachable,
    none of which exist in the page.

    The page as NVDA has built it, through the browse mode tree interceptor.
    That is the reading order the user actually navigates, with its landmarks,
    headings and text ranges.

    The page as the browser sees it, through the DevTools Protocol, in both
    directions: queries that ask, and commands that act.

The third one matters most to test honestly, because a protocol connection can
answer queries perfectly while its ability to act has been lost. So the test
does not only read: it dispatches a real input event and asks the accessibility
domain for a live tree, which are the two capabilities every later feature
depends on.
"""

import ctypes

import addonHandler
import api
import textInfos

from .logger import abbreviate, homerLog, logSection

addonHandler.initTranslation()

maximumAncestors = 8


def escape(vValue):
    import html

    return html.escape(str(vValue if vValue is not None else ""), quote=True)


def collectBrowserUi():
    """Read Edge's own window through NVDA objects and the Windows API."""
    lFindings = []
    try:
        objForeground = api.getForegroundObject()
        iHandle = getattr(objForeground, "windowHandle", 0)
        lFindings.append(("Foreground window name", getattr(objForeground, "name", "")))
        lFindings.append(("Window handle", iHandle))
        lFindings.append(("Process id", getattr(objForeground, "processID", 0)))
        lFindings.append(
            ("Application module", getattr(getattr(objForeground, "appModule", None), "appName", ""))
        )
        # The Windows API directly, rather than through NVDA, so the two can be
        # compared. If they disagree, the object model is stale.
        bufferTitle = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(iHandle, bufferTitle, 512)
        bufferClass = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(iHandle, bufferClass, 256)
        lFindings.append(("Window text from the Windows API", bufferTitle.value))
        lFindings.append(("Window class from the Windows API", bufferClass.value))
    except Exception as exception:
        lFindings.append(("Error", str(exception)))
        return lFindings, False

    try:
        objFocus = api.getFocusObject()
        lAncestors = []
        obj = objFocus
        for _iStep in range(maximumAncestors):
            if not obj:
                break
            sRole = getattr(getattr(obj, "role", None), "displayString", "") or str(
                getattr(obj, "role", "")
            )
            sName = (getattr(obj, "name", "") or "").strip()
            lAncestors.append(f"{sRole}: {sName}" if sName else sRole)
            obj = getattr(obj, "parent", None)
        lFindings.append(("Object ancestry from the focus", " / ".join(lAncestors)))
    except Exception as exception:
        lFindings.append(("Ancestry error", str(exception)))
    return lFindings, True


def collectVirtualBuffer(treeInterceptor):
    """Read the page as NVDA has built it."""
    lFindings = []
    if not treeInterceptor:
        lFindings.append(("Result", "No browse mode document has focus"))
        return lFindings, False
    try:
        lFindings.append(
            ("Browse mode class", type(treeInterceptor).__name__)
        )
        lFindings.append(
            ("Class ancestry", ", ".join(cls.__name__ for cls in type(treeInterceptor).__mro__[:5]))
        )
        sAddress = getattr(treeInterceptor, "documentConstantIdentifier", "") or ""
        lFindings.append(("Document address", sAddress))
        info = treeInterceptor.makeTextInfo(textInfos.POSITION_ALL)
        sText = info.text or ""
        lFindings.append(("Characters in the buffer", len(sText)))
        infoFirst = treeInterceptor.makeTextInfo(textInfos.POSITION_FIRST)
        for sType, sLabel in (
            ("heading", "Headings"),
            ("link", "Links"),
            ("landmark", "Landmarks"),
        ):
            try:
                iCount = sum(
                    1 for _item in treeInterceptor._iterNodesByType(sType, "next", infoFirst)
                )
            except Exception:
                iCount = -1
            lFindings.append((sLabel, iCount if iCount >= 0 else "not supported here"))
        return lFindings, len(sText) > 0
    except Exception as exception:
        lFindings.append(("Error", str(exception)))
        return lFindings, False


def collectProtocol(cdpSession):
    """Query the browser, then act on it, and report both."""
    lFindings = []
    bQuery = False
    bAction = False
    try:
        dVersion = cdpSession.call("Browser.getVersion")
        lFindings.append(("Browser", dVersion.get("product", "")))
        lFindings.append(("Protocol version", dVersion.get("protocolVersion", "")))
        dTarget, sSessionId = cdpSession.findActivePageSession()
        lFindings.append(("Active page", dTarget.get("url", "")))
        lFindings.append(("Session", sSessionId))
        bQuery = True
    except Exception as exception:
        lFindings.append(("Query error", str(exception)))
        return lFindings, False, False

    try:
        vTitle = cdpSession.evaluate(sSessionId, "document.title")
        lFindings.append(("Script evaluation", f"document.title returned {vTitle!r}"))
    except Exception as exception:
        lFindings.append(("Script evaluation error", str(exception)))

    try:
        dDocument = cdpSession.call("DOM.getDocument", {"depth": 1}, sSessionId)
        iRoot = (dDocument.get("root") or {}).get("nodeId", 0)
        lFindings.append(("DOM domain", f"document node {iRoot}"))
    except Exception as exception:
        lFindings.append(("DOM domain error", str(exception)))

    try:
        cdpSession.call("Accessibility.enable", {}, sSessionId)
        dTree = cdpSession.call("Accessibility.getPartialAXTree", {"fetchRelatives": False}, sSessionId)
        lNodes = dTree.get("nodes") or []
        lFindings.append(("Accessibility domain", f"{len(lNodes)} nodes from the live tree"))
    except Exception as exception:
        lFindings.append(("Accessibility domain error", str(exception)))

    try:
        # A real input event, chosen because it changes nothing: moving the
        # pointer to the corner has no side effect, but it proves the input
        # channel is open, which reading alone never does.
        cdpSession.call(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": 0, "y": 0, "button": "none", "clickCount": 0},
            sSessionId,
        )
        lFindings.append(("Input domain", "a pointer event was accepted"))
        bAction = True
    except Exception as exception:
        lFindings.append(("Input domain error", str(exception)))

    try:
        dHistory = cdpSession.call("Page.getNavigationHistory", {}, sSessionId)
        lEntries = dHistory.get("entries") or []
        lFindings.append(("Navigation history", f"{len(lEntries)} entries"))
    except Exception as exception:
        lFindings.append(("Navigation history error", str(exception)))

    return lFindings, bQuery, bAction


def buildReportHtml(dResults):
    lParts = ["<h1>HomerView self test</h1>"]
    for sTitle, (lFindings, bWorking) in dResults.items():
        # Translators: shown in the self test for a working or failing channel.
        sVerdict = "working" if bWorking else "not available"
        lParts.append(f"<h2>{escape(sTitle)}: {escape(sVerdict)}</h2>")
        lParts.append("<table><tbody>")
        for sLabel, vValue in lFindings:
            lParts.append(
                f"<tr><td>{escape(sLabel)}</td><td>{escape(abbreviate(str(vValue), 300))}</td></tr>"
            )
        lParts.append("</tbody></table>")
    lParts.append(
        "<p>The third channel is reported as two separate things on purpose. A protocol "
        "connection can answer every query while having lost the ability to act, and a "
        "test that only reads would not notice.</p>"
    )
    return "\n".join(lParts)


def runNvdaSide(treeInterceptor):
    """Collect everything that must be read on NVDA's own thread."""
    logSection("Command: self test")
    lUi, bUi = collectBrowserUi()
    lBuffer, bBuffer = collectVirtualBuffer(treeInterceptor)
    homerLog.info(f"Self test, browser window: {bUi}; virtual buffer: {bBuffer}")
    return lUi, bUi, lBuffer, bBuffer
