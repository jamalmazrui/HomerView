"""Dependency free HTTP that behaves like a browser.

A port of the practical parts of the C# Web module. Everything here exists
because a plain urlopen fails on real sites for reasons that have nothing to do
with the code being wrong.

A request without a realistic User-Agent is refused by a large share of sites.
A request for a file linked from a page, sent without that page as the Referer
and without the Sec-Fetch headers a browser sends, looks like a scraper and
comes back as a login page. A saved file needs its name from the
Content-Disposition header when the server gives one, including the RFC 5987
encoded form, and from the address when it does not. That name needs cleaning
of characters Windows forbids, and numbering when it is already taken. When the
address has no extension, the MIME type has to supply one.

None of this is difficult. All of it is easy to leave out, and each omission
produces a failure that looks like something else.
"""

import html
import mimetypes
import os
import re
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

defaultTimeoutSeconds = 30.0
maximumNameLength = 120
userAgent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)

reAnchor = re.compile(r"""<a\s[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""", re.IGNORECASE | re.DOTALL)
reDispositionExtended = re.compile(r"filename\*\s*=\s*[^']*''([^;]+)", re.IGNORECASE)
reDispositionPlain = re.compile(r'filename\s*=\s*"?([^";]+)"?', re.IGNORECASE)
reTag = re.compile(r"<[^>]+>")
reUnsafe = re.compile(r'[\\/*?:"<>|]')


def buildHeaders(sPageUrl="", sCookies="", sUserAgent=""):
    """Headers that make a request look like a click rather than a script."""
    dHeaders = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": sUserAgent or userAgent,
    }
    if sCookies:
        dHeaders["Cookie"] = sCookies
    if sPageUrl:
        dHeaders["Referer"] = sPageUrl
        dHeaders["Sec-Fetch-Dest"] = "document"
        dHeaders["Sec-Fetch-Mode"] = "navigate"
        dHeaders["Sec-Fetch-User"] = "?1"
        dHeaders["Upgrade-Insecure-Requests"] = "1"
        try:
            parsedPage = urlparse(sPageUrl)
            dHeaders["Sec-Fetch-Site"] = "same-origin"
        except Exception:
            pass
    return dHeaders


def fetchText(sUrl, nTimeout=defaultTimeoutSeconds, sPageUrl=""):
    request = urllib.request.Request(sUrl, headers=buildHeaders(sPageUrl))
    with urllib.request.urlopen(request, timeout=nTimeout) as response:
        bBody = response.read()
    return bBody.decode("utf-8", errors="replace")


def nameFromDisposition(sHeader):
    """Read a filename from Content-Disposition, extended form first."""
    if not sHeader:
        return ""
    match = reDispositionExtended.search(sHeader)
    if match:
        return unquote(match.group(1)).strip()
    match = reDispositionPlain.search(sHeader)
    return match.group(1).strip() if match else ""


def extensionForMime(sMime):
    """Guess an extension from a MIME type, for an address that has none."""
    sMime = (sMime or "").split(";")[0].strip().lower()
    if not sMime:
        return ""
    sExtension = mimetypes.guess_extension(sMime) or ""
    # The standard library prefers some archaic spellings.
    return {".jpe": ".jpg", ".htm": ".htm", ".txt": ".txt"}.get(sExtension, sExtension)


def sanitizeName(sName, sFallback="download"):
    sName = unquote(str(sName or "")).strip().strip(".")
    sName = reUnsafe.sub("_", sName)
    sName = " ".join(sName.split())
    sName = "".join(c for c in sName if ord(c) >= 32)
    # Windows' reserved device names cannot be file names, with or without an extension (kit 1.62.5).
    if re.match(r"(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)", sName): sName = "_" + sName
    if not sName:
        sName = sFallback
    if len(sName) > maximumNameLength:
        sRoot, sExtension = os.path.splitext(sName)
        sName = sRoot[: maximumNameLength - len(sExtension)] + sExtension
    return sName


def nameFromUrl(sUrl, sFallback="download"):
    sPath = urlparse(str(sUrl or "")).path
    return sanitizeName(Path(unquote(sPath)).name, sFallback)


def uniquePath(pathFolder, sName):
    """Return a path that does not exist, numbering duplicates as Windows does."""
    pathFolder = Path(pathFolder)
    pathCandidate = pathFolder / sName
    if not pathCandidate.exists():
        return pathCandidate
    sStem, sExtension = pathCandidate.stem, pathCandidate.suffix
    for iCount in range(2, 1000):
        pathCandidate = pathFolder / f"{sStem} ({iCount}){sExtension}"
        if not pathCandidate.exists():
            return pathCandidate
    return pathFolder / f"{sStem} ({os.getpid()}){sExtension}"


def getLinks(sHtml, sBaseUrl=""):
    """Return address and text for every anchor, addresses made absolute.

    Regular expressions rather than a parser, deliberately. The markup this
    meets is often malformed, and a strict parser gives up exactly where a
    forgiving pattern still finds the links.
    """
    parsed = urlparse(sBaseUrl) if sBaseUrl else None
    sOrigin = f"{parsed.scheme}://{parsed.netloc}" if parsed and parsed.netloc else ""
    lLinks = []
    for match in reAnchor.finditer(sHtml or ""):
        sHref = html.unescape(match.group(1).strip())
        sText = html.unescape(reTag.sub(" ", match.group(2))).strip()
        # Every relative address made absolute against the page, as described, not only those starting with a slash
        # (kit 1.62.5, from an audit by another AI: next.html and #part stayed relative).
        sAbsolute = urljoin(sBaseUrl, sHref) if sBaseUrl and not re.match(r"(?i)^(javascript|mailto|tel|data):", sHref) else sHref
        lLinks.append((sAbsolute, sText))
    return lLinks
