"""The IBM Equal Access accessibility engine, run the same way axe is.

The concern about Node.js is well founded and does not apply here, because the
IBM project ships two quite different things under similar names.

`accessibility-checker` is the Node package. It drives Puppeteer, writes
baselines, and belongs in a build pipeline. It needs Node, it pulls in a second
browser, and it collects telemetry by default. None of that can go in an NVDA
add-on.

`accessibility-checker-engine` is the rule engine itself, and it is plain
JavaScript meant to be injected into a page. IBM's own documentation gives a
script tag pointing at a content delivery network and a two line API. That is
exactly the shape axe-core has, so it drops into the machinery HomerView
already has for axe, with no Node anywhere.

The engine is Apache 2.0. Its rules are harmonised with the W3C ACT Rules
community group, and its rulesets cover WCAG 2.0, 2.1 and 2.2 at A and AA, plus
IBM's own unified set which folds in EN 301 549 and the US Section 508
standards. That last one is the reason to bother: axe checks WCAG, while the
IBM ruleset checks a superset that several procurement regimes actually ask
about.

IBM's documentation warns that a page's content security policy can block the
script tag, and offers its own rule server as an alternative host. That warning
does not apply to HomerView at all: the source is delivered through
Runtime.evaluate, which runs in the page's context through the debugger rather
than as a script element, so no policy is consulted. The alternative host is
still used as a fallback, but for availability rather than policy.
"""

import json
import re
import urllib.request

from .logger import abbreviate, homerLog, logSection

aceFetchTimeoutSeconds = 45.0
aceResultsFileName = "Ace.json"
aceRunTimeoutSeconds = 240.0
userAgent = "HomerView (+NVDA add-on, IBM Equal Access engine)"

# IBM's unified set folds WCAG together with EN 301 549 and Section 508, which
# is the one worth running by default. The others are here for a report that
# has to name a single standard.
defaultRuleset = "IBM_Accessibility"
lRulesets = ["IBM_Accessibility", "WCAG_2_2", "WCAG_2_1", "WCAG_2_0"]

lAceCdnUrls = [
    "https://unpkg.com/accessibility-checker-engine@latest/ace.js",
    "https://cdn.jsdelivr.net/npm/accessibility-checker-engine@latest/ace.js",
    "https://able.ibm.com/rules/archives/latest/js/ace.js",
]

# The engine reports a level and an outcome as a pair. Turning that into words
# a reader can act on is most of the work of presenting its output.
dLevelMeaning = {
    ("VIOLATION", "FAIL"): ("violation", "A confirmed failure that needs fixing."),
    ("VIOLATION", "POTENTIAL"): ("needs review", "Possibly a failure. A person has to judge."),
    ("RECOMMENDATION", "FAIL"): ("recommendation", "Not a failure, but worth improving."),
    ("RECOMMENDATION", "POTENTIAL"): ("needs review", "Possibly worth improving. A person has to judge."),
    ("INFORMATION", "MANUAL"): ("manual check", "The engine cannot decide this at all."),
    ("VIOLATION", "PASS"): ("pass", "This rule passed."),
    ("RECOMMENDATION", "PASS"): ("pass", "This rule passed."),
}

dCachedScript = {}


class AceError(Exception):
    pass


def fetchText(sUrl):
    request = urllib.request.Request(sUrl, headers={"User-Agent": userAgent})
    with urllib.request.urlopen(request, timeout=aceFetchTimeoutSeconds) as response:
        return response.read().decode("utf-8")


def getAceScript():
    """Fetch the engine once per session, trying each host in turn."""
    if dCachedScript.get("source"):
        return dCachedScript["source"], dCachedScript["url"]
    lFailures = []
    for sUrl in lAceCdnUrls:
        homerLog.info(f"Fetching the IBM engine from {sUrl}")
        try:
            sSource = fetchText(sUrl)
        except Exception as exception:
            homerLog.warning(f"Could not fetch the IBM engine from {sUrl}: {exception}")
            lFailures.append(f"{sUrl}: {exception}")
            continue
        dCachedScript["source"] = sSource
        dCachedScript["url"] = sUrl
        homerLog.info(f"Fetched the IBM engine, {len(sSource)} characters, from {sUrl}")
        return sSource, sUrl
    raise AceError(
        "The IBM Equal Access engine could not be downloaded. Check the internet "
        "connection. Tried: " + "; ".join(lFailures)
    )


def buildRunScript(sRuleset):
    return (
        "(async () => {"
        " const checker = new ace.Checker();"
        f' const report = await checker.check(document, ["{sRuleset}"]);'
        " return JSON.stringify(report); })()"
    )


def normalise(dReport):
    """Group the engine's results into buckets a reader can use."""
    dBuckets = {}
    for dResult in dReport.get("results") or []:
        lValue = dResult.get("value") or ["", ""]
        tKey = (str(lValue[0]), str(lValue[1] if len(lValue) > 1 else ""))
        sBucket, sMeaning = dLevelMeaning.get(tKey, ("other", "Unclassified result."))
        if sBucket == "pass":
            dBuckets.setdefault("pass", []).append(dResult)
            continue
        dBuckets.setdefault(sBucket, []).append(dResult)
    return dBuckets


def describeResult(dResult):
    dPath = dResult.get("path") or {}
    return {
        "help": dResult.get("help", "") or dResult.get("helpUrl", ""),
        "message": " ".join(str(dResult.get("message", "")).split()),
        "path": dPath.get("dom", "") or dPath.get("aria", ""),
        "ruleId": dResult.get("ruleId", ""),
        "snippet": " ".join(str(dResult.get("snippet", "")).split())[:400],
    }


def runAce(cdpSession, pathFolder, sRuleset=defaultRuleset):
    """Inject the IBM engine into the focused page, run it, and save the report."""
    logSection("Command: run the IBM Equal Access engine")
    sSource, sSourceUrl = getAceScript()
    dTarget, sSessionId = cdpSession.findActivePageSession()
    sPageUrl = dTarget.get("url", "")
    sPageTitle = dTarget.get("title", "") or sPageUrl
    homerLog.info(f"Running the IBM engine on {abbreviate(sPageTitle, 120)} with {sRuleset}")

    cdpSession.evaluate(sSessionId, sSource, aceRunTimeoutSeconds)
    if not cdpSession.evaluate(sSessionId, 'typeof ace !== "undefined" && !!ace.Checker'):
        raise AceError("The IBM engine did not load into the page")
    homerLog.info("IBM engine injected; running the rules")

    sReport = cdpSession.evaluate(sSessionId, buildRunScript(sRuleset), aceRunTimeoutSeconds)
    if not sReport:
        raise AceError("The IBM engine returned no report")
    dReport = json.loads(sReport)
    dBuckets = normalise(dReport)
    dCounts = {sName: len(lItems) for sName, lItems in dBuckets.items()}
    homerLog.info(f"IBM engine counts: {dCounts}")
    for dResult in (dBuckets.get("violation") or [])[:40]:
        dShown = describeResult(dResult)
        homerLog.debug(f"  {dShown['ruleId']}: {abbreviate(dShown['message'], 200)}")

    pathResults = pathFolder / aceResultsFileName
    pathResults.write_text(json.dumps(dReport, indent=2), encoding="utf-8")
    homerLog.info(f"Saved the IBM report to {pathResults}, {pathResults.stat().st_size} bytes")

    return {
        "buckets": {k: [describeResult(d) for d in v] for k, v in dBuckets.items() if k != "pass"},
        "counts": dCounts,
        "pageTitle": sPageTitle,
        "pageUrl": sPageUrl,
        "path": str(pathResults),
        "report": dReport,
        "ruleset": sRuleset,
        "sourceUrl": sSourceUrl,
    }


def buildRows(dSummary):
    """One row per finding, in the order a reader would want to triage them."""
    lRows = [["Kind", "Rule", "Message", "Path", "Snippet"]]
    for sBucket in ("violation", "needs review", "recommendation", "manual check"):
        for dItem in dSummary.get("buckets", {}).get(sBucket) or []:
            lRows.append([
                sBucket,
                dItem.get("ruleId", ""),
                dItem.get("message", ""),
                dItem.get("path", ""),
                dItem.get("snippet", ""),
            ])
    return lRows


def buildSheets(dSummary):
    """A summary sheet, then one sheet for each kind that has findings."""
    dCounts = dSummary.get("counts", {})
    lSheets = [(
        "Summary",
        [["Page", dSummary.get("pageTitle", "")],
         ["Address", dSummary.get("pageUrl", "")],
         ["Ruleset", dSummary.get("ruleset", "")],
         ["Engine source", dSummary.get("sourceUrl", "")],
         [],
         ["Kind", "Count"]]
        + [[sName, dCounts.get(sName, 0)]
           for sName in ("violation", "needs review", "recommendation", "manual check")],
    )]
    for sBucket in ("violation", "needs review", "recommendation", "manual check"):
        lItems = dSummary.get("buckets", {}).get(sBucket) or []
        if not lItems:
            continue
        lRows = [["Rule", "Message", "Path", "Snippet"]]
        for dItem in lItems:
            lRows.append([
                dItem.get("ruleId", ""), dItem.get("message", ""),
                dItem.get("path", ""), dItem.get("snippet", ""),
            ])
        lSheets.append((sBucket.title()[:31], lRows))
    return lSheets


def buildReportHtml(dSummary):
    import html

    def escape(vValue):
        return html.escape(str(vValue if vValue is not None else ""), quote=True)

    dCounts = dSummary.get("counts", {})
    lParts = [f"<h1>IBM Equal Access report: {escape(dSummary.get('pageTitle', ''))}</h1>"]
    lParts.append(f"<p>{escape(dSummary.get('pageUrl', ''))}</p>")
    lParts.append(
        f"<p>Ruleset {escape(dSummary.get('ruleset', ''))}, which folds WCAG together with "
        "EN 301 549 and the US Section 508 standards. Engine fetched from "
        f"{escape(dSummary.get('sourceUrl', ''))}.</p>"
    )
    lParts.append("<h2>Results by kind</h2><table>")
    lParts.append("<thead><tr><th>Kind</th><th>Count</th><th>What it means</th></tr></thead><tbody>")
    for sName, sMeaning in (
        ("violation", "A confirmed failure that needs fixing."),
        ("needs review", "Possibly a failure. A person has to judge."),
        ("recommendation", "Not a failure, but worth improving."),
        ("manual check", "The engine cannot decide this at all."),
    ):
        lParts.append(
            f"<tr><td>{escape(sName)}</td><td>{dCounts.get(sName, 0)}</td>"
            f"<td>{escape(sMeaning)}</td></tr>"
        )
    lParts.append("</tbody></table>")
    for sBucket in ("violation", "needs review", "recommendation", "manual check"):
        lItems = dSummary.get("buckets", {}).get(sBucket) or []
        if not lItems:
            continue
        lParts.append(f"<h2>{escape(sBucket.capitalize())} ({len(lItems)})</h2>")
        for dItem in lItems[:80]:
            lParts.append('<article class="violation">')
            lParts.append(f"<h3>{escape(dItem.get('ruleId', ''))}</h3>")
            lParts.append(f"<p>{escape(dItem.get('message', ''))}</p>")
            if dItem.get("path"):
                lParts.append(f"<p>Path: <code>{escape(dItem['path'])}</code></p>")
            if dItem.get("snippet"):
                lParts.append(f"<pre><code>{escape(dItem['snippet'])}</code></pre>")
            lParts.append("</article>")
    lParts.append(
        f"<h2>Saved file</h2><p><code>{escape(dSummary.get('path', ''))}</code>, "
        "in the engine's own format.</p>"
    )
    lParts.append(
        "<h2>How this differs from the axe report</h2>"
        "<p>Two engines disagree usefully. axe checks WCAG. The IBM ruleset checks a "
        "superset that also covers EN 301 549 and Section 508, and it separates a "
        "recommendation from a failure rather than folding both into one list. Running "
        "both and reading where they differ finds more than either alone.</p>"
    )
    return "\n".join(lParts)
