"""Act on the page by describing what you want, in the spirit of Stagehand.

Stagehand is an MIT licensed browser automation framework from Browserbase.
Its interesting idea is not the language model; it is the page representation.
Stagehand drives a browser over the DevTools Protocol and hands the model the
page's accessibility tree rather than its markup, because roles and names are
what an action is actually about. A screen reader user navigates that same
tree. So the representation transfers to HomerView exactly.

What does not transfer is the model. HomerView has no such service, and adding
one would mean sending the page somewhere. So this resolves a phrase by
matching it against the page's controls instead of by inference.

For this particular user that trade is favourable rather than merely
acceptable. A model guesses which control you meant and acts; this finds every
control that could match, tells you the role and name of each, and lets you
choose when there is more than one. The result is deterministic, reviewable
before it happens, and repeatable, which is what Stagehand's own documentation
says people want once an automation reaches production.

Actions are dispatched as real input events through the Input domain, at the
element's own coordinates, rather than by calling click in script. A scripted
click fires no pointer sequence, does not reliably move focus, and does not
satisfy the user-activation checks that guard popups and the clipboard.
"""

import re

import addonHandler

from .logger import abbreviate, homerLog, logSection

addonHandler.initTranslation()

actTimeoutSeconds = 30.0
maximumCandidates = 12
strongScore = 90

# The verb decides what happens; everything after it names the target.
dVerbs = {
    "check": "check",
    "choose": "click",
    "click": "click",
    "enter": "type",
    "fill": "type",
    "focus": "focus",
    "follow": "click",
    "open": "click",
    "press": "click",
    "read": "read",
    "select": "click",
    "tick": "check",
    "type": "type",
    "uncheck": "uncheck",
    "untick": "uncheck",
}

# A phrase often names the kind of thing as well as its label.
dRoleWords = {
    "box": ["textbox", "checkbox", "combobox"],
    "button": ["button"],
    "checkbox": ["checkbox"],
    "field": ["textbox", "searchbox", "combobox"],
    "heading": ["heading"],
    "link": ["link"],
    "menu": ["menu", "menuitem"],
    "option": ["option", "radio"],
    "tab": ["tab"],
}

# Enumerates what can be acted on, with the name a screen reader would use and
# the coordinates an input event needs. Names come from the same sources the
# accessible name calculation uses, in the same order of precedence.
surveyScript = r"""(() => {
    const lResults = [];
    const visible = el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return s.display !== "none" && s.visibility !== "hidden" &&
            s.opacity !== "0" && r.width > 0 && r.height > 0;
    };
    const labelFor = el => {
        if (el.labels && el.labels.length) {
            return Array.from(el.labels).map(l => (l.innerText || "").trim()).join(" ");
        }
        const sId = el.getAttribute("aria-labelledby");
        if (sId) {
            return sId.split(/\s+/).map(s => {
                const elRef = document.getElementById(s);
                return elRef ? (elRef.innerText || "").trim() : "";
            }).join(" ").trim();
        }
        return "";
    };
    const roleOf = el => {
        const sRole = (el.getAttribute("role") || "").toLowerCase();
        if (sRole) return sRole;
        const sTag = el.tagName.toLowerCase();
        if (sTag === "a") return el.hasAttribute("href") ? "link" : "generic";
        if (sTag === "button") return "button";
        if (sTag === "select") return "combobox";
        if (sTag === "textarea") return "textbox";
        if (/^h[1-6]$/.test(sTag)) return "heading";
        if (sTag === "input") {
            const sType = (el.getAttribute("type") || "text").toLowerCase();
            if (sType === "checkbox") return "checkbox";
            if (sType === "radio") return "radio";
            if (sType === "submit" || sType === "button" || sType === "reset") return "button";
            if (sType === "search") return "searchbox";
            return "textbox";
        }
        return "generic";
    };
    const lNodes = Array.from(document.querySelectorAll(
        "a[href], button, input:not([type=hidden]), select, textarea, summary, " +
        "[role=button], [role=link], [role=checkbox], [role=radio], [role=tab], " +
        "[role=menuitem], [role=option], [role=combobox], [role=textbox], [contenteditable=true]"));
    for (let i = 0; i < lNodes.length && lResults.length < 400; i += 1) {
        const el = lNodes[i];
        if (!visible(el)) continue;
        const sName = (
            (el.getAttribute("aria-label") || "").trim() ||
            labelFor(el) ||
            (el.innerText || "").trim() ||
            (el.getAttribute("title") || "").trim() ||
            (el.getAttribute("alt") || "").trim() ||
            (el.getAttribute("placeholder") || "").trim() ||
            (el.getAttribute("value") || "").trim()
        ).replace(/\s+/g, " ").slice(0, 160);
        if (!sName) continue;
        const r = el.getBoundingClientRect();
        lResults.push({
            checked: el.checked === true,
            index: i,
            name: sName,
            role: roleOf(el),
            x: Math.round(r.left + r.width / 2),
            y: Math.round(r.top + r.height / 2)
        });
    }
    window.__homerViewTargets = lNodes;
    return lResults;
})()"""


def parsePhrase(sPhrase):
    """Split a phrase into a verb, a target, and a value where there is one."""
    sPhrase = " ".join(str(sPhrase or "").split())
    sVerb = "click"
    lWords = sPhrase.split()
    if lWords and lWords[0].lower() in dVerbs:
        sVerb = dVerbs[lWords[0].lower()]
        lWords = lWords[1:]
    sRest = " ".join(lWords)
    sValue = ""
    if sVerb == "type":
        # "type Jamal in the search field" and "type Jamal into search".
        match = re.split(r"\s+(?:in|into|to)\s+", sRest, maxsplit=1)
        if len(match) == 2:
            sValue, sRest = match[0], match[1]
        else:
            sValue, sRest = sRest, ""
    for sWord in ("the", "a", "an"):
        sRest = re.sub(rf"^\s*{sWord}\s+", "", sRest, flags=re.IGNORECASE)
    return sVerb, sRest.strip(), sValue.strip()


def scoreCandidate(dCandidate, sTarget, lWantedRoles):
    """Rank a control against the phrase. Higher is better."""
    sName = (dCandidate.get("name") or "").lower()
    sRole = (dCandidate.get("role") or "").lower()
    sTarget = sTarget.lower().strip()
    if not sTarget:
        return 0
    iScore = 0
    if sName == sTarget:
        iScore = 100
    elif sName.startswith(sTarget):
        iScore = 85
    elif sTarget in sName:
        iScore = 70
    else:
        lWords = [s for s in re.split(r"\W+", sTarget) if s]
        if not lWords:
            return 0
        iHits = sum(1 for s in lWords if s in sName)
        if not iHits:
            return 0
        iScore = int(45 * iHits / len(lWords))
    if lWantedRoles:
        iScore += 10 if sRole in lWantedRoles else -25
    # A shorter name that still matches is usually the one meant.
    iScore -= min(10, max(0, (len(sName) - len(sTarget)) // 20))
    return iScore


def findCandidates(lSurvey, sTarget):
    lWantedRoles = []
    for sWord, lRoles in dRoleWords.items():
        if re.search(rf"\b{sWord}s?\b", sTarget, re.IGNORECASE):
            lWantedRoles.extend(lRoles)
            sTarget = re.sub(rf"\b{sWord}s?\b", " ", sTarget, flags=re.IGNORECASE)
    sTarget = " ".join(sTarget.split())
    lScored = []
    for dCandidate in lSurvey:
        iScore = scoreCandidate(dCandidate, sTarget, lWantedRoles)
        if iScore > 0:
            lScored.append((iScore, dCandidate))
    lScored.sort(key=lambda t: -t[0])
    return lScored[:maximumCandidates]


def describeCandidate(dCandidate):
    return f"{dCandidate.get('role', '')}: {dCandidate.get('name', '')}"


def performAction(cdpSession, sSessionId, dCandidate, sVerb, sValue):
    """Carry out the action with real input events."""
    iIndex = dCandidate["index"]
    cdpSession.evaluate(
        sSessionId,
        f'window.__homerViewTargets[{int(iIndex)}]'
        '.scrollIntoView({block: "center", inline: "center"})',
    )
    dBox = cdpSession.evaluate(
        sSessionId,
        f"(() => {{ const r = window.__homerViewTargets[{int(iIndex)}]"
        ".getBoundingClientRect();"
        " return {x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2)}; })()",
    ) or {}
    iX, iY = int(dBox.get("x", dCandidate.get("x", 0))), int(dBox.get("y", dCandidate.get("y", 0)))
    homerLog.info(f"Acting: {sVerb} on {describeCandidate(dCandidate)} at {iX},{iY}")

    if sVerb == "read":
        return cdpSession.evaluate(
            sSessionId,
            f"(window.__homerViewTargets[{int(iIndex)}].innerText || '').trim().slice(0, 2000)",
        ) or ""

    if sVerb == "focus":
        cdpSession.evaluate(sSessionId, f"window.__homerViewTargets[{int(iIndex)}].focus()")
        return "focused"

    for dParameters in (
        {"type": "mouseMoved", "x": iX, "y": iY, "button": "none", "clickCount": 0},
        {"type": "mousePressed", "x": iX, "y": iY, "button": "left", "clickCount": 1},
        {"type": "mouseReleased", "x": iX, "y": iY, "button": "left", "clickCount": 1},
    ):
        cdpSession.call("Input.dispatchMouseEvent", dParameters, sSessionId)

    if sVerb == "type" and sValue:
        cdpSession.evaluate(sSessionId, f"window.__homerViewTargets[{int(iIndex)}].focus()")
        cdpSession.call("Input.insertText", {"text": sValue}, sSessionId)
        return f"typed {sValue}"
    if sVerb in ("check", "uncheck"):
        bWanted = sVerb == "check"
        bNow = bool(
            cdpSession.evaluate(
                sSessionId, f"window.__homerViewTargets[{int(iIndex)}].checked === true"
            )
        )
        if bNow != bWanted:
            # The click above already toggled it the wrong way; put it back.
            for dParameters in (
                {"type": "mousePressed", "x": iX, "y": iY, "button": "left", "clickCount": 1},
                {"type": "mouseReleased", "x": iX, "y": iY, "button": "left", "clickCount": 1},
            ):
                cdpSession.call("Input.dispatchMouseEvent", dParameters, sSessionId)
        return "checked" if bWanted else "unchecked"
    return "clicked"


def survey(cdpSession):
    """Return the page's actionable controls, with the session to act on."""
    logSection("Command: act on the page")
    dTarget, sSessionId = cdpSession.findActivePageSession()
    lSurvey = cdpSession.evaluate(sSessionId, surveyScript, actTimeoutSeconds) or []
    homerLog.info(f"Survey found {len(lSurvey)} actionable controls")
    return lSurvey, sSessionId
