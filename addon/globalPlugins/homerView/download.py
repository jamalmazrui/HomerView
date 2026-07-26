"""Find downloadable links on a page and fetch them as the browser would.

The technique is urlFido's. The browser is not asked to download anything;
instead the file is fetched directly over HTTP with the session's own cookies
and the headers a browser would have sent had the user clicked the link.

That last part is what makes it work. Sites commonly gate a file on the Referer,
and many inspect the Sec-Fetch headers that every modern browser sends. A
request without them looks like a scraper and comes back as a 403 or a login
page rather than the file. So the request carries the page's address as the
Referer, the browser's own user agent, the cookies the protocol reports for that
address, and the Sec-Fetch set that a navigation from a link would produce.
"""

import re
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import paths
import addonHandler

from .cdp import CdpError
from .logger import abbreviate, homerLog, logSection

addonHandler.initTranslation()

addonHandler.initTranslation()

downloadChunkBytes = 65536
downloadTimeoutSeconds = 120.0
maximumFileNameLength = 120
maximumLinks = 2000

reDisposition = re.compile(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?", re.IGNORECASE)
reUnsafe = re.compile(r'[\\/*?:"<>|]')

# Extensions that are almost always page navigation rather than a file the user
# means to keep. Offering them would bury the ones that matter.
setSkippedExtensions = {
    "asp", "aspx", "cfm", "htm", "html", "jsp", "php", "shtml", "xhtml",
}

# Extensions for which a web page IS the expected answer.
setHtmlExtensions = {"htm", "html", "xhtml", "shtml"}

reGitHubBlob = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/blob/(.+)$", re.IGNORECASE)


def resolveDownloadUrl(sUrl):
    """Turn a page that merely shows a file into the file itself.

    A GitHub blob address is a web page about the file, not the file. Following
    it saves the same few hundred kilobytes of GitHub markup under every name,
    which is silently wrong: the files appear to arrive and none of them open.
    """
    match = reGitHubBlob.match(sUrl)
    if match:
        sRaw = f"https://raw.githubusercontent.com/{match.group(1)}/{match.group(2)}/{match.group(3)}"
        homerLog.debug(f"Rewrote a GitHub blob address to {abbreviate(sRaw, 200)}")
        return sRaw
    return sUrl

linkScript = r"""(() => {
    const lLinks = [];
    for (const elAnchor of Array.from(document.querySelectorAll("a[href]"))) {
        let sAbsolute = "";
        try {
            sAbsolute = new URL(elAnchor.getAttribute("href"), window.location.href).href;
        } catch (error) {
            continue;
        }
        if (!sAbsolute.startsWith("http")) continue;
        let sPath = "";
        try {
            sPath = new URL(sAbsolute).pathname;
        } catch (error) {
            continue;
        }
        const iDot = sPath.lastIndexOf(".");
        const iSlash = sPath.lastIndexOf("/");
        if (iDot <= iSlash + 1) continue;
        const sExtension = sPath.slice(iDot + 1).toLowerCase();
        if (!/^[a-z0-9]{1,8}$/.test(sExtension)) continue;
        lLinks.push({
            extension: sExtension,
            text: (elAnchor.textContent || "").trim().slice(0, 200),
            url: sAbsolute
        });
    }
    return lLinks;
})()"""


class DownloadError(Exception):
    pass


def analyseLinks(cdpSession):
    """Return the links on the focused page that point at a file."""
    logSection("Command: analyse links for download")
    dTarget, sSessionId = cdpSession.findActivePageSession()
    sPageUrl = dTarget.get("url", "")
    lLinks = cdpSession.evaluate(sSessionId, linkScript) or []
    homerLog.info(f"Found {len(lLinks)} links with a file extension on {abbreviate(sPageUrl, 200)}")

    dSeen = {}
    for dLink in lLinks[:maximumLinks]:
        sExtension = dLink.get("extension", "")
        if sExtension in setSkippedExtensions:
            continue
        dSeen.setdefault(dLink["url"], dLink)
    lUnique = list(dSeen.values())
    lExtensions = sorted({d["extension"] for d in lUnique})
    dCounts = {}
    for dLink in lUnique:
        dCounts[dLink["extension"]] = dCounts.get(dLink["extension"], 0) + 1
    homerLog.info(f"Extensions offered: {lExtensions}")
    homerLog.info(f"Links by extension: {dCounts}")
    return {
        "counts": dCounts,
        "extensions": lExtensions,
        "links": lUnique,
        "pageUrl": sPageUrl,
        "sessionId": sSessionId,
    }


def parseExtensions(sText):
    """Accept a list written with or without leading periods, in any order."""
    lParts = re.split(r"[\s,;]+", str(sText or ""))
    lExtensions = []
    for sPart in lParts:
        sPart = sPart.strip().lstrip(".").lower()
        if sPart and sPart not in lExtensions:
            lExtensions.append(sPart)
    return sorted(lExtensions)


def getBrowserUserAgent(cdpSession, sSessionId):
    try:
        return cdpSession.evaluate(sSessionId, "navigator.userAgent") or ""
    except CdpError:
        return ""


def getCookieHeader(cdpSession, sSessionId, sUrl):
    """Return the session's cookies for one address, as a request header."""
    dResult = {}
    try:
        dResult = cdpSession.call("Network.getCookies", {"urls": [sUrl]}, sSessionId)
    except CdpError as exception:
        homerLog.debug(f"Network.getCookies needed the domain enabled: {exception}")
        try:
            cdpSession.call("Network.enable", {}, sSessionId)
            dResult = cdpSession.call("Network.getCookies", {"urls": [sUrl]}, sSessionId)
        except CdpError as exceptionRetry:
            homerLog.warning(f"No cookies could be read: {exceptionRetry}")
            return ""
    lParts = [
        f"{d.get('name')}={d.get('value')}"
        for d in dResult.get("cookies", [])
        if d.get("name")
    ]
    homerLog.debug(f"Replaying {len(lParts)} cookies for {abbreviate(sUrl, 120)}")
    return "; ".join(lParts)


def buildHeaders(sFileUrl, sPageUrl, sUserAgent, sCookies):
    """Present the request the way a click on the link would have presented it."""
    dHeaders = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": sUserAgent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HomerView",
    }
    if sCookies:
        dHeaders["Cookie"] = sCookies
    if sPageUrl:
        dHeaders["Referer"] = sPageUrl
        try:
            parsedPage = urlparse(sPageUrl)
            parsedFile = urlparse(sFileUrl)
            bSameSite = parsedPage.hostname == parsedFile.hostname
            dHeaders["Sec-Fetch-Site"] = "same-origin" if bSameSite else "cross-site"
            if not bSameSite:
                dHeaders["Origin"] = f"{parsedPage.scheme}://{parsedPage.netloc}"
        except Exception:
            pass
    return dHeaders


def fileNameForAnnouncement(dLink):
    """The base name to speak before a file is fetched."""
    sPath = urlparse(resolveDownloadUrl(dLink["url"])).path
    sName = Path(unquote(sPath)).name
    return sName or dLink.get("text") or dLink["url"]


def cleanFileName(sName, sExtension):
    sName = unquote(str(sName or "")).strip().strip(".")
    sName = reUnsafe.sub("_", sName)
    sName = " ".join(sName.split())
    if not sName:
        sName = "download"
    if len(sName) > maximumFileNameLength:
        sName = sName[:maximumFileNameLength]
    if sExtension and not sName.lower().endswith("." + sExtension):
        sName = f"{sName}.{sExtension}"
    return sName


def nameFromResponse(response, sFileUrl, sExtension):
    sDisposition = response.headers.get("Content-Disposition", "") if response.headers else ""
    match = reDisposition.search(sDisposition or "")
    if match:
        return cleanFileName(Path(match.group(1)).name, sExtension)
    sPath = urlparse(sFileUrl).path
    return cleanFileName(Path(unquote(sPath)).name, sExtension)


def downloadOne(dLink, sPageUrl, sUserAgent, sCookies, pathFolder):
    sFileUrl = resolveDownloadUrl(dLink["url"])
    sExtension = dLink.get("extension", "")
    request = urllib.request.Request(
        sFileUrl, headers=buildHeaders(sFileUrl, sPageUrl, sUserAgent, sCookies)
    )
    with urllib.request.urlopen(request, timeout=downloadTimeoutSeconds) as response:
        # A web page returned where a document was asked for means the address
        # was a page about the file rather than the file. Saving it would put
        # markup on disk under a name that promises a document.
        sType = (response.headers.get("Content-Type", "") or "").split(";")[0].strip().lower()
        if sType in ("text/html", "application/xhtml+xml") and sExtension not in setHtmlExtensions:
            raise DownloadError(
                f"the server returned a web page rather than a {sExtension} file"
            )
        sName = nameFromResponse(response, sFileUrl, sExtension)
        pathTarget = paths.uniquePath(pathFolder, sName)
        iBytes = 0
        with open(pathTarget, "wb") as fTarget:
            while True:
                bChunk = response.read(downloadChunkBytes)
                if not bChunk:
                    break
                fTarget.write(bChunk)
                iBytes += len(bChunk)
    homerLog.info(f"Downloaded {pathTarget.name}, {iBytes} bytes, from {abbreviate(sFileUrl, 200)}")
    return pathTarget, iBytes


def downloadLinks(cdpSession, dAnalysis, lExtensions, functionAnnounce=None):
    """Download every link whose extension the user accepted."""
    logSection("Command: download files")
    setWanted = set(lExtensions)
    lChosen = [d for d in dAnalysis["links"] if d.get("extension") in setWanted]
    homerLog.info(f"Downloading {len(lChosen)} files with extensions {sorted(setWanted)}")
    if not lChosen:
        return {"failed": 0, "files": [], "folder": "", "saved": 0}

    sSessionId = dAnalysis["sessionId"]
    sPageUrl = dAnalysis["pageUrl"]
    sUserAgent = getBrowserUserAgent(cdpSession, sSessionId)
    pathFolder = paths.getDownloadsFolder()
    homerLog.info(f"Saving to {pathFolder}")

    dCookieCache = {}
    lFiles = []
    iFailed = 0
    for iIndex, dLink in enumerate(lChosen, 1):
        sOrigin = ""
        try:
            parsed = urlparse(dLink["url"])
            sOrigin = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
        if sOrigin not in dCookieCache:
            dCookieCache[sOrigin] = getCookieHeader(cdpSession, sSessionId, dLink["url"])
        homerLog.info(f"File {iIndex} of {len(lChosen)}: {abbreviate(dLink['url'], 200)}")
        if functionAnnounce:
            functionAnnounce(fileNameForAnnouncement(dLink))
        try:
            pathTarget, iBytes = downloadOne(
                dLink, sPageUrl, sUserAgent, dCookieCache[sOrigin], pathFolder
            )
            lFiles.append({"bytes": iBytes, "name": pathTarget.name})
        except Exception as exception:
            iFailed += 1
            homerLog.warning(f"Failed: {abbreviate(dLink['url'], 200)} because {exception}")
            if functionAnnounce:
                # Translators: Spoken when one file in a download fails.
                functionAnnounce(_("Error"))
    homerLog.info(f"Downloaded {len(lFiles)} files, {iFailed} failed")
    return {
        "failed": iFailed,
        "files": lFiles,
        "folder": str(pathFolder),
        "saved": len(lFiles),
    }
