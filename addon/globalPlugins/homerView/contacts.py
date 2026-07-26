"""Find how to report an accessibility problem to the people who own a site.

Ported from AccReporter, whose reason for existing was the step after the scan:
a user with a disability has found a barrier, so how do they actually tell the
publisher about it? Scanners are common; the reporting channel is not.

Three sources feed the search, because each catches what the others miss.

The page the user is on is read through the protocol, so anchors added by
JavaScript after load are included. The site's home page is fetched separately,
because a footer almost always carries contact, accessibility, and social links
even when the current page does not. Finally a short list of conventional
accessibility paths is probed with HEAD requests, which finds statements that
nothing links to.

Everything runs on the worker thread and every request has a timeout, so a slow
or hostile site delays nothing that the user can feel.
"""

import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .logger import abbreviate, homerLog

contactFetchTimeoutSeconds = 5.0
homePageFetchTimeoutSeconds = 8.0
maximumLinksPerBucket = 25
userAgent = "HomerView (+NVDA add-on)"

# Deliberately excludes X, formerly Twitter. This was a product decision in
# AccReporter rather than an oversight: the platform has repeatedly failed to
# surface accessibility complaints reliably, so listing it would send an
# advocacy user somewhere their report is unlikely to be read.
lExcludedSocialDomains = ["x.com", "twitter.com"]
lSocialDomains = [
    "bsky.app",
    "facebook.com",
    "linkedin.com",
    "mastodon.social",
    "threads.net",
]

# Probed in order. The first four are accessibility statements, which is the
# most valuable find, so they are probed first.
lStatementPaths = [
    "/accessibility",
    "/accessibility-statement",
    "/accessibility-statement.html",
    "/.well-known/accessibility-statement",
]
lContactPaths = [
    "/contact",
    "/contact-us",
    "/contact.html",
]

lAccessibilityWords = ["accessibility", "a11y"]
lContactWords = ["contact", "feedback", "support", "help", "report"]

reAnchor = re.compile(r"""<a\s[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""", re.IGNORECASE | re.DOTALL)
reTag = re.compile(r"<[^>]+>")

# The same extraction, run inside the page so that anchors created by script
# after load are seen. Kept close to AccReporter's original.
domContactScript = r"""(() => {
    const lExcludedSocialDomains = ["x.com", "twitter.com"]
lSocialDomains = ["bsky.app", "facebook.com", "linkedin.com", "mastodon.social", "threads.net"];
    const dResult = {accessibility: [], contact: [], mailto: [], social: [], statement: ""};
    for (const elAnchor of Array.from(document.querySelectorAll("a[href]"))) {
        const sHref = elAnchor.getAttribute("href") || "";
        const sText = (elAnchor.textContent || "").trim().toLowerCase();
        const sAriaLabel = (elAnchor.getAttribute("aria-label") || "").toLowerCase();
        const sLabel = sText || sAriaLabel;
        if (sHref.toLowerCase().startsWith("mailto:")) {
            dResult.mailto.push(sHref);
            continue;
        }
        let sAbsolute = sHref;
        try {
            sAbsolute = new URL(sHref, window.location.href).href;
        } catch (error) {
            continue;
        }
        if (!sAbsolute.startsWith("http")) continue;
        const bAccessibility = sLabel.includes("accessibility") || sLabel.includes("a11y") ||
            sAbsolute.toLowerCase().includes("/accessibility");
        const bContact = ["contact", "feedback", "support", "help", "report"].some(w => sLabel.includes(w));
        if (bAccessibility) {
            if (sAbsolute.toLowerCase().includes("/accessibility") && !dResult.statement) {
                dResult.statement = sAbsolute;
            }
            dResult.accessibility.push(sAbsolute);
        } else if (bContact) {
            dResult.contact.push(sAbsolute);
        }
        for (const sDomain of lSocialDomains) {
            if (sAbsolute.includes(sDomain)) {
                dResult.social.push(sAbsolute);
                break;
            }
        }
    }
    return dResult;
})()"""


def normalizeUrl(sUrl):
    """Reduce an address to a comparable form.

    Two links to the same page differing only by a trailing slash or by the case
    of the host are the same channel, and listing both wastes the reader's time.
    """
    parsed = urlparse(sUrl)
    sPath = parsed.path or "/"
    if len(sPath) > 1 and sPath.endswith("/"):
        sPath = sPath.rstrip("/") or "/"
    sQuery = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{sPath}{sQuery}"


def isExcludedHost(sUrl):
    sHost = urlparse(sUrl).netloc.lower()
    return any(sHost == s or sHost.endswith("." + s) for s in lExcludedSocialDomains)


def emptyContacts():
    return {"accessibility": [], "contact": [], "mailto": [], "social": [], "statement": ""}


def fetchText(sUrl, nTimeout):
    try:
        request = urllib.request.Request(
            sUrl, headers={"Accept": "text/html", "User-Agent": userAgent}
        )
        with urllib.request.urlopen(request, timeout=nTimeout) as response:
            bBody = response.read(2_000_000)
        return bBody.decode("utf-8", errors="replace")
    except Exception as exception:
        homerLog.debug(f"Could not fetch {sUrl}: {exception}")
        return ""


def pathResolves(sUrl):
    """Probe with HEAD, returning the address it settled on, or an empty string.

    The body is never downloaded; a server that does not implement HEAD answers
    405 and the probe moves on.

    The final address is checked against the site root. Single page applications
    answer 200 for every address, so a bare probe reports success for paths that
    do not exist. When the probe lands back at the root, the path did not exist
    and the result is discarded.
    """
    try:
        request = urllib.request.Request(
            sUrl, method="HEAD", headers={"User-Agent": userAgent}
        )
        with urllib.request.urlopen(request, timeout=contactFetchTimeoutSeconds) as response:
            bOk = 200 <= response.status < 300
            sFinal = getattr(response, "url", "") or sUrl
    except Exception as exception:
        homerLog.debug(f"Probed {sUrl}: {exception}")
        return ""
    if not bOk:
        homerLog.debug(f"Probed {sUrl}: not found")
        return ""
    if urlparse(sFinal).path in ("", "/"):
        homerLog.debug(f"Probed {sUrl}: settled at the site root, so the path does not exist")
        return ""
    homerLog.debug(f"Probed {sUrl}: resolved to {sFinal}")
    return sFinal


def extractFromHtml(sHtml, sPageUrl, dResult):
    """Pull contact signals out of fetched markup.

    Regular expressions rather than a parser, because the goal is to find
    signals in real-world markup that is often malformed, and a strict parser
    gives up where a forgiving pattern still finds the footer links.
    """
    parsed = urlparse(sPageUrl)
    sOrigin = f"{parsed.scheme}://{parsed.netloc}"
    for match in reAnchor.finditer(sHtml):
        sHref = match.group(1).strip()
        sLabel = reTag.sub(" ", match.group(2)).strip().lower()
        if sHref.lower().startswith("mailto:"):
            dResult["mailto"].append(sHref)
            continue
        sAbsolute = sHref
        if sHref.startswith("//"):
            sAbsolute = f"{parsed.scheme}:{sHref}"
        elif sHref.startswith("/"):
            sAbsolute = sOrigin + sHref
        if not sAbsolute.lower().startswith("http"):
            continue
        sLower = sAbsolute.lower()
        bAccessibility = any(w in sLabel for w in lAccessibilityWords) or "/accessibility" in sLower
        bContact = any(w in sLabel for w in lContactWords)
        if bAccessibility:
            dResult["accessibility"].append(sAbsolute)
        elif bContact:
            dResult["contact"].append(sAbsolute)
        for sDomain in lSocialDomains:
            if sDomain in sLower:
                dResult["social"].append(sAbsolute)
                break


def mergeContacts(dFirst, dSecond):
    dMerged = emptyContacts()
    for sBucket in ("accessibility", "contact", "mailto", "social"):
        lSeen = []
        for sLink in list(dFirst.get(sBucket) or []) + list(dSecond.get(sBucket) or []):
            sKey = sLink if sBucket == "mailto" else normalizeUrl(sLink)
            if sKey not in lSeen:
                lSeen.append(sKey)
        dMerged[sBucket] = lSeen[:maximumLinksPerBucket]
    dMerged["statement"] = dFirst.get("statement") or dSecond.get("statement") or ""
    return dMerged


def discoverContacts(cdpSession, sSessionId, sPageUrl):
    """Return the contact channels for the site the user is on."""
    homerLog.info(f"Discovering contact channels for {abbreviate(sPageUrl, 200)}")
    dFromPage = emptyContacts()
    try:
        dFromPage = cdpSession.evaluate(sSessionId, domContactScript) or emptyContacts()
        homerLog.info(
            "From the page itself: "
            f"{len(dFromPage.get('accessibility') or [])} accessibility, "
            f"{len(dFromPage.get('contact') or [])} contact, "
            f"{len(dFromPage.get('mailto') or [])} mailto, "
            f"{len(dFromPage.get('social') or [])} social"
        )
    except Exception as exception:
        homerLog.warning(f"Reading contacts from the page failed: {exception}")

    dFetched = emptyContacts()
    parsed = urlparse(sPageUrl)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        sOrigin = f"{parsed.scheme}://{parsed.netloc}"
        sHomeHtml = fetchText(sOrigin + "/", homePageFetchTimeoutSeconds)
        if sHomeHtml:
            homerLog.info(f"Fetched the home page, {len(sHomeHtml)} characters")
            extractFromHtml(sHomeHtml, sOrigin + "/", dFetched)
        for sPath in lStatementPaths:
            sResolved = pathResolves(sOrigin + sPath)
            if sResolved:
                dFetched["statement"] = sResolved
                # Also list it, so a statement found by probing is not lost when
                # the page itself links to a different one.
                dFetched["accessibility"].append(sResolved)
                homerLog.info(f"Accessibility statement found at {sResolved}")
                break
        for sPath in lContactPaths:
            sResolved = pathResolves(sOrigin + sPath)
            if sResolved:
                dFetched["contact"].append(sResolved)
                homerLog.info(f"Contact page found at {sResolved}")
                break
    else:
        homerLog.info("The page is not on the web, so no site-level lookup was attempted")

    dContacts = mergeContacts(dFromPage, dFetched)
    homerLog.info(
        "Contacts found: "
        f"{len(dContacts['accessibility'])} accessibility, "
        f"{len(dContacts['contact'])} contact, "
        f"{len(dContacts['mailto'])} mailto, "
        f"{len(dContacts['social'])} social, "
        f"statement {dContacts['statement'] or 'none'}"
    )
    return dContacts
