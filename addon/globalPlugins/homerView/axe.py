"""Run axe-core against the current HomerView page and save the results.

The approach follows urlCheck: fetch axe.min.js from a public content delivery
network so that no Node.js installation is needed, try more than one network,
and inject the source text rather than a script url.

Injecting text matters twice over. It survives a page whose content security
policy forbids external scripts, and here it is delivered through
Runtime.evaluate, which runs in the page's own context through the debugger
rather than as a script element, so the policy does not apply at all.

The script is fetched once per NVDA session and reused, since it is roughly
six hundred kilobytes and does not change between pages.
"""

import json
import re
import urllib.request
from datetime import datetime, timezone

from .logger import abbreviate, homerLog, logSection

axeFetchTimeoutSeconds = 30.0
axeResultsFileName = "Axe.json"
axeRunTimeoutSeconds = 180.0
# AccReporter scoped its run to the standards most publishers actually claim,
# skipping AAA rules that would fill an advocacy user's report with findings the
# site never undertook to meet. Set lAxeTags to an empty list to run every rule.
lAxeTags = ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"]
dAxeRunOptions = {"resultTypes": ["violations", "incomplete", "passes", "inapplicable"]}
fallbackAxeVersion = "4.11"
lAxeCdnUrls = [
    "https://cdn.jsdelivr.net/npm/axe-core@4.11.0/axe.min.js",
    "https://unpkg.com/axe-core@4.11.0/axe.min.js",
]
lOutcomeNames = ["violations", "incomplete", "passes", "inapplicable"]
userAgent = "HomerView (+NVDA add-on, axe-core)"

dCachedScript = {}


class AxeError(Exception):
    pass


def fetchText(sUrl):
    request = urllib.request.Request(sUrl, headers={"User-Agent": userAgent})
    with urllib.request.urlopen(request, timeout=axeFetchTimeoutSeconds) as response:
        return response.read().decode("utf-8")


def readAxeVersion(sSource):
    """Pull the version out of the bundle so the report can name it."""
    match = re.search(
        r'(?:axe\.version|version)\s*[=:]\s*["\']([0-9]+\.[0-9]+(?:\.[0-9]+)?)["\']',
        sSource[:8000],
    )
    return match.group(1) if match else fallbackAxeVersion


def getAxeScript():
    """Return the axe-core source, fetching it once per session."""
    if dCachedScript.get("source"):
        homerLog.debug(f"Reusing the axe-core source from {dCachedScript.get('url')}")
        return dCachedScript["source"], dCachedScript["url"]
    lFailures = []
    for sUrl in lAxeCdnUrls:
        homerLog.info(f"Fetching axe-core from {sUrl}")
        try:
            sSource = fetchText(sUrl)
        except Exception as exception:
            homerLog.warning(f"Could not fetch axe-core from {sUrl}: {exception}")
            lFailures.append(f"{sUrl}: {exception}")
            continue
        dCachedScript["source"] = sSource
        dCachedScript["url"] = sUrl
        dCachedScript["version"] = readAxeVersion(sSource)
        homerLog.info(
            f"Fetched axe-core {dCachedScript['version']}, {len(sSource)} characters, from {sUrl}"
        )
        return sSource, sUrl
    raise AxeError(
        "axe-core could not be downloaded. Check the internet connection. Tried: "
        + "; ".join(lFailures)
    )


def buildRunOptions():
    dOptions = dict(dAxeRunOptions)
    if lAxeTags:
        dOptions["runOnly"] = {"type": "tag", "values": lAxeTags}
    return dOptions


def runAxe(cdpSession, pathFolder):
    """Inject axe-core into the focused page, run it, and save the results.

    Only the top document is analysed for now. Covering nested frames needs axe
    injected into each of them before the page loads, which means reloading, and
    that would discard whatever the user had typed.
    """
    logSection("Command: run axe-core")
    sSource, sSourceUrl = getAxeScript()
    dTarget, sSessionId = cdpSession.findActivePageSession()
    sPageUrl = dTarget.get("url", "")
    sPageTitle = dTarget.get("title", "")
    homerLog.info(f"Running axe-core against {abbreviate(sPageTitle, 120)} at {abbreviate(sPageUrl, 300)}")

    cdpSession.evaluate(sSessionId, sSource)
    if not cdpSession.evaluate(sSessionId, "Boolean(window.axe && window.axe.run)"):
        raise AxeError("axe-core did not load into the page")
    homerLog.info("axe-core injected; running the rules")

    dOptions = buildRunOptions()
    homerLog.info(f"axe-core options: {dOptions}")
    sExpression = (
        "(async () => JSON.stringify(await window.axe.run(document, "
        + json.dumps(dOptions)
        + ")))()"
    )
    sResults = cdpSession.evaluate(sSessionId, sExpression, axeRunTimeoutSeconds)
    if not sResults:
        raise AxeError("axe-core returned no results")
    dResults = json.loads(sResults)

    dCounts = {sOutcome: len(dResults.get(sOutcome) or []) for sOutcome in lOutcomeNames}
    homerLog.info(f"axe-core rule counts: {dCounts}")
    for dViolation in (dResults.get("violations") or [])[:40]:
        homerLog.debug(
            f"Violation {dViolation.get('id')}: impact {dViolation.get('impact')}, "
            f"{len(dViolation.get('nodes') or [])} nodes, {abbreviate(dViolation.get('help', ''), 200)}"
        )

    pathResults = pathFolder / axeResultsFileName
    pathResults.write_text(json.dumps(dResults, indent=2), encoding="utf-8")
    homerLog.info(f"Saved axe-core results to {pathResults}, {pathResults.stat().st_size} bytes")

    return {
        "counts": dCounts,
        "results": dResults,
        "sessionId": sSessionId,
        "path": str(pathResults),
        "pageTitle": sPageTitle,
        "pageUrl": sPageUrl,
        "sourceUrl": sSourceUrl,
        "timestampUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": dCachedScript.get("version", fallbackAxeVersion),
    }
