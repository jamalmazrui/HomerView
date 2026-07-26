"""Summarise a page's structure the way JAWS Page Explorer does.

JAWS 2026 added Page Explorer on Insert+Shift+E, which puts an overview of the
current page into the Results Viewer: the page layout, where the main content
is, the links worth knowing about, and navigation tips with keystrokes tailored
to what the page actually contains. This is HomerView's equivalent, with two
deliberate differences.

The tips give NVDA keystrokes rather than JAWS ones, which is the part a JAWS
description cannot help an NVDA user with.

And the analysis is rule-based rather than sent to a language model. HomerView
has no AI service and inventing a dependency on one would be a poor trade: the
structural facts a screen reader user needs, which region holds the content,
whether a heading level is skipped, whether a header is pinned over the page,
are exact questions with exact answers, and a model would only paraphrase them
less reliably. What a model would add is prose about the subject matter, which
is a different feature and is better served by the main content command.

The visual section is the unusual part and the reason the command earns its
place. A screen reader flattens a page into a reading order, which hides things
a sighted reader gets for free: that a banner is pinned over the content, that a
dialog is open on top of everything, that a region is present in the markup but
invisible, that something visible has been hidden from assistive technology.
Only notable findings appear; a page with none of them says so.
"""

from .logger import abbreviate, homerLog, logSection

analysisTimeoutSeconds = 30.0
maximumHeadingsShown = 40
maximumLinksShown = 25
maximumRegionsShown = 20
wordsPerMinute = 200

analysisScript = r"""(() => {
    const text = el => (el && el.innerText ? el.innerText : "").trim();
    const label = el => {
        const sLabelled = el.getAttribute("aria-labelledby");
        if (sLabelled) {
            const elTarget = document.getElementById(sLabelled.split(/\s+/)[0]);
            if (elTarget) return text(elTarget).slice(0, 80);
        }
        return (el.getAttribute("aria-label") || el.getAttribute("title") || "").trim().slice(0, 80);
    };
    const visible = el => {
        const dStyle = getComputedStyle(el);
        if (dStyle.display === "none" || dStyle.visibility === "hidden" || dStyle.opacity === "0") return false;
        const dRect = el.getBoundingClientRect();
        return dRect.width > 1 && dRect.height > 1;
    };
    const offScreen = el => {
        const dRect = el.getBoundingClientRect();
        return dRect.right < 0 || dRect.bottom < 0 ||
            dRect.left > (window.innerWidth || 0) * 3 || dRect.top > (document.body.scrollHeight || 0) + 1000;
    };

    const dLandmarkTags = {
        header: "banner", nav: "navigation", main: "main",
        aside: "complementary", footer: "contentinfo", form: "form", section: "region"
    };
    const lLandmarkRoles = ["banner", "navigation", "main", "complementary", "contentinfo",
        "form", "search", "region"];

    // Regions
    const lRegions = [];
    const lRegionNodes = Array.from(document.querySelectorAll(
        "header,nav,main,aside,footer,form,section,[role]"));
    for (const elNode of lRegionNodes) {
        let sRole = (elNode.getAttribute("role") || "").toLowerCase();
        if (!sRole) {
            sRole = dLandmarkTags[elNode.tagName.toLowerCase()] || "";
            // A section or form is only a landmark when it is named.
            if ((sRole === "region" || sRole === "form") && !label(elNode)) sRole = "";
            // A header or footer is only a landmark at the top level.
            if ((sRole === "banner" || sRole === "contentinfo") &&
                elNode.closest("article,section,main,aside")) sRole = "";
        }
        if (!lLandmarkRoles.includes(sRole)) continue;
        const sText = text(elNode);
        lRegions.push({
            characters: sText.length,
            headings: elNode.querySelectorAll("h1,h2,h3,h4,h5,h6,[role=heading]").length,
            hidden: !visible(elNode),
            label: label(elNode),
            links: elNode.querySelectorAll("a[href]").length,
            role: sRole
        });
    }

    // Headings
    const lHeadings = [];
    for (const elNode of Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role=heading]"))) {
        let iLevel = parseInt(elNode.tagName.slice(1), 10);
        if (isNaN(iLevel)) iLevel = parseInt(elNode.getAttribute("aria-level") || "2", 10);
        lHeadings.push({level: iLevel, text: text(elNode).slice(0, 100), hidden: !visible(elNode)});
    }

    // Links
    const lAllLinks = Array.from(document.querySelectorAll("a[href]"));
    const setHrefs = new Set();
    const lImportant = [];
    const lSkipLinks = [];
    const dImportantWords = {
        "skip": "skip link", "search": "search", "sign in": "sign in", "log in": "sign in",
        "login": "sign in", "sign up": "sign up", "register": "sign up", "account": "account",
        "cart": "cart", "checkout": "checkout", "contact": "contact", "accessibility": "accessibility",
        "help": "help", "support": "support", "privacy": "privacy", "menu": "menu"
    };
    for (const elLink of lAllLinks) {
        const sHref = elLink.getAttribute("href") || "";
        setHrefs.add(sHref);
        const sLabel = (text(elLink) || label(elLink)).toLowerCase();
        if (!sLabel) continue;
        if (sHref.startsWith("#") && sLabel.includes("skip")) {
            lSkipLinks.push({text: text(elLink).slice(0, 80), visible: visible(elLink)});
            continue;
        }
        for (const sWord in dImportantWords) {
            if (sLabel.startsWith(sWord) || sLabel === sWord) {
                lImportant.push({kind: dImportantWords[sWord], text: text(elLink).slice(0, 80),
                    url: elLink.href});
                break;
            }
        }
    }

    // Forms, fields, tables
    const lTables = [];
    for (const elTable of Array.from(document.querySelectorAll("table"))) {
        const iHeaderCells = elTable.querySelectorAll("th").length;
        lTables.push({
            caption: text(elTable.querySelector("caption")).slice(0, 80),
            columns: elTable.rows.length ? elTable.rows[0].cells.length : 0,
            headerCells: iHeaderCells,
            rows: elTable.rows.length
        });
    }

    // Media and images
    const lImages = Array.from(document.querySelectorAll("img"));
    const iDecorative = lImages.filter(el => el.getAttribute("alt") === "").length;
    const iUnnamed = lImages.filter(el =>
        el.getAttribute("alt") === null && !el.getAttribute("aria-label") &&
        el.getAttribute("role") !== "presentation" && visible(el)).length;
    const lMedia = Array.from(document.querySelectorAll("video,audio"));
    const iAutoplay = lMedia.filter(el => el.hasAttribute("autoplay")).length;

    // Visual aspects a reading order hides
    const lPinned = [];
    const lDialogs = [];
    const lHiddenFromAt = [];
    const lVisuallyHidden = [];
    for (const elNode of Array.from(document.querySelectorAll("body *")).slice(0, 6000)) {
        const dStyle = getComputedStyle(elNode);
        if ((dStyle.position === "fixed" || dStyle.position === "sticky")) {
            const dRect = elNode.getBoundingClientRect();
            if (dRect.height > 40 && dRect.width > 200 && visible(elNode) &&
                !elNode.parentElement.closest("[data-homerview-pinned]")) {
                elNode.setAttribute("data-homerview-pinned", "1");
                lPinned.push({
                    height: Math.round(dRect.height),
                    position: dStyle.position,
                    role: elNode.getAttribute("role") || elNode.tagName.toLowerCase(),
                    top: Math.round(dRect.top)
                });
            }
        }
        if (elNode.getAttribute("aria-hidden") === "true" && visible(elNode) &&
            text(elNode).length > 40) {
            lHiddenFromAt.push({characters: text(elNode).length,
                text: text(elNode).slice(0, 80)});
        }
    }
    for (const elDialog of Array.from(document.querySelectorAll("[role=dialog],[role=alertdialog],dialog"))) {
        if (visible(elDialog)) {
            lDialogs.push({label: label(elDialog) || text(elDialog).slice(0, 80),
                modal: elDialog.getAttribute("aria-modal") === "true" || elDialog.hasAttribute("open")});
        }
    }

    const lLive = Array.from(document.querySelectorAll("[aria-live]"))
        .filter(el => (el.getAttribute("aria-live") || "").toLowerCase() !== "off")
        .map(el => (el.getAttribute("aria-live") || "").toLowerCase());

    const lFrames = Array.from(document.querySelectorAll("iframe")).map(el => ({
        title: (el.getAttribute("title") || "").slice(0, 80),
        src: (el.getAttribute("src") || "").slice(0, 120),
        visible: visible(el)
    }));

    // A consent banner is worth flagging because it usually blocks everything.
    let sConsent = "";
    for (const elNode of Array.from(document.querySelectorAll("div,section,aside,dialog")).slice(0, 3000)) {
        const sText = text(elNode).toLowerCase();
        if (sText.length > 40 && sText.length < 1200 && visible(elNode) &&
            (sText.includes("cookie") || sText.includes("consent")) &&
            (sText.includes("accept") || sText.includes("agree") || sText.includes("reject"))) {
            sConsent = text(elNode).slice(0, 140);
            break;
        }
    }

    const elMain = document.querySelector("main, [role=main]");
    const sBodyText = text(document.body);

    return {
        autoplay: iAutoplay,
        consent: sConsent,
        decorativeImages: iDecorative,
        dialogs: lDialogs.slice(0, 5),
        fields: document.querySelectorAll("input:not([type=hidden]),select,textarea,[contenteditable=true]").length,
        forms: document.querySelectorAll("form").length,
        frames: lFrames.slice(0, 10),
        headings: lHeadings.slice(0, 200),
        hiddenFromAt: lHiddenFromAt.slice(0, 5),
        images: lImages.length,
        importantLinks: lImportant.slice(0, 40),
        lang: document.documentElement.getAttribute("lang") || "",
        liveRegions: lLive,
        mainCharacters: elMain ? text(elMain).length : 0,
        media: lMedia.length,
        pinned: lPinned.slice(0, 6),
        regions: lRegions.slice(0, 40),
        skipLinks: lSkipLinks.slice(0, 5),
        tables: lTables.slice(0, 20),
        title: document.title || "",
        totalCharacters: sBodyText.length,
        totalLinks: lAllLinks.length,
        uniqueLinks: setHrefs.size,
        unnamedImages: iUnnamed,
        url: location.href
    };
})()"""


def escape(vValue):
    return (
        str(vValue if vValue is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def plural(iCount, sSingular, sPlural=None):
    return sSingular if iCount == 1 else (sPlural or sSingular + "s")


def verb(iCount, sSingular, sPlural):
    """Agree the verb with the count. A screen reader user hears every slip."""
    return sSingular if iCount == 1 else sPlural


def times(iCount):
    if iCount == 1:
        return "once"
    if iCount == 2:
        return "twice"
    return f"{iCount} times"


def describeRegion(dRegion):
    sName = dRegion.get("label") or ""
    sRole = dRegion.get("role") or "region"
    lParts = [f"{sRole} landmark"]
    if sName:
        lParts.append(f'named "{sName}"')
    lDetail = []
    if dRegion.get("headings"):
        lDetail.append(f"{dRegion['headings']} {plural(dRegion['headings'], 'heading')}")
    if dRegion.get("links"):
        lDetail.append(f"{dRegion['links']} {plural(dRegion['links'], 'link')}")
    pass  # the character count this reported has been dropped
    if lDetail:
        lParts.append("with " + ", ".join(s for s in lDetail if s))
    if dRegion.get("hidden"):
        lParts.append("(not visible)")
    return " ".join(lParts)


def readingMinutes(iCharacters):
    iWords = max(1, iCharacters // 5)
    return max(1, round(iWords / wordsPerMinute))


def article(iNumber):
    """Return a or an, since the number is spoken and 8, 11, and 18 take an."""
    sNumber = str(iNumber)
    if sNumber.startswith("8") or sNumber in ("11", "18") or sNumber.startswith(("11", "18")):
        return "an"
    return "a"


def headingProblems(lHeadings):
    """Return notable faults in the heading outline, or an empty list."""
    lNotes = []
    lLevels = [d["level"] for d in lHeadings]
    iFirstLevel = lLevels[0] if lLevels else 0
    iCountOne = lLevels.count(1)
    if not lLevels:
        lNotes.append("The page has no headings at all, so heading navigation will not help here.")
        return lNotes
    if iCountOne == 0:
        lNotes.append("There is no level one heading, so H will not take you to a page title.")
    elif iCountOne > 1:
        lNotes.append(f"There are {iCountOne} level one headings, which usually means several unrelated sections.")
    if iFirstLevel > 1:
        lNotes.append(f"The first heading is level {iFirstLevel} rather than level one.")
    iSkips = 0
    for iIndex in range(1, len(lLevels)):
        if lLevels[iIndex] - lLevels[iIndex - 1] > 1:
            iSkips += 1
    if iSkips:
        lNotes.append(
            f"The outline skips a level {times(iSkips)}, so some headings sit deeper than they look."
        )
    iHidden = sum(1 for d in lHeadings if d.get("hidden"))
    if iHidden:
        lNotes.append(
            f"{iHidden} {plural(iHidden, 'heading')} {verb(iHidden, 'is', 'are')} in the markup "
            "but not visible on screen."
        )
    return lNotes


def visualNotes(dPage):
    """Only things a reading order hides and that are worth knowing."""
    lNotes = []
    for dDialog in asList(dPage.get("dialogs")):
        sLabel = dDialog.get("label") or "untitled"
        sModal = "modal " if dDialog.get("modal") else ""
        lNotes.append(
            f'A {sModal}dialog is open on top of the page: "{sLabel}". '
            "Deal with it before anything else, since it may be blocking the rest."
        )
    if dPage.get("consent"):
        lNotes.append(
            f'A cookie or consent banner is showing: "{dPage["consent"]}". '
            "These usually sit over the page and take the first tab stops."
        )
    for dPinned in asList(dPage.get("pinned")):
        sWhere = "at the top" if dPinned.get("top", 0) < 100 else "over the page"
        lNotes.append(
            f"A {dPinned.get('role')} is pinned {sWhere} using {dPinned.get('position')} positioning, "
            f"{dPinned.get('height')} pixels tall. It stays put as the page scrolls, so it can cover "
            "content you have just moved to."
        )
    for dHidden in asList(dPage.get("hiddenFromAt")):
        lNotes.append(
            f'{dHidden.get("characters", 0)} characters are visible on screen but hidden from '
            f'screen readers with aria-hidden, beginning "{dHidden.get("text", "")}".'
        )
    if dPage.get("unnamedImages"):
        iCount = dPage["unnamedImages"]
        lNotes.append(
            f"{iCount} visible {plural(iCount, 'image')} {verb(iCount, 'has', 'have')} no "
            f"alternative text at all, so {verb(iCount, 'its', 'their')} content is unavailable."
        )
    if dPage.get("autoplay"):
        lNotes.append(
            f"{asList(dPage.get("autoplay"))} media {plural(asList(dPage.get("autoplay")), 'element')} "
            f"{verb(asList(dPage.get("autoplay")), 'is', 'are')} set to play automatically, which may talk "
            "over speech."
        )
    lLive = asList(dPage.get("liveRegions"))
    if lLive:
        iAssertive = sum(1 for s in lLive if s == "assertive")
        sNote = (
            f"{len(lLive)} live {plural(len(lLive), 'region')} will announce changes "
            "without you asking."
        )
        if iAssertive:
            sNote += (
                f" {iAssertive} of them {verb(iAssertive, 'is', 'are')} assertive and will "
                "interrupt whatever is being read."
            )
        lNotes.append(sNote)
    lFrames = [d for d in (asList(dPage.get("frames"))) if d.get("visible")]
    if lFrames:
        lUnnamed = [d for d in lFrames if not d.get("title")]
        sNote = (
            f"{len(lFrames)} visible {plural(len(lFrames), 'frame')} "
            f"{verb(len(lFrames), 'is', 'are')} embedded in this page."
        )
        if lUnnamed:
            sNote += (
                f" {len(lUnnamed)} of them {verb(len(lUnnamed), 'has', 'have')} no title, "
                "so NVDA can only call them frames."
            )
        lNotes.append(sNote)
    return lNotes


def navigationTips(dPage):
    """Keystrokes chosen for what this page actually contains."""
    lTips = []
    lRegions = asList(dPage.get("regions"))
    lRoles = [d.get("role") for d in lRegions]
    if dPage.get("mainCharacters"):
        lTips.append(
            f"Press J to jump straight to the main content, which holds about "
            f"roughly {article(readingMinutes(dPage['mainCharacters']))} "
            f"{readingMinutes(dPage['mainCharacters'])} minute read."
        )
    elif "main" not in lRoles:
        lTips.append(
            "There is no main landmark, so J will report that. Use H for the first heading instead, "
            "or NVDA+Alt+R to extract just the readable part into a clean document."
        )
    if dPage.get("skipLinks"):
        lTips.append(
            f"The page offers a skip link. Press Tab once from the top of the document to reach it."
        )
    if len(lRegions) >= 3:
        lTips.append(
            f"There are {len(lRegions)} landmarks. Press D and Shift+D to move between them, or "
            "NVDA+F7 for the elements list."
        )
    lHeadings = asList(dPage.get("headings"))
    if len(lHeadings) >= 8:
        lTips.append(
            f"With {len(lHeadings)} headings, H and Shift+H are the fastest way through this page. "
            "Number keys 1 to 6 move by heading level."
        )
    lTables = [d for d in (asList(dPage.get("tables"))) if d.get("headerCells")]
    if lTables:
        iRows = sum(d.get("rows", 0) for d in lTables)
        lTips.append(
            f"{len(lTables)} data {plural(len(lTables), 'table')} with about {iRows} rows in total. "
            "Press T to move between tables, then Control+Alt with the arrow keys to move between "
            "cells, which announces row and column headers as you go."
        )
    lLayoutTables = [d for d in (asList(dPage.get("tables"))) if not d.get("headerCells")]
    if lLayoutTables:
        lTips.append(
            f"{len(lLayoutTables)} {plural(len(lLayoutTables), 'table')} "
            f"{verb(len(lLayoutTables), 'has', 'have')} no header cells, so "
            f"{verb(len(lLayoutTables), 'it is', 'they are')} probably being used for layout "
            "rather than data."
        )
    if dPage.get("fields"):
        lTips.append(
            f"{dPage['fields']} form {plural(dPage['fields'], 'field')} across "
            f"{dPage.get('forms', 0)} {plural(dPage.get('forms', 0), 'form')}. Press F to move between "
            "fields, and Enter or Space to switch to focus mode when you reach one."
        )
    iLinks = dPage.get("totalLinks", 0)
    if iLinks > 150:
        lTips.append(
            f"There are {iLinks} links, which is a lot to arrow through. Use NVDA+F7 to list them, "
            "or press N to skip past a block of links."
        )
    return lTips


def buildSummaryHtml(dPage):
    """Build the document shown in NVDA's browseable message window."""
    lParts = []
    iCharacters = dPage.get("totalCharacters", 0)
    lRegions = asList(dPage.get("regions"))
    lHeadings = asList(dPage.get("headings"))

    lParts.append(f"<h1>Page explorer: {escape(dPage.get('title') or dPage.get('url'))}</h1>")
    lParts.append(f"<p>Address: {escape(dPage.get('url'))}</p>")

    lOverview = [
        f"roughly {article(readingMinutes(iCharacters))} {readingMinutes(iCharacters)} minute read",
        f"{len(lRegions)} {plural(len(lRegions), 'landmark')}",
        f"{len(lHeadings)} {plural(len(lHeadings), 'heading')}",
        f"{dPage.get('totalLinks', 0)} links, {dPage.get('uniqueLinks', 0)} of them distinct",
    ]
    if dPage.get("fields"):
        lOverview.append(f"{dPage['fields']} form {plural(dPage['fields'], 'field')}")
    if dPage.get("tables"):
        lOverview.append(f"{len(asList(dPage.get("tables")))} {plural(len(asList(dPage.get("tables"))), 'table')}")
    if dPage.get("images"):
        lOverview.append(f"{dPage['images']} {plural(dPage['images'], 'image')}")
    lParts.append("<h2>Overview</h2>")
    lParts.append("<p>This page has " + "; ".join(escape(s) for s in lOverview) + ".</p>")
    if not dPage.get("lang"):
        lParts.append(
            "<p>The page does not declare a language, so speech may use the wrong voice.</p>"
        )

    lParts.append("<h2>Regions</h2>")
    if lRegions:
        lParts.append("<ul>")
        for dRegion in lRegions[:maximumRegionsShown]:
            lParts.append(f"<li>{escape(describeRegion(dRegion))}</li>")
        lParts.append("</ul>")
        if len(lRegions) > maximumRegionsShown:
            lParts.append(f"<p>and {len(lRegions) - maximumRegionsShown} more.</p>")
    else:
        lParts.append(
            "<p>This page defines no landmarks, so there is no structural map to move around by. "
            "Headings are the only guide here.</p>"
        )

    lParts.append("<h2>Heading outline</h2>")
    if lHeadings:
        lParts.append("<ul>")
        for dHeading in lHeadings[:maximumHeadingsShown]:
            sIndent = "&nbsp;" * ((dHeading["level"] - 1) * 2)
            lParts.append(
                f"<li>{sIndent}Level {dHeading['level']}: {escape(dHeading['text'])}</li>"
            )
        lParts.append("</ul>")
        if len(lHeadings) > maximumHeadingsShown:
            lParts.append(f"<p>and {len(lHeadings) - maximumHeadingsShown} more.</p>")
    lNotes = headingProblems(lHeadings)
    if lNotes:
        lParts.append("<ul>")
        lParts.extend(f"<li>{escape(s)}</li>" for s in lNotes)
        lParts.append("</ul>")

    lImportant = asList(dPage.get("importantLinks"))
    lParts.append("<h2>Links worth knowing about</h2>")
    if lImportant:
        dByKind = {}
        for dLink in lImportant:
            dByKind.setdefault(dLink["kind"], []).append(dLink)
        lParts.append("<ul>")
        for sKind in sorted(dByKind):
            dLink = dByKind[sKind][0]
            lParts.append(
                f'<li>{escape(sKind)}: <a href="{escape(dLink["url"])}">{escape(dLink["text"])}</a></li>'
            )
        lParts.append("</ul>")
    else:
        lParts.append("<p>Nothing stood out. Press K to move through links, or NVDA+F7 to list them.</p>")

    lVisual = visualNotes(dPage)
    lParts.append("<h2>Visual aspects to be aware of</h2>")
    if lVisual:
        lParts.append("<ul>")
        lParts.extend(f"<li>{escape(s)}</li>" for s in lVisual)
        lParts.append("</ul>")
    else:
        lParts.append("<p>Nothing notable. The reading order should match what is on screen.</p>")

    lTips = navigationTips(dPage)
    lParts.append("<h2>How to get around this page</h2>")
    if lTips:
        lParts.append("<ol>")
        lParts.extend(f"<li>{escape(s)}</li>" for s in lTips)
        lParts.append("</ol>")
    else:
        lParts.append("<p>This is a simple page. Arrow keys will do.</p>")

    return "\n".join(lParts)


def asList(vValue):
    """Return a list whatever the browser sent.

    The analysis script returns some fields as lists and others as counts or
    strings, and both ends have been edited more than once. A summary that
    fails entirely because one field arrived as a number rather than a list is
    a poor trade, so every collection is read through this.
    """
    if isinstance(vValue, list):
        return vValue
    if vValue in (None, "", 0):
        return []
    return [vValue]


def asCount(vValue):
    """Return a number whatever the browser sent."""
    if isinstance(vValue, list):
        return len(vValue)
    try:
        return int(vValue or 0)
    except (TypeError, ValueError):
        return 0


def explorePage(cdpSession):
    """Analyse the focused page and return the summary to show."""
    logSection("Command: explore the page")
    dTarget, sSessionId = cdpSession.findActivePageSession()
    homerLog.info(f"Exploring {abbreviate(dTarget.get('title', ''), 120)}")
    dPage = cdpSession.evaluate(sSessionId, analysisScript, analysisTimeoutSeconds)
    if not dPage:
        raise RuntimeError("The page could not be analysed")
    homerLog.info(
        f"Page explorer found {len(dPage.get('regions') or [])} landmarks, "
        f"{len(dPage.get('headings') or [])} headings, {dPage.get('totalLinks')} links, "
        f"{dPage.get('fields')} fields, {len(dPage.get('tables') or [])} tables, "
        f"{len(dPage.get('pinned') or [])} pinned elements, "
        f"{len(dPage.get('dialogs') or [])} open dialogs"
    )
    return {
        "html": buildSummaryHtml(dPage),
        "regions": len(asList(dPage.get("regions"))),
        "title": dPage.get("title") or dPage.get("url", ""),
        "visualCount": len(visualNotes(dPage)),
    }
