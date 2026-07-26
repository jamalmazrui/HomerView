"""Comparing versions, and asking GitHub what the latest release is.

The C# Version module and the Elevate Version command in DbDo, EdSharp and
FileDir all do this, and all three ended up writing it again. Here it is once.

Two things are worth stating because both have been got wrong in real programs.

A version is compared as numbers, not as text. Compared as text, 1.11.0 sorts
before 1.9.2, which is the wrong answer and stays wrong until someone notices
that upgrades stopped being offered.

The latest release is looked up two ways. The releases API is cleaner but rate
limits callers who do not authenticate, and a program that checks on every
start will meet that limit. The releases page redirects to the tagged release
and has no such limit, so it serves as the fallback.
"""

import json
import re
import urllib.request

fetchTimeoutSeconds = 30.0
userAgent = "Homer (+version check)"


def parse(sVersion):
    """Turn a version into a tuple of numbers, ignoring any leading letter."""
    return tuple(int(s) for s in re.findall(r"\d+", str(sVersion or ""))) or (0,)


def compare(sLeft, sRight):
    """Return 1, 0 or minus 1, comparing numerically rather than as text."""
    tLeft, tRight = parse(sLeft), parse(sRight)
    iLength = max(len(tLeft), len(tRight))
    tLeft += (0,) * (iLength - len(tLeft))
    tRight += (0,) * (iLength - len(tRight))
    return (tLeft > tRight) - (tLeft < tRight)


def isNewer(sCandidate, sCurrent):
    return compare(sCandidate, sCurrent) > 0


def fetchLatestTag(sOwnerRepo):
    """Return the latest release tag for owner/repo, or an empty string."""
    sApiUrl = f"https://api.github.com/repos/{sOwnerRepo}/releases/latest"
    try:
        request = urllib.request.Request(
            sApiUrl, headers={"Accept": "application/vnd.github+json", "User-Agent": userAgent})
        with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
            sTag = str(json.loads(response.read().decode("utf-8")).get("tag_name", "")).strip()
        if sTag:
            return sTag
    except Exception:
        pass
    sPageUrl = f"https://github.com/{sOwnerRepo}/releases/latest"
    try:
        request = urllib.request.Request(sPageUrl, headers={"User-Agent": userAgent})
        with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
            sFinalUrl = getattr(response, "url", "") or ""
        match = re.search(r"/tag/([^/]+)/?$", sFinalUrl)
        if match:
            return match.group(1)
    except Exception:
        pass
    return ""


def describe(sInstalled, sLatest):
    """Say in one sentence how the two compare."""
    if not sLatest:
        return "The latest version could not be determined."
    iComparison = compare(sLatest, sInstalled)
    if iComparison > 0:
        return f"A newer version is available: {sLatest}, and {sInstalled} is installed."
    if iComparison == 0:
        return f"Version {sInstalled} is the latest."
    return f"Version {sInstalled} is newer than the published {sLatest}."
