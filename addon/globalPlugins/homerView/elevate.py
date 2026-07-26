"""Elevate Version: check for a newer HomerView and install it.

The design is DbDo's, which is the fullest of the three and had the sharpest
reasoning behind each step. Four of its decisions are kept unchanged.

The version check asks the GitHub releases API for the latest tag, and falls
back to fetching the releases page and reading the tag out of the address it
redirects to. The API is cleaner but rate limits unauthenticated callers, and
the redirect has no such limit, so having both means a check that works when
the first is exhausted.

Being already current does not end the command. It offers to reinstall the same
version instead, which is what someone wants when a build is damaged or an
install did not take. That last case is not hypothetical: a tester ran an older
add-on for a whole session because an installer checkbox was unchecked, and this
command is how he would have repaired it himself.

Running a newer version than the public release is reported rather than treated
as an error, and no downgrade is offered. That is the normal state of the
developer's own machine.

The version is compared numerically rather than as text, so 1.11.0 is correctly
newer than 1.9.2. String comparison gets that backwards, and this project has
already passed the point where it matters.

One thing differs from DbDo, and it is the point of the command here. DbDo
downloads an installer and lets it take over. HomerView's program files matter
less than its add-on: the add-on is what NVDA loads, and until NVDA has it,
nothing works. So the add-on package is downloaded and handed to NVDA, which
asks the user to confirm and then restarts itself. The installer is mentioned
afterwards, for the documentation and the converters, but it is not what makes
the commands appear.
"""

import json
import os
import re
import urllib.error
import urllib.request

import addonHandler

from . import paths
from .logger import abbreviate, homerLog, logError, logSection

addonHandler.initTranslation()

addonAssetName = "HomerView.nvda-addon"
fetchTimeoutSeconds = 30.0
installerAssetName = "HomerView_setup.exe"
projectRepository = "JamalMazrui/HomerView"
userAgent = "HomerView (+NVDA add-on, version check)"

apiUrl = f"https://api.github.com/repos/{projectRepository}/releases/latest"
latestPageUrl = f"https://github.com/{projectRepository}/releases/latest"
addonDownloadUrl = f"https://github.com/{projectRepository}/releases/latest/download/{addonAssetName}"
installerDownloadUrl = f"https://github.com/{projectRepository}/releases/latest/download/{installerAssetName}"


class ElevateError(Exception):
    pass


def fetchLatestTag():
    """Return the latest release tag, by the API or by the redirect."""
    try:
        request = urllib.request.Request(
            apiUrl, headers={"Accept": "application/vnd.github+json", "User-Agent": userAgent})
        with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
            dRelease = json.loads(response.read().decode("utf-8"))
        sTag = str(dRelease.get("tag_name", "")).strip()
        if sTag:
            homerLog.info(f"The releases API reports the latest tag as {sTag}")
            return sTag
        homerLog.warning("The releases API answered without a tag_name")
    except Exception as exception:
        homerLog.warning(f"The releases API could not be reached: {exception}")

    # The API rate limits unauthenticated callers; the redirect does not.
    try:
        request = urllib.request.Request(latestPageUrl, headers={"User-Agent": userAgent})
        with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
            sFinalUrl = getattr(response, "url", "") or ""
        match = re.search(r"/tag/([^/]+)/?$", sFinalUrl)
        if match:
            sTag = match.group(1)
            homerLog.info(f"The releases page redirected to tag {sTag}")
            return sTag
        homerLog.warning(f"The releases page redirected to {abbreviate(sFinalUrl, 200)} with no tag")
    except Exception as exception:
        homerLog.warning(f"The releases page could not be reached: {exception}")
    raise ElevateError(
        "The latest version could not be determined. Check the internet connection, "
        f"or visit {latestPageUrl}"
    )


# Version comparison lives in the shared toolkit, because three programs in
# this family needed it and wrote it three times.
from .homer.version import compare as compareVersions  # noqa: E402


def readInstalledVersion():
    from . import logger

    return logger.readAddonVersion()


def downloadAsset(sUrl, sName):
    """Download a release asset to the temporary folder."""
    pathTarget = paths.getTempFolder() / sName
    homerLog.info(f"Downloading {sUrl}")
    request = urllib.request.Request(sUrl, headers={"User-Agent": userAgent})
    with urllib.request.urlopen(request, timeout=fetchTimeoutSeconds) as response:
        bBody = response.read()
    if len(bBody) < 1000:
        raise ElevateError(
            f"The download was only {len(bBody)} bytes, which is too small to be the "
            "add-on. The release may not have that file attached."
        )
    pathTarget.write_bytes(bBody)
    homerLog.info(f"Wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return pathTarget


def checkForUpdate():
    """Return what is installed, what is available, and how they compare."""
    logSection("Command: elevate version")
    sInstalled = readInstalledVersion()
    sLatest = fetchLatestTag().lstrip("vV").strip()
    iComparison = compareVersions(sLatest, sInstalled)
    homerLog.info(
        f"Installed {sInstalled}, latest {sLatest}, "
        f"{'newer available' if iComparison > 0 else 'up to date' if iComparison == 0 else 'ahead of release'}"
    )
    return {"comparison": iComparison, "installed": sInstalled, "latest": sLatest}


def installAddon():
    """Download the add-on and hand it to NVDA, which does the rest."""
    pathAddon = downloadAsset(addonDownloadUrl, addonAssetName)
    # Handing the file to the shell is what reaches NVDA, because NVDA
    # registers itself for this extension. NVDA then shows its own
    # confirmation and restarts itself, which is the right flow for something
    # this consequential: the user sees the prompt they expect and can decline.
    try:
        os.startfile(str(pathAddon))
        homerLog.info(f"Handed {pathAddon} to NVDA for installation")
        return {"opened": True, "path": str(pathAddon)}
    except Exception:
        logError("The add-on downloaded but could not be handed to NVDA")
        return {"opened": False, "path": str(pathAddon)}
