r"""keys.py -- part of the shared Homer toolkit.

ONE WAY TO HANDLE A KEY IN A HOMER APP'S NVDA ADD-ON, MATCHING ITS JAWS SCRIPTS.

Every Homer app's screen reader scripts decide two things about a key, the same
way in JAWS and NVDA (the homer-screen-reader skill's key-handling reference):

  WHAT the script does with it
    capture          the script does the work; the app never sees the key
    passQuietly      the key goes to the app, and the reader says nothing
    passThenSpeak    the key goes to the app, then the reader speaks
    speakThenPass    the reader speaks, then the key goes to the app

  WHERE it does so
    everywhere       in every control of the app
    only here        in one control, window or process, with a stated fallback
                     elsewhere: the reader's own handling, or the key passed on

The app does the work and speaks through the kit's Say; a script only decides
who gets the key and whether the reader adds anything. Keyboard interruptibility
is on in every reader, so the next key cuts off speech in progress; nothing here
interrupts speech itself.

This module holds the NVDA half. Each app's build copies it into its add-on --
DbDo's into appModules\homer, HomerView's into globalPlugins\homerView\homer --
so every add-on runs the same code. It imports NVDA's modules only when a
function is called, so it can be imported, and checked, outside NVDA too.

THE SIX-PACK RULE. A key is sent to the app by its six-pack name even when the
user pressed the number pad with NumLock off: NVDA names those keys numpad1 to
numpad9, and sending the original gesture back did not deliver extended keys
reliably (DbDo's add-on, NVDA 2025 and 2026). passQuietly and the others build a
fresh gesture from the canonical name, so the app always sees the same key.
"""

import time

# Number-pad keys with NumLock off, by the six-pack key they stand for. numpad5 has none.
dNumpadToSixpack = {
	"numpad7": "home", "numpad1": "end", "numpad9": "pageUp", "numpad3": "pageDown",
	"numpad8": "upArrow", "numpad2": "downArrow", "numpad4": "leftArrow", "numpad6": "rightArrow",
}


def canonicalChord(gesture):
	"""The gesture as a chord for KeyboardInputGesture.fromName: kb:alt+control+numpad6 -> alt+control+rightArrow."""
	sId = gesture.identifiers[0] if getattr(gesture, "identifiers", None) else ""
	lParts = sId.split(":", 1)[-1].split("+")
	return "+".join(lParts[:-1] + [dNumpadToSixpack.get(lParts[-1], lParts[-1])])


def passQuietly(gesture):
	"""Send the key to the app by its six-pack name; the reader says nothing."""
	import keyboardHandler
	from logHandler import log
	sChord = canonicalChord(gesture)
	try:
		keyboardHandler.KeyboardInputGesture.fromName(sChord).send()
	except Exception as oError:
		log.error("homer keys: passQuietly(%r) failed, so the original key is sent: %s" % (sChord, oError))
		gesture.send()


def passThenSpeak(gesture, sText, iDelayMs=50):
	"""Send the key, then speak sText once the app has had a moment to act on it."""
	import core
	import ui
	passQuietly(gesture)
	core.callLater(iDelayMs, ui.message, sText)


def speakThenPass(gesture, sText):
	"""Speak sText, then send the key."""
	import ui
	ui.message(sText)
	passQuietly(gesture)


# QUIET FOCUS, for a key passed only in one control whose move the reader would
# otherwise announce -- such as DbDo's grid, where DbDo reads the row itself.
# quietNextFocus() is called as the key is sent; the control's overlay class
# then skips the one focus announcement the move causes.
nQuietFocusUntil = 0.0


def quietNextFocus(nSeconds=0.5):
	"""Leave the next focus announcement, within nSeconds, unspoken."""
	global nQuietFocusUntil
	nQuietFocusUntil = time.time() + nSeconds


def focusIsQuiet():
	"""True once, for the focus announcement quietNextFocus asked to skip."""
	global nQuietFocusUntil
	if time.time() < nQuietFocusUntil:
		nQuietFocusUntil = 0.0
		return True
	return False


def onlyHere(functionScript, bHere):
	"""Where: only here, for a global plugin's or app module's getScript. Returns the script where it belongs and None
	elsewhere; None hands the key back, so it goes on to the focused program as though it were not bound."""
	return functionScript if bHere else None


def windowClassIs(obj, sClassPart):
	"""Whether obj's window class contains sClassPart, such as SysListView32: the usual test for 'only here' by control."""
	return sClassPart in (getattr(obj, "windowClassName", "") or "")


def sayVersions(appModule):
	"""The program's name and version, then the add-on's: NVDA's counterpart of the JAWS scripts' JAWS+Q."""
	import addonHandler
	import ui
	sProgram = "%s %s" % (getattr(appModule, "productName", "") or appModule.appName, getattr(appModule, "productVersion", "") or "")
	try:
		oAddon = addonHandler.getCodeAddon()
		sAddon = "%s add-on %s" % (oAddon.manifest["summary"], oAddon.version)
	except Exception:
		sAddon = "add-on version unknown"
	ui.message("%s; %s" % (sProgram.strip(), sAddon))
