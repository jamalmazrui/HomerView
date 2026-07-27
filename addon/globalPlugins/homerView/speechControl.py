"""The Homer grave accent family: punctuation, rate and volume.

EdSharp puts four adjustments on one key with different modifiers, and the
arrangement is worth copying exactly because it is easy to remember and easy to
reach. From edsharp.jkm:

    JAWSKey+Grave         toggle punctuation between all and none
    Control+Grave         speak faster
    Control+Shift+Grave   speak slower
    Alt+Grave             louder
    Alt+Shift+Grave       softer

HomerView keeps the same shape. Punctuation moves to Control+Alt+Grave, since
NVDA's own modifier is not used for page commands here, and the other four are
unchanged.

Everything is done through NVDA's own speech configuration rather than by
talking to a synthesiser, so a change made here is the change the user would
have made in NVDA's settings, is saved with their profile, and survives
restarting. A command that adjusted something NVDA did not know about would
disagree with the settings dialog the moment it was opened.

Punctuation toggles between none and all rather than cycling four levels. Homer
does it that way because the two ends are what a reader actually switches
between: reading prose, and reading a url or a line of code where every
character matters.
"""

import addonHandler
import config
import ui

from .logger import homerLog, logError

addonHandler.initTranslation()

rateStep = 5
volumeStep = 5

# NVDA's symbol levels. The two ends are what a reader switches between.
dSymbolLevels = {
    0: "none",
    100: "some",
    200: "most",
    300: "all",
    400: "character",
}


def getSpeechSection():
    return config.conf["speech"][config.conf["speech"]["synth"]]


def togglePunctuation():
    """Switch between no punctuation and all of it, as Homer does."""
    try:
        iCurrent = config.conf["speech"]["symbolLevel"]
        iWanted = 0 if iCurrent > 0 else 300
        config.conf["speech"]["symbolLevel"] = iWanted
        homerLog.info(f"Punctuation level {iCurrent} became {iWanted}")
        # Translators: Reported when punctuation is turned off.
        ui.message(_("No punctuation") if iWanted == 0 else _("All punctuation"))
    except Exception:
        logError("The punctuation level could not be changed")
        # Translators: Reported when a speech setting could not be changed.
        ui.message(_("That speech setting could not be changed"))


def adjustRate(bFaster):
    """Speak faster or slower, in NVDA's own setting."""
    try:
        dSection = getSpeechSection()
        iCurrent = dSection["rate"]
        iWanted = max(0, min(100, iCurrent + (rateStep if bFaster else -rateStep)))
        dSection["rate"] = iWanted
        homerLog.info(f"Speech rate {iCurrent} became {iWanted}")
        # The number is spoken rather than a word, because a reader adjusting
        # rate is aiming at a value and needs to know where they have got to.
        # Translators: Reported after changing the speech rate.
        ui.message(_("Rate {value}").format(value=iWanted))
    except Exception:
        logError("The speech rate could not be changed")
        # Translators: Reported when a speech setting could not be changed.
        ui.message(_("That speech setting could not be changed"))


def adjustVolume(bLouder):
    """Louder or softer, in NVDA's own setting."""
    try:
        dSection = getSpeechSection()
        iCurrent = dSection["volume"]
        iWanted = max(0, min(100, iCurrent + (volumeStep if bLouder else -volumeStep)))
        dSection["volume"] = iWanted
        homerLog.info(f"Speech volume {iCurrent} became {iWanted}")
        # Translators: Reported after changing the speech volume.
        ui.message(_("Volume {value}").format(value=iWanted))
    except Exception:
        logError("The speech volume could not be changed")
        # Translators: Reported when a speech setting could not be changed.
        ui.message(_("That speech setting could not be changed"))


def reportSpeechSettings():
    """Say where the three adjustable settings currently stand."""
    try:
        dSection = getSpeechSection()
        iLevel = config.conf["speech"]["symbolLevel"]
        return [
            _("Punctuation: {level}").format(level=dSymbolLevels.get(iLevel, iLevel)),
            _("Rate: {value}").format(value=dSection["rate"]),
            _("Volume: {value}").format(value=dSection["volume"]),
        ]
    except Exception:
        logError("The speech settings could not be read")
        return [_("The speech settings could not be read")]
