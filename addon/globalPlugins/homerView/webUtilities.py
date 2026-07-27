"""Look things up on the web without leaving HomerView, and without a key.

The uploaded WebClient scripts are from about 2009, and most of what they
called is gone: outside.in, nextstop, tweetmeme, letsbetrends, the free
WhitePages and ZoomInfo tiers, bighugelabs, the old Google AJAX endpoints.
That is not decay so much as a change of business model. In 2009 a public API
was how a company got attention; by about 2015 it was how a company got paid,
and the free tier became a key, then a quota, then a credit card.

ProgrammableWeb, which catalogued that world, shut down in 2022 after
seventeen years. So the question this module answers is a narrower one than it
would have been then: what is still there for nothing.

The answer is better than expected, and the pattern is clear. What survives
without a key is mostly funded by somebody who is not selling the data:
governments, universities, libraries, museums, and volunteer projects. That is
also, as it happens, the data most worth having.

Everything here needs no key, no account and no payment. Where a service asks
something of callers in return, that request is honoured: a User-Agent naming
this program, and a pause between calls to the same host. The pause is not
politeness for its own sake. These are shared services with no revenue from
us, and a program that hammers one is why the next one asks for a key.
"""

import json
import threading
import time
import urllib.parse
import urllib.request

import addonHandler

from .logger import abbreviate, homerLog, logError, logSection

addonHandler.initTranslation()

fetchTimeoutSeconds = 20.0
maximumResults = 10

# A program that identifies itself can be asked to stop. One that does not gets
# the whole user agent blocked, which is how these services die for everyone.
userAgent = "HomerView/1.0 (NVDA add-on; https://github.com/JamalMazrui/HomerView)"

# One second between calls to the same host, which is what Nominatim's usage
# policy asks for by name and what the others would ask for if they said.
politePauseSeconds = 1.0
dLastCall = {}
lockCalls = threading.Lock()


def fetch(sUrl, sAccept="application/json"):
    """Fetch a url, pausing if this host was called a moment ago."""
    sHost = urllib.parse.urlparse(sUrl).netloc
    with lockCalls:
        nSince = time.monotonic() - dLastCall.get(sHost, 0)
        if nSince < politePauseSeconds:
            nWait = politePauseSeconds - nSince
            homerLog.debug(f"Waiting {nWait:.2f}s before calling {sHost} again")
            time.sleep(nWait)
        dLastCall[sHost] = time.monotonic()
    homerLog.info(f"Fetching {abbreviate(sUrl, 200)}")
    request = urllib.request.Request(
        sUrl, headers={"Accept": sAccept, "User-Agent": userAgent})
    with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
        return response.read().decode("utf-8", errors="replace")


def fetchJson(sUrl):
    return json.loads(fetch(sUrl))


def quote(sText):
    return urllib.parse.quote(str(sText or "").strip())


# --- The lookups -----------------------------------------------------------
#
# Each returns a list of lines. A list rather than a paragraph because the
# result is shown in a message box, where a reader moves by line.


def lookupWord(dValues):
    sWord = dValues.get("word", "")
    """A definition, from a free dictionary that needs no key."""
    lLines = []
    try:
        lEntries = fetchJson(f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(sWord)}")
    except Exception as exception:
        homerLog.warning(f"The dictionary lookup failed: {exception}")
        return [("", [_("No definition was found for {word}.").format(word=sWord)])]
    for dEntry in lEntries[:2]:
        if dEntry.get("phonetic"):
            lLines.append(_("Pronounced {phonetic}").format(phonetic=dEntry["phonetic"]))
        for dMeaning in (dEntry.get("meanings") or [])[:4]:
            lLines.append("")
            lLines.append(str(dMeaning.get("partOfSpeech", "")))
            for dDefinition in (dMeaning.get("definitions") or [])[:3]:
                lLines.append("  " + str(dDefinition.get("definition", "")))
                if dDefinition.get("example"):
                    lLines.append("    " + _("Example: {text}").format(
                        text=dDefinition["example"]))
    return [("", lLines)] if lLines else [("", [_("No definition was found for {word}.").format(word=sWord)])]


def lookupRelatedWords(dValues):
    sWord = dValues.get("word", "")
    """Synonyms and related words, from Datamuse, which needs no key.

    This replaces the thesaurus the old scripts used, which now wants a key.
    """
    lLines = []
    for sLabel, sParameter in (
        (_("Means much the same"), "ml"),
        (_("Sounds like"), "sl"),
        (_("Often follows it"), "rel_bga"),
    ):
        try:
            lWords = fetchJson(f"https://api.datamuse.com/words?{sParameter}={quote(sWord)}&max=12")
        except Exception:
            continue
        if lWords:
            lLines.append(sLabel + ": " + ", ".join(d.get("word", "") for d in lWords))
    return [("", lLines)] if lLines else [("", [_("Nothing related to {word} was found.").format(word=sWord)])]


def lookupEncyclopedia(dValues):
    sSubject = dValues.get("subject", "")
    """The opening of a Wikipedia article, which needs no key."""
    try:
        dPage = fetchJson(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + quote(sSubject.replace(" ", "_")))
    except Exception as exception:
        homerLog.warning(f"The encyclopedia lookup failed: {exception}")
        return [("", [_("No article was found about {subject}.").format(subject=sSubject)])]
    lLines = [str(dPage.get("title", "")), ""]
    if dPage.get("description"):
        lLines.append(str(dPage["description"]))
        lLines.append("")
    lLines.append(str(dPage.get("extract", "")))
    if (dPage.get("content_urls") or {}).get("desktop", {}).get("page"):
        lLines.extend(["", dPage["content_urls"]["desktop"]["page"]])
    return [("", lLines)]


def lookupPlace(dValues):
    sPlace = dValues.get("place", "")
    """Where a place is, from OpenStreetMap's geocoder, which needs no key.

    Nominatim's usage policy asks for an identifying User-Agent and no more
    than one call a second. Both are honoured above.
    """
    try:
        lPlaces = fetchJson(
            f"https://nominatim.openstreetmap.org/search?q={quote(sPlace)}&format=json&limit=5")
    except Exception as exception:
        homerLog.warning(f"The place lookup failed: {exception}")
        return [("", [_("No place called {place} was found.").format(place=sPlace)])]
    lLines = []
    for dPlace in lPlaces:
        lLines.append(str(dPlace.get("display_name", "")))
        lLines.append(_("  Latitude {lat}, longitude {lon}").format(
            lat=dPlace.get("lat", ""), lon=dPlace.get("lon", "")))
        lLines.append("")
    return [("", lLines)] if lLines else [("", [_("No place called {place} was found.").format(place=sPlace)])]


def lookupWeather(dValues):
    sPlace = dValues.get("place", "")
    """A forecast, from Open-Meteo, which needs no key.

    Two calls: the place is turned into coordinates first, because a forecast
    service is not a gazetteer and should not be asked to be one.
    """
    try:
        lPlaces = fetchJson(
            f"https://nominatim.openstreetmap.org/search?q={quote(sPlace)}&format=json&limit=1")
        if not lPlaces:
            return [_("No place called {place} was found.").format(place=sPlace)]
        dPlace = lPlaces[0]
        dWeather = fetchJson(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={dPlace['lat']}&longitude={dPlace['lon']}"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&forecast_days={dValues.get('days') or 4}"
            f"&temperature_unit={'celsius' if str(dValues.get('units','')).lower().startswith('c') else 'fahrenheit'}&wind_speed_unit=mph&timezone=auto")
    except Exception as exception:
        homerLog.warning(f"The weather lookup failed: {exception}")
        return [("", [_("The weather could not be fetched.")])]
    dNow = dWeather.get("current", {})
    lLines = [
        str(dPlace.get("display_name", sPlace)),
        "",
        _("Now: {temp} degrees, humidity {humidity} percent, wind {wind} miles an hour").format(
            humidity=dNow.get("relative_humidity_2m", "?"),
            temp=dNow.get("temperature_2m", "?"),
            wind=dNow.get("wind_speed_10m", "?")),
        "",
    ]
    dDaily = dWeather.get("daily", {})
    for iDay, sDate in enumerate(dDaily.get("time", [])):
        lLines.append(_("{date}: high {high}, low {low}, rain {rain} percent").format(
            date=sDate,
            high=dDaily["temperature_2m_max"][iDay],
            low=dDaily["temperature_2m_min"][iDay],
            rain=dDaily.get("precipitation_probability_max", [None] * 9)[iDay]))
    return [("", lLines)]


def lookupBooks(dValues):
    sSubject = dValues.get("subject", "")
    """Books, from Open Library, which needs no key."""
    try:
        dResult = fetchJson(
            f"https://openlibrary.org/search.json?q={quote(sSubject)}&limit={maximumResults}")
    except Exception as exception:
        homerLog.warning(f"The book search failed: {exception}")
        return [("", [_("No books were found about {subject}.").format(subject=sSubject)])]
    lLines = []
    for dBook in dResult.get("docs", [])[:maximumResults]:
        lLines.append(str(dBook.get("title", "")))
        if dBook.get("author_name"):
            lLines.append("  " + ", ".join(dBook["author_name"][:3]))
        if dBook.get("first_publish_year"):
            lLines.append("  " + str(dBook["first_publish_year"]))
        lLines.append("")
    return [("", lLines)] if lLines else [("", [_("No books were found about {subject}.").format(subject=sSubject)])]


def lookupExchangeRate(dValues):
    """Currency, from the European Central Bank's rates, which need no key."""
    sFrom = (dValues.get("fromCurrency") or "USD").upper()
    sTo = (dValues.get("toCurrency") or "EUR").upper()
    sAmount = str(dValues.get("amount") or "1")
    try:
        dRates = fetchJson(f"https://api.frankfurter.app/latest?amount={quote(sAmount)}"
            f"&from={quote(sFrom)}&to={quote(sTo)}")
    except Exception as exception:
        homerLog.warning(f"The exchange rate lookup failed: {exception}")
        return [("", [_("That exchange rate could not be fetched.")])]
    lLines = [_("Rates for {date}, from the European Central Bank").format(
        date=dRates.get("date", "")), ""]
    for sCode, nRate in (dRates.get("rates") or {}).items():
        lLines.append(f"{sAmount} {dRates.get('base', sFrom)} = {nRate} {sCode}")
    return [("", lLines)]


def lookupEarthquakes(dValues):
    """Recent earthquakes, from the United States Geological Survey, no key."""
    try:
        dResult = fetchJson(
            "https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson&limit={quote(str(dValues.get('count') or 15))}"
            f"&minmagnitude={quote(str(dValues.get('magnitude') or 4.5))}&orderby=time")
    except Exception as exception:
        homerLog.warning(f"The earthquake lookup failed: {exception}")
        return [("", [_("The earthquake list could not be fetched.")])]
    lLines = []
    for dFeature in dResult.get("features", []):
        dProperties = dFeature.get("properties", {})
        import datetime

        sWhen = datetime.datetime.fromtimestamp(
            (dProperties.get("time") or 0) / 1000).strftime("%Y-%m-%d %H:%M")
        lLines.append(f"{dProperties.get('mag', '?')}  {dProperties.get('place', '')}")
        lLines.append("  " + sWhen)
    return [("", lLines)] if lLines else [("", [_("No recent earthquakes were reported.")])]


def lookupResearch(dValues):
    sSubject = dValues.get("subject", "")
    """Recent papers, from arXiv, which needs no key."""
    import re

    try:
        sXml = fetch(
            "https://export.arxiv.org/api/query"
            f"?search_query=all:{quote(sSubject)}"
            f"&max_results={quote(str(dValues.get('count') or 8))}&sortBy=submittedDate"
            "&sortOrder=descending", "application/atom+xml")
    except Exception as exception:
        homerLog.warning(f"The research lookup failed: {exception}")
        return [("", [_("No papers were found about {subject}.").format(subject=sSubject)])]
    lLines = []
    for sEntry in re.findall(r"<entry>(.*?)</entry>", sXml, re.S)[:8]:
        matchTitle = re.search(r"<title>(.*?)</title>", sEntry, re.S)
        matchDate = re.search(r"<published>(.*?)</published>", sEntry)
        if matchTitle:
            lLines.append(" ".join(matchTitle.group(1).split()))
            if matchDate:
                lLines.append("  " + matchDate.group(1)[:10])
            lLines.append("")
    return [("", lLines)] if lLines else [("", [_("No papers were found about {subject}.").format(subject=sSubject)])]


def lookupArchive(dValues):
    sUrl = dValues.get("url", "")
    """Whether a page was saved, from the Internet Archive, which needs no key.

    Worth having when a link is dead, which for a reader following a citation
    is often.
    """
    try:
        dResult = fetchJson(f"https://archive.org/wayback/available?url={quote(sUrl)}")
    except Exception as exception:
        homerLog.warning(f"The archive lookup failed: {exception}")
        return [("", [_("The archive could not be asked about that address.")])]
    dSnapshot = (dResult.get("archived_snapshots") or {}).get("closest") or {}
    if not dSnapshot.get("available"):
        return [("", [_("The Internet Archive has no copy of that page.")])]
    return [("", [
        _("The Internet Archive has a copy."),
        "",
        _("Saved: {when}").format(when=str(dSnapshot.get("timestamp", ""))[:8]),
        str(dSnapshot.get("url", "")),
    ])]


def lookupPostalCode(dValues):
    """Where a postal code is, from Zippopotam, which needs no key."""
    sCode = str(dValues.get("code") or "").strip()
    sCountry = (dValues.get("country") or "us").strip().lower()
    try:
        dResult = fetchJson(f"https://api.zippopotam.us/{quote(sCountry)}/{quote(sCode)}")
    except Exception as exception:
        homerLog.warning(f"The postal code lookup failed: {exception}")
        return [("", [_("That postal code was not found.")])]
    lLines = [f"{dResult.get('post code', '')}, {dResult.get('country', '')}", ""]
    for dPlace in dResult.get("places", []):
        lLines.append(f"{dPlace.get('place name', '')}, {dPlace.get('state', '')}")
    return [("", lLines)]


def lookupFacts(dValues):
    sSubject = dValues.get("subject", "")
    """Structured facts, from Wikidata, which needs no key.

    Wikipedia gives prose; Wikidata gives the same knowledge as fields, so a
    date of birth or a founding year comes back as a value rather than as a
    sentence to be read through. It is the same project, and just as free.
    """
    try:
        dSearch = fetchJson(
            "https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json"
            f"&language=en&limit=5&search={quote(sSubject)}")
    except Exception as exception:
        homerLog.warning(f"The Wikidata search failed: {exception}")
        return [("", [_("Nothing was found about {subject}.").format(subject=sSubject)])]
    lLines = []
    for dEntity in (dSearch.get("search") or [])[:5]:
        lLines.append(str(dEntity.get("label", "")))
        if dEntity.get("description"):
            lLines.append("  " + str(dEntity["description"]))
        if dEntity.get("concepturi"):
            lLines.append("  " + str(dEntity["concepturi"]))
        lLines.append("")
    return [("", lLines)] if lLines else [("", [_("Nothing was found about {subject}.").format(subject=sSubject)])]


def lookupGoogleBooks(dValues):
    sSubject = dValues.get("subject", "")
    """Books, from Google Books, which answers without a key.

    Offered alongside Open Library because the two disagree usefully. Open
    Library is stronger on older and library-held books; Google Books is
    stronger on recent and self-published ones. A reader looking for a
    particular title is better served by being able to ask both.
    """
    try:
        dResult = fetchJson(
            "https://www.googleapis.com/books/v1/volumes"
            f"?q={quote(sSubject)}&maxResults={quote(str(dValues.get('count') or maximumResults))}")
    except Exception as exception:
        homerLog.warning(f"The Google Books search failed: {exception}")
        return [("", [_("No books were found about {subject}.").format(subject=sSubject)])]
    lLines = []
    for dItem in (dResult.get("items") or [])[:maximumResults]:
        dInfo = dItem.get("volumeInfo", {})
        lLines.append(str(dInfo.get("title", "")))
        if dInfo.get("subtitle"):
            lLines.append("  " + str(dInfo["subtitle"]))
        if dInfo.get("authors"):
            lLines.append("  " + ", ".join(dInfo["authors"][:3]))
        if dInfo.get("publishedDate"):
            lLines.append("  " + str(dInfo["publishedDate"]))
        lLines.append("")
    return [("", lLines)] if lLines else [("", [_("No books were found about {subject}.").format(subject=sSubject)])]


def lookupQuickAnswer(dValues):
    sQuestion = dValues.get("question", "")
    """A short factual answer, from DuckDuckGo's Instant Answer service.

    This needs no key. Worth a note: DuckDuckGo's search service is
    proprietary, and it is not listed on the HomerView start page for that
    reason. Calling a free service is a different question from recommending a
    company, and the answers here are largely drawn from Wikipedia anyway.
    Remove this entry if you would rather not call them at all.
    """
    try:
        dAnswer = fetchJson(
            "https://api.duckduckgo.com/"
            f"?q={quote(sQuestion)}&format=json&no_html=1&skip_disambig=1")
    except Exception as exception:
        homerLog.warning(f"The quick answer lookup failed: {exception}")
        return [("", [_("No quick answer was found.")])]
    lLines = []
    if dAnswer.get("Heading"):
        lLines.extend([str(dAnswer["Heading"]), ""])
    if dAnswer.get("AbstractText"):
        lLines.append(str(dAnswer["AbstractText"]))
        if dAnswer.get("AbstractSource"):
            lLines.append(_("Source: {source}").format(source=dAnswer["AbstractSource"]))
        if dAnswer.get("AbstractURL"):
            lLines.append(str(dAnswer["AbstractURL"]))
    if dAnswer.get("Answer"):
        lLines.extend([str(dAnswer["Answer"]), ""])
    for dTopic in (dAnswer.get("RelatedTopics") or [])[:6]:
        if isinstance(dTopic, dict) and dTopic.get("Text"):
            lLines.append("  " + str(dTopic["Text"]))
    return [("", lLines)] if lLines else [("", [_("No quick answer was found.")])]


# Each lookup declares the fields it needs, and the dialog is built from that.
# Squeezing two values into one box, as an earlier version did with the
# exchange rate and the postal code, saves a line of code and costs the user a
# guess about the separator every time they use it.
#
# A field is a name, a label, a default, and optionally a list of values to
# offer on F4. The name is what the lookup receives.
lUtilities = [
    (_("Define a word"), [("word", _("&Word:"), "", None)], lookupWord),
    (_("Words related to a word"), [("word", _("&Word:"), "", None)], lookupRelatedWords),
    (_("Look something up in Wikipedia"), [("subject", _("&Subject:"), "", None)],
     lookupEncyclopedia),
    (_("Facts about a subject"), [("subject", _("&Subject:"), "", None)], lookupFacts),
    (_("Quick answer to a question"), [("question", _("&Question:"), "", None)],
     lookupQuickAnswer),
    (_("Find a place"), [("place", _("&Place:"), "", None)], lookupPlace),
    (_("Weather forecast"), [
        ("place", _("&Place:"), "", None),
        ("days", _("&Days ahead:"), "4", ["1", "2", "3", "4", "5", "6", "7"]),
        ("units", _("&Units:"), "Fahrenheit", ["Fahrenheit", "Celsius"]),
    ], lookupWeather),
    (_("Find books in Open Library"), [
        ("subject", _("&Title, author or subject:"), "", None),
        ("count", _("&How many:"), "10", ["5", "10", "20", "40"]),
    ], lookupBooks),
    (_("Find books in Google Books"), [
        ("subject", _("&Title, author or subject:"), "", None),
        ("count", _("&How many:"), "10", ["5", "10", "20", "40"]),
    ], lookupGoogleBooks),
    (_("Exchange rate"), [
        ("fromCurrency", _("&From currency:"), "USD",
         ["AUD", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "INR", "JPY", "MXN", "USD", "ZAR"]),
        ("toCurrency", _("&To currency:"), "EUR",
         ["AUD", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "INR", "JPY", "MXN", "USD", "ZAR"]),
        ("amount", _("&Amount:"), "1", None),
    ], lookupExchangeRate),
    (_("Recent earthquakes"), [
        ("magnitude", _("&Smallest magnitude:"), "4.5", ["2.5", "4.5", "6.0", "7.0"]),
        ("count", _("&How many:"), "15", ["5", "15", "30", "50"]),
    ], lookupEarthquakes),
    (_("Recent research papers"), [
        ("subject", _("&Subject:"), "", None),
        ("count", _("&How many:"), "8", ["5", "8", "20", "40"]),
    ], lookupResearch),
    (_("Is a page in the Internet Archive"), [("url", _("&Web address:"), "", None)],
     lookupArchive),
    (_("Where is a postal code"), [
        ("code", _("Postal &code:"), "", None),
        ("country", _("Coun&try:"), "us",
         ["au", "br", "ca", "de", "es", "fr", "gb", "in", "it", "jp", "mx", "nl", "us"]),
    ], lookupPostalCode),
]


def runUtility(iIndex, dValues):
    """Run one lookup and return its result as sections a page can render."""
    logSection(f"Command: web utility {iIndex}")
    sName, _lFields, functionLookup = lUtilities[iIndex]
    homerLog.info(f"{sName}: {abbreviate(str(dValues), 200)}")
    lSections = functionLookup(dValues)
    iLines = sum(len(lLines) for _sHeading, lLines in lSections)
    homerLog.info(f"{sName} returned {len(lSections)} sections, {iLines} lines")
    return {"name": sName, "sections": lSections, "values": dValues}



