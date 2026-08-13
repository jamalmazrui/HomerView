"""What is behind a link, without going there.

A sighted reader hovers a link and the address appears in the corner. They see
the domain, and often that is enough: they can tell a link to the article from
a link to the advertisement, and they can tell that "click here" goes somewhere
unrelated to what it says. A blind reader has the address on Alt+U, but an
address is not an answer. Is it a page or a file? How big? Does it still exist?
Does it go where the link's own words claim?

This asks the target and reports what came back. It is deliberately more than
the address, because the address is the part the reader already had.

Nothing is downloaded and nothing is opened. The request asks for headers only
where the server will answer that way, and reads a limited amount of the page
where it will not. A file is never fetched in full: knowing that something is
a 300 megabyte archive is exactly the reason not to fetch it.

The redirect chain is followed and reported, because where a link ends up is
what matters and it is often not where it points. A shortener, a tracker and a
sign-in wall all look the same from the page, and all three are worth knowing
about before following.
"""

import html
import re
import urllib.error
import urllib.parse
import urllib.request

import addonHandler

from .logger import abbreviate, homerLog, logError, logSection

addonHandler.initTranslation()

# Enough of a page to hold the head, and no more. Metadata lives in the first
# few kilobytes, and reading a whole page to find a title is wasteful when the
# reader is waiting.
readLimitBytes = 96 * 1024
requestTimeoutSeconds = 15.0
maximumRedirects = 8

userAgent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
)

# What a content type means, said as a person would say it.
dTypeNames = {
    "application/epub+zip": "EPUB ebook",
    "application/json": "JSON data",
    "application/msword": "Word document",
    "application/pdf": "PDF document",
    "application/rtf": "rich text",
    "application/vnd.ms-excel": "Excel workbook",
    "application/vnd.ms-powerpoint": "PowerPoint presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        "PowerPoint presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel workbook",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word document",
    "application/x-7z-compressed": "7-Zip archive",
    "application/zip": "Zip archive",
    "audio/mpeg": "MP3 audio",
    "image/gif": "GIF image",
    "image/jpeg": "JPEG image",
    "image/png": "PNG image",
    "image/svg+xml": "SVG image",
    "text/csv": "comma separated values",
    "text/html": "web page",
    "text/plain": "plain text",
    "video/mp4": "MP4 video",
}

# Hosts whose only purpose is to redirect. Worth naming, because a reader
# should know the link is not telling them where it goes.
setShorteners = {
    "bit.ly", "buff.ly", "cutt.ly", "goo.gl", "is.gd", "lnkd.in", "ow.ly",
    "rebrand.ly", "t.co", "tinyurl.com", "trib.al",
}


class Redirecting(urllib.request.HTTPRedirectHandler):
    """Follow redirects, and remember every step.

    Where a link ends up is what matters, and it is often not where it points.
    Recording the path is what lets the reader be told that a link to one site
    finished at another.
    """

    def __init__(self):
        self.lChain = []

    def redirect_request(self, request, response, iCode, sMessage, dHeaders, sNewUrl):
        self.lChain.append((iCode, sNewUrl))
        return super().redirect_request(request, response, iCode, sMessage, dHeaders, sNewUrl)


def openTarget(sUrl, sMethod="GET"):
    """Fetch a target, following redirects, and return the response and path."""
    redirecting = Redirecting()
    opener = urllib.request.build_opener(redirecting)
    request = urllib.request.Request(sUrl, method=sMethod, headers={
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": userAgent,
    })
    response = opener.open(request, timeout=requestTimeoutSeconds)
    return response, redirecting.lChain


def describeSize(vBytes):
    """A size as a phrase, from the shared formatter."""
    from .homer import util

    return util.formatBytes(vBytes) if vBytes not in (None, "") else ""


def firstMatch(sHtml, *lPatterns):
    for sPattern in lPatterns:
        match = re.search(sPattern, sHtml, re.I | re.S)
        if match:
            sValue = " ".join(html.unescape(match.group(1)).split())
            if sValue:
                return sValue
    return ""


def readPageFacts(sHtml):
    """Pull what a reader would want to know out of a page's head.

    The same five conventions metadata.py reads, in the same order of
    preference, because a page that fills in Open Graph and nothing else is
    common and its title is still its title.
    """
    dFacts = {}
    dFacts["title"] = firstMatch(
        sHtml,
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)',
        r"<title[^>]*>(.*?)</title>",
    )
    dFacts["description"] = firstMatch(
        sHtml,
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
    )
    dFacts["site"] = firstMatch(
        sHtml, r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)')
    dFacts["author"] = firstMatch(
        sHtml,
        r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+property=["\']article:author["\'][^>]+content=["\']([^"\']+)',
    )
    dFacts["published"] = firstMatch(
        sHtml,
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
        r'<time[^>]+datetime=["\']([^"\']+)',
    )
    dFacts["language"] = firstMatch(sHtml, r'<html[^>]+lang=["\']([^"\']+)')
    dFacts["kind"] = firstMatch(
        sHtml, r'<meta[^>]+property=["\']og:type["\'][^>]+content=["\']([^"\']+)')

    # A rough sense of length, from the visible text. Not exact, and does not
    # need to be: the question is whether this is a paragraph or an hour.
    sBody = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", sHtml, flags=re.I | re.S)
    sBody = re.sub(r"<[^>]+>", " ", sBody)
    iWords = len(re.findall(r"[A-Za-z']+", sBody))
    dFacts["words"] = iWords

    # Whether reading it will mean signing in, which is worth knowing before
    # following rather than after.
    sLower = sHtml.lower()
    dFacts["wall"] = any(s in sLower for s in (
        "subscribe to continue", "subscribers only", "paywall",
        "sign in to continue", "log in to continue", "create a free account",
        "you have reached your article limit",
    ))
    return dFacts


def describeLink(sUrl, sLinkText=""):
    """Ask a link's target what it is, and return lines describing it."""
    logSection("Command: describe the link target")
    homerLog.info(f"Asking about {abbreviate(sUrl, 300)}")
    sHost = urllib.parse.urlparse(sUrl).netloc.lower()
    lLines = []

    try:
        response, lChain = openTarget(sUrl)
    except urllib.error.HTTPError as exception:
        homerLog.warning(f"The target answered {exception.code}")
        return [
            _("The link does not work."),
            "",
            _("The server answered {code}, {reason}.").format(
                code=exception.code, reason=exception.reason),
            sUrl,
        ]
    except Exception as exception:
        logError("The link target could not be reached")
        return [
            _("The link could not be reached."),
            "",
            str(exception),
            sUrl,
        ]

    try:
        sFinalUrl = getattr(response, "url", sUrl) or sUrl
        dHeaders = getattr(response, "headers", {})
        sType = str(dHeaders.get("Content-Type", "")).split(";")[0].strip().lower()
        sLength = dHeaders.get("Content-Length", "")
        sDisposition = str(dHeaders.get("Content-Disposition", ""))
        sFinalHost = urllib.parse.urlparse(sFinalUrl).netloc.lower()

        # What kind of thing it is.
        sWhat = dTypeNames.get(sType, sType or _("something the server did not name"))
        lLines.append(_("A {what}").format(what=sWhat))

        sSize = describeSize(sLength)
        if sSize:
            lLines.append(_("about {size}").format(size=sSize))

        # A file that will be saved rather than shown.
        if "attachment" in sDisposition.lower():
            match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', sDisposition, re.I)
            if match:
                lLines.append(_("saved as {name}").format(
                    name=urllib.parse.unquote(match.group(1))))

        # Where it actually ends up.
        if sFinalHost and sFinalHost != sHost:
            lLines.append("")
            lLines.append(_("It goes to {host}, not {claimed}.").format(
                claimed=sHost, host=sFinalHost))
        if sHost in setShorteners:
            lLines.append(_("The link itself only redirects, so its address said nothing."))
        if lChain:
            lLines.append(_("{count} redirects on the way.").format(count=len(lChain)))

        # For a page, what it is about.
        if sType == "text/html":
            bBytes = response.read(readLimitBytes)
            sHtml = bBytes.decode("utf-8", errors="replace")
            dFacts = readPageFacts(sHtml)
            lLines.append("")
            if dFacts.get("title"):
                lLines.append(dFacts["title"])
            if dFacts.get("site"):
                lLines.append(_("on {site}").format(site=dFacts["site"]))
            if dFacts.get("author"):
                lLines.append(_("by {author}").format(author=dFacts["author"]))
            if dFacts.get("published"):
                lLines.append(_("published {date}").format(date=dFacts["published"][:10]))
            if dFacts.get("description"):
                lLines.append("")
                lLines.append(dFacts["description"])
            if dFacts.get("words") > 200:
                iMinutes = max(1, round(dFacts["words"] / 220))
                lLines.append("")
                lLines.append(_("Roughly {count} words, about {minutes} minutes.").format(
                    count=dFacts["words"], minutes=iMinutes))
            if dFacts.get("wall"):
                lLines.append("")
                lLines.append(_("It looks as though reading it needs a subscription or an account."))
            if dFacts.get("language") and not dFacts["language"].lower().startswith("en"):
                lLines.append(_("The page says it is in {language}.").format(
                    language=dFacts["language"]))

            # Does the link say where it goes? A link whose words name a
            # different subject than the page is worth flagging, because that
            # is the mismatch a sighted reader catches by hovering.
            sTitle = (dFacts.get("title") or "").lower()
            sText = " ".join((sLinkText or "").split()).lower()
            if sText and sTitle and len(sText) > 8:
                setText = {s for s in re.findall(r"[a-z']{4,}", sText)}
                setTitle = {s for s in re.findall(r"[a-z']{4,}", sTitle)}
                if setText and not (setText & setTitle):
                    lLines.append("")
                    lLines.append(
                        _("The link's words and the page's title have nothing in common."))
    finally:
        try:
            response.close()
        except Exception:
            pass

    lLines.append("")
    lLines.append(sFinalUrl)
    homerLog.info(f"Described in {len(lLines)} lines")
    return lLines
