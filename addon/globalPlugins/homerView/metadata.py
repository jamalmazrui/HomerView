"""What a page says about itself: title, author, publisher, date, licence.

Web pages carry a surprising amount of description that a reader never hears,
because it lives in the head of the document rather than in its body. A screen
reader announces the title and nothing else. Who wrote this, when, for whom,
and under what licence are all commonly present and never spoken.

There is no single convention, which is why this reads five of them:

    Plain meta elements, the oldest: description, author, keywords, copyright.
    Open Graph, written for social previews but the most consistently filled in
    of any scheme in practice.
    Twitter cards, which overlap Open Graph and sometimes carry what it lacks.
    Dublin Core, the librarians' scheme, common on academic and government
    sites and the only one that names a rights holder properly.
    JSON-LD following schema.org, which news sites and publishers now use, and
    which carries author, publisher, date and licence as structured data.

The Python package for this outside a browser is extruct, which reads JSON-LD,
microdata, RDFa, Open Graph and microformats from fetched markup. It is not
usable here: an NVDA add-on has only the standard library, and more to the
point, fetched markup is the wrong source. Reading the live document through
the protocol sees metadata that script inserted after load, which on a modern
publishing site is most of it.
"""

import json

from .logger import abbreviate, homerLog, logSection

metadataTimeoutSeconds = 30.0

extractScript = r"""(() => {
    const dResult = {jsonLd: [], links: {}, meta: {}, page: {}};
    const put = (dBag, sKey, sValue) => {
        if (!sKey || !sValue) return;
        sValue = String(sValue).trim();
        if (!sValue) return;
        if (dBag[sKey] === undefined) dBag[sKey] = sValue;
    };

    dResult.page.title = document.title || "";
    dResult.page.language = document.documentElement.getAttribute("lang") || "";
    dResult.page.address = location.href;
    dResult.page.characters = (document.body ? (document.body.innerText || "").length : 0);
    dResult.page.lastModified = document.lastModified || "";

    for (const el of Array.from(document.querySelectorAll("meta"))) {
        const sKey = (el.getAttribute("name") || el.getAttribute("property") ||
                      el.getAttribute("http-equiv") || el.getAttribute("itemprop") || "").trim();
        put(dResult.meta, sKey.toLowerCase(), el.getAttribute("content"));
    }

    for (const el of Array.from(document.querySelectorAll("link[rel]"))) {
        const sRel = (el.getAttribute("rel") || "").trim().toLowerCase();
        if (["license", "canonical", "author", "alternate", "publisher"].indexOf(sRel) !== -1) {
            put(dResult.links, sRel, el.getAttribute("href"));
        }
    }

    for (const el of Array.from(document.querySelectorAll('script[type="application/ld+json"]'))) {
        try {
            dResult.jsonLd.push(JSON.parse(el.textContent));
        } catch (error) {
            // A malformed block is common and is not worth failing over.
        }
    }

    const elTime = document.querySelector("time[datetime]");
    if (elTime) put(dResult.page, "timeElement", elTime.getAttribute("datetime"));
    const elItemAuthor = document.querySelector('[itemprop="author"]');
    if (elItemAuthor) put(dResult.page, "microdataAuthor", (elItemAuthor.textContent || "").trim());

    return dResult;
})()"""

# Each field, and every place it is conventionally written, best source first.
lFieldSources = [
    ("Title", ["og:title", "twitter:title", "dc.title", "citation_title"]),
    ("Site", ["og:site_name", "application-name", "apple-mobile-web-app-title"]),
    ("Author", ["author", "article:author", "dc.creator", "citation_author", "twitter:creator"]),
    ("Publisher", ["publisher", "dc.publisher", "og:site_name", "citation_journal_title"]),
    ("Published", ["article:published_time", "datepublished", "dc.date", "date",
                   "citation_publication_date", "og:updated_time"]),
    ("Modified", ["article:modified_time", "datemodified", "last-modified", "dc.modified"]),
    ("Summary", ["description", "og:description", "twitter:description", "dc.description"]),
    ("Licence", ["dc.rights", "rights", "copyright", "license"]),
    ("Language", ["dc.language", "content-language", "og:locale"]),
    ("Type", ["og:type", "dc.type"]),
    ("Section", ["article:section", "dc.subject"]),
    ("Keywords", ["keywords", "news_keywords", "dc.subject"]),
    ("Built with", ["generator"]),
]

lJsonLdFields = [
    ("Title", ["headline", "name"]),
    ("Author", ["author"]),
    ("Publisher", ["publisher"]),
    ("Published", ["datePublished"]),
    ("Modified", ["dateModified"]),
    ("Summary", ["description", "abstract"]),
    ("Licence", ["license"]),
    ("Type", ["@type"]),
]


def flattenJsonLd(vNode, dOut, iDepth=0):
    """Pull the useful fields out of a JSON-LD block, however it is nested."""
    if iDepth > 4:
        return
    if isinstance(vNode, list):
        for vItem in vNode:
            flattenJsonLd(vItem, dOut, iDepth + 1)
        return
    if not isinstance(vNode, dict):
        return
    for sLabel, lKeys in lJsonLdFields:
        for sKey in lKeys:
            if sKey not in vNode or sLabel in dOut:
                continue
            vValue = vNode[sKey]
            if isinstance(vValue, dict):
                vValue = vValue.get("name") or vValue.get("@id") or ""
            elif isinstance(vValue, list):
                lNames = []
                for vItem in vValue:
                    if isinstance(vItem, dict):
                        lNames.append(str(vItem.get("name") or ""))
                    else:
                        lNames.append(str(vItem))
                vValue = ", ".join(s for s in lNames if s)
            sValue = str(vValue or "").strip()
            if sValue:
                dOut[sLabel] = sValue
    for sKey in ("@graph", "mainEntity", "mainEntityOfPage", "isPartOf"):
        if sKey in vNode:
            flattenJsonLd(vNode[sKey], dOut, iDepth + 1)


def summarise(dRaw):
    """Return the fields worth reporting, and where each came from."""
    dMeta = {k.lower(): v for k, v in (dRaw.get("meta") or {}).items()}
    dLinks = dRaw.get("links") or {}
    dPage = dRaw.get("page") or {}
    dJson = {}
    for vBlock in dRaw.get("jsonLd") or []:
        flattenJsonLd(vBlock, dJson)

    lFields = []
    for sLabel, lKeys in lFieldSources:
        sValue = ""
        sSource = ""
        for sKey in lKeys:
            if dMeta.get(sKey):
                sValue = dMeta[sKey]
                sSource = sKey
                break
        if not sValue and dJson.get(sLabel):
            sValue = dJson[sLabel]
            sSource = "JSON-LD"
        if not sValue and sLabel == "Licence" and dLinks.get("license"):
            sValue = dLinks["license"]
            sSource = "link rel=license"
        if not sValue and sLabel == "Title":
            sValue = dPage.get("title", "")
            sSource = "document title"
        if not sValue and sLabel == "Language":
            sValue = dPage.get("language", "")
            sSource = "html lang"
        if not sValue and sLabel == "Author" and dPage.get("microdataAuthor"):
            sValue = dPage["microdataAuthor"]
            sSource = "microdata"
        if not sValue and sLabel == "Published" and dPage.get("timeElement"):
            sValue = dPage["timeElement"]
            sSource = "time element"
        if sValue:
            lFields.append((sLabel, sValue, sSource))

    lExtra = []
    setUsed = {sKey for _sLabel, lKeys in lFieldSources for sKey in lKeys}
    for sKey in sorted(dMeta):
        if sKey in setUsed or sKey.startswith(("viewport", "theme-color", "msapplication", "format-detection")):
            continue
        lExtra.append((sKey, dMeta[sKey]))
    return lFields, lExtra, dLinks, dPage


def buildReportHtml(dRaw):
    import html

    def escape(vValue):
        return html.escape(str(vValue if vValue is not None else ""), quote=True)

    lFields, lExtra, dLinks, dPage = summarise(dRaw)
    lParts = ["<h1>Page information</h1>"]
    lParts.append(f"<p>{escape(dPage.get('address', ''))}</p>")
    if lFields:
        lParts.append("<h2>What this page says about itself</h2>")
        lParts.append("<table><thead><tr><th>Field</th><th>Value</th><th>Where it came from</th>"
                      "</tr></thead><tbody>")
        for sLabel, sValue, sSource in lFields:
            lParts.append(
                f"<tr><td>{escape(sLabel)}</td><td>{escape(sValue)}</td>"
                f"<td>{escape(sSource)}</td></tr>"
            )
        lParts.append("</tbody></table>")
    else:
        lParts.append("<h2>What this page says about itself</h2>")
        lParts.append(
            "<p>Nothing beyond its title. The page carries no description, author, date or "
            "licence in any of the five conventions checked.</p>"
        )

    if dLinks:
        lParts.append("<h2>Declared links</h2><ul>")
        for sRel in sorted(dLinks):
            lParts.append(
                f'<li>{escape(sRel)}: <a href="{escape(dLinks[sRel])}">'
                f"{escape(dLinks[sRel])}</a></li>"
            )
        lParts.append("</ul>")

    lParts.append("<h2>The document itself</h2><ul>")
    lParts.append(f"<li>Characters of readable text: {dPage.get('characters', 0)}</li>")
    if dPage.get("lastModified"):
        lParts.append(f"<li>Last modified, as the browser reports it: "
                      f"{escape(dPage['lastModified'])}</li>")
    lParts.append(f"<li>Structured data blocks: {len(dRaw.get('jsonLd') or [])}</li>")
    lParts.append("</ul>")

    if lExtra:
        lParts.append(f"<h2>Other meta elements ({len(lExtra)})</h2>")
        lParts.append("<table><thead><tr><th>Name</th><th>Content</th></tr></thead><tbody>")
        for sKey, sValue in lExtra[:60]:
            lParts.append(f"<tr><td>{escape(sKey)}</td><td>{escape(sValue)}</td></tr>")
        lParts.append("</tbody></table>")
    return "\n".join(lParts)


def readMetadata(cdpSession):
    """Read everything the focused page declares about itself."""
    logSection("Command: page information")
    dTarget, sSessionId = cdpSession.findActivePageSession()
    dRaw = cdpSession.evaluate(sSessionId, extractScript, metadataTimeoutSeconds)
    if not dRaw:
        raise RuntimeError("The page information could not be read")
    lFields, lExtra, dLinks, dPage = summarise(dRaw)
    homerLog.info(
        f"Page information: {len(lFields)} named fields, {len(lExtra)} other meta elements, "
        f"{len(dRaw.get('jsonLd') or [])} structured data blocks"
    )
    for sLabel, sValue, sSource in lFields:
        homerLog.debug(f"  {sLabel} ({sSource}): {abbreviate(sValue, 200)}")
    return {
        "address": dPage.get("address", ""),
        "fields": lFields,
        "html": buildReportHtml(dRaw),
        "title": dPage.get("title", ""),
    }
