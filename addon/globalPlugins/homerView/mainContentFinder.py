"""Finding where a page's main content begins, and taking the cursor there.

Shift+J has always been the deliberate guess, for the half of the web that
declares no main landmark. Its guess was the first heading past the banner and
the navigation, which is right often enough to be useful and wrong in the two
places it matters most: a page whose article begins with a paragraph rather
than a heading, and a page whose navigation contains headings of its own.

This asks the browser instead. The same scoring Readability uses, and that
Firefox's reading mode is built on, is applied in the page: the element with
the most text and the fewest links wins, because that is what an article looks
like and what navigation does not.

Three ways of answering were considered, and they are not equal.

Mozilla's Readability is the best of them and is already here: HomerView
fetches, caches and injects it for the extract command. It has been developed
since 2010, ships in Firefox's reading mode, and has absorbed fifteen years of
corrections against pages that broke it. Its scoring is far more careful than
anything written here would be: it weighs paragraphs by comma count, propagates
a share of each paragraph's score to its parent and grandparent, penalises the
usual class and identifier names, and cleans the result afterwards.

The first version of this module reimplemented a simplified version of that
scoring, which was a mistake. A worse copy of an algorithm already loaded in
the same page is not worth having, and it would have drifted from the extract
command, so two commands claiming to find the main content would have disagreed
about where it was.

So Readability answers when it is available. The scoring below is the fallback
for when it could not be fetched, which is the same fallback the extract
command already uses, and it stays deliberately simple because a simple rule
that is understood beats a complicated one that is imitated.

The bridge between the two halves is the interesting part, and it is
deliberately not node identity. Chromium can say which DOM node holds the main
content, and NVDA's browse buffer has no notion of a DOM node, so mapping one
to the other would mean maintaining a correspondence that breaks whenever the
page changes. Instead the browser is asked for the opening WORDS of the main
content, and those words are found in NVDA's own buffer using NVDA's own
search. Text is the one representation both sides already share.

That is slower than a node lookup and enormously more robust. It also degrades
well: if the words cannot be found, the old heading heuristic still runs.
"""

import json

import addonHandler

from .logger import abbreviate, homerLog, logError, logSection

addonHandler.initTranslation()

findTimeoutSeconds = 20.0

# How much of the opening to ask for. Long enough to be unique on the page,
# short enough that a stray character does not prevent a match.
openingWords = 12

# Ask Readability where the article begins. Readability returns the article as
# markup rather than a position, so its opening text is what is wanted: the
# same text will be in NVDA's buffer, and that is the bridge.
readabilityOpeningScript = r"""(() => {
    if (typeof Readability === "undefined") return null;
    try {
        const dArticle = new Readability(document.cloneNode(true)).parse();
        if (!dArticle || !dArticle.content) return null;
        // The article as text, so its opening words can be searched for.
        const elHolder = document.createElement("div");
        elHolder.innerHTML = dArticle.content;
        const sText = (elHolder.innerText || elHolder.textContent || "")
            .replace(/\s+/g, " ").trim();
        if (!sText) return null;
        return {
            how: "Readability",
            length: dArticle.length || sText.length,
            text: sText.slice(0, 400),
            title: dArticle.title || ""
        };
    } catch (error) {
        return null;
    }
})()"""

# The extract command's own fallback, reused rather than written again.
from .mainContent import fallbackScript  # noqa: E402

def findMainContentOpening(cdpSession):
    """Ask where the main content starts, and for its first words.

    Readability first, because it is better than anything written here and is
    already loaded. The simple scoring second, for when it could not be
    fetched.
    """
    from . import mainContent

    logSection("Finding where the main content begins")
    dTarget, sSessionId = cdpSession.findActivePageSession()

    dResult = {}
    try:
        # The same injection the extract command uses, so the two commands
        # cannot disagree about where the article is.
        if mainContent.injectReadability(cdpSession, sSessionId):
            dResult = cdpSession.evaluate(
                sSessionId, readabilityOpeningScript, findTimeoutSeconds) or {}
    except Exception as exception:
        homerLog.warning(f"Readability could not be asked: {exception}")
        dResult = {}

    if not (dResult or {}).get("text"):
        homerLog.info("Readability gave no answer, so the simple scoring runs")
        dScored = cdpSession.evaluate(sSessionId, fallbackScript, findTimeoutSeconds) or {}
        if dScored.get("content"):
            # The fallback returns markup, as the extract command needs. Turn
            # it into the opening text this command needs.
            sText = cdpSession.evaluate(
                sSessionId,
                "(() => { const el = document.createElement('div');"
                f" el.innerHTML = {json.dumps(dScored['content'])};"
                " return (el.innerText || el.textContent || '')"
                ".replace(/\\s+/g, ' ').trim().slice(0, 400); })()",
                findTimeoutSeconds) or ""
            dResult = {"how": dScored.get("method", "scoring"), "text": sText,
                       "length": dScored.get("length", 0)}
    sText = str(dResult.get("text", "")).strip()
    homerLog.info(
        f"Main content by {dResult.get('how') or 'nothing'}: "
        f"{dResult.get('tag', '')} of {dResult.get('length', 0)} characters, "
        f"opening {abbreviate(sText, 120)}"
    )
    if not sText:
        return {}
    # The first several words, which is what will be searched for. A whole
    # paragraph would fail on any difference in spacing or punctuation between
    # what the browser reports and what NVDA built.
    lWords = sText.split()
    dResult["opening"] = " ".join(lWords[:openingWords])
    return dResult
