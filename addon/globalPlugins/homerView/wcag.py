"""WCAG success criteria, and the mapping from axe-core rules to them.

Ported from urlCheck. Two tables do the work.

dWcagSc gives every success criterion a short name, a conformance level, and
the principle it sits under, so a report can say 1.3.1 Info and Relationships,
Level A, Perceivable rather than leaving the reader with a bare number.

dAdvisoryRefs covers axe's best-practice rules, which carry no wcag tags at all.
These are the closest related criteria, and a report must label them advisory:
telling a publisher they have failed a criterion they have not actually failed
wastes everyone's time and undermines the parts of the report that are true.
"""

import re

understandingUrlBase = "https://www.w3.org/WAI/WCAG22/Understanding/"

# Success criterion number to short name, conformance level, and principle.
dWcagSc = {
    "1.1.1": ("Non-text Content", "A", "Perceivable"),
    "1.2.1": ("Audio-only and Video-only (Prerecorded)", "A", "Perceivable"),
    "1.2.2": ("Captions (Prerecorded)", "A", "Perceivable"),
    "1.2.3": ("Audio Description or Media Alternative", "A", "Perceivable"),
    "1.2.4": ("Captions (Live)", "AA", "Perceivable"),
    "1.2.5": ("Audio Description (Prerecorded)", "AA", "Perceivable"),
    "1.2.6": ("Sign Language (Prerecorded)", "AAA", "Perceivable"),
    "1.2.7": ("Extended Audio Description (Prerecorded)", "AAA", "Perceivable"),
    "1.2.8": ("Media Alternative (Prerecorded)", "AAA", "Perceivable"),
    "1.2.9": ("Audio-only (Live)", "AAA", "Perceivable"),
    "1.3.1": ("Info and Relationships", "A", "Perceivable"),
    "1.3.2": ("Meaningful Sequence", "A", "Perceivable"),
    "1.3.3": ("Sensory Characteristics", "A", "Perceivable"),
    "1.3.4": ("Orientation", "AA", "Perceivable"),
    "1.3.5": ("Identify Input Purpose", "AA", "Perceivable"),
    "1.3.6": ("Identify Purpose", "AAA", "Perceivable"),
    "1.4.1": ("Use of Color", "A", "Perceivable"),
    "1.4.2": ("Audio Control", "A", "Perceivable"),
    "1.4.3": ("Contrast (Minimum)", "AA", "Perceivable"),
    "1.4.4": ("Resize Text", "AA", "Perceivable"),
    "1.4.5": ("Images of Text", "AA", "Perceivable"),
    "1.4.6": ("Contrast (Enhanced)", "AAA", "Perceivable"),
    "1.4.7": ("Low or No Background Audio", "AAA", "Perceivable"),
    "1.4.8": ("Visual Presentation", "AAA", "Perceivable"),
    "1.4.9": ("Images of Text (No Exception)", "AAA", "Perceivable"),
    "1.4.10": ("Reflow", "AA", "Perceivable"),
    "1.4.11": ("Non-text Contrast", "AA", "Perceivable"),
    "1.4.12": ("Text Spacing", "AA", "Perceivable"),
    "1.4.13": ("Content on Hover or Focus", "AA", "Perceivable"),
    "2.1.1": ("Keyboard", "A", "Operable"),
    "2.1.2": ("No Keyboard Trap", "A", "Operable"),
    "2.1.3": ("Keyboard (No Exception)", "AAA", "Operable"),
    "2.1.4": ("Character Key Shortcuts", "A", "Operable"),
    "2.2.1": ("Timing Adjustable", "A", "Operable"),
    "2.2.2": ("Pause, Stop, Hide", "A", "Operable"),
    "2.2.3": ("No Timing", "AAA", "Operable"),
    "2.2.4": ("Interruptions", "AAA", "Operable"),
    "2.2.5": ("Re-authenticating", "AAA", "Operable"),
    "2.2.6": ("Timeouts", "AAA", "Operable"),
    "2.3.1": ("Three Flashes or Below Threshold", "A", "Operable"),
    "2.3.2": ("Three Flashes", "AAA", "Operable"),
    "2.3.3": ("Animation from Interactions", "AAA", "Operable"),
    "2.4.1": ("Bypass Blocks", "A", "Operable"),
    "2.4.2": ("Page Titled", "A", "Operable"),
    "2.4.3": ("Focus Order", "A", "Operable"),
    "2.4.4": ("Link Purpose (In Context)", "A", "Operable"),
    "2.4.5": ("Multiple Ways", "AA", "Operable"),
    "2.4.6": ("Headings and Labels", "AA", "Operable"),
    "2.4.7": ("Focus Visible", "AA", "Operable"),
    "2.4.8": ("Location", "AAA", "Operable"),
    "2.4.9": ("Link Purpose (Link Only)", "AAA", "Operable"),
    "2.4.10": ("Section Headings", "AAA", "Operable"),
    "2.4.11": ("Focus Not Obscured (Minimum)", "AA", "Operable"),
    "2.4.12": ("Focus Not Obscured (Enhanced)", "AAA", "Operable"),
    "2.4.13": ("Focus Appearance", "AA", "Operable"),
    "2.5.1": ("Pointer Gestures", "A", "Operable"),
    "2.5.2": ("Pointer Cancellation", "A", "Operable"),
    "2.5.3": ("Label in Name", "A", "Operable"),
    "2.5.4": ("Motion Actuation", "A", "Operable"),
    "2.5.5": ("Target Size (Enhanced)", "AAA", "Operable"),
    "2.5.6": ("Concurrent Input Mechanisms", "AAA", "Operable"),
    "2.5.7": ("Dragging Movements", "AA", "Operable"),
    "2.5.8": ("Target Size (Minimum)", "AA", "Operable"),
    "3.1.1": ("Language of Page", "A", "Understandable"),
    "3.1.2": ("Language of Parts", "AA", "Understandable"),
    "3.1.3": ("Unusual Words", "AAA", "Understandable"),
    "3.1.4": ("Abbreviations", "AAA", "Understandable"),
    "3.1.5": ("Reading Level", "AAA", "Understandable"),
    "3.1.6": ("Pronunciation", "AAA", "Understandable"),
    "3.2.1": ("On Focus", "A", "Understandable"),
    "3.2.2": ("On Input", "A", "Understandable"),
    "3.2.3": ("Consistent Navigation", "AA", "Understandable"),
    "3.2.4": ("Consistent Identification", "AA", "Understandable"),
    "3.2.5": ("Change on Request", "AAA", "Understandable"),
    "3.2.6": ("Consistent Help", "A", "Understandable"),
    "3.3.1": ("Error Identification", "A", "Understandable"),
    "3.3.2": ("Labels or Instructions", "A", "Understandable"),
    "3.3.3": ("Error Suggestion", "AA", "Understandable"),
    "3.3.4": ("Error Prevention (Legal, Financial, Data)", "AA", "Understandable"),
    "3.3.5": ("Help", "AAA", "Understandable"),
    "3.3.6": ("Error Prevention (All)", "AAA", "Understandable"),
    "3.3.7": ("Redundant Entry", "A", "Understandable"),
    "3.3.8": ("Accessible Authentication (Minimum)", "AA", "Understandable"),
    "3.3.9": ("Accessible Authentication (Enhanced)", "AAA", "Understandable"),
    "4.1.1": ("Parsing", "A", "Robust"),
    "4.1.2": ("Name, Role, Value", "A", "Robust"),
    "4.1.3": ("Status Messages", "AA", "Robust"),
}

# Advisory only: closest related criteria for axe best-practice rules.
dAdvisoryRefs = {
    "accesskeys": ['2.1.4'],
    "aria-allowed-role": ['4.1.2'],
    "aria-dialog-name": ['4.1.2'],
    "avoid-inline-spacing": ['1.4.12'],
    "css-orientation-lock": ['1.3.4'],
    "empty-heading": ['2.4.6'],
    "empty-table-header": ['1.3.1'],
    "focus-trap": ['2.1.2'],
    "frame-tested": ['4.1.2'],
    "heading-order": ['2.4.6'],
    "hidden-content": ['4.1.2'],
    "identical-links-same-purpose": ['2.4.9'],
    "label-title-only": ['3.3.2'],
    "landmark-banner-is-top-level": ['1.3.1'],
    "landmark-complementary-is-top-level": ['1.3.1'],
    "landmark-contentinfo-is-top-level": ['1.3.1'],
    "landmark-main-is-top-level": ['1.3.1'],
    "landmark-no-duplicate-banner": ['1.3.1'],
    "landmark-no-duplicate-contentinfo": ['1.3.1'],
    "landmark-no-duplicate-main": ['1.3.1'],
    "landmark-one-main": ['2.4.1'],
    "landmark-unique": ['1.3.1'],
    "meta-viewport": ['1.4.4'],
    "p-as-heading": ['1.3.1'],
    "page-has-heading-one": ['2.4.6'],
    "presentation-role-conflict": ['4.1.2'],
    "region": ['1.3.1', '2.4.1'],
    "scope-attr-valid": ['1.3.1'],
    "scrollable-region-focusable": ['2.1.1'],
    "select-name": ['4.1.2'],
    "server-side-image-map": ['2.1.1'],
    "skip-link": ['2.4.1'],
    "summary-name": ['4.1.2'],
    "tabindex": ['2.4.3'],
    "table-duplicate-name": ['1.3.1'],
    "table-fake-caption": ['1.3.1'],
    "target-size": ['2.5.8'],
}



def refFromTag(sTag):
    """Return a criterion number such as 1.4.3 from an axe tag such as wcag143."""
    sTag = str(sTag)
    if not sTag.startswith("wcag"):
        return ""
    if re.fullmatch(r"wcag\d+[a-z]+", sTag):
        return ""
    sDigits = re.sub(r"[^0-9]", "", sTag)
    if len(sDigits) < 3:
        return ""
    return f"{sDigits[0]}.{sDigits[1]}.{sDigits[2]}"


def refsForRule(dRule):
    """Return the criteria for a rule, and whether they are advisory."""
    lRefs = []
    for sTag in dRule.get("tags") or []:
        sRef = refFromTag(sTag)
        if sRef and sRef not in lRefs:
            lRefs.append(sRef)
    if lRefs:
        return lRefs, False
    if "best-practice" in (dRule.get("tags") or []):
        for sRef in dAdvisoryRefs.get(str(dRule.get("id") or ""), []):
            if sRef not in lRefs:
                lRefs.append(sRef)
        return lRefs, True
    return [], False


def describeRef(sRef):
    """Return name, level, and principle for a criterion, or empty strings."""
    tInfo = dWcagSc.get(sRef)
    return tInfo if tInfo else ("", "", "")


def isBestPractice(dRule):
    return "best-practice" in (dRule.get("tags") or [])


def understandingUrl(sRef):
    return f"{understandingUrlBase}{sRef}/"
