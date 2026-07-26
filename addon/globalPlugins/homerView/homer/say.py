"""One way to announce text, whatever happens to be listening.

The C# Say module exists because a program outside a screen reader has to try
several channels in turn: the JAWS COM interface, then the NVDA controller
client, then a native UIA notification. Inside an NVDA add-on none of that is
needed, because NVDA is the host and speaks directly.

What is still worth having is the single entry point. Library code that calls
NVDA's ui.message cannot be tested outside NVDA and cannot be reused in a plain
program. Calling say() instead means the module works in both places, and the
one import of NVDA is here rather than scattered through every caller.
"""

import sys


def say(sText, bInterrupt=False):
    """Announce text through whatever is available."""
    if not sText:
        return False
    try:
        import ui

        ui.message(str(sText))
        return True
    except Exception:
        pass
    try:
        import speech

        speech.speakText(str(sText))
        return True
    except Exception:
        pass
    # Outside a screen reader, saying something to nobody should not be an
    # error, but it should be visible when a developer is watching.
    print(str(sText), file=sys.stderr)
    return False


def spell(sText):
    """Announce text one character at a time."""
    if not sText:
        return False
    try:
        import speech

        speech.speakSpelling(str(sText))
        return True
    except Exception:
        return say(" ".join(str(sText)))


def browseable(sBody, sTitle="", bHtml=True):
    """Show text in a window that can be read like a document."""
    try:
        import ui

        try:
            ui.browseableMessage(sBody, sTitle, bHtml)
        except TypeError:
            ui.browseableMessage(sBody, title=sTitle, isHtml=bHtml)
        return True
    except Exception:
        return say(sBody)
