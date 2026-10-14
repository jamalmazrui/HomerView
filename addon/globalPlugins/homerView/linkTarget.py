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
import html.parser
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


class TooManyRedirects(Exception):
    """A link that redirects more than maximumRedirects times. Its message names the last address reached."""


class Redirecting(urllib.request.HTTPRedirectHandler):
    """Follow redirects, and remember every step.

    Where a link ends up is what matters, and it is often not where it points.
    Recording the path is what lets the reader be told that a link to one site
    finished at another.

    THE LIMIT IS THIS ONE (14 October 2026, from an audit by another AI).
    maximumRedirects was declared and never used, so urllib's own limit of ten
    applied, with a message about an infinite loop. The ninth redirect now
    stops the fetch, and the message names the last address reached.
    """

    max_redirections = maximumRedirects + 1

    def __init__(self):
        self.lChain = []

    def redirect_request(self, request, response, iCode, sMessage, dHeaders, sNewUrl):
        if len(self.lChain) >= maximumRedirects:
            raise TooManyRedirects(_(
                "The link redirects more than {count} times, so HomerView stopped following it. "
                "The last address reached was {address}").format(
                count=maximumRedirects, address=self.lChain[-1][1]))
        self.lChain.append((iCode, sNewUrl))
        return super().redirect_request(request, response, iCode, sMessage, dHeaders, sNewUrl)


class PageFactsParser(html.parser.HTMLParser):
    """The facts readPageFacts wants, read by an HTML parser rather than by patterns.

    BY THE MARKUP, NOT ITS ORDER (14 October 2026, from an audit by another
    AI). The patterns expected name or property before content, so a meta
    element written the other way round, which is just as valid, gave nothing:
    an author's name went unsaid. A parser reads attributes in any order, in
    any case, quoted or not, across lines, with entities decoded.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.dMeta = {}
        self.sTitle = ""
        self.bInTitle = False
        self.sLanguage = ""
        self.sTime = ""

    def handle_starttag(self, sTag, lAttributes):
        dAttributes = {sName.lower(): (sValue or "") for sName, sValue in lAttributes}
        if sTag == "meta":
            sKey = (dAttributes.get("property") or dAttributes.get("name") or "").strip().lower()
            sContent = " ".join(dAttributes.get("content", "").split())
            if sKey and sContent and sKey not in self.dMeta: self.dMeta[sKey] = sContent
        elif sTag == "title" and not self.sTitle:
            self.bInTitle = True
        elif sTag == "html" and not self.sLanguage:
            self.sLanguage = dAttributes.get("lang", "").strip()
        elif sTag == "time" and not self.sTime:
            self.sTime = dAttributes.get("datetime", "").strip()

    def handle_endtag(self, sTag):
        if sTag == "title": self.bInTitle = False

    def handle_data(self, sData):
        if self.bInTitle: self.sTitle += sData


def readHead(sHtml):
    """A PageFactsParser that has read sHtml; a damaged page gives what was read before the damage."""
    oParser = PageFactsParser()
    try:
        oParser.feed(sHtml)
        oParser.close()
    except Exception as exception:
        homerLog.info(f"The page's markup could not all be read: {exception}")
    return oParser


def firstOf(oParser, *lKeys):
    """The first of these meta names or properties that the page fills in."""
    for sKey in lKeys:
        sValue = oParser.dMeta.get(sKey, "")
        if sValue: return sValue
    return ""


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


def readPageFacts(sHtml):
    """Pull what a reader would want to know out of a page's head.

    The same five conventions metadata.py reads, in the same order of
    preference, because a page that fills in Open Graph and nothing else is
    common and its title is still its title.
    """
    oParser = readHead(sHtml)
    dFacts = {}
    dFacts["title"] = firstOf(oParser, "og:title", "twitter:title") or " ".join(oParser.sTitle.split())
    dFacts["description"] = firstOf(oParser, "description", "og:description")
    dFacts["site"] = firstOf(oParser, "og:site_name")
    dFacts["author"] = firstOf(oParser, "author", "article:author")
    dFacts["published"] = firstOf(oParser, "article:published_time") or oParser.sTime
    dFacts["language"] = oParser.sLanguage
    dFacts["kind"] = firstOf(oParser, "og:type")

    # A rough sense of length, from the visible text. Not exact, and does not
    # need to be: the question is whether this is a paragraph or an hour.
    # MENUS ARE NOT THE ARTICLE (14 October 2026, from an audit by another AI): the navigation, header, footer and
    # side panels of a page were counted as its words, so a long menu could pass for content. A section the part read
    # ends inside has no closing tag, so it runs to the end of what was read.
    sBody = re.sub(r"<(script|style|nav|header|footer|aside|noscript)\b[^>]*>.*?(?:</\1>|\Z)", " ", sHtml, flags=re.I | re.S)
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


def lengthLine(iWords, bTruncated):
    """How long the page is, as far as the part read can tell; "" when it is too short to be worth saying.

    A SAMPLE IS SAID TO BE ONE (14 October 2026, from an audit by another AI). Only the first readLimitBytes of a page
    are read, so a long page looked short: its words were counted in the first part alone, and a reading time was
    given as though for the whole. When the page goes on past what was read, the count is a lower bound and says
    so; and when the part read holds too little to judge, that is said rather than nothing.
    """
    iKb = readLimitBytes // 1024
    if bTruncated:
        if iWords > 200:
            return _("At least {count} words, so at least {minutes} minutes: only its first {kb} KB were read, and it goes on.").format(
                count=iWords, minutes=max(1, round(iWords / 220)), kb=iKb)
        return _("Only its first {kb} KB were read, and it goes on, so its length is not known.").format(kb=iKb)
    if iWords > 200:
        return _("Roughly {count} words, about {minutes} minutes.").format(count=iWords, minutes=max(1, round(iWords / 220)))
    return ""


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
            # Whether the page goes on past what was read: one byte more is enough to know.
            bTruncated = bool(len(bBytes) >= readLimitBytes and response.read(1))
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
            sLength = lengthLine(dFacts.get("words", 0), bTruncated)
            if sLength:
                lLines.append("")
                lLines.append(sLength)
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
