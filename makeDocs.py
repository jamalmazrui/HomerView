"""Generate Hotkeys.md and the command section of HomerView.md.

Both come from the command table, and from the same grouping, so the standalone
list and the guide cannot disagree about what a key does or where it belongs.

The standalone file uses one heading level higher than the section inside the
guide, because it is a document in its own right rather than part of one.
"""

import pathlib
import re
import sys

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
        "Alt+NVDA+H, never NVDA+Alt+H. Key names are the ones JAWS uses, because most",
        "blind Windows users have read those for years, so Accent rather than Grave",
        "and SemiColon rather than semicolon.", "",
        "Where a command has two keys, the short one works inside a HomerView page",
        "and the long one works anywhere.", "",
        "A command with no key still runs, from the Alternate Menu on Alt+NVDA+F10.",
        "You can give it a key in NVDA's Input Gestures dialog, under the HomerView",
        "category, where every command here can be changed.", "",
    ]
    lLines += commandLines(1)
    pathlib.Path("Hotkeys.md").write_text("\n".join(lLines) + "\n", encoding="utf-8")
    return sum(1 for s in lLines if s.startswith("- **"))


def writeGuideSection():
    """Replace the command section of HomerView.md with a fresh one."""
    pathGuide = pathlib.Path("HomerView.md")
    sGuide = pathGuide.read_text(encoding="utf-8-sig")
    sStart = "# Every command\n"
    sEnd = "\n# Opening documents"
    iStart, iEnd = sGuide.index(sStart), sGuide.index(sEnd)
    lLines = [
        "# Every command", "",
        "Every command HomerView has, grouped by what you are trying to do and",
        "sorted by name inside each group. Where the key is not obvious, the",
        "description says why it is that key.", "",
        "The same list is also a file of its own, Hotkeys.md, so you can keep it",
        "open beside your work. Alt+Shift+H builds it inside HomerView.", "",
    ]
    lLines += commandLines(2)
    pathGuide.write_text(sGuide[:iStart] + "\n".join(lLines) + sGuide[iEnd:], encoding="utf-8")
    return sum(1 for s in lLines if s.startswith("- **"))


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
    print(f"HomerView.md command section: {writeGuideSection()} commands")
    print()
    for sName in ("ReadMe", "HomerView", "Developer", "History", "Announce", "Hotkeys"):
        sText = pathlib.Path(f"{sName}.md").read_text(encoding="utf-8-sig")
        nGrade = grade(sText)
        sFlag = "" if nGrade <= 9.0 else "   ABOVE NINTH GRADE"
        print(f"  {sName + '.md':16} {len(re.findall(r'[A-Za-z]+', sText)):>5} words, "
              f"grade {nGrade:>4.1f}{sFlag}")
