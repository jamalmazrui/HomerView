"""Turn an axe-core result and a set of contact channels into a readable report.

The shape comes from AccReporter: a document rather than a dialog, one h1, an h2
per section, an h3 per violation, a working skip link, affected elements inside
expandable sections, violations ordered by severity, and a pre-written email to
the publisher.

The substance comes from urlCheck, whose report is considerably richer than a
list of rule names. Each of its choices fixes a way that raw axe output misleads
a reader.

axe reports its checks in three groups and they do not mean the same thing. A
check under "any" is one of several alternative fixes, and only one is needed.
Checks under "all" and "none" are every one required. Running them together into
one list, which is the obvious thing to do, tells a publisher to make five
changes when one would do.

A bare rule name such as "region" tells a reader nothing about why it matters.
Mapping the rule to its WCAG criterion, with the criterion's name, conformance
level, and a link to the official explanation, turns it into something a
publisher can act on and a user can cite.

Best practice rules carry no WCAG tags at all. Presenting them as compliance
failures would be an overclaim, so they are labelled and their related criteria
are marked advisory.

The element's own HTML and its selector are what let someone find the thing in
their code, so both are shown for every instance.

One urlCheck feature is deliberately left out. Its report puts a coloured emoji
beside each severity. A screen reader announces that as "red circle" immediately
before the word "critical", so the reader hears the severity twice and one of
the times is noise.
"""

import html
from datetime import datetime
from urllib.parse import quote

from . import wcag
from .contacts import isExcludedHost
from .logger import homerLog

dImpactOrder = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
lImpactNames = ["critical", "serious", "moderate", "minor"]
maximumEmailViolations = 5
maximumPatternRows = 10
maximumSnippetCharacters = 400
reportHtmlFileName = "Report.htm"
reportTextFileName = "Report.txt"

dImpactMeaning = {
    "critical": "Blocks some people completely. Fix first.",
    "serious": "Very hard to work around. High priority.",
    "moderate": "Causes real difficulty. Fix when you can.",
    "minor": "A small problem. There is usually a workaround.",
}

dOutcomeMeaning = {
    "violations": "Confirmed problems that need fixing.",
    "incomplete": "Possible problems that a person has to judge.",
    "passes": "Rules this page passed automatically.",
    "inapplicable": "Rules that had nothing to test on this page.",
}

lGlossary = [
    ("axe-core", "The testing engine, made by Deque Systems, that ran the rules against this page."),
    ("impact", "How badly a problem affects people, from critical down to minor."),
    ("inapplicable", "A rule that had nothing to test on this page."),
    ("needs review", "A result the engine could not decide, so a person has to look."),
    ("instance", "One element on the page that failed a rule. A single rule can fail many times."),
    ("rule", "One automated test, such as image-alt or color-contrast."),
    ("selector", "The address of an element within the page, used to find it in the code."),
    ("violation", "A confirmed problem found automatically."),
    ("best practice", "Advice that improves accessibility but is not itself a WCAG requirement."),
    ("WCAG", "Web Content Accessibility Guidelines, the standard most accessibility law refers to."),
    ("Level A and Level AA", "Conformance levels. Level A is the minimum; Level AA is what most laws require."),
]

lResources = [
    ("https://www.w3.org/WAI/WCAG22/Understanding/", "Understanding WCAG 2.2, the official explanation of every criterion"),
    ("https://dequeuniversity.com/rules/axe/4.11/", "Deque, the full list of axe-core rules with guidance"),
    ("https://accessibilityinsights.io/docs/web/overview/", "Accessibility Insights, a free tool for manual testing"),
    ("https://www.w3.org/WAI/planning/statements/", "W3C guidance on writing an accessibility statement"),
]

lNextSteps = [
    "Start with the critical and serious problems. They affect the most people, the most severely.",
    "Use the selector and the HTML shown for each instance to find the exact element in the code.",
    "Where a fix is listed under Fix any one of these, only one of the listed changes is needed.",
    "Send the report to the publisher using one of the channels below, and keep a copy.",
    "Ask for a reply. A good accessibility statement says how long a response should take.",
    "Remember that an automated scan finds roughly a third of accessibility barriers. "
    "A page with no violations can still be hard to use.",
]

reportStyle = """
body { font-family: Segoe UI, Arial, sans-serif; line-height: 1.5; margin: 0 auto; max-width: 60em; padding: 1em; }
.skipLink { left: -999px; position: absolute; }
.skipLink:focus { left: 0; position: static; }
.impact { border: 1px solid; border-radius: 0.2em; font-weight: bold; padding: 0 0.4em; }
.impactCritical { border-color: #c00000; color: #c00000; }
.impactSerious { border-color: #8b0000; color: #8b0000; }
.impactModerate { border-color: #c05000; color: #c05000; }
.impactMinor { border-color: #6b6b00; color: #6b6b00; }
.bestPractice { border: 1px solid #444; border-radius: 0.2em; padding: 0 0.4em; }
.violation { border-left: 0.3em solid #767676; margin-bottom: 1.5em; padding-left: 1em; }
.instance { border-left: 0.2em solid #bbb; margin: 0.8em 0; padding-left: 0.8em; }
.note { background: #f4f4f4; border-left: 0.3em solid #767676; padding: 0.5em 1em; }
.advisory { font-style: italic; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #999; padding: 0.3em 0.5em; text-align: left; }
pre { background: #f4f4f4; overflow-x: auto; padding: 1em; white-space: pre-wrap; }
code { background: #f4f4f4; padding: 0 0.2em; }
"""


def escape(vValue):
    return html.escape(str(vValue if vValue is not None else ""), quote=True)


def sortViolations(lViolations):
    """Most severe first, and within a severity the rule failing most often."""
    return sorted(
        lViolations,
        key=lambda d: (dImpactOrder.get(d.get("impact") or "", 99), -len(d.get("nodes") or [])),
    )


def countInstances(lRules):
    return sum(len(d.get("nodes") or []) for d in lRules)


def flattenTarget(vTarget):
    """Turn axe's target into one readable selector path.

    A target is normally a list of strings, but axe nests a list when the element
    sits inside a frame or a shadow root, outermost first.
    """
    lParts = []
    for vEntry in vTarget if isinstance(vTarget, list) else [vTarget]:
        if isinstance(vEntry, list):
            lParts.append(" >> ".join(str(v) for v in vEntry))
        else:
            lParts.append(str(vEntry))
    return " | ".join(p for p in lParts if p)


def describeChecks(dNode):
    """Return the fix groups with their correct meaning.

    Anything under any is a choice of one. Anything under all or none is
    required. Merging them, which is the obvious shortcut, asks a publisher for
    several changes when one would do.
    """
    lGroups = []
    lAny = dNode.get("any") or []
    lAll = list(dNode.get("all") or []) + list(dNode.get("none") or [])
    if lAny:
        lGroups.append(("Fix any one of these", lAny))
    if lAll:
        lGroups.append(("Fix all of these", lAll))
    return lGroups


def describeCheckData(dCheck):
    """Render a check's extra data, such as the contrast ratio it measured."""
    vData = dCheck.get("data")
    if isinstance(vData, dict):
        lParts = [f"{k}: {v}" for k, v in vData.items() if v is not None and str(v).strip()]
        return ", ".join(lParts)
    if vData is not None and str(vData).strip():
        return str(vData)
    return ""


def snippet(sHtml):
    sHtml = " ".join(str(sHtml or "").split())
    if len(sHtml) > maximumSnippetCharacters:
        return sHtml[:maximumSnippetCharacters] + " ..."
    return sHtml


def wcagLineParts(dRule):
    """Return the criteria for a rule as (number, readable phrase) pairs."""
    lRefs, bAdvisory = wcag.refsForRule(dRule)
    lParts = []
    for sRef in lRefs:
        sName, sLevel, sPrinciple = wcag.describeRef(sRef)
        if sName:
            lParts.append((sRef, f"{sRef} {sName} (Level {sLevel}, {sPrinciple})"))
        else:
            lParts.append((sRef, sRef))
    return lParts, bAdvisory


def patternRows(lViolations):
    """Which rules and which criteria account for the most failing elements."""
    dRules = {}
    dRefs = {}
    for dViolation in lViolations:
        iNodes = len(dViolation.get("nodes") or [])
        sId = dViolation.get("id") or ""
        dRules[sId] = dRules.get(sId, 0) + iNodes
        lRefs, bAdvisory = wcag.refsForRule(dViolation)
        for sRef in lRefs:
            dRefs[sRef] = dRefs.get(sRef, 0) + iNodes
    lRules = sorted(dRules.items(), key=lambda t: (-t[1], t[0]))[:maximumPatternRows]
    lRefs = sorted(dRefs.items(), key=lambda t: (-t[1], t[0]))[:maximumPatternRows]
    return lRules, lRefs


def narrativeLines(lViolations, sPageTitle):
    """A plain language account, at around a ninth grade reading level."""
    iInstances = countInstances(lViolations)
    if not iInstances:
        return [
            f"No accessibility violations were found automatically on {sPageTitle}.",
            "That is a good sign, but an automated scan finds only some kinds of problem. "
            "Roughly a third of accessibility barriers can be caught this way. The rest need "
            "a person using a screen reader, or a keyboard alone, to notice them.",
        ]
    dByImpact = {}
    for dViolation in lViolations:
        sImpact = dViolation.get("impact") or ""
        dByImpact[sImpact] = dByImpact.get(sImpact, 0) + len(dViolation.get("nodes") or [])
    lLines = []
    if iInstances == 1:
        lLines.append(f"One accessibility problem was found on {sPageTitle}.")
    else:
        lLines.append(
            f"{iInstances} accessibility problems were found on {sPageTitle}, "
            f"across {len(lViolations)} rule{'' if len(lViolations) == 1 else 's'}."
        )
    lSeverity = [f"{dByImpact[s]} {s}" for s in lImpactNames if dByImpact.get(s)]
    if lSeverity:
        lLines.append(
            "By severity: " + ", ".join(lSeverity) + ". "
            "Critical and serious problems block or badly hinder people who rely on a screen "
            "reader, a keyboard alone, or voice control. Those come first."
        )
    dLevels = {}
    for dViolation in lViolations:
        lRefs, bAdvisory = wcag.refsForRule(dViolation)
        if bAdvisory:
            continue
        for sRef in lRefs:
            sName, sLevel, sPrinciple = wcag.describeRef(sRef)
            if sLevel:
                dLevels[sLevel] = dLevels.get(sLevel, 0) + 1
    if dLevels.get("A"):
        lLines.append(
            "Some of these fail WCAG Level A criteria, which are the minimum for basic "
            "accessibility."
        )
    elif dLevels.get("AA"):
        lLines.append(
            "Some of these fail WCAG Level AA criteria, which most accessibility laws and "
            "policies require."
        )
    return lLines


def buildEmailBody(sPageTitle, sPageUrl, lViolations, sReportPath):
    iInstances = countInstances(lViolations)
    lLines = [
        "Dear Web Accessibility Team,",
        "",
        "I am writing to report accessibility problems I found on this page:",
        f"  {sPageUrl}",
        "",
        f"An automated scan with axe-core found {len(lViolations)} rule failure(s) "
        f"affecting {iInstances} element(s).",
        "",
    ]
    for dViolation in lViolations[:maximumEmailViolations]:
        sImpact = (dViolation.get("impact") or "unknown").upper()
        lLines.append(f"- [{sImpact}] {dViolation.get('help', '')}")
        lParts, bAdvisory = wcagLineParts(dViolation)
        if lParts:
            lLines.append(
                ("  Related to WCAG " if bAdvisory else "  WCAG ")
                + "; ".join(sText for sRef, sText in lParts)
            )
        if wcag.isBestPractice(dViolation):
            lLines.append("  This one is a best practice rather than a WCAG requirement.")
        lLines.append(f"  Affects {len(dViolation.get('nodes') or [])} element(s).")
        lLines.append(f"  Guidance: {dViolation.get('helpUrl', '')}")
        lLines.append("")
    if len(lViolations) > maximumEmailViolations:
        lLines.append(
            f"... and {len(lViolations) - maximumEmailViolations} further rule failure(s). "
            "The full report has the detail, including the exact elements affected."
        )
        lLines.append("")
    lLines.append(f"A full report is saved at {sReportPath} and can be attached to this message.")
    lLines.append(
        "Please note that an automated scan finds only some kinds of barrier, so this is a "
        "starting point rather than a complete picture."
    )
    lLines.append("")
    lLines.append("Thank you for your attention to this.")
    return "\n".join(lLines)


def buildMailtoUrl(sAddress, sPageTitle, sBody):
    sTarget = sAddress[7:] if sAddress.lower().startswith("mailto:") else sAddress
    sTarget = sTarget.split("?", 1)[0]
    sSubject = quote(f"Accessibility problems on {sPageTitle}")
    return f"mailto:{sTarget}?subject={sSubject}&body={quote(sBody)}"


def renderLinkList(lLinks, sEmptyMessage):
    if not lLinks:
        return f"<p>{escape(sEmptyMessage)}</p>"
    return (
        "<ul>\n"
        + "\n".join(f'<li><a href="{escape(s)}">{escape(s)}</a></li>' for s in lLinks)
        + "\n</ul>"
    )


def renderChecks(dNode):
    lGroups = describeChecks(dNode)
    if not lGroups:
        sSummary = str(dNode.get("failureSummary") or "").strip()
        return f"<p>{escape(sSummary)}</p>" if sSummary else ""
    lParts = ["<p><strong>How to fix</strong></p>"]
    for sTitle, lChecks in lGroups:
        lParts.append(f"<p>{escape(sTitle)}:</p>")
        lParts.append("<ul>")
        for dCheck in lChecks:
            sMessage = escape(dCheck.get("message", ""))
            sData = describeCheckData(dCheck)
            if sData:
                sMessage += f" ({escape(sData)})"
            lRelatedItems = [
                f"<li><code>{escape(flattenTarget(d.get('target') or []))}</code></li>"
                for d in (dCheck.get("relatedNodes") or [])
                if d.get("target")
            ]
            if lRelatedItems:
                sMessage += (
                    "<ul><li>Related elements:<ul>" + "\n".join(lRelatedItems) + "</ul></li></ul>"
                )
            lParts.append(f"<li>{sMessage}</li>")
        lParts.append("</ul>")
    return "\n".join(lParts)


def renderInstance(dNode, iIndex, iTotal, sRuleImpact):
    sSelector = flattenTarget(dNode.get("target") or [])
    sSnippet = snippet(dNode.get("html"))
    sNodeImpact = dNode.get("impact") or ""
    lParts = ['<div class="instance">', f"<p><strong>Instance {iIndex} of {iTotal}</strong></p>"]
    if sSelector:
        lParts.append(f"<p>Selector: <code>{escape(sSelector)}</code></p>")
    if sSnippet:
        lParts.append(f"<p>HTML:</p>\n<pre><code>{escape(sSnippet)}</code></pre>")
    lParts.append(renderChecks(dNode))
    if sNodeImpact and sNodeImpact != sRuleImpact:
        lParts.append(f"<p>Impact for this element: {escape(sNodeImpact)}</p>")
    lParts.append("</div>")
    return "\n".join(p for p in lParts if p)


def renderViolation(dViolation, iIndex):
    sImpact = dViolation.get("impact") or "unknown"
    sRuleId = dViolation.get("id") or ""
    lNodes = dViolation.get("nodes") or []
    lWcagParts, bAdvisory = wcagLineParts(dViolation)
    sBadge = (
        ' <span class="bestPractice">best practice</span>'
        if wcag.isBestPractice(dViolation)
        else ""
    )
    if lWcagParts:
        sIntro = "Related WCAG criteria, advisory only" if bAdvisory else "WCAG criteria this fails"
        sClass = ' class="advisory"' if bAdvisory else ""
        lWcagHtml = [
            f'<li><a href="{escape(wcag.understandingUrl(sRef))}">{escape(sText)}</a></li>'
            for sRef, sText in lWcagParts
        ]
        sWcag = f"<p{sClass}>{escape(sIntro)}:</p>\n<ul>\n" + "\n".join(lWcagHtml) + "\n</ul>"
    else:
        sWcag = "<p>No WCAG criterion is mapped to this rule.</p>"
    sPlural = "" if len(lNodes) == 1 else "s"
    lInstances = [renderInstance(d, i, len(lNodes), sImpact) for i, d in enumerate(lNodes, 1)]
    return f"""<article class="violation">
<h3 id="rule{iIndex}"><span class="impact impact{sImpact.capitalize()}">{escape(sImpact)}</span>{sBadge} {escape(dViolation.get('help', ''))}</h3>
<p>{escape(dViolation.get('description', ''))}</p>
<p>Rule <code>{escape(sRuleId)}</code>, {len(lNodes)} affected element{sPlural}.
<a href="{escape(dViolation.get('helpUrl', ''))}">How to fix this, from Deque</a>.</p>
{sWcag}
<details>
<summary>Affected elements ({len(lNodes)})</summary>
{chr(10).join(lInstances)}
</details>
<p><a href="#contents">Back to contents</a></p>
</article>"""


def renderSocialNote(sPageUrl):
    """Explain the omission, but only where it is not absurd.

    The note belongs with the social list rather than at the end of the whole
    section, where it read as though it applied to the contact pages above it.
    And on the excluded site itself the note makes no sense at all, so it is
    left out there.
    """
    if isExcludedHost(sPageUrl):
        return ""
    return (
        '<p class="note">This list leaves out X, formerly Twitter, on purpose. '
        "Accessibility reports sent there have a poor record of reaching anyone who "
        "can act on them, so sending you there would waste your time.</p>"
    )


def renderContacts(dContacts, sPageTitle, sPageUrl, lViolations, sReportPath):
    sBody = buildEmailBody(sPageTitle, sPageUrl, lViolations, sReportPath)
    lMailtoItems = []
    for sMailto in dContacts.get("mailto") or []:
        sUrl = buildMailtoUrl(sMailto, sPageTitle, sBody)
        sShown = sMailto[7:] if sMailto.lower().startswith("mailto:") else sMailto
        lMailtoItems.append(f'<li><a href="{escape(sUrl)}">Write to {escape(sShown)}</a></li>')
    sMailtoHtml = (
        "<ul>\n" + "\n".join(lMailtoItems) + "\n</ul>"
        if lMailtoItems
        else "<p>No email address was found on this site.</p>"
    )
    sStatement = dContacts.get("statement") or ""
    sStatementHtml = (
        f'<p><a href="{escape(sStatement)}">{escape(sStatement)}</a></p>'
        if sStatement
        else "<p>No accessibility statement was found.</p>"
    )
    return f"""<section aria-labelledby="headingContact">
<h2 id="headingContact">Reporting this to the publisher</h2>
<h3>Email</h3>
<p>Each link below opens a message already written, naming the page and the worst problems found. Review it, add anything you want to say in your own words, and send it.</p>
{sMailtoHtml}
<h3>Accessibility statement</h3>
{sStatementHtml}
<h3>Accessibility pages</h3>
{renderLinkList(dContacts.get("accessibility"), "No accessibility page was found.")}
<h3>Contact and support pages</h3>
{renderLinkList(dContacts.get("contact"), "No contact page was found.")}
<h3>Social channels</h3>
{renderLinkList(dContacts.get("social"), "No social channel was found.")}
{renderSocialNote(sPageUrl)}
</section>"""


def buildContents(lViolations, lIncomplete):
    lContents = [
        '<li><a href="#headingSummary">Summary and next steps</a></li>',
        '<li><a href="#headingDetails">Scan details</a></li>',
        '<li><a href="#headingPatterns">Where to start</a></li>',
        f'<li><a href="#headingViolations">Violations ({len(lViolations)})</a>',
    ]
    if lViolations:
        lContents.append("<ul>")
        for iIndex, dViolation in enumerate(lViolations, 1):
            lContents.append(
                f'<li><a href="#rule{iIndex}">{escape(dViolation.get("impact") or "")}: '
                f'{escape(dViolation.get("help", ""))}</a></li>'
            )
        lContents.append("</ul>")
    lContents.append("</li>")
    lContents.extend([
        f'<li><a href="#headingIncomplete">Needing human review ({len(lIncomplete)})</a></li>',
        '<li><a href="#headingContact">Reporting this to the publisher</a></li>',
        '<li><a href="#headingFiles">Saved files</a></li>',
        '<li><a href="#headingGlossary">Glossary</a></li>',
        '<li><a href="#headingResources">Where to learn more</a></li>',
    ])
    return "\n".join(lContents)


def buildReportHtml(dAxeResult, dContacts, sPageTitle, sPageUrl, sReportPath, sPlainText, sTextPath):
    lViolations = sortViolations(dAxeResult.get("violations") or [])
    lIncomplete = dAxeResult.get("incomplete") or []
    lPasses = dAxeResult.get("passes") or []
    lInapplicable = dAxeResult.get("inapplicable") or []
    dEngine = dAxeResult.get("testEngine") or {}
    dEnvironment = dAxeResult.get("testEnvironment") or {}
    lRulePatterns, lRefPatterns = patternRows(lViolations)

    lOutcomeRows = [
        f"<tr><td>{escape(sName)}</td><td>{len(lBucket)}</td>"
        f"<td>{countInstances(lBucket)}</td><td>{escape(dOutcomeMeaning[sName])}</td></tr>"
        for sName, lBucket in (
            ("violations", lViolations),
            ("incomplete", lIncomplete),
            ("passes", lPasses),
            ("inapplicable", lInapplicable),
        )
    ]

    dByImpact = {}
    for dViolation in lViolations:
        sImpact = dViolation.get("impact") or ""
        dByImpact[sImpact] = dByImpact.get(sImpact, 0) + len(dViolation.get("nodes") or [])
    lImpactRows = [
        f"<tr><td>{escape(s)}</td><td>{dByImpact.get(s, 0)}</td>"
        f"<td>{escape(dImpactMeaning[s])}</td></tr>"
        for s in lImpactNames
    ]

    lRuleRows = [f"<tr><td><code>{escape(s)}</code></td><td>{i}</td></tr>" for s, i in lRulePatterns]
    lRefRows = []
    for sRef, iCount in lRefPatterns:
        sName, sLevel, sPrinciple = wcag.describeRef(sRef)
        lRefRows.append(
            f'<tr><td><a href="{escape(wcag.understandingUrl(sRef))}">{escape(sRef)}</a></td>'
            f"<td>{escape(sName)}</td><td>{escape(sLevel)}</td><td>{escape(sPrinciple)}</td>"
            f"<td>{iCount}</td></tr>"
        )

    sRuleTable = (
        "<table>\n<thead><tr><th>Rule</th><th>Elements</th></tr></thead>\n<tbody>\n"
        + "\n".join(lRuleRows)
        + "\n</tbody>\n</table>"
        if lRuleRows
        else "<p>No violations were found.</p>"
    )
    sRefTable = (
        "<table>\n<thead><tr><th>Criterion</th><th>Name</th><th>Level</th>"
        "<th>Principle</th><th>Elements</th></tr></thead>\n<tbody>\n"
        + "\n".join(lRefRows)
        + "\n</tbody>\n</table>"
        if lRefRows
        else "<p>No violations mapped to a WCAG criterion.</p>"
    )

    sIncompleteHtml = (
        "<ul>\n"
        + "\n".join(
            f"<li><code>{escape(d.get('id', ''))}</code>: {escape(d.get('help', ''))} "
            f"({len(d.get('nodes') or [])} element(s))</li>"
            for d in lIncomplete
        )
        + "\n</ul>"
        if lIncomplete
        else "<p>Nothing needs human review.</p>"
    )
    if any((d.get("id") or "") == "frame-tested" for d in lIncomplete):
        sIncompleteHtml += (
            '<p class="note">This page contains frames. HomerView tests the top document '
            "only, so anything inside a frame was not examined. Open the framed content in "
            "its own tab and test that separately if it matters.</p>"
        )

    sViolationsHtml = (
        "\n".join(renderViolation(d, i) for i, d in enumerate(lViolations, 1))
        if lViolations
        else "<p>No violations were found.</p>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HomerView accessibility report: {escape(sPageTitle)}</title>
<style>{reportStyle}</style>
</head>
<body>
<a class="skipLink" href="#mainContent">Skip to main content</a>
<header>
<h1>HomerView accessibility report</h1>
<p>Page: {escape(sPageTitle)}</p>
<p>Address: <a href="{escape(sPageUrl)}">{escape(sPageUrl)}</a></p>
</header>
<nav aria-labelledby="contents">
<h2 id="contents">Contents</h2>
<ul>
{buildContents(lViolations, lIncomplete)}
</ul>
</nav>
<main id="mainContent">
<section aria-labelledby="headingSummary">
<h2 id="headingSummary">Summary and next steps</h2>
{chr(10).join(f"<p>{escape(s)}</p>" for s in narrativeLines(lViolations, sPageTitle))}
<h3>What to do next</h3>
<ol>
{chr(10).join(f"<li>{escape(s)}</li>" for s in lNextSteps)}
</ol>
</section>
<section aria-labelledby="headingDetails">
<h2 id="headingDetails">Scan details</h2>
<dl>
<dt>Scanned</dt><dd>{escape(dAxeResult.get("timestamp", ""))}</dd>
<dt>Report written</dt><dd>{escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}</dd>
<dt>Engine</dt><dd>axe-core {escape(dEngine.get("version", "unknown"))}</dd>
<dt>Window size</dt><dd>{escape(dEnvironment.get("windowWidth", "unknown"))} by {escape(dEnvironment.get("windowHeight", "unknown"))} pixels</dd>
<dt>Browser</dt><dd>{escape(dEnvironment.get("userAgent", "unknown"))}</dd>
</dl>
<h3>Results by outcome</h3>
<table>
<thead><tr><th>Outcome</th><th>Rules</th><th>Elements</th><th>What it means</th></tr></thead>
<tbody>
{chr(10).join(lOutcomeRows)}
</tbody>
</table>
<p>Window size matters, because some rules depend on layout. A narrow window can change the result.</p>
</section>
<section aria-labelledby="headingPatterns">
<h2 id="headingPatterns">Where to start</h2>
<h3>Failing elements by severity</h3>
<table>
<thead><tr><th>Severity</th><th>Elements</th><th>What it means</th></tr></thead>
<tbody>
{chr(10).join(lImpactRows)}
</tbody>
</table>
<h3>Rules with the most failures</h3>
{sRuleTable}
<h3>WCAG criteria most affected</h3>
{sRefTable}
</section>
<section aria-labelledby="headingViolations">
<h2 id="headingViolations">Violations ({len(lViolations)})</h2>
<p>Most severe first, and within a severity the rule that fails most often.</p>
{sViolationsHtml}
</section>
<section aria-labelledby="headingIncomplete">
<h2 id="headingIncomplete">Needing human review ({len(lIncomplete)})</h2>
<p>axe-core could not decide these automatically. They are not necessarily faults.</p>
{sIncompleteHtml}
</section>
{renderContacts(dContacts, sPageTitle, sPageUrl, lViolations, sReportPath)}
<section aria-labelledby="headingFiles">
<h2 id="headingFiles">Saved files</h2>
<ul>
<li>This report: <code>{escape(sReportPath)}</code></li>
<li>Plain text version: <code>{escape(sTextPath)}</code></li>
</ul>
<h3>Plain text version</h3>
<p>Select the text below and copy it if you would rather paste the report into a form or a message.</p>
<pre>{escape(sPlainText)}</pre>
</section>
<section aria-labelledby="headingGlossary">
<h2 id="headingGlossary">Glossary</h2>
<dl>
{chr(10).join(f"<dt>{escape(sTerm)}</dt><dd>{escape(sMeaning)}</dd>" for sTerm, sMeaning in lGlossary)}
</dl>
</section>
<section aria-labelledby="headingResources">
<h2 id="headingResources">Where to learn more</h2>
<ul>
{chr(10).join(f'<li><a href="{escape(sUrl)}">{escape(sText)}</a></li>' for sUrl, sText in lResources)}
</ul>
</section>
</main>
</body>
</html>
"""


def buildPlainTextReport(dAxeResult, dContacts, sPageTitle, sPageUrl, sReportPath):
    lViolations = sortViolations(dAxeResult.get("violations") or [])
    lIncomplete = dAxeResult.get("incomplete") or []
    dEngine = dAxeResult.get("testEngine") or {}
    lLines = [
        "HomerView accessibility report",
        "==============================",
        f"Page: {sPageTitle}",
        f"Address: {sPageUrl}",
        f"Scanned: {dAxeResult.get('timestamp', '')}",
        f"Engine: axe-core {dEngine.get('version', 'unknown')}",
        "",
        "SUMMARY",
        "-------",
    ]
    lLines.extend(narrativeLines(lViolations, sPageTitle))
    lLines.append("")
    lLines.append("WHAT TO DO NEXT")
    lLines.append("---------------")
    lLines.extend(f"{i}. {s}" for i, s in enumerate(lNextSteps, 1))
    lLines.append("")
    lLines.append("VIOLATIONS")
    lLines.append("----------")
    if not lViolations:
        lLines.append("None found.")
    for iIndex, dViolation in enumerate(lViolations, 1):
        lNodes = dViolation.get("nodes") or []
        lLines.append(
            f"{iIndex}. [{(dViolation.get('impact') or 'unknown').upper()}] {dViolation.get('help', '')}"
        )
        lLines.append(f"   {dViolation.get('description', '')}")
        lLines.append(f"   Rule: {dViolation.get('id', '')}")
        lWcagParts, bAdvisory = wcagLineParts(dViolation)
        if lWcagParts:
            lLines.append(
                ("   Related WCAG, advisory: " if bAdvisory else "   WCAG: ")
                + "; ".join(sText for sRef, sText in lWcagParts)
            )
        if wcag.isBestPractice(dViolation):
            lLines.append("   This is a best practice rather than a WCAG requirement.")
        lLines.append(f"   Guidance: {dViolation.get('helpUrl', '')}")
        lLines.append(f"   Affected elements: {len(lNodes)}")
        for iNode, dNode in enumerate(lNodes, 1):
            lLines.append(f"     Instance {iNode} of {len(lNodes)}")
            sSelector = flattenTarget(dNode.get("target") or [])
            if sSelector:
                lLines.append(f"       Selector: {sSelector}")
            sSnippet = snippet(dNode.get("html"))
            if sSnippet:
                lLines.append(f"       HTML: {sSnippet}")
            for sTitle, lChecks in describeChecks(dNode):
                lLines.append(f"       {sTitle}:")
                for dCheck in lChecks:
                    sData = describeCheckData(dCheck)
                    lLines.append(
                        f"         - {dCheck.get('message', '')}" + (f" ({sData})" if sData else "")
                    )
        lLines.append("")
    lLines.append("NEEDING HUMAN REVIEW")
    lLines.append("--------------------")
    if not lIncomplete:
        lLines.append("None.")
    for dRule in lIncomplete:
        lLines.append(
            f"- {dRule.get('id', '')}: {dRule.get('help', '')} "
            f"({len(dRule.get('nodes') or [])} element(s))"
        )
    if any((d.get("id") or "") == "frame-tested" for d in lIncomplete):
        lLines.append("  Note: this page contains frames. Only the top document was tested.")
    lLines.append("")
    lLines.append("REPORTING THIS TO THE PUBLISHER")
    lLines.append("-------------------------------")
    for sTitle, sBucket, sEmpty in (
        ("Email", "mailto", "No email address was found."),
        ("Accessibility pages", "accessibility", "No accessibility page was found."),
        ("Contact and support pages", "contact", "No contact page was found."),
        ("Social channels", "social", "No social channel was found."),
    ):
        lLines.append(f"{sTitle}:")
        lLinks = dContacts.get(sBucket) or []
        lLines.extend([f"  {s}" for s in lLinks] or [f"  {sEmpty}"])
    lLines.append(f"Accessibility statement: {dContacts.get('statement') or 'not found'}")
    lLines.append("")
    lLines.append("GLOSSARY")
    lLines.append("--------")
    lLines.extend(f"{sTerm}: {sMeaning}" for sTerm, sMeaning in lGlossary)
    lLines.append("")
    lLines.append(f"Full report saved at {sReportPath}")
    return "\n".join(lLines)


def writeReports(dAxeResult, dContacts, sPageTitle, sPageUrl, pathFolder):
    """Write both report files and return where they went."""
    pathHtml = pathFolder / reportHtmlFileName
    pathText = pathFolder / reportTextFileName
    sPlainText = buildPlainTextReport(dAxeResult, dContacts, sPageTitle, sPageUrl, str(pathHtml))
    pathText.write_text(sPlainText, encoding="utf-8")
    sHtml = buildReportHtml(
        dAxeResult, dContacts, sPageTitle, sPageUrl, str(pathHtml), sPlainText, str(pathText)
    )
    pathHtml.write_text(sHtml, encoding="utf-8")
    homerLog.info(f"Wrote {pathHtml}, {pathHtml.stat().st_size} bytes")
    homerLog.info(f"Wrote {pathText}, {pathText.stat().st_size} bytes")
    return pathHtml, pathText
