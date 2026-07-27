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
import time
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
# Two minutes was too long. One slow host held the whole batch for fifty two
# seconds, and every download after it failed instantly on name resolution:
# nine in the same second. Ten dead hosts would each have failed at their own
# pace, so what happened was the resolver giving up after the stall rather than
# ten addresses that do not exist. A shorter wait means one bad host costs a
# few seconds instead of a minute, and gives the stack less to recover from.
downloadTimeoutSeconds = 25.0

# A name that will not resolve is often a name that will not resolve just now.
# One retry after a pause costs little and recovers the common case, which is a
# resolver that has been briefly overwhelmed.
retryPauseSeconds = 2.0
retryAttempts = 2

# Errors worth trying again, and errors that mean what they say. There is no
# point retrying a 404.
setTransientErrors = {
    "getaddrinfo failed", "temporary failure in name resolution",
    "timed out", "connection reset", "connection aborted",
    "no route to host", "network is unreachable",
}
maximumFileNameLength = 120
maximumLinks = 2000

reDisposition = re.compile(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?", re.IGNORECASE)
reUnsafe = re.compile(r'[\\/*?:"<>|]')

# Extensions that are a way of reaching another page rather than a file, and
# that carry no file of their own. A page addressed as .php is the site's own
# navigation, and offering hundreds of them would bury the files that matter.
#
# Web pages are NOT in this set. A reader may well want the page itself, and
# htm and html are offered like anything else; they are simply left out of the
# line that is filled in for you, so they are one keystroke away rather than
# in the way.
setSkippedExtensions = {
    "asp", "aspx", "cfm", "cgi", "do", "jsp", "php", "pl", "py",
}

# Not offered by default, though still listed and still available by typing
# them in. Page addresses and script assets are numerous and rarely wanted.
setNotByDefault = {
    "css", "htm", "html", "js", "json", "shtml", "xhtml", "xml",
}

# What a file of each kind is, so the chooser can say so rather than showing a
# bare list of extensions. Everything named in this project's documentation is
# here, and the list is the answer to "what can this command actually fetch".
dExtensionNames = {
    "7z": "7-Zip archive", "aac": "AAC audio", "avi": "AVI video",
    "bmp": "Bitmap image", "csv": "Comma separated values",
    "doc": "Word document", "docx": "Word document", "epub": "EPUB ebook",
    "exe": "Windows program", "flac": "FLAC audio", "gif": "GIF image",
    "gz": "Gzip archive", "htm": "Web page", "html": "Web page",
    "jpeg": "JPEG image", "jpg": "JPEG image", "json": "JSON data",
    "m4a": "M4A audio", "m4b": "M4B audiobook", "md": "Markdown",
    "mobi": "Mobipocket ebook", "mp3": "MP3 audio", "mp4": "MP4 video",
    "msi": "Windows installer", "odp": "OpenDocument presentation",
    "ods": "OpenDocument spreadsheet", "odt": "OpenDocument text",
    "ogg": "Ogg audio", "pdf": "PDF document", "png": "PNG image",
    "ppt": "PowerPoint presentation", "pptx": "PowerPoint presentation",
    "rar": "RAR archive", "rtf": "Rich text", "svg": "SVG image",
    "tar": "Tar archive", "txt": "Plain text", "wav": "WAV audio",
    "webp": "WebP image", "wma": "WMA audio", "xls": "Excel workbook",
    "xlsx": "Excel workbook", "xml": "XML data", "zip": "Zip archive",
    "unknown": "named by the server",
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
    // Where a download can hide, beyond an anchor with a file name in its
    // address. All three of these are ordinary on real pages and all three
    // were being missed.
    const dMimeExtensions = {
        "application/pdf": "pdf", "application/zip": "zip",
        "application/epub+zip": "epub", "application/rtf": "rtf",
        "application/msword": "doc", "application/vnd.ms-excel": "xls",
        "application/vnd.ms-powerpoint": "ppt", "application/json": "json",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "text/csv": "csv", "text/plain": "txt", "text/html": "html",
        "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif",
        "image/svg+xml": "svg", "audio/mpeg": "mp3", "video/mp4": "mp4"
    };

    const extensionOf = (sName) => {
        if (!sName) return "";
        const sClean = sName.split("?")[0].split("#")[0];
        const iDot = sClean.lastIndexOf(".");
        const iSlash = sClean.lastIndexOf("/");
        if (iDot <= iSlash + 1) return "";
        const sExtension = sClean.slice(iDot + 1).toLowerCase();
        return /^[a-z0-9]{1,8}$/.test(sExtension) ? sExtension : "";
    };

    const lLinks = [];
    const setSeen = new Set();
    for (const elAnchor of Array.from(
            document.querySelectorAll("a[href], area[href], link[href][download]"))) {
        let sAbsolute = "";
        try {
            sAbsolute = new URL(elAnchor.getAttribute("href"), window.location.href).href;
        } catch (error) {
            continue;
        }
        if (!sAbsolute.startsWith("http")) continue;
        if (setSeen.has(sAbsolute)) continue;

        let sExtension = "";
        let sSource = "";

        // The download attribute carries the name the file will be saved as,
        // which is the most reliable answer there is and is often the only one
        // when the address itself has no file name in it.
        const sDownload = elAnchor.getAttribute("download");
        if (sDownload) {
            sExtension = extensionOf(sDownload);
            if (sExtension) sSource = "download attribute";
        }

        // The address, which is the usual case.
        if (!sExtension) {
            try {
                sExtension = extensionOf(new URL(sAbsolute).pathname);
                if (sExtension) sSource = "address";
            } catch (error) {
                sExtension = "";
            }
        }

        // A declared type, for an address that names no file at all. A link to
        // /download/12345 with type application/pdf is a PDF, and skipping it
        // for want of a dot in the address loses exactly the files a reader
        // most often wants.
        if (!sExtension) {
            const sType = (elAnchor.getAttribute("type") || "").toLowerCase().split(";")[0].trim();
            if (dMimeExtensions[sType]) {
                sExtension = dMimeExtensions[sType];
                sSource = "declared type";
            }
        }

        // Nothing said what it is, but the link says it is a download. Marked
        // as unknown so it can be offered, since the server will name it in
        // its response and HomerView reads that name.
        if (!sExtension && elAnchor.hasAttribute("download")) {
            sExtension = "unknown";
            sSource = "download attribute without a name";
        }

        if (!sExtension) continue;
        setSeen.add(sAbsolute);
        lLinks.push({
            extension: sExtension,
            source: sSource,
            text: (elAnchor.textContent || elAnchor.getAttribute("aria-label") || "").trim().slice(0, 200),
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
    # Everything found is offered; what is filled in for you is the subset
    # worth having by default. A reader who wants the web pages types html.
    lDefault = [s for s in lExtensions if s not in setNotByDefault]
    dSources = {}
    for dLink in lUnique:
        sSource = dLink.get("source", "address")
        dSources[sSource] = dSources.get(sSource, 0) + 1
    homerLog.info(f"Extensions offered: {lExtensions}")
    homerLog.info(f"Filled in by default: {lDefault}")
    homerLog.info(f"Links by extension: {dCounts}")
    homerLog.info(f"How each link was identified: {dSources}")
    return {
        "counts": dCounts,
        "default": lDefault,
        "extensions": lExtensions,
        "links": lUnique,
        "pageUrl": sPageUrl,
        "sessionId": sSessionId,
    }


def describeExtensions(lExtensions, dCounts):
    """Say what each kind is, so the chooser is readable rather than cryptic."""
    lLines = []
    for sExtension in lExtensions:
        sWhat = dExtensionNames.get(sExtension, "")
        iCount = dCounts.get(sExtension, 0)
        if sWhat:
            lLines.append(f"{sExtension}: {sWhat}, {iCount}")
        else:
            lLines.append(f"{sExtension}: {iCount}")
    return lLines


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


def isTransient(exception):
    """Say whether an error is worth trying again."""
    sText = str(exception).lower()
    return any(s in sText for s in setTransientErrors)


def describeFailure(exception):
    """Say in ordinary words why a file did not arrive.

    A reader who is told ten files failed learns nothing they can act on. Told
    that ten addresses could not be found, they know the page is old and the
    files have moved, which is a different problem from a server refusing them.
    """
    sText = str(exception).lower()
    if "getaddrinfo" in sText or "name resolution" in sText:
        return _("the address could not be found")
    if "timed out" in sText or "timeout" in sText:
        return _("the server did not answer in time")
    if "404" in sText:
        return _("the file is no longer there")
    if "403" in sText:
        return _("the server refused it")
    if "401" in sText:
        return _("it needs a sign in")
    if "certificate" in sText or "ssl" in sText:
        return _("the secure connection failed")
    if "connection" in sText:
        return _("the connection failed")
    return str(exception)


def downloadOne(dLink, sPageUrl, sUserAgent, sCookies, pathFolder):
    sFileUrl = resolveDownloadUrl(dLink["url"])
    sExtension = dLink.get("extension", "")
    request = urllib.request.Request(
        sFileUrl, headers=buildHeaders(sFileUrl, sPageUrl, sUserAgent, sCookies)
    )
    # Try again once on an error that is likely to pass.
    for iAttempt in range(1, retryAttempts + 1):
        try:
            return fetchOne(request, dLink, pathFolder)
        except Exception as exception:
            if iAttempt >= retryAttempts or not isTransient(exception):
                raise
            homerLog.info(
                f"Attempt {iAttempt} failed on {abbreviate(dLink.get('url', ''), 120)}: "
                f"{exception}. Waiting {retryPauseSeconds} seconds and trying once more."
            )
            time.sleep(retryPauseSeconds)


def fetchOne(request, dLink, pathFolder):
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
    dReasons = {}
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
            sReason = describeFailure(exception)
            dReasons[sReason] = dReasons.get(sReason, 0) + 1
            homerLog.warning(
                f"Failed: {abbreviate(dLink['url'], 200)} because {sReason} ({exception})")
            if functionAnnounce:
                # Translators: Spoken when one file in a download fails.
                functionAnnounce(_("Error"))
    homerLog.info(f"Downloaded {len(lFiles)} files, {iFailed} failed")
    if dReasons:
        homerLog.info(f"Why they failed: {dReasons}")
    return {
        "failed": iFailed,
        "reasons": dReasons,
        "files": lFiles,
        "folder": str(pathFolder),
        "saved": len(lFiles),
    }
