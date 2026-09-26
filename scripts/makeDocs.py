"""Generate Hotkeys.md and the command section of HomerView.md.

Both come from the command table, and from the same grouping, so the standalone
list and the guide cannot disagree about what a key does or where it belongs.

The standalone file uses one heading level higher than the section inside the
guide, because it is a document in its own right rather than part of one.
"""

import io
import os
import pathlib
import re
import sys

# EVERY PATH BELOW IS RELATIVE TO THE PROJECT, so this starts there. It moved
# into scripts\ on 26 September 2026 and is run both by the build, from the
# project folder, and by hand from wherever a person happens to be; changing
# directory once is what makes both work.
_sScriptFolder = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.dirname(_sScriptFolder)
         if os.path.basename(_sScriptFolder).lower() == "scripts" else _sScriptFolder)
sys.path.insert(0, "addon/globalPlugins/homerView")
import commands as c  # noqa: E402

sPage = pathlib.Path("addon/globalPlugins/homerView/pageBuffer.py").read_text(encoding="utf-8-sig")
sSegment = sPage[sPage.index("dModifierNames = {"):sPage.index("dHomerNames = {")]
dNames = {"re": re}
exec(compile(sSegment, "describeGesture", "exec"), dNames)
describe = dNames["describeGesture"]


def keysOf(lKeys):
    """Every key that runs a command, shortest first."""
    return ", or ".join(
        describe(s) for s in sorted(set(lKeys), key=lambda k: (len(k.split("+")), k)))


def commandLines(iLevel):
    """The whole command list, at whichever heading level is wanted."""
    lLines = []
    for sTitle, lEntries in c.grouped():
        lLines.append("#" * iLevel + " " + sTitle)
        lLines.append("")
        # Sorted by name inside each group, so a reader who half remembers what
        # a command is called can find it without reading the group twice.
        for sScript, dEntry in sorted(lEntries, key=lambda t: t[1]["name"].lower()):
            sKeys = keysOf(dEntry["keys"]) or "no key"
            lLines.append(f"- **{dEntry['name']}**, {sKeys}. {dEntry['description']}")
        lLines.append("")
    return lLines


# THE HOMER SPELLING OF A KEY, so an NVDA gesture and a JAWS key map line can
# be compared at all. NVDA writes "kb:alt+shift+'" and "kb:alt+f1"; JAWS writes
# Alt+Shift+Apostrophe and Alt+F1. This is a Python stand-in for the kit's
# KeyName class, which holds the full table in C#; when the kit grows a Python
# mirror, this goes and that is used. Modifiers alphabetised, Control spelled
# out, the reader key called NVDA or JAWS, punctuation by its JAWS name.
dKeySpelling = {"'": "Apostrophe", "`": "GraveAccent", ";": "SemiColon", "/": "Slash",
                ".": "Period", ",": "Comma", "-": "Dash", "=": "Equals", "[": "LeftBracket",
                "]": "RightBracket", "\\": "Backslash", "space": "Space", "delete": "Delete",
                "downarrow": "DownArrow", "uparrow": "UpArrow", "leftarrow": "LeftArrow",
                "rightarrow": "RightArrow", "pageup": "PageUp", "pagedown": "PageDown",
                "home": "Home", "end": "End", "tab": "Tab", "enter": "Enter", "escape": "Escape",
                "backspace": "Backspace", "insert": "Insert", "accent": "GraveAccent",
                "grave": "GraveAccent", "graveaccent": "GraveAccent", "scrolllock": "ScrollLock",
                "numpaddelete": "NumPadDelete", "capslock": "CapsLock"}
dModifier = {"ctrl": "Control", "control": "Control", "alt": "Alt", "shift": "Shift",
             "windows": "Windows", "win": "Windows", "nvda": "NVDA", "jawskey": "JAWS", "jaws": "JAWS"}


def canonicalKey(sKey):
    """One spelling for a keystroke, whichever notation it came in."""
    sKey = (sKey or "").replace("kb:", "")
    lParts = [p.strip() for p in sKey.split("+") if p.strip()]
    lMods, sMain = [], ""
    for i, sPart in enumerate(lParts):
        sLower = sPart.lower()
        if i < len(lParts) - 1 and sLower in dModifier:
            lMods.append(dModifier[sLower])
        elif sLower in dKeySpelling:
            sMain = dKeySpelling[sLower]
        elif re.fullmatch(r"f\d{1,2}", sLower):
            sMain = sLower.upper()
        else:
            sMain = sPart.upper() if len(sPart) == 1 else sPart
    return "+".join(sorted(lMods) + [sMain]) if sMain else ""


def writeHotkeys():
    lLines = [
        "---", "title: HomerView Hotkeys",
        "subtitle: Every command, its key, and why that key",
        "author: Jamal Mazrui", "---", "",
        "# About this list", "",
        "Every HomerView command, grouped by what you are trying to do and sorted by",
        "name inside each group. Where the key is not obvious, the description says",
        "why it is that key.", "",
        "The same list is in the guide, HomerView.md, as one of its sections. This",
        "file is here so you can keep it open beside your work.", "",
        "Press Alt+Shift+H in HomerView and the program builds this list for itself,",
        "from the same source, so it is never out of date.", "",
        "# How to read a key", "",
        "Modifiers come in alphabetical order: Alt, Control, NVDA, Shift. So",
        "Alt+NVDA+C, never NVDA+Alt+C. Key names are the ones JAWS uses, because most",
        "blind Windows users have read those for years, so Accent rather than Grave",
        "and SemiColon rather than semicolon.", "",
        "ALMOST EVERY KEY IS THE SAME ON JAWS AND NVDA NOW. The screen reader",
        "modifier is gone from all but a few, because these keys live in the",
        "browser's own key map and do nothing in any other program, so they never",
        "needed to be safe everywhere on the machine.", "",
        "Alt+Shift+letter rather than Alt+letter, because a Chromium browser fires",
        "a page's access key on Alt+letter and does not on Alt+Shift+letter.", "",
        "A command with no key still runs, from the Alternate Menu on Alt+F10.",
        "You can give it a key in NVDA's Input Gestures dialog, under the HomerView",
        "category, where every command here can be changed.", "",
    ]
    lLines += commandLines(1)
    pathlib.Path("help/hotkeys.md").write_text("\n".join(lLines) + "\n", encoding="utf-8")
    return sum(1 for s in lLines if s.startswith("- **"))


def writeStartPage():
    """Write the start page's command list from the two key tables.

    WHY THIS IS GENERATED NOW. The list was prose inside startPage.py, and on
    17 September 2026 it was describing a key scheme from several weeks
    earlier: J and Shift+J for the main content, Y and Alt+Y for the yield
    commands, Alt+K for the accessibility check. Every one of those had moved,
    and the page a new reader sees first was the last thing telling the truth.

    ONLY COMMANDS WITH THE SAME KEY ON BOTH SCREEN READERS. The start page is
    the friendliest page HomerView has, and a line that has to explain that
    JAWS uses one key and NVDA another is not friendly. A command whose keys
    differ is left off entirely rather than hedged: it is still on the
    Alternate Menu, which is where a reader looks for everything.

    The JAWS keys come from chainJawsScripts and the NVDA keys from the command
    table, so the page cannot drift from either.
    """
    import re as reModule

    # NVDA keys, names and descriptions.
    dNvda = {}
    for sScript, dEntry in c.byScript().items():
        if not dEntry["keys"]:
            continue
        dNvda[dEntry["name"]] = (dEntry["keys"][0].replace("kb:", ""), dEntry["description"])

    # JAWS keys, by the script name the menu rows also use.
    sChain = pathlib.Path("scripts/chainJawsScripts.ps1").read_text(encoding="utf-8-sig")
    dJaws = {}
    for oMatch in reModule.finditer(r'"([^"=]+)=(\w+)"', sChain):
        dJaws[oMatch.group(2)] = oMatch.group(1)

    # The menu rows tie a JAWS script to the command name both sides use.
    sJss = pathlib.Path("scripts/jaws/HomerView.jss").read_text(encoding="utf-8-sig")
    dNameOfScript = {}
    for oMatch in reModule.finditer(r'"([^"\\]+?), [^"]*?\\t(hV\w+)\\t[PA]"', sJss):
        dNameOfScript[oMatch.group(2)] = oMatch.group(1)

    lRows = []
    for sScript, sJawsKey in dJaws.items():
        sName = dNameOfScript.get(sScript)
        if not sName or sName not in dNvda:
            continue
        sNvdaKey, sDescription = dNvda[sName]
        if canonicalKey(sJawsKey) != canonicalKey(sNvdaKey):
            continue
        lRows.append((sName, canonicalKey(sJawsKey), sDescription))
    lRows.sort(key=lambda t: t[0].lower())

    lLines = ["<h2>Commands</h2>",
              "<p>These work the same way whether you use JAWS or NVDA. Press Alt+F10",
              "for the full list, including the few that differ.</p>",
              "<ul>"]
    for sName, sKey, sDescription in lRows:
        # THE FIRST SENTENCE ONLY. The command table's descriptions carry the
        # reasoning behind a key as well as what it does, which belongs in the
        # hotkey list and not on the page somebody meets first. A start page
        # earns its place by being short.
        sShort = sDescription.split(". ")[0].rstrip(".") + "."
        lLines.append("<li><strong>%s</strong>, %s &mdash; %s</li>"
                      % (sName, sKey, sShort))
    lLines.append("</ul>")

    pathPage = pathlib.Path("addon/globalPlugins/homerView/startPage.py")
    sPage = pathPage.read_text(encoding="utf-8-sig")
    sBegin = "<!-- COMMANDS BEGIN. Written by makeDocs; do not edit between the markers. -->"
    sEnd = "<!-- COMMANDS END -->"
    iStart = sPage.index(sBegin) + len(sBegin)
    iFinish = sPage.index(sEnd)
    sPage = sPage[:iStart] + "\r\n" + "\r\n".join(lLines) + "\r\n" + sPage[iFinish:]
    # THE HOMER ENCODING, WRITTEN BACK DELIBERATELY. write_text uses the
    # platform newline, which on a file read as CRLF and rewritten leaves a
    # mixture: every generated line LF and every untouched line CRLF. The
    # file still parses and still works, which is exactly why it would have
    # gone unnoticed.
    sPage = sPage.replace("\r\n", "\n")

    # THE VERSION IS THE CONTENT, NOT A NUMBER SOMEBODY REMEMBERS.
    #
    # The add-on rewrites the reader's copy of the page only when the
    # version marker in it differs, and on 17 September 2026 the page was
    # rewritten here while startPageVersion stayed at 18. So the marker
    # matched, the copy was judged current, and the reader went on being
    # shown a page describing keys that no longer existed.
    #
    # A hash of the page cannot be forgotten. Change any word and the
    # version changes with it.
    import hashlib
    iStartText = sPage.index('startPageText = ')
    sBody = sPage[iStartText:]
    sVersion = hashlib.md5(sBody.encode("utf-8")).hexdigest()[:8]
    sPage = reModule.sub(r'(?m)^startPageVersion = "[^"]*"',
                         'startPageVersion = "' + sVersion + '"', sPage, count=1)
    with io.open(pathPage, "w", encoding="utf-8-sig", newline="\r\n") as oFile:
        oFile.write(sPage)

    # AND THE SECOND COPY, WHICH IS THE ONE THE DESKTOP SHORTCUT SERVES.
    #
    # Start.htm at the top of the project is installed into Program Files
    # and copied to the reader's folder by HomerView.exe. It is a separate
    # file from startPage.py and nothing kept the two together, so fixing
    # one left the other describing the old keys. It is rendered from the
    # same text here, so there is one source and two outputs.
    sRendered = sPage[sPage.index('startPageText = """') + len('startPageText = """'):]
    sRendered = sRendered[:sRendered.index('"""')]
    sRendered = sRendered.replace("{version}", sVersion)
    os.makedirs("templates", exist_ok=True)
    with io.open("templates/Start.htm", "w", encoding="utf-8-sig", newline="\r\n") as oFile:
        oFile.write(sRendered.lstrip("\n"))
    return len(lRows)


def writeHotkeysInix():
    """Write configs\\Hotkeys.inix from the two key tables.

    The old Hotkeys.inix was hand-maintained and read by nothing, and by
    26 September 2026 it listed Alt+NVDA+H and Alt+NVDA+F10 -- keys that had
    not existed for weeks -- while being shipped to every user. The kit lays
    an app's hotkey list in configs\\, so it lives there, and it is written
    from the same tables as hotkeys.md and the start page, so it cannot be
    wrong on its own.

    Every command is listed. Where the two screen readers share a key it is
    written once; where they differ, both are written, marked.
    """
    import re as reModule
    dNvda = {}
    for sScript, dEntry in c.byScript().items():
        sKey = dEntry["keys"][0].replace("kb:", "") if dEntry["keys"] else ""
        dNvda[dEntry["name"]] = (sKey, dEntry["description"])
    sChain = pathlib.Path("scripts/chainJawsScripts.ps1").read_text(encoding="utf-8-sig")
    dJaws = {m.group(2): m.group(1) for m in reModule.finditer(r'"([^"=]+)=(\w+)"', sChain)}
    sJss = pathlib.Path("scripts/jaws/HomerView.jss").read_text(encoding="utf-8-sig")
    dJawsKeyOfName = {}
    for m in reModule.finditer(r'"([^"\\]+?), [^"]*?\\t(hV\w+)\\t[PA]"', sJss):
        if m.group(2) in dJaws:
            dJawsKeyOfName[m.group(1)] = dJaws[m.group(2)]

    lLines = ["[Hotkeys]",
              "; Written by makeDocs from the command table and the JAWS key list. Do not",
              "; edit: the next build writes it again. Name=Key, Description. Where JAWS",
              "; and NVDA differ, both keys are given.", ""]
    for sName in sorted(dNvda, key=str.lower):
        sNvdaKey, sDescription = dNvda[sName]
        sNvda = canonicalKey(sNvdaKey)
        sJawsKey = canonicalKey(dJawsKeyOfName.get(sName, ""))
        if sNvda and sJawsKey and sNvda != sJawsKey:
            sKey = "NVDA %s, JAWS %s" % (sNvda, sJawsKey)
        else:
            sKey = sNvda or sJawsKey or "no key"
        sShort = sDescription.split(". ")[0].rstrip(".") + "."
        lLines.append("%s=%s, %s" % (sName, sKey, sShort))
    os.makedirs("configs", exist_ok=True)
    with io.open("configs/Hotkeys.inix", "w", encoding="utf-8-sig", newline="\r\n") as oFile:
        oFile.write("\n".join(lLines) + "\n")
    return len(dNvda)


def checkGuideKeys():
    """Every NVDA key the guide states, against the command table.

    WHY THIS EXISTS. checkGuideSection only ever asked whether a command was
    MENTIONED. On 26 September 2026 four entries named keys that had changed
    nine days earlier -- Log to Clipboard, Save Page, Toggle Punctuation, and
    Consult Copilot, which a blanket replace had given another command's key --
    and every build passed, because each command was still mentioned.

    THE NVDA SIDE ONLY, because there the guide and the table use the same
    names. The JAWS menu names some commands differently ("Hot Key Help" for
    Hotkey Summary), so a JAWS check by name would report agreement as error.
    Keys are compared in the one Homer spelling, so "Accent" and "GraveAccent"
    are the same key.
    """
    sGuide = pathlib.Path("help/HomerView.md").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    dTable = {e["name"]: sorted(canonicalKey(k) for k in e["keys"]) for e in c.byScript().values()}
    lWrong = []
    for oMatch in re.finditer(r"^- \*\*(.+?)\*\*\n    - NVDA: (.+)\n", sGuide, re.M):
        sName, sKeys = oMatch.group(1), oMatch.group(2)
        if sName not in dTable:
            continue
        lGuide = sorted(canonicalKey(x.strip()) for x in re.split(r",\s*or\s*|,\s*|\s+or\s+", sKeys)
                        if x.strip() and "no key" not in x.lower())
        if lGuide != dTable[sName]:
            lWrong.append("%s: the guide says %s, the command table says %s"
                          % (sName, " or ".join(lGuide) or "no key", " or ".join(dTable[sName]) or "no key"))
    return lWrong


def checkGuideSection():



    """Say whether the guide's hotkey section still names every command.

    IT USED TO REWRITE THAT SECTION, AND THAT WAS WRONG TWICE OVER.

    First, the anchors it cut between -- "# Every command" and "# Opening
    documents" -- were the headings the guide had when this was written. The
    guide was later restructured to the house rule, h2 for a topic category
    and h3 for a topic, and neither string existed any more. So this raised
    ValueError, and the guide silently stopped being regenerated while
    Hotkeys.md went on being correct.

    Second, and the reason it is not simply repaired: THE GUIDE SAYS MORE THAN
    THE TABLE KNOWS. Its hotkey section gives the NVDA key AND the JAWS key for
    every command, and the command table holds only NVDA gestures. Rewriting
    the section from the table would have quietly deleted every JAWS key in the
    guide, which is the opposite of the parity the guide exists to describe.

    So it checks instead. Anything in the table and not in the guide is named
    here, and adding it is a two-minute job that only a person can do, because
    only a person knows the JAWS key.
    """
    sGuide = pathlib.Path("help/HomerView.md").read_text(encoding="utf-8-sig")
    lMissing = []
    for _sTitle, lEntries in c.grouped():
        for _sScript, dEntry in lEntries:
            if ("**" + dEntry["name"] + "**") not in sGuide:
                lMissing.append(dEntry["name"])
    return lMissing


def grade(sText):
    """A rough reading level, for checking that the documents stay plain."""
    sBody = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", sText)
    sBody = re.sub(r"^---.*?---", "", sBody, flags=re.S)
    sBody = re.sub(r"^#.*$", "", sBody, flags=re.M)
    sBody = re.sub(r"^    .*$", "", sBody, flags=re.M)
    sBody = re.sub(r"https?://\S+", "", sBody)
    lSentences = [s for s in re.split(r"[.!?]+", sBody) if len(s.split()) > 3]
    lWords = re.findall(r"[A-Za-z']+", sBody)
    if not lSentences or not lWords:
        return 0.0

    def syllables(sWord):
        sWord = sWord.lower()
        iCount = len(re.findall(r"[aeiouy]+", sWord))
        if sWord.endswith("e") and iCount > 1:
            iCount -= 1
        return max(1, iCount)

    return (0.39 * (len(lWords) / len(lSentences))
            + 11.8 * (sum(syllables(s) for s in lWords) / len(lWords)) - 15.59)


if __name__ == "__main__":
    print(f"Hotkeys.md: {writeHotkeys()} commands")
    print(f"Start page: {writeStartPage()} commands with the same key on both")
    print(f"Hotkeys.inix: {writeHotkeysInix()} commands")
    # A GUIDE THAT NAMES THE WRONG KEY IS A PROGRAM THAT DOES NOT WORK AS
    # ADVERTISED, so both failures stop the build. A missing command used to
    # be printed and passed, and "Page Folder" was printed on every build for
    # weeks without anyone acting on it -- which is what a notice that never
    # fails anything turns into.
    bFailed = False
    lMissing = checkGuideSection()
    if lMissing:
        bFailed = True
        print(f"ERROR: HomerView.md does not mention {len(lMissing)} command(s):")
        for sName in lMissing:
            print(f"  {sName}")
    else:
        print("HomerView.md mentions every command in the table.")
    lWrongKeys = checkGuideKeys()
    if lWrongKeys:
        bFailed = True
        print(f"ERROR: HomerView.md names the wrong NVDA key for {len(lWrongKeys)} command(s):")
        for sLine in lWrongKeys:
            print(f"  {sLine}")
    else:
        print("HomerView.md names the right NVDA key for every command.")
    print()
    # MATCHED WITHOUT REGARD TO CASE, because the file on disk is README.md
    # while the setup script and this list both say ReadMe.md. Windows does
    # not care and neither does the installer; a case-sensitive filesystem
    # does, and this then stopped with a file-not-found on a name that was
    # plainly there. Worth settling one day with git mv; worth not failing
    # over meanwhile.
    dOnDisk = {p.name.lower(): p for p in list(pathlib.Path(".").glob("*.md")) + list(pathlib.Path("help").glob("*.md"))}
    for sName in ("ReadMe", "HomerView", "Developer", "History", "Announce", "Hotkeys"):
        pathDocument = dOnDisk.get(sName.lower() + ".md")
        if pathDocument is None:
            print(f"  {sName + '.md':16} is not here")
            continue
        sText = pathDocument.read_text(encoding="utf-8-sig")
        nGrade = grade(sText)
        sFlag = "" if nGrade <= 9.0 else "   ABOVE NINTH GRADE"
        print(f"  {sName + '.md':16} {len(re.findall(r'[A-Za-z]+', sText)):>5} words, "
              f"grade {nGrade:>4.1f}{sFlag}")
    if bFailed:
        # The build reads this exit code and stops, naming makeDocs.
        sys.exit(1)
